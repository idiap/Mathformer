#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic native, aggregate MCP and real Lunar/PRISM execution fixtures.

No provider or external compiler exists in this simulator. Fixed model JSON and
seeded random streams are the fixtures; the PRISM toolchain is never replaced.
"""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.path[:0] = [str(LUNAR / "app/backend"), str(ROOT / "scripts")]
import asyncio
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import tempfile
import unittest
from unittest.mock import patch
import yaml
from theory_evolution_simulate_tools import source
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.workflow_contract.validator import validate
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_paper_theory_evolution_simulate_workflow/workflow.yaml"
AUTHORED = "skills/control/workflow-contract-validator/references/theory-evolution-simulate.workflow.json"


def oracle():
    spec = importlib.util.spec_from_loader(
        "sim_original",
        SourceFileLoader(
            "sim_original",
            str(ROOT / "tests/mcp/fixtures/theory_evolution_simulate_original.py.txt"),
        ),
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def model():
    metrics = [
        "lean_executability",
        "anchor_coverage",
        "mathlib_grounding",
        "reverse_informal_consistency",
        "proof_coherence",
        "workflow_evidence",
    ]

    def phase(i, n):
        return dict(
            id=i,
            duration_steps=n,
            target=dict.fromkeys(metrics, 0.9),
            gain_rate=0.4,
            cost_per_step=2,
            regression_probability=0.65,
        )

    return dict(
        model_id="deterministic-fixture",
        metrics=metrics,
        initial_state=dict.fromkeys(metrics, 0.2),
        protected_metrics=metrics[:2],
        delta_notation={"epsilon": 1e-6},
        noise={"gain_sigma": 0.1, "cost_sigma": 0.1, "regression_scale": 0.4},
        couplings=[
            {"source": metrics[0], "target": metrics[1], "weight": 0.7},
            {"source": metrics[1], "target": metrics[0], "weight": 0.2},
        ],
        phases=[
            phase("empty", 0),
            phase("first", 2),
            phase("negative", -2),
            phase("last", 1),
        ],
        acceptance_thresholds={
            "complete": {metrics[0]: 0.95},
            "draft": {metrics[0]: 0.1},
        },
    )


def invoke(m, path, out, runs=2, seed=7, json_output=True):
    argv = [
        "sim",
        "--model",
        str(path),
        "--output-dir",
        str(out),
        "--runs",
        str(runs),
        "--seed",
        str(seed),
    ] + (["--json"] if json_output else [])
    stream = io.StringIO()
    with patch.object(sys, "argv", argv), redirect_stdout(stream):
        code = m.main()
    return code, stream.getvalue()


def snapshot(d):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(d))] + [
        asset(r["path"], (ROOT / r["path"]).read_text())
        for r in d["provenance"]["sources"]
    ]


class SimulationTests(unittest.TestCase):
    def test_original_source_equivalence(self):
        old, native = oracle(), source()
        for count in [0, 1, 256]:
            m = model()
            m["phases"][1]["duration_steps"] = count
            for seed in [7, 18]:
                self.assertEqual(
                    native.simulate_one(m, 2, seed), old.simulate_one(m, 2, seed)
                )
        for status, threshold in [("complete", 0), ("draft", 0.4), ("blocked", 1)]:
            m = model()
            m["phases"] = []
            m["acceptance_thresholds"] = {
                "complete": {m["metrics"][0]: threshold},
                "draft": {m["metrics"][0]: 0 if status == "draft" else 1},
            }
            self.assertEqual(native.simulate_one(m, 0, 7)["status"], status)
        m = model()
        m["gate_thresholds"] = m.pop("acceptance_thresholds")
        self.assertEqual(native.simulate_one(m, 0, 7), old.simulate_one(m, 0, 7))
        del m["gate_thresholds"]
        for implementation in [old, native]:
            with self.assertRaises(KeyError):
                implementation.simulate_one(m, 0, 7)
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "model.json"
            p.write_text(json.dumps(model()))
            out = Path(temp) / "out"
            for formatting in [False, True]:
                expected = invoke(old, p, out, json_output=formatting)
                artifacts = {f.name: f.read_bytes() for f in out.iterdir()}
                self.assertEqual(
                    invoke(native, p, out, json_output=formatting), expected
                )
                self.assertEqual(
                    {f.name: f.read_bytes() for f in out.iterdir()}, artifacts
                )

    def test_contract_and_generator(self):
        d = yaml.safe_load(Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text())
        self.assertEqual(d, json.loads((ROOT / AUTHORED).read_text()))
        r = validate(
            ROOT / AUTHORED, repository_root=ROOT, require_declared_bindings=True
        )
        self.assertTrue(r["valid"], r)
        for row in d["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        spec = importlib.util.spec_from_file_location(
            "sim_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        normalizer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(normalizer)
        self.assertEqual(
            next(x for x in normalizer.inventory() if x["id"] == d["id"]), d
        )

    def test_registered_tools_compile_and_execute(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        d = yaml.safe_load(Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text())
        manager = SessionManager()
        with tempfile.TemporaryDirectory(prefix="simulation-fixture-") as temp:
            directory = Path(temp)
            path = directory / "model.json"
            out = directory / "out"
            config = StdioConfig(
                command=str(ROOT / ".venv/bin/python"),
                args=[
                    str(ROOT / "tests/mcp/fixtures/theory_evolution_model_server.py"),
                    str(directory),
                ],
                cwd=str(ROOT),
            )
            async with manager.open("simulation", config, {}) as remote:
                failure = None
                try:
                    tools = [
                        t.model_dump(by_alias=True, exclude_none=True)
                        for t in await remote.tools()
                    ]
                    self.assertIn("mathformer_run_workflow", {t["name"] for t in tools})

                    def compile(doc, inventory=None):
                        assets = snapshot(doc)
                        compiled = compile_workflow(
                            "mcp:simulation",
                            workflow_documents([DESCRIPTOR], assets)[0],
                            tools if inventory is None else inventory,
                        )
                        return compiled, assets

                    workflow, assets = compile(d)
                    self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                    self.assertTrue(workflow["runtime_source"])
                    self.assertEqual(set(workflow["bindings"]), set(d["operations"]))
                    for op in d["operations"]:
                        target = d["operations"][op]["execution"]["binding"]["target"]
                        self.assertFalse(
                            compile(d, [t for t in tools if t["name"] != target])[0][
                                "runnable"
                            ]
                        )

                    async def allow():
                        pass

                    async def run(m, runs=2, doc=None):
                        path.write_text(json.dumps(m))
                        w, a = compile(doc) if doc else (workflow, assets)
                        return await execute(
                            w,
                            a,
                            {
                                "model": m,
                                "options": {
                                    "output_dir": str(out),
                                    "runs": runs,
                                    "json": True,
                                },
                                "context": {
                                    "working_directory": str(directory),
                                    "model_path": str(path),
                                },
                            },
                            remote,
                            allow,
                        )

                    # Mixed empty/negative/positive phases, coupling/regression, history and seed continuity.
                    m = model()
                    path.write_text(json.dumps(m))
                    expected = invoke(oracle(), path, out)
                    artifacts = {f.name: f.read_bytes() for f in out.iterdir()}
                    for f in out.iterdir():
                        f.unlink()
                    result = await run(m)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(result["outputs"]["stdout"], expected[1])
                    self.assertEqual(
                        {f.name: f.read_bytes() for f in out.iterdir()}, artifacts
                    )
                    self.assertEqual(
                        result["outputs"]["result"]["status_probabilities"],
                        {"complete": 0.0, "draft": 1.0, "blocked": 0.0},
                    )
                    simulation = json.loads(
                        (out / "simulated_trajectories.json").read_text()
                    )
                    self.assertEqual(
                        simulation["runs"],
                        [oracle().simulate_one(m, i, 7) for i in range(2)],
                    )
                    self.assertEqual([r["seed"] for r in simulation["runs"]], [7, 1016])
                    self.assertEqual(
                        len(
                            [
                                c
                                for c in result["calls"]
                                if c["tool"].endswith("advance_step")
                            ]
                        ),
                        10,
                    )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["runtime"]["provenance"])
                    self.assertTrue(result["replay_artifacts"])
                    # Scientific status never terminates steps or turns success into failure.
                    for status in ["complete", "blocked"]:
                        m = model()
                        m["acceptance_thresholds"] = {
                            "complete": (
                                {} if status == "complete" else {m["metrics"][0]: 1}
                            ),
                            "draft": {m["metrics"][0]: 1},
                        }
                        result = await run(m, 1)
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertEqual(
                            result["outputs"]["result"]["status_probabilities"][status],
                            1,
                        )
                        self.assertEqual(
                            sum(
                                c["tool"].endswith("advance_step")
                                for c in result["calls"]
                            ),
                            5,
                        )
                    # Exact run/phase caps terminate normally; empty trajectories still classify.
                    m = model()
                    m["phases"] = []
                    result = await run(m, 64)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(
                        sum(c["tool"].endswith("finish_run") for c in result["calls"]),
                        64,
                    )
                    m = model()
                    m["phases"] = [{**m["phases"][0], "id": str(i)} for i in range(16)]
                    result = await run(m, 1)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(
                        sum(
                            c["tool"].endswith("finish_phase") for c in result["calls"]
                        ),
                        16,
                    )
                    # Native aggregation and classification errors propagate without a report call succeeding.
                    for n in [0, -1]:
                        failed = await run(model(), n)
                        self.assertEqual(failed["status"], "failed", failed)
                        self.assertEqual(
                            [c["tool"] for c in failed["calls"]],
                            [
                                "mathformer_theory_simulate_" + n
                                for n in [
                                    "load",
                                    "initialize_run",
                                    "prepare_phase",
                                    "advance_step",
                                    "finish_phase",
                                    "finish_run",
                                    "report",
                                ]
                            ],
                        )
                    m = model()
                    del m["acceptance_thresholds"]
                    failed = await run(m, 1)
                    self.assertEqual(failed["status"], "failed", failed)
                    self.assertTrue(failed["calls"][-1]["tool"].endswith("finish_run"))
                    # Reduce only descriptor bounds to exercise Lunar's real exhaustion path.
                    bounded = deepcopy(d)

                    def lower(node):
                        if (
                            node.get("kind") == "loop"
                            and node.get("state_type") == "PhaseState"
                        ):
                            node["max_iterations"] = 1
                        for key in ["steps", "cases"]:
                            for child in node.get(key, []):
                                lower(child)
                        for key in ["body", "default"]:
                            if isinstance(node.get(key), dict):
                                lower(node[key])

                    lower(bounded["flow"])
                    failed = await run(model(), 1, bounded)
                    self.assertEqual(failed["status"], "failed", failed)
                    self.assertEqual(failed["failure_disposition"], "fail")
                    self.assertEqual(
                        sum(
                            c["tool"].endswith("advance_step") for c in failed["calls"]
                        ),
                        2,
                    )
                    self.assertFalse(
                        any(c["tool"].endswith("report") for c in failed["calls"])
                    )
                    # Native write ordering remains visible on a late artifact failure.
                    svg = out / "trajectory_shape.svg"
                    svg.unlink()
                    svg.mkdir()
                    report = out / "plausible_parameters_report.md"
                    report.unlink()
                    failed = await run(model(), 1)
                    self.assertEqual(failed["status"], "failed", failed)
                    self.assertTrue(failed["calls"][-1]["tool"].endswith("report"))
                    self.assertTrue((out / "simulated_trajectories.json").is_file())
                    self.assertTrue((out / "plausible_parameters.json").is_file())
                    self.assertTrue((out / "trajectory_summary.csv").is_file())
                    self.assertTrue(svg.is_dir())
                    self.assertFalse(report.exists())
                    # Actual aggregate policy rejects output escaping its configured root.
                    m = model()
                    path.write_text(json.dumps(m))
                    with self.assertRaises(Exception):
                        await remote.call(
                            "mathformer_theory_simulate_load",
                            {
                                "model": m,
                                "options": {
                                    "output_dir": str(
                                        directory.parent / (directory.name + "-escape")
                                    )
                                },
                                "context": {
                                    "working_directory": str(directory),
                                    "model_path": str(path),
                                },
                            },
                        )
                    blocker = directory / "blocker"
                    blocker.write_text("fixture")
                    with self.assertRaises(Exception):
                        await remote.call(
                            "mathformer_theory_simulate_load",
                            {
                                "model": m,
                                "options": {"output_dir": str(blocker / "out")},
                                "context": {
                                    "working_directory": str(directory),
                                    "model_path": str(path),
                                },
                            },
                        )
                except Exception as error:
                    failure = error
            if failure is not None:
                raise failure
            readonly = StdioConfig(
                command=str(ROOT / ".venv/bin/python"),
                args=[
                    str(ROOT / "tests/mcp/fixtures/theory_evolution_model_server.py"),
                    str(directory),
                    "--readonly",
                ],
                cwd=str(ROOT),
            )
            async with manager.open("readonly", readonly, {}) as remote:
                with self.assertRaises(Exception):
                    await remote.call(
                        "mathformer_theory_simulate_load",
                        {
                            "model": model(),
                            "options": {"output_dir": str(directory / "denied")},
                            "context": {
                                "working_directory": str(directory),
                                "model_path": str(path),
                            },
                        },
                    )
                self.assertFalse((directory / "denied").exists())
        self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
