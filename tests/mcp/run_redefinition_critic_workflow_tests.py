#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic native fixtures through registered MCP and real Lunar/PRISM.

This critic has no provider or external compiler boundary. No model, solver,
credentials or production workflow run is needed; PRISM is never substituted.
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
import hashlib
import json
import unittest
import yaml
from api_critic_tools import source
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute, ExecutionRejected

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_mathformerphysicslib_redefinition_critic_workflow/workflow.yaml"


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


def occurrence(path, name=None, foundation=False, imports=False):
    return dict(
        path=path,
        is_foundation=foundation,
        imports_foundation=imports,
        ownership_declarations=[] if name is None else [{"name": name}],
    )


def fixtures():
    graph = {
        "concepts": [
            {
                "concept_id": "spread",
                "occurrences": [occurrence(str(i), "x") for i in range(10)],
            },
            {
                "concept_id": "owned",
                "occurrences": [
                    occurrence("z", "x", True),
                    occurrence("a", "y", True),
                    occurrence("overlap", "x", imports=True),
                    occurrence("bypass", "q"),
                    occurrence("legal", "q", imports=True),
                    occurrence("healthy", imports=True),
                    42,
                ],
            },
            {
                "concept_id": "block",
                "occurrences": [occurrence(str(i)) for i in range(12)],
            },
            {"concept_id": "last", "occurrences": [occurrence("one", "x")]},
        ]
    }
    grounding = {
        "concepts": [
            {"concept_id": "owned", "grounding_level": "local_blocker"},
            {"concept_id": "owned", "grounding_level": "direct_mathlib"},
            {"concept_id": "spread", "grounding_level": "local_blocker"},
            {"concept_id": "block", "grounding_level": "local_blocker"},
        ]
    }
    return [
        ({}, {}),
        ({"concepts": []}, {}),
        ({"concepts": [graph["concepts"][2]]}, grounding),
        (graph, grounding),
    ]


class CriticTests(unittest.TestCase):
    def setUp(self):
        namespace = {}
        exec(
            "from typing import Mapping, Any\n"
            + (
                ROOT / "tests/mcp/fixtures/redefinition_critic_original.py.txt"
            ).read_text(),
            namespace,
        )
        self.original = namespace["critic_redefinitions"]
        self.native = source()

    def test_native_equivalence_and_state(self):
        for graph, grounding in fixtures() + [({"concepts": [{}] * 1025}, {})]:
            self.assertEqual(
                self.native.critic_redefinitions(graph, grounding),
                self.original(graph, grounding),
            )
            packet = self.native.initialize_redefinition_traversal(graph, grounding)
            self.assertEqual(packet["has_concepts"], bool(graph.get("concepts")))
            state = packet["state"]
            for i in range(len(state["concepts"])):
                previous = deepcopy(state)
                packet = self.native.visit_redefinition_concept(state)
                self.assertEqual(state, previous)
                state = packet["state"]
                self.assertEqual(state["cursor"], i + 1)
                self.assertEqual(packet["done"], i + 1 == len(state["concepts"]))
            self.assertEqual(
                self.native.finish_redefinition_report(state),
                self.original(graph, grounding),
            )
        graph, grounding = fixtures()[-1]
        report = self.original(graph, grounding)
        self.assertFalse(report["ok"])
        self.assertEqual(report["finding_count"], 5)
        self.assertEqual(
            [f["kind"] for f in report["findings"]],
            [
                "concept_spread_without_foundation_owner",
                "unresolved_grounding_blocker",
                "confirmed_competing_concept_owner",
                "confirmed_competing_concept_owner",
                "unresolved_grounding_blocker",
            ],
        )
        self.assertEqual(
            report["reuse_metrics"],
            dict(
                healthy_downstream_uses=1,
                downstream_local_declarations=14,
                confirmed_duplicate_owners=2,
            ),
        )
        self.assertEqual(len(report["findings"][0]["evidence"]), 8)
        self.assertEqual(len(report["findings"][-1]["evidence"]), 8)
        self.assertEqual(report["findings"][2]["owner_module"], "a")
        self.assertTrue(self.original(*fixtures()[2])["ok"])
        # Native entrypoint retains arbitrary iterables and original exceptions.
        for call in (self.original, self.native.critic_redefinitions):
            self.assertEqual(call({"concepts": iter([{}])}, {})["finding_count"], 0)
            with self.assertRaises(KeyError):
                call({}, {"concepts": [{}]})
            with self.assertRaises(AttributeError):
                call({"concepts": [None]}, {})
        graph = {
            "concepts": [
                {
                    "occurrences": [occurrence("f", "x", True)]
                    + [occurrence(str(i), "x") for i in range(12)]
                }
            ]
        }
        self.assertEqual(
            self.native.critic_redefinitions(graph, {})["finding_count"], 12
        )

    def test_original_cli_report_and_exit_status(self):
        import importlib.util
        from contextlib import redirect_stdout
        import io
        import tempfile

        path = (
            ROOT
            / "skills/mathformerphysicslib/mathformerphysicslib-redefinition-critic/scripts/critic_redefinitions.py"
        )
        spec = importlib.util.spec_from_file_location("redefinition_cli_fixture", path)
        wrapper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(wrapper)
        graph, grounding = fixtures()[-1]
        with tempfile.TemporaryDirectory() as directory:
            graph_path = Path(directory) / "graph.json"
            graph_path.write_text(json.dumps(graph))
            grounding_path = Path(directory) / "grounding.json"
            grounding_path.write_text(json.dumps(grounding))
            output = io.StringIO()
            with redirect_stdout(output):
                code = wrapper.main(
                    [
                        "--concept-graph",
                        str(graph_path),
                        "--grounding-report",
                        str(grounding_path),
                        "--json",
                    ]
                )
            self.assertEqual(code, 0)
            self.assertEqual(
                json.loads(output.getvalue()), self.original(graph, grounding)
            )
            self.assertFalse(json.loads(output.getvalue())["ok"])

    def test_registered_mcp_and_lunar(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(
            document["id"], "hub_mathformerphysicslib_redefinition_critic_workflow"
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
        failure = None
        async with manager.open(
            "redefinition",
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
            try:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile(doc, inventory=None):
                    received = assets(doc)
                    selected = workflow_documents([DESCRIPTOR], received)[0]
                    w = compile_workflow(
                        "mcp:redefinition",
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

                async def run(graph, grounding=None, doc=None):
                    selected, received = compile(doc) if doc else (w, a)
                    return await execute(
                        selected,
                        received,
                        {"concept_graph": graph, "grounding": grounding or {}},
                        remote,
                        allow,
                    )

                for graph, grounding in fixtures():
                    result = await run(graph, grounding)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(
                        result["outputs"], {"report": self.original(graph, grounding)}
                    )
                    self.assertEqual(
                        [c["tool"] for c in result["calls"]],
                        ["mathformer_redefinition_critic_initialize"]
                        + ["mathformer_redefinition_critic_visit_concept"]
                        * max(1, len(graph.get("concepts", [])))
                        + ["mathformer_redefinition_critic_finish_report"],
                    )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["replay_artifacts"])
                graph, grounding = fixtures()[-1]
                packet = await remote.call(
                    "mathformer_redefinition_critic_initialize",
                    dict(concept_graph=graph, grounding=grounding),
                )
                self.assertEqual(
                    packet,
                    self.native.initialize_redefinition_traversal(graph, grounding),
                )
                for _ in graph["concepts"]:
                    expected = self.native.visit_redefinition_concept(packet["state"])
                    packet = await remote.call(
                        "mathformer_redefinition_critic_visit_concept",
                        {"state": packet["state"]},
                    )
                    self.assertEqual(packet, expected)
                self.assertEqual(
                    await remote.call(
                        "mathformer_redefinition_critic_finish_report",
                        {"state": packet["state"]},
                    ),
                    {"report": self.original(graph, grounding)},
                )
                result = await run({"concepts": [{}] * 1024})
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(len(result["calls"]), 1026)
                self.assertEqual(
                    result["outputs"],
                    {"report": self.original({"concepts": [{}] * 1024}, {})},
                )
                with self.assertRaises(ExecutionRejected):
                    await run({"concepts": [{}] * 1025})
                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        "mathformer_redefinition_critic_initialize",
                        {"concept_graph": {"concepts": [{}] * 1025}, "grounding": {}},
                    )
                bounded = deepcopy(document)
                bounded["flow"]["steps"][1]["max_iterations"] = 1
                result = await run({"concepts": [{}, {}]}, doc=bounded)
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(result["failure_disposition"], "fail")
                self.assertEqual(len(result["calls"]), 2)
                self.assertIsNone(result["outputs"])
                budget = deepcopy(document)
                budget["policy"]["limits"]["max_operation_calls"] = 1
                result = await run({"concepts": [{}]}, doc=budget)
                self.assertEqual(result["status"], "failed")
                self.assertIn("budget", str(result).lower())
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in result["calls"]
                    ),
                    1,
                )
                result = await run(
                    {
                        "concepts": [
                            {
                                "occurrences": [
                                    {
                                        "ownership_declarations": True,
                                        "is_foundation": True,
                                    }
                                ]
                            },
                            {},
                        ]
                    }
                )
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(len(result["calls"]), 2)
                self.assertEqual(result["calls"][-1]["status"], "rejected")
                self.assertIsNone(result["outputs"])
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
