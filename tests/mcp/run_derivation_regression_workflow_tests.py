#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402
"""Native oracle, real checker children, MCP, and Lunar/PRISM execution tests.

Only temporary source fixtures are executed. The static checker has no external
model/provider/compiler boundary, so no production algorithm is substituted.
"""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != python.parent.parent.resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.path[:0] = [
    str(ROOT / "scripts"),
    str(ROOT / "tests/mcp/fixtures"),
    str(LUNAR / "app/backend"),
]

import asyncio
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
import tempfile
import unittest
import yaml

from derivation_regression_tools import create_server
from derivation_regression_mount import (
    ROOT as FIXTURE_ROOT,
    RUNNER,
    CHECKER,
    REPORT,
    load,
    stage,
    configure,
)
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute
from mcp_connections.workflow_contract.validator import validate

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_physics_lean_derivation_completeness_regression_workflow/workflow.yaml"
AUTHORED = (
    ROOT
    / "skills/control/workflow-contract-validator/references/derivation-regression.workflow.json"
)
ORIGINAL = ROOT / "tests/mcp/fixtures/derivation_regression_original.py.txt"
ORDER = (
    ["self_test"]
    + ["fixture"] * 4
    + ["formal_case"] * 5
    + ["assertions", "persist", "emit_return"]
)


def assets(document):
    def asset(path, content):
        return {
            "path": path,
            "content": content,
            "encoding": "text",
            "sha256": hashlib.sha256(content.encode()).hexdigest(),
        }

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(row["path"], (ROOT / row["path"]).read_text())
        for row in document["provenance"]["sources"]
    ]


def cli(module, json_output):
    with redirect_stdout(io.StringIO()) as output:
        code = module.main(["--json"] if json_output else [])
    return code, output.getvalue()


class DerivationRegressionTests(unittest.TestCase):
    def test_original_equivalence_and_failure_collection(self):
        self.assertEqual(ROOT, FIXTURE_ROOT)
        for mode in (
            "success",
            "assertion_failure",
            "missing_input",
            "malformed_record",
            "write_failure",
        ):
            for json_output in (False, True):
                with (
                    self.subTest(mode=mode, json_output=json_output),
                    tempfile.TemporaryDirectory() as directory,
                ):
                    root = Path(directory)
                    stage(root, mode)
                    original = load(ORIGINAL, "derivation_oracle")
                    expected_calls = configure(original, root)
                    native = load(ROOT / RUNNER, "derivation_adapted")
                    actual_calls = configure(native, root)
                    if mode in ("missing_input", "malformed_record", "write_failure"):
                        error = (
                            IsADirectoryError
                            if mode == "write_failure"
                            else RuntimeError
                        )
                        with self.assertRaises(error):
                            cli(original, json_output)
                        with self.assertRaises(error):
                            cli(native, json_output)
                        self.assertEqual(
                            len(actual_calls),
                            {
                                "missing_input": 2,
                                "malformed_record": 6,
                                "write_failure": 10,
                            }[mode],
                        )
                        if mode != "write_failure":
                            self.assertFalse((root / REPORT).exists())
                    else:
                        expected = cli(original, json_output)
                        expected_bytes = (root / REPORT).read_bytes()
                        actual = cli(native, json_output)
                        self.assertEqual(actual, expected)
                        self.assertEqual((root / REPORT).read_bytes(), expected_bytes)
                        report = json.loads(expected_bytes)
                        self.assertEqual(len(report["checks"]), 11)
                        self.assertEqual(report["ok"], mode == "success")
                        self.assertEqual(actual[0], 0 if report["ok"] else 1)
                        self.assertEqual(len(actual_calls), 10)
                        checks = {check["id"]: check for check in report["checks"]}
                        if mode == "success":
                            self.assertTrue(
                                all(check["ok"] for check in checks.values())
                            )
                            detail = checks[
                                "formalphysics_0014_obligations_and_probes"
                            ]["detail"]
                            self.assertEqual(
                                detail["commutator_status"],
                                "proved_from_commutator_expectation",
                            )
                            self.assertEqual(detail["probe_count"], 4)
                            self.assertEqual(detail["repair_frontier_count"], 0)
                            self.assertEqual(detail["recursive_frontier_count"], 0)
                            self.assertIn(
                                "compiled_surface",
                                checks["compiled_surface_flag_preserved_when_blocked"][
                                    "detail"
                                ]["flags"],
                            )
                            self.assertEqual(
                                checks[
                                    "formalphysics_0052_position_expectation_complete"
                                ]["detail"]["measure_status"],
                                "mathlib_reused",
                            )
                        else:
                            self.assertTrue(checks["self_test_passes"]["ok"])
                            self.assertFalse(
                                checks["legitimate_source_law_witness_passes"]["ok"]
                            )
                            self.assertFalse(
                                checks["formalphysics_0074_chained_bridge_complete"][
                                    "ok"
                                ]
                            )
                            self.assertTrue(
                                checks[
                                    "formalphysics_0052_position_expectation_complete"
                                ]["ok"]
                            )
                        if json_output:
                            self.assertEqual(json.loads(actual[1]), report)
                        else:
                            self.assertEqual(
                                actual[1],
                                ("PASS" if report["ok"] else "FAIL")
                                + " derivation completeness regression\n",
                            )
                        self.assertEqual(expected_bytes[-1:], b"\n")
                    self.assertEqual(actual_calls, expected_calls)

    def test_real_checker_branches_and_helper_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stage(root)
            native = load(ROOT / RUNNER, "derivation_branch_tests")
            configure(native, root)
            # Target-restatement findings take priority over an open frontier.
            blocked = native.run_fixture("direct_target_hypothesis", 1)
            self.assertEqual(blocked["status"], "blocked_target_restating_assumption")
            self.assertFalse(blocked["ok"])
            complete = native.run_fixture("source_law_witness_not_target", None)
            self.assertEqual(complete["status"], "complete_autoformalization")
            partial = native.run_fixture("source_law_witness_not_target", 1)
            self.assertEqual(partial["status"], "derivation_partial")
            self.assertIn("compiled_surface", partial["artifacts"][0]["status_flags"])
            self.assertEqual(partial["artifacts"][0]["recursive_frontier_count"], 1)
            # Preserve the helper's recursive-plan path, although this graph uses 0.
            plan = (
                root
                / "artifacts/physics_lean/dirac_recursive_batch/recursive_grounding_plan.json"
            )
            plan.write_text('{"recursive_frontier": [{"id": "remaining"}]}')
            recursive = native.run_formalphysics_case("formalphysics_0014")
            self.assertEqual(recursive["status"], "derivation_partial")
            self.assertEqual(
                native.run_formalphysics_case(
                    "formalphysics_0014", recursive_frontier_count=0
                )["status"],
                "complete_autoformalization",
            )
            # A missing mathematical obligation also blocks without child exit failure.
            lean = (
                root
                / "libraries/MathformerPhysicsLib/Lean/formalphysics_0015/MathformerPhysics.lean"
            )
            lean.write_text("import Mathlib\n")
            missing = native.run_formalphysics_case(
                "formalphysics_0015", recursive_frontier_count=0
            )
            self.assertEqual(missing["status"], "derivation_partial")
            self.assertGreater(missing["artifacts"][0]["blocked_obligation_count"], 0)
            # Exercise run_json's actual parse/process failures with fixed Python commands.
            import subprocess

            native.subprocess = subprocess
            with self.assertRaises(json.JSONDecodeError):
                native.run_json(["-c", "print('malformed JSON')"])
            with self.assertRaisesRegex(RuntimeError, "STDERR:\\nchild diagnostic"):
                native.run_json(
                    [
                        "-c",
                        "import sys; print('child diagnostic', file=sys.stderr); sys.exit(7)",
                    ]
                )

    def test_registration_policy_and_generator(self):
        async def denied():
            server = create_server(readonly=True)
            for name, args in (("self_test", {}), ("persist", {"report": {}})):
                with self.assertRaisesRegex(Exception, "read-only policy"):
                    await server.call_tool("mathformer_derivation_" + name, args)

        asyncio.run(denied())
        from mathformer_mcp_service import service_coverage_report

        tools = service_coverage_report(ROOT / "unused-config", {})["mcp_tools"]
        for operation in set(ORDER):
            self.assertIn("mathformer_derivation_" + operation, tools)
        self.assertIn(
            "register_derivation_regression_tools(mcp, _analysis_write_policy)",
            (ROOT / "scripts/mcp_server.py").read_text(),
        )
        generator = load(
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
            "derivation_generator",
        )
        projected = [
            d
            for d in generator.inventory()
            if d["id"] == "hub_physics_lean_derivation_completeness_regression_workflow"
        ]
        self.assertEqual(projected, [json.loads(AUTHORED.read_text())])

    def test_lunar_mcp_prism(self):
        asyncio.run(self.scenarios())

    async def scenarios(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document, json.loads(AUTHORED.read_text()))
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["id"],
            "hub_physics_lean_derivation_completeness_regression_workflow",
        )
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
        for mode, json_output in (
            ("success", True),
            ("success", False),
            ("assertion_failure", False),
            ("missing_input", True),
            ("malformed_record", True),
            ("write_failure", True),
        ):
            with (
                self.subTest(mode=mode, json_output=json_output),
                tempfile.TemporaryDirectory() as directory,
            ):
                root = Path(directory)
                stage(root, mode)
                original = load(ORIGINAL, "lunar_derivation_oracle")
                expected_calls = configure(original, root)
                try:
                    expected_code, expected_stdout = cli(original, json_output)
                    expected_bytes = (root / REPORT).read_bytes()
                    (root / REPORT).unlink()
                except (RuntimeError, OSError):
                    expected_code, expected_stdout, expected_bytes = None, None, None
                manager = SessionManager()
                async with manager.open(
                    "derivation",
                    StdioConfig(
                        command=sys.executable,
                        args=[
                            "tests/mcp/fixtures/derivation_regression_server.py",
                            str(root),
                        ],
                        cwd=str(ROOT),
                    ),
                    {},
                ) as remote:
                    inventory = [
                        tool.model_dump(by_alias=True, exclude_none=True)
                        for tool in await remote.tools()
                    ]

                    def compile(doc, tools=None):
                        received = assets(doc)
                        workflow = compile_workflow(
                            "mcp:derivation",
                            workflow_documents([DESCRIPTOR], received)[0],
                            inventory if tools is None else tools,
                        )
                        return workflow, received

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
                        return await execute(
                            w, a, {"json_output": json_output}, remote, allow
                        )

                    result = await run()
                    ledger = (await remote.call("fixture_ledger", {"clear": True}))[
                        "calls"
                    ]
                    self.assertEqual(ledger, expected_calls)
                    if expected_bytes is None:
                        self.assertEqual(result["status"], "failed", result)
                        self.assertIsNone(result["outputs"])
                        failed = {
                            "missing_input": "fixture",
                            "malformed_record": "formal_case",
                            "write_failure": "persist",
                        }[mode]
                        self.assertEqual(
                            result["calls"][-1]["tool"],
                            "mathformer_derivation_" + failed,
                        )
                        self.assertEqual(result["calls"][-1]["status"], "rejected")
                        if mode != "write_failure":
                            self.assertFalse((root / REPORT).exists())
                        continue
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(
                        result["outputs"],
                        {
                            "report": json.loads(expected_bytes),
                            "report_path": REPORT,
                            "exit_code": expected_code,
                            "stdout": expected_stdout,
                        },
                    )
                    self.assertEqual((root / REPORT).read_bytes(), expected_bytes)
                    self.assertEqual(
                        [c["tool"] for c in result["calls"]],
                        ["mathformer_derivation_" + n for n in ORDER],
                    )
                    self.assertEqual(len(result["calls"]), 13)
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["replay_artifacts"])
                    # Exact native arguments; no plans, timeout, retries, or repair loop.
                    self.assertEqual(ledger[0], [CHECKER, "--self-test", "--json"])
                    self.assertEqual(
                        ledger[4][-3:], ["--recursive-frontier-count", "1", "--json"]
                    )
                    for call in ledger[5:]:
                        self.assertEqual(
                            call[-3:], ["--recursive-frontier-count", "0", "--json"]
                        )
                        self.assertIn("--source-record", call)
                        self.assertNotIn("--recursive-plan", call)
                    if mode != "success" or not json_output:
                        continue
                    # Host budget cuts are additional bounds; source has no loop/exhaustion.
                    for budget in (1, 10, 11, 12):
                        (root / REPORT).unlink(missing_ok=True)
                        bounded = deepcopy(document)
                        bounded["policy"]["limits"]["max_operation_calls"] = budget
                        limited = await run(bounded)
                        self.assertEqual(limited["status"], "failed", limited)
                        self.assertIsNone(limited["outputs"])
                        self.assertEqual(
                            sum(
                                bool(c.get("transport_call_performed"))
                                for c in limited["calls"]
                            ),
                            budget,
                        )
                        self.assertIn(
                            "budget", json.dumps(limited["calls"][-1]).lower()
                        )
                        calls = (await remote.call("fixture_ledger", {"clear": True}))[
                            "calls"
                        ]
                        self.assertEqual(calls, expected_calls[: min(budget, 10)])
                        self.assertEqual((root / REPORT).is_file(), budget == 12)
                self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
