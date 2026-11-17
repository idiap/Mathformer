#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Offline native catalog, advertised MCP interfaces and real Lunar/PRISM tests.

The workflow is deterministic: there is no model/provider/compiler boundary to
fake. Compiler fixtures vary qualification and bounds, using the real parser,
checker, compiler and runtime for every executable case.
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
sys.path[:0] = [str(LUNAR / "app/backend"), str(ROOT / "scripts")]

import asyncio
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
from importlib.machinery import SourceFileLoader
import importlib.util
import io
import json
import tempfile
import unittest
import yaml

from catalog_check_tools import source, SOURCE
from adoption_catalog_tools import CatalogTools
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_adoption_catalog_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
METADATA = (
    "skills/control/workflow-contract-validator/references/portable-adoption.json"
)
CATALOG = "docs/migrations/portable-repository-adoption/catalog.md"
CONTEXT = dict(
    dry_run=False,
    json_output=True,
    keep_going=False,
    allow_mutating=True,
    write_report=False,
)
CASES = json.loads(
    (ROOT / "tests/mcp/fixtures/adoption_catalog_cases.json").read_text()
)


def snapshot(document):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    paths = {SCHEMA, *[row["path"] for row in document["provenance"]["sources"]]}
    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(p, (ROOT / p).read_text()) for p in sorted(paths)
    ]


def populate(root, mode="success"):
    metadata = root / METADATA
    metadata.parent.mkdir(parents=True)
    metadata.write_text(source().METADATA.read_text())
    catalog = root / CATALOG
    catalog.parent.mkdir(parents=True)
    if mode == "malformed":
        metadata.write_text("{")
    if mode == "invalid":
        metadata.write_text("{}")
    if mode == "missing":
        metadata.unlink()
    if mode == "missing_parent":
        catalog.parent.rmdir()
    if mode == "catalog_directory":
        catalog.mkdir()
    if mode == "metadata_directory":
        metadata.unlink()
        metadata.mkdir()
    return metadata, catalog


def oracle():
    path = ROOT / "tests/mcp/fixtures/adoption_catalog_original.py.txt"
    loader = SourceFileLoader("adoption_catalog_oracle", str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = module
    loader.exec_module(module)
    module.ROOT = ROOT
    module.validate_metadata.__defaults__ = (ROOT,)
    module.local_path.__defaults__ = (ROOT,)
    return module


class CatalogTests(unittest.TestCase):
    def test_native_and_original_entrypoint(self):
        original, native = oracle(), source()
        data = json.loads(native.METADATA.read_text())
        self.assertEqual(native.catalog_text(data), original.catalog_text(data))
        # Cells, row ordering, aliases, inner exhaustion and final newline.
        synthetic = deepcopy(data)
        synthetic["surfaces"][0]["operations"][0]["typing"][
            "output_authority"
        ] = "pipe|cell\nnext"
        synthetic["surfaces"][0]["operations"][0]["outputs"][
            "authority"
        ] = "pipe|cell\nnext"
        state = native.catalog_begin(synthetic)
        for position, surface in enumerate(synthetic["surfaces"]):
            previous = len(state["lines"])
            done = native.catalog_append_surface(state)
            self.assertEqual(state["position"], position + 1)
            self.assertEqual(len(state["lines"]) - previous, len(surface["operations"]))
            self.assertEqual(done, position == len(synthetic["surfaces"]) - 1)
        self.assertEqual(native.catalog_finish(state), original.catalog_text(synthetic))
        self.assertIn("pipe\\|cell next", native.catalog_finish(state))
        with self.assertRaises(IndexError):
            native.catalog_append_surface(state)
        # Real cursor reaches its 1024th surface and stops, without validating a
        # fabricated production metadata collection or altering the native CLI.
        surface = deepcopy(data["surfaces"][0])
        state = dict(data={"surfaces": [surface] * 1024}, position=0, lines=[])
        for index in range(1024):
            self.assertEqual(native.catalog_append_surface(state), index == 1023)
        self.assertEqual(state["position"], 1024)
        self.assertEqual(len(state["lines"]), 1024 * len(surface["operations"]))
        # Only context paths change in the oracle; all native behavior is real.
        for case in CASES["runtime"]:
            observed = []
            for module in [original, native]:
                with (
                    self.subTest(case=case["name"], module=module.__name__),
                    tempfile.TemporaryDirectory(dir=ROOT) as directory,
                ):
                    root = Path(directory)
                    metadata, catalog = populate(root, case["name"])
                    old_catalog, defaults = (
                        module.CATALOG,
                        module.load_contract.__defaults__,
                    )
                    module.CATALOG, module.load_contract.__defaults__ = catalog, (
                        metadata,
                    )
                    output = io.StringIO()
                    try:
                        with redirect_stdout(output):
                            if case["returncode"] == 1:
                                with self.assertRaises(IsADirectoryError):
                                    module.main(["catalog"])
                            else:
                                self.assertEqual(
                                    module.main(["catalog"]), case["returncode"]
                                )
                        if case["returncode"] != 1:
                            result = json.loads(output.getvalue())
                            self.assertEqual(result["ok"], case["returncode"] == 0)
                            if case["catalog"]:
                                self.assertEqual(
                                    result,
                                    dict(
                                        ok=True,
                                        path=str(catalog.relative_to(ROOT)),
                                        checked=False,
                                    ),
                                )
                                self.assertEqual(
                                    catalog.read_text(), original.catalog_text(data)
                                )
                            else:
                                self.assertIn("error", result)
                        observed.append(
                            output.getvalue()
                            .replace(str(root), "<root>")
                            .replace(root.name, "<fixture>")
                        )
                        if case["name"] == "success":
                            with redirect_stdout(io.StringIO()):
                                self.assertEqual(module.main(["catalog", "--check"]), 0)
                            catalog.write_text("stale")
                            with redirect_stdout(io.StringIO()):
                                self.assertEqual(module.main(["catalog", "--check"]), 2)
                    finally:
                        module.CATALOG, module.load_contract.__defaults__ = (
                            old_catalog,
                            defaults,
                        )
            self.assertEqual(observed[0], observed[1])

    def test_continuation_integrity_and_write_audit(self):
        service = CatalogTools(lambda path: None)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, catalog = populate(root)
            try:
                boundary = service.prepare(CONTEXT, [], str(root))["boundary"]
                data = service.load(boundary)["data"]
                self.assertEqual(
                    data["value"], json.loads(source().METADATA.read_text())
                )
                process = service.records[boundary["session"]]["process"]
                state = service.begin(data)["state"]
                changed = deepcopy(state)
                changed["position"] += 1
                with self.assertRaises(ValueError):
                    service.append(changed)
                while True:
                    previous = deepcopy(state)
                    row = service.append(state)
                    state = row["state"]
                    self.assertIs(
                        service.records[boundary["session"]]["process"], process
                    )
                    with self.assertRaises(ValueError):
                        service.append(previous)
                    if row["done"]:
                        break
                text = service.text(state)["text"]
                with self.assertRaises(ValueError):
                    service.publish(boundary, text + "tampered")
                (root / "unexpected.txt").write_text("intervening write")
                result = service.publish(boundary, text)["result"]
                self.assertEqual(result["returncode"], 0)
                self.assertFalse(result["ok"])
                self.assertEqual(result["status"], "undeclared_writes")
                self.assertEqual(
                    result["write_audit"]["unexpected_paths"], ["unexpected.txt"]
                )
                self.assertEqual(result["write_audit"]["declared_paths"], [CATALOG])
                self.assertEqual(
                    catalog.read_text(),
                    source().catalog_text(json.loads(source().METADATA.read_text())),
                )
                self.assertIsNotNone(process.returncode)
                self.assertFalse(service.records)
                with self.assertRaises(KeyError):
                    service.publish(boundary, text)
            finally:
                service.close()

    def test_registered_tools_and_real_lunar(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        spec = importlib.util.spec_from_file_location(
            "catalog_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        normalizer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(normalizer)
        self.assertEqual(normalizer.adoption_catalog_descriptor(), document)
        self.assertEqual(document["id"], "hub_adoption_catalog_workflow")
        self.assertEqual(document["aliases"], ["adoption:catalog"])
        self.assertEqual(
            document["policy"]["limits"],
            dict(wall_time_seconds=3600, max_operation_calls=1030),
        )
        self.assertTrue(
            all(
                op["execution"]["mode"] == "deterministic"
                for op in document["operations"].values()
            )
        )
        self.assertIn(
            SOURCE, [row["path"] for row in document["provenance"]["sources"]]
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        server = (
            'import sys;from pathlib import Path;sys.path.insert(0,"scripts");'
            'sys.path.extend(str(p) for p in Path(".venv/lib").glob("python*/site-packages"));'
            'from mcp_server import mcp;mcp.run(transport="stdio")'
        )
        failure = None
        async with manager.open(
            "catalog",
            StdioConfig(
                command=sys.executable, args=["-B", "-c", server], cwd=str(ROOT)
            ),
            {},
        ) as remote:
            try:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile_doc(doc, inventory=None):
                    assets = snapshot(doc)
                    workflow = compile_workflow(
                        "mcp:catalog",
                        workflow_documents([DESCRIPTOR], assets)[0],
                        tools if inventory is None else inventory,
                    )
                    return workflow, assets

                workflow, assets = compile_doc(document)
                self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                self.assertTrue(workflow["runtime_source"])
                self.assertEqual(set(workflow["bindings"]), set(document["operations"]))
                for case in CASES["compiler"]:
                    doc, inventory = deepcopy(document), tools
                    if case["name"] == "missing_append":
                        inventory = [
                            t
                            for t in tools
                            if t["name"] != "mathformer_adoption_catalog_append"
                        ]
                    if case["name"] == "draft":
                        doc["lifecycle"] = "draft"
                    if case["name"] == "specification_only":
                        doc["lifecycle"] = "draft"
                        doc["operations"]["append_surface"]["execution"] = dict(
                            mode="specification_only",
                            reason="Fixture qualification gap",
                        )
                    compiled, _ = compile_doc(doc, inventory)
                    self.assertEqual(
                        compiled["runnable"], case["runnable"], compiled["diagnostics"]
                    )

                async def authorize():
                    pass

                async def run(root, context=None, extra=None, doc=None):
                    w, a = compile_doc(doc) if doc else (workflow, assets)
                    self.assertTrue(w["runnable"], w["diagnostics"])
                    return await execute(
                        w,
                        a,
                        dict(
                            context=context or CONTEXT,
                            extra_args=extra or [],
                            repository_root=str(root),
                        ),
                        remote,
                        authorize,
                    )

                for case in CASES["runtime"]:
                    with (
                        self.subTest(case=case["name"]),
                        tempfile.TemporaryDirectory() as directory,
                    ):
                        root = Path(directory)
                        _, catalog = populate(root, case["name"])
                        result = await run(root)
                        self.assertEqual(result["status"], "accepted", result)
                        payload = result["outputs"]["result"]
                        self.assertEqual(
                            payload["returncode"], case["returncode"], payload
                        )
                        self.assertEqual(payload["ok"], case["catalog"])
                        self.assertEqual(len(result["calls"]), case["calls"])
                        self.assertTrue(payload["write_audit"]["ok"])
                        self.assertEqual(
                            payload["write_audit"]["observed_paths"],
                            [CATALOG] if case["catalog"] else [],
                        )
                        if case["returncode"] == 1:
                            self.assertIn("IsADirectoryError", payload["stderr"])
                            self.assertEqual(payload["stdout"], "")
                        else:
                            emitted = json.loads(payload["stdout"])
                            self.assertEqual(emitted["ok"], case["returncode"] == 0)
                            if case["catalog"]:
                                self.assertEqual(
                                    emitted, dict(ok=True, path=CATALOG, checked=False)
                                )
                                self.assertEqual(
                                    catalog.read_text(),
                                    source().catalog_text(
                                        json.loads(source().METADATA.read_text())
                                    ),
                                )
                        self.assertEqual(
                            sum(
                                c["operation"] == "append_surface"
                                for c in result["calls"]
                            ),
                            4 if case["calls"] == 9 else 0,
                        )
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["replay_artifacts"])
                # Dry-run and preflight failures never read even malformed input.
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    _, catalog = populate(root, "malformed")
                    for context, args in [
                        ({**CONTEXT, "dry_run": True, "allow_mutating": False}, []),
                        ({**CONTEXT, "allow_mutating": False}, []),
                        (CONTEXT, ["--check"]),
                    ]:
                        result = await run(root, context, args)
                        self.assertEqual(result["status"], "accepted", result)
                        payload = result["outputs"]["result"]
                        self.assertEqual(payload["ok"], context["dry_run"])
                        self.assertEqual(len(result["calls"]), 4)
                        self.assertNotIn("stdout", payload)
                        self.assertNotIn("write_audit", payload)
                        self.assertFalse(catalog.exists())
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    _, catalog = populate(root)
                    # Last permitted iteration stops successfully (four surfaces).
                    bounded = deepcopy(document)
                    bounded["flow"]["steps"][2]["max_iterations"] = 4
                    result = await run(root, doc=bounded)
                    self.assertEqual(result["status"], "accepted", result)
                    catalog.unlink()
                    bounded["flow"]["steps"][2]["max_iterations"] = 1
                    result = await run(root, doc=bounded)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]],
                        ["prepare", "load", "begin_catalog", "append_surface"],
                    )
                    self.assertFalse(catalog.exists())
                    budget = deepcopy(document)
                    budget["policy"]["limits"]["max_operation_calls"] = 3
                    result = await run(root, doc=budget)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(
                        sum(
                            bool(c.get("transport_call_performed"))
                            for c in result["calls"]
                        ),
                        3,
                    )
                    self.assertIn("budget", json.dumps(result).lower())
                    self.assertFalse(catalog.exists())
                timed = deepcopy(document)
                timed["policy"]["limits"]["wall_time_seconds"] = 1
                w, a = compile_doc(timed)

                async def never_authorized():
                    await asyncio.Event().wait()

                with self.assertRaises(TimeoutError):
                    await execute(w, a, {}, remote, never_authorized)
            except Exception as exc:
                failure = exc
        self.assertFalse(manager.active)
        if failure is not None:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
