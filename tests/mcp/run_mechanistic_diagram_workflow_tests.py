#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic source/registered-MCP/real-PRISM fixtures; no external provider.

The source has no provider or external compiler boundary. Preset dictionaries,
CLI argv and temporary filesystem paths are its complete deterministic fixtures.
The Lunar parser, checker, compiler and runtime are used without substitution.
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
from mechanistic_diagram_tools import source
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_paper_mechanistic_diagram_model_workflow/workflow.yaml"


def oracle():
    path = ROOT / "tests/mcp/fixtures/mechanistic_diagram_original.py.txt"
    spec = importlib.util.spec_from_loader(
        "diagram_original", SourceFileLoader("diagram_original", str(path))
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def invoke(module, argv):
    stream, errors = io.StringIO(), io.StringIO()
    with (
        patch.object(sys, "argv", ["diagram", *argv]),
        redirect_stdout(stream),
        redirect_stderr(errors),
    ):
        try:
            code = module.main()
        except SystemExit as error:
            code = error.code
    return code, stream.getvalue(), errors.getvalue()


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


class DiagramTests(unittest.TestCase):
    def test_original_cli_equivalence(self):
        old, native = oracle(), source()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "nested/diagram.json"
            for preset, counts in [
                ("mathformer-framework", (9, 13)),
                ("observability-stack", (7, 8)),
            ]:
                for is_json in [False, True]:
                    argv = ["--preset", preset, "--output", str(output)] + (
                        ["--json"] if is_json else []
                    )
                    expected = invoke(old, argv)
                    data = output.read_bytes()
                    output.unlink()
                    self.assertEqual(invoke(native, argv), expected)
                    self.assertEqual(output.read_bytes(), data)
                    model = json.loads(data)
                    self.assertEqual((len(model["nodes"]), len(model["edges"])), counts)
                    self.assertEqual(
                        data.decode(),
                        json.dumps(model, indent=2, sort_keys=True) + "\n",
                    )
            for argv in [
                [],
                ["--help"],
                ["--preset", "invalid"],
                ["--output", str(output), "--unknown"],
            ]:
                self.assertEqual(invoke(native, argv), invoke(old, argv))
            self.assertEqual(invoke(native, ["--output", str(output)])[0], 0)
            self.assertEqual(
                json.loads(output.read_text()), native.PRESETS["mathformer-framework"]()
            )
            blocker = Path(directory) / "blocker"
            blocker.write_text("blocked")
            for module in [old, native]:
                with self.assertRaises(OSError):
                    invoke(module, ["--output", str(blocker / "diagram.json")])

    def test_real_registered_mcp_and_lunar(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_paper_mechanistic_diagram_model_workflow")
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
        server = str(ROOT / "scripts/mechanistic_diagram_tools.py")
        failure = None
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            async with manager.open(
                "diagram",
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
                        selected = workflow_documents([DESCRIPTOR], assets)[0]
                        qualified = compile_workflow(
                            "mcp:diagram",
                            selected,
                            tools if inventory is None else inventory,
                        )
                        return qualified, assets

                    workflow, assets = compile(document)
                    self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                    self.assertTrue(workflow["runtime_source"])
                    self.assertEqual(
                        set(workflow["bindings"]), set(document["operations"])
                    )
                    self.assertFalse(compile(document, [])[0]["runnable"])

                    async def authorize():
                        pass

                    async def run(argv, doc=None):
                        selected, received = compile(doc) if doc else (workflow, assets)
                        return await execute(
                            selected, received, {"argv": argv}, remote, authorize
                        )

                    for preset, counts in [
                        ("mathformer-framework", (9, 13)),
                        ("observability-stack", (7, 8)),
                    ]:
                        for json_report in [False, True]:
                            output = (
                                directory
                                / preset
                                / ("json.json" if json_report else "text.json")
                            )
                            argv = ["--preset", preset, "--output", str(output)] + (
                                ["--json"] if json_report else []
                            )
                            result = await run(argv)
                            self.assertEqual(result["status"], "accepted", result)
                            payload = json.loads(output.read_text())
                            self.assertEqual(payload, source().PRESETS[preset]())
                            self.assertEqual(result["outputs"]["diagram"], payload)
                            report = (
                                {
                                    "ok": True,
                                    "output": str(output),
                                    "node_count": counts[0],
                                    "edge_count": counts[1],
                                }
                                if json_report
                                else f"Wrote {output}"
                            )
                            self.assertEqual(
                                result["outputs"],
                                {"diagram": payload, "report": report, "exit_code": 0},
                            )
                            self.assertEqual(
                                [c["tool"] for c in result["calls"]],
                                [
                                    "mathformer_diagram_" + s
                                    for s in ["parse", "construct", "write", "report"]
                                ],
                            )
                            self.assertTrue(result["runtime"]["effect_records"])
                            self.assertTrue(result["runtime"]["provenance"])
                            self.assertTrue(result["replay_artifacts"])
                    # Help exits successfully before construction, even with an output.
                    absent = directory / "help-must-not-write.json"
                    result = await run(["--help", "--output", str(absent)])
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertIsNone(result["outputs"]["diagram"])
                    self.assertEqual(result["outputs"]["exit_code"], 0)
                    self.assertIn("--preset", result["outputs"]["report"])
                    self.assertEqual(len(result["calls"]), 1)
                    self.assertFalse(absent.exists())
                    for argv in [
                        [],
                        ["--preset", "unknown", "--output", str(absent)],
                        ["--output", str(absent), "--unexpected"],
                    ]:
                        result = await run(argv)
                        self.assertEqual(result["status"], "failed", result)
                        self.assertIsNone(result["outputs"])
                        self.assertEqual(len(result["calls"]), 1)
                        self.assertEqual(result["calls"][0]["status"], "rejected")
                        self.assertFalse(absent.exists())
                    # Real filesystem failure propagates, does not report or retry.
                    blocker = directory / "blocker"
                    blocker.write_text("blocked")
                    failed = await run(["--output", str(blocker / "diagram.json")])
                    self.assertEqual(failed["status"], "failed", failed)
                    self.assertIsNone(failed["outputs"])
                    self.assertEqual(len(failed["calls"]), 3)
                    self.assertEqual(failed["calls"][-1]["status"], "rejected")
                    # Host bounds add no native iteration or exhaustion step.
                    bounded = deepcopy(document)
                    bounded["policy"]["limits"]["max_operation_calls"] = 2
                    failed = await run(["--output", str(absent)], bounded)
                    self.assertEqual(failed["status"], "failed")
                    self.assertIn("budget", str(failed).lower())
                    self.assertEqual(
                        sum(
                            bool(c.get("transport_call_performed"))
                            for c in failed["calls"]
                        ),
                        2,
                    )
                    self.assertFalse(absent.exists())
                    timed = deepcopy(document)
                    timed["policy"]["limits"]["wall_time_seconds"] = 1
                    compiled, received = compile(timed)

                    async def pending():
                        await asyncio.Event().wait()

                    with self.assertRaises(TimeoutError):
                        await execute(
                            compiled,
                            received,
                            {"argv": ["--output", str(absent)]},
                            remote,
                            pending,
                        )
                    self.assertFalse(absent.exists())
                except Exception as error:
                    failure = error
        self.assertFalse(manager.active)
        if failure:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
