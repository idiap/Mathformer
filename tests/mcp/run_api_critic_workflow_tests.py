#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Filesystem fixtures through actual registered MCP tools and Lunar/PRISM.

The critic has no provider or external compiler boundary. These fixtures use
real files; the PRISM parser, checker, compiler, and runtime are never replaced.
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
import tempfile
import unittest
import yaml
from api_critic_tools import source
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute, ExecutionRejected

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_mathformerphysicslib_api_operability_critic_workflow/workflow.yaml"


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


class CriticTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "Foundations").mkdir()
        (self.root / "Foundations/api.lean").write_text("Alpha BETA")
        self.native = source()
        self.previous = self.native.REPO_ROOT
        self.native.REPO_ROOT = self.root
        self.addCleanup(setattr, self.native, "REPO_ROOT", self.previous)
        namespace = {"Mapping": dict, "Any": object, "REPO_ROOT": self.root}
        exec(
            (ROOT / "tests/mcp/fixtures/api_critic_original.py.txt").read_text(),
            namespace,
        )
        self.original = namespace["critic_api"]

    def concept(self, terms, owner="Foundations/api.lean", name="fixture"):
        return dict(concept_id=name, owner_module=owner, api_terms=terms)

    def graphs(self):
        return [
            {},
            {"concepts": []},
            {"concepts": [self.concept(["alpha", "missing"])]},
            {
                "concepts": [
                    self.concept(["absent"], None),
                    self.concept(["absent"], "Other"),
                    self.concept([]),
                    self.concept(["missing"], "Foundations/missing"),
                    self.concept(["ALPHA", "missing"]),
                    self.concept(["beta"]),
                    self.concept(["alpha", "alpha", "missing"]),
                    self.concept(["alpha", "beta"]),
                ]
            },
        ]

    def test_native_equivalence_state_and_exceptions(self):
        for graph in self.graphs() + [{"concepts": [self.concept(["missing"])] * 1025}]:
            self.assertEqual(self.native.critic_api(graph), self.original(graph))
            packet = self.native.initialize_api_traversal(graph)
            state = packet["state"]
            for i in range(len(state["concepts"])):
                previous = deepcopy(state)
                packet = self.native.visit_api_concept(state, self.root)
                self.assertEqual(state, previous)
                state = packet["state"]
                self.assertEqual(state["index"], i + 1)
                self.assertEqual(packet["done"], i + 1 == len(state["concepts"]))
            self.assertEqual(self.native.finish_api_report(state), self.original(graph))
        # The native entrypoint also retains support for non-indexable iterables.
        for call in (self.native.critic_api, self.original):
            self.assertEqual(
                call({"concepts": iter([self.concept(["missing"])])})["finding_count"],
                1,
            )
        report = self.native.critic_api(self.graphs()[-1])
        self.assertEqual([f["severity"] for f in report["findings"]], ["high", "low"])
        self.assertEqual(report["findings"][1]["present_terms"], ["ALPHA"])
        self.assertFalse(report["ok"])
        for graph, error in [
            ({"concepts": [self.concept([None])]}, AttributeError),
            ({"concepts": [self.concept(["x"], "Foundations")]}, IsADirectoryError),
        ]:
            for call in (self.original, self.native.critic_api):
                with self.assertRaises(error):
                    call(graph)

    def test_registered_mcp_and_lunar(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(
            document["id"], "hub_mathformerphysicslib_api_operability_critic_workflow"
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
            "api",
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
                        "mcp:api", selected, tools if inventory is None else inventory
                    )
                    return w, received

                w, a = compile(document)
                self.assertTrue(w["runnable"], w["diagnostics"])
                self.assertTrue(w["runtime_source"])
                self.assertEqual(set(w["bindings"]), set(document["operations"]))
                self.assertFalse(compile(document, [])[0]["runnable"])

                async def allow():
                    pass

                async def run(graph, doc=None):
                    selected, received = compile(doc) if doc else (w, a)
                    return await execute(
                        selected,
                        received,
                        {"concept_graph": graph, "repository_root": str(self.root)},
                        remote,
                        allow,
                    )

                for graph in self.graphs():
                    result = await run(graph)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(
                        result["outputs"], {"report": self.original(graph)}
                    )
                    count = len(graph.get("concepts", []))
                    self.assertEqual(
                        [c["tool"] for c in result["calls"]],
                        ["mathformer_api_critic_initialize"]
                        + ["mathformer_api_critic_visit"] * max(1, count)
                        + ["mathformer_api_critic_finish"],
                    )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["replay_artifacts"])
                graph = self.graphs()[-1]
                packet = await remote.call(
                    "mathformer_api_critic_initialize", {"graph": graph}
                )
                self.assertEqual(packet, self.native.initialize_api_traversal(graph))
                for i in range(len(graph["concepts"])):
                    expected = self.native.visit_api_concept(packet["state"], self.root)
                    packet = await remote.call(
                        "mathformer_api_critic_visit",
                        {"state": packet["state"], "repository_root": str(self.root)},
                    )
                    self.assertEqual(packet, expected)
                self.assertEqual(
                    await remote.call(
                        "mathformer_api_critic_finish", {"state": packet["state"]}
                    ),
                    {"report": self.original(graph)},
                )
                graph = {"concepts": [{}] * 1024}
                result = await run(graph)
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(len(result["calls"]), 1026)
                self.assertEqual(result["outputs"], {"report": self.original(graph)})
                # Oversize admission, rather than truncating the native traversal.
                graph["concepts"].append(self.concept(["missing"]))
                with self.assertRaises(ExecutionRejected):
                    await run(graph)
                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        "mathformer_api_critic_initialize", {"graph": graph}
                    )
                graph = {
                    "concepts": [self.concept(["missing"]), self.concept(["missing"])]
                }
                bounded = deepcopy(document)
                bounded["flow"]["steps"][1]["max_iterations"] = 1
                result = await run(graph, bounded)
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(result["failure_disposition"], "fail")
                self.assertEqual(len(result["calls"]), 2)
                self.assertIsNone(result["outputs"])
                budget = deepcopy(document)
                budget["policy"]["limits"]["max_operation_calls"] = 1
                result = await run(graph, budget)
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
                            self.concept(["x"], "Foundations"),
                            self.concept(["missing"]),
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
