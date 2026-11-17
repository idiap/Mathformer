#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402 - explicit test runtime and module path setup
"""Runnable native/MCP/Lunar/PRISM equivalence and stopping regressions."""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != python.parent.parent.resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.path[:0] = [
    str(ROOT),
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT / "tests/mcp/fixtures"),
]
import asyncio
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
import tempfile
import unittest
from unittest.mock import patch
import yaml
from physics_backend_suite_tools import source, create_server
from backend_suite_boundary import load, stage, install
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute
from mcp_connections.workflow_contract.validator import validate

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_physics_lean_backend_suite_workflow/workflow.yaml"
NATIVE = ROOT / "tests/physics_lean/run_lean_physics_backend_suite.py"
ORIGINAL = ROOT / "tests/mcp/fixtures/backend_suite_original.py.txt"


def assets(document):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(row["path"], (ROOT / row["path"]).read_text())
        for row in document["provenance"]["sources"]
    ]


class BackendSuiteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        source.cache_clear()
        self.addCleanup(source.cache_clear)

    def original(self, mode="success"):
        native = load(ORIGINAL, "backend_original")
        calls = install(native, self.directory, mode)
        return native, calls

    def test_shared_entrypoint_equivalence_and_cli(self):
        for mode in ("success", "compile_failure", "boolean_failure"):
            with self.subTest(mode=mode):
                stage(self.directory, mode)
                original, expected_calls = self.original(mode)
                expected = original.run_suite()
                snapshots = {
                    p.relative_to(self.directory): p.read_bytes()
                    for p in (self.directory / "artifacts").rglob("*.json")
                }
                native = load(NATIVE, "backend_adapted")
                calls = install(native, self.directory, mode)
                actual = native.run_suite()
                self.assertEqual(actual, expected)
                self.assertEqual(calls, expected_calls)
                for path, content in snapshots.items():
                    self.assertEqual(
                        (self.directory / path).read_bytes(), content, str(path)
                    )
                self.assertEqual(actual["ok"], mode == "success")
                self.assertFalse(actual["release_ok"])
                self.assertEqual(actual["artifact_status"], "candidate")
                self.assertEqual(len(actual["adversarial"]["cases"]), 5)
                self.assertEqual(
                    actual["controlled_artifact"]["fresh_compile"]["source_sha256"],
                    hashlib.sha256(native.CONTROLLED_LEAN.read_bytes()).hexdigest(),
                )
                # main keeps native exit and printed report semantics.
                with (
                    patch.object(sys, "argv", ["suite", "--json"]),
                    redirect_stdout(io.StringIO()) as out,
                ):
                    self.assertEqual(native.main(), 0 if mode == "success" else 1)
                self.assertEqual(json.loads(out.getvalue()), expected)
        # Native parse/load errors, process errors and compiler exceptions abort.
        for mode, error in (
            ("bad_json", json.JSONDecodeError),
            ("child_failure", RuntimeError),
            ("compiler_exception", OSError),
            ("regression_failure", RuntimeError),
            ("thoroughness_failure", RuntimeError),
        ):
            stage(self.directory, mode)
            original, original_calls = self.original(mode)
            with self.assertRaises(error):
                original.run_suite()
            native = load(NATIVE, "backend_adapted")
            calls = install(native, self.directory, mode)
            with self.assertRaises(error):
                native.run_suite()
            self.assertEqual(calls, original_calls)

    def test_registration_policy(self):
        # Read-only policy must reject before even reading stored reports.
        async def check():
            await create_server(readonly=True).call_tool(
                "mathformer_physics_backend_prepare_controlled", {}
            )

        with self.assertRaisesRegex(Exception, "read-only policy"):
            asyncio.run(check())
        from mathformer_mcp_service import service_coverage_report

        coverage = service_coverage_report(ROOT / "unused-fixture-config", {})
        expected = [
            "mathformer_physics_backend_" + name
            for name in (
                "prepare_controlled",
                "collect_plan",
                "begin_arguments",
                "append_argument",
                "finish_controlled",
                "begin_adversarial",
                "check_fixture",
                "derivation_regression",
                "thoroughness_regression",
                "write_suite",
            )
        ]
        self.assertTrue(set(expected).issubset(coverage["mcp_tools"]))
        server = (ROOT / "scripts/mcp_server.py").read_text()
        self.assertIn(
            "register_physics_backend_suite_tools(mcp, _analysis_write_policy)", server
        )

    def test_native_recursion_stopping_rules(self):
        path = (
            ROOT
            / "skills/physics-lean/physics-lean-recursive-repair-loop-controller/scripts/control_recursive_repair_loop.py"
        )
        native = load(path, "backend_recursion")
        expansion = {
            "status": "needs_expansion",
            "exhaustive": True,
            "iteration_signature": "same",
            "outstanding_nodes": [{"id": "library-object"}],
            "next_frontier": [{"node_id": "library-object", "action": "work_object"}],
        }

        def run(e=None, history=None, iteration=1):
            return native.build_control_plan(
                expansion_map=e or expansion,
                previous_expansion_maps=history or [],
                iteration=iteration,
                max_iterations=6,
            )

        self.assertEqual(run()["status"], "recurse")
        self.assertEqual(run(iteration=5)["status"], "recurse")
        self.assertEqual(run(iteration=6)["blockers"], ["max_iterations_reached:6"])
        self.assertEqual(
            run(history=[expansion])["blockers"], ["repeated_iteration_signature:same"]
        )
        self.assertEqual(
            run({**expansion, "exhaustive": False})["blockers"],
            ["expansion_map_not_exhaustive"],
        )
        self.assertEqual(
            run({**expansion, "status": "blocked"})["blockers"],
            ["expansion_map_blocked"],
        )
        done = run(
            {**expansion, "status": "complete", "outstanding_nodes": []}, [expansion], 6
        )
        self.assertEqual(done["status"], "complete")
        self.assertEqual(done["next_actions"], [])
        self.assertEqual(
            run({**expansion, "outstanding_nodes": []})["status"], "complete"
        )

    def test_lunar_registered_workflow(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        contract_path = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
        document = yaml.safe_load(contract_path.read_text())
        self.assertEqual(document["id"], "hub_physics_lean_backend_suite_workflow")
        self.assertEqual(document["lifecycle"], "active")
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", dir=ROOT
        ) as supplied:
            json.dump(document, supplied)
            supplied.flush()
            checked = validate(Path(supplied.name), ROOT, True)
        self.assertTrue(checked["valid"], checked)
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        for mode in (
            "success",
            "compile_failure",
            "boolean_failure",
            "compiler_exception",
            "bad_json",
            "child_failure",
            "regression_failure",
            "thoroughness_failure",
        ):
            stage(self.directory, mode)
            original, expected_calls = self.original(mode)
            try:
                expected = original.run_suite()
            except (RuntimeError, OSError, ValueError):
                expected = None
            manager = SessionManager()
            failure = None
            async with manager.open(
                "backend",
                StdioConfig(
                    command=sys.executable,
                    args=[
                        "tests/mcp/fixtures/backend_suite_server.py",
                        str(self.directory),
                        mode,
                    ],
                    cwd=str(ROOT),
                ),
                {},
            ) as remote:
                try:
                    inventory = [
                        tool.model_dump(by_alias=True, exclude_none=True)
                        for tool in await remote.tools()
                    ]

                    def compile(doc, tools=None):
                        received = assets(doc)
                        w = compile_workflow(
                            "mcp:backend",
                            workflow_documents([DESCRIPTOR], received)[0],
                            inventory if tools is None else tools,
                        )
                        return w, received

                    workflow, received = compile(document)
                    self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                    self.assertTrue(workflow["runtime_source"])
                    self.assertEqual(
                        set(workflow["bindings"]), set(document["operations"])
                    )
                    self.assertFalse(compile(document, [])[0]["runnable"])

                    async def allow():
                        pass

                    async def run(doc=None):
                        w, a = compile(doc) if doc else (workflow, received)
                        return await execute(w, a, {}, remote, allow)

                    result = await run()
                    self.assertEqual(
                        (await remote.call("fixture_ledger", {}))["calls"],
                        expected_calls,
                    )
                    if expected is None:
                        self.assertEqual(result["status"], "failed", result)
                        self.assertIsNone(result["outputs"])
                        self.assertEqual(result["calls"][-1]["status"], "rejected")
                        failed_step = {
                            "compiler_exception": "prepare_controlled",
                            "bad_json": "prepare_controlled",
                            "child_failure": "check_fixture",
                            "regression_failure": "derivation_regression",
                            "thoroughness_failure": "thoroughness_regression",
                        }[mode]
                        self.assertEqual(
                            result["calls"][-1]["tool"],
                            "mathformer_physics_backend_" + failed_step,
                        )
                        continue
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(result["outputs"]["report"], expected)
                    self.assertEqual(result["outputs"]["ok"], expected["ok"])
                    self.assertFalse(result["outputs"]["release_ok"])
                    self.assertEqual(
                        json.loads(
                            (
                                self.directory
                                / "artifacts/physics_lean/backend_suite/lean_physics_backend_suite_report.json"
                            ).read_text()
                        ),
                        expected,
                    )
                    expected_tools = (
                        ["prepare_controlled"]
                        + ["collect_plan"] * 4
                        + ["begin_arguments"]
                        + ["append_argument"] * 4
                        + ["finish_controlled", "begin_adversarial"]
                        + ["check_fixture"] * 5
                        + [
                            "derivation_regression",
                            "thoroughness_regression",
                            "write_suite",
                        ]
                    )
                    self.assertEqual(
                        [c["tool"] for c in result["calls"]],
                        ["mathformer_physics_backend_" + n for n in expected_tools],
                    )
                    self.assertEqual(len(result["calls"]), 20)
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["replay_artifacts"])
                    if mode != "success":
                        continue
                    # Exercise real registered state ports, guards and fixed final transitions.
                    prepared = await remote.call(
                        "mathformer_physics_backend_prepare_controlled", {}
                    )
                    plans = prepared["state"]
                    self.assertEqual(
                        plans, {"cursor": 0, "repair_reports": {}, "repair_paths": []}
                    )
                    labels = [
                        "notational_collapse",
                        "abstraction_elevation",
                        "proof_strategy",
                        "implicit_premise",
                    ]
                    for cursor, label in enumerate(labels, 1):
                        old = deepcopy(plans)
                        advanced = await remote.call(
                            "mathformer_physics_backend_collect_plan",
                            {"evidence": prepared["evidence"], "state": plans},
                        )
                        plans = advanced["state"]
                        self.assertEqual(old["cursor"], cursor - 1)
                        self.assertEqual(plans["cursor"], cursor)
                        self.assertEqual(list(plans["repair_reports"]), labels[:cursor])
                        self.assertTrue(
                            plans["repair_paths"][-1].endswith(
                                label + "_repair_plan.json"
                            )
                        )
                        self.assertEqual(advanced["done"], cursor == 4)
                    args = (
                        await remote.call(
                            "mathformer_physics_backend_begin_arguments",
                            {"plans": plans},
                        )
                    )["state"]
                    for cursor in range(1, 5):
                        advanced = await remote.call(
                            "mathformer_physics_backend_append_argument",
                            {"plans": plans, "state": args},
                        )
                        args = advanced["state"]
                        self.assertEqual(
                            args["repair_args"],
                            [
                                v
                                for path in plans["repair_paths"][:cursor]
                                for v in ("--repair-plan", path)
                            ],
                        )
                        self.assertEqual(advanced["done"], cursor == 4)
                    fixtures = (
                        await remote.call(
                            "mathformer_physics_backend_begin_adversarial", {}
                        )
                    )["state"]
                    for cursor in range(1, 6):
                        advanced = await remote.call(
                            "mathformer_physics_backend_check_fixture",
                            {"state": fixtures},
                        )
                        fixtures = advanced["state"]
                        self.assertEqual(fixtures["cursor"], cursor)
                        self.assertEqual(len(fixtures["results"]), cursor)
                        self.assertEqual(advanced["done"], cursor == 5)
                    # Source recursion is advisory and called once with no histories.
                    calls = (await remote.call("fixture_ledger", {}))["calls"]
                    recursion = [
                        c
                        for c in calls
                        if "control_recursive_repair_loop.py" in " ".join(c)
                    ]
                    self.assertEqual(len(recursion), 1)
                    self.assertEqual(
                        recursion[0][-6:],
                        [
                            "--iteration",
                            "1",
                            "--max-iterations",
                            "6",
                            "--output",
                            "artifacts/physics_lean/backend_suite/controlled_artifact/formalphysics_0000/recursive_repair_control.json",
                        ],
                    )
                    recursive = json.loads(
                        (self.directory / recursion[0][-1]).read_text()
                    )
                    self.assertEqual(recursive["prior_iteration_signatures"], [])
                    self.assertIn(
                        recursive["status"], ("recurse", "complete", "blocked")
                    )
                    # Real parser/checker/compiler/runtime must enforce all three bounds.
                    for index, limit, call_count in ((1, 3, 4), (3, 3, 9), (6, 4, 16)):
                        bounded = deepcopy(document)
                        bounded["flow"]["steps"][index]["max_iterations"] = limit
                        exhausted = await run(bounded)
                        self.assertEqual(exhausted["status"], "failed", exhausted)
                        self.assertEqual(exhausted["failure_disposition"], "fail")
                        self.assertIsNone(exhausted["outputs"])
                        self.assertEqual(len(exhausted["calls"]), call_count)
                    budget = deepcopy(document)
                    budget["policy"]["limits"]["max_operation_calls"] = 1
                    limited = await run(budget)
                    self.assertEqual(limited["status"], "failed")
                    self.assertEqual(
                        sum(
                            bool(c.get("transport_call_performed"))
                            for c in limited["calls"]
                        ),
                        1,
                    )
                except Exception as exc:
                    failure = exc
            self.assertFalse(manager.active)
            if failure:
                raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
