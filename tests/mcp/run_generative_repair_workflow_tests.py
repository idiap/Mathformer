#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Differential native fixtures through registered MCP and real Lunar/PRISM.

The source constructs prompts only. External provider and compiler tripwires
prove that advisory acceptance requirements never turn into executed gates.
"""

from tempfile import gettempdir

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.path[:0] = [str(LUNAR / "app/backend"), str(ROOT / "scripts"), str(ROOT)]
sys.path.extend(str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages"))

import asyncio
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import subprocess
import urllib.request
import tempfile
import unittest
from unittest.mock import patch
import yaml
from mcp.server.fastmcp.exceptions import ToolError
from mcp_connections.client import MCPConnectionError
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute
import mcp_server
from generative_repair_tools import native

PREFIX = "mathformer_generative_repair_"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])


def asset(path, content):
    return {
        "path": path,
        "content": content,
        "encoding": "text",
        "sha256": hashlib.sha256(content.encode()).hexdigest(),
    }


class RegisteredRemote:
    """Use the actual service registry/dispatcher; no source-step substitutions."""

    def __init__(self):
        self.history = []

    async def tools(self):
        return await mcp_server.mcp.list_tools()

    async def call(self, name, arguments):
        self.history.append((name, deepcopy(arguments)))
        try:
            content, structured = await mcp_server.mcp.call_tool(name, arguments)
        except ToolError as error:
            raise MCPConnectionError(str(error)) from error
        assert structured is not None, content
        return structured


async def invoke(argv, context, document=None):
    document = yaml.safe_load(CONTRACT.read_text()) if document is None else document
    assets = [asset("workflow.yaml", json.dumps(document))]
    assets += [
        asset(s["path"], (ROOT / s["path"]).read_text())
        for s in document["provenance"]["sources"]
    ]
    workflow = workflow_documents(["workflow.yaml"], assets)[0]
    tools = [
        t.model_dump(by_alias=True, exclude_none=True)
        for t in await mcp_server.mcp.list_tools()
    ]
    compiled = compile_workflow("mcp:mathformer", workflow, tools)
    assert compiled["runnable"] is True, compiled["diagnostics"]
    remote = RegisteredRemote()

    async def authorize():
        pass

    with redirect_stderr(io.StringIO()):
        result = await execute(
            compiled, assets, {"argv": argv, "context": context}, remote, authorize
        )
    return result, remote.history


def original():
    path = ROOT / "tests/mcp/fixtures/generative_repair_original.py.txt"
    assert (
        hashlib.sha256(path.read_bytes()).hexdigest()
        == "688d2db9210e669fe43efdcdacf4e5e1caa3c96004ca799dc15a444a84ee3451"
    )
    spec = importlib.util.spec_from_loader(
        "_generative_original", SourceFileLoader("_generative_original", str(path))
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GenerativeRepairTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="generative-plan-fixture-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.context = {
            "working_directory": str(self.root),
            "program_name": "repair-plan.py",
        }
        self.oracle = original()
        # These are the only substituted execution boundaries. Neither is
        # reachable in this workflow: a call would be a semantic regression.
        self.compiler = self.enterContext(
            patch.object(
                subprocess,
                "run",
                side_effect=AssertionError("compiler/gate process invoked"),
            )
        )
        self.provider = self.enterContext(
            patch.object(
                urllib.request,
                "urlopen",
                side_effect=AssertionError("provider invoked"),
            )
        )
        self.addCleanup(self.assert_no_external_calls)

    def assert_no_external_calls(self):
        self.compiler.assert_not_called()
        self.provider.assert_not_called()

    def run_workflow(self, argv, document=None):
        return asyncio.run(invoke(argv, self.context, document))

    def packets(self, monitor=None, loop=None, objects=None, repairs=None):
        values = {
            "monitor-report": monitor or {},
            "repair-loop": loop or {},
            "object-packet": objects or {},
            "workbench-plan": {"status": "library_work_required"},
        }
        argv = []
        for name, packet in values.items():
            path = self.root / (name + ".json")
            path.write_text(json.dumps(packet, ensure_ascii=False))
            argv += ["--" + name, str(path)]
        for i, plan in enumerate(repairs or []):
            path = self.root / f"repair-{i}.json"
            path.write_text(json.dumps(plan))
            argv += ["--repair-plan", str(path)]
        return argv

    def compare(self, argv):
        result, history = self.run_workflow(argv)
        self.assertEqual(result["status"], "accepted", result)
        out = result["outputs"]
        # All original input files in differential calls use absolute paths.
        stdout = io.StringIO()
        with redirect_stdout(stdout), patch.object(sys, "argv", ["repair-plan.py"]):
            code = self.oracle.main(argv)
        self.assertEqual(code, out["exit_code"])
        self.assertEqual(stdout.getvalue(), out["stdout"])
        current_stdout = io.StringIO()
        with (
            redirect_stdout(current_stdout),
            patch.object(sys, "argv", ["repair-plan.py"]),
        ):
            self.assertEqual(native.main(argv), code)
        self.assertEqual(current_stdout.getvalue(), stdout.getvalue())
        if out["plan"] is not None:
            self.assertEqual(json.loads(stdout.getvalue()), out["plan"])
            self.assertEqual(len(out["plan"]["probe_prompts"]), 4)
            self.assertTrue(
                out["plan"]["acceptance_policy"]["generative_output_is_advisory"]
            )
            self.assertTrue(out["plan"]["requires_deterministic_first"])
            self.assertIn(
                "lake build",
                out["plan"]["acceptance_policy"]["must_rerun_after_any_proposed_edit"],
            )
        self.assertTrue(result["runtime"]["effect_records"])
        self.assertTrue(result["replay_artifacts"])
        return out["plan"], history

    def test_status_branches_and_high_risk(self):
        for monitor, loop, status in [
            ({}, {}, "needs_deterministic_repair_loop"),
            (
                {"status": "fail"},
                {"status": "not_required"},
                "needs_deterministic_repair_loop",
            ),
            ({"status": "pass"}, {}, "not_required"),
            ({"status": "pass"}, {"status": "not_required"}, "not_required"),
            ({"status": "fail"}, {"status": "blocked_on_library_or_labels"}, "ready"),
            ({"status": "unknown"}, {"status": None}, "ready"),
        ]:
            for high_risk in (False, True):
                with self.subTest(monitor=monitor, loop=loop, high_risk=high_risk):
                    argv = self.packets(monitor, loop) + (
                        ["--high-risk"] if high_risk else []
                    )
                    plan, history = self.compare(argv)
                    self.assertEqual(plan["status"], status)
                    self.assertEqual(plan["high_risk"], high_risk)
                    self.assertEqual(
                        [n.removeprefix(PREFIX) for n, _ in history],
                        ["load", "prepare", "prompts", "guards", "assemble", "emit"],
                    )
                    self.assertEqual(history[4][1]["status"], status)

    def test_categories_objects_repair_order_and_native_repr(self):
        for active in ([], ["z", 4, "z"]):
            argv = self.packets(
                {"category_counts": {"z": "2", "a": 1, "zero": 0, "negative": -1}},
                {"active_categories": active, "blockers": [{"z": "é", "a": 1}]},
                {
                    "objects": [
                        {"object_class": "operator"},
                        None,
                        "skip",
                        {},
                        {"object_class": {"z": 1, "a": 2}},
                        {"object_class": "operator"},
                    ]
                },
                [{"style": "second"}, {}, {"style": "first"}],
            )
            plan, _ = self.compare(argv)
            self.assertEqual(
                plan["active_categories"], ["z", "4", "z"] if active else ["a", "z"]
            )
            self.assertEqual(
                plan["detected_object_classes"],
                ["operator", "None", "{'z': 1, 'a': 2}", "operator"],
            )
            self.assertEqual(plan["repair_plan_styles"], ["second", "unknown", "first"])
            self.assertIn("[{'z': 'é', 'a': 1}]", plan["probe_prompts"][0]["prompt"])
        plan, _ = self.compare(self.packets({"category_counts": []}))
        self.assertEqual(plan["active_categories"], [])

    def test_preview_bounds_and_inline_empty_precedence(self):
        for count in (799, 800, 801, 5000):
            argv = ["--source-text", "  é" * count, "--lean-text", "x" * count]
            _, history = self.compare(argv)
            prepared = history[2][1]["prepared"]
            self.assertEqual(
                prepared["source_preview"], (" ".join(("  é" * count).split()))[:800]
            )
            self.assertEqual(len(prepared["lean_preview"]), min(800, count))
        plan, _ = self.compare(
            [
                "--source-file",
                str(Path(gettempdir()) / "mathformer-test-fixtures/no-such-source"),
                "--source-text",
                "",
                "--lean-file",
                str(Path(gettempdir()) / "mathformer-test-fixtures/no-such-lean"),
                "--lean-text",
                "",
            ]
        )
        self.assertIn(
            "Source preview:\n\n\nLean preview:\n\n", plan["probe_prompts"][0]["prompt"]
        )

    def test_relative_file_context_and_exact_file_output(self):
        (self.root / "source.txt").write_text("source\n  é")
        (self.root / "lean.txt").write_text("theorem fixture : True := by trivial")
        result, history = self.run_workflow(
            [
                "--source-file",
                "source.txt",
                "--lean-file",
                "lean.txt",
                "--output",
                "out/plan.json",
            ]
        )
        self.assertEqual(result["status"], "accepted", result)
        self.assertEqual(result["outputs"]["stdout"], "")
        actual = (self.root / "out/plan.json").read_bytes()
        original_out = self.root / "original/plan.json"
        self.assertEqual(
            self.oracle.main(
                [
                    "--source-file",
                    str(self.root / "source.txt"),
                    "--lean-file",
                    str(self.root / "lean.txt"),
                    "--output",
                    str(original_out),
                ]
            ),
            0,
        )
        self.assertEqual(actual, original_out.read_bytes())
        self.assertEqual(json.loads(actual), result["outputs"]["plan"])
        self.assertEqual(
            history[-1][1]["control"]["output"], str(self.root / "out/plan.json")
        )

    def test_self_test_skips_inputs_and_help_early_stop(self):
        plan, _ = self.compare(
            [
                "--self-test",
                "--source-file",
                str(Path(gettempdir()) / "mathformer-test-fixtures/missing"),
                "--monitor-report",
                str(Path(gettempdir()) / "mathformer-test-fixtures/missing"),
                "--repair-plan",
                str(Path(gettempdir()) / "mathformer-test-fixtures/missing"),
            ]
        )
        self.assertEqual(plan["status"], "ready")
        self.assertTrue(plan["high_risk"])
        result, history = self.run_workflow(
            [
                "--help",
                "--source-file",
                str(Path(gettempdir()) / "mathformer-test-fixtures/missing"),
            ]
        )
        self.assertEqual(result["status"], "accepted", result)
        stdout = io.StringIO()
        with (
            redirect_stdout(stdout),
            patch.object(sys, "argv", ["repair-plan.py"]),
            self.assertRaises(SystemExit) as stop,
        ):
            self.oracle.main(
                [
                    "--help",
                    "--source-file",
                    str(Path(gettempdir()) / "mathformer-test-fixtures/missing"),
                ]
            )
        self.assertEqual(stop.exception.code, 0)
        self.assertEqual(
            result["outputs"],
            {"plan": None, "exit_code": 0, "stdout": stdout.getvalue()},
        )
        self.assertEqual([n.removeprefix(PREFIX) for n, _ in history], ["load", "help"])

    def test_errors_stop_at_the_native_step(self):
        invalid = self.root / "invalid.json"
        invalid.write_text("{invalid")
        cases = [
            (["--unrecognized"], "load"),
            (["--monitor-report", str(invalid)], "load"),
            (
                [
                    "--source-file",
                    str(Path(gettempdir()) / "mathformer-test-fixtures/missing"),
                    "--monitor-report",
                    str(invalid),
                ],
                "load",
            ),
            (
                self.packets({"status": "pass", "category_counts": {"bad": "NaN"}}),
                "prepare",
            ),
        ]
        # packets() intentionally overwrites files; create independent payloads
        # for failures after the earlier fixtures have been consumed.
        for argv, last in cases:
            result, history = self.run_workflow(
                argv + ["--output", str(self.root / "never.json")]
            )
            self.assertEqual(result["status"], "failed", result)
            self.assertIsNone(result["outputs"])
            self.assertTrue(history[-1][0].endswith("_" + last), history)
            self.assertFalse((self.root / "never.json").exists())
        for packets, last in [
            ({"loop": {"status": []}}, "guards"),
            ({"repairs": ["invalid-plan"]}, "assemble"),
        ]:
            result, history = self.run_workflow(self.packets(**packets))
            self.assertEqual(result["status"], "failed", result)
            self.assertTrue(history[-1][0].endswith("_" + last), history)

    def test_emit_failure_and_service_write_policy(self):
        blocked = self.root / "file"
        blocked.write_text("not a directory")
        result, history = self.run_workflow(["--output", str(blocked / "out.json")])
        self.assertEqual(result["status"], "failed")
        self.assertTrue(history[-1][0].endswith("_emit"))
        with patch.object(mcp_server, "_READONLY", True):
            result, _ = self.run_workflow(["--output", str(self.root / "denied.json")])
            self.assertEqual(result["status"], "failed")
        self.assertFalse((self.root / "denied.json").exists())
        with patch.object(mcp_server, "_ALLOWED_WRITE_ROOTS", [self.root / "allowed"]):
            result, _ = self.run_workflow(["--output", str(self.root / "denied.json")])
            self.assertEqual(result["status"], "failed")
        self.assertFalse((self.root / "denied.json").exists())

    def test_exact_call_bound_and_budget_exhaustion(self):
        document = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(document["policy"]["limits"]["max_operation_calls"], 6)
        result, history = self.run_workflow([])
        self.assertEqual(result["status"], "accepted")
        self.assertEqual(len(history), 6)
        document["policy"]["limits"]["max_operation_calls"] = 5
        result, history = self.run_workflow(
            ["--output", str(self.root / "never.json")], document
        )
        self.assertEqual(result["status"], "failed", result)
        self.assertIsNone(result["outputs"])
        self.assertEqual(len(history), 5)
        self.assertTrue(history[-1][0].endswith("_assemble"))
        self.assertFalse((self.root / "never.json").exists())

    def test_registered_self_test_assertions_and_evidence_check(self):
        data, control = native.load_inputs(["--self-test"])
        plan = self.oracle.build_plan(**data)
        plan["forbidden_shortcuts"] = []

        async def call(plan_json):
            return await mcp_server.mcp.call_tool(
                PREFIX + "emit",
                {"control": control, "plan": plan, "plan_json": plan_json},
            )

        with self.assertRaises(ToolError):
            asyncio.run(call(json.dumps(plan)))
        with self.assertRaises(ToolError):
            asyncio.run(call("{}"))

    def test_authored_generator_and_provenance(self):
        doc = yaml.safe_load(CONTRACT.read_text())
        generator_path = (
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py"
        )
        spec = importlib.util.spec_from_file_location(
            "_generative_normalizer", generator_path
        )
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)
        generated = [item for item in generator.inventory() if item["id"] == doc["id"]]
        self.assertEqual(generated, [doc])
        authored = json.loads(
            (
                ROOT
                / "skills/control/workflow-contract-validator/references/generative-repair.workflow.json"
            ).read_text()
        )
        self.assertEqual(doc, authored)
        self.assertEqual(doc["lifecycle"], "active")
        self.assertTrue(
            any(
                s["path"].endswith("/build_physics_lean_generative_repair_plan.py")
                for s in doc["provenance"]["sources"]
            )
        )
        for row in doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(GenerativeRepairTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
