#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic input fixtures through real MCP and Lunar/PRISM.

This generator has no model/provider or external compiler boundary. Tests use
real canonicalization and the real PRISM parser, checker, compiler and runtime.
Only temporary JSONL destinations are written; no hub or production run occurs.
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
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import tempfile
import unittest
from unittest.mock import patch
import yaml
from theorem_seed_tools import source, SOURCE
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_kb_generate_seeds_workflow/workflow.yaml"


def oracle():
    path = ROOT / "tests/mcp/fixtures/theorem_seed_original.py.txt"
    spec = importlib.util.spec_from_loader(
        "seed_oracle", SourceFileLoader("seed_oracle", str(path))
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.REPO_ROOT = ROOT
    return module


def scrub(entries):
    entries = deepcopy(entries)
    for entry in entries:
        for record in entry["provenance"]:
            record.pop("retrieved_at", None)
    return entries


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
        for row in {r["path"]: r for r in document["provenance"]["sources"]}.values()
    ]


class SeedTests(unittest.TestCase):
    def test_native_equivalence_and_selection(self):
        native, original = source(), oracle()
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "nested/seeds.jsonl"
            cases = [
                [],
                ["--family", "group", "--include-theorems"],
                ["--family", "relation", "--include-axioms"],
                ["--family", "set", "--include-theorems"],
                [
                    "--family",
                    "group",
                    "--family",
                    "all",
                    "--family",
                    "group",
                    "--include-axioms",
                    "--include-theorems",
                ],
            ]
            for flags in cases:
                for reporting in ([], ["--json"]):
                    args = flags + reporting + ["--output", str(output)]
                    rows, streams = [], []
                    for module in (original, native):
                        out = io.StringIO()
                        with (
                            patch.object(sys, "argv", ["seed", *args]),
                            redirect_stdout(out),
                        ):
                            self.assertEqual(module.main(), 0)
                        rows.append(
                            scrub(
                                [
                                    json.loads(line)
                                    for line in output.read_text().splitlines()
                                ]
                            )
                        )
                        streams.append(out.getvalue())
                    self.assertEqual(rows[0], rows[1])
                    self.assertEqual(streams[0], streams[1])
                    options = native.parse_options(args)
                    expected = [
                        s["id"]
                        for s in native.SEEDS
                        if s["family"] in options["families"]
                        and s["kind"] in options["kinds"]
                    ]
                    self.assertEqual([e["id"] for e in rows[1]], expected)
                    self.assertTrue(
                        all(e["status"] == "generated_candidate" for e in rows[1])
                    )
            # Empty collection and relative paths are supported by the native writer.
            empty = native.parse_options(["--output", str(output)])
            with redirect_stdout(io.StringIO()):
                self.assertEqual(
                    native.write_report(empty, {"index": 13, "entries": []})["report"][
                        "entry_count"
                    ],
                    0,
                )
            self.assertEqual(output.read_bytes(), b"")
            relative = os.path.relpath(output, ROOT)
            with redirect_stdout(io.StringIO()):
                result = native.write_report(
                    {**empty, "output": relative}, {"index": 13, "entries": []}
                )
            self.assertEqual(
                Path(result["report"]["output"]).resolve(), output.resolve()
            )
            for flags, code in [
                (["--help"], 0),
                (["--family", "bad"], 2),
                (["--unknown"], 2),
            ]:
                for module in (original, native):
                    with (
                        patch.object(sys, "argv", ["seed", *flags]),
                        redirect_stdout(io.StringIO()),
                        redirect_stderr(io.StringIO()),
                        self.assertRaises(SystemExit) as error,
                    ):
                        module.main()
                    self.assertEqual(error.exception.code, code)
            self.assertFalse(native.scan_done({"index": 12}))
            self.assertTrue(native.scan_done({"index": 13}))
            with self.assertRaises(IndexError):
                native.inspect_seed(empty, {"index": 13})
            with self.assertRaises(KeyError):
                native.retain_advance({"index": 0, "entries": []}, {})

    def test_registered_mcp_lunar(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_kb_generate_seeds_workflow")
        self.assertEqual(document["lifecycle"], "active")
        self.assertIn(
            SOURCE,
            [
                row["path"]
                for row in {
                    r["path"]: r for r in document["provenance"]["sources"]
                }.values()
            ],
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        server = "scripts/theorem_seed_tools.py"
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "seeds.jsonl"
            async with manager.open(
                "seed",
                StdioConfig(command=sys.executable, args=[server], cwd=str(ROOT)),
                {},
            ) as remote:
                try:
                    tools = [
                        tool.model_dump(by_alias=True, exclude_none=True)
                        for tool in await remote.tools()
                    ]

                    def compile(doc, inventory=None):
                        assets = snapshot(doc)
                        workflow = workflow_documents([DESCRIPTOR], assets)[0]
                        return (
                            compile_workflow(
                                "mcp:seed",
                                workflow,
                                tools if inventory is None else inventory,
                            ),
                            assets,
                        )

                    compiled, assets = compile(document)
                    self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                    self.assertTrue(compiled["runtime_source"])
                    self.assertEqual(
                        set(compiled["bindings"]), set(document["operations"])
                    )
                    self.assertFalse(compile(document, [])[0]["runnable"])

                    async def authorize():
                        pass

                    async def run(flags, doc=None):
                        selected, received = compile(doc) if doc else (compiled, assets)
                        return await execute(
                            selected, received, {"extra_args": flags}, remote, authorize
                        )

                    for flags, count, retains in [
                        ([], 13, 13),
                        (["--family", "set", "--include-theorems"], 1, 1),
                    ]:
                        result = await run([*flags, "--json", "--output", str(output)])
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertEqual(
                            result["outputs"]["report"]["entry_count"], count
                        )
                        self.assertEqual(result["outputs"]["exit_code"], 0)
                        self.assertEqual(
                            json.loads(result["outputs"]["stdout"]),
                            result["outputs"]["report"],
                        )
                        rows = [
                            json.loads(line) for line in output.read_text().splitlines()
                        ]
                        self.assertEqual(
                            [e["id"] for e in rows],
                            result["outputs"]["report"]["entry_ids"],
                        )
                        expected = [
                            source().make_entry(s).to_dict()
                            for s in source().SEEDS
                            if s["id"] in result["outputs"]["report"]["entry_ids"]
                        ]
                        self.assertEqual(scrub(rows), scrub(expected))
                        names = [c["tool"] for c in result["calls"]]
                        self.assertEqual(len(names), 41)
                        self.assertEqual(
                            names.count("mathformer_theorem_seed_retain"), retains
                        )
                        self.assertEqual(
                            names.count("mathformer_theorem_seed_skip"), 13 - retains
                        )
                        self.assertEqual(names[0], "mathformer_theorem_seed_parse")
                        self.assertEqual(names[-1], "mathformer_theorem_seed_write")
                        for index in range(13):
                            self.assertEqual(
                                names[1 + 3 * index], "mathformer_theorem_seed_inspect"
                            )
                            self.assertEqual(
                                names[3 + 3 * index], "mathformer_theorem_seed_done"
                            )
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["replay_artifacts"])
                    before = output.read_bytes()
                    help_result = await run(["--help", "--output", str(output)])
                    self.assertEqual(help_result["status"], "accepted", help_result)
                    self.assertIsNone(help_result["outputs"]["report"])
                    self.assertIn(
                        "--include-theorems", help_result["outputs"]["stdout"]
                    )
                    self.assertEqual(
                        [c["tool"] for c in help_result["calls"]],
                        [
                            "mathformer_theorem_seed_parse",
                            "mathformer_theorem_seed_halt",
                            "mathformer_theorem_seed_help",
                        ],
                    )
                    self.assertEqual(output.read_bytes(), before)
                    bad = await run(["--family", "invalid", "--output", str(output)])
                    self.assertEqual(bad["status"], "failed", bad)
                    self.assertEqual(len(bad["calls"]), 1)
                    self.assertEqual(output.read_bytes(), before)
                    # Real filesystem failure propagates from the last call, no retry.
                    bad = await run(["--output", str(Path(folder))])
                    self.assertEqual(bad["status"], "failed", bad)
                    self.assertEqual(len(bad["calls"]), 41)
                    self.assertIsNone(bad["outputs"])
                    for bound in (1, 12):
                        limited = deepcopy(document)
                        limited["flow"]["steps"][1]["max_iterations"] = bound
                        bad = await run(["--output", str(output)], limited)
                        self.assertEqual(bad["status"], "failed", bad)
                        self.assertEqual(len(bad["calls"]), 1 + 3 * bound)
                        self.assertEqual(output.read_bytes(), before)
                    limited = deepcopy(document)
                    limited["policy"]["limits"]["max_operation_calls"] = 2
                    bad = await run(["--output", str(output)], limited)
                    self.assertEqual(bad["status"], "failed", bad)
                    self.assertEqual(
                        sum(
                            bool(c.get("transport_call_performed"))
                            for c in bad["calls"]
                        ),
                        2,
                    )
                    self.assertEqual(output.read_bytes(), before)
                    # Impossible selection exercises skip-only traversal with source operations.
                    state = {"index": 0, "entries": []}
                    options = {
                        "families": [],
                        "kinds": [],
                        "output": str(output),
                        "json": False,
                    }
                    for _ in range(13):
                        inspected = await remote.call(
                            "mathformer_theorem_seed_inspect",
                            {"options": options, "state": state},
                        )
                        self.assertFalse(inspected["matches"])
                        state = (
                            await remote.call(
                                "mathformer_theorem_seed_skip", {"state": state}
                            )
                        )["state"]
                    self.assertEqual(state, {"index": 13, "entries": []})
                    self.assertTrue(
                        (
                            await remote.call(
                                "mathformer_theorem_seed_done", {"state": state}
                            )
                        )["done"]
                    )
                    written = await remote.call(
                        "mathformer_theorem_seed_write",
                        {"options": options, "state": state},
                    )
                    self.assertEqual(written["report"]["entry_count"], 0)
                    self.assertEqual(output.read_bytes(), b"")
                except Exception:
                    import traceback

                    traceback.print_exc()
                    raise
        self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
