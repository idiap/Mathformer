#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402 - Lunar environment and import paths must be set before imports.
"""Exercise real KB commands, registered MCP tools, and Lunar's PRISM runtime.

There are no external providers or theorem compilers in this regression. The
only inputs synthesized here are candidate discovery reports in temporary dirs.
No production KB, proofs, credentials, or model services are used.
"""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.path[:0] = [str(LUNAR / "app/backend"), str(ROOT / "scripts"), str(ROOT)]

import asyncio
import contextlib
from copy import deepcopy
import hashlib
import io
import json
import re
import tempfile
import unittest
from unittest.mock import patch
import yaml
from premise_kb_e2e_tools import source, register_premise_kb_e2e_tools
from mcp.server.fastmcp import FastMCP
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_kb_e2e_workflow/workflow.yaml"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
SERVER = ROOT / "tests/mcp/fixtures/premise_kb_e2e_server.py"


def fixture(root, mode="success", count=1):
    artifacts = root / "vampire"
    artifacts.mkdir(exist_ok=True)
    for i in range(count if mode != "empty" else 0):
        directory = artifacts / f"{i:03d}"
        directory.mkdir()
        # Deliberately candidates, never proved artifacts; ingestion needs no ATP.
        report = {
            "ok": False,
            "informal_statement": f"Fixture group candidate {i}",
            "winner": {"formulas": [{"role": "conjecture", "formula": f"p(f{i})"}]},
        }
        (directory / "discovery_report.json").write_text(
            "{invalid" if mode == "malformed" else json.dumps(report)
        )
    return artifacts


def snapshot(doc):
    def asset(path, text):
        return {
            "path": path,
            "content": text,
            "encoding": "text",
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
        }

    return [asset(DESCRIPTOR, json.dumps(doc))] + [
        asset(row["path"], (ROOT / row["path"]).read_text())
        for row in doc["provenance"]["sources"]
    ]


def stable(value):
    # Native KB provenance timestamps vary; preserve every other field and order.
    if isinstance(value, dict):
        return {k: stable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [stable(v) for v in value]
    if isinstance(value, str):
        return re.sub(r"\d{4}-\d\d-\d\dT[0-9:.]+(?:\+00:00|Z)", "<timestamp>", value)
    return value


class KBTests(unittest.TestCase):
    def test_shared_native_stages_state_and_fixed_arguments(self):
        native = source()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifacts = fixture(root, count=14)
            kb = root / "kb"
            kb.mkdir()
            (kb / "stale").write_text("old")
            state = native.prepare(
                {"kb_root": str(kb), "artifact_root": str(artifacts)}
            )
            self.assertFalse(kb.exists())
            self.assertFalse(state["json"])
            self.assertEqual(state["responses"], {})
            state = native.populate(state)
            self.assertEqual(
                list(state["responses"]),
                ["init", "seeds", "vampire", "bloom", "embeddings"],
            )
            self.assertEqual(state["responses"]["vampire"]["candidate_count"], 12)
            self.assertEqual(
                state["responses"]["vampire"]["artifact_root"], str(artifacts)
            )
            index_path = Path(state["responses"]["embeddings"]["embedding_index"])
            self.assertEqual(
                json.loads((index_path.parent / "metadata.json").read_text())[
                    "dimension"
                ],
                256,
            )
            state = native.query(state)
            self.assertEqual(
                list(state["responses"])[-4:],
                ["membership", "absent", "search", "distance"],
            )
            self.assertLessEqual(len(state["responses"]["search"]["hits"]), 5)
            self.assertTrue(
                all(
                    "cosine_distance" in hit
                    for hit in state["responses"]["search"]["hits"]
                )
            )
            state = native.update_report(state)
            self.assertEqual(
                list(state["responses"])[-3:], ["promote", "reject", "report"]
            )
            self.assertEqual(len(state["responses"]), 12)
            payload = native.assess(state)
            self.assertEqual(len(payload["assertions"]), 13)
            self.assertTrue(payload["ok"], payload)
            self.assertEqual(
                state["responses"]["promote"]["entry"]["status"], "reviewed_informal"
            )
            self.assertEqual(
                state["responses"]["reject"]["entry"]["status"], "rejected"
            )
            for fmt in [False, True]:
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    result = native.emit(payload, {"json": fmt})
                self.assertEqual(result["exit_code"], 0)
                self.assertEqual(result["stdout"], out.getvalue())
                if fmt:
                    self.assertEqual(json.loads(out.getvalue()), payload)
                else:
                    self.assertEqual(len(out.getvalue().splitlines()), 3)

    def test_original_main_output_and_failure_equivalence(self):
        # Supply the same isolated artifact context to the frozen original. This
        # changes only its hardcoded input path; its algorithm stays untouched.
        frozen = (
            ROOT / "tests/mcp/fixtures/premise_kb_e2e_original.py.txt"
        ).read_text()
        for mode in ["success", "empty", "malformed"]:
            for json_output in [True, False]:
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    artifacts = fixture(root, mode)
                    kb = root / "kb"
                    scope = {
                        "__name__": "_original_kb",
                        "__file__": str(ROOT / "tests/kb/run_premise_kb_e2e.py"),
                    }
                    exec(
                        frozen.replace('"artifacts/vampire_atp"', repr(str(artifacts))),
                        scope,
                    )
                    results = []
                    for main, extra in [
                        (scope["main"], []),
                        (source().main, ["--artifact-root", str(artifacts)]),
                    ]:
                        out = io.StringIO()
                        with (
                            patch.object(
                                sys,
                                "argv",
                                [
                                    "kb",
                                    "--kb-root",
                                    str(kb),
                                    *extra,
                                    *(["--json"] if json_output else []),
                                ],
                            ),
                            contextlib.redirect_stdout(out),
                        ):
                            try:
                                code = main()
                                results.append(
                                    (
                                        code,
                                        (
                                            stable(json.loads(out.getvalue()))
                                            if json_output
                                            else out.getvalue()
                                        ),
                                    )
                                )
                            except RuntimeError as error:
                                self.assertIn("command failed:", str(error))
                                self.assertIn("ingest-vampire", str(error))
                                self.assertEqual(out.getvalue(), "")
                                results.append(("RuntimeError", "ingest-vampire"))
                    self.assertEqual(*results)
                    self.assertEqual(
                        results[0][0],
                        {"success": 0, "empty": 3, "malformed": "RuntimeError"}[mode],
                    )

    def test_mcp_write_guard_precedes_reset(self):
        # FastMCP propagates the policy error and leaves the directory intact.
        async def guarded():
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "kb"
                path.mkdir()
                marker = path / "keep"
                marker.write_text("retained")
                mcp = FastMCP("denied")

                def deny(path):
                    raise ValueError("read-only fixture")

                register_premise_kb_e2e_tools(mcp, deny)
                with self.assertRaises(Exception) as raised:
                    await mcp.call_tool(
                        "mathformer_kb_e2e_prepare", {"request": {"kb_root": str(path)}}
                    )
                self.assertIn("read-only fixture", str(raised.exception))
                self.assertEqual(marker.read_text(), "retained")

        asyncio.run(guarded())

    def test_real_registered_mcp_and_lunar_execution(self):
        doc = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(doc["id"], "hub_kb_e2e_workflow")
        self.assertEqual(doc["lifecycle"], "active")
        self.assertEqual(doc["policy"]["limits"]["max_operation_calls"], 6)
        self.assertEqual(doc["policy"]["failure"]["retry"]["max_attempts"], 1)
        for row in doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )

        async def scenario(mode, fmt=True, budget=6):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                artifacts = fixture(root, mode)
                kb = root / "kb"
                kb.mkdir()
                (kb / "stale").write_text("old")
                manager = SessionManager()
                failure = None
                async with manager.open(
                    "kb-e2e",
                    StdioConfig(
                        command=sys.executable, args=[str(SERVER)], cwd=str(ROOT)
                    ),
                    {},
                ) as remote:
                    try:
                        tools = [
                            tool.model_dump(by_alias=True, exclude_none=True)
                            for tool in await remote.tools()
                        ]
                        bound = {
                            "mathformer_kb_e2e_" + name for name in doc["operations"]
                        }
                        self.assertTrue(bound.issubset({t["name"] for t in tools}))
                        document = deepcopy(doc)
                        document["policy"]["limits"]["max_operation_calls"] = budget
                        assets = snapshot(document)
                        compiled = compile_workflow(
                            "mcp:kb-e2e",
                            workflow_documents([DESCRIPTOR], assets)[0],
                            tools,
                        )
                        self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                        self.assertTrue(compiled["runtime_source"])
                        self.assertEqual(
                            set(compiled["bindings"]), set(doc["operations"])
                        )

                        async def authorize():
                            pass

                        result = await execute(
                            compiled,
                            assets,
                            {
                                "request": {
                                    "kb_root": str(kb),
                                    "artifact_root": str(artifacts),
                                    "json": fmt,
                                }
                            },
                            remote,
                            authorize,
                        )
                        self.assertFalse((kb / "stale").exists())
                        self.assertTrue(result["runtime"]["effect_records"])
                        if mode == "malformed":
                            self.assertEqual(result["status"], "failed", result)
                            self.assertIsNone(result["outputs"])
                            self.assertEqual(
                                len(result["calls"]), 2
                            )  # prepare, failed populate; no retry
                            self.assertEqual(result["calls"][-1]["status"], "rejected")
                            self.assertFalse((kb / "bloom/manifest.json").exists())
                            self.assertFalse((kb / "embeddings/index.json").exists())
                            history = [
                                json.loads(line)
                                for line in (kb / "curation_log.jsonl")
                                .read_text()
                                .splitlines()
                            ]
                            self.assertGreaterEqual(len(history), 8)
                            self.assertEqual(
                                {row["action"] for row in history}, {"add_entry"}
                            )
                            self.assertEqual((kb / "rejected.jsonl").read_text(), "")
                        elif budget < 6:
                            self.assertEqual(len(result["calls"]), 6)
                            self.assertEqual(result["status"], "failed", result)
                            self.assertIsNone(result["outputs"])
                            self.assertEqual(result["calls"][-1]["status"], "rejected")
                        else:
                            self.assertEqual(result["status"], "accepted", result)
                            self.assertEqual(len(result["calls"]), 6)
                            output = result["outputs"]["result"]
                            self.assertEqual(
                                output["exit_code"], 0 if mode == "success" else 3
                            )
                            payload = output["payload"]
                            self.assertEqual(payload["ok"], mode == "success")
                            self.assertEqual(len(payload["assertions"]), 13)
                            self.assertTrue(
                                payload["assertions"]["promote_updates_status"]
                            )
                            self.assertTrue(
                                payload["assertions"]["reject_updates_status"]
                            )
                            self.assertGreaterEqual(
                                payload["report"]["rejected_count"], 1
                            )
                            if mode == "empty":
                                self.assertFalse(
                                    payload["assertions"]["vampire_import_seen"]
                                )
                            if fmt:
                                self.assertEqual(json.loads(output["stdout"]), payload)
                            else:
                                self.assertEqual(
                                    output["stdout"].splitlines()[0], "ok: True"
                                )
                            self.assertTrue(result["replay_artifacts"])
                    except Exception as error:
                        failure = error
                self.assertFalse(manager.active)
                if failure is not None:
                    raise failure

        for mode, fmt, budget in [
            ("success", True, 6),
            ("success", False, 6),
            ("empty", True, 6),
            ("malformed", True, 6),
            ("success", True, 5),
        ]:
            asyncio.run(scenario(mode, fmt, budget))


if __name__ == "__main__":
    unittest.main(verbosity=2)
