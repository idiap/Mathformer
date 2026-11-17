#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic filesystem fixtures through native source, MCP and real PRISM.

There is no model/provider or external compiler boundary in this validator.
No source step or PRISM boundary is replaced. All writes use temporary contexts.
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
from contextlib import redirect_stdout
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
from runtime_trace_validation_tools import (
    source,
    register_runtime_trace_validation_tools,
)
from mcp.server.fastmcp import FastMCP
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute, ExecutionRejected

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_meta_skills_runtime_trace_validate_workflow/workflow.yaml"
SCHEMA = {"required": ["step", "evidence", "artifacts"], "allowed_steps": ["check"]}
GOOD = (
    json.dumps({"step": "check", "evidence": ["fixture"], "artifacts": ["present.txt"]})
    + "\n"
)


def original():
    path = ROOT / "tests/mcp/fixtures/runtime_trace_validation_original.py.txt"
    spec = importlib.util.spec_from_loader(
        "trace_validation_oracle",
        SourceFileLoader("trace_validation_oracle", str(path)),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


class TraceValidationTests(unittest.TestCase):
    def setUp(self):
        base = ROOT / "artifacts/workflow_hub"
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(
            prefix="trace-validation-fixture-", dir=base
        )
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def context(self, name, traces):
        root = self.directory / name
        (root / "meta_skills/schemas").mkdir(parents=True)
        (root / "meta_skills/schemas/runtime_skill_application.schema.json").write_text(
            json.dumps(SCHEMA)
        )
        trace_root = root / "artifacts/meta_skills/runtime"
        trace_root.mkdir(parents=True)
        for name, text in traces.items():
            (trace_root / name).write_text(text)
        # These must not be discovered by the nonrecursive *.jsonl glob.
        (trace_root / "ignored.txt").write_text("not json")
        (trace_root / "nested").mkdir()
        (trace_root / "nested/ignored.jsonl").write_text("not json")
        (root / "present.txt").write_text("fixture")
        return root

    def output(self, root):
        return root / "artifacts/meta_skills/runtime_trace_validation.json"

    def invoke(self, module, root, cli=None):
        with patch.multiple(
            module,
            REPO_ROOT=root,
            SCHEMA_PATH=root
            / "meta_skills/schemas/runtime_skill_application.schema.json",
            TRACE_ROOT=root / "artifacts/meta_skills/runtime",
            OUTPUT_PATH=self.output(root),
        ):
            if cli is not None:
                stream = io.StringIO()
                with (
                    patch.object(sys, "argv", ["validate", *cli]),
                    redirect_stdout(stream),
                ):
                    code = module.main()
                return code, stream.getvalue()
            return module.run()

    def test_native_oracle_order_checks_blank_lines_and_cli(self):
        bad = (
            "\n{\n"
            + json.dumps({"step": "wrong", "evidence": [], "artifacts": ["missing"]})
            + "\n"
            + json.dumps({"artifacts": "wrong"})
            + "\n"
            + GOOD
        )
        root = self.context(
            "oracle", {"z.jsonl": GOOD, "a.jsonl": bad, "b.jsonl": "\n  \n"}
        )
        expected = self.invoke(original(), root)
        before = self.output(root).read_bytes()
        self.assertEqual(self.invoke(source(), root), expected)
        self.assertEqual(self.output(root).read_bytes(), before)
        self.assertEqual(
            [r["path"] for r in expected["results"]],
            [
                "artifacts/meta_skills/runtime/" + p
                for p in ["a.jsonl", "b.jsonl", "z.jsonl"]
            ],
        )
        self.assertEqual([r["event_count"] for r in expected["results"]], [4, 0, 1])
        self.assertEqual(
            [f["code"] for f in expected["findings"]],
            [
                "invalid_jsonl",
                "invalid_step",
                "missing_evidence",
                "missing_artifact",
                "missing_field",
                "missing_field",
                "invalid_step",
                "missing_evidence",
                "artifacts_not_list",
                "empty_trace",
            ],
        )
        self.assertEqual(expected["results"][0]["findings"][0]["line"], 2)
        self.assertTrue(expected["results"][-1]["ok"])
        for args in ([], ["--json"]):
            self.assertEqual(
                self.invoke(source(), root, args), self.invoke(original(), root, args)
            )
            self.assertEqual(self.invoke(source(), root, args)[0], 1)
        good = self.context("good", {"one.jsonl": GOOD})
        self.assertEqual(self.invoke(source(), good, []), (0, "PASS runtime traces\n"))
        empty = self.context("empty", {})
        self.assertEqual(self.invoke(source(), empty), self.invoke(original(), empty))
        self.assertFalse(self.invoke(source(), empty)["ok"])

    def test_native_uncaught_failures_and_unbounded_discovery(self):
        for value, error in [("1\n", TypeError), ("[]\n", AttributeError)]:
            root = self.context(
                str(error.__name__),
                {"a.jsonl": GOOD, "b.jsonl": value, "z.jsonl": GOOD},
            )
            for module in (original(), source()):
                with self.assertRaises(error):
                    self.invoke(module, root)
                self.assertFalse(self.output(root).exists())
        root = self.context("schema-error", {})
        (root / "meta_skills/schemas/runtime_skill_application.schema.json").write_text(
            "{"
        )
        for module in (original(), source()):
            with self.assertRaises(json.JSONDecodeError):
                self.invoke(module, root)
        root = self.context(
            "native-unbounded", {f"{i:04}.jsonl": GOOD for i in range(1001)}
        )
        expected = self.invoke(original(), root)
        self.assertEqual(self.invoke(source(), root), expected)
        self.assertEqual(expected["trace_count"], 1001)
        self.assertTrue(expected["ok"])

    def test_write_policy(self):
        from mcp.shared.memory import create_connected_server_and_client_session

        async def scenario():
            root = self.context("readonly", {})

            def denied(path):
                raise ValueError("service is read-only")

            server = FastMCP("readonly-fixture")
            register_runtime_trace_validation_tools(server, denied)
            async with create_connected_server_and_client_session(
                server._mcp_server
            ) as session:
                result = await session.call_tool(
                    "mathformer_trace_validation_initialize",
                    {"repository_root": str(root), "discovered_trace_count": 0},
                )
                result = await session.call_tool(
                    "mathformer_trace_validation_write_report",
                    {"state": result.structuredContent["state"]},
                )
                self.assertTrue(result.isError)
                self.assertIn("read-only", str(result))
                self.assertFalse(self.output(root).exists())

        asyncio.run(scenario())

    def test_real_registered_tools_and_lunar(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(
            document["id"], "hub_meta_skills_runtime_trace_validate_workflow"
        )
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 2002},
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        failure = None
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp.server.fastmcp import FastMCP;from runtime_trace_validation_tools import register_runtime_trace_validation_tools;mcp=FastMCP("trace-validation");register_runtime_trace_validation_tools(mcp);mcp.run(transport="stdio")'
        async with manager.open(
            "trace-validation",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
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
                    return (
                        compile_workflow(
                            "mcp:trace-validation",
                            selected,
                            tools if inventory is None else inventory,
                        ),
                        assets,
                    )

                workflow, assets = compile(document)
                self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                self.assertTrue(workflow["runtime_source"])
                self.assertEqual(set(workflow["bindings"]), set(document["operations"]))
                self.assertFalse(compile(document, [])[0]["runnable"])

                async def authorize():
                    pass

                async def run(root, count, doc=None):
                    compiled, received = compile(doc) if doc else (workflow, assets)
                    return await execute(
                        compiled,
                        received,
                        {"repository_root": str(root), "discovered_trace_count": count},
                        remote,
                        authorize,
                    )

                for label, traces in [
                    ("good", {"z.jsonl": GOOD, "a.jsonl": GOOD}),
                    (
                        "findings",
                        {"a.jsonl": "{\n{}\n" + GOOD, "b.jsonl": "\n", "z.jsonl": GOOD},
                    ),
                    ("empty", {}),
                ]:
                    root = self.context("runtime-" + label, traces)
                    expected = self.invoke(original(), root)
                    expected_bytes = self.output(root).read_bytes()
                    self.output(root).unlink()
                    result = await run(root, len(traces))
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(result["outputs"], {"report": expected})
                    self.assertEqual(self.output(root).read_bytes(), expected_bytes)
                    prefix = "mathformer_trace_validation_"
                    self.assertEqual(
                        [c["tool"] for c in result["calls"]],
                        [prefix + "initialize"]
                        + (
                            [prefix + "validate_file", prefix + "accumulate"]
                            * len(traces)
                            if traces
                            else [prefix + "empty_state"]
                        )
                        + [prefix + "write_report"],
                    )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["replay_artifacts"])
                root = self.context("mismatch", {"a.jsonl": GOOD})
                for count in (0, 2):
                    result = await run(root, count)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(len(result["calls"]), 1)
                    self.assertFalse(self.output(root).exists())
                with self.assertRaises(ExecutionRejected):
                    await run(root, 1001)
                # Adapter accepts the exact domain boundary, rejects larger actual discovery.
                root = self.context(
                    "bound-discovery", {f"{i:04}.jsonl": GOOD for i in range(1000)}
                )
                initialized = await remote.call(
                    "mathformer_trace_validation_initialize",
                    {"repository_root": str(root), "discovered_trace_count": 1000},
                )
                self.assertEqual(len(initialized["state"]["traces"]), 1000)
                self.assertEqual(initialized["state"]["cursor"], 0)
                (root / "artifacts/meta_skills/runtime/extra.jsonl").write_text(GOOD)
                result = await run(root, 1000)
                self.assertEqual(result["status"], "failed")
                for label in ("type", "schema", "read", "write"):
                    root = self.context(
                        "runtime-" + label,
                        {
                            "a.jsonl": GOOD,
                            "b.jsonl": "1\n" if label == "type" else GOOD,
                        },
                    )
                    if label == "schema":
                        (
                            root
                            / "meta_skills/schemas/runtime_skill_application.schema.json"
                        ).write_text("{")
                    if label == "read":
                        (root / "artifacts/meta_skills/runtime/b.jsonl").write_bytes(
                            b"\xff"
                        )
                    if label == "write":
                        self.output(root).mkdir()
                    result = await run(root, 2)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(
                        len(result["calls"]),
                        {"type": 4, "schema": 1, "read": 4, "write": 6}[label],
                    )
                    self.assertEqual(result["calls"][-1]["status"], "rejected")
                    if label != "write":
                        self.assertFalse(self.output(root).exists())
                bounded = deepcopy(document)
                bounded["flow"]["steps"][1]["max_iterations"] = 1
                root = self.context("last-iteration", {"a.jsonl": GOOD})
                self.assertEqual((await run(root, 1, bounded))["status"], "accepted")
                root = self.context("exhaustion", {"a.jsonl": GOOD, "b.jsonl": GOOD})
                result = await run(root, 2, bounded)
                self.assertEqual(result["status"], "failed", result)
                self.assertIn("exhaust", str(result).lower())
                self.assertEqual(len(result["calls"]), 3)
                self.assertFalse(self.output(root).exists())
                budget = deepcopy(document)
                budget["policy"]["limits"]["max_operation_calls"] = 1
                result = await run(root, 2, budget)
                self.assertEqual(result["status"], "failed")
                self.assertIn("budget", str(result).lower())
                self.assertFalse(self.output(root).exists())
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
