#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Fixture audit data through production MCP registrations and real Lunar/PRISM.

This audit has no external provider or compiler boundary. Nothing substitutes
for PRISM parsing, checking, compilation, execution, or native audit steps.
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
import ast
import asyncio
from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace
import unittest
import yaml
from router_coverage_tools import source
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_control_workflow_router_coverage_workflow/workflow.yaml"
DOMAIN = {"route_cap": 10000, "actions_per_route_cap": 10000}


def route(name, actions):
    return dict(
        route_id=name,
        title="Title " + name,
        action_ids=actions,
        skill_routes=["skill"],
        examples=["example"],
    )


def oracle(context):
    # Frozen original algorithm, evaluated on fixture collections, is an oracle
    # only. No production step, tool, or compiler is replaced.
    tree = ast.parse(
        (ROOT / "tests/mcp/fixtures/router_coverage_original.py.txt").read_text()
    )
    functions = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name in ("resolve_action_family", "build_coverage_report")
    ]
    space = {
        "Any": object,
        "mathformer": SimpleNamespace(
            WorkflowAction=object,
            build_registry=lambda: {
                k: SimpleNamespace(**v) for k, v in context["registry"].items()
            },
            build_intent_routes=lambda: [
                SimpleNamespace(**r) for r in context["routes"]
            ],
        ),
    }
    exec(
        compile(
            ast.Module(body=functions, type_ignores=[]), "<frozen audit oracle>", "exec"
        ),
        space,
    )
    return space["build_coverage_report"]()


def assets(document):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(r["path"], (ROOT / r["path"]).read_text())
        for r in document["provenance"]["sources"]
    ]


class RouterTests(unittest.TestCase):
    def test_domain_caps_and_native_state(self):
        native = source()
        context = {
            "registry": {"x": {"family": "f"}},
            "routes": [route("many", ["x"] * 10000)],
        }
        state = native.initialize_coverage(DOMAIN, context)["state"]
        native.begin_coverage_route(state)
        for index in range(10000):
            result = native.visit_coverage_action(state)
            self.assertEqual(result["actions_done"], index == 9999)
        self.assertEqual(state["action_index"], 10000)
        self.assertEqual(state["covered"], ["f"])
        self.assertTrue(native.finish_coverage_route(state)["routes_done"])
        self.assertEqual(native.finalize_coverage(state), oracle(context))
        context["routes"][0]["action_ids"].append("x")
        with self.assertRaisesRegex(ValueError, "exceeds"):
            native.initialize_coverage(DOMAIN, context)
        context = {"registry": {}, "routes": [route(str(i), []) for i in range(10000)]}
        state = native.initialize_coverage(DOMAIN, context)["state"]
        for index in range(10000):
            self.assertFalse(native.begin_coverage_route(state)["has_actions"])
            self.assertEqual(
                native.finish_coverage_route(state)["routes_done"], index == 9999
            )
        self.assertEqual(
            len(native.finalize_coverage(state)["routes_without_actions"]), 10000
        )
        context["routes"].append(route("overflow", []))
        with self.assertRaisesRegex(ValueError, "exceeds"):
            native.initialize_coverage(DOMAIN, context)
        with self.assertRaises(IndexError):
            native.visit_coverage_action(state)

    def test_registered_tools_compile_execute_and_failures(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(
            document["id"], "hub_control_workflow_router_coverage_workflow"
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        self.assertIn(
            source().REPO_ROOT
            / "skills/control/mathformer-workflow-router/scripts/route_mathformer_workflow.py",
            [ROOT / r["path"] for r in document["provenance"]["sources"]],
        )
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        failure = None
        async with manager.open(
            "router-test",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {},
        ) as remote:
            try:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def qualify(doc, inventory=tools):
                    snapshot = assets(doc)
                    workflow = compile_workflow(
                        "mcp:router-test",
                        workflow_documents([DESCRIPTOR], snapshot)[0],
                        inventory,
                    )
                    self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                    return workflow, snapshot

                workflow, snapshot = qualify(document)

                async def allow():
                    pass

                async def run(context, doc=document):
                    compiled, data = qualify(doc)
                    return await execute(
                        compiled,
                        data,
                        {"domain": DOMAIN, "context": context},
                        remote,
                        allow,
                    )

                fixtures = [
                    {"registry": {}, "routes": []},
                    {"registry": {"a": {"family": "missing"}}, "routes": []},
                    {
                        "registry": {
                            "test:family:fallback": {"family": "registered"},
                            "a": {"family": "a"},
                            "m": {"family": "missing"},
                        },
                        "routes": [
                            route(
                                "r",
                                [
                                    "unknown",
                                    "a",
                                    "a",
                                    "test:family:fallback",
                                    "test:family:extra",
                                ],
                            ),
                            route("empty", []),
                            route("last", ["a"]),
                        ],
                    },
                    {
                        "registry": {"a": {"family": "a"}},
                        "routes": [route("ok", ["a", "a"])],
                    },
                ]
                for context in fixtures:
                    self.assertEqual(
                        source().build_coverage_report(deepcopy(context)),
                        oracle(context),
                    )
                    result = await run(context)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(result["outputs"], {"report": oracle(context)})
                    expected = ["initialize"] + (
                        [] if context["routes"] else ["empty_state"]
                    )
                    for r in context["routes"]:
                        expected += (
                            ["begin_route"]
                            + ["visit_action"] * len(r["action_ids"])
                            + ["finish_route"]
                        )
                    expected += ["finalize"]
                    self.assertEqual(
                        [c["tool"] for c in result["calls"]],
                        ["mathformer_router_coverage_" + n for n in expected],
                    )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["runtime"]["provenance"])
                    self.assertTrue(result["replay_artifacts"])
                # Exact last-item success and exhausted bounds use real tools and
                # compiler, with smaller test-only loop bounds to keep tests quick.
                limited = deepcopy(document)
                limited["flow"]["steps"][1]["max_iterations"] = 3
                one = {
                    "registry": {"a": {"family": "a"}},
                    "routes": [route("one", ["a"])],
                }
                result = await run(one, limited)
                self.assertEqual(result["status"], "accepted", result)
                self.assertTrue(result["outputs"]["report"]["ok"])
                for context, expected in [
                    (
                        {
                            "registry": one["registry"],
                            "routes": [route("one", ["a", "a"])],
                        },
                        ["initialize", "begin_route", "visit_action", "visit_action"],
                    ),
                    (
                        {
                            "registry": one["registry"],
                            "routes": [route("one", ["a"]), route("two", ["a"])],
                        },
                        ["initialize", "begin_route", "visit_action", "finish_route"],
                    ),
                ]:
                    result = await run(context, limited)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(result["failure_disposition"], "fail")
                    self.assertEqual(
                        [c["tool"] for c in result["calls"]],
                        ["mathformer_router_coverage_" + n for n in expected],
                    )
                budget = deepcopy(document)
                budget["policy"]["limits"]["max_operation_calls"] = 1
                result = await run(one, budget)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(
                    [c["status"] for c in result["calls"]], ["accepted", "rejected"]
                )
                self.assertIn("budget", result["calls"][-1]["error"])
                # A real native IndexError is an MCP tool error, not a report finding.
                bad = deepcopy(document)
                bad["flow"]["steps"][0]["operation"] = "visit_action"
                bad["flow"]["steps"][0]["arguments"] = {
                    "state": {
                        "literal": source().initialize_coverage(
                            DOMAIN, {"registry": {}, "routes": []}
                        )["state"]
                    }
                }
                # Keep the normal signature of load exports; a dedicated minimal
                # workflow calls visit_action and tests source failure propagation.
                bad["flow"] = {
                    "kind": "call",
                    "operation": "visit_action",
                    "arguments": bad["flow"]["steps"][0]["arguments"],
                }
                bad["outputs"] = {
                    "state": {"type": "State", "value": {"ref": "flow.outputs.state"}}
                }
                result = await run(one, bad)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(len(result["calls"]), 1)
                self.assertEqual(result["calls"][0]["status"], "rejected")
                missing = [
                    t
                    for t in tools
                    if t["name"] != "mathformer_router_coverage_visit_action"
                ]
                selected = workflow_documents([DESCRIPTOR], assets(document))[0]
                unavailable = compile_workflow("mcp:router-test", selected, missing)
                self.assertFalse(unavailable["runnable"])
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure is not None:
            raise failure


if __name__ == "__main__":
    unittest.main()
