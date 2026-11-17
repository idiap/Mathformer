#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Execute real suite steps and Lunar/PRISM against isolated filesystem inputs."""

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
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import json
import shutil
import tempfile
import unittest
import yaml
from meta_suite_tools import source
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_meta_skills_validate_workflow/workflow.yaml"


def fixture(root):
    # Copy only the actual command implementations. Absent registries/inputs are
    # deliberate filesystem fixtures. No provider, credentials or solver exists.
    shutil.copytree(ROOT / "meta_skills/schemas", root / "meta_skills/schemas")
    for command in source().COMMANDS:
        path = root / command[0]
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / command[0], path)


def snapshot(doc):
    def asset(path, content):
        return dict(
            path=path,
            content=content,
            encoding="text",
            sha256=hashlib.sha256(content.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(doc))] + [
        asset(row["path"], (ROOT / row["path"]).read_text())
        for row in {r["path"]: r for r in doc["provenance"]["sources"]}.values()
    ]


def stable(report):
    report = deepcopy(report)
    for row in report["results"]:
        row.pop("duration_seconds")
    return report


class SuiteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        fixture(self.root)

    def test_native_process_parsing_state_and_exceptions(self):
        native = source()
        for code, expected in [
            ("print('{\"ok\": false}')", False),
            ("print('{\"ok\": true}')", True),
            ('print("plain")', True),
            ("import sys; print('{\"ok\": true}'); sys.exit(7)", False),
        ]:
            check = native.run_command(["-c", code], self.root)
            self.assertEqual(check["ok"], expected)
            self.assertEqual(check["command"], [sys.executable, "-c", code])
        check = native.run_command(
            ["-c", 'import sys;print("x"*5000);print("e"*5000,file=sys.stderr)'],
            self.root,
        )
        self.assertEqual(len(check["stdout"]), 4000)
        self.assertEqual(len(check["stderr"]), 4000)
        self.assertEqual(len(check["payload"]["stdout"]), 5001)
        failed_array = native.run_command(
            ["-c", 'import sys;print("[]");sys.exit(1)'], self.root
        )
        self.assertFalse(failed_array["ok"])
        self.assertEqual(failed_array["payload"], [])
        with self.assertRaises(AttributeError):
            native.run_command(["-c", 'print("[]")'], self.root)
        with self.assertRaises(OSError):
            native.run_command(["-c", "pass"], self.root / "absent")
        results = native.initialize_results()
        for index in range(10):
            self.assertEqual(native.select_command(results), native.COMMANDS[index])
            previous = deepcopy(results)
            result = native.append_and_test(results, check)
            self.assertEqual(results, previous)
            self.assertEqual(result["done"], index == 9)
            results = result["results"]
        with self.assertRaises(IndexError):
            native.select_command(results)
        report = native.aggregate_write_return(results, self.root / "pass.json")
        self.assertTrue(report["ok"])
        self.assertEqual(report["summary"], {"pass": 10, "fail": 0})
        self.assertEqual(json.loads((self.root / "pass.json").read_text()), report)
        blocker = self.root / "block"
        blocker.write_text("file")
        with self.assertRaises(OSError):
            native.aggregate_write_return(results, blocker / "report.json")

    def test_original_suite_equivalence(self):
        native = source()
        spec = importlib.util.spec_from_loader(
            "suite_oracle",
            SourceFileLoader(
                "suite_oracle",
                str(ROOT / "tests/mcp/fixtures/meta_suite_original.py.txt"),
            ),
        )
        original = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(original)
        old_root, old_output = native.REPO_ROOT, native.OUTPUT_PATH
        try:
            for module in (original, native):
                module.REPO_ROOT = self.root
                module.OUTPUT_PATH = self.root / "report.json"
            expected = original.run_suite()
            actual = native.run_suite()
            self.assertEqual(stable(actual), stable(expected))
            self.assertEqual(actual["check_count"], 10)
            self.assertFalse(actual["ok"])
            # Uncaught launch failures preserve any earlier report.
            native.REPO_ROOT = self.root / "absent"
            before = native.OUTPUT_PATH.read_bytes()
            with self.assertRaises(OSError):
                native.run_suite()
            self.assertEqual(native.OUTPUT_PATH.read_bytes(), before)
        finally:
            native.REPO_ROOT, native.OUTPUT_PATH = old_root, old_output

    def test_registered_mcp_lunar_parser_checker_compiler_runtime(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        doc = yaml.safe_load(Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text())
        self.assertEqual(doc["id"], "hub_meta_skills_validate_workflow")
        self.assertEqual(doc["lifecycle"], "active")
        for row in doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp.server.fastmcp import FastMCP;from meta_suite_tools import register_meta_suite_tools;mcp=FastMCP("suite-fixture");register_meta_suite_tools(mcp);mcp.run(transport="stdio")'
        async with manager.open(
            "suite",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {},
        ) as remote:
            tools = [
                tool.model_dump(by_alias=True, exclude_none=True)
                for tool in await remote.tools()
            ]

            def compile(document, inventory=None):
                assets = snapshot(document)
                selected = workflow_documents([DESCRIPTOR], assets)[0]
                return (
                    compile_workflow(
                        "mcp:suite", selected, tools if inventory is None else inventory
                    ),
                    assets,
                )

            compiled, assets = compile(doc)
            self.assertTrue(compiled["runnable"], compiled["diagnostics"])
            self.assertTrue(compiled["runtime_source"])
            self.assertEqual(set(compiled["bindings"]), set(doc["operations"]))
            self.assertFalse(compile(doc, [])[0]["runnable"])

            async def authorize():
                pass

            async def run(document=doc, root=None, output=None):
                workflow, assets = compile(document)
                return await execute(
                    workflow,
                    assets,
                    {
                        "repo_root": str(root or self.root),
                        "output_path": str(output or self.root / "report.json"),
                    },
                    remote,
                    authorize,
                )

            result = await run()
            self.assertEqual(result["status"], "accepted", result)
            report = result["outputs"]["report"]
            expected = source().aggregate_write_return(
                [source().run_command(c, self.root) for c in source().COMMANDS],
                self.root / "expected.json",
            )
            self.assertEqual(stable(report), stable(expected))
            self.assertEqual(
                json.loads((self.root / "report.json").read_text()), report
            )
            self.assertEqual(
                [r["command"][1:] for r in report["results"]], source().COMMANDS
            )
            self.assertGreater(report["summary"]["pass"], 0)
            self.assertGreater(report["summary"]["fail"], 0)
            self.assertEqual(report["results"][2]["payload"]["ok"], True)
            self.assertEqual(len(result["calls"]), 32)
            self.assertEqual(
                [c["tool"] for c in result["calls"]],
                ["mathformer_meta_suite_initialize"]
                + [
                    "mathformer_meta_suite_" + step
                    for _ in range(10)
                    for step in ("select", "run", "append")
                ]
                + ["mathformer_meta_suite_finalize"],
            )
            self.assertTrue(result["replay_artifacts"])
            self.assertTrue(result["runtime"]["effect_records"])
            # Native failures abort before append/finalize; no retries.
            failed = await run(
                root=self.root / "absent", output=self.root / "never.json"
            )
            self.assertEqual(failed["status"], "failed", failed)
            self.assertIsNone(failed["outputs"])
            self.assertEqual(len(failed["calls"]), 3)
            self.assertFalse((self.root / "never.json").exists())
            blocker = self.root / "blocked"
            blocker.write_text("file")
            failed = await run(output=blocker / "report.json")
            self.assertEqual(failed["status"], "failed", failed)
            self.assertEqual(len(failed["calls"]), 32)
            self.assertEqual(failed["calls"][-1]["status"], "rejected")
            exhausted = deepcopy(doc)
            exhausted["flow"]["steps"][1]["max_iterations"] = 9
            failed = await run(exhausted, output=self.root / "exhausted.json")
            self.assertEqual(failed["status"], "failed", failed)
            self.assertFalse((self.root / "exhausted.json").exists())
            self.assertEqual(
                sum(c["tool"] == "mathformer_meta_suite_run" for c in failed["calls"]),
                9,
            )
            budget = deepcopy(doc)
            budget["policy"]["limits"]["max_operation_calls"] = 2
            failed = await run(budget, output=self.root / "budget.json")
            self.assertEqual(failed["status"], "failed")
            self.assertFalse((self.root / "budget.json").exists())
            self.assertEqual(
                sum(bool(c.get("transport_call_performed")) for c in failed["calls"]), 2
            )
            self.assertIn("budget", str(failed).lower())
            timed = deepcopy(doc)
            timed["policy"]["limits"]["wall_time_seconds"] = 1
            workflow, assets = compile(timed)

            async def pending():
                await asyncio.Event().wait()

            with self.assertRaises(TimeoutError):
                await execute(
                    workflow,
                    assets,
                    {
                        "repo_root": str(self.root),
                        "output_path": str(self.root / "timeout.json"),
                    },
                    remote,
                    pending,
                )
            self.assertFalse((self.root / "timeout.json").exists())
            # Reject arbitrary commands at the advertised MCP interface.
            with self.assertRaises(Exception):
                await remote.call(
                    "mathformer_meta_suite_run",
                    {
                        "command": ["-c", "raise SystemExit(0)"],
                        "repo_root": str(self.root),
                    },
                )
        self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
