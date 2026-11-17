#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402
"""Real local corpus/KB steps, MCP registration, and Lunar PRISM execution.

No model or external compiler is used by this source. Deterministic fixtures
are the native catalog plus isolated empty, stale, truncated and malformed
artifact directories. All native subprocesses are local Python KB commands.
"""

from tempfile import gettempdir
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
from copy import deepcopy
import contextlib
import hashlib
import io
import importlib.util
import json
import re
import tempfile
import unittest
from unittest.mock import patch
import yaml
from famous_corpus_tools import source, register_famous_corpus_tools
from mcp.server.fastmcp import FastMCP
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_kb_famous_corpus_workflow/workflow.yaml"
SERVER = ROOT / "tests/mcp/fixtures/famous_corpus_server.py"


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
        for row in {r["path"]: r for r in doc["provenance"]["sources"]}.values()
    ]


class FamousTests(unittest.TestCase):
    def test_native_equivalence_and_observability(self):
        native = source()
        scope = {
            "__name__": "_original_famous",
            "__file__": str(ROOT / "tests/kb/run_famous_theorem_corpus.py"),
        }
        exec(
            (ROOT / "tests/mcp/fixtures/famous_corpus_original.py.txt").read_text(),
            scope,
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "artifacts"
            for fmt in [True, False]:
                results = []
                for main in [scope["main"], native.main]:
                    root.mkdir(exist_ok=True)
                    (root / "stale").write_text("old")
                    out = io.StringIO()
                    with (
                        patch.object(
                            sys,
                            "argv",
                            [
                                "famous",
                                "--artifact-root",
                                str(root),
                                *(["--json"] if fmt else []),
                            ],
                        ),
                        contextlib.redirect_stdout(out),
                    ):
                        code = main()
                    self.assertFalse((root / "stale").exists())
                    self.assertEqual(code, 0)
                    results.append(out.getvalue())

                # Only source-owned creation timestamps differ across native runs.
                def stable(text):
                    return re.sub(
                        r"\d{4}-\d\d-\d\dT[0-9:.]+(?:\+00:00|Z)", "<timestamp>", text
                    )

                self.assertEqual(*map(stable, results))
                if fmt:
                    payload = json.loads(results[0])
                    self.assertEqual(len(payload["assertions"]), 14)
                    self.assertTrue(all(payload["assertions"].values()))

    def test_native_failures_and_fixed_arguments(self):
        native = source()
        spec = importlib.util.spec_from_file_location(
            "_famous_catalog_fixture", native.GENERATOR
        )
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)
        entries = generator.build_entries(limit=500)
        self.assertEqual(len(entries), 500)
        self.assertEqual(generator.build_entries(limit=1)[0].id, entries[0].id)
        with self.assertRaisesRegex(ValueError, "Catalog has only"):
            generator.build_entries(limit=100000)
        with tempfile.TemporaryDirectory() as directory:
            paths = native.prepare({"artifact_root": directory})
            generated = native.generate_read(paths)
            self.assertEqual(len(generated["records"]), 500)
            self.assertEqual(len({r["id"] for r in generated["records"]}), 500)
            indexed = native.index(paths)
            self.assertEqual(indexed["vampire_candidate_count"], 0)
            self.assertEqual(indexed["duplicate_count"], 0)
            self.assertEqual(len(indexed["add_results"]), 500)
            self.assertLessEqual(len(indexed["smoke_hits"]), 5)
            self.assertEqual(
                json.loads(
                    (
                        Path(indexed["embedding_index"]).parent / "metadata.json"
                    ).read_text()
                )["dimension"],
                256,
            )
            probes = native.probe(paths, indexed)
            self.assertTrue(native.assess(paths, generated, indexed, probes)["ok"])
            generated["records"][0]["canonical_hashes"] = {}
            payload = native.assess(paths, generated, indexed, probes)
            self.assertFalse(payload["ok"])
            self.assertFalse(payload["assertions"]["all_have_hashes"])
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(native.emit(payload, 3), 3)
            self.assertEqual(json.loads(out.getvalue()), payload)
            # A real malformed input drives the native indexer subprocess failure.
            Path(paths["corpus_path"]).write_text("{invalid\n")
            with self.assertRaisesRegex(RuntimeError, "command failed:"):
                native.index(paths)
            with self.assertRaisesRegex(RuntimeError, "command failed:"):
                native.run_json([sys.executable, "-c", "raise SystemExit(7)"])

    def test_mcp_guard_before_reset_and_path_integrity(self):
        async def run():
            with tempfile.TemporaryDirectory() as directory:
                marker = Path(directory) / "keep"
                marker.write_text("old")
                mcp = FastMCP("denied")

                def deny(path):
                    raise ValueError("write denied")

                register_famous_corpus_tools(mcp, deny)
                with self.assertRaisesRegex(Exception, "write denied"):
                    await mcp.call_tool(
                        "mathformer_famous_prepare",
                        {"request": {"artifact_root": directory}},
                    )
                self.assertEqual(marker.read_text(), "old")
                with self.assertRaisesRegex(Exception, "native artifact context"):
                    await mcp.call_tool(
                        "mathformer_famous_index",
                        {
                            "paths": {
                                "artifact_root": directory,
                                "corpus_path": str(
                                    Path(gettempdir())
                                    / "mathformer-test-fixtures/wrong"
                                ),
                                "kb_root": directory + "/kb",
                            }
                        },
                    )

        asyncio.run(run())

    def test_real_mcp_lunar_compile_execute_branches_budgets_and_failure(self):
        doc = yaml.safe_load(Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text())
        self.assertEqual(doc["id"], "hub_kb_famous_corpus_workflow")
        self.assertEqual(doc["lifecycle"], "active")
        self.assertEqual(
            doc["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 6},
        )
        self.assertEqual(doc["policy"]["failure"]["retry"]["max_attempts"], 1)
        self.assertIn(
            "tests/kb/run_famous_theorem_corpus.py",
            [r["path"] for r in doc["provenance"]["sources"]],
        )
        for row in doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )

        async def scenario(mode):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / "artifacts"
                root.mkdir()
                (root / "stale").write_text("old")
                manager = SessionManager()
                failure = None
                async with manager.open(
                    "famous",
                    StdioConfig(
                        command=sys.executable, args=[str(SERVER)], cwd=str(ROOT)
                    ),
                    {},
                ) as remote:
                    try:
                        tools = [
                            t.model_dump(by_alias=True, exclude_none=True)
                            for t in await remote.tools()
                        ]
                        document = deepcopy(doc)
                        if mode == "budget":
                            document["policy"]["limits"]["max_operation_calls"] = 5
                        assets = snapshot(document)
                        compiled = compile_workflow(
                            "mcp:famous",
                            workflow_documents([DESCRIPTOR], assets)[0],
                            tools,
                        )
                        self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                        self.assertTrue(compiled["runtime_source"])
                        self.assertEqual(
                            set(compiled["bindings"]), set(doc["operations"])
                        )

                        # Inject test artifact damage after generation, forwarding every
                        # call to the real MCP service. No production step is replaced.
                        class ArtifactFixture:
                            async def tools(self):
                                return await remote.tools()

                            async def call(self, name, arguments=None):
                                response = await remote.call(name, arguments)
                                if (
                                    name == "mathformer_famous_generate_read"
                                    and mode in {"truncated", "malformed"}
                                ):
                                    path = root / "famous_theorems_axioms_500.jsonl"
                                    path.write_text(
                                        "{invalid\n"
                                        if mode == "malformed"
                                        else "\n".join(
                                            path.read_text().splitlines()[:-1]
                                        )
                                        + "\n"
                                    )
                                return response

                        async def authorize():
                            pass

                        result = await execute(
                            compiled,
                            assets,
                            {"request": {"artifact_root": str(root)}},
                            ArtifactFixture(),
                            authorize,
                        )
                        self.assertFalse((root / "stale").exists())
                        self.assertTrue(result["runtime"]["effect_records"])
                        if mode in {"budget", "malformed"}:
                            self.assertEqual(result["status"], "failed", result)
                            self.assertIsNone(result["outputs"])
                            self.assertEqual(
                                len(result["calls"]), 6 if mode == "budget" else 3
                            )
                            self.assertEqual(result["calls"][-1]["status"], "rejected")
                            if mode == "budget":
                                self.assertIn("budget", result["calls"][-1]["error"])
                            else:
                                self.assertFalse(
                                    (root / "kb/bloom/manifest.json").exists()
                                )
                        else:
                            self.assertEqual(result["status"], "accepted", result)
                            self.assertEqual(len(result["calls"]), 6)
                            output = result["outputs"]
                            self.assertEqual(
                                output["exit_code"], 0 if mode == "success" else 3
                            )
                            self.assertEqual(output["payload"]["ok"], mode == "success")
                            self.assertEqual(
                                json.loads(output["stdout"]), output["payload"]
                            )
                            if mode == "truncated":
                                self.assertFalse(
                                    output["payload"]["assertions"]["indexer_added_500"]
                                )
                                self.assertTrue(
                                    output["payload"]["assertions"][
                                        "exactly_500_entries"
                                    ]
                                )
                            self.assertTrue(result["replay_artifacts"])
                    except Exception as error:
                        failure = error
                self.assertFalse(manager.active)
                if failure is not None:
                    raise failure

        for mode in ["success", "truncated", "malformed", "budget"]:
            asyncio.run(scenario(mode))


if __name__ == "__main__":
    unittest.main(verbosity=2)
