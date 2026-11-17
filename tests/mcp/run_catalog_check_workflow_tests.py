#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic native/MCP/Lunar integration; no providers or external compilers."""

from tempfile import gettempdir
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
# Use Lunar's installed runtime dependencies without changing the project env.
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.path[:0] = [str(LUNAR / "app/backend"), str(ROOT / "scripts")]

import asyncio
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
import yaml

from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute
from catalog_check_tools import source

CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_adoption_catalog_check_workflow/workflow.yaml"


def asset(path, text):
    return {
        "path": path,
        "content": text,
        "encoding": "text",
        "sha256": hashlib.sha256(text.encode()).hexdigest(),
    }


def snapshot(document):
    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(row["path"], (ROOT / row["path"]).read_text())
        for row in document["provenance"]["sources"]
    ]


def load_original():
    # The pre-extraction selected source is an immutable test oracle.
    path = ROOT / "tests/mcp/fixtures/catalog_check_original.py.txt"
    from importlib.machinery import SourceFileLoader

    spec = importlib.util.spec_from_loader(
        "catalog_original_oracle",
        SourceFileLoader("catalog_original_oracle", str(path)),
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    # The backup lives at a different depth: supply the original repository context.
    module.ROOT = ROOT
    module.validate_metadata.__defaults__ = (ROOT,)
    module.local_path.__defaults__ = (ROOT,)
    return module


class CatalogCheckTests(unittest.TestCase):
    def test_native_steps_and_cli_oracle(self):
        native = source()
        data = json.loads(native.METADATA.read_text())
        expected = native.catalog_text(data)
        original = load_original()
        self.assertEqual(original.catalog_text(data), expected)
        self.assertTrue(expected.endswith("\n"))
        # Authored operation order and escaping are observable, including empty aliases.
        first = data["surfaces"][0]["operations"][0]["id"]
        self.assertIn(first, expected.splitlines()[8])
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            directory = Path(directory)
            metadata = directory / "metadata.json"
            catalog = directory / "catalog.md"
            metadata.write_text(json.dumps(data))
            for module in [original, native]:
                old_catalog, defaults = (
                    module.CATALOG,
                    module.load_contract.__defaults__,
                )
                module.CATALOG = catalog
                module.load_contract.__defaults__ = (metadata,)
                try:
                    for content in [None, expected + " ", expected]:
                        if content is None:
                            catalog.unlink(missing_ok=True)
                        else:
                            catalog.write_text(content)
                        stdout = io.StringIO()
                        with redirect_stdout(stdout):
                            code = module.main(["catalog", "--check"])
                        value = json.loads(stdout.getvalue())
                        self.assertEqual(code, 0 if content == expected else 2)
                        self.assertEqual(
                            value,
                            (
                                {
                                    "ok": True,
                                    "path": str(catalog.relative_to(ROOT)),
                                    "checked": True,
                                }
                                if code == 0
                                else {
                                    "ok": False,
                                    "error": "generated pilot catalog is stale",
                                }
                            ),
                        )
                    metadata.write_text("{")
                    with redirect_stdout(io.StringIO()) as stdout:
                        self.assertEqual(module.main(["catalog", "--check"]), 2)
                    self.assertFalse(json.loads(stdout.getvalue())["ok"])
                    metadata.write_text(json.dumps(data))
                finally:
                    module.CATALOG, module.load_contract.__defaults__ = (
                        old_catalog,
                        defaults,
                    )
        with self.assertRaises(IsADirectoryError):
            native.catalog_is_stale("", ROOT)
        with self.assertRaises(ValueError):
            native.validate_metadata({"schema_version": 3})

    def test_registered_tools_compile_and_execute(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(document["id"], "hub_adoption_catalog_check_workflow")
        self.assertEqual(document["policy"]["limits"]["max_operation_calls"], 4)
        assets = snapshot(document)
        manager = SessionManager()
        # Import the production registration directly; no server config or credentials.
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        async with manager.open(
            "catalog",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {},
        ) as remote:
            failure = None
            try:
                tools = [
                    tool.model_dump(by_alias=True, exclude_none=True)
                    for tool in await remote.tools()
                ]
                workflow = compile_workflow(
                    "mcp:catalog", workflow_documents([DESCRIPTOR], assets)[0], tools
                )
                self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                self.assertTrue(workflow["runtime_source"])
                self.assertEqual(set(workflow["bindings"]), set(document["operations"]))

                async def authorize():
                    pass

                async def run(inputs, doc=None):
                    if doc is None:
                        return await execute(
                            workflow, assets, inputs, remote, authorize
                        )
                    received = snapshot(doc)
                    compiled = compile_workflow(
                        "mcp:catalog",
                        workflow_documents([DESCRIPTOR], received)[0],
                        tools,
                    )
                    self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                    return await execute(compiled, received, inputs, remote, authorize)

                with tempfile.TemporaryDirectory(dir=ROOT) as directory:
                    directory = Path(directory)
                    metadata = directory / "metadata.json"
                    catalog = directory / "catalog.md"
                    data = json.loads(source().METADATA.read_text())
                    metadata.write_text(json.dumps(data))
                    generated = source().catalog_text(data)
                    inputs = {
                        "metadata_path": str(metadata),
                        "catalog_path": str(catalog),
                    }
                    for content in [None, generated + "\n", generated]:
                        if content is not None:
                            catalog.write_text(content)
                        result = await run(inputs)
                        self.assertEqual(result["status"], "accepted", result)
                        completion = result["outputs"]["completion"]
                        self.assertEqual(
                            completion["returncode"], 0 if content == generated else 2
                        )
                        self.assertEqual(
                            completion["json"],
                            (
                                {
                                    "ok": True,
                                    "path": str(catalog.relative_to(ROOT)),
                                    "checked": True,
                                }
                                if content == generated
                                else {
                                    "ok": False,
                                    "error": "generated pilot catalog is stale",
                                }
                            ),
                        )
                        self.assertEqual(len(result["calls"]), 4)
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["replay_artifacts"])
                        if content is None:
                            self.assertFalse(catalog.exists())
                        else:
                            self.assertEqual(catalog.read_text(), content)
                    # Native validation rejects on the first error; graph stops after load.
                    for content in ["{", "{}"]:
                        metadata.write_text(content)
                        result = await run(inputs)
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertEqual(
                            result["outputs"]["completion"]["returncode"], 2
                        )
                        self.assertEqual(len(result["calls"]), 2)
                    metadata.unlink()
                    result = await run(inputs)
                    self.assertEqual(result["outputs"]["completion"]["returncode"], 2)
                    self.assertEqual(len(result["calls"]), 2)
                    metadata.write_text(json.dumps(data))
                    # Non-caught native I/O errors propagate, with no terminal success or retry.
                    result = await run({**inputs, "catalog_path": str(directory)})
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(len(result["calls"]), 3)
                    # Real runtime budget fails before a fourth MCP call.
                    bounded = deepcopy(document)
                    bounded["policy"]["limits"]["max_operation_calls"] = 3
                    result = await run(inputs, bounded)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(len(result["calls"]), 4)
                    self.assertEqual(
                        sum(
                            bool(call.get("transport_call_performed"))
                            for call in result["calls"]
                        ),
                        3,
                    )
                    self.assertEqual(result["calls"][-1]["status"], "rejected")
                    self.assertIn("budget", json.dumps(result).lower())
                    # Advertised render/compare interfaces also exercise caught step failures.
                    loaded = await remote.call(
                        "mathformer_catalog_load", {"metadata_path": str(metadata)}
                    )
                    self.assertEqual(loaded["data"], data)
                    rendered_ok = await remote.call(
                        "mathformer_catalog_render", {"data": loaded["data"]}
                    )
                    self.assertEqual(rendered_ok["text"], generated)
                    self.assertTrue(rendered_ok["ok"])
                    rendered = await remote.call(
                        "mathformer_catalog_render", {"data": {}}
                    )
                    self.assertFalse(rendered["ok"])
                    self.assertEqual(rendered["completion"]["returncode"], 2)
                    compared = await remote.call(
                        "mathformer_catalog_compare",
                        {
                            "text": "",
                            "catalog_path": str(
                                Path(gettempdir())
                                / "mathformer-test-fixtures/outside-repository"
                            ),
                        },
                    )
                    self.assertFalse(compared["ok"])
                timed = deepcopy(document)
                timed["policy"]["limits"]["wall_time_seconds"] = 1
                timed_assets = snapshot(timed)
                timed_workflow = compile_workflow(
                    "mcp:catalog",
                    workflow_documents([DESCRIPTOR], timed_assets)[0],
                    tools,
                )
                self.assertTrue(
                    timed_workflow["runnable"], timed_workflow["diagnostics"]
                )

                async def wait_for_authority():
                    await asyncio.Event().wait()

                with self.assertRaises(TimeoutError):
                    await execute(
                        timed_workflow, timed_assets, {}, remote, wait_for_authority
                    )
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure is not None:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
