#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic filesystem fixtures through native steps, MCP and Lunar/PRISM.

No external provider/compiler exists in this critic. PRISM parsing, checking,
compilation and runtime are real; no production workflows or credentials are used.
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
import io
import json
import tempfile
import unittest
import yaml
from integration_critic_tools import source
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute, ExecutionRejected

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_mathformerphysicslib_integration_critic_workflow/workflow.yaml"


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


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.index = self.root / "MathformerPhysicsLib/Lean/Foundations.lean"
        self.native = source()
        namespace = {
            "Mapping": dict,
            "Any": object,
            "Path": Path,
            "FOUNDATIONS_INDEX": self.native.FOUNDATIONS_INDEX,
        }
        exec(
            (
                ROOT / "tests/mcp/fixtures/integration_critic_original.py.txt"
            ).read_text(),
            namespace,
        )
        self.original = namespace["critic_integration"]

    def concept(self, name="fixture", status="owned", owner="Foundations/API.lean"):
        return dict(concept_id=name, owner_status=status, owner_module=owner)

    def graphs(self):
        return [
            {},
            {"concepts": []},
            {"concepts": [self.concept()]},
            {
                "concepts": [
                    self.concept("unowned", "ambiguous"),
                    self.concept("none", owner=None),
                    self.concept("other", owner="Other"),
                    self.concept("first"),
                    self.concept("second"),
                    {},
                    self.concept("last"),
                ]
            },
        ]

    def test_shared_source_equivalence_order_context_and_state(self):
        for inventory in (
            {},
            {"foundations_index_exists": True},
            {"manifest_has_foundations": True},
            {"foundations_index_exists": True, "manifest_has_foundations": True},
        ):
            for graph in self.graphs() + [{"concepts": [self.concept()] * 1001}]:
                for root in (None, self.root):
                    expected = self.original(inventory, graph, root)
                    self.assertEqual(
                        self.native.critic_integration(inventory, graph, root), expected
                    )
                    packet = self.native.initialize_integration_traversal(
                        inventory, graph, root
                    )
                    self.assertEqual(packet["empty"], not graph.get("concepts", []))
                    state = packet["state"]
                    for i in range(len(state["concepts"])):
                        previous = deepcopy(state)
                        packet = self.native.visit_integration_concept(state)
                        self.assertEqual(state, previous)
                        state = packet["state"]
                        self.assertEqual(state["index"], i + 1)
                        self.assertEqual(
                            packet["done"], i + 1 == len(state["concepts"])
                        )
                    self.assertEqual(
                        self.native.finish_integration_report(state), expected
                    )
        # The original entrypoint remains unbounded and accepts iterators.
        for fn in (self.original, self.native.critic_integration):
            self.assertEqual(
                fn({}, {"concepts": iter([self.concept()])}, self.root)[
                    "finding_count"
                ],
                3,
            )
            with self.assertRaises(AttributeError):
                fn({}, {"concepts": [None]}, self.root)
        graph = {"concepts": [self.concept("first"), self.concept("second")]}
        state = self.native.initialize_integration_traversal({}, graph, self.root)[
            "state"
        ]
        state = self.native.visit_integration_concept(state)["state"]
        self.index.parent.mkdir(parents=True)
        self.index.write_text("fixture")
        state = self.native.visit_integration_concept(state)["state"]
        self.assertEqual(
            [f.get("concept_id") for f in state["findings"]], [None, None, "first"]
        )
        for fn in (self.original, self.native.critic_integration):
            self.assertEqual(fn({}, graph, self.root)["finding_count"], 2)
        self.index.unlink()
        self.index.mkdir()
        self.assertEqual(
            self.native.critic_integration({}, graph, self.root),
            self.original({}, graph, self.root),
        )
        self.assertEqual(self.original({}, graph, self.root)["finding_count"], 2)

    def test_cli_fixture_input_output_and_selftest_envelope(self):
        path = (
            ROOT
            / "skills/mathformerphysicslib/mathformerphysicslib-integration-critic/scripts/critic_integration.py"
        )
        spec = importlib.util.spec_from_file_location("integration_cli", path)
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        inv = self.root / "inventory.json"
        graph = self.root / "graph.json"
        out = self.root / "report.json"
        inv.write_text("{}")
        graph.write_text(json.dumps({"concepts": []}))
        stream = io.StringIO()
        with redirect_stdout(stream):
            self.assertEqual(
                cli.main(
                    [
                        "--inventory",
                        str(inv),
                        "--concept-graph",
                        str(graph),
                        "--output",
                        str(out),
                    ]
                ),
                0,
            )
        expected = self.original({}, {"concepts": []})
        self.assertEqual(json.loads(stream.getvalue()), expected)
        self.assertEqual(json.loads(out.read_text()), expected)
        self.assertFalse(expected["ok"])
        stream = io.StringIO()
        with redirect_stdout(stream):
            self.assertEqual(cli.main(["--self-test", "--json"]), 0)
        self.assertEqual(json.loads(stream.getvalue()), expected)
        with self.assertRaises(FileNotFoundError):
            cli.main(["--inventory", str(self.root / "missing")])

    def test_registered_mcp_and_lunar(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(
            document["id"], "hub_mathformerphysicslib_integration_critic_workflow"
        )
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document,
            json.loads(
                (
                    ROOT
                    / "skills/control/workflow-contract-validator/references/integration-critic.workflow.json"
                ).read_text()
            ),
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        # Import production registrations without invoking service configuration.
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        failure_error = None
        async with manager.open(
            "integration",
            StdioConfig(
                command=str(ROOT / ".venv/bin/python"),
                args=["-c", server],
                cwd=str(ROOT),
            ),
            {},
        ) as remote:
            try:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile(doc, inventory=None):
                    received = assets(doc)
                    selected = workflow_documents([DESCRIPTOR], received)[0]
                    w = compile_workflow(
                        "mcp:integration",
                        selected,
                        tools if inventory is None else inventory,
                    )
                    return w, received

                w, a = compile(document)
                self.assertTrue(w["runnable"], w["diagnostics"])
                self.assertTrue(w["runtime_source"])
                self.assertEqual(set(w["bindings"]), set(document["operations"]))
                self.assertFalse(compile(document, [])[0]["runnable"])

                async def allow():
                    pass

                async def run(graph, inventory=None, root=None, doc=None):
                    selected, received = compile(doc) if doc else (w, a)
                    return await execute(
                        selected,
                        received,
                        {
                            "inventory": inventory or {},
                            "concept_graph": graph,
                            "repository_root": root,
                        },
                        remote,
                        allow,
                    )

                for graph in self.graphs():
                    for root in (None, str(self.root)):
                        result = await run(graph, root=root)
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertEqual(
                            result["outputs"],
                            {
                                "report": self.original(
                                    {}, graph, None if root is None else Path(root)
                                )
                            },
                        )
                        count = len(graph.get("concepts", []))
                        self.assertEqual(
                            [c["tool"] for c in result["calls"]],
                            ["mathformer_integration_critic_initialize"]
                            + ["mathformer_integration_critic_visit"] * max(1, count)
                            + ["mathformer_integration_critic_finish"],
                        )
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["replay_artifacts"])
                graph = self.graphs()[-1]
                packet = await remote.call(
                    "mathformer_integration_critic_initialize",
                    {
                        "inventory": {},
                        "concept_graph": graph,
                        "repository_root": str(self.root),
                    },
                )
                self.assertEqual(
                    packet,
                    self.native.initialize_integration_traversal({}, graph, self.root),
                )
                for _ in graph["concepts"]:
                    expected = self.native.visit_integration_concept(packet["state"])
                    packet = await remote.call(
                        "mathformer_integration_critic_visit",
                        {"state": packet["state"]},
                    )
                    self.assertEqual(packet, expected)
                self.assertEqual(
                    await remote.call(
                        "mathformer_integration_critic_finish",
                        {"state": packet["state"]},
                    ),
                    {"report": self.original({}, graph, self.root)},
                )
                self.index.parent.mkdir(parents=True)
                self.index.write_text("fixture")
                result = await run(
                    graph,
                    inventory={
                        "foundations_index_exists": True,
                        "manifest_has_foundations": True,
                    },
                    root=str(self.root),
                )
                self.assertEqual(result["outputs"]["report"]["findings"], [])
                self.assertTrue(result["outputs"]["report"]["ok"])
                result = await run({}, inventory={"foundations_index_exists": True})
                self.assertTrue(result["outputs"]["report"]["ok"])
                self.assertEqual(
                    result["outputs"]["report"]["findings"][0]["severity"], "medium"
                )
                graph = {"concepts": [{}] * 1000}
                result = await run(graph)
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(len(result["calls"]), 1002)
                self.assertEqual(
                    result["outputs"], {"report": self.original({}, graph)}
                )
                graph["concepts"].append({})
                with self.assertRaises(ExecutionRejected):
                    await run(graph)
                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        "mathformer_integration_critic_initialize",
                        {
                            "inventory": {},
                            "concept_graph": graph,
                            "repository_root": None,
                        },
                    )
                graph = {"concepts": [self.concept("first"), self.concept("second")]}
                bounded = deepcopy(document)
                bounded["flow"]["steps"][1]["max_iterations"] = 1
                result = await run(graph, doc=bounded)
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(result["failure_disposition"], "fail")
                self.assertEqual(len(result["calls"]), 2)
                self.assertIsNone(result["outputs"])
                budget = deepcopy(document)
                budget["policy"]["limits"]["max_operation_calls"] = 1
                result = await run(graph, doc=budget)
                self.assertEqual(result["status"], "failed")
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in result["calls"]
                    ),
                    1,
                )
                # The real filesystem fails at inspection, after initialization.
                # Long path components deterministically raise ENAMETOOLONG on supported Python.
                long_root = str(self.root / ("x" * 300))
                for fn in (self.original, self.native.critic_integration):
                    with self.assertRaises(OSError):
                        fn({}, graph, Path(long_root))
                result = await run(graph, root=long_root)
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(len(result["calls"]), 2)
                self.assertEqual(result["calls"][-1]["status"], "rejected")
                self.assertIsNone(result["outputs"])
                with self.assertRaises(ExecutionRejected):
                    await run({"concepts": [None]})
                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        "mathformer_integration_critic_visit",
                        {
                            "state": {
                                "concepts": [None],
                                "index": 0,
                                "findings": [],
                                "foundations_index": str(self.index),
                            }
                        },
                    )
                failure = deepcopy(document)
                failure["operations"]["initialize"]["execution"]["binding"][
                    "target"
                ] = "mathformer_integration_critic_visit"
                self.assertFalse(compile(failure)[0]["runnable"])
            except Exception as error:
                failure_error = error
        self.assertFalse(manager.active)
        if failure_error:
            raise failure_error


if __name__ == "__main__":
    unittest.main(verbosity=2)
