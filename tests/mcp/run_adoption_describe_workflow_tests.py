#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic real-source/MCP/PRISM tests; no external provider boundaries."""

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
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import tempfile
import unittest
import yaml

from catalog_check_tools import source
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_adoption_describe_workflow/workflow.yaml"


def snapshot(document):
    def asset(path, text):
        return {
            "path": path,
            "content": text,
            "encoding": "text",
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
        }

    schema = "skills/control/workflow-contract-validator/references/portable-adoption.schema.json"
    nullable = "skills/control/workflow-contract-validator/references/portable-adoption-nullable.schema.json"
    return [
        asset(DESCRIPTOR, json.dumps(document)),
        asset(schema, (ROOT / schema).read_text()),
        asset(nullable, (ROOT / nullable).read_text()),
    ] + [
        asset(row["path"], (ROOT / row["path"]).read_text())
        for row in document["provenance"]["sources"]
    ]


class DescribeTests(unittest.TestCase):
    def test_original_cli_equivalence(self):
        path = ROOT / "tests/mcp/fixtures/adoption_describe_original.py.txt"
        spec = importlib.util.spec_from_loader(
            "describe_oracle", SourceFileLoader("describe_oracle", str(path))
        )
        original = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = original
        source()  # initialize the native provenance import path before the oracle
        spec.loader.exec_module(original)
        native = source()
        original.ROOT = ROOT
        original.validate_metadata.__defaults__ = (ROOT,)
        original.local_path.__defaults__ = (ROOT,)
        original.load_contract.__defaults__ = (native.METADATA,)
        data, _ = native.load_contract()
        op = data["surfaces"][0]["operations"][0]
        for args in [
            [op["id"]],
            *[[alias] for alias in op["aliases"]],
            ["unknown"],
            [],
            [op["id"], "--bad"],
        ]:
            observed = []
            for module in [original, native]:
                stdout, stderr = io.StringIO(), io.StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    try:
                        code = module.main(["describe", *args])
                    except SystemExit as error:
                        code = error.code
                observed.append((code, stdout.getvalue(), stderr.getvalue()))
            self.assertEqual(*observed)
        # Resolving twice must not retain identity/alias collision state.
        self.assertEqual(native.resolve(op["id"], data), native.resolve(op["id"], data))
        for mutate in ["duplicate", "collision", "duplicate_alias"]:
            invalid = deepcopy(data)
            operation = invalid["surfaces"][0]["operations"][0]
            if mutate == "duplicate":
                invalid["surfaces"].append(deepcopy(invalid["surfaces"][0]))
            elif mutate == "collision":
                operation["aliases"].append(operation["id"])
            else:
                operation["aliases"].extend(["alias-chain", "alias-chain"])
            with self.assertRaises(ValueError):
                native.resolve(op["id"], invalid)

    def test_registered_tools_and_real_lunar_runtime(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_adoption_describe_workflow")
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(document["policy"]["limits"]["max_operation_calls"], 4)
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        data, _ = source().load_contract()
        surface = data["surfaces"][0]
        op = surface["operations"][0]
        expected = {
            "returncode": 0,
            "json": {"surface": surface["id"], "operation": op},
        }
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        failure = None
        async with manager.open(
            "describe",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {},
        ) as remote:
            try:
                tools = [
                    tool.model_dump(by_alias=True, exclude_none=True)
                    for tool in await remote.tools()
                ]

                def compile(doc):
                    assets = snapshot(doc)
                    compiled = compile_workflow(
                        "mcp:describe",
                        workflow_documents([DESCRIPTOR], assets)[0],
                        tools,
                    )
                    self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                    self.assertTrue(compiled["runtime_source"])
                    self.assertEqual(set(compiled["bindings"]), set(doc["operations"]))
                    return compiled, assets

                workflow, assets = compile(document)

                async def authorize():
                    pass

                async def run(inputs, doc=None):
                    compiled, received = compile(doc) if doc else (workflow, assets)
                    return await execute(compiled, received, inputs, remote, authorize)

                for identity in [op["id"], *op["aliases"]]:
                    result = await run({"extra_args": [identity]})
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(result["outputs"], {"result": expected})
                    self.assertEqual(
                        [call["tool"] for call in result["calls"]],
                        [
                            "mathformer_describe_parse",
                            "mathformer_describe_load",
                            "mathformer_describe_emit",
                        ],
                    )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["runtime"]["provenance"])
                    self.assertTrue(result["replay_artifacts"])
                result = await run({"extra_args": ["unknown"]})
                self.assertEqual(
                    result["outputs"]["result"],
                    {
                        "returncode": 2,
                        "json": {"ok": False, "error": "unknown operation: unknown"},
                    },
                )
                for args in [[], [op["id"], "--bad"], [op["id"], "extra"]]:
                    result = await run({"extra_args": args})
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(len(result["calls"]), 1)
                with tempfile.TemporaryDirectory(dir=ROOT) as directory:
                    path = Path(directory) / "metadata.json"
                    for content in [None, "{", "{}", json.dumps(data)]:
                        if content is not None:
                            path.write_text(content)
                        result = await run(
                            {"extra_args": [op["id"]], "metadata_path": str(path)}
                        )
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertEqual(
                            result["outputs"]["result"]["returncode"],
                            0 if content == json.dumps(data) else 2,
                        )
                        self.assertEqual(len(result["calls"]), 3)
                        self.assertEqual(
                            result["calls"][-1]["tool"],
                            (
                                "mathformer_describe_emit"
                                if content == json.dumps(data)
                                else "mathformer_describe_error"
                            ),
                        )
                    # Unhandled I/O error propagates from native load with no retry.
                    result = await run(
                        {"extra_args": [op["id"]], "metadata_path": directory}
                    )
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(len(result["calls"]), 2)
                # Failed revalidation is caught by the same native describe boundary.
                result = await remote.call(
                    "mathformer_describe_emit", {"identity": op["id"], "metadata": {}}
                )
                self.assertEqual(result["result"]["returncode"], 2)
                bounded = deepcopy(document)
                bounded["policy"]["limits"]["max_operation_calls"] = 2
                result = await run({"extra_args": [op["id"]]}, bounded)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(
                    sum(
                        bool(call.get("transport_call_performed"))
                        for call in result["calls"]
                    ),
                    2,
                )
                self.assertEqual(result["calls"][-1]["status"], "rejected")
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
                        {"extra_args": [op["id"]]},
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
