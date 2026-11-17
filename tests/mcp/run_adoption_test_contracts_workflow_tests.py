#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native suite parity and real MCP/Lunar/PRISM bounded execution."""

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
from copy import deepcopy
import hashlib
import io
import json
import re
import unittest
import yaml
from adoption_tests_boundary import SuiteBoundary
from adoption_test_contracts_tools import AdoptionTestTools
import mathformer as hub
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_adoption_test_contracts_workflow/workflow.yaml"
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


class AdoptionWorkflowTests(unittest.TestCase):
    maxDiff = None

    def test_original_entrypoint_parity_and_shared_steps(self):
        with SuiteBoundary() as fixture:
            # Execute the frozen original class under the same compiler fixture.
            oracle = type(sys)("adoption_original_oracle")
            oracle.__file__ = str(ROOT / "tests/control/test_portable_adoption.py")
            sys.modules[oracle.__name__] = oracle
            exec(
                compile(
                    (
                        ROOT / "tests/mcp/fixtures/adoption_tests_original.py.txt"
                    ).read_text(),
                    oracle.__file__,
                    "exec",
                ),
                oracle.__dict__,
            )
            original_stream = io.StringIO()
            expected = unittest.TextTestRunner(stream=original_stream).run(
                unittest.defaultTestLoader.loadTestsFromTestCase(oracle.AdoptionTests)
            )
            self.assertTrue(expected.wasSuccessful(), original_stream.getvalue())
            self.assertEqual(expected.testsRun, 11)
            self.assertEqual(expected.skipped, [])
            tools = AdoptionTestTools()
            boundary = tools.prepare(CONTEXT)["boundary"]
            initialized = tools.initialize(boundary)
            self.assertTrue(initialized["ready"])
            state = initialized["state"]
            self.assertEqual(len(state["remaining"]), 11)
            self.assertEqual(state["remaining"], sorted(state["remaining"]))
            for index in range(11):
                case = tools.run(state)["test"]
                self.assertEqual(case["status"], "success", case)
                advanced = tools.advance(state, case)
                self.assertEqual(advanced["done"], index == 10)
                self.assertEqual(len(advanced["state"]["results"]), index + 1)
                state = advanced["state"]
            with self.assertRaises(ValueError):
                tools.run(state)
            result = tools.finish(boundary, state)["result"]
            self.assertTrue(result["ok"], result)
            self.assertEqual(result["returncode"], 0)

            def normalize(text):
                return re.sub(r"Ran 11 tests in [\d.]+s", "Ran 11 tests in TIME", text)

            self.assertEqual(
                normalize(result["stderr"]), normalize(original_stream.getvalue())
            )
            self.assertFalse(tools.sessions)
            # The optional-runtime skip remains a recorded native test outcome.
            fixture.compiler.mode = "missing"
            skipped_module = type(sys)("adoption_no_compiler")
            skipped_module.__file__ = str(
                ROOT / "tests/control/test_portable_adoption.py"
            )
            sys.modules[skipped_module.__name__] = skipped_module
            exec(
                compile(
                    Path(skipped_module.__file__).read_text(),
                    skipped_module.__file__,
                    "exec",
                ),
                skipped_module.__dict__,
            )
            stream = io.StringIO()
            skipped = unittest.TextTestRunner(stream=stream).run(
                unittest.defaultTestLoader.loadTestsFromModule(skipped_module)
            )
            self.assertTrue(skipped.wasSuccessful(), stream.getvalue())
            self.assertEqual(skipped.testsRun, 11)
            self.assertEqual(len(skipped.skipped), 1)
            self.assertEqual(
                skipped.skipped[0][1], "adjacent PRISM runtime unavailable"
            )
            fixture.compiler.mode = "success"
            # Preflight rejects extra args without launching a suite.
            item = hub.build_registry()["adoption:test-contracts"]
            failed = hub.prepare_leaf_boundary(item, hub.RunContext(), ["--extra"])
            self.assertFalse(failed["execute"])
            self.assertFalse(failed["payload"]["ok"])
            # Native write audit uses real temporary files, even after success.
            b = tools.prepare(CONTEXT)["boundary"]
            init = tools.initialize(b)
            state = init["state"]
            while state["remaining"]:
                state = tools.advance(state, tools.run(state)["test"])["state"]
            (fixture.root / "undeclared.txt").write_text("compiler artifact")
            r = tools.finish(b, state)["result"]
            self.assertEqual(r["status"], "undeclared_writes")
            self.assertFalse(r["ok"])
            self.assertIn("undeclared.txt", r["write_audit"]["unexpected_paths"])

    def test_registered_mcp_lunar_prism_execution(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_adoption_test_contracts_workflow")
        self.assertEqual(document["lifecycle"], "active")
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        server = 'import sys;sys.path[:0]=["scripts","tests/mcp/fixtures"];from adoption_tests_boundary import serve;serve()'
        async with manager.open(
            "adoption-tests",
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
                    workflow = compile_workflow(
                        "mcp:adoption-tests",
                        workflow_documents([DESCRIPTOR], assets)[0],
                        inventory,
                    )
                    self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                    self.assertTrue(workflow["runtime_source"])
                    self.assertEqual(set(workflow["bindings"]), set(doc["operations"]))
                    return workflow, assets

                workflow, assets = compile(document)

                async def authorize():
                    pass

                async def run(doc=None, dry=False):
                    w, a = compile(doc) if doc else (workflow, assets)
                    return await execute(
                        w,
                        a,
                        {"context": {**CONTEXT, "dry_run": dry}},
                        remote,
                        authorize,
                    )

                result = await run(dry=True)
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(result["outputs"]["result"]["status"], "dry_run")
                self.assertEqual(
                    [c["operation"] for c in result["calls"]],
                    [
                        "prepare_boundary",
                        "initialize_suite",
                        "setup_failed",
                        "early_result",
                    ],
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
                    sum(c["operation"] == "run_test" for c in result["calls"]), 11
                )
                self.assertTrue(result["runtime"]["effect_records"])
                self.assertTrue(result["runtime"]["provenance"])
                self.assertTrue(result["replay_artifacts"])
                # An external compiler error becomes a native unittest error;
                # all later cases still run and the suite exits unsuccessfully.
                await remote.call(
                    "test_adoption_suite_boundary", {"mode": "compiler_failure"}
                )
                result = await run()
                self.assertEqual(result["status"], "accepted", result)
                self.assertFalse(result["outputs"]["result"]["ok"])
                self.assertEqual(result["outputs"]["result"]["returncode"], 1)
                self.assertIn("Ran 11 tests", result["outputs"]["result"]["stderr"])
                self.assertEqual(
                    sum(c["operation"] == "run_test" for c in result["calls"]), 11
                )
                # Bad class input follows setup_failed without executing any case.
                await remote.call(
                    "test_adoption_suite_boundary", {"mode": "setup_failure"}
                )
                result = await run()
                self.assertEqual(result["status"], "accepted", result)
                self.assertFalse(result["outputs"]["result"]["ok"])
                self.assertEqual(result["outputs"]["result"]["returncode"], 1)
                self.assertEqual(
                    [c["operation"] for c in result["calls"]],
                    [
                        "prepare_boundary",
                        "initialize_suite",
                        "setup_failed",
                        "finish_boundary",
                    ],
                )
                await remote.call("test_adoption_suite_boundary", {"mode": "success"})
                # Exhaustion stops before finalization; no partial successful result.
                bounded = deepcopy(document)
                loop = bounded["flow"]["steps"][2]
                loop["max_iterations"] = 1
                result = await run(bounded)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(result["failure_disposition"], "fail")
                self.assertEqual(
                    sum(c["operation"] == "run_test" for c in result["calls"]), 1
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
