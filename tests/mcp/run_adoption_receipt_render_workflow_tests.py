#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic receipt fixtures through native steps, MCP and real PRISM.

There are no external provider/compiler calls in this workflow. Nothing replaces
PRISM's parser/checker/compiler or runtime, and no recorded operation is replayed.
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

from adoption_receipt_render_tools import source
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_adoption_receipt_render_workflow/workflow.yaml"


def oracle():
    path = ROOT / "tests/mcp/fixtures/adoption_receipt_render_original.py.txt"
    spec = importlib.util.spec_from_loader(
        "receipt_oracle", SourceFileLoader("receipt_oracle", str(path))
    )
    module = importlib.util.module_from_spec(spec)
    source()  # make the existing reasoning_log module available
    spec.loader.exec_module(module)
    return module


def receipt(directory, status="complete", metadata=None):
    """Fixed identities and events avoid clocks, random UUIDs and live operations."""
    native = source()
    metadata = {} if metadata is None else metadata
    identity = "0123456789abcdef0123456789abcdef"
    terminal = {
        "schema_version": 1,
        "invocation_id": identity,
        "parent_invocation_id": None,
        "status": status,
        "result": {"text": "<untrusted> & 雪"},
    }
    md, rd = native.canonical_digest(metadata), native.canonical_digest(terminal)
    events = []
    for index in (1, 2):
        application = {
            "skill_call_id": identity,
            "parent_call_id": None,
            "skill": str(metadata.get("skill_id", "portable-adoption")),
            "status": (
                "running"
                if index == 1
                else ("complete" if status == "complete" else "error")
            ),
        }
        application["inputs" if index == 1 else "evidence"] = {"metadata_digest": md}
        if index == 2:
            application["evidence"]["result_digest"] = rd
        events.append(
            {
                "step": (
                    "skill_application_start"
                    if index == 1
                    else (
                        "skill_application_complete"
                        if status == "complete"
                        else "skill_application_error"
                    )
                ),
                "event_index": index,
                "payload": {
                    **{
                        key: application[key]
                        for key in ("skill_call_id", "parent_call_id", "skill")
                    },
                    "skill_application": application,
                },
            }
        )
    provenance = {
        "schema_version": 1,
        "invocation_id": identity,
        "parent_invocation_id": None,
        "status": status,
        "metadata": metadata,
        "metadata_digest": md,
        "result_digest": rd,
    }
    save(directory, provenance, terminal, events)
    return provenance, terminal, events


def save(directory, provenance, terminal, events):
    raw = "".join(
        json.dumps(event, ensure_ascii=False) + "\n" for event in events
    ).encode()
    provenance["reasoning_digest"] = hashlib.sha256(raw).hexdigest()
    (directory / "reasoning.jsonl").write_bytes(raw)
    (directory / "provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False)
    )
    (directory / "result.json").write_text(json.dumps(terminal, ensure_ascii=False))


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


class ReceiptTests(unittest.TestCase):
    def test_original_cli_and_shared_state(self):
        native, original = source(), oracle()
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            for status in ("complete", "failed", "cancelled"):
                for metadata in (
                    {},
                    {
                        "skill_label": '<b>"雪" &',
                        "attempt": 2,
                        "fixture": {"b": False, "a": None},
                    },
                ):
                    record, _, _ = receipt(directory, status, metadata)
                    rows = native.summary_base_rows(record)
                    self.assertEqual(
                        rows,
                        [
                            ("Invocation", record["invocation_id"]),
                            ("Status", status),
                            ("Result SHA-256", record["result_digest"]),
                        ],
                    )
                    self.assertIs(native.summary_append_metadata(record, rows), rows)
                    self.assertEqual(len(rows), 3 + len(metadata))
                    self.assertEqual([row[0] for row in rows[3:]], sorted(metadata))
                    self.assertEqual(
                        native.summary_html(rows), original.render_summary(directory)
                    )
                    self.assertEqual(
                        native.render_summary(directory),
                        original.render_summary(directory),
                    )
                    outputs = []
                    for module in (original, native):
                        stream = io.StringIO()
                        with redirect_stdout(stream):
                            code = module.main(["render", str(directory)])
                        outputs.append((code, stream.getvalue()))
                    self.assertEqual(*outputs)
                    self.assertEqual(outputs[0][0], 0)
            (directory / "provenance.json").write_text("{")
            outputs = []
            for module in (original, native):
                stream = io.StringIO()
                with redirect_stdout(stream):
                    code = module.main(["render", str(directory)])
                outputs.append((code, stream.getvalue()))
            self.assertEqual(*outputs)
            self.assertEqual(outputs[0][0], 1)
            self.assertFalse(json.loads(outputs[0][1])["ok"])

    def test_real_registered_mcp_and_lunar(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_adoption_receipt_render_workflow")
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 4},
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        # Import the production registration without loading service config/credentials.
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        failure = None
        async with manager.open(
            "receipt",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {},
        ) as remote:
            try:
                tools = [
                    tool.model_dump(by_alias=True, exclude_none=True)
                    for tool in await remote.tools()
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
                unavailable, _ = compile(document, [])
                self.assertFalse(unavailable["runnable"])
                self.assertTrue(unavailable["diagnostics"])

                async def authorize():
                    pass

                async def run(directory, doc=None):
                    compiled, received = compile(doc) if doc else (workflow, assets)
                    return await execute(
                        compiled,
                        received,
                        {"directory": str(directory)},
                        remote,
                        authorize,
                    )

                with tempfile.TemporaryDirectory() as temporary:
                    directory = Path(temporary)
                    # Zero and maximum allowed metadata traversal, all terminal branches.
                    for status in ("complete", "failed", "cancelled"):
                        for metadata in (
                            {},
                            {key: '<雪 & "' for key in source().METADATA_KEYS},
                        ):
                            record, _, _ = receipt(directory, status, metadata)
                            before = {
                                p.name: p.read_bytes() for p in directory.iterdir()
                            }
                            result = await run(directory)
                            self.assertEqual(result["status"], "accepted", result)
                            self.assertEqual(
                                result["outputs"],
                                {"html": oracle().render_summary(directory)},
                            )
                            self.assertEqual(
                                [c["tool"] for c in result["calls"]],
                                [
                                    "mathformer_receipt_validate",
                                    "mathformer_receipt_base_rows",
                                    "mathformer_receipt_append_metadata",
                                    "mathformer_receipt_assemble_html",
                                ],
                            )
                            self.assertEqual(
                                before,
                                {p.name: p.read_bytes() for p in directory.iterdir()},
                            )
                            self.assertTrue(result["runtime"]["effect_records"])
                            self.assertTrue(result["replay_artifacts"])
                            self.assertNotIn("<雪", result["outputs"]["html"])
                    # Inspect actual transported carried state, not just final HTML.
                    response = await remote.call(
                        "mathformer_receipt_validate", {"directory": str(directory)}
                    )
                    self.assertEqual(response["record"], record)
                    response = await remote.call(
                        "mathformer_receipt_base_rows", {"record": record}
                    )
                    self.assertEqual(len(response["rows"]), 3)
                    response = await remote.call(
                        "mathformer_receipt_append_metadata",
                        {"record": record, "rows": response["rows"]},
                    )
                    self.assertEqual(len(response["rows"]), 3 + len(record["metadata"]))
                    self.assertEqual(
                        [r[0] for r in response["rows"][3:]], sorted(record["metadata"])
                    )
                    response = await remote.call(
                        "mathformer_receipt_assemble_html", {"rows": response["rows"]}
                    )
                    self.assertEqual(
                        response["html"], source().render_summary(directory)
                    )
                    for corruption in (
                        "missing",
                        "malformed",
                        "duplicate",
                        "nonfinite",
                        "metadata",
                        "result_digest",
                        "status",
                        "identity",
                        "version",
                        "event_count",
                        "event_order",
                        "event_join",
                        "digest_join",
                    ):
                        record, terminal, events = receipt(directory)
                        if corruption == "metadata":
                            record["metadata"] = {"unapproved": True}
                            record["metadata_digest"] = source().canonical_digest(
                                record["metadata"]
                            )
                        elif corruption == "result_digest":
                            terminal["result"] = "tampered"
                        elif corruption == "status":
                            terminal["status"] = record["status"] = "unknown"
                            record["result_digest"] = source().canonical_digest(
                                terminal
                            )
                        elif corruption == "identity":
                            record["parent_invocation_id"] = record["invocation_id"]
                        elif corruption == "version":
                            record["schema_version"] = 2
                        elif corruption == "event_count":
                            events.append(deepcopy(events[-1]))
                        elif corruption == "event_order":
                            events.reverse()
                        elif corruption == "event_join":
                            events[1]["payload"]["skill_application"][
                                "skill_call_id"
                            ] = "wrong"
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
                            (directory / "provenance.json").write_text(
                                '{"status":1,"status":2}'
                            )
                        elif corruption == "nonfinite":
                            (directory / "provenance.json").write_text('{"status":NaN}')
                        with self.assertRaises(ValueError):
                            source().render_summary(directory)
                        with self.assertRaises(ValueError):
                            oracle().render_summary(directory)
                        result = await run(directory)
                        self.assertEqual(
                            result["status"], "failed", (corruption, result)
                        )
                        self.assertIsNone(result["outputs"])
                        self.assertEqual(len(result["calls"]), 1)
                        self.assertEqual(
                            result["calls"][0]["tool"], "mathformer_receipt_validate"
                        )
                    receipt(directory)
                    bounded = deepcopy(document)
                    bounded["policy"]["limits"]["max_operation_calls"] = 3
                    result = await run(directory, bounded)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(
                        sum(
                            bool(c.get("transport_call_performed"))
                            for c in result["calls"]
                        ),
                        3,
                    )
                    self.assertEqual(result["calls"][-1]["status"], "rejected")
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
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
