#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Source equivalence, deterministic matrix boundaries, real MCP and PRISM runtime."""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT / "tests/mcp/fixtures"),
    str(ROOT),
]
import asyncio
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
from io import StringIO
import json
import tempfile
from types import ModuleType
import unittest
from unittest.mock import patch
import yaml
from e2e_all_backends_tools import source
from e2e_all_backends_boundary import install
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_e2e_all_backends_workflow/workflow.yaml"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])


def assets(document):
    files = {DESCRIPTOR: json.dumps(document)}
    for row in document["provenance"]["sources"]:
        files[row["path"]] = (ROOT / row["path"]).read_text()
    return [
        {
            "path": path,
            "content": text,
            "encoding": "text",
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
        }
        for path, text in files.items()
    ]


class AllBackendsTests(unittest.TestCase):
    def test_original_entrypoint_equivalence(self):
        original = ModuleType("original")
        original.__file__ = str(ROOT / "tests/e2e/run_all_backends.py")
        exec(
            (ROOT / "tests/mcp/fixtures/e2e_all_backends_original.py.txt").read_text(),
            original.__dict__,
        )
        native = source()
        for mode in ("success", "mixed", "empty", "launch_error"):
            for flag in (False, True):
                with tempfile.TemporaryDirectory() as tmp:
                    results = []
                    for module in (original, native):
                        # Same paths, fresh filesystem, same deterministic compiler.
                        import shutil

                        root = Path(tmp) / "repo"
                        shutil.rmtree(root, ignore_errors=True)
                        runner, calls = install(module, root, mode)
                        output = StringIO()
                        with (
                            patch.object(
                                sys,
                                "argv",
                                ["run_all_backends.py"] + (["--json"] if flag else []),
                            ),
                            redirect_stdout(output),
                        ):
                            if mode == "launch_error":
                                with self.assertRaisesRegex(
                                    OSError, "fixture launch failed"
                                ):
                                    module.main()
                                self.assertFalse(module.OUT.exists())
                                continue
                            code = module.main()
                        wrapper = json.loads(
                            (
                                module.OUT.parent / "e2e_all_backends_wrapper.json"
                            ).read_text()
                        )
                        report = json.loads(module.OUT.read_text())
                        results.append(
                            (code, output.getvalue(), wrapper, report, list(calls))
                        )
                        self.assertEqual(report["schema_errors"], [])
                        self.assertTrue(
                            (runner.ARTIFACT_ROOT / "dependency_map.json").exists()
                        )
                        if mode == "mixed":
                            self.assertEqual(
                                [r["status"] for r in report["results"]],
                                ["fail", "fail", "skip", "pass", "fail", "pass"],
                            )
                            self.assertEqual(
                                [r["check_id"] for r in report["results"]],
                                [
                                    "fail",
                                    "timeout",
                                    "skip",
                                    "expected",
                                    "audit",
                                    "pass",
                                ],
                            )
                            self.assertEqual(
                                [c["timeout"] for c in calls], [120, 7, 120, 120, 120]
                            )
                            self.assertEqual(report["results"][1]["stdout"], "partial")
                            self.assertEqual(
                                report["results"][4]["write_audit"]["unexpected_paths"],
                                ["unexpected.txt"],
                            )
                            self.assertEqual(code, 3)
                        else:
                            self.assertEqual(code, 0)
                            self.assertEqual(
                                report["summary"]["total"],
                                1 if mode == "success" else 0,
                            )
                    if results:
                        self.assertEqual(results[0], results[1])
        # Parser errors must precede launch.
        with (
            patch.object(sys, "argv", ["wrapper", "--invalid"]),
            redirect_stdout(StringIO()),
        ):
            with self.assertRaises(SystemExit) as error:
                native.main()
            self.assertEqual(error.exception.code, 2)

    def test_registered_tools_compiler_and_runtime(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(document["id"], "hub_e2e_all_backends_workflow")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 900, "max_operation_calls": 3},
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )

        async def allow():
            pass

        for mode in ("success", "mixed", "empty", "launch_error"):
            for flag in (False, True):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    manager = SessionManager()
                    config = StdioConfig(
                        command=sys.executable,
                        args=[
                            str(ROOT / "tests/mcp/fixtures/e2e_all_backends_server.py"),
                            tmp,
                            mode,
                        ],
                        cwd=str(ROOT),
                    )
                    async with manager.open("all-backends", config, {}) as remote:
                        tools = [
                            tool.model_dump(by_alias=True, exclude_none=True)
                            for tool in await remote.tools()
                        ]

                        def compile_doc(doc):
                            snapshot = assets(doc)
                            compiled = compile_workflow(
                                "mcp:all-backends",
                                workflow_documents([DESCRIPTOR], snapshot)[0],
                                tools,
                            )
                            self.assertTrue(
                                compiled["runnable"], compiled["diagnostics"]
                            )
                            self.assertTrue(compiled["runtime_source"])
                            self.assertEqual(
                                set(compiled["bindings"]), set(doc["operations"])
                            )
                            return compiled, snapshot

                        workflow, snapshot = compile_doc(document)
                        inputs = {
                            "json_output": flag,
                            "context": {"allow_mutating": True},
                        }
                        result = await execute(
                            workflow, snapshot, inputs, remote, allow
                        )
                        if mode == "launch_error":
                            self.assertEqual(result["status"], "failed", result)
                            self.assertIsNone(result["outputs"])
                            self.assertEqual(
                                [c["operation"] for c in result["calls"]],
                                ["prepare_command", "run_suite"],
                            )
                            self.assertFalse(
                                (
                                    root
                                    / "artifacts/test_program/e2e_all_backends_wrapper.json"
                                ).exists()
                            )
                            continue
                        self.assertEqual(result["status"], "accepted", result)
                        output = result["outputs"]
                        self.assertEqual(
                            output["exit_code"], 3 if mode == "mixed" else 0
                        )
                        self.assertEqual(output["report"]["ok"], mode != "mixed")
                        self.assertEqual(
                            output["report"],
                            json.loads(
                                (
                                    root
                                    / "artifacts/test_program/e2e_all_backends_wrapper.json"
                                ).read_text()
                            ),
                        )
                        self.assertEqual(
                            [c["operation"] for c in result["calls"]],
                            [
                                "prepare_command",
                                "run_suite",
                                "write_wrapper_and_return",
                            ],
                        )
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["replay_artifacts"])
                        detailed = json.loads(
                            (
                                root / "artifacts/test_program/e2e_all_backends.json"
                            ).read_text()
                        )
                        self.assertEqual(
                            detailed["summary"]["total"],
                            {"success": 1, "mixed": 6, "empty": 0}[mode],
                        )
                        # Explicit authorization denial fails before the native run.
                        denied = await execute(
                            workflow,
                            snapshot,
                            {**inputs, "context": {"allow_mutating": False}},
                            remote,
                            allow,
                        )
                        self.assertEqual(denied["status"], "failed")
                        self.assertEqual(
                            [c["operation"] for c in denied["calls"]],
                            ["prepare_command", "run_suite"],
                        )
                        if mode == "success" and flag:
                            for budget in (1, 2):
                                bounded = deepcopy(document)
                                bounded["policy"]["limits"][
                                    "max_operation_calls"
                                ] = budget
                                compiled, snap = compile_doc(bounded)
                                exhausted = await execute(
                                    compiled, snap, inputs, remote, allow
                                )
                                self.assertEqual(
                                    exhausted["status"], "failed", exhausted
                                )
                                self.assertIsNone(exhausted["outputs"])
                                self.assertEqual(
                                    sum(
                                        bool(c.get("transport_call_performed"))
                                        for c in exhausted["calls"]
                                    ),
                                    budget,
                                )
                            prepared = await remote.call(
                                "mathformer_e2e_all_backends_prepare",
                                {"json_output": True},
                            )
                            prepared["plan"]["command"] = ["forbidden"]
                            with self.assertRaises(Exception):
                                await remote.call(
                                    "mathformer_e2e_all_backends_execute",
                                    {**prepared, "context": {"allow_mutating": True}},
                                )
                    self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
