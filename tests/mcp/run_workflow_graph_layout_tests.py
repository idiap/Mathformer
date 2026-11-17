#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic native/MCP/Lunar fixtures. No provider or external compiler exists
in this source; the actual PRISM parser, checker, compiler and runtime are used.
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
import plan_workflow_graph_layout as native
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_docs_workflow_graph_layout_workflow/workflow.yaml"


def graph(edges=0, hooks=26, shared=3):
    # Repeated skill placement and duplicate indexes exercise last-write-wins.
    nodes = [
        {"data": {"node_type": "workflow", "id": "workflow:z"}},
        {"data": {"node_type": "skill", "id": "old", "skill": "s"}},
        {"data": {"node_type": "skill", "id": "skill:s", "skill": "s"}},
    ]
    nodes += [
        {
            "data": {
                "node_type": "workflow_step",
                "id": f"step:{i}",
                "stack": "Z",
                "sequence_index": i,
            }
        }
        for i in [1, 2, 3]
    ]
    nodes += [
        {
            "data": {
                "node_type": "workflow_step",
                "id": "latest",
                "stack": "Z",
                "sequence_index": "1",
            }
        }
    ]
    return {
        "repo": "répo",
        "source_document": "source.md",
        "graph": {
            "elements": {
                "nodes": nodes,
                "edges": [
                    {"data": {"edge_type": "skill_handoff"}} for _ in range(edges)
                ],
            }
        },
        "stacks": {
            "z": {
                "label": "Z",
                "ordered_hooks": [
                    {"index": i, "skill": s}
                    for i, s in [(1, "s"), (2, "missing"), (3, "s")]
                ],
            }
        },
        "summary": {"total_hooks": hooks, "shared_skills": shared},
    }


def snapshot(document):
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


class LayoutTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="graph-layout-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.path = self.root / "artifacts/workflow_graphs/workflow_graphs.json"
        self.path.parent.mkdir(parents=True)
        self.path.write_text(json.dumps(graph()))
        self.output = self.path.with_name("workflow_layout_plan.json")
        spec = importlib.util.spec_from_loader(
            "_graph_oracle",
            SourceFileLoader(
                "_graph_oracle",
                str(ROOT / "tests/mcp/fixtures/workflow_graph_layout_original.py.txt"),
            ),
        )
        self.oracle = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.oracle)
        self.oracle.REPO_ROOT = self.root
        self.oracle.DEFAULT_GRAPH = self.path
        self.oracle.DEFAULT_OUTPUT = self.output

    def cli(self, module, args):
        out, err = io.StringIO(), io.StringIO()
        with (
            redirect_stdout(out),
            redirect_stderr(err),
            patch.object(sys, "argv", ["layout", *args]),
        ):
            try:
                code = (
                    module.main(args, self.root) if module is native else module.main()
                )
            except (SystemExit, ValueError, KeyError, OSError) as e:
                code = (type(e).__name__, str(e))
        return code, out.getvalue(), err.getvalue()

    def test_original_entrypoint_and_branches(self):
        for args in [
            [],
            ["--json"],
            ["--graph", str(self.path), "--output", "nested/plan.json", "--json"],
            ["--help"],
            ["--unknown"],
        ]:
            a = self.cli(native, args)
            b = self.cli(self.oracle, args)
            self.assertEqual(a, b)
        for n, risk in [
            (0, "low"),
            (8, "low"),
            (9, "medium"),
            (18, "medium"),
            (19, "high"),
        ]:
            for hooks, shared, count in [
                (25, 4, 3),
                (26, 4, 4),
                (25, 3, 4),
                (26, 3, 5),
            ]:
                m = graph(n, hooks, shared)
                p = native.build_plan(m)
                self.assertEqual(p, self.oracle.build_plan(m))
                self.assertEqual(
                    p["pressure"]["view_pressure"]["drilldown"]["clutter_risk"], risk
                )
                self.assertEqual(len(p["recommendations"]), count)
                pos = p["views"]["drilldown"]["stack_layouts"]["z"]["positions"]
                self.assertEqual(
                    pos,
                    {
                        "workflow:z": {"x": -320, "y": 0},
                        "latest": {"x": 0, "y": 0},
                        "skill:s": {"x": 620, "y": 190},
                        "step:2": {"x": 310, "y": 0},
                        "step:3": {"x": 620, "y": 0},
                    },
                )
        empty = graph()
        empty["stacks"] = {}
        empty["graph"]["elements"] = {"nodes": [], "edges": []}
        self.assertEqual(native.build_plan(empty), self.oracle.build_plan(empty))
        for mutate in [
            lambda m: m["graph"]["elements"]["nodes"].clear(),
            lambda m: m["stacks"]["z"]["ordered_hooks"][0].update(index="bad"),
        ]:
            m = graph()
            mutate(m)
            for module in [native, self.oracle]:
                with self.assertRaises((KeyError, ValueError)):
                    module.build_plan(m)

    def test_registered_mcp_and_lunar(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_docs_workflow_graph_layout_workflow")
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        failure = None
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;sys.argv=["layout"];mcp.run(transport="stdio")'
        async with manager.open(
            "layout",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {},
        ) as remote:
            try:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile(doc, inventory=tools):
                    assets = snapshot(doc)
                    workflow = compile_workflow(
                        "mcp:layout",
                        workflow_documents([DESCRIPTOR], assets)[0],
                        inventory,
                    )
                    return workflow, assets

                c, a = compile(document)
                self.assertTrue(c["runnable"], c["diagnostics"])
                self.assertTrue(c["runtime_source"])
                self.assertEqual(set(c["bindings"]), set(document["operations"]))
                self.assertFalse(compile(document, [])[0]["runnable"])

                async def allow():
                    pass

                async def run(args, doc=document):
                    c, a = compile(doc)
                    self.assertTrue(c["runnable"], c["diagnostics"])
                    return await execute(
                        c,
                        a,
                        {"argv": args, "context": {"repository_root": str(self.root)}},
                        remote,
                        allow,
                    )

                for n in [0, 8, 9, 18, 19]:
                    self.path.write_text(json.dumps(graph(n)))
                    expected = self.cli(self.oracle, ["--json"])
                    original_bytes = self.output.read_bytes()
                    self.output.unlink()
                    result = await run(["--json"])
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(self.output.read_bytes(), original_bytes)
                    self.assertEqual(
                        result["outputs"]["result"],
                        {
                            "ok": True,
                            "output": "artifacts/workflow_graphs/workflow_layout_plan.json",
                            "views": ["drilldown"],
                            "exit_code": 0,
                            "stdout": expected[1],
                        },
                    )
                    self.assertEqual(
                        [r["tool"] for r in result["calls"]],
                        [
                            "mathformer_graph_layout_" + s
                            for s in ["resolve", "read", "build", "emit"]
                        ],
                    )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["runtime"]["provenance"])
                    self.assertTrue(result["replay_artifacts"])
                result = await run([])
                self.assertEqual(
                    result["outputs"]["result"]["stdout"],
                    "ok: artifacts/workflow_graphs/workflow_layout_plan.json\n",
                )
                result = await run(["--help"])
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(len(result["calls"]), 2)
                self.assertEqual(
                    result["outputs"]["result"]["stdout"],
                    self.cli(self.oracle, ["--help"])[1],
                )
                for args, count in [
                    (["--unknown"], 1),
                    (["--graph", "absent.json"], 2),
                ]:
                    result = await run(args)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(len(result["calls"]), count)
                self.path.write_text("{")
                result = await run([])
                self.assertEqual(result["status"], "failed")
                self.assertEqual(len(result["calls"]), 2)
                m = graph()
                m["graph"]["elements"]["nodes"] = []
                self.path.write_text(json.dumps(m))
                self.output.unlink()
                result = await run([])
                self.assertEqual(result["status"], "failed")
                self.assertEqual(len(result["calls"]), 3)
                self.assertFalse(self.output.exists())
                self.path.write_text(json.dumps(graph()))
                occupied = self.root / "occupied"
                occupied.write_text("retain")
                result = await run(["--output", "occupied/plan.json"])
                self.assertEqual(result["status"], "failed")
                self.assertEqual(len(result["calls"]), 4)
                self.assertEqual(occupied.read_text(), "retain")
                # Native write happens before relative_to rejects an outside output.
                outside = self.root.parent / (self.root.name + "-outside.json")
                try:
                    result = await run(["--output", str(outside)])
                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(len(result["calls"]), 4)
                    self.assertEqual(
                        json.loads(outside.read_text()), native.build_plan(graph())
                    )
                finally:
                    outside.unlink(missing_ok=True)
                bounded = deepcopy(document)
                bounded["policy"]["limits"]["max_operation_calls"] = 3
                result = await run([], bounded)
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(
                    sum(
                        bool(r.get("transport_call_performed")) for r in result["calls"]
                    ),
                    3,
                )
                self.assertFalse(self.output.exists())
                timed = deepcopy(document)
                timed["policy"]["limits"]["wall_time_seconds"] = 1
                c, a = compile(timed)

                async def pending():
                    await asyncio.Event().wait()

                with self.assertRaises(TimeoutError):
                    await execute(
                        c,
                        a,
                        {"argv": [], "context": {"repository_root": str(self.root)}},
                        remote,
                        pending,
                    )
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure is not None:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
