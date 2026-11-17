#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402 -- bootstrap the host Lunar environment
"""Frozen oracle, real MCP tools, PRISM parser/checker/compiler and runtime.

This pure planner has no model/provider or theorem compiler dependency. Fixtures
are decoded expansion maps and histories; no production scientific run occurs.
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
import itertools
import json
import tempfile
import unittest
import yaml

from recursive_repair_control_tools import source, SOURCE
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_physics_lean_recursive_repair_control_workflow/workflow.yaml"
AUTHORED = "skills/control/workflow-contract-validator/references/recursive-repair-control.workflow.json"
ORIGINAL = ROOT / "tests/mcp/fixtures/recursive_repair_control_original.py.txt"
PREFIX = "mathformer_recursive_repair_control_"


def oracle():
    loader = SourceFileLoader("recursive_control_original", str(ORIGINAL))
    module = importlib.util.module_from_spec(
        importlib.util.spec_from_loader(loader.name, loader)
    )
    loader.exec_module(module)
    return module


def packet(expansion_map=None, history=None, iteration=1, maximum=6):
    return dict(
        expansion_map={} if expansion_map is None else expansion_map,
        previous_expansion_maps=[] if history is None else history,
        iteration=iteration,
        max_iterations=maximum,
    )


def expansion(**updates):
    return dict(
        status="needs_expansion",
        exhaustive=True,
        iteration_signature="new",
        outstanding_nodes=[{"id": "second"}, {"id": "first"}],
        next_frontier=[
            {
                "node_id": "second",
                "owner_skill": "workbench",
                "action": "repair",
                "blockers": ["b", "a", "b"],
            },
            {"node_id": "first", "action": "check"},
        ],
        **updates,
    )


def updated(**updates):
    return {**expansion(), **updates}


def fixtures():
    return [
        (packet(), "blocked", "non_exhaustive"),
        (packet(expansion()), "recurse", "recurse"),
        # Initial complete bypasses all three checks; even invalid frontier is unused.
        (
            packet(
                updated(
                    status="complete",
                    outstanding_nodes=[],
                    exhaustive=False,
                    next_frontier=[None],
                ),
                [{"iteration_signature": "new"}],
                8,
                -1,
            ),
            "complete",
            "complete",
        ),
        (
            packet(
                updated(status="not_required", outstanding_nodes=[], exhaustive=False),
                [{"iteration_signature": "new"}],
                6,
                6,
            ),
            "complete",
            "complete",
        ),
        (
            packet(updated(exhaustive=False), [{"iteration_signature": "new"}], 6, 6),
            "blocked",
            "non_exhaustive",
        ),
        (
            packet(expansion(), [{"iteration_signature": "new"}], 6, 6),
            "blocked",
            "repeated",
        ),
        (packet(expansion(), [], 6, 6), "blocked", "iteration_cap"),
        (packet(updated(outstanding_nodes=[])), "complete", "complete"),
        # No-outstanding completion is after the history and cap checks.
        (
            packet(updated(outstanding_nodes=[]), [{"iteration_signature": "new"}]),
            "blocked",
            "repeated",
        ),
        (packet(updated(outstanding_nodes=[]), [], 6, 6), "blocked", "iteration_cap"),
        (packet(updated(status="complete")), "recurse", "recurse"),
        (
            packet(updated(status="blocked", outstanding_nodes=[])),
            "blocked",
            "complete",
        ),
        (
            packet(updated(status="blocked", exhaustive=False), [], 10, 6),
            "blocked",
            "non_exhaustive",
        ),
        (
            packet(updated(status="blocked"), [{"iteration_signature": "new"}]),
            "blocked",
            "repeated",
        ),
        (packet(updated(status="blocked"), [], 6, 6), "blocked", "iteration_cap"),
        (packet(updated(status="blocked")), "blocked", "recurse"),
        (packet(expansion(), [], -2, -1), "recurse", "recurse"),
        (packet(expansion(), [], -1, -1), "blocked", "iteration_cap"),
        (
            packet(
                updated(iteration_signature=17),
                [
                    {"iteration_signature": 0},
                    {},
                    {"iteration_signature": False},
                    {"iteration_signature": 17},
                    {"iteration_signature": "17"},
                ],
            ),
            "blocked",
            "repeated",
        ),
        (
            packet(
                updated(iteration_signature=None, exhaustive="false"),
                [{"iteration_signature": "unrelated"}],
            ),
            "recurse",
            "recurse",
        ),
        (
            packet(
                updated(next_frontier=[{"node_id": i} for i in range(137)]),
                [{"iteration_signature": str(i)} for i in range(137)],
            ),
            "recurse",
            "recurse",
        ),
    ]


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


class RecursiveControlTests(unittest.TestCase):
    def test_native_equivalence_and_nonmutation(self):
        native, old = source(), oracle()
        self.assertEqual(
            hashlib.sha256(ORIGINAL.read_bytes()).hexdigest(),
            "b2fb4a4973181f6fd8cc9a920aa0d947c216ee80db9f7384f06e290e30bc68ab",
        )
        for p, status, branch in fixtures():
            before = deepcopy(p)
            actual = native.build_control_plan(**p)
            self.assertEqual(actual, old.build_control_plan(**p))
            self.assertEqual(actual["decision"], status)
            self.assertEqual(p, before)
            state = native.prepare_state(**p)
            selection = native.select_branch(state=state, branch=branch)
            saved = deepcopy(selection)
            self.assertEqual(
                native.finish_plan(state=state, selection=selection), actual
            )
            self.assertEqual(selection, saved)
            self.assertEqual(actual["iteration"], p["iteration"])
            self.assertEqual(actual["max_iterations"], p["max_iterations"])
            self.assertEqual(
                actual["required_rerun_gates"], old.REQUIRED_RECURSION_GATES
            )
            self.assertEqual(actual["recursion_invariants"], old.RECURSION_INVARIANTS)
            self.assertEqual(
                len(actual["next_actions"]),
                (
                    0
                    if status == "complete"
                    else len(p["expansion_map"].get("next_frontier", []))
                ),
            )
        for status, exhaustive, outstanding, repeated, iteration in itertools.product(
            ["complete", "not_required", "blocked", "needs_expansion", None],
            [True, False],
            [[], [{}]],
            [True, False],
            [-1, 0, 6, 7],
        ):
            p = packet(
                updated(
                    status=status, exhaustive=exhaustive, outstanding_nodes=outstanding
                ),
                [{"iteration_signature": "new"}] if repeated else [],
                iteration,
            )
            self.assertEqual(
                native.build_control_plan(**p), old.build_control_plan(**p)
            )

    def test_native_cli_defaults_history_output_and_exit(self):
        native, old = source(), oracle()
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            current = directory / "current.json"
            previous = directory / "previous.json"
            current.write_text(json.dumps(expansion()))
            previous.write_text(json.dumps({"iteration_signature": "new"}))
            argv = [
                "--expansion-map",
                str(current),
                "--previous-expansion-map",
                str(previous),
                "--previous-expansion-map",
                str(previous),
                "--iteration",
                "1",
                "--max-iterations",
                "8",
            ]
            for args in [
                [],
                argv,
                ["--iteration", "-3", "--max-iterations", "-4"],
                ["--self-test", "--expansion-map", str(directory / "absent")],
            ]:
                for flags in [[], ["--output", str(directory / "nested/out.json")]]:
                    observed = []
                    for module in [old, native]:
                        stream = io.StringIO()
                        with redirect_stdout(stream):
                            code = module.main(args + flags)
                        value = (
                            (directory / "nested/out.json").read_text()
                            if flags
                            else stream.getvalue()
                        )
                        self.assertEqual(code, 0)  # Blocked is a normal decision.
                        self.assertTrue(value.endswith("\n"))
                        observed.append((code, stream.getvalue(), value))
                    self.assertEqual(*observed)
            self.assertEqual(native.parse_args([]).iteration, 1)
            self.assertEqual(native.parse_args([]).max_iterations, 6)

    def test_native_failure_and_late_frontier_projection(self):
        malformed = [
            (packet(updated(next_frontier=[None])), AttributeError),
            (packet(updated(outstanding_nodes=None)), TypeError),
            # Frontier failure precedes len(None), as in the frozen source.
            (
                packet(
                    updated(
                        status="blocked", outstanding_nodes=None, next_frontier=[None]
                    )
                ),
                AttributeError,
            ),
            (packet(updated(next_frontier=None)), TypeError),
            (packet(expansion(), [None]), AttributeError),
        ]
        for p, error in malformed:
            for module in [source(), oracle()]:
                with self.assertRaises(error):
                    module.build_control_plan(**deepcopy(p))
        with self.assertRaises(ValueError):
            source().select_branch(state={}, branch="unknown")
        # Preserve native early bypass even for non-integer Python callers.
        # The typed workflow and CLI only admit integers.
        for p in [
            packet(updated(status="complete", outstanding_nodes=[]), [], "unused", {}),
            packet(updated(exhaustive=False), [], "unused", {}),
            packet(expansion(), [{"iteration_signature": "new"}], "unused", {}),
        ]:
            self.assertEqual(
                source().build_control_plan(**p), oracle().build_control_plan(**p)
            )

    def test_lunar_runtime(self):
        asyncio.run(self.runtime())

    async def runtime(self):
        document = yaml.safe_load(
            Path(
                os.environ.get("WORKFLOW_CONTRACT_PATH", ROOT / DESCRIPTOR)
            ).read_text()
        )
        self.assertEqual(document, json.loads((ROOT / AUTHORED).read_text()))
        self.assertEqual(document["lifecycle"], "active")
        self.assertIn(SOURCE, [r["path"] for r in document["provenance"]["sources"]])
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
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        service_python = ROOT / ".venv/bin/python"
        async with manager.open(
            "recursive-control",
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
                assets = snapshot(doc)
                workflow = workflow_documents([DESCRIPTOR], assets)[0]
                return (
                    compile_workflow(
                        "mcp:recursive-control",
                        workflow,
                        tools if inventory is None else inventory,
                    ),
                    assets,
                )

            compiled, assets = compile(document)
            self.assertTrue(compiled["runnable"], compiled["diagnostics"])
            self.assertEqual(compiled["runtime_status"], "ready")
            self.assertTrue(compiled["prism_source"])
            self.assertTrue(compiled["runtime_source"])
            self.assertEqual(set(compiled["bindings"]), set(document["operations"]))
            self.assertFalse(compile(document, [])[0]["runnable"])

            async def allow():
                pass

            async def run(p, doc=None):
                w, a = compile(doc) if doc else (compiled, assets)
                self.assertTrue(w["runnable"], w["diagnostics"])
                return await execute(w, a, p, remote, allow)

            for p, status, branch in fixtures():
                result = await run(p)
                self.assertEqual(result["status"], "accepted", result)
                expected = oracle().build_control_plan(**p)
                self.assertEqual(result["outputs"], {"plan": expected})
                self.assertEqual(
                    [c["tool"] for c in result["calls"]],
                    [
                        PREFIX + name
                        for name in ["prepare_state", "select_branch", "finish_plan"]
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
                # Each decision is one invocation, including recurse and blocked.
                self.assertEqual(len(result["calls"]), 3)
                self.assertEqual(result["outputs"]["plan"]["decision"], status)
                # Directly exercise every tool and selected branch interface.
                prepared = await remote.call(PREFIX + "prepare_state", p)
                self.assertEqual(prepared, {"state": source().prepare_state(**p)})
                selected = await remote.call(
                    PREFIX + "select_branch", {**prepared, "branch": branch}
                )
                self.assertEqual(
                    selected,
                    {"selection": source().select_branch(**prepared, branch=branch)},
                )
                self.assertEqual(
                    await remote.call(PREFIX + "finish_plan", {**prepared, **selected}),
                    {"plan": expected},
                )
            # A malformed frontier reaches native finish and propagates failure;
            # a complete decision leaves the same malformed frontier unused.
            for p in [
                packet(updated(next_frontier=[None])),
                packet(updated(next_frontier=None)),
                packet(updated(outstanding_nodes=None)),
            ]:
                result = await run(p)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(len(result["calls"]), 3)
                self.assertEqual(result["calls"][-1]["status"], "rejected")
                self.assertTrue(result["calls"][-1]["error"])
            with self.assertRaises(MCPConnectionError):
                await remote.call(
                    PREFIX + "select_branch", {"state": {}, "branch": "unknown"}
                )
            # Lunar's call bound is separate from the caller's iteration cap.
            for budget in [1, 2]:
                limited = deepcopy(document)
                limited["policy"]["limits"]["max_operation_calls"] = budget
                result = await run(packet(expansion()), limited)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(len(result["calls"]), budget + 1)
                self.assertIn("budget is exhausted", result["calls"][-1]["error"])
                self.assertFalse(result["calls"][-1].get("execution_performed"))
            timed = deepcopy(document)
            timed["policy"]["limits"]["wall_time_seconds"] = 1
            w, a = compile(timed)

            async def pending_authorization():
                await asyncio.Event().wait()

            with self.assertRaises(TimeoutError):
                await execute(w, a, packet(expansion()), remote, pending_authorization)
        self.assertFalse(manager.active)


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False).result
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
