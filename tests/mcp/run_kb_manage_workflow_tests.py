#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic native KB fixtures through real MCP and Lunar/PRISM.

There are no provider/compiler boundaries in this local command workflow:
embeddings use the real deterministic hash vectors. No substitutions are used.
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
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
import hashlib
import io
import json
import re
import tempfile
import unittest
from unittest.mock import patch
import yaml
import manage_premise_kb as native
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_kb_manage_workflow/workflow.yaml"


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


def stable(value, directory):
    text = (
        json.dumps(value, sort_keys=True)
        .replace(str(directory / "native"), "<KB>")
        .replace(str(directory / "oracle"), "<KB>")
    )
    return re.sub(r"\d{4}-\d\d-\d\dT[0-9:.]+(?:\+00:00|Z)", "<time>", text)


class ManageTests(unittest.TestCase):
    def test_runtime(self):
        base = ROOT / "artifacts/workflow_hub"
        base.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix="manage-fixture-", dir=base
        ) as directory:
            asyncio.run(self.scenario(Path(directory)))

    async def scenario(self, directory):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_kb_manage_workflow")
        self.assertEqual(document["lifecycle"], "active")
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        scope = {
            "__name__": "_kb_manage_original",
            "__file__": str(ROOT / "scripts/manage_premise_kb.py"),
        }
        exec(
            compile(
                (ROOT / "tests/mcp/fixtures/kb_manage_original.py.txt").read_text(),
                scope["__file__"],
                "exec",
            ),
            scope,
        )
        corpus = directory / "corpus.jsonl"
        rows = [
            {
                "id": "first",
                "status": "generated_candidate",
                "informal_statement": "Every fixture zero is zero",
                "latex_statement": "fixture zero equals zero",
                "domain_tags": ["fixture"],
            },
            {
                "id": "second",
                "status": "generated_candidate",
                "informal_statement": "Every fixture one is one",
                "domain_tags": ["other"],
            },
            {"id": "duplicate", "informal_statement": "Every fixture zero is zero"},
        ]
        corpus.write_text("\n" + "\n".join(json.dumps(row) for row in rows) + "\n\n")
        artifacts = directory / "reports"
        for i in [2, 0, 1]:
            report = artifacts / str(i) / "discovery_report.json"
            report.parent.mkdir(parents=True)
            report.write_text(
                json.dumps(
                    {
                        "ok": False,
                        "informal_statement": f"Fixture report {i}",
                        "winner": {
                            "formulas": [
                                {"role": "conjecture", "formula": f"p{i}(a)"},
                                {"role": "conjecture", "formula": f"q{i}(a)"},
                            ]
                        },
                    }
                )
            )
        entry_file = directory / "entry.json"
        entry_file.write_text(
            json.dumps(
                {
                    "id": "queued",
                    "status": "source_backed_candidate",
                    "informal_statement": "Queued fixture",
                }
            )
        )
        manager = SessionManager()
        self.assertIn(
            "register_kb_manage_tools(mcp, _graph_layout_write_policy)",
            (ROOT / "scripts/mcp_server.py").read_text(),
        )
        # Isolate the production registrations from unrelated optional SymPy services.
        server = 'import sys;sys.path.insert(0,"scripts");from mcp.server.fastmcp import FastMCP;from kb_manage_tools import register_kb_manage_tools;mcp=FastMCP("kb-manage");register_kb_manage_tools(mcp);mcp.run(transport="stdio")'
        async with manager.open(
            "kb-manage",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {},
        ) as remote:
            tools = [
                t.model_dump(by_alias=True, exclude_none=True)
                for t in await remote.tools()
            ]

            def compile_doc(doc, inventory=tools):
                assets = snapshot(doc)
                workflow = workflow_documents([DESCRIPTOR], assets)[0]
                return compile_workflow("mcp:kb-manage", workflow, inventory), assets

            compiled, assets = compile_doc(document)
            self.assertTrue(compiled["runnable"], compiled["diagnostics"])
            self.assertTrue(compiled["runtime_source"])
            self.assertEqual(set(compiled["bindings"]), set(document["operations"]))
            self.assertFalse(compile_doc(document, [])[0]["runnable"])

            async def authorize():
                pass

            async def run(command, doc=None, root=None):
                selected, received = compile_doc(doc) if doc else (compiled, assets)
                return await execute(
                    selected,
                    received,
                    {
                        "extra_args": [
                            "--kb-root",
                            str(root or directory / "native"),
                            "--json",
                            *command,
                        ]
                    },
                    remote,
                    authorize,
                )

            async def compare(command, expected_group):
                result = await run(command)
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(
                    [c["tool"] for c in result["calls"]],
                    [
                        "mathformer_kb_manage_prepare",
                        "mathformer_kb_manage_" + expected_group,
                        "mathformer_kb_manage_finish",
                    ],
                )
                stream = io.StringIO()
                with (
                    patch.object(
                        sys,
                        "argv",
                        [
                            "manage_premise_kb.py",
                            "--kb-root",
                            str(directory / "oracle"),
                            "--json",
                            *command,
                        ],
                    ),
                    redirect_stdout(stream),
                ):
                    code = scope["main"]()
                self.assertEqual(code, result["outputs"]["exit_code"])
                payload = json.loads(stream.getvalue())
                self.assertEqual(
                    stable(payload, directory),
                    stable(result["outputs"]["payload"], directory),
                )
                self.assertEqual(
                    stable(stream.getvalue(), directory),
                    stable(result["outputs"]["stdout"], directory),
                )
                self.assertTrue(result["runtime"]["effect_records"])
                self.assertTrue(result["replay_artifacts"])
                for filename in (
                    "entries.jsonl",
                    "rejected.jsonl",
                    "curation_queue.jsonl",
                    "curation_log.jsonl",
                ):
                    path = directory / "native" / filename
                    if path.exists():
                        other = directory / "oracle" / filename
                        self.assertEqual(
                            stable(
                                [
                                    json.loads(line)
                                    for line in path.read_text().splitlines()
                                ],
                                directory,
                            ),
                            stable(
                                [
                                    json.loads(line)
                                    for line in other.read_text().splitlines()
                                ],
                                directory,
                            ),
                        )
                return result["outputs"]["payload"]

            await compare(["init"], "initialize")
            self.assertEqual(
                (await compare(["search", "--query", "empty"], "query"))["hits"], []
            )
            self.assertEqual(
                (
                    await compare(
                        [
                            "ingest-vampire",
                            "--artifact-root",
                            str(directory / "absent-reports"),
                        ],
                        "ingest",
                    )
                )["candidate_count"],
                0,
            )
            self.assertEqual(
                native.prepare(["search", "--query", "x"])["options"]["k"], 10
            )
            self.assertEqual(
                native.prepare(["build-bloom"])["options"]["false_positive_rate"], 0.01
            )
            self.assertEqual(
                native.prepare(["build-embeddings"])["options"]["dimension"], 512
            )
            self.assertIsNone(native.prepare(["ingest-vampire"])["options"]["limit"])
            payload = await compare(["ingest-corpus", "--path", str(corpus)], "ingest")
            self.assertEqual(payload["candidate_count"], 3)
            self.assertEqual(sum(r["added"] for r in payload["results"]), 2)
            await compare(["build-bloom"], "index")
            await compare(["build-embeddings"], "index")
            has = await compare(
                ["has", "--statement", rows[0]["informal_statement"]], "query"
            )
            self.assertEqual(has["membership"]["resolved_entry_ids"], ["first"])
            hits = (
                await compare(["search", "--query", "fixture", "--k", "1"], "query")
            )["hits"]
            self.assertEqual(len(hits), 1)
            hits = (
                await compare(["search", "--query", "fixture", "--k", "10"], "query")
            )["hits"]
            self.assertEqual(
                len(hits), 2
            )  # finite exhaustion + multiple surfaces deduplicated
            self.assertEqual(len({h["entry_id"] for h in hits}), 2)
            self.assertEqual(
                (
                    await compare(
                        ["search", "--query", "fixture", "--proved-only"], "query"
                    )
                )["hits"],
                [],
            )
            await compare(
                [
                    "distance",
                    "--query",
                    rows[0]["informal_statement"],
                    "--entry-id",
                    "first",
                ],
                "query",
            )
            await compare(["refresh-canonical"], "refresh")
            await compare(
                [
                    "enqueue-source",
                    "--entry-file",
                    str(entry_file),
                    "--reason",
                    "fixture",
                ],
                "enqueue",
            )
            await compare(
                [
                    "enqueue-web",
                    "--url",
                    "https://example.invalid/fixture",
                    "--statement",
                    "Web fixture",
                ],
                "enqueue",
            )
            await compare(
                ["reject", "--entry-id", "second", "--notes", "fixture rejection"],
                "curate",
            )
            await compare(["report"], "report")
            human = await execute(
                compiled,
                assets,
                {"extra_args": ["--kb-root", str(directory / "native"), "report"]},
                remote,
                authorize,
            )
            self.assertEqual(human["status"], "accepted", human)
            stream = io.StringIO()
            with (
                patch.object(
                    sys,
                    "argv",
                    [
                        "manage_premise_kb.py",
                        "--kb-root",
                        str(directory / "oracle"),
                        "report",
                    ],
                ),
                redirect_stdout(stream),
            ):
                self.assertEqual(scope["main"](), 0)
            self.assertEqual(
                stable(human["outputs"]["stdout"], directory),
                stable(stream.getvalue(), directory),
            )
            # No promotions performed. The real storage proof gate must fail.
            before = {
                p.name: p.read_bytes() for p in (directory / "native").glob("*.jsonl")
            }
            failed = await run(
                ["promote", "--entry-id", "first", "--status", "proved_formal"]
            )
            self.assertEqual(failed["status"], "failed", failed)
            self.assertEqual(len(failed["calls"]), 2)
            self.assertIsNone(failed["outputs"])
            self.assertEqual(
                before,
                {
                    p.name: p.read_bytes()
                    for p in (directory / "native").glob("*.jsonl")
                },
            )
            for command in (
                ["distance", "--query", "x", "--entry-id", "missing"],
                ["ingest-corpus", "--path", str(directory / "missing")],
                ["not-a-command"],
            ):
                failed = await run(command)
                self.assertEqual(failed["status"], "failed", failed)
                self.assertLessEqual(len(failed["calls"]), 2)
            for limit, count in [("0", 0), ("1", 2), ("-1", 4)]:
                payload = await compare(
                    [
                        "ingest-vampire",
                        "--artifact-root",
                        str(artifacts),
                        "--limit",
                        limit,
                    ],
                    "ingest",
                )
                self.assertEqual(payload["candidate_count"], count)
            self.assertEqual(
                (
                    await compare(
                        ["ingest-vampire", "--artifact-root", str(artifacts)], "ingest"
                    )
                )["candidate_count"],
                6,
            )
            await compare(["ingest-seeds"], "ingest")
            failed = await run(
                ["init"], root=directory.parent.parent.parent / "outside"
            )
            self.assertEqual(failed["status"], "failed")
            bounded = deepcopy(document)
            bounded["policy"]["limits"]["max_operation_calls"] = 2
            failed = await run(["report"], bounded)
            self.assertEqual(failed["status"], "failed", failed)
            self.assertIn("budget", str(failed).lower())
            self.assertEqual(
                sum(bool(c.get("transport_call_performed")) for c in failed["calls"]), 2
            )
            timed = deepcopy(document)
            timed["policy"]["limits"]["wall_time_seconds"] = 1
            selected, received = compile_doc(timed)

            async def pending():
                await asyncio.Event().wait()

            with self.assertRaises(TimeoutError):
                await execute(
                    selected, received, {"extra_args": ["report"]}, remote, pending
                )
            # Both native formatting modes and false payload status.
            for json_output in (True, False):
                state = native.prepare(["report"] + (["--json"] if json_output else []))
                stream = io.StringIO()
                with redirect_stdout(stream):
                    self.assertEqual(native.finish(state, {"ok": False}), 3)
                self.assertIn("false" if json_output else "False", stream.getvalue())
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                native.prepare([])
        self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
