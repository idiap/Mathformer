#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""No provider or external compiler is needed by this source test workflow.

Exercise its real subprocess, registered MCP ports and Lunar's real PRISM
parser/checker/compiler/runtime. No production implementation is substituted.
"""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.path[:0] = [str(LUNAR / "app/backend"), str(ROOT / "scripts"), str(ROOT)]
import asyncio
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
import re
import subprocess
import tempfile
import unittest
import yaml
from adoption_provenance_test_tools import ProvenanceTestTools
import mathformer as hub
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_adoption_test_provenance_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
CONTEXT = dict(
    dry_run=False,
    json_output=True,
    keep_going=False,
    allow_mutating=False,
    write_report=False,
)


def snapshot(document):
    def asset(path, text):
        return {
            "path": path,
            "content": text,
            "encoding": "text",
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
        }

    paths = {row["path"] for row in document["provenance"]["sources"]} | {SCHEMA}
    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(path, (ROOT / path).read_text()) for path in sorted(paths)
    ]


def source():
    spec = importlib.util.spec_from_file_location(
        "provenance_source", ROOT / "tests/control/test_adoption_provenance.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProvenanceWorkflowTests(unittest.TestCase):
    maxDiff = None

    def test_native_parity_cursor_errors_and_protocol_guards(self):
        # Frozen source uses its native project-relative __file__, so execute
        # under that filename to retain the real receipt module import path.
        oracle_code = (
            ROOT / "tests/mcp/fixtures/provenance_original.py.txt"
        ).read_text()
        oracle = type(sys)("provenance_oracle")
        oracle.__file__ = str(ROOT / "tests/control/test_adoption_provenance.py")
        exec(compile(oracle_code, oracle.__file__, "exec"), oracle.__dict__)
        stream = io.StringIO()
        result = unittest.TextTestRunner(stream=stream).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(oracle.ReceiptTests)
        )
        self.assertTrue(result.wasSuccessful(), stream.getvalue())
        self.assertEqual(result.testsRun, 11)
        self.assertFalse(result.skipped)
        service = ProvenanceTestTools()
        try:
            boundary = service.prepare(CONTEXT)["boundary"]
            state = service.initialize(boundary)["state"]
            self.assertEqual(state["tests"], sorted(state["tests"]))
            self.assertEqual(len(state["tests"]), 11)
            with self.assertRaises(ValueError):
                service.finish(boundary, state)
            for index in range(11):
                old = deepcopy(state)
                observation = service.run_case(state)["observation"]
                self.assertEqual(observation, {"status": "passed", "diagnostics": []})
                with self.assertRaises(ValueError):
                    service.run_case(state)
                with self.assertRaises(ValueError):
                    service.advance(state, {"status": "error", "diagnostics": []})
                advanced = service.advance(state, observation)
                state = advanced["state"]
                self.assertEqual(advanced["done"], index == 10)
                self.assertEqual(state["index"], index + 1)
                self.assertEqual(state["tests_run"], index + 1)
                self.assertEqual(state["failures"] + state["errors"], 0)
                with self.assertRaises(ValueError):
                    service.run_case(old)
            with self.assertRaises(ValueError):
                service.run_case(state)
            native_boundary = service.sessions[state["session"]]["native"]
            payload = service.finish(boundary, state)["result"]
            self.assertTrue(payload["ok"], payload)
            self.assertEqual(payload["returncode"], 0)
            self.assertEqual(payload["stdout"], "")

            def normalize(value):
                return re.sub(r"Ran 11 tests in [\d.]+s", "Ran 11 tests in TIME", value)

            self.assertEqual(normalize(payload["stderr"]), normalize(stream.getvalue()))
            self.assertTrue(payload["write_audit"]["ok"])
            self.assertFalse(service.sessions)
            # The real after-snapshot audit cannot accept an undeclared write.
            with tempfile.TemporaryDirectory(
                prefix="provenance-audit-", dir=ROOT
            ) as temp:
                marker = Path(temp) / "unexpected.txt"
                marker.write_text("fixture write")
                audited = hub.finish_leaf_boundary(
                    hub.build_registry()["adoption:test-provenance"],
                    native_boundary,
                    payload,
                )
                self.assertFalse(audited["ok"])
                self.assertEqual(audited["status"], "undeclared_writes")
                self.assertIn(
                    marker.relative_to(ROOT).as_posix(),
                    audited["write_audit"]["unexpected_paths"],
                )
                self.assertIn("wrote outside its declared roots", audited["stderr"])
            # A native entrypoint invokes the same cursor and runner summary.
            native = subprocess.run(
                [sys.executable, "tests/control/test_adoption_provenance.py"],
                text=True,
                capture_output=True,
                cwd=ROOT,
            )
            self.assertEqual(native.returncode, 0, native.stderr)
            self.assertEqual(normalize(native.stderr), normalize(payload["stderr"]))

            # Exercise real unittest assertion/error propagation and continuation
            # using fixture cases; no receipt operation is replaced.
            class Cases(unittest.TestCase):
                def test_a(self):
                    self.fail("fixture assertion")

                def test_b(self):
                    raise ValueError("fixture error")

                def test_c(self):
                    self.assertTrue(True)

            native_result = unittest.TestResult()
            cursor = source().ReceiptCursor(
                native_result, unittest.defaultTestLoader.loadTestsFromTestCase(Cases)
            )
            statuses = []
            for index in range(3):
                observation = cursor.run_case()
                statuses.append(observation["status"])
                self.assertEqual(cursor.advance(observation), index == 2)
            self.assertEqual(statuses, ["failure", "error", "passed"])
            self.assertEqual(cursor.state()["tests_run"], 3)
            self.assertEqual(cursor.state()["failures"], 1)
            self.assertEqual(cursor.state()["errors"], 1)
            self.assertFalse(native_result.wasSuccessful())

            # Cancellation is propagated by unittest, without cursor advancement.
            class Cancel(unittest.TestCase):
                def test_cancel(self):
                    raise KeyboardInterrupt("cancel")

            cursor = source().ReceiptCursor(
                unittest.TestResult(), [Cancel("test_cancel")]
            )
            with self.assertRaises(KeyboardInterrupt):
                cursor.run_case()
            self.assertEqual(cursor.index, 0)
        finally:
            service.close()

    def test_registered_mcp_and_real_lunar_prism_execution(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_adoption_test_provenance_workflow")
        self.assertEqual(document["lifecycle"], "active")
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        # Import the actual production registrations without the CLI config loader.
        server = 'import sys;sys.path[:0]=["scripts","."];from mcp_server import mcp;mcp.run(transport="stdio")'
        async with manager.open(
            "provenance-tests",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {},
        ) as remote:
            failure = None
            try:
                inventory = [
                    tool.model_dump(by_alias=True, exclude_none=True)
                    for tool in await remote.tools()
                ]

                def compile(doc):
                    assets = snapshot(doc)
                    compiled = compile_workflow(
                        "mcp:provenance-tests",
                        workflow_documents([DESCRIPTOR], assets)[0],
                        inventory,
                    )
                    self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                    self.assertTrue(compiled["runtime_source"])
                    self.assertEqual(set(compiled["bindings"]), set(doc["operations"]))
                    return compiled, assets

                workflow, assets = compile(document)

                async def authorize():
                    pass

                async def run(doc=None, **inputs):
                    w, a = compile(doc) if doc else (workflow, assets)
                    return await execute(
                        w, a, {"context": CONTEXT, **inputs}, remote, authorize
                    )

                early = await run(context={**CONTEXT, "dry_run": True})
                self.assertEqual(early["status"], "accepted", early)
                self.assertEqual(early["outputs"]["result"]["status"], "dry_run")
                self.assertEqual(
                    [c["operation"] for c in early["calls"]],
                    ["prepare", "initialize", "inactive", "early"],
                )
                denied = await run(extra_args=["--failfast"])
                self.assertEqual(denied["status"], "accepted", denied)
                self.assertFalse(denied["outputs"]["result"]["ok"])
                self.assertTrue(denied["outputs"]["result"]["preflight_errors"])
                self.assertEqual(
                    [c["operation"] for c in denied["calls"]],
                    ["prepare", "initialize", "inactive", "early"],
                )
                result = await run()
                self.assertEqual(result["status"], "accepted", result)
                payload = result["outputs"]["result"]
                self.assertTrue(payload["ok"], payload)
                self.assertEqual(payload["returncode"], 0)
                self.assertIn("Ran 11 tests", payload["stderr"])
                self.assertNotIn("skipped", payload["stderr"])
                self.assertEqual(len(result["calls"]), 25)
                self.assertEqual(
                    [c["operation"] for c in result["calls"]],
                    ["prepare", "initialize"]
                    + ["run_case", "advance"] * 11
                    + ["finish"],
                )
                self.assertTrue(result["runtime"]["effect_records"])
                self.assertTrue(result["runtime"]["provenance"])
                self.assertTrue(result["replay_artifacts"])
                # A real registered tool rejects a forged live-state identity;
                # Lunar propagates the MCP failure and never finalizes the suite.
                invalid = deepcopy(document)
                invalid["flow"]["steps"][2]["body"]["cases"][0]["body"]["steps"][0][
                    "arguments"
                ]["state"] = {
                    "literal": {
                        "session": "not-a-real-session",
                        "index": 0,
                        "tests": [],
                        "tests_run": 0,
                        "failures": 0,
                        "errors": 0,
                    }
                }
                rejected = await run(invalid)
                self.assertEqual(rejected["status"], "failed", rejected)
                self.assertIsNone(rejected["outputs"])
                self.assertEqual(
                    [c["operation"] for c in rejected["calls"]],
                    ["prepare", "initialize", "run_case"],
                )
                self.assertEqual(rejected["calls"][-1]["status"], "rejected")
                bounded = deepcopy(document)
                bounded["flow"]["steps"][2]["max_iterations"] = 1
                result = await run(bounded)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(result["failure_disposition"], "fail")
                self.assertEqual(
                    [c["operation"] for c in result["calls"]],
                    ["prepare", "initialize", "run_case", "advance"],
                )
                budget = deepcopy(document)
                budget["policy"]["limits"]["max_operation_calls"] = 1
                result = await run(budget)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertIn("budget", json.dumps(result).lower())
                timed = deepcopy(document)
                timed["policy"]["limits"]["wall_time_seconds"] = 1
                w, a = compile(timed)

                async def stalled_authority():
                    await asyncio.Event().wait()

                with self.assertRaises(TimeoutError):
                    await execute(w, a, {"context": CONTEXT}, remote, stalled_authority)
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
