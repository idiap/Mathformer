#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Seeded small-model fixtures, real aggregate MCP, and real Lunar/PRISM runtime.

The simulation owns its seeded RNG and has no external provider or compiler to
substitute. All scientific steps, rendering, parser/checker/compiler and runtime
are real. Only CLI config discovery is bypassed by the existing test server.
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
from contextlib import chdir, redirect_stdout
from copy import deepcopy
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import shutil
import tempfile
import unittest
from unittest.mock import patch
import yaml
from theory_evolution_suite_tools import source
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.workflow_contract.validator import validate
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_paper_theory_evolution_suite_workflow/workflow.yaml"
AUTHORED = "skills/control/workflow-contract-validator/references/theory-evolution-suite.workflow.json"
SCENARIOS = [
    "baseline",
    "accelerated_grounding",
    "grounding_bottleneck",
    "drift_repair_pressure",
    "noisy_plateau",
]


def oracle():
    source()  # Establish the native sibling-import path before loading the frozen CLI.
    name = "theory_suite_original"
    spec = importlib.util.spec_from_loader(
        name,
        SourceFileLoader(
            name,
            str(ROOT / "tests/mcp/fixtures/theory_evolution_suite_original.py.txt"),
        ),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def model():
    metrics = list(source().METRIC_LABELS)

    def phase(name, steps):
        return dict(
            id=name,
            duration_steps=steps,
            target=dict.fromkeys(metrics, 0.85),
            gain_rate=0.4,
            cost_per_step=2,
            regression_probability=0.7,
        )

    return dict(
        model_id="suite-fixture",
        metrics=metrics,
        protected_metrics=metrics[:2],
        initial_state=dict.fromkeys(metrics, 0.2),
        delta_notation={"epsilon": 1e-6},
        noise={"gain_sigma": 0.1, "cost_sigma": 0.2, "regression_scale": 0.3},
        couplings=[
            {"source": "mathlib_grounding", "target": "semantic_shape", "weight": 0.7}
        ],
        phases=[
            phase("drafting", 0),
            phase("mathlib_grounding", 2),
            phase("execution_critique", -2),
            phase("repair", 1),
            phase("consistency", 1),
            phase("evaluation_reflection", 1),
        ],
        acceptance_thresholds={
            "complete": {"lean_executability": 1},
            "draft": {"lean_executability": 0},
        },
    )


def invoke(module, options):
    argv = ["suite", "--model", options["model"], "--output-dir", options["output_dir"]]
    for key in ["runs", "seed"]:
        if key in options:
            argv += ["--" + key, str(options[key])]
    if "scenarios" in options:
        argv += ["--scenarios", *options["scenarios"]]
    if options.get("json"):
        argv += ["--json"]
    stream = io.StringIO()
    with patch.object(sys, "argv", argv), redirect_stdout(stream):
        code = module.main()
    return code, stream.getvalue()


def tree(path):
    return {
        str(p.relative_to(path)): p.read_bytes() for p in path.rglob("*") if p.is_file()
    }


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


class SuiteTests(unittest.TestCase):
    def test_contract_provenance_and_generator(self):
        d = yaml.safe_load(Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text())
        self.assertEqual(d, json.loads((ROOT / AUTHORED).read_text()))
        result = validate(
            ROOT / AUTHORED, repository_root=ROOT, require_declared_bindings=True
        )
        self.assertTrue(result["valid"], result)
        for row in d["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        spec = importlib.util.spec_from_file_location(
            "suite_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        normalizer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(normalizer)
        self.assertEqual(
            next(x for x in normalizer.inventory() if x["id"] == d["id"]), d
        )
        import mathformer as hub

        registry = hub.build_registry()
        action = registry["paper:theory-evolution-suite"]
        self.assertEqual(action.timeout_seconds, 1200)
        self.assertEqual(list(action.depends_on), [])
        self.assertTrue(action.allows_extra_args)
        audit = hub.audit_control(registry)
        for path in [
            "scripts/theory_evolution_suite_tools.py",
            "tests/mcp/run_theory_evolution_suite_workflow_tests.py",
        ]:
            self.assertNotIn(path, audit["uncontrolled_entrypoints"])

    def test_original_entrypoint_and_shared_stages(self):
        old, native = oracle(), source()
        original = model()
        for scenario in SCENARIOS:
            self.assertEqual(
                native.apply_scenario(original, scenario),
                old.apply_scenario(original, scenario),
            )
        self.assertEqual(original, model())
        accelerated = native.apply_scenario(original, "accelerated_grounding")
        self.assertAlmostEqual(accelerated["phases"][1]["gain_rate"], 0.4 * 1.22)
        self.assertEqual(
            native.apply_scenario(original, "drift_repair_pressure")["phases"][3][
                "duration_steps"
            ],
            5,
        )
        self.assertAlmostEqual(
            native.apply_scenario(original, "grounding_bottleneck")["phases"][1][
                "gain_rate"
            ],
            0.4 * 0.55,
        )
        self.assertAlmostEqual(
            native.apply_scenario(original, "noisy_plateau")["phases"][1]["target"][
                "lean_executability"
            ],
            0.79,
        )
        with tempfile.TemporaryDirectory() as temp, chdir(temp):
            path = Path("model.json")
            path.write_text(json.dumps(original))
            options = {"model": str(path), "output_dir": "out", "runs": 2, "seed": 11}
            for selection in [SCENARIOS, ["baseline", "baseline"]]:
                for json_output in [False, True]:
                    options.update(scenarios=selection, json=json_output)
                    expected = invoke(old, options)
                    artifacts = tree(Path("out"))
                    shutil.rmtree("out")
                    self.assertEqual(invoke(native, options), expected)
                    self.assertEqual(tree(Path("out")), artifacts)
                    shutil.rmtree("out")
            # The original CLI still permits more than five entries.
            options.update(scenarios=["baseline"] * 6, runs=1)
            self.assertEqual(invoke(native, options), invoke(old, options))
            for runs in [0, -1]:
                options.update(scenarios=["baseline"], runs=runs)
                for implementation in [old, native]:
                    with self.assertRaises(ZeroDivisionError):
                        invoke(implementation, options)

    def test_registered_tools_and_lunar_runtime(self):
        asyncio.run(self.runtime())

    async def runtime(self):
        d = yaml.safe_load(Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text())
        manager = SessionManager()
        with tempfile.TemporaryDirectory(prefix="theory-suite-fixture-") as temp:
            directory = Path(temp)
            out = directory / "out"
            path = directory / "model.json"
            config = StdioConfig(
                command=str(ROOT / ".venv/bin/python"),
                args=[
                    str(ROOT / "tests/mcp/fixtures/theory_evolution_model_server.py"),
                    str(directory),
                ],
                cwd=str(ROOT),
            )
            failure = None
            async with manager.open("theory-suite", config, {}) as remote:
                try:
                    tools = [
                        t.model_dump(by_alias=True, exclude_none=True)
                        for t in await remote.tools()
                    ]
                    self.assertIn("mathformer_run_workflow", {t["name"] for t in tools})

                    def compile(doc, inventory=None):
                        assets = snapshot(doc)
                        return (
                            compile_workflow(
                                "mcp:theory-suite",
                                workflow_documents([DESCRIPTOR], assets)[0],
                                tools if inventory is None else inventory,
                            ),
                            assets,
                        )

                    workflow, assets = compile(d)
                    self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                    self.assertTrue(workflow["runtime_source"])
                    self.assertEqual(set(workflow["bindings"]), set(d["operations"]))
                    for operation in d["operations"].values():
                        target = operation["execution"]["binding"]["target"]
                        self.assertFalse(
                            compile(d, [t for t in tools if t["name"] != target])[0][
                                "runnable"
                            ]
                        )

                    async def authorize():
                        pass

                    async def run(m, options=None, doc=None):
                        path.write_text(json.dumps(m))
                        w, a = compile(doc) if doc else (workflow, assets)
                        return await execute(
                            w,
                            a,
                            {
                                "options": {
                                    "model": "model.json",
                                    "output_dir": "out",
                                    **(options or {}),
                                },
                                "context": {"working_directory": str(directory)},
                            },
                            remote,
                            authorize,
                        )

                    # All five transforms, exact loop bound, native artifact bytes/stdout.
                    m = model()
                    path.write_text(json.dumps(m))
                    options = {
                        "model": "model.json",
                        "output_dir": "out",
                        "runs": 2,
                        "seed": 11,
                        "json": True,
                    }
                    with chdir(directory):
                        expected = invoke(oracle(), options)
                    artifacts = tree(out)
                    shutil.rmtree(out)
                    result = await run(m, {"runs": 2, "seed": 11, "json": True})
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(result["outputs"]["stdout"], expected[1])
                    self.assertEqual(result["outputs"]["exit_code"], 0)
                    self.assertEqual(
                        result["outputs"]["manifest"],
                        json.loads(
                            (out / "simulation_suite_manifest.json").read_text()
                        ),
                    )
                    self.assertEqual(tree(out), artifacts)
                    self.assertEqual(len(result["calls"]), 17)
                    self.assertEqual(
                        [c["tool"] for c in result["calls"]],
                        ["mathformer_theory_suite_initialize"]
                        + [
                            "mathformer_theory_suite_" + s
                            for _ in SCENARIOS
                            for s in ["prepare_scenario", "run_scenario", "accumulate"]
                        ]
                        + ["mathformer_theory_suite_finalize_suite"],
                    )
                    for index, scenario in enumerate(SCENARIOS):
                        simulation = json.loads(
                            (out / scenario / "simulated_trajectories.json").read_text()
                        )
                        scenario_model = oracle().apply_scenario(m, scenario)
                        self.assertEqual(
                            simulation["runs"],
                            [
                                oracle().simulate_one(
                                    scenario_model, i, 11 + index * 8191
                                )
                                for i in range(2)
                            ],
                        )
                        n = sum(
                            max(p["duration_steps"], 0)
                            for p in scenario_model["phases"]
                        )
                        for trajectory in simulation["runs"]:
                            self.assertEqual(len(trajectory["transitions"]), n)
                            self.assertEqual(len(trajectory["states"]), n + 1)
                            self.assertEqual(
                                trajectory["total_cost"],
                                trajectory["states"][-1]["cumulative_cost"],
                            )
                            self.assertTrue(
                                all(t["cost"] >= 0 for t in trajectory["transitions"])
                            )
                            self.assertTrue(
                                all(
                                    0 <= v <= 1
                                    for state in trajectory["states"]
                                    for v in state["metrics"].values()
                                )
                            )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["runtime"]["provenance"])
                    self.assertTrue(result["replay_artifacts"])
                    # Complete, draft, blocked all exhaust phases and return successful exit.
                    for status in ["complete", "draft", "blocked"]:
                        m = model()
                        m["acceptance_thresholds"] = {
                            "complete": (
                                {}
                                if status == "complete"
                                else {"lean_executability": 1}
                            ),
                            "draft": (
                                {} if status == "draft" else {"lean_executability": 1}
                            ),
                        }
                        result = await run(m, {"runs": 1, "scenarios": ["baseline"]})
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertEqual(
                            result["outputs"]["manifest"]["scenarios"][0][
                                "status_probabilities"
                            ][status],
                            1,
                        )
                        trajectory = json.loads(
                            (out / "baseline/simulated_trajectories.json").read_text()
                        )["runs"][0]
                        self.assertEqual(len(trajectory["transitions"]), 5)
                        self.assertEqual(len(result["calls"]), 5)
                    # Native fallback thresholds, empty phase ranges, default 128 runs and seed 17.
                    m = model()
                    m["phases"][1]["duration_steps"] = 0
                    m["phases"][3]["duration_steps"] = -1
                    m["gate_thresholds"] = m.pop("acceptance_thresholds")
                    result = await run(m, {"scenarios": ["baseline"]})
                    self.assertEqual(result["status"], "accepted", result)
                    simulation = json.loads(
                        (out / "baseline/simulated_trajectories.json").read_text()
                    )
                    self.assertEqual(len(simulation["runs"]), 128)
                    self.assertEqual(
                        [r["seed"] for r in simulation["runs"]],
                        [17 + i * 1009 for i in range(128)],
                    )
                    self.assertTrue(
                        all(len(r["transitions"]) == 2 for r in simulation["runs"])
                    )
                    # Inner ranges are source-owned, beyond neighboring simulator contract caps.
                    m = model()
                    m["phases"] = m["phases"][1:2]
                    m["phases"][0]["duration_steps"] = 257
                    m["acceptance_thresholds"] = {"complete": {}, "draft": {}}
                    result = await run(m, {"runs": 1, "scenarios": ["baseline"]})
                    self.assertEqual(result["status"], "accepted", result)
                    trajectory = json.loads(
                        (out / "baseline/simulated_trajectories.json").read_text()
                    )["runs"][0]
                    self.assertEqual(len(trajectory["transitions"]), 257)
                    self.assertEqual(trajectory["status"], "complete")
                    self.assertGreater(trajectory["total_cost"], 0)
                    self.assertTrue(
                        any(
                            delta["relative_down"] > 0
                            for t in trajectory["transitions"]
                            for delta in t["delta"].values()
                        )
                    )
                    m["phases"] = []
                    result = await run(m, {"runs": 129, "scenarios": ["baseline"]})
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(
                        len(
                            json.loads(
                                (
                                    out / "baseline/simulated_trajectories.json"
                                ).read_text()
                            )["runs"]
                        ),
                        129,
                    )
                    # Duplicate selection is ordered; second run replaces the same scenario artifacts.
                    result = await run(
                        model(), {"runs": 1, "scenarios": ["baseline", "baseline"]}
                    )
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(
                        [s["id"] for s in result["outputs"]["manifest"]["scenarios"]],
                        ["baseline", "baseline"],
                    )
                    self.assertEqual(
                        json.loads(
                            (out / "baseline/simulated_trajectories.json").read_text()
                        )["seed"],
                        17 + 8191,
                    )
                    # Native summary and threshold errors propagate once without terminal artifacts.
                    for count in [0, -1]:
                        shutil.rmtree(out)
                        result = await run(
                            model(), {"runs": count, "scenarios": ["baseline"]}
                        )
                        self.assertEqual(result["status"], "failed", result)
                        self.assertEqual(len(result["calls"]), 3)
                        self.assertTrue((out / "baseline/model.json").exists())
                        self.assertFalse(
                            (out / "baseline/simulated_trajectories.json").exists()
                        )
                        self.assertFalse(
                            (out / "simulation_suite_manifest.json").exists()
                        )
                    m = model()
                    del m["acceptance_thresholds"]
                    result = await run(m, {"runs": 1, "scenarios": ["baseline"]})
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(len(result["calls"]), 3)
                    m = model()
                    m["phases"] = []
                    result = await run(m, {"runs": 1, "scenarios": ["baseline"]})
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(
                        json.loads(
                            (out / "baseline/simulated_trajectories.json").read_text()
                        )["runs"][0]["transitions"],
                        [],
                    )
                    # Actual PRISM exhaustion and operation-call budget paths.
                    bounded = deepcopy(d)
                    bounded["flow"]["steps"][1]["max_iterations"] = 1
                    result = await run(
                        model(),
                        {"runs": 1, "scenarios": ["baseline", "noisy_plateau"]},
                        bounded,
                    )
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(result["failure_disposition"], "fail")
                    self.assertEqual(len(result["calls"]), 4)
                    budget = deepcopy(d)
                    budget["policy"]["limits"]["max_operation_calls"] = 2
                    result = await run(
                        model(), {"runs": 1, "scenarios": ["baseline"]}, budget
                    )
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIn("budget", str(result).lower())
                    self.assertEqual(
                        sum(
                            bool(c.get("transport_call_performed"))
                            for c in result["calls"]
                        ),
                        2,
                    )
                    # Late write failure retains earlier outputs, prevents manifest/terminal success.
                    shutil.rmtree(out)
                    (out / "scenario_status_probabilities.svg").mkdir(parents=True)
                    result = await run(model(), {"runs": 1, "scenarios": ["baseline"]})
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(len(result["calls"]), 5)
                    self.assertTrue((out / "scenario_metric_comparison.svg").is_file())
                    self.assertFalse((out / "scenario_summary.csv").exists())
                    self.assertFalse((out / "simulation_suite_manifest.json").exists())
                    # Native load/mkdir failure and actual aggregate write-root guard.
                    path.write_text("{invalid")
                    with self.assertRaises(Exception):
                        await remote.call(
                            "mathformer_theory_suite_initialize",
                            {
                                "options": {"model": str(path), "output_dir": str(out)},
                                "context": {"working_directory": str(directory)},
                            },
                        )
                    escape = directory.parent / (directory.name + "-escape")
                    result = await run(model(), {"output_dir": str(escape), "runs": 1})
                    self.assertEqual(result["status"], "failed", result)
                    self.assertFalse(escape.exists())
                    blocker = directory / "blocker"
                    blocker.write_text("fixture")
                    result = await run(
                        model(), {"output_dir": str(blocker / "out"), "runs": 1}
                    )
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(len(result["calls"]), 1)
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
                        "mathformer_theory_suite_initialize",
                        {
                            "options": {
                                "model": str(path),
                                "output_dir": str(directory / "denied"),
                            },
                            "context": {"working_directory": str(directory)},
                        },
                    )
                self.assertFalse((directory / "denied").exists())
        self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
