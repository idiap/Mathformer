#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402
"""Execute real registered 0004 stages through Lunar and PRISM on JSON fixtures.

This controller has no model/provider or theorem compiler call of its own.
Decoded expansion-map fixtures exercise its file-input boundary without running
the transitive scientific pipeline. PRISM's parser/checker/compiler/runtime and
MCP transport are real. WORKFLOW_CONTRACT_PATH is required, never inferred.
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

import run_sympy_recursive_repair_control_workflow_tests as shared
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute
from sympy_recursive_repair_control_tools import source, SOURCE

DESCRIPTOR = (
    "skills/control/workflow-contract-validator/references/normalized-workflows/hub/"
    "hub_physics_sympy_recursive_repair_control_0004_workflow/workflow.yaml"
)
AUTHORED = ROOT / (
    "skills/control/workflow-contract-validator/references/"
    "sympy-recursive-repair-control-0004.workflow.json"
)
PREFIX = "mathformer_sympy_recursive_repair_0004_"


class SympyRecursiveControl0004Tests(shared.SympyRecursiveControlTests):
    # Inherit independent frozen-source branch matrix, CLI output/log equivalence,
    # and cartographer result-evidence tests. Only the bound workflow differs.
    async def runtime(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document, json.loads(AUTHORED.read_text()))
        self.assertEqual(
            document["id"], "hub_physics_sympy_recursive_repair_control_0004_workflow"
        )
        self.assertEqual(document["lifecycle"], "active")
        self.assertIn(SOURCE, [s["path"] for s in document["provenance"]["sources"]])
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        from normalize_workflows_tools import source as normalizer

        self.assertEqual(
            next(d for d in normalizer().inventory() if d["id"] == document["id"]),
            document,
        )

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

        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        service_python = ROOT / ".venv/bin/python"
        async with manager.open(
            "sympy-control-0004",
            StdioConfig(
                command=(
                    str(service_python) if service_python.exists() else sys.executable
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
                snapshot = assets(doc)
                workflow = workflow_documents([DESCRIPTOR], snapshot)[0]
                return (
                    compile_workflow(
                        "mcp:sympy-control-0004",
                        workflow,
                        tools if inventory is None else inventory,
                    ),
                    snapshot,
                )

            compiled, snapshot = compile(document)
            self.assertTrue(compiled["runnable"], compiled["diagnostics"])
            self.assertEqual(compiled["runtime_status"], "ready")
            self.assertTrue(compiled["prism_source"])
            self.assertTrue(compiled["runtime_source"])
            self.assertEqual(set(compiled["bindings"]), set(document["operations"]))
            self.assertFalse(compile(document, [])[0]["runnable"])
            for operation in document["operations"]:
                target = document["operations"][operation]["execution"]["binding"][
                    "target"
                ]
                self.assertFalse(
                    compile(document, [t for t in tools if t["name"] != target])[0][
                        "runnable"
                    ]
                )

            async def allow():
                pass

            async def run(inputs, doc=None):
                workflow, evidence = compile(doc) if doc else (compiled, snapshot)
                self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                return await execute(workflow, evidence, inputs, remote, allow)

            with tempfile.TemporaryDirectory() as tmp:
                directory = Path(tmp)
                current = directory / "current.json"

                def inputs(p, output=None, reasoning_log=None):
                    current.write_text(json.dumps(p["expansion_map"]))
                    paths = []
                    for i, exp in enumerate(p["previous_expansion_maps"]):
                        path = directory / f"previous-{i}.json"
                        path.write_text(json.dumps(exp))
                        paths.append(path.name)
                    return dict(
                        request=dict(
                            expansion_map=current.name,
                            previous_expansion_maps=paths,
                            iteration=p["iteration"],
                            max_iterations=p["max_iterations"],
                        ),
                        context=dict(working_directory=str(directory)),
                        output_path=output,
                        reasoning_log=reasoning_log,
                    )

                for p, status, branch in shared.fixtures():
                    supplied = inputs(p)
                    before = deepcopy(supplied)
                    result = await run(supplied)
                    self.assertEqual(result["status"], "accepted", result)
                    expected = shared.oracle().build_control_plan(**p)
                    self.assertEqual(result["outputs"]["plan"], expected)
                    self.assertEqual(result["outputs"]["plan"]["status"], status)
                    self.assertEqual(result["outputs"]["exit_code"], 0)
                    self.assertEqual(
                        result["outputs"]["stdout_text"],
                        json.dumps(expected, ensure_ascii=False, indent=2) + "\n",
                    )
                    state = result["outputs"]["state"]
                    self.assertEqual(state["request"]["case"], "formalphysics_0004")
                    for key, value in p.items():
                        self.assertEqual(state[key], value)
                    self.assertEqual(supplied, before)
                    self.assertEqual(
                        [c["tool"] for c in result["calls"]],
                        [
                            PREFIX + n
                            for n in [
                                "load_state",
                                "compute_guards",
                                "finish_plan",
                                "emit_plan",
                            ]
                        ],
                    )
                    self.assertTrue(
                        all(
                            c["execution_performed"] and c["status"] == "accepted"
                            for c in result["calls"]
                        )
                    )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["runtime"]["provenance"])
                    self.assertTrue(result["replay_artifacts"])
                    loaded = await remote.call(
                        PREFIX + "load_state",
                        {k: supplied[k] for k in ["request", "context"]},
                    )
                    guarded = await remote.call(PREFIX + "compute_guards", loaded)
                    self.assertEqual(source().choose_branch(guarded["guards"]), branch)
                    finished = await remote.call(
                        PREFIX + "finish_plan", {**loaded, "branch": branch}
                    )
                    self.assertEqual(finished["plan"], expected)
                    # Finishing has no logging or file emission side effect.
                    self.assertEqual(json.loads(finished["plan_json"]), expected)

                supplied = inputs(
                    shared.packet(shared.expansion()), "nested/out.json", "events.jsonl"
                )
                del supplied["request"]["iteration"]
                del supplied["request"]["max_iterations"]
                result = await run(supplied)
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(result["outputs"]["state"]["iteration"], 1)
                self.assertEqual(result["outputs"]["state"]["max_iterations"], 6)
                self.assertEqual(result["outputs"]["stdout_text"], "")
                self.assertEqual(
                    (directory / "nested/out.json").read_text(),
                    json.dumps(
                        shared.oracle().build_control_plan(
                            **shared.packet(shared.expansion())
                        ),
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                )
                event = shared.stable_event(directory / "events.jsonl")
                self.assertEqual(
                    event["step"], "physics_sympy_recursive_repair_control_complete"
                )
                self.assertEqual(event["payload"]["decision"], "recurse")

                for p, count in [
                    (shared.packet(shared.expansion(next_frontier=[None])), 3),
                    (shared.packet(shared.expansion(next_frontier=None)), 3),
                    (shared.packet(shared.expansion(outstanding_nodes=None)), 3),
                    (shared.packet(shared.expansion(), [None]), 1),
                ]:
                    result = await run(inputs(p))
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(len(result["calls"]), count)
                    self.assertEqual(result["calls"][-1]["status"], "rejected")

                supplied = inputs(shared.packet(shared.expansion()))
                for request in [
                    dict(case=None),
                    dict(expansion_map="absent.json"),
                    dict(
                        expansion_map=current.name,
                        previous_expansion_maps=["absent.json"],
                    ),
                ]:
                    result = await run({**supplied, "request": request})
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(len(result["calls"]), 1)
                current.write_text("{")
                result = await run(supplied)
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(len(result["calls"]), 1)

                supplied = inputs(
                    shared.packet(shared.expansion()),
                    str(directory),
                    "before-failure.jsonl",
                )
                result = await run(supplied)
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(len(result["calls"]), 4)
                self.assertEqual(
                    len((directory / "before-failure.jsonl").read_text().splitlines()),
                    1,
                )
                self.assertIsNone(result["outputs"])

                loaded = await remote.call(
                    PREFIX + "load_state",
                    {k: supplied[k] for k in ["request", "context"]},
                )
                for extra in [
                    dict(branch="unknown"),
                    dict(branch="recurse", state_json="{}"),
                ]:
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(PREFIX + "finish_plan", {**loaded, **extra})
                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        PREFIX + "emit_plan",
                        dict(
                            plan={},
                            plan_json='{"different":true}',
                            output_path=None,
                            reasoning_log=None,
                            context=supplied["context"],
                        ),
                    )

                for budget in [1, 2, 3]:
                    limited = deepcopy(document)
                    limited["policy"]["limits"]["max_operation_calls"] = budget
                    result = await run(
                        inputs(shared.packet(shared.expansion())), limited
                    )
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(len(result["calls"]), budget + 1)
                    self.assertIn("budget is exhausted", result["calls"][-1]["error"])
                    self.assertFalse(result["calls"][-1].get("execution_performed"))
                timed = deepcopy(document)
                timed["policy"]["limits"]["wall_time_seconds"] = 1
                workflow, evidence = compile(timed)

                async def pending():
                    await asyncio.Event().wait()

                with self.assertRaises(TimeoutError):
                    await execute(
                        workflow,
                        evidence,
                        inputs(shared.packet(shared.expansion())),
                        remote,
                        pending,
                    )
        self.assertFalse(manager.active)


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False).result
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
