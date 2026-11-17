#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Fixture repositories, real registered MCP tools and Lunar/PRISM runtime.

There is no provider/model or external compiler boundary in this workflow.
Only deterministic filesystem inputs are supplied; no production run is made.
Compiler fixtures vary bounds/inventory while retaining real compilation.
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
from copy import deepcopy
from contextlib import redirect_stdout
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import tempfile
import unittest
from unittest.mock import patch
import yaml
from workflow_evolution_tools import source
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_meta_skills_workflow_evolution_workflow/workflow.yaml"
PREFIX = "mathformer_workflow_evolution_"


def original():
    loader = SourceFileLoader(
        "evolution_oracle",
        str(ROOT / "tests/mcp/fixtures/workflow_evolution_original.py.txt"),
    )
    module = importlib.util.module_from_spec(
        importlib.util.spec_from_loader(loader.name, loader)
    )
    loader.exec_module(module)
    return module


def valid():
    return dict(
        schema_version="fixture",
        workflow_id="fixture",
        source_report="evidence",
        states=[
            dict(state_id="s", status="pass", owner="fixture", evidence=["evidence"])
        ],
        transitions=[
            dict(**{"from": "s", "to": "s"}, condition="fixture", evidence=["evidence"])
        ],
        gates=[dict(gate_id="g", status="pass", evidence=["evidence"])],
        reflective_questions=[dict(question="fixture", evidence_needed="fixture")],
        next_delta={"decision": "stop"},
    )


def bad():
    data = valid()
    data["source_report"] = "absent"
    data["states"][0]["evidence"] = []
    data["transitions"][0]["to"] = "unknown"
    data["transitions"][0]["evidence"] = ["missing"]
    data["gates"] = [1, {}]
    data["reflective_questions"] = []
    data["next_delta"] = {}
    return data


def snapshot(document):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(row["path"], (ROOT / row["path"]).read_text())
        for row in document["provenance"]["sources"]
    ]


class EvolutionTests(unittest.TestCase):
    def setUp(self):
        base = ROOT / "artifacts/workflow_hub"
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="evolution-fixture-", dir=base)
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def context(self, name, rows):
        root = self.directory / name
        (root / "meta_skills/schemas").mkdir(parents=True)
        (root / "meta_skills/registry/tasks").mkdir(parents=True)
        (root / "meta_skills/schemas/workflow_evolution.schema.json").write_bytes(
            (ROOT / "meta_skills/schemas/workflow_evolution.schema.json").read_bytes()
        )
        (root / "evidence").write_text("fixture")
        for task, data in rows.items():
            path = (
                root / "meta_skills/registry/tasks" / task / "workflow_evolution.json"
            )
            path.parent.mkdir()
            path.write_text(json.dumps(data))
        return root

    def output(self, root):
        return root / "artifacts/meta_skills/workflow_evolution_validation.json"

    def invoke(self, module, root, cli=False):
        with patch.multiple(
            module,
            REPO_ROOT=root,
            SCHEMA_PATH=root / "meta_skills/schemas/workflow_evolution.schema.json",
            GRAPH_ROOT=root / "meta_skills/registry/tasks",
            OUTPUT_PATH=self.output(root),
        ):
            if not cli:
                return module.run()
            stream = io.StringIO()
            with (
                patch.object(sys, "argv", ["evolution", "--json"]),
                redirect_stdout(stream),
            ):
                code = module.main()
            return code, stream.getvalue()

    def test_native_equivalence_and_failure(self):
        for label, rows in [
            ("empty", {}),
            ("valid", {"z": valid(), "a": valid()}),
            ("errors", {"z": valid(), "a": {}, "b": bad()}),
        ]:
            root = self.context(label, rows)
            expected = self.invoke(original(), root)
            serialized = self.output(root).read_bytes()
            self.assertEqual(self.invoke(source(), root), expected)
            self.assertEqual(self.output(root).read_bytes(), serialized)
            self.assertEqual(
                self.invoke(source(), root, True), self.invoke(original(), root, True)
            )
            self.assertEqual(expected["ok"], label == "valid")
            if label == "errors":
                self.assertEqual(
                    [r["path"].split("/")[-2] for r in expected["results"]],
                    ["a", "b", "z"],
                )
                self.assertTrue(expected["results"][-1]["ok"])
                self.assertEqual(
                    {f["code"] for f in expected["results"][0]["findings"]},
                    {"missing_field"},
                )
                self.assertTrue(
                    {
                        "missing_source_report",
                        "missing_evidence",
                        "missing_evidence_path",
                        "transition_unknown_endpoint",
                        "next_delta_missing_decision",
                        "empty_collection",
                        "non_object_row",
                        "missing_nested_field",
                    }
                    <= {f["code"] for f in expected["findings"]}
                )
        root = self.context("uncapped", {str(i): valid() for i in range(1025)})
        self.assertEqual(self.invoke(source(), root), self.invoke(original(), root))
        self.assertEqual(self.invoke(source(), root)["graph_count"], 1025)
        for label, text, error in [
            ("json", "{", json.JSONDecodeError),
            ("shape", "1", TypeError),
            ("row", json.dumps({**valid(), "states": [1]}), AttributeError),
            ("transition", json.dumps({**valid(), "transitions": [1]}), AttributeError),
        ]:
            root = self.context(label, {"a": valid(), "b": valid(), "z": valid()})
            (root / "meta_skills/registry/tasks/b/workflow_evolution.json").write_text(
                text
            )
            for module in (original(), source()):
                with self.assertRaises(error):
                    self.invoke(module, root)
                self.assertFalse(self.output(root).exists())

    def test_native_schema_failure_timing(self):
        for index, schema in enumerate([{}, 1, {"required": [], "nested_required": 1}]):
            for nonempty in (False, True):
                root = self.context(
                    "schema-" + str(index) + "-" + str(nonempty),
                    {"a": valid()} if nonempty else {},
                )
                (
                    root / "meta_skills/schemas/workflow_evolution.schema.json"
                ).write_text(json.dumps(schema))
                if nonempty:
                    outcomes = []
                    for module in (original(), source()):
                        try:
                            self.invoke(module, root)
                        except Exception as error:
                            outcomes.append(type(error))
                    self.assertEqual(len(outcomes), 2)
                    self.assertEqual(*outcomes)
                    self.assertFalse(self.output(root).exists())
                else:
                    self.assertEqual(
                        self.invoke(source(), root), self.invoke(original(), root)
                    )

    def test_mcp_registration_and_write_policy(self):
        # Production server mounts this exact registrar; avoid importing unrelated backends.
        import ast

        tree = ast.parse((ROOT / "scripts/mcp_server.py").read_text())
        self.assertTrue(
            any(
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "register_workflow_evolution_tools"
                for node in ast.walk(tree)
            )
        )
        from workflow_evolution_tools import register_workflow_evolution_tools
        from mcp.server.fastmcp import FastMCP

        async def scenario():
            root = self.context("readonly", {})

            def deny(path):
                raise ValueError("read-only fixture policy")

            mcp = FastMCP("policy")
            register_workflow_evolution_tools(mcp, deny)
            async with mcp._mcp_server.lifespan(mcp._mcp_server):
                from mcp.shared.memory import create_connected_server_and_client_session

                async with create_connected_server_and_client_session(
                    mcp._mcp_server
                ) as session:
                    initialized = await session.call_tool(
                        PREFIX + "initialize",
                        {"scope": {"graph_cap": 1024}, "repository_root": str(root)},
                    )
                    result = await session.call_tool(
                        PREFIX + "finish",
                        {"state": initialized.structuredContent["state"]},
                    )
                    self.assertTrue(result.isError)
                    self.assertIn("read-only", str(result))
                    self.assertFalse(self.output(root).exists())

        asyncio.run(scenario())

    def test_real_mcp_lunar(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_meta_skills_workflow_evolution_workflow")
        self.assertEqual(document["lifecycle"], "active")
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        # The same production tool registrar is mounted without unrelated backend imports.
        server = 'import sys;sys.path.insert(0,"scripts");from mcp.server.fastmcp import FastMCP;from workflow_evolution_tools import register_workflow_evolution_tools;mcp=FastMCP("evolution");register_workflow_evolution_tools(mcp);mcp.run(transport="stdio")'
        failure = None
        async with manager.open(
            "evolution",
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
                    return (
                        compile_workflow(
                            "mcp:evolution",
                            workflow_documents([DESCRIPTOR], assets)[0],
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

                async def run(root, doc=None):
                    w, a = compile(doc) if doc else (workflow, assets)
                    self.assertTrue(w["runnable"], w["diagnostics"])
                    return await execute(
                        w,
                        a,
                        {"repository_root": str(root), "scope": {"graph_cap": 1024}},
                        remote,
                        authorize,
                    )

                for label, rows in [
                    ("empty", {}),
                    ("valid", {"z": valid(), "a": valid()}),
                    ("errors", {"a": {}, "b": bad(), "z": valid()}),
                ]:
                    root = self.context("runtime-" + label, rows)
                    expected = self.invoke(original(), root)
                    serialized = self.output(root).read_bytes()
                    self.output(root).unlink()
                    result = await run(root)
                    self.assertEqual(result["status"], "accepted", result)
                    self.maxDiff = None
                    self.assertEqual(result["outputs"], {"report": expected})
                    self.assertEqual(self.output(root).read_bytes(), serialized)
                    names = (
                        ["initialize"]
                        + (
                            ["validate_current", "accumulate"] * len(rows)
                            if rows
                            else ["empty_state"]
                        )
                        + ["finish"]
                    )
                    self.assertEqual(
                        [c["tool"] for c in result["calls"]],
                        [PREFIX + n for n in names],
                    )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["replay_artifacts"])
                root = self.context("state", {"z": valid(), "a": {}})
                initialized = await remote.call(
                    PREFIX + "initialize",
                    {"scope": {"graph_cap": 1024}, "repository_root": str(root)},
                )
                state = initialized["state"]
                self.assertTrue(initialized["has_graphs"])
                self.assertEqual(state["cursor"], 0)
                for index in range(2):
                    fixed = deepcopy(state)
                    findings = (
                        await remote.call(PREFIX + "validate_current", {"state": state})
                    )["findings"]
                    self.assertEqual(state, fixed)
                    advanced = await remote.call(
                        PREFIX + "accumulate", {"state": state, "findings": findings}
                    )
                    state = advanced["state"]
                    self.assertEqual(state["cursor"], index + 1)
                    self.assertEqual(advanced["done"], index == 1)
                    self.assertEqual(
                        state["all_findings"], fixed["all_findings"] + findings
                    )
                    for key in [
                        "paths",
                        "schema",
                        "nested_order",
                        "repository_root",
                        "output_path",
                    ]:
                        self.assertEqual(state[key], fixed[key])
                self.assertFalse(self.output(root).exists())
                for count in (1024, 1025):
                    root = self.context(
                        "bound-" + str(count), {str(i): valid() for i in range(count)}
                    )
                    if count == 1024:
                        admitted = await remote.call(
                            PREFIX + "initialize",
                            {
                                "scope": {"graph_cap": 1024},
                                "repository_root": str(root),
                            },
                        )
                        self.assertEqual(len(admitted["state"]["paths"]), count)
                    else:
                        result = await run(root)
                        self.assertEqual(result["status"], "failed")
                        self.assertEqual(len(result["calls"]), 1)
                    self.assertFalse(self.output(root).exists())
                for label, text in [
                    ("parse", "{"),
                    ("shape", "1"),
                    ("state", json.dumps({**valid(), "states": [1]})),
                    ("transition", json.dumps({**valid(), "transitions": [1]})),
                ]:
                    root = self.context(
                        "runtime-" + label, {"a": valid(), "b": valid(), "z": valid()}
                    )
                    (
                        root / "meta_skills/registry/tasks/b/workflow_evolution.json"
                    ).write_text(text)
                    result = await run(root)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(len(result["calls"]), 4)
                    self.assertEqual(
                        result["calls"][-1]["tool"], PREFIX + "validate_current"
                    )
                    self.assertFalse(self.output(root).exists())
                root = self.context("missing-schema", {})
                (root / "meta_skills/schemas/workflow_evolution.schema.json").unlink()
                result = await run(root)
                self.assertEqual(result["status"], "failed")
                self.assertEqual(len(result["calls"]), 1)
                self.assertFalse(self.output(root).exists())
                root = self.context("write-fail", {"a": valid()})
                self.output(root).mkdir(parents=True)
                result = await run(root)
                self.assertEqual(result["status"], "failed")
                self.assertEqual(len(result["calls"]), 4)
                bounded = deepcopy(document)
                bounded["flow"]["steps"][1]["max_iterations"] = 1
                root = self.context("at-bound", {"a": valid()})
                self.assertEqual((await run(root, bounded))["status"], "accepted")
                root = self.context("exhausted", {"a": valid(), "b": valid()})
                result = await run(root, bounded)
                self.assertEqual(result["status"], "failed", result)
                self.assertIn("exhaust", str(result).lower())
                self.assertFalse(self.output(root).exists())
                budget = deepcopy(document)
                budget["policy"]["limits"]["max_operation_calls"] = 1
                result = await run(root, budget)
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
