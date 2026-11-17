#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Offline real-source/MCP/PRISM compiler/runtime fixtures for adoption:validate.

No model/provider or external compiler is invoked by this workflow. Nothing in
its source or the Lunar compiler/runtime is replaced. Fixtures are input files.
"""

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

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_adoption_validate_workflow/workflow.yaml"


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
    native = source()
    path = ROOT / "tests/mcp/fixtures/adoption_validate_original.py.txt"
    spec = importlib.util.spec_from_loader(
        "adoption_validate_oracle",
        SourceFileLoader("adoption_validate_oracle", str(path)),
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.ROOT = ROOT
    module.local_path.__defaults__ = (ROOT,)
    module.validate_metadata.__defaults__ = (ROOT,)
    module.load_contract.__defaults__ = (native.METADATA,)
    return module


def cli(module, path):
    defaults = module.load_contract.__defaults__
    module.load_contract.__defaults__ = (path,)
    out = io.StringIO()
    try:
        with redirect_stdout(out):
            code = module.main(["validate"])
        return {"returncode": code, "json": json.loads(out.getvalue())}
    finally:
        module.load_contract.__defaults__ = defaults


def fixtures(data):
    # Real checked source paths, Python/hub/PRISM binding branches, and skill /
    # workflow reasoning mappings are retained from the authored native input.
    yield "all-binding-kinds", data
    one = deepcopy(data)
    one["surfaces"] = one["surfaces"][:1]
    yield "one-surface", one
    for name in [
        "roots",
        "schema-type",
        "unknown-field",
        "empty-surfaces",
        "duplicate-surface",
        "duplicate-operation",
        "alias-collision",
        "duplicate-alias",
        "adapter",
        "symbol",
        "authority",
        "reasoning",
        "source-path",
        "hub-action",
        "io",
        "writes",
        "prism-authority",
    ]:
        value = deepcopy(data)
        surface = value["surfaces"][0]
        op = surface["operations"][0]
        if name == "roots":
            value["canonical_roots"] = ["changed"]
        elif name == "schema-type":
            value["schema_version"] = True
        elif name == "unknown-field":
            value["unknown"] = 1
        elif name == "empty-surfaces":
            value["surfaces"] = []
        elif name == "duplicate-surface":
            value["surfaces"].append(deepcopy(surface))
        elif name == "duplicate-operation":
            surface["operations"].append(deepcopy(op))
        elif name == "alias-collision":
            op["aliases"].append(op["id"])
        elif name == "duplicate-alias":
            op["aliases"].extend(["same-alias", "same-alias"])
        elif name == "adapter":
            op["binding"]["symbol"] = "wrong_adapter"
        elif name == "symbol":
            op["id"] = "fixture:no-adapter"
            op["binding"]["symbol"] = "not_a_callable"
        elif name == "authority":
            op["outputs"]["authority"] += "_changed"
        elif name == "reasoning":
            op["typing"]["sources"]["reasoning_method"] += "_missing"
        elif name == "source-path":
            op["typing"]["sources"]["reasoning_method"] = "../escape#fragment"
        elif name == "hub-action":
            op = next(
                o
                for s in value["surfaces"]
                for o in s["operations"]
                if o["binding"]["kind"] == "hub_action"
            )
            op["id"] = "fixture:no-adapter"
            op["binding"]["action_id"] = "missing:action"
        elif name == "io":
            op["inputs"]["description"] = ""
        elif name == "writes":
            op["outputs"]["writes"] = ["artifacts/fixture"]
        elif name == "prism-authority":
            op = next(
                o
                for s in value["surfaces"]
                for o in s["operations"]
                if o["binding"]["kind"] == "prism_entrypoint"
            )
            op["typing"]["authority_profile"] = "decision_authority"
        yield name, value


class AdoptionValidationTests(unittest.TestCase):
    def test_real_source_equivalence_and_schema_branches(self):
        original, native = oracle(), source()
        data = native.read_metadata()
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "metadata.json"
            for name, value in fixtures(data):
                with self.subTest(name=name):
                    path.write_text(json.dumps(value))
                    before = path.read_bytes()
                    self.assertEqual(cli(original, path), cli(native, path))
                    self.assertEqual(path.read_bytes(), before)
                    if name not in ("all-binding-kinds", "one-surface"):
                        self.assertEqual(cli(native, path)["returncode"], 2)
            for raw in ("{", "null", "[]", "{}"):
                path.write_text(raw)
                self.assertEqual(cli(original, path), cli(native, path))
            path.unlink()
            self.assertEqual(cli(original, path), cli(native, path))
        # Parser failure stays outside the native handler; no error JSON emitted.
        for module in (original, native):
            out, err = io.StringIO(), io.StringIO()
            with (
                redirect_stdout(out),
                redirect_stderr(err),
                self.assertRaises(SystemExit),
            ):
                module.main(["validate", "--bad"])
            self.assertEqual(out.getvalue(), "")
            self.assertIn("unrecognized arguments", err.getvalue())
        # Source library still returns tuples and independent sets/indexes.
        self.assertEqual(
            original.validate_metadata(data), native.validate_metadata(data)
        )
        state = native.metadata_initialize(data)
        self.assertEqual(state["identities"], set())
        for position in range(len(data["surfaces"])):
            self.assertEqual(state["position"], position)
            native.metadata_check_surface(state)
            self.assertEqual(
                native.metadata_advance(state), position == len(data["surfaces"]) - 1
            )
        self.assertEqual(native.metadata_finish(state), native.validate_metadata(data))
        # Descriptor domain bound is absent in the native library: 4097 valid
        # finite workflow surfaces still validate with the real schema/checks.
        large = large_fixture(data, 4097)
        self.assertEqual(len(native.validate_metadata(large)["operations"]), 4097)

    def test_registered_mcp_tools_and_real_lunar_execution(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_adoption_validate_workflow")
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 8195},
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        self.assertEqual(
            document,
            json.loads(
                (
                    ROOT
                    / "skills/control/workflow-contract-validator/references/adoption-validate.workflow.json"
                ).read_text()
            ),
        )
        data = source().read_metadata()
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        async with manager.open(
            "adoption-validation",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {},
        ) as remote:
            tools = [
                t.model_dump(by_alias=True, exclude_none=True)
                for t in await remote.tools()
            ]

            def compile(doc, inventory=None):
                assets = snapshot(doc)
                compiled = compile_workflow(
                    "mcp:adoption-validation",
                    workflow_documents([DESCRIPTOR], assets)[0],
                    tools if inventory is None else inventory,
                )
                return compiled, assets

            workflow, assets = compile(document)
            self.assertTrue(workflow["runnable"], workflow["diagnostics"])
            self.assertTrue(workflow["runtime_source"])
            self.assertEqual(set(workflow["bindings"]), set(document["operations"]))
            absent, _ = compile(document, [])
            self.assertFalse(absent["runnable"])

            async def authorize():
                pass

            async def run(inputs, doc=None):
                compiled, received = compile(doc) if doc else (workflow, assets)
                self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                return await execute(compiled, received, inputs, remote, authorize)

            with tempfile.TemporaryDirectory(dir=ROOT) as directory:
                path = Path(directory) / "metadata.json"
                for name, value in fixtures(data):
                    with self.subTest(runtime=name):
                        path.write_text(json.dumps(value))
                        result = await run({"metadata_path": str(path)})
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertEqual(
                            result["outputs"], {"result": cli(source(), path)}
                        )
                        self.assertEqual(
                            result["calls"][-1]["tool"], "mathformer_validate_finish"
                        )
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["replay_artifacts"])
                        if name in (
                            "all-binding-kinds",
                            "one-surface",
                            "alias-collision",
                        ):
                            self.assertEqual(
                                len(result["calls"]), 3 + 2 * len(value["surfaces"])
                            )
                        if name in (
                            "duplicate-operation",
                            "duplicate-alias",
                            "adapter",
                        ):
                            self.assertEqual(
                                len(result["calls"]), 5
                            )  # no second source body
                for raw in ("{", "null", "[]", "{}"):
                    path.write_text(raw)
                    result = await run({"metadata_path": str(path)})
                    self.assertEqual(result["outputs"], {"result": cli(source(), path)})
                    self.assertEqual(len(result["calls"]), 5)
                path.unlink()
                result = await run({"metadata_path": str(path)})
                self.assertEqual(result["outputs"], {"result": cli(source(), path)})
                # Directory read is not among the CLI's caught errors.
                result = await run({"metadata_path": directory})
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(len(result["calls"]), 1)
                # An uncaught source AST error stops at the current surface;
                # no advance or finish operation may run afterward.
                broken = Path(directory) / "broken.py"
                broken.write_text("def invalid(:\n")
                invalid = deepcopy(data)
                op = invalid["surfaces"][0]["operations"][0]
                op["id"] = "fixture:syntax"
                op["binding"]["path"] = str(broken.relative_to(ROOT))
                path.write_text(json.dumps(invalid))
                result = await run({"metadata_path": str(path)})
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(
                    [c["tool"] for c in result["calls"]],
                    [
                        "mathformer_validate_load",
                        "mathformer_validate_initialize",
                        "mathformer_validate_check_surface",
                    ],
                )
                # Inspect actual transported state and independent invocations.
                path.write_text(json.dumps(data))
                loaded = await remote.call(
                    "mathformer_validate_load", {"metadata_path": str(path)}
                )
                first = (await remote.call("mathformer_validate_initialize", loaded))[
                    "state"
                ]
                self.assertEqual(first["position"], 0)
                self.assertEqual(first["identities"], [])
                checked = (
                    await remote.call(
                        "mathformer_validate_check_surface", {"state": first}
                    )
                )["state"]
                self.assertEqual(checked["position"], 0)
                self.assertEqual(checked["identities"], [data["surfaces"][0]["id"]])
                self.assertEqual(
                    set(checked["operations"]),
                    {o["id"] for o in data["surfaces"][0]["operations"]},
                )
                advanced = await remote.call(
                    "mathformer_validate_advance_guard", {"state": checked}
                )
                self.assertEqual(advanced["state"]["position"], 1)
                self.assertFalse(advanced["done"])
                second = (await remote.call("mathformer_validate_initialize", loaded))[
                    "state"
                ]
                self.assertEqual(second["identities"], [])
                # Last valid domain iteration stops exactly at 4096. This tests
                # the actual advance tool without 8192 redundant MCP calls.
                last = {
                    **checked,
                    "data": {"surfaces": [None] * 4096},
                    "position": 4095,
                }
                end = await remote.call(
                    "mathformer_validate_advance_guard", {"state": last}
                )
                self.assertTrue(end["done"])
                self.assertEqual(end["state"]["position"], 4096)
                path.write_text(json.dumps(large_fixture(data, 4097)))
                oversized = await run({"metadata_path": str(path)})
                self.assertEqual(oversized["outputs"]["result"]["returncode"], 2)
                self.assertIn("4096", oversized["outputs"]["result"]["json"]["error"])
                # Lower fixture bounds exercise real exhaustion and exact-bound
                # success using the unchanged registered tools/source bodies.
                path.write_text(json.dumps(data))
                bounded = deepcopy(document)
                bounded["flow"]["steps"][2]["max_iterations"] = 1
                result = await run({"metadata_path": str(path)}, bounded)
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(result["failure_disposition"], "fail")
                self.assertIsNone(result["outputs"])
                self.assertEqual(len(result["calls"]), 4)
                one = deepcopy(data)
                one["surfaces"] = one["surfaces"][:1]
                path.write_text(json.dumps(one))
                result = await run({"metadata_path": str(path)}, bounded)
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(result["outputs"], {"result": cli(source(), path)})
                budget = deepcopy(document)
                budget["policy"]["limits"]["max_operation_calls"] = 2
                result = await run({"metadata_path": str(path)}, budget)
                self.assertEqual(result["status"], "failed")
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in result["calls"]
                    ),
                    2,
                )
                self.assertIn("budget", result["calls"][-1]["error"].lower())
                timed = deepcopy(document)
                timed["policy"]["limits"]["wall_time_seconds"] = 1
                timed_workflow, timed_assets = compile(timed)

                async def pending_authority():
                    await asyncio.Event().wait()

                with self.assertRaises(TimeoutError):
                    await execute(
                        timed_workflow,
                        timed_assets,
                        {"metadata_path": str(path)},
                        remote,
                        pending_authority,
                    )

        self.assertFalse(manager.active)


def large_fixture(data, count):
    # A real workflow owner and Python callable, without an explicit-adapter id.
    # Its canonical workflow reasoning fragment exists in the native taxonomy.
    result = deepcopy(data)
    prototype = deepcopy(next(s for s in data["surfaces"] if s["kind"] == "workflow"))
    operation = deepcopy(data["surfaces"][0]["operations"][0])
    workflow_op = prototype["operations"][0]
    operation["typing"]["reasoning_method"] = workflow_op["typing"]["reasoning_method"]
    operation["typing"]["sources"]["reasoning_method"] = workflow_op["typing"][
        "sources"
    ]["reasoning_method"]
    # Small existing Python source keeps large finite traversal practical.
    operation["binding"] = {
        "kind": "python_function",
        "path": "scripts/adoption_validate_tools.py",
        "symbol": "register_adoption_validate_tools",
    }
    operation["typing"]["invocation_mechanism"] = "python_function"
    result["surfaces"] = []
    for i in range(count):
        surface = deepcopy(prototype)
        surface["id"] = f"fixture_{i}_workflow"
        op = deepcopy(operation)
        op["id"] = f"fixture:operation_{i}"
        op["aliases"] = []
        surface["operations"] = [op]
        result["surfaces"].append(surface)
    return result


if __name__ == "__main__":
    unittest.main(verbosity=2)
