#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Fixture traces through registered MCP and real Lunar PRISM compile/execute.

This deterministic source has no provider/model or external compiler boundary.
No provider substitution is necessary; the PRISM toolchain is always real.
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
from runtime_trace_tools import source
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_meta_skills_runtime_trace_record_workflow/workflow.yaml"
PREFIX = "mathformer_runtime_trace_"


def oracle():
    loader = SourceFileLoader(
        "trace_oracle", str(ROOT / "tests/mcp/fixtures/runtime_trace_original.py.txt")
    )
    module = importlib.util.module_from_spec(
        importlib.util.spec_from_loader(loader.name, loader)
    )
    loader.exec_module(module)
    module.REPO_ROOT = ROOT
    return module


def snapshot(document):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(path, (ROOT / path).read_text())
        for path in dict.fromkeys(r["path"] for r in document["provenance"]["sources"])
    ]


def timeless(rows):
    return [{k: v for k, v in row.items() if k != "timestamp_utc"} for row in rows]


class TraceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.native, self.original = source(), oracle()

    def argv(self, json_output=False, relative=False):
        paths = [
            self.directory / "nested/trace.jsonl",
            self.directory / "nested/trace.md",
        ]
        if relative:
            paths = [Path(os.path.relpath(p, ROOT)) for p in paths]
        return ["--output-jsonl", str(paths[0]), "--output-md", str(paths[1])] + (
            ["--json"] if json_output else []
        )

    def read(self):
        path = self.directory / "nested"
        return [
            json.loads(line) for line in (path / "trace.jsonl").read_text().splitlines()
        ], (path / "trace.md").read_text()

    def test_original_cli_equivalence_and_helpers(self):
        self.assertEqual(
            self.native.parse_check([]),
            dict(
                workflow="mathformerphysicslib.coherence",
                output_jsonl=str(self.native.DEFAULT_JSONL),
                output_md=str(self.native.DEFAULT_MD),
                json=False,
            ),
        )
        for relative in (True, False):
            for json_output in (True, False):
                argv = self.argv(json_output, relative)
                outcomes = []
                for module in (self.original, self.native):
                    stream = io.StringIO()
                    with (
                        patch.object(sys, "argv", ["recorder", *argv]),
                        redirect_stdout(stream),
                    ):
                        code = module.main()
                    rows, md = self.read()
                    outcomes.append((code, stream.getvalue(), timeless(rows), md))
                    self.assertEqual(len(rows), 7)
                    self.assertEqual(len({r["timestamp_utc"] for r in rows}), 1)
                    self.assertEqual(
                        [r["next_action"]["type"] for r in rows],
                        ["continue"] * 6 + ["none"],
                    )
                    self.assertEqual(
                        [r["event_id"].split(".")[3] for r in rows],
                        [f"{i:02}" for i in range(1, 8)],
                    )
                self.assertEqual(*outcomes)
        for argv in (["--workflow", "unsupported"], ["--invalid"], ["--output-md"]):
            codes = []
            for module in (self.original, self.native):
                with (
                    patch.object(sys, "argv", ["recorder", *argv]),
                    redirect_stderr(io.StringIO()),
                ):
                    with self.assertRaises(SystemExit) as caught:
                        module.main()
                codes.append(caught.exception.code)
            self.assertEqual(*codes)
        for module in (self.original, self.native):
            module.write_trace(
                [], self.directory / "empty.jsonl", self.directory / "empty.md"
            )
            self.assertEqual((self.directory / "empty.jsonl").read_text(), "")
            self.assertIn("Workflow: none", (self.directory / "empty.md").read_text())
            with self.assertRaises(FileNotFoundError):
                module.write_trace(
                    module.coherence_events(),
                    self.directory / "partial.jsonl",
                    self.directory / "missing/trace.md",
                )
            self.assertEqual(
                len((self.directory / "partial.jsonl").read_text().splitlines()), 7
            )

        class BrokenStream:
            def write(self, text):
                raise OSError("fixture stdout failure")

        with self.assertRaises(OSError):
            self.native.emit_success(
                {"json": False}, {"event_count": 7}, stdout=BrokenStream()
            )

    def test_authored_generator_retains_bindings(self):
        path = (
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py"
        )
        spec = importlib.util.spec_from_file_location("trace_normalizer", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        documents = module.inventory()
        selected = [
            d
            for d in documents
            if d["id"] == "hub_meta_skills_runtime_trace_record_workflow"
        ]
        self.assertEqual(len(selected), 1)
        self.assertEqual(
            selected[0],
            yaml.safe_load(Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()),
        )

    def test_registered_tools_lunar_execution_and_stops(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(
            document["id"], "hub_meta_skills_runtime_trace_record_workflow"
        )
        self.assertEqual(document["lifecycle"], "active")
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        async with manager.open(
            "trace",
            StdioConfig(
                command=(
                    str(ROOT / ".venv/bin/python")
                    if (ROOT / ".venv/bin/python").exists()
                    else sys.executable
                ),
                args=["-c", server],
                cwd=str(ROOT),
            ),
            {},
        ) as remote:
            tools = [
                t.model_dump(by_alias=True, exclude_none=True)
                for t in await remote.tools()
            ]

            def compile(doc, inventory=None):
                assets = snapshot(doc)
                compiled = compile_workflow(
                    "mcp:trace",
                    workflow_documents([DESCRIPTOR], assets)[0],
                    tools if inventory is None else inventory,
                )
                return compiled, assets

            workflow, assets = compile(document)
            self.assertTrue(workflow["runnable"], workflow["diagnostics"])
            self.assertTrue(workflow["runtime_source"])
            self.assertEqual(set(workflow["bindings"]), set(document["operations"]))
            self.assertFalse(compile(document, [])[0]["runnable"])

            async def allow():
                pass

            async def run(argv, doc=None):
                w, a = compile(doc) if doc else (workflow, assets)
                self.assertTrue(w["runnable"], w["diagnostics"])
                return await execute(w, a, {"argv": argv}, remote, allow)

            for json_output in (False, True):
                argv = self.argv(json_output, relative=True)
                # Overwrite behavior is part of the source contract.
                (self.directory / "nested").mkdir(exist_ok=True)
                (self.directory / "nested/trace.jsonl").write_text("stale\n")
                result = await run(argv)
                self.assertEqual(result["status"], "accepted", result)
                args = self.native.parse_check(argv)
                payload = dict(
                    ok=True,
                    event_count=7,
                    jsonl=args["output_jsonl"],
                    markdown=args["output_md"],
                )
                stream = io.StringIO()
                self.native.emit_success(args, payload, stdout=stream)
                self.assertEqual(
                    result["outputs"],
                    {
                        "payload": payload,
                        "completion": dict(exit_code=0, stdout=stream.getvalue()),
                    },
                )
                self.assertEqual(
                    [c["tool"] for c in result["calls"]],
                    [PREFIX + n for n in ("parse", "events", "write", "finish")],
                )
                rows, md = self.read()
                self.assertEqual(
                    timeless(rows), timeless(self.original.coherence_events())
                )
                self.assertEqual(len(rows), 7)
                self.assertTrue(
                    md.endswith(
                        "- `skill_application_complete`: Runtime trace complete.\n"
                    )
                )
                self.assertTrue(result["runtime"]["effect_records"])
                self.assertTrue(result["runtime"]["provenance"])
                self.assertTrue(result["replay_artifacts"])
            for argv in (
                ["--workflow", "unsupported"],
                ["--invalid"],
                ["--output-md"],
                ["--help"],
            ):
                result = await run(argv)
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(len(result["calls"]), 1)
                self.assertIsNone(result["outputs"])
            # Filesystem failures stop after write, preserving earlier partial effects.
            for jsonl, md in [
                (self.directory / "partial.jsonl", self.directory / "absent/trace.md"),
                (self.directory, self.directory / "never.md"),
            ]:
                result = await run(
                    ["--output-jsonl", str(jsonl), "--output-md", str(md)]
                )
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(len(result["calls"]), 3)
                self.assertIsNone(result["outputs"])
                self.assertFalse(md.exists())
            self.assertEqual(
                len((self.directory / "partial.jsonl").read_text().splitlines()), 7
            )
            # This source has fixed finite traversals, no convergence/exhaustion loop.
            # The contract budget is distinct; it blocks the third call before writing.
            capped = deepcopy(document)
            capped["policy"]["limits"]["max_operation_calls"] = 2
            target = self.directory / "budget.jsonl"
            result = await run(
                [
                    "--output-jsonl",
                    str(target),
                    "--output-md",
                    str(self.directory / "budget.md"),
                ],
                capped,
            )
            self.assertEqual(result["status"], "failed", result)
            self.assertEqual(
                sum(bool(c.get("transport_call_performed")) for c in result["calls"]), 2
            )
            self.assertFalse(target.exists())
            self.assertIn("budget", str(result).lower())
            # Argument termination did not terminate the server.
            rows = (await remote.call(PREFIX + "events", {}))["rows"]
            self.assertEqual(timeless(rows), timeless(self.original.coherence_events()))
        self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
