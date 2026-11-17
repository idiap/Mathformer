#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Real native steps, registered MCP tools and Lunar PRISM compilation/runtime."""

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
]
import asyncio
from copy import deepcopy
import hashlib
import json
import tempfile
import unittest
import warnings
import yaml
from catalog_check_tools import source
from invoke_compiler_boundary import CompilerBoundary
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_adoption_invoke_workflow/workflow.yaml"


def snapshot(document):
    def asset(path, text):
        return {
            "path": path,
            "content": text,
            "encoding": "text",
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
        }

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(row["path"], (ROOT / row["path"]).read_text())
        for row in document["provenance"]["sources"]
    ]


def oracle():
    scope = dict(vars(source()))
    exec(
        (ROOT / "tests/mcp/fixtures/adoption_invoke_original.py.txt").read_text(), scope
    )
    return scope["invoke"]


class InvokeTests(unittest.TestCase):
    maxDiff = None

    def test_original_and_shared_steps(self):
        native = source()
        with (
            CompilerBoundary(native) as compiler,
            tempfile.TemporaryDirectory() as directory,
        ):
            original = oracle()
            log = Path(directory) / "log.jsonl"
            log.write_text("")
            cases = [
                (
                    "router:resolve",
                    {"request": "validate portable repository adoption"},
                ),
                (
                    "router:resolve",
                    {"request": "validate", "limit": 1, "family": "control"},
                ),
                ("control:workflow-contract", {}),
                ("control:reasoning-log-summary", {"log_file": str(log)}),
                ("reasoning-log:validate", {"log_file": str(log)}),
                ("artifact_acceptance_loop:public", {}),
                ("artifact_acceptance_loop:material", {}),
            ]
            for identity, inputs in cases:
                compiler.mode = "success"
                expected = original(identity, inputs)
                prepared = native.prepare_invocation(identity, inputs)
                self.assertIs(prepared["inputs"], inputs)
                self.assertEqual(prepared["oid"], identity)
                self.assertEqual(native.execute_invocation(prepared), expected)
                self.assertEqual(native.invoke(identity, inputs), expected)
            for identity, inputs, error in [
                ("missing", {}, ValueError),
                ("router:resolve", [], ValueError),
                ("router:resolve", {"extra": 1}, ValueError),
                ("router:resolve", {}, ValueError),
                ("reasoning-log:validate", {"log_file": 3}, ValueError),
            ]:
                for fn in [original, native.invoke]:
                    with self.assertRaises(error):
                        fn(identity, inputs)
            for mode, count, error in [
                ("missing", 0, FileNotFoundError),
                ("run_fail", 1, RuntimeError),
                ("verify_fail", 2, RuntimeError),
            ]:
                compiler.mode = mode
                for fn in [original, native.invoke]:
                    compiler.calls.clear()
                    with self.assertRaises(error):
                        fn("artifact_acceptance_loop:public", {})
                    self.assertEqual(len(compiler.calls), count)
            # Native recording remains best effort and restores inherited context.
            import adoption_provenance as provenance

            compiler.mode = "success"
            target = Path(directory) / "receipts"
            token = provenance._CURRENT.set("parent")
            try:
                result = native.invoke(
                    "router:resolve", {"request": "validate"}, target
                )
                self.assertEqual(provenance._CURRENT.get(), "parent")
                receipt = next(target.iterdir())
                self.assertEqual(
                    provenance.validate_invocation(receipt)["status"], "complete"
                )
                self.assertEqual(
                    json.loads((receipt / "provenance.json").read_text())[
                        "parent_invocation_id"
                    ],
                    "parent",
                )
                blocked = Path(directory) / "file"
                blocked.write_text("no directory")
                with warnings.catch_warnings(record=True) as caught:
                    self.assertEqual(
                        native.invoke(
                            "router:resolve", {"request": "validate"}, blocked
                        ),
                        result,
                    )
                    self.assertTrue(caught)
                with self.assertRaisesRegex(ValueError, "request must be a string"):
                    native.invoke("router:resolve", {}, target)
                self.assertEqual(provenance._CURRENT.get(), "parent")
            finally:
                provenance._CURRENT.reset(token)

    def test_real_mcp_and_lunar(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_adoption_invoke_workflow")
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(document["policy"]["limits"]["max_operation_calls"], 2)
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        server = 'import sys;sys.path[:0]=["scripts","tests/mcp/fixtures"];from invoke_compiler_boundary import serve;serve()'
        async with manager.open(
            "invoke",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {},
        ) as remote:
            failure = None
            try:
                tools = [
                    tool.model_dump(by_alias=True, exclude_none=True)
                    for tool in await remote.tools()
                ]

                def compile(doc):
                    assets = snapshot(doc)
                    workflow = compile_workflow(
                        "mcp:invoke", workflow_documents([DESCRIPTOR], assets)[0], tools
                    )
                    self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                    self.assertTrue(workflow["runtime_source"])
                    self.assertEqual(set(workflow["bindings"]), set(doc["operations"]))
                    return workflow, assets

                compiled, assets = compile(document)

                async def authorize():
                    pass

                async def run(identity, inputs, doc=None, output=None):
                    workflow, received = compile(doc) if doc else (compiled, assets)
                    return await execute(
                        workflow,
                        received,
                        {"identity": identity, "inputs": inputs, "output_dir": output},
                        remote,
                        authorize,
                    )

                native = source()
                data, index = native.load_contract()
                with (
                    tempfile.TemporaryDirectory() as directory,
                    CompilerBoundary(native),
                ):
                    log = Path(directory) / "log.jsonl"
                    log.write_text("")
                    for oid, inputs, operation in [
                        (
                            "router:resolve",
                            {"request": "validate portable repository adoption"},
                            "router",
                        ),
                        (
                            "router:resolve",
                            {"request": "validate", "limit": 1, "family": "control"},
                            "router",
                        ),
                        ("control:workflow-contract", {}, "hub_action"),
                        (
                            "control:reasoning-log-summary",
                            {"log_file": str(log)},
                            "reasoning_log",
                        ),
                        (
                            "reasoning-log:validate",
                            {"log_file": str(log)},
                            "reasoning_log",
                        ),
                        ("artifact_acceptance_loop:public", {}, "prism_fixture"),
                        ("artifact_acceptance_loop:material", {}, "prism_fixture"),
                    ]:
                        for identity in [oid, *index["operations"][oid][1]["aliases"]]:
                            await remote.call(
                                "test_compiler_boundary", {"mode": "success"}
                            )
                            observed = await run(identity, inputs)
                            self.assertEqual(observed["status"], "accepted", observed)
                            expected = oracle()(identity, inputs)
                            if operation == "hub_action":
                                # Server and client have distinct isolated repository fixtures.
                                self.assertTrue(
                                    Path(observed["outputs"]["result"]["cwd"]).is_dir()
                                )
                                expected["cwd"] = observed["outputs"]["result"]["cwd"]
                            self.assertEqual(observed["outputs"], {"result": expected})
                            self.assertEqual(
                                [c["operation"] for c in observed["calls"]],
                                ["prepare", operation],
                            )
                            self.assertTrue(observed["runtime"]["effect_records"])
                            self.assertTrue(observed["runtime"]["provenance"])
                            self.assertTrue(observed["replay_artifacts"])
                            if operation == "prism_fixture":
                                self.assertFalse(
                                    observed["outputs"]["result"]["backend_verified"]
                                )
                                calls = (
                                    await remote.call(
                                        "test_compiler_boundary", {"mode": "success"}
                                    )
                                )["calls"]
                                self.assertEqual(len(calls), 2)
                                self.assertIn("verify-run", calls[1]["argv"])
                    # A failed native hub action remains a payload, not an exception.
                    await remote.call("test_compiler_boundary", {"mode": "run_fail"})
                    result = await run("control:workflow-contract", {})
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertFalse(result["outputs"]["result"]["ok"])
                    self.assertEqual(result["outputs"]["result"]["returncode"], 4)
                    for mode, count in [
                        ("missing", 0),
                        ("run_fail", 1),
                        ("verify_fail", 2),
                    ]:
                        await remote.call("test_compiler_boundary", {"mode": mode})
                        result = await run("artifact_acceptance_loop:public", {})
                        self.assertEqual(result["status"], "failed", result)
                        self.assertIsNone(result["outputs"])
                        self.assertEqual(len(result["calls"]), 2)
                        calls = (
                            await remote.call(
                                "test_compiler_boundary", {"mode": "success"}
                            )
                        )["calls"]
                        self.assertEqual(len(calls), count)
                    for identity, inputs, count in [
                        ("unknown", {}, 1),
                        ("router:resolve", {"unknown": 1}, 1),
                        ("router:resolve", {}, 2),
                        ("reasoning-log:validate", {}, 2),
                    ]:
                        result = await run(identity, inputs)
                        self.assertEqual(result["status"], "failed", result)
                        self.assertIsNone(result["outputs"])
                        self.assertEqual(len(result["calls"]), count)
                    receipts = Path(directory) / "recorded"
                    result = await run(
                        "router:resolve", {"request": "validate"}, output=str(receipts)
                    )
                    self.assertEqual(result["status"], "accepted", result)
                    import adoption_provenance

                    self.assertEqual(
                        adoption_provenance.validate_invocation(
                            next(receipts.iterdir())
                        )["status"],
                        "complete",
                    )
                    limited = deepcopy(document)
                    limited["policy"]["limits"]["max_operation_calls"] = 1
                    result = await run(
                        "router:resolve", {"request": "validate"}, limited
                    )
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(
                        sum(
                            bool(c.get("transport_call_performed"))
                            for c in result["calls"]
                        ),
                        1,
                    )
                    self.assertIn("budget", json.dumps(result).lower())
                    timed = deepcopy(document)
                    timed["policy"]["limits"]["wall_time_seconds"] = 1
                    timed_workflow, timed_assets = compile(timed)

                    async def wait_for_authority():
                        await asyncio.Event().wait()

                    with self.assertRaises(TimeoutError):
                        await execute(
                            timed_workflow,
                            timed_assets,
                            {
                                "identity": "router:resolve",
                                "inputs": {"request": "validate"},
                                "output_dir": None,
                            },
                            remote,
                            wait_for_authority,
                        )
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
