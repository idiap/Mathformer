#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402
"""Real local KB, MCP, PRISM parser/checker/compiler/runtime regression.

All data live in temporary directories. Embeddings are native deterministic
hash vectors; no model provider, external compiler, credentials or ATP is used.
The isolated server registers production tools without unrelated services.
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
import shutil
import tempfile
import unittest
from unittest.mock import patch
import yaml
from mcp.server.fastmcp import FastMCP
from premise_kb_index_tools import source, register_premise_kb_index_tools
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute, ExecutionRejected

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_kb_index_workflow/workflow.yaml"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
SERVER = ROOT / "tests/mcp/fixtures/premise_kb_index_server.py"


def fixture(root):
    def entry(identifier, text):
        return {
            "id": identifier,
            "status": "generated_candidate",
            "domain_tags": ["fixture"],
            "informal_statement": text,
        }

    seed = root / "seed.jsonl"
    corpus = root / "corpus.jsonl"
    seed.write_text(
        "\n" + json.dumps(entry("first", "Every fixture zero is zero")) + "\n\n"
    )
    corpus.write_text(
        "\n".join(
            json.dumps(row)
            for row in [
                entry("duplicate", "Every fixture zero is zero"),
                entry("second", "Every fixture one is one"),
            ]
        )
        + "\n"
    )
    artifacts = root / "vampire"
    # Creation order deliberately differs from report sort order; each report
    # has two entries, so a one-report limit must still ingest two candidates.
    for i in [2, 0, 1]:
        directory = artifacts / f"{i:02d}"
        directory.mkdir(parents=True)
        (directory / "discovery_report.json").write_text(
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
    return seed, corpus, artifacts


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
    if isinstance(value, dict):
        return {key: stable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [stable(item) for item in value]
    if isinstance(value, str):
        return re.sub(r"\d{4}-\d\d-\d\dT[0-9:.]+(?:\+00:00|Z)", "<time>", value)
    return value


class KBIndexTests(unittest.TestCase):
    def test_original_cli_equivalence_outputs_data_and_histories(self):
        scope = {
            "__name__": "_frozen_indexer",
            "__file__": str(
                ROOT
                / "skills/premise-kb/premise-kb-indexer/scripts/index_premise_kb.py"
            ),
        }
        exec(
            (ROOT / "tests/mcp/fixtures/premise_kb_index_original.py.txt").read_text(),
            scope,
        )
        for switches in [
            [],
            ["--json"],
            ["--build-bloom", "--json"],
            ["--smoke-query", "fixture", "--json"],
            ["--build-embeddings", "--smoke-query", "fixture", "--json"],
        ]:
            with (
                self.subTest(switches=switches),
                tempfile.TemporaryDirectory() as directory,
            ):
                root = Path(directory)
                seed, corpus, artifacts = fixture(root)
                kb = root / "kb"
                args = [
                    "index",
                    "--kb-root",
                    str(kb),
                    "--seed-jsonl",
                    str(seed),
                    "--corpus-jsonl",
                    str(corpus),
                    "--vampire-artifact-root",
                    str(artifacts),
                    "--vampire-limit",
                    "-1",
                    "--embedding-dimension",
                    "32",
                    *switches,
                ]
                observations = []
                for main in [scope["main"], source().main]:
                    output = io.StringIO()
                    with (
                        patch.object(sys, "argv", args),
                        contextlib.redirect_stdout(output),
                    ):
                        code = main()
                    files = {
                        str(p.relative_to(kb)): stable(p.read_text())
                        for p in kb.rglob("*")
                        if p.is_file()
                    }
                    observations.append((code, stable(output.getvalue()), files))
                    shutil.rmtree(kb)
                self.assertEqual(*observations)
                self.assertEqual(observations[0][0], 0)

    def test_shared_steps_guards_order_exhaustion_and_report_limits(self):
        native = source()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            seed, corpus, artifacts = fixture(root)
            for limit, count in [(None, 6), (0, 0), (1, 2), (-1, 4), (20, 6)]:
                state = native.initialize(
                    [
                        "--kb-root",
                        str(root / f"kb{limit}"),
                        "--corpus-jsonl",
                        str(corpus),
                        "--seed-jsonl",
                        str(seed),
                        "--vampire-artifact-root",
                        str(artifacts),
                        *([] if limit is None else ["--vampire-limit", str(limit)]),
                    ]
                )
                self.assertEqual(state["files"], [str(seed), str(corpus)])
                self.assertEqual(state["options"]["embedding_dimension"], 512)
                self.assertEqual(state["options"]["vampire_limit"], limit)
                first = native.ingest_file(state)
                self.assertFalse(first["done"])
                last = native.ingest_file(first["state"])
                self.assertTrue(last["done"])
                self.assertEqual(last["state"]["cursor"], 2)
                self.assertEqual(
                    [row["added"] for row in state["results"]], [True, False, True]
                )
                state = native.ingest_vampire(state)
                self.assertEqual(state["vampire_count"], count)
                self.assertEqual(len(state["results"]), 3 + count)
                self.assertIs(native.retain(state), state)
            # No native cap: exhaust 1025 empty files without rolling back prior state.
            empty = root / "empty.jsonl"
            empty.write_text("\n\n")
            state = native.initialize(
                ["--kb-root", str(root / "many"), *[f"--seed-jsonl={empty}"] * 1025]
            )
            for i in range(1025):
                result = native.ingest_file(state)
                self.assertEqual(result["done"], i == 1024)
            self.assertEqual(state["cursor"], 1025)
            self.assertEqual(state["results"], [])

    def test_native_failure_equivalence_and_partial_writes(self):
        native = source()
        scope = {
            "__name__": "_frozen_failure",
            "__file__": str(
                ROOT
                / "skills/premise-kb/premise-kb-indexer/scripts/index_premise_kb.py"
            ),
        }
        exec(
            (ROOT / "tests/mcp/fixtures/premise_kb_index_original.py.txt").read_text(),
            scope,
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            seed, corpus, artifacts = fixture(root)
            corpus.write_text("{invalid\n")
            observations = []
            for main in [scope["main"], native.main]:
                kb = root / "kb"
                output = io.StringIO()
                with (
                    patch.object(
                        sys,
                        "argv",
                        [
                            "index",
                            "--kb-root",
                            str(kb),
                            "--seed-jsonl",
                            str(seed),
                            "--corpus-jsonl",
                            str(corpus),
                        ],
                    ),
                    contextlib.redirect_stdout(output),
                ):
                    with self.assertRaises(json.JSONDecodeError):
                        main()
                self.assertEqual(output.getvalue(), "")
                observations.append(
                    {
                        str(p.relative_to(kb)): p.read_text()
                        for p in kb.rglob("*")
                        if p.is_file()
                    }
                )
                shutil.rmtree(kb)
            self.assertEqual(*observations)
            self.assertEqual(len(observations[0]["entries.jsonl"].splitlines()), 1)
            self.assertEqual(len(observations[0]["curation_log.jsonl"].splitlines()), 1)

    def test_mcp_write_policy_before_initialization_and_mutations(self):
        async def run():
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / "kb"
                server = FastMCP("guarded")

                def deny(path):
                    raise ValueError("denied fixture write")

                register_premise_kb_index_tools(server, deny)
                with self.assertRaises(Exception) as caught:
                    await server.call_tool(
                        "mathformer_kb_index_initialize",
                        {"extra_args": ["--kb-root", str(root)]},
                    )
                self.assertIn("denied fixture write", str(caught.exception))
                self.assertFalse(root.exists())
                state = source().initialize(["--kb-root", str(root)])
                with self.assertRaises(Exception):
                    await server.call_tool(
                        "mathformer_kb_index_build_embeddings", {"state": state}
                    )
                self.assertFalse((root / "embeddings/index.json").exists())

        asyncio.run(run())

    def test_real_lunar_registered_bindings_branches_failures_and_budgets(self):
        doc = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(doc["id"], "hub_kb_index_workflow")
        self.assertEqual(doc["lifecycle"], "active")
        self.assertEqual(
            doc["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 1034},
        )
        self.assertEqual(doc["policy"]["failure"]["retry"]["max_attempts"], 1)
        authored = json.loads(
            (
                ROOT
                / "skills/control/workflow-contract-validator/references/premise-kb-index.workflow.json"
            ).read_text()
        )
        self.assertEqual(doc, authored)
        for row in doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )

        async def run():
            manager = SessionManager()
            async with manager.open(
                "kb-index",
                StdioConfig(command=sys.executable, args=[str(SERVER)], cwd=str(ROOT)),
                {},
            ) as remote:
                tools = [
                    tool.model_dump(by_alias=True, exclude_none=True)
                    for tool in await remote.tools()
                ]
                self.assertEqual(
                    {t["name"] for t in tools},
                    {"mathformer_kb_index_" + name for name in doc["operations"]},
                )

                async def scenario(mode):
                    with tempfile.TemporaryDirectory() as directory:
                        root = Path(directory)
                        seed, corpus, artifacts = fixture(root)
                        kb = root / "kb"
                        document = deepcopy(doc)
                        args = ["--kb-root", str(kb)]
                        if mode != "empty":
                            args += [
                                "--seed-jsonl",
                                str(seed),
                                "--corpus-jsonl",
                                str(corpus),
                            ]
                        if mode in ["all", "forced", "vampire-failure"]:
                            args += [
                                "--vampire-artifact-root",
                                str(artifacts),
                                "--vampire-limit",
                                "1",
                                "--build-bloom",
                                "--smoke-query",
                                "fixture",
                                "--embedding-dimension",
                                "32",
                                "--json",
                            ]
                        if mode == "all":
                            args += ["--build-embeddings"]
                        if mode == "file-failure":
                            corpus.write_text("{invalid\n")
                        if mode == "vampire-failure":
                            # First report would succeed, second fails before any Vampire entry is inserted.
                            args[args.index("--vampire-limit") + 1] = "2"
                            (artifacts / "01/discovery_report.json").write_text(
                                "{invalid"
                            )
                        if mode == "parse-failure":
                            args += ["--unknown-option"]
                        if mode in ["loop-exhaustion", "last-at-bound"]:
                            document["flow"]["steps"][1]["max_iterations"] = 1
                            if mode == "last-at-bound":
                                args = ["--kb-root", str(kb), "--seed-jsonl", str(seed)]
                        if mode == "budget":
                            document["policy"]["limits"]["max_operation_calls"] = 2
                        assets = snapshot(document)
                        compiled = compile_workflow(
                            "mcp:kb-index",
                            workflow_documents([DESCRIPTOR], assets)[0],
                            tools,
                        )
                        self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                        self.assertTrue(compiled["runtime_source"])
                        self.assertEqual(
                            set(compiled["bindings"]), set(doc["operations"])
                        )

                        async def allow():
                            pass

                        result = await execute(
                            compiled, assets, {"extra_args": args}, remote, allow
                        )
                        calls = result["calls"]
                        if mode in [
                            "file-failure",
                            "vampire-failure",
                            "parse-failure",
                            "loop-exhaustion",
                            "budget",
                        ]:
                            self.assertEqual(result["status"], "failed", result)
                            self.assertIsNone(result["outputs"])
                            self.assertFalse(
                                any(c["tool"].endswith("_report") for c in calls)
                            )
                            if mode == "parse-failure":
                                self.assertFalse(kb.exists())
                                self.assertEqual(len(calls), 1)
                            else:
                                entries = (
                                    (kb / "entries.jsonl").read_text().splitlines()
                                )
                                self.assertEqual(
                                    len(entries), 2 if mode == "vampire-failure" else 1
                                )
                                self.assertFalse((kb / "bloom/manifest.json").exists())
                            return
                        self.assertEqual(result["status"], "accepted", result)
                        out = result["outputs"]
                        payload = out["result"]
                        self.assertEqual(out["exit_code"], 0)
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["replay_artifacts"])
                        self.assertEqual(
                            sum(c["tool"].endswith("_ingest_file") for c in calls),
                            (
                                0
                                if mode == "empty"
                                else 1 if mode == "last-at-bound" else 2
                            ),
                        )
                        self.assertEqual(
                            payload["duplicate_count"],
                            (
                                0
                                if mode in ["empty", "last-at-bound"]
                                else 2 if mode in ["all", "forced"] else 1
                            ),
                        )
                        self.assertEqual(
                            payload["entry_count"],
                            (
                                0
                                if mode == "empty"
                                else (
                                    1
                                    if mode == "last-at-bound"
                                    else 3 if mode in ["all", "forced"] else 2
                                )
                            ),
                        )
                        history = (kb / "curation_log.jsonl").read_text().splitlines()
                        self.assertEqual(len(history), payload["added_count"])
                        if mode in ["all", "forced"]:
                            self.assertEqual(json.loads(out["stdout"]), payload)
                            self.assertEqual(payload["vampire_candidate_count"], 2)
                            self.assertEqual(
                                sum(
                                    c["tool"].endswith("_build_embeddings")
                                    for c in calls
                                ),
                                1,
                            )
                            self.assertTrue(payload["smoke_hits"])
                            self.assertLessEqual(len(payload["smoke_hits"]), 5)
                            self.assertEqual(
                                json.loads(
                                    (kb / "embeddings/metadata.json").read_text()
                                )["dimension"],
                                32,
                            )
                            self.assertEqual(
                                json.loads((kb / "bloom/manifest.json").read_text())[
                                    "entry_count"
                                ],
                                3,
                            )
                        else:
                            self.assertIn("ok: True\n", out["stdout"])
                            self.assertIsNone(payload["embedding_index"])
                            self.assertEqual(payload["smoke_hits"], [])
                            self.assertEqual(payload["bloom_paths"], {})

                for mode in [
                    "empty",
                    "plain",
                    "all",
                    "forced",
                    "last-at-bound",
                    "file-failure",
                    "vampire-failure",
                    "parse-failure",
                    "loop-exhaustion",
                    "budget",
                ]:
                    with self.subTest(mode=mode):
                        await scenario(mode)
                # The descriptor token cap rejects before native initialization.
                assets = snapshot(doc)
                compiled = compile_workflow(
                    "mcp:kb-index", workflow_documents([DESCRIPTOR], assets)[0], tools
                )

                async def allow():
                    pass

                with self.assertRaises(ExecutionRejected):
                    await execute(
                        compiled,
                        assets,
                        {"extra_args": ["--json"] * 1025},
                        remote,
                        allow,
                    )
            self.assertFalse(manager.active)

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main(verbosity=2)
