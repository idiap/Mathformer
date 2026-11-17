#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic filesystem fixtures through production MCP and real Lunar/PRISM.

This source has no model/provider or external compiler boundary. Nothing replaces
its steps, tools, PRISM parser/checker/compiler, or runtime.
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
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import tempfile
import unittest
import yaml
from reasoning_index_tools import source
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_control_reasoning_log_index_validate_workflow/workflow.yaml"


def oracle():
    path = ROOT / "tests/mcp/fixtures/reasoning_index_original.py.txt"
    spec = importlib.util.spec_from_loader(
        "index_oracle", SourceFileLoader("index_oracle", str(path))
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.REPO_ROOT = ROOT
    return module


def assets(document):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(r["path"], (ROOT / r["path"]).read_text())
        for r in document["provenance"]["sources"]
    ]


class IndexTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.native, self.original = source(), oracle()
        self.entry = {field: "fixture" for field in self.native.REQUIRED_FIELDS}
        self.entry.update(
            log_file=str(ROOT / "artifacts/../README.md"),
            event_count=True,
            validation_status="pass",
            quality_status="unknown",
            reports=[],
        )

    def file(self, name, payload=None, raw=None):
        path = self.directory / name
        if payload is not None or raw is not None:
            path.write_text(json.dumps(payload) if raw is None else raw)
        return path

    def test_original_equivalence_state_order_and_cli(self):
        mixed = [
            None,
            {},
            {
                **self.entry,
                "log_file": str(self.directory / "absent"),
                "event_count": -1,
                "validation_status": "invalid",
                "quality_status": "bad",
            },
            self.entry,
        ]
        for name, payload, raw in [
            ("missing", None, None),
            ("invalid", None, "{"),
            ("empty", {"entries": []}, None),
            ("wrong", {"entries": {}}, None),
            ("valid", {"entries": [self.entry]}, None),
            ("mixed", {"entries": mixed}, None),
            ("unbounded", {"entries": [None] * 1001}, None),
        ]:
            with self.subTest(name=name):
                path = self.file(name, payload, raw)
                self.assertEqual(
                    self.native.validate_index(path), self.original.validate_index(path)
                )
                for flags in ([], ["--json"]):
                    observed = []
                    for module in (self.native, self.original):
                        stream = io.StringIO()
                        with redirect_stdout(stream):
                            code = module.main(["--index", str(path), *flags])
                        observed.append((code, stream.getvalue()))
                    self.assertEqual(*observed)
        report = self.native.validate_index(self.directory / "mixed")
        self.assertEqual(
            [f["code"] for f in report["findings"]],
            [
                "entry_not_object",
                "entry_missing_fields",
                "invalid_event_count",
                "invalid_status",
                "invalid_status",
                "log_file_outside_artifacts",
                "log_file_missing",
                "invalid_event_count",
                "invalid_status",
                "invalid_status",
            ],
        )
        for payload, error in [
            ([], AttributeError),
            ({"entries": [{**self.entry, "quality_status": []}]}, TypeError),
        ]:
            path = self.file("raises", payload)
            for module in (self.native, self.original):
                with self.assertRaises(error):
                    module.validate_index(path)
        for module in (self.native, self.original):
            with self.assertRaises(IsADirectoryError):
                module.validate_index(self.directory)

    def test_real_registered_tools_and_lunar(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(
            document["id"], "hub_control_reasoning_log_index_validate_workflow"
        )
        self.assertEqual(document["lifecycle"], "active")
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        failure = None
        async with manager.open(
            "index",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {},
        ) as remote:
            try:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile(doc, inventory=None):
                    received = assets(doc)
                    selected = workflow_documents([DESCRIPTOR], received)[0]
                    qualified = compile_workflow(
                        "mcp:index", selected, tools if inventory is None else inventory
                    )
                    return qualified, received

                workflow, received = compile(document)
                self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                self.assertTrue(workflow["runtime_source"])
                self.assertEqual(set(workflow["bindings"]), set(document["operations"]))
                missing, _ = compile(document, [])
                self.assertFalse(missing["runnable"])

                async def allow():
                    pass

                async def run(path, doc=None):
                    w, a = compile(doc) if doc else (workflow, received)
                    return await execute(w, a, {"index": str(path)}, remote, allow)

                for name, payload, raw in [
                    ("absent", None, None),
                    ("json", None, "{"),
                    ("empty", {"entries": []}, None),
                    ("notlist", {"entries": 5}, None),
                    ("good", {"entries": [self.entry]}, None),
                    ("findings", {"entries": [None, {}, self.entry]}, None),
                ]:
                    path = self.file(name, payload, raw)
                    result = await run(path)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(
                        result["outputs"],
                        {"report": self.original.validate_index(path)},
                    )
                    count = (
                        len(payload["entries"])
                        if isinstance(payload, dict)
                        and isinstance(payload.get("entries"), list)
                        else 0
                    )
                    self.assertEqual(
                        [c["tool"] for c in result["calls"]],
                        ["mathformer_reasoning_index_load"]
                        + ["mathformer_reasoning_index_advance"] * max(1, count)
                        + ["mathformer_reasoning_index_finalize"],
                    )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["replay_artifacts"])
                path = self.file("states", {"entries": [None, {}, self.entry]})
                loaded = await remote.call(
                    "mathformer_reasoning_index_load", {"index": str(path)}
                )
                expected = self.native.load_initialize(path)
                self.assertEqual(loaded, expected)
                for offset in range(3):
                    expected = self.native.validate_entry_advance(expected["state"])
                    loaded = await remote.call(
                        "mathformer_reasoning_index_advance", {"state": loaded["state"]}
                    )
                    self.assertEqual(loaded, expected)
                    self.assertEqual(loaded["state"]["offset"], offset + 1)
                    self.assertEqual(loaded["done"], offset == 2)
                self.assertEqual(
                    await remote.call(
                        "mathformer_reasoning_index_finalize",
                        {"state": loaded["state"]},
                    ),
                    {"report": self.original.validate_index(path)},
                )
                # Exact admitted bound stops normally with findings (not early on failure).
                path = self.file("limit", {"entries": [None] * 1000})
                result = await run(path)
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(len(result["calls"]), 1002)
                self.assertEqual(
                    result["outputs"], {"report": self.original.validate_index(path)}
                )
                path = self.file("over", {"entries": [None] * 1001})
                result = await run(path)
                self.assertEqual(result["status"], "failed")
                self.assertEqual(len(result["calls"]), 1)
                self.assertIsNone(result["outputs"])
                # Deterministic compiler fixtures exercise fail-on-exhaustion and call budgets.
                path = self.file("two", {"entries": [None, None]})
                bounded = deepcopy(document)
                bounded["flow"]["steps"][1]["max_iterations"] = 1
                result = await run(path, bounded)
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(result["failure_disposition"], "fail")
                self.assertEqual(len(result["calls"]), 2)
                self.assertIsNone(result["outputs"])
                budget = deepcopy(document)
                budget["policy"]["limits"]["max_operation_calls"] = 1
                result = await run(path, budget)
                self.assertEqual(result["status"], "failed")
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in result["calls"]
                    ),
                    1,
                )
                self.assertIn("budget", str(result).lower())
                for path, count in [
                    (self.file("shape", []), 1),
                    (self.directory, 1),
                    (
                        self.file(
                            "status",
                            {"entries": [{**self.entry, "validation_status": []}]},
                        ),
                        2,
                    ),
                ]:
                    result = await run(path)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(len(result["calls"]), count)
                    self.assertEqual(result["calls"][-1]["status"], "rejected")
                timed = deepcopy(document)
                timed["policy"]["limits"]["wall_time_seconds"] = 1
                w, a = compile(timed)

                async def pending():
                    await asyncio.Event().wait()

                with self.assertRaises(TimeoutError):
                    await execute(w, a, {"index": str(path)}, remote, pending)
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
