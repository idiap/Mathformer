#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Real unittest/MCP/Lunar/PRISM parity; no scientific or provider execution.

This source has no external model/compiler calls. Deterministic compiler inputs
are actual contract snapshots and MCP schemas; the PRISM compiler is never stubbed.
Native stale projections remain failures in HubResult, as in the original suite.
"""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.dont_write_bytecode = True
sys.path[:0] = [str(LUNAR / "app/backend"), str(ROOT / "scripts"), str(ROOT)]
import asyncio
from copy import deepcopy
import hashlib
import io
import json
import tempfile
import unittest
import yaml
from normalized_workflow_test_tools import NormalizedTestTools, source_suite
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_control_normalized_workflows_tests_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
CONTEXT = dict(
    dry_run=False,
    json_output=False,
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


def original():
    module = type(sys)("_normalized_original")
    module.__file__ = str(ROOT / "tests/control/test_normalized_workflows.py")
    sys.modules[module.__name__] = module
    exec(
        compile(
            (ROOT / "tests/mcp/fixtures/normalized_tests_original.py.txt").read_text(),
            module.__file__,
            "exec",
        ),
        module.__dict__,
    )
    return module


def outcomes(result):
    return {
        "run": result.testsRun,
        "failures": [c._testMethodName for c, _ in result.failures],
        "errors": [c._testMethodName for c, _ in result.errors],
        "skipped": result.skipped,
    }


class NormalizedExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        cls.module = source_suite()
        cls.oracle_stream = io.StringIO()
        cls.oracle = unittest.TextTestRunner(stream=cls.oracle_stream).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(
                original().NormalizedWorkflowTests
            )
        )
        assert cls.oracle.testsRun == 12 and not cls.oracle.skipped

    def test_original_and_shared_native_entrypoint(self):
        stream = io.StringIO()
        result = unittest.TextTestRunner(stream=stream).run(
            unittest.defaultTestLoader.loadTestsFromModule(self.module)
        )
        self.assertEqual(outcomes(result), outcomes(self.oracle))
        service = NormalizedTestTools()
        prepared = service.prepare(CONTEXT, [])
        self.assertTrue(prepared["execute"])
        initialized = service.initialize(prepared["boundary"])
        self.assertTrue(initialized["runnable"])
        state = initialized["state"]
        self.assertEqual(state["remaining"], sorted(state["remaining"]))
        self.assertEqual(len(state["remaining"]), 12)
        for index in range(12):
            old = deepcopy(state)
            step = service.visit(state)
            self.assertEqual(step["done"], index == 11)
            state = step["state"]
            self.assertEqual(len(state["results"]), index + 1)
            with self.assertRaises(ValueError):
                service.visit(old)
        self.assertEqual(
            [r["method"] for r in state["results"] if r["status"] == "failure"],
            outcomes(self.oracle)["failures"],
        )
        self.assertEqual(
            [r["method"] for r in state["results"] if r["status"] == "error"],
            outcomes(self.oracle)["errors"],
        )
        self.assertTrue(any(r["status"] == "success" for r in state["results"]))
        with self.assertRaises(ValueError):
            service.visit(state)
        final = service.finish(state, prepared["boundary"])["result"]
        self.assertEqual(final["ok"], self.oracle.wasSuccessful())
        self.assertEqual(final["returncode"], 0 if self.oracle.wasSuccessful() else 1)
        self.assertIn("Ran 12 tests", final["stderr"])
        self.assertFalse(service.sessions)
        self.assertTrue(final["write_audit"]["ok"], final)
        self.assertFalse(service.prepare(CONTEXT, ["unexpected"])["execute"])
        # Actual write audit rejects a real undeclared file. No source calls mocked.
        service = NormalizedTestTools()
        prepared = service.prepare(CONTEXT, [])
        state = service.initialize(prepared["boundary"])["state"]
        while state["remaining"]:
            state = service.visit(state)["state"]
        with tempfile.NamedTemporaryFile(
            dir=ROOT, prefix="normalized-audit-", suffix=".txt"
        ) as file:
            final = service.finish(state, prepared["boundary"])["result"]
            self.assertEqual(final["status"], "undeclared_writes")
            self.assertFalse(final["ok"])
            self.assertIn(
                Path(file.name).name, final["write_audit"]["unexpected_paths"]
            )

    def test_registered_lunar_prism_path(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = self.document
        self.assertEqual(
            document["id"], "hub_control_normalized_workflows_tests_workflow"
        )
        self.assertEqual(document["lifecycle"], "active")
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        failure = None
        async with manager.open(
            "normalized-tests",
            StdioConfig(
                command=sys.executable,
                args=[
                    "-B",
                    "-c",
                    'import sys;sys.path[:0]=["scripts","."];from mcp_server import mcp;mcp.run(transport="stdio")',
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

                def compiled(doc):
                    assets = snapshot(doc)
                    w = compile_workflow(
                        "mcp:normalized-tests",
                        workflow_documents([DESCRIPTOR], assets)[0],
                        inventory,
                    )
                    self.assertTrue(w["runnable"], w["diagnostics"])
                    self.assertTrue(w["runtime_source"])
                    self.assertEqual(set(w["bindings"]), set(doc["operations"]))
                    return w, assets

                workflow, assets = compiled(document)
                absent = deepcopy(document)
                absent["operations"]["visit_test"]["execution"]["binding"][
                    "target"
                ] = "unregistered_tool"
                rejected = compile_workflow(
                    "mcp:normalized-tests",
                    workflow_documents([DESCRIPTOR], snapshot(absent))[0],
                    inventory,
                )
                self.assertFalse(rejected["runnable"])
                self.assertTrue(rejected["diagnostics"])

                async def authorize():
                    pass

                async def run(doc=None, dry=False, extra=None):
                    w, a = compiled(doc) if doc else (workflow, assets)
                    return await execute(
                        w,
                        a,
                        {
                            "context": {**CONTEXT, "dry_run": dry},
                            "extra_args": extra or [],
                        },
                        remote,
                        authorize,
                    )

                dry = await run(dry=True)
                self.assertEqual(dry["status"], "accepted", dry)
                self.assertEqual(dry["outputs"]["result"]["status"], "dry_run")
                self.assertEqual(
                    [c["operation"] for c in dry["calls"]],
                    ["prepare", "initialize_suite", "retain_state", "early_result"],
                )
                bad = await run(extra=["unexpected"])
                self.assertEqual(bad["status"], "accepted", bad)
                self.assertFalse(bad["outputs"]["result"]["ok"])
                self.assertTrue(bad["outputs"]["result"]["preflight_errors"])
                self.assertEqual(len(bad["calls"]), 4)
                result = await run()
                self.assertEqual(result["status"], "accepted", result)
                payload = result["outputs"]["result"]
                self.assertEqual(payload["ok"], self.oracle.wasSuccessful(), payload)
                self.assertEqual(
                    payload["returncode"], 0 if self.oracle.wasSuccessful() else 1
                )
                self.assertIn("Ran 12 tests", payload["stderr"])
                for method in outcomes(self.oracle)["failures"]:
                    self.assertIn("FAIL: " + method, payload["stderr"])
                for method in outcomes(self.oracle)["errors"]:
                    self.assertIn("ERROR: " + method, payload["stderr"])
                self.assertTrue(payload["write_audit"]["ok"])
                self.assertEqual(len(result["calls"]), 15)
                self.assertEqual(
                    sum(c["operation"] == "visit_test" for c in result["calls"]), 12
                )
                self.assertTrue(result["runtime"]["effect_records"])
                self.assertTrue(result["runtime"]["provenance"])
                self.assertTrue(result["replay_artifacts"])
                # The actual PRISM bounded loop must fail instead of finalizing partial results.
                bounded = deepcopy(document)
                bounded["flow"]["steps"][2]["max_iterations"] = 1
                result = await run(bounded)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(result["failure_disposition"], "fail")
                self.assertEqual(
                    sum(c["operation"] == "visit_test" for c in result["calls"]), 1
                )
                self.assertFalse(
                    any(c["operation"] == "finish" for c in result["calls"])
                )
                budget = deepcopy(document)
                budget["policy"]["limits"]["max_operation_calls"] = 1
                result = await run(budget)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertIn("budget", json.dumps(result).lower())
                # Invalid transport state fails at the registered callable boundary.
                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        "mathformer_normalized_tests_visit",
                        {
                            "state": {
                                "shared": {"session": "missing"},
                                "remaining": [],
                                "results": [],
                            }
                        },
                    )
                invalid = deepcopy(document)
                invalid["flow"]["steps"][2]["body"]["cases"][0]["body"]["arguments"][
                    "state"
                ] = {
                    "literal": {
                        "shared": {"session": "missing"},
                        "remaining": [],
                        "results": [],
                    }
                }
                result = await run(invalid)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(
                    [c["operation"] for c in result["calls"]],
                    ["prepare", "initialize_suite", "visit_test"],
                )
                timed = deepcopy(document)
                timed["policy"]["limits"]["wall_time_seconds"] = 1
                w, a = compiled(timed)

                async def stalled_authority():
                    await asyncio.Event().wait()

                with self.assertRaises(TimeoutError):
                    await execute(
                        w,
                        a,
                        {"context": CONTEXT, "extra_args": []},
                        remote,
                        stalled_authority,
                    )
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
