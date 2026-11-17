#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Original CLI parity and registered MCP execution through real Lunar/PRISM."""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT),
    str(ROOT / "tests/mcp/fixtures"),
]
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
from vampire_group_example_tools import source, register_vampire_group_example_tools
from vampire_group_example_boundary import compiler
from backends.atp.MathformerATP import vampire as v
from mcp.server.fastmcp import FastMCP
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_example_vampire_group_workflow/workflow.yaml"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
FIXTURE = ROOT / "tests/mcp/fixtures/vampire_group_example_boundary.py"


def assets(doc):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(doc))] + [
        asset(row["path"], (ROOT / row["path"]).read_text())
        for row in doc["provenance"]["sources"]
    ]


def clean(value):
    if isinstance(value, dict):
        return {
            k: clean(val)
            for k, val in value.items()
            if k not in ("generated_at", "elapsed_seconds")
        }
    if isinstance(value, list):
        return [clean(val) for val in value]
    return (
        re.sub(r"\d{4}-\d\d-\d\dT[0-9:.]+\+00:00", "<time>", value)
        if isinstance(value, str)
        else value
    )


def oracle(root):
    scope = {
        "__file__": str(ROOT / "examples/vampire_complex_group_theorem_to_proofs.py"),
        "__name__": "original_group_example",
    }
    exec(
        (ROOT / "tests/mcp/fixtures/vampire_group_example_original.py.txt").read_text(),
        scope,
    )
    scope["ARTIFACT_ROOT"] = root / "output"
    return scope["main"]


def invoke(main, root):
    out = io.StringIO()
    with (
        patch.dict(os.environ, {"VAMPIRE_BIN": "fixture-vampire"}),
        patch.object(v.subprocess, "run", side_effect=compiler),
        contextlib.redirect_stdout(out),
    ):
        try:
            result = main()
        except (TypeError, RuntimeError) as error:
            result = type(error).__name__, str(error)
    return result, out.getvalue()


class GroupExampleTests(unittest.TestCase):
    def test_original_entrypoint_parity(self):
        for mode in [
            "success",
            "nofalse",
            "unproved",
            "error",
            "unsatisfiable",
            "contradictory",
        ]:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "fixture-mode").write_text(mode)
                with patch.object(source(), "ARTIFACT_ROOT", root / "output"):
                    results = []
                    files = []
                    histories = []
                    for main in [oracle(root), source().main]:
                        shutil.rmtree(root / "output", ignore_errors=True)
                        (root / "calls.jsonl").unlink(missing_ok=True)
                        results.append(invoke(main, root))
                        files.append(
                            {
                                p.name: (
                                    clean(json.loads(p.read_text()))
                                    if p.suffix == ".json"
                                    else clean(p.read_text())
                                )
                                for p in (root / "output").iterdir()
                                if p.is_file()
                            }
                        )
                        histories.append((root / "calls.jsonl").read_text())
                    self.assertEqual(*results)
                    self.assertEqual(*files)
                    self.assertEqual(*[clean(h) for h in histories])
                    code = results[0][0]
                    self.assertEqual(
                        code if isinstance(code, int) else code[0],
                        {
                            "nofalse": 3,
                            "unproved": "TypeError",
                            "error": "RuntimeError",
                        }.get(mode, 0),
                    )
                    if mode not in ("unproved", "error"):
                        excerpt = (
                            results[0][1]
                            .split("Formal proof excerpt:\n")[1]
                            .split("\n\nInformal proof:")[0]
                        )
                        self.assertEqual(len(excerpt.splitlines()), 23)
                        self.assertTrue(excerpt.endswith("..."))

    def test_continuations_and_guard(self):
        async def run():
            server = FastMCP("group-test")
            sessions = register_vampire_group_example_tools(server)
            statement = source().INPUT_PATH.read_text()
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "fixture-mode").write_text("success")
                with (
                    patch.object(source(), "ARTIFACT_ROOT", root / "output"),
                    patch.dict(os.environ, {"VAMPIRE_BIN": "fixture-vampire"}),
                    patch.object(v.subprocess, "run", side_effect=compiler),
                ):
                    init = (
                        await server.call_tool(
                            "mathformer_group_example_initialize_search",
                            {"statement": statement},
                        )
                    )[1]
                    state = init["state"]
                    self.assertEqual(state["evidence"], {"candidate_count": 1})
                    attempt = (
                        await server.call_tool(
                            "mathformer_group_example_direct_attempt", {"state": state}
                        )
                    )[1]["attempt"]
                    self.assertTrue(attempt["evidence"]["proof_found"])
                    with self.assertRaises(Exception):
                        await server.call_tool(
                            "mathformer_group_example_direct_attempt", {"state": state}
                        )
                    carried = (
                        await server.call_tool(
                            "mathformer_group_example_carry_candidate",
                            {"state": state, "attempt": attempt},
                        )
                    )[1]
                    self.assertTrue(carried["done"])
                    self.assertEqual(carried["state"]["evidence"]["attempt_count"], 1)
                    report = (
                        await server.call_tool(
                            "mathformer_group_example_finalize_report",
                            {"statement": statement, "state": carried["state"]},
                        )
                    )[1]["report"]
                    self.assertEqual(report["attempt_count"], 1)
                    self.assertEqual(len(sessions), 0)
                    with self.assertRaises(Exception):
                        await server.call_tool(
                            "mathformer_group_example_finalize_report",
                            {"statement": statement, "state": carried["state"]},
                        )
            denied = FastMCP("denied")

            def guard():
                raise PermissionError("read-only fixture")

            register_vampire_group_example_tools(denied, guard)
            with self.assertRaises(Exception):
                await denied.call_tool(
                    "mathformer_group_example_initialize_search",
                    {"statement": statement},
                )

        asyncio.run(run())

    def test_real_lunar_execution(self):
        doc = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(doc["id"], "hub_example_vampire_group_workflow")
        self.assertEqual(doc["lifecycle"], "active")
        for row in doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )

        async def scenario(mode, exhausted=False):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "fixture-mode").write_text(mode)
                manager = SessionManager()
                async with manager.open(
                    "group-example",
                    StdioConfig(
                        command=sys.executable,
                        args=[str(FIXTURE), str(root)],
                        cwd=str(ROOT),
                    ),
                    {},
                ) as remote:
                    try:
                        tools = [
                            t.model_dump(by_alias=True, exclude_none=True)
                            for t in await remote.tools()
                        ]
                        document = deepcopy(doc)
                        if exhausted:
                            document["flow"]["steps"][2]["until"] = {"literal": False}
                        snapshot = assets(document)
                        compiled = compile_workflow(
                            "mcp:group-example",
                            workflow_documents([DESCRIPTOR], snapshot)[0],
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
                            compiled, snapshot, {}, remote, authorize
                        )
                        calls = [
                            json.loads(line)
                            for line in (root / "calls.jsonl").read_text().splitlines()
                        ]
                        self.assertEqual(
                            len(calls), 1
                        )  # no retries; stop at proof or finite exhaustion
                        if mode == "error" or exhausted:
                            self.assertEqual(result["status"], "failed", result)
                            self.assertIsNone(result["outputs"])
                            self.assertFalse(
                                (root / "output/discovery_report.json").exists()
                            )
                            self.assertEqual(
                                len(result["calls"]), 3 if mode == "error" else 4
                            )
                            return
                        persisted = json.loads(
                            (root / "output/discovery_report.json").read_text()
                        )
                        self.assertEqual(persisted["candidate_count"], 1)
                        self.assertEqual(persisted["attempt_count"], 1)
                        self.assertFalse(persisted["premise_loop"]["enabled"])
                        self.assertIsNone(
                            persisted["attempts"][0]["premise_selection_report"]
                        )
                        if mode == "unproved":
                            self.assertEqual(result["status"], "failed", result)
                            self.assertEqual(len(result["calls"]), 6)
                            self.assertIsNone(persisted["winning_informal_proof"])
                            self.assertEqual(result["calls"][-1]["status"], "rejected")
                            return
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertEqual(len(result["calls"]), 7)
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["replay_artifacts"])
                        self.assertEqual(
                            result["outputs"]["exit_code"],
                            3 if mode == "nofalse" else 0,
                        )
                        self.assertEqual(result["outputs"]["report"], persisted)
                        history = (root / "calls.jsonl").read_text()
                        shutil.rmtree(root / "output")
                        (root / "calls.jsonl").unlink()
                        original, stdout = invoke(oracle(root), root)
                        self.assertEqual(original, result["outputs"]["exit_code"])
                        expected = json.loads(
                            (root / "output/discovery_report.json").read_text()
                        )
                        self.assertEqual(clean(persisted), clean(expected))
                        self.assertEqual(
                            clean(history), clean((root / "calls.jsonl").read_text())
                        )
                    except BaseException:
                        import traceback

                        traceback.print_exc()
                        raise
                self.assertFalse(manager.active)

        for mode in [
            "success",
            "nofalse",
            "unproved",
            "error",
            "unsatisfiable",
            "contradictory",
        ]:
            with self.subTest(mode=mode):
                asyncio.run(scenario(mode))
        asyncio.run(scenario("success", exhausted=True))


if __name__ == "__main__":
    unittest.main(verbosity=2)
