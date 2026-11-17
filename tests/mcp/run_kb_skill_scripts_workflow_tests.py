#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Isolated native subprocesses, registered MCP tools and real Lunar/PRISM.

There are no provider/compiler boundaries in this deterministic KB workflow.
Fixtures are local Vampire report inputs; no prover or production action runs.
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
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
import tempfile
import types
import unittest
from unittest.mock import patch
import yaml
from kb_skill_scripts_tools import source, register_kb_skill_scripts_tools
from mcp.server.fastmcp import FastMCP
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_kb_skill_scripts_workflow/workflow.yaml"


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


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base = ROOT / "artifacts/workflow_hub"
        base.mkdir(parents=True, exist_ok=True)
        cls.temp = tempfile.TemporaryDirectory(prefix="kb-skills-fixture-", dir=base)
        cls.directory = Path(cls.temp.name)
        cls.vampire = cls.directory / "reports"
        # The fixed limit is eight sorted reports, rather than eight entries.
        for i in reversed(range(10)):
            folder = cls.vampire / f"{i:02}"
            folder.mkdir(parents=True)
            (folder / "discovery_report.json").write_text(
                json.dumps(
                    {
                        "ok": False,
                        "informal_statement": f"Fixture predicate {i}",
                        "winner": {
                            "formulas": [
                                {"role": "conjecture", "formula": f"fixture_{i}(a)"}
                            ]
                        },
                    }
                )
            )
        cls.context = {"vampire_artifact_root": str(cls.vampire)}

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_native_commands_and_failure(self):
        native = source()
        # Exercise actual run_json's nonzero and malformed-report failure paths.
        with self.assertRaisesRegex(RuntimeError, "command failed"):
            native.run_json(
                [sys.executable, "-c", 'import sys;print("failure");sys.exit(7)']
            )
        with self.assertRaises(json.JSONDecodeError):
            native.run_json([sys.executable, "-c", 'print("not json")'])

        # Service write admission rejects before reset and child dispatch.
        def deny():
            raise ValueError("read only")

        server = FastMCP("readonly")
        register_kb_skill_scripts_tools(server, deny)

        async def check():
            result = await server.call_tool(
                "mathformer_kb_skill_scripts_prepare",
                {
                    "request": {
                        "artifact_root": str(self.directory / "readonly"),
                        "json": True,
                    }
                },
            )
            return result

        with self.assertRaisesRegex(Exception, "read only"):
            asyncio.run(check())
        self.assertFalse((self.directory / "readonly").exists())

    def test_real_lunar_mcp(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_kb_skill_scripts_workflow")
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
        # Use the production registration function without unrelated optional backends.
        command = 'import sys;sys.path.insert(0,"scripts");from mcp.server.fastmcp import FastMCP;from kb_skill_scripts_tools import register_kb_skill_scripts_tools;mcp=FastMCP("kb-skills");register_kb_skill_scripts_tools(mcp);mcp.run(transport="stdio")'
        async with manager.open(
            "kb-skills",
            StdioConfig(command=sys.executable, args=["-c", command], cwd=str(ROOT)),
            {},
        ) as remote:
            tools = [
                tool.model_dump(by_alias=True, exclude_none=True)
                for tool in await remote.tools()
            ]

            def compile(doc, inventory=None):
                assets = snapshot(doc)
                result = compile_workflow(
                    "mcp:kb-skills",
                    workflow_documents([DESCRIPTOR], assets)[0],
                    tools if inventory is None else inventory,
                )
                return result, assets

            compiled, assets = compile(document)
            self.assertTrue(compiled["runnable"], compiled["diagnostics"])
            self.assertTrue(compiled["runtime_source"])
            self.assertEqual(set(compiled["bindings"]), set(document["operations"]))
            missing, _ = compile(document, [])
            self.assertFalse(missing["runnable"])

            async def authorize():
                pass

            async def run(root, doc=None, context=None):
                selected, received = compile(doc) if doc else (compiled, assets)
                return await execute(
                    selected,
                    received,
                    {
                        "request": {"artifact_root": str(root), "json": True},
                        "context": context or self.context,
                    },
                    remote,
                    authorize,
                )

            output = self.directory / "runtime"
            output.mkdir()
            (output / "stale").write_text("reset me")
            result = await run(output)
            self.assertEqual(result["status"], "accepted", result)
            self.assertEqual(result["outputs"]["exit_code"], 0, result)
            payload = result["outputs"]["result"]
            self.assertTrue(payload["ok"])
            self.assertEqual(
                payload["top_hit_ids"][0], "group.inverse_triple_product_reverse_order"
            )
            self.assertTrue(all(payload["assertions"].values()))
            self.assertFalse((output / "stale").exists())
            self.assertEqual(json.loads(result["outputs"]["stdout"]), payload)
            self.assertEqual(
                [c["tool"] for c in result["calls"]],
                [
                    "mathformer_kb_skill_scripts_" + step
                    for step in ("prepare", "generate", "index", "finish")
                ],
            )
            self.assertTrue(result["runtime"]["effect_records"])
            self.assertTrue(result["replay_artifacts"])
            # Transported steps retain complete reports, fixed arguments, and index data.
            paths = {
                "artifact_root": str(output),
                "seed_jsonl": str(output / "generated_seeds.jsonl"),
                "kb_root": str(output / "kb"),
            }
            generated = (
                await remote.call(
                    "mathformer_kb_skill_scripts_generate", {"paths": paths}
                )
            )["generated"]
            self.assertGreaterEqual(generated["entry_count"], 10)
            indexed = (
                await remote.call(
                    "mathformer_kb_skill_scripts_index",
                    {"paths": paths, "context": self.context},
                )
            )["indexed"]
            self.assertEqual(indexed["vampire_candidate_count"], 8)
            self.assertEqual(
                indexed["added_count"], 0
            )  # second ingestion retains duplicate history
            self.assertEqual(indexed["duplicate_count"], generated["entry_count"] + 8)
            self.assertTrue(Path(indexed["embedding_index"]).is_file())
            metadata = json.loads(
                (Path(indexed["embedding_index"]).parent / "metadata.json").read_text()
            )
            self.assertEqual(metadata["dimension"], 256)
            self.assertEqual(metadata["entry_count"], generated["entry_count"] + 8)
            self.assertEqual(len(indexed["smoke_hits"]), 5)
            # Ordinary assertion failure emits a payload and exit 3, not an exception.
            empty = deepcopy(indexed)
            empty["smoke_hits"] = []
            finished = await remote.call(
                "mathformer_kb_skill_scripts_finish",
                {
                    "request": {"json": False},
                    "paths": paths,
                    "generated": generated,
                    "indexed": empty,
                },
            )
            self.assertEqual(finished["exit_code"], 3)
            self.assertEqual(
                finished["result"]["assertions"]["smoke_query_finds_triple"], []
            )
            self.assertTrue(finished["stdout"].startswith("ok: False\n"))
            # Frozen original: relocate only the hardcoded report input into the fixture.
            # Algorithms and subprocess commands remain the original entrypoint's.
            text = (
                ROOT / "tests/mcp/fixtures/kb_skill_scripts_original.py.txt"
            ).read_text()
            original = types.ModuleType("original_kb")
            original.__file__ = str(ROOT / "tests/kb/run_premise_kb_skill_scripts.py")
            exec(
                compile_builtin(
                    text.replace('"artifacts/vampire_atp"', repr(str(self.vampire))),
                    original.__file__,
                    "exec",
                ),
                original.__dict__,
            )
            stream = io.StringIO()
            with (
                patch.object(
                    sys, "argv", ["original", "--artifact-root", str(output), "--json"]
                ),
                redirect_stdout(stream),
            ):
                self.assertEqual(original.main(), 0)
            self.assertEqual(json.loads(stream.getvalue()), payload)
            # Empty report traversal terminates normally and keeps the seed-only result.
            absent = self.directory / "absent-reports"
            success = await run(
                self.directory / "empty", context={"vampire_artifact_root": str(absent)}
            )
            self.assertEqual(success["status"], "accepted", success)
            self.assertEqual(
                success["outputs"]["result"]["indexed_entry_count"],
                generated["entry_count"],
            )
            # Child failure aborts before finish; malformed JSON is not retried.
            broken = self.directory / "broken-reports"
            broken.mkdir()
            (broken / "discovery_report.json").write_text("{malformed")
            failed = await run(
                self.directory / "failed",
                context={"vampire_artifact_root": str(broken)},
            )
            self.assertEqual(failed["status"], "failed", failed)
            self.assertIsNone(failed["outputs"])
            self.assertEqual(len(failed["calls"]), 3)
            self.assertEqual(failed["calls"][-1]["status"], "rejected")
            # Normalization operation ceiling is enforced by Lunar, not child retries.
            limited = deepcopy(document)
            limited["policy"]["limits"]["max_operation_calls"] = 1
            bounded = self.directory / "bounded"
            failed = await run(bounded, limited)
            self.assertEqual(failed["status"], "failed", failed)
            self.assertEqual(
                sum(bool(c.get("transport_call_performed")) for c in failed["calls"]), 1
            )
            self.assertFalse((bounded / "generated_seeds.jsonl").exists())
            self.assertIn("budget", str(failed).lower())
            timed = deepcopy(document)
            timed["policy"]["limits"]["wall_time_seconds"] = 1
            selected, received = compile(timed)

            async def pending():
                await asyncio.Event().wait()

            with self.assertRaises(TimeoutError):
                await execute(
                    selected,
                    received,
                    {
                        "request": {"artifact_root": str(output), "json": True},
                        "context": self.context,
                    },
                    remote,
                    pending,
                )
        self.assertFalse(manager.active)


compile_builtin = compile
if __name__ == "__main__":
    unittest.main(verbosity=2)
