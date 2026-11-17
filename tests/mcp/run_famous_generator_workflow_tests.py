#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native generator, actual MCP interfaces, and real Lunar PRISM execution.

The source has no provider or external compiler boundary. The deterministic
catalog and isolated output paths are the fixtures; no production step is mocked.
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
from copy import deepcopy
from contextlib import redirect_stdout, redirect_stderr
import hashlib
import io
import json
import re
import tempfile
import unittest
import yaml
from famous_generator_tools import source, register_famous_generator_tools
from mcp.server.fastmcp import FastMCP
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_kb_generate_famous_corpus_workflow/workflow.yaml"
SERVER = ROOT / "tests/mcp/fixtures/famous_generator_server.py"


def snapshot(doc):
    def asset(path, text):
        return {
            "path": path,
            "content": text,
            "encoding": "text",
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
        }

    return [asset(DESCRIPTOR, json.dumps(doc))] + [
        asset(p, (ROOT / p).read_text())
        for p in dict.fromkeys(r["path"] for r in doc["provenance"]["sources"])
    ]


def stable(text):
    return re.sub(r"\d{4}-\d\d-\d\dT[0-9:.]+(?:\+00:00|Z)", "<time>", text)


class GeneratorTests(unittest.TestCase):
    def test_original_equivalence_and_native_failures(self):
        native = source()
        scope = {
            "__name__": "original_seed",
            "__file__": str(
                ROOT
                / "skills/premise-kb/premise-kb-theorem-seed-generator/scripts/generate_famous_theorem_axiom_corpus.py"
            ),
        }
        exec(
            (ROOT / "tests/mcp/fixtures/famous_generator_original.py.txt").read_text(),
            scope,
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "nested/corpus.jsonl"
            for limit in [500, 1, 0, -1, -501, 501]:
                for fmt in [False, True]:
                    results = []
                    for main in [scope["main"], native.main]:
                        output.parent.mkdir(exist_ok=True)
                        output.write_text("stale")
                        old = sys.argv
                        sys.argv = [
                            "generator",
                            "--limit",
                            str(limit),
                            "--output",
                            str(output),
                            *(["--json"] if fmt else []),
                        ]
                        stream = io.StringIO()
                        try:
                            with redirect_stdout(stream):
                                try:
                                    outcome = main()
                                except ValueError as error:
                                    outcome = (type(error).__name__, str(error))
                        finally:
                            sys.argv = old
                        results.append(
                            (outcome, stream.getvalue(), stable(output.read_text()))
                        )
                    self.assertEqual(*results)
                    if limit == 501:
                        self.assertEqual(output.read_text(), "stale")
                    else:
                        count = len(list(range(500))[:limit])
                        self.assertEqual(len(output.read_text().splitlines()), count)
                        self.assertEqual(results[0][0], 0 if count == limit else 3)
            parsed = native.parse_seed([])
            self.assertEqual(parsed["options"]["limit"], 500)
            state = parsed["state"]
            domain = next(iter(native.DOMAIN_CATALOG.values()))
            names = domain["names"]
            try:
                domain["names"] = names[:-1]
                with self.assertRaisesRegex(ValueError, "exactly 20 names"):
                    native.open_domain(state)
            finally:
                domain["names"] = names
            self.assertEqual(native.infer_kind("Axiom lemma"), "axiom")
            self.assertEqual(native.infer_kind("Some lemma"), "lemma")
            self.assertEqual(native.infer_kind("Some theorem"), "theorem")
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                native.parse_seed(["--limit", "wrong"])

    def test_registered_write_guard(self):
        async def run():
            mcp = FastMCP("guard")

            def deny(path):
                raise ValueError("write denied")

            register_famous_generator_tools(mcp, deny)
            with tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "corpus"
                output.write_text("keep")
                with self.assertRaisesRegex(Exception, "write denied"):
                    await mcp.call_tool(
                        "mathformer_seed_write",
                        {
                            "entries": [],
                            "options": {
                                "output": str(output),
                                "limit": 0,
                                "json": True,
                            },
                        },
                    )
                self.assertEqual(output.read_text(), "keep")

        asyncio.run(run())

    def test_lunar_registered_tools_and_runtime(self):
        doc = yaml.safe_load(Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text())
        self.assertEqual(doc["id"], "hub_kb_generate_famous_corpus_workflow")
        self.assertEqual(doc["lifecycle"], "active")
        self.assertEqual(
            doc["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 553},
        )
        self.assertEqual(doc["policy"]["failure"]["retry"]["max_attempts"], 1)
        for row in doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )

        async def scenario():
            manager = SessionManager()
            with tempfile.TemporaryDirectory() as directory:
                async with manager.open(
                    "seed",
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
                        with self.assertRaisesRegex(
                            Exception, "rejected the operation"
                        ):
                            await remote.call(
                                "mathformer_seed_parse", {"argv": ["--help"]}
                            )
                        self.assertEqual(len(await remote.tools()), 6)

                        async def allow():
                            pass

                        for mode in [
                            "complete",
                            "exhausted",
                            "budget",
                            "parse_failure",
                            "io_failure",
                        ]:
                            print("  runtime fixture: " + mode, flush=True)
                            document = deepcopy(doc)
                            output = Path(directory) / mode / "corpus"
                            argv = ["--output", str(output), "--limit", "-1", "--json"]
                            if mode == "exhausted":
                                document["flow"]["steps"][1]["body"]["steps"][1][
                                    "max_iterations"
                                ] = 19
                            if mode == "budget":
                                document["policy"]["limits"]["max_operation_calls"] = 2
                            if mode == "parse_failure":
                                argv = ["--limit", "wrong"]
                            if mode == "io_failure":
                                # Drive a real native I/O error without replacing a step.
                                output.parent.write_text("parent is a file")
                            assets = snapshot(document)
                            compiled = compile_workflow(
                                "mcp:seed",
                                workflow_documents([DESCRIPTOR], assets)[0],
                                tools,
                            )
                            self.assertTrue(
                                compiled["runnable"], compiled["diagnostics"]
                            )
                            self.assertTrue(compiled["runtime_source"])
                            self.assertEqual(
                                set(compiled["bindings"]), set(doc["operations"])
                            )
                            result = await execute(
                                compiled, assets, {"argv": argv}, remote, allow
                            )
                            if mode == "complete":
                                self.assertEqual(
                                    result["status"], "accepted", str(result)[:2000]
                                )
                                self.assertEqual(len(result["calls"]), 553)
                                names = [c["tool"] for c in result["calls"]]
                                self.assertEqual(
                                    names.count("mathformer_seed_append"), 500
                                )
                                self.assertEqual(
                                    names.count("mathformer_seed_open"), 25
                                )
                                out = result["outputs"]
                                self.assertEqual(out["exit_code"], 3)
                                self.assertEqual(out["result"]["entry_count"], 499)
                                self.assertTrue(out["result"]["ok"])
                                self.assertEqual(
                                    json.loads(out["stdout"]), out["result"]
                                )
                                records = [
                                    json.loads(line)
                                    for line in output.read_text().splitlines()
                                ]
                                self.assertEqual(
                                    [r["id"] for r in records],
                                    out["result"]["entry_ids"],
                                )
                                expected = [
                                    e.to_dict()
                                    for e in source().build_entries(limit=-1)
                                ]
                                self.assertEqual(
                                    stable(json.dumps(records, sort_keys=True)),
                                    stable(json.dumps(expected, sort_keys=True)),
                                )
                                self.assertTrue(result["runtime"]["effect_records"])
                                self.assertTrue(result["replay_artifacts"])
                                # Real tool boundary keeps the over-limit error and zero slice.
                                state = {
                                    "domain_index": 25,
                                    "name_index": 0,
                                    "names": [],
                                    "entries": records,
                                }
                                with self.assertRaisesRegex(
                                    Exception, "rejected the operation"
                                ):
                                    await remote.call(
                                        "mathformer_seed_slice",
                                        {"state": state, "options": {"limit": 501}},
                                    )
                                sliced = await remote.call(
                                    "mathformer_seed_slice",
                                    {"state": state, "options": {"limit": 0}},
                                )
                                self.assertEqual(sliced, {"entries": []})
                            else:
                                self.assertEqual(
                                    result["status"], "failed", str(result)[:2000]
                                )
                                self.assertIsNone(result["outputs"])
                                self.assertFalse(output.exists())
                                if mode == "exhausted":
                                    self.assertEqual(len(result["calls"]), 21)
                                    self.assertEqual(
                                        result["failure_disposition"], "fail"
                                    )
                                elif mode == "budget":
                                    self.assertEqual(len(result["calls"]), 3)
                                    self.assertIn(
                                        "budget", result["calls"][-1]["error"]
                                    )
                                elif mode == "parse_failure":
                                    self.assertEqual(len(result["calls"]), 1)
                                else:
                                    self.assertEqual(len(result["calls"]), 553)
                    except Exception:
                        import traceback

                        traceback.print_exc()
                        raise
                self.assertFalse(manager.active)

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main(verbosity=2)
