#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Real source, registered MCP and Lunar PRISM with deterministic file fixtures.

No external provider/compiler is used by this workflow. Lean files are inventory
inputs, never compiled. PRISM parsing/checking/compilation/execution stays real.
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
from copy import deepcopy
from contextlib import redirect_stdout
import io
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import json
import tempfile
import unittest
import yaml
from coherence_loop_tools import source
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_mathformerphysicslib_coherence_loop_report_workflow/workflow.yaml"


def assets(document):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(s["path"], (ROOT / s["path"]).read_text())
        for s in document["provenance"]["sources"]
    ]


def fixture(root):
    lean = root / "MathformerPhysicsLib/Lean"
    lean.mkdir(parents=True)
    (lean / "formalphysics_vector.lean").write_text(
        "import Mathlib\ndef vector : Nat := 1\n"
    )
    (lean / "Other.lean").write_text("import Mathlib\ndef vector : Nat := 2\n")
    return lean


class CoherenceLoopTests(unittest.TestCase):
    def test_original_equivalence_and_source_branches(self):
        native = source()
        loader = SourceFileLoader(
            "coherence_loop_original",
            str(ROOT / "tests/mcp/fixtures/coherence_loop_original.py.txt"),
        )
        spec = importlib.util.spec_from_loader(loader.name, loader)
        original = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(original)
        import coherence_common as common

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            fixture(root)
            # Supply filesystem context only; no native stage is substituted.
            names = ["REPO_ROOT", "LIB_ROOT", "LEAN_ROOT", "FOUNDATIONS_INDEX"]
            saved = [getattr(common, n) for n in names]
            values = [
                root,
                root / "MathformerPhysicsLib",
                root / "MathformerPhysicsLib/Lean",
                root / "MathformerPhysicsLib/Lean/Foundations.lean",
            ]
            original.REPO_ROOT = root
            native_root = native.REPO_ROOT
            native.REPO_ROOT = root
            for n, v in zip(names, values):
                setattr(common, n, v)
            output = root / "out"
            try:
                for prior in [
                    None,
                    "{",
                    "[]",
                    "{}",
                    json.dumps(
                        {
                            "concepts": [
                                {
                                    "concept_id": "vector_field.real.euclidean3",
                                    "grounding_level": "direct_mathlib",
                                }
                            ]
                        }
                    ),
                ]:

                    def reset():
                        output.mkdir(exist_ok=True)
                        path = output / "mathlib_grounding.json"
                        if prior is None:
                            path.unlink(missing_ok=True)
                        else:
                            path.write_text(prior)

                    reset()
                    before = original.run_loop(output)
                    content = {p.name: p.read_bytes() for p in output.iterdir()}
                    reset()
                    after = native.run_loop(output, root)
                    self.assertEqual(before, after)
                    self.assertEqual(
                        content, {p.name: p.read_bytes() for p in output.iterdir()}
                    )
                    self.assertTrue(after["ok"])
                    self.assertEqual(after["gate_status"], "blocked")
                    self.assertEqual(len(after["checks"]), 6)
                    self.assertEqual(after["generative_probe_count"], 7)
                    self.assertEqual(len(content), 10)
                for empty in [False, True]:
                    if empty:
                        for p in (root / "MathformerPhysicsLib/Lean").iterdir():
                            p.unlink()
                    emissions = []
                    for main in [original.main, native.main]:
                        (output / "mathlib_grounding.json").unlink(missing_ok=True)
                        stream = io.StringIO()
                        with redirect_stdout(stream):
                            code = main(["--json", "--output-dir", str(output)])
                        self.assertEqual(code, 1 if empty else 0)
                        emissions.append(stream.getvalue())
                    self.assertEqual(*emissions)
            finally:
                native.REPO_ROOT = native_root
                for n, v in zip(names, saved):
                    setattr(common, n, v)
        levels = [
            "unverified_local",
            "local_blocker",
            "mathlib_bridge",
            "direct_mathlib",
            "unknown",
        ]
        prior = {
            "concepts": [
                {"concept_id": str(i), "grounding_level": level}
                for i, level in enumerate(levels)
            ]
        }
        current = {
            "concepts": [
                {"concept_id": str(i), "grounding_level": level}
                for i, level in enumerate(reversed(levels))
            ]
            + [{"concept_id": "new", "grounding_level": "local_blocker"}]
        }
        comparison = native.compare_grounding(prior, current)
        self.assertEqual(comparison["regression_count"], 2)
        self.assertEqual(comparison["improvement_count"], 2)
        self.assertFalse(comparison["ok"])
        self.assertEqual(native.compare_grounding(prior, prior)["status"], "monotonic")
        for findings, status in [
            ([], "accepted"),
            ([{"severity": "medium", "kind": "thin_foundation_api"}], "warn"),
            (
                [{"severity": "high", "kind": "confirmed_competing_concept_owner"}],
                "blocked",
            ),
        ]:
            plans = native.plan_and_gate([{"findings": findings}])
            self.assertEqual(plans["gate"]["status"], status)
            self.assertEqual(plans["generative"]["probe_count"], 7)
            self.assertEqual(plans["repairs"]["action_count"], len(findings))
        kinds = [
            "concept_spread_without_foundation_owner",
            "manifest_missing_foundations",
            "foundation_without_operable_api",
            "unknown",
        ]
        actions = native.plan_and_gate(
            [{"findings": [{"kind": k, "severity": "medium"} for k in kinds]}]
        )["repairs"]["actions"]
        self.assertEqual(
            [a["action"] for a in actions],
            [
                "consolidate_concept_owner",
                "repair_integration_surface",
                "add_operable_bridge_api",
                "record_or_block_gap",
            ],
        )

    def test_registered_mcp_lunar_prism(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(
            document["id"], "hub_mathformerphysicslib_coherence_loop_report_workflow"
        )
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document,
            json.loads(
                (
                    ROOT
                    / "skills/control/workflow-contract-validator/references/coherence-loop.workflow.json"
                ).read_text()
            ),
        )
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 9},
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            lean = fixture(root)
            output = root / "out"
            async with manager.open(
                "coherence-loop",
                StdioConfig(
                    command=str(ROOT / ".venv/bin/python"),
                    args=["-c", server],
                    cwd=str(ROOT),
                ),
                {},
            ) as remote:
                try:
                    tools = [
                        t.model_dump(by_alias=True, exclude_none=True)
                        for t in await remote.tools()
                    ]

                    def compile(d):
                        received = assets(d)
                        compiled = compile_workflow(
                            "mcp:coherence-loop",
                            workflow_documents([DESCRIPTOR], received)[0],
                            tools,
                        )
                        self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                        return compiled, received

                    async def allow():
                        pass

                    async def run(d=document, destination=output):
                        compiled, received = compile(d)
                        return await execute(
                            compiled,
                            received,
                            {
                                "output_dir": str(destination),
                                "repository_root": str(root),
                            },
                            remote,
                            allow,
                        )

                    for prior in [
                        None,
                        "{",
                        "[]",
                        "{}",
                        json.dumps(
                            {
                                "concepts": [
                                    {
                                        "concept_id": "vector_field.real.euclidean3",
                                        "grounding_level": "direct_mathlib",
                                    }
                                ]
                            }
                        ),
                    ]:
                        output.mkdir(exist_ok=True)
                        previous = output / "mathlib_grounding.json"
                        if prior is None:
                            previous.unlink(missing_ok=True)
                        else:
                            previous.write_text(prior)
                        result = await run()
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertEqual(len(result["calls"]), 9)
                        self.assertEqual(
                            [c["tool"] for c in result["calls"]],
                            [
                                "mathformer_coherence_loop_" + s["operation"]
                                for s in document["flow"]["steps"]
                            ],
                        )
                        self.assertTrue(result["outputs"]["result"]["ok"])
                        self.assertEqual(
                            result["outputs"]["result"]["gate_status"], "blocked"
                        )
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["replay_artifacts"])
                        written = {p.name: p.read_bytes() for p in output.iterdir()}
                        comparison = json.loads(previous.read_text())[
                            "monotonic_comparison"
                        ]
                        self.assertEqual(
                            comparison["status"],
                            (
                                "regressed"
                                if prior and "direct_mathlib" in prior
                                else "no_previous_report"
                            ),
                        )
                        if prior is None:
                            previous.unlink()
                        else:
                            previous.write_text(prior)
                        self.assertEqual(
                            result["outputs"],
                            {"result": source().run_loop(output, root)},
                        )
                        self.assertEqual(
                            written, {p.name: p.read_bytes() for p in output.iterdir()}
                        )
                    # Fresh artifact is the only cross-run state; no automatic repairs.
                    result = await run()
                    self.assertEqual(
                        json.loads((output / "mathlib_grounding.json").read_text())[
                            "monotonic_comparison"
                        ]["status"],
                        "monotonic",
                    )
                    self.assertEqual(len(result["calls"]), 9)
                    self.assertEqual(
                        sorted(p.name for p in lean.iterdir()),
                        ["Other.lean", "formalphysics_vector.lean"],
                    )
                    # Empty finite traversal returns a false runner ok as data.
                    for p in lean.iterdir():
                        p.unlink()
                    result = await run()
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertFalse(result["outputs"]["result"]["ok"])
                    self.assertEqual(result["outputs"]["result"]["module_count"], 0)
                    self.assertEqual(len(result["calls"]), 9)
                    # The descriptor budget stops before write; native source has no loop bound.
                    bounded = deepcopy(document)
                    bounded["policy"]["limits"]["max_operation_calls"] = 7
                    target = root / "bounded"
                    result = await run(bounded, target)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(
                        sum(
                            bool(c.get("transport_call_performed"))
                            for c in result["calls"]
                        ),
                        7,
                    )
                    self.assertIn("budget", result["calls"][-1]["error"])
                    self.assertEqual(list(target.iterdir()), [])
                    # Inventory I/O failure aborts before critics and writes, without retry.
                    (root / "MathformerPhysicsLib/MANIFEST.json").write_text("{")
                    result = await run()
                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(len(result["calls"]), 2)
                    self.assertEqual(result["calls"][-1]["status"], "rejected")
                    blocker = root / "blocker"
                    blocker.write_text("file")
                    result = await run(destination=blocker / "out")
                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(len(result["calls"]), 1)
                    # Write failure retains native partial artifacts: Markdown is first.
                    (root / "MathformerPhysicsLib/MANIFEST.json").unlink()
                    target = root / "partial"
                    target.mkdir()
                    (target / "inventory.json").mkdir()
                    result = await run(destination=target)
                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(len(result["calls"]), 8)
                    self.assertTrue((target / "coherence_report.md").exists())
                    self.assertFalse((target / "mathlib_grounding.json").exists())
                except BaseException as error:
                    failure = error
                else:
                    failure = None
            if failure is not None:
                raise failure
        self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
