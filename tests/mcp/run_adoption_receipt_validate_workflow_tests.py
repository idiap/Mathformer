#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Offline deterministic fixtures through registered MCP, real PRISM and Lunar.

No provider or external compiler boundary exists in receipt validation. The
actual PRISM parser, checker, compiler and runtime execute without substitution.
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
from run_adoption_receipt_render_workflow_tests import receipt, save
from adoption_receipt_render_tools import source
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_adoption_receipt_validate_workflow/workflow.yaml"


def oracle():
    path = ROOT / "tests/mcp/fixtures/adoption_receipt_validate_original.py.txt"
    spec = importlib.util.spec_from_loader(
        "validate_oracle", SourceFileLoader("validate_oracle", str(path))
    )
    module = importlib.util.module_from_spec(spec)
    source()
    spec.loader.exec_module(module)
    return module


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


class ReceiptValidationTests(unittest.TestCase):
    def test_mcp_prism_native_equivalence(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_adoption_receipt_validate_workflow")
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 5},
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        original = oracle()
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        async with manager.open(
            "receipt",
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
                    "mcp:receipt",
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

            async def run(directory, doc=None):
                compiled, received = compile(doc) if doc else (workflow, assets)
                self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                return await execute(
                    compiled, received, {"directory": str(directory)}, remote, authorize
                )

            def compare(directory):
                results = []
                for module in (original, source()):
                    stream = io.StringIO()
                    with redirect_stdout(stream):
                        code = module.main(["validate", str(directory)])
                    results.append((code, stream.getvalue()))
                self.assertEqual(*results)
                return results[0]

            with tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                for status in ("complete", "failed", "cancelled"):
                    for metadata in (
                        {},
                        {key: '<雪 & "' for key in source().METADATA_KEYS},
                    ):
                        record, _, _ = receipt(directory, status, metadata)
                        before = {p.name: p.read_bytes() for p in directory.iterdir()}
                        self.assertEqual(compare(directory)[0], 0)
                        result = await run(directory)
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertEqual(result["outputs"], {"provenance": record})
                        self.assertEqual(
                            [c["tool"] for c in result["calls"]],
                            [
                                "mathformer_receipt_read_check",
                                "mathformer_receipt_pack_cursor",
                                "mathformer_receipt_validate_event",
                                "mathformer_receipt_validate_event",
                                "mathformer_receipt_finish_joins",
                            ],
                        )
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["replay_artifacts"])
                        self.assertEqual(
                            before,
                            {p.name: p.read_bytes() for p in directory.iterdir()},
                        )
                        # Inspect transported context and enumerate state on both branches.
                        checked = await remote.call(
                            "mathformer_receipt_read_check",
                            {"directory": str(directory)},
                        )
                        self.assertEqual(checked["complete"], status == "complete")
                        state = (
                            await remote.call(
                                "mathformer_receipt_pack_cursor",
                                {
                                    "receipt": checked["receipt"],
                                    "terminal_step": (
                                        "skill_application_complete"
                                        if status == "complete"
                                        else "skill_application_error"
                                    ),
                                    "terminal_status": (
                                        "complete" if status == "complete" else "error"
                                    ),
                                },
                            )
                        )["state"]
                        for index in (1, 2):
                            self.assertEqual(state["index"], index)
                            advanced = await remote.call(
                                "mathformer_receipt_validate_event", {"state": state}
                            )
                            self.assertEqual(advanced["done"], index == 2)
                            self.assertEqual(
                                advanced["state"]["receipt"], checked["receipt"]
                            )
                            state = advanced["state"]
                        self.assertEqual(state["index"], 3)
                        self.assertEqual(
                            await remote.call(
                                "mathformer_receipt_finish_joins", {"state": state}
                            ),
                            {"provenance": record},
                        )
                        with self.assertRaises(ValueError):
                            source().receipt_validate_event(state)
                # Parsing traverses all lines before the count bound; native error order is retained.
                corruptions = {
                    "missing": 1,
                    "malformed": 1,
                    "duplicate": 1,
                    "nonfinite": 1,
                    "metadata": 1,
                    "result_digest": 1,
                    "event_count": 1,
                    "extra_bad_line": 1,
                    "version": 1,
                    "identity": 1,
                    "parent": 1,
                    "status": 1,
                    "start": 3,
                    "terminal": 4,
                    "shape": 4,
                    "digest_join": 5,
                }
                for corruption, calls in corruptions.items():
                    record, terminal, events = receipt(directory)
                    if corruption == "metadata":
                        record["metadata"] = {"unapproved": True}
                    elif corruption == "result_digest":
                        terminal["result"] = "tampered"
                    elif corruption == "version":
                        record["schema_version"] = 2
                    elif corruption == "identity":
                        record["invocation_id"] = "A" * 32
                    elif corruption == "parent":
                        record["parent_invocation_id"] = record["invocation_id"]
                    elif corruption == "status":
                        terminal["status"] = record["status"] = "unknown"
                        record["result_digest"] = source().canonical_digest(terminal)
                    elif corruption == "event_count":
                        events.append(deepcopy(events[-1]))
                    elif corruption == "start":
                        events[0]["event_index"] = 9
                    elif corruption == "terminal":
                        events[1]["payload"]["skill_application"]["status"] = "running"
                    elif corruption == "shape":
                        del events[1]["payload"]
                    elif corruption == "digest_join":
                        events[0]["payload"]["skill_application"]["inputs"][
                            "metadata_digest"
                        ] = "wrong"
                    save(directory, record, terminal, events)
                    if corruption == "missing":
                        (directory / "result.json").unlink()
                    elif corruption == "malformed":
                        (directory / "provenance.json").write_text("{")
                    elif corruption == "duplicate":
                        (directory / "provenance.json").write_text('{"a":1,"a":2}')
                    elif corruption == "nonfinite":
                        (directory / "provenance.json").write_text('{"a":NaN}')
                    elif corruption == "extra_bad_line":
                        with (directory / "reasoning.jsonl").open("ab") as stream:
                            stream.write(b"{bad json\n")
                    self.assertEqual(compare(directory)[0], 1, corruption)
                    result = await run(directory)
                    self.assertEqual(result["status"], "failed", (corruption, result))
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(len(result["calls"]), calls, (corruption, result))
                receipt(directory)
                bounded = deepcopy(document)
                bounded["flow"]["steps"][2]["max_iterations"] = 1
                result = await run(directory, bounded)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(len(result["calls"]), 3)
                limited = deepcopy(document)
                limited["policy"]["limits"]["max_operation_calls"] = 4
                result = await run(directory, limited)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in result["calls"]
                    ),
                    4,
                )
                self.assertIn("budget", json.dumps(result).lower())
                timed = deepcopy(document)
                timed["policy"]["limits"]["wall_time_seconds"] = 1
                compiled, received = compile(timed)
                self.assertTrue(compiled["runnable"], compiled["diagnostics"])

                async def pending_authority():
                    await asyncio.Event().wait()

                with self.assertRaises(TimeoutError):
                    await execute(
                        compiled,
                        received,
                        {"directory": str(directory)},
                        remote,
                        pending_authority,
                    )
        self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
