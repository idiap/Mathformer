#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402 -- bootstrap the host Lunar/PRISM environment
"""Frozen-source equivalence and registered MCP -> Lunar -> real PRISM execution.

Deterministic decoded JSON maps, histories, and subprocess-result evidence are
fixtures for this controller. It has no direct provider or theorem compiler;
none is simulated. Tests never invoke the transitive scientific case pipeline.
The actual PRISM parser, checker, compiler, and runtime are used unchanged.
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
from importlib.machinery import SourceFileLoader
import importlib.util
import io
import itertools
import json
import subprocess
import tempfile
import unittest
import yaml

from sympy_recursive_repair_control_tools import source, SOURCE
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_physics_sympy_recursive_repair_control_0000_workflow/workflow.yaml"
AUTHORED = "skills/control/workflow-contract-validator/references/sympy-recursive-repair-control.workflow.json"
ORIGINAL = ROOT / "tests/mcp/fixtures/sympy_recursive_repair_control_original.py.txt"
PREFIX = "mathformer_sympy_recursive_repair_"


def oracle():
    loader = SourceFileLoader("sympy_recursive_control_original", str(ORIGINAL))
    module = importlib.util.module_from_spec(
        importlib.util.spec_from_loader(loader.name, loader)
    )
    loader.exec_module(module)
    return module


def expansion(**updates):
    return {
        **dict(
            case_id="fixture",
            status="needs_expansion",
            exhaustive=True,
            iteration_signature="new",
            outstanding_nodes=[{"id": "second"}, {"id": "first"}],
            next_frontier=[
                {"node_id": "second", "action": "repair", "blockers": ["b", "a", "b"]},
                {"node_id": "first", "action": "check"},
            ],
        ),
        **updates,
    }


def packet(exp=None, history=None, iteration=1, maximum=6):
    return dict(
        expansion_map={} if exp is None else exp,
        previous_expansion_maps=[] if history is None else history,
        iteration=iteration,
        max_iterations=maximum,
    )


def fixtures():
    return [
        (packet(), "blocked", "non_exhaustive"),
        (packet(expansion()), "recurse", "recurse"),
        (
            packet(
                expansion(
                    case_id={"z": 1, "a": 2},
                    next_frontier=[
                        {"node_id": "nested", "blockers": [{"z": 1, "a": 2}]}
                    ],
                )
            ),
            "recurse",
            "recurse",
        ),
        (
            packet(
                expansion(
                    status="complete",
                    outstanding_nodes=[],
                    exhaustive=False,
                    next_frontier=[None],
                ),
                [{"iteration_signature": "new"}],
                9,
                -1,
            ),
            "complete",
            "complete",
        ),
        (
            packet(
                expansion(
                    status="not_required", outstanding_nodes=[], exhaustive=False
                ),
                [{"iteration_signature": "new"}],
                6,
                6,
            ),
            "complete",
            "complete",
        ),
        (
            packet(expansion(exhaustive=False), [{"iteration_signature": "new"}], 6, 6),
            "blocked",
            "non_exhaustive",
        ),
        (
            packet(expansion(), [{"iteration_signature": "new"}], 6, 6),
            "blocked",
            "repeated",
        ),
        (packet(expansion(), [], 6, 6), "blocked", "at_cap"),
        (packet(expansion(outstanding_nodes=[])), "complete", "complete"),
        (
            packet(expansion(outstanding_nodes=[]), [{"iteration_signature": "new"}]),
            "blocked",
            "repeated",
        ),
        (packet(expansion(outstanding_nodes=[]), [], 6, 6), "blocked", "at_cap"),
        (packet(expansion(status="complete")), "recurse", "recurse"),
        (
            packet(expansion(status="blocked", outstanding_nodes=[])),
            "blocked",
            "complete",
        ),
        (
            packet(expansion(status="blocked", exhaustive=False)),
            "blocked",
            "non_exhaustive",
        ),
        (
            packet(expansion(status="blocked"), [{"iteration_signature": "new"}]),
            "blocked",
            "repeated",
        ),
        (packet(expansion(status="blocked"), [], 6, 6), "blocked", "at_cap"),
        (packet(expansion(status="blocked")), "blocked", "recurse"),
        (packet(expansion(), [], -2, -1), "recurse", "recurse"),
        (packet(expansion(), [], -1, -1), "blocked", "at_cap"),
        (
            packet(
                expansion(iteration_signature=17),
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
            packet(expansion(iteration_signature=None, exhaustive="false")),
            "recurse",
            "recurse",
        ),
        (
            packet(
                expansion(next_frontier=[{"node_id": i} for i in range(137)]),
                [{"iteration_signature": str(i)} for i in range(137)],
            ),
            "recurse",
            "recurse",
        ),
    ]


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


def stable_event(path):
    event = json.loads(path.read_text().splitlines()[-1])
    dynamic = {
        "timestamp_utc",
        "timestamp_unix_ms",
        "monotonic_ns",
        "elapsed_ms_since_log_start",
        "elapsed_ms_since_prev_event",
        "skill_call_id",
        "run_id",
    }

    def scrub(value):
        if isinstance(value, dict):
            return {k: scrub(v) for k, v in value.items() if k not in dynamic}
        if isinstance(value, list):
            return [scrub(v) for v in value]
        return value

    return scrub(event)


class SympyRecursiveControlTests(unittest.TestCase):
    def test_source_equivalence_and_branch_matrix(self):
        native, old = source(), oracle()
        self.assertEqual(
            hashlib.sha256(ORIGINAL.read_bytes()).hexdigest(),
            "541c47ab9510e296669a8fcdf8124d225b055d21f580216fa4bc2f5b6b795ef0",
        )
        for p, status, branch in fixtures():
            before = deepcopy(p)
            expected = old.build_control_plan(**p)
            self.assertEqual(native.build_control_plan(**p), expected)
            self.assertEqual(expected["status"], status)
            self.assertEqual(native.choose_branch(native.compute_guards(p)), branch)
            self.assertEqual(native.finish_plan(p, branch), expected)
            self.assertEqual(p, before)
            self.assertEqual(expected["iteration"], p["iteration"])
            self.assertEqual(
                expected["required_rerun_gates"], old.REQUIRED_RECURSION_GATES
            )
            self.assertEqual(expected["recursion_invariants"], old.RECURSION_INVARIANTS)
        for status, exhaustive, outstanding, repeated, iteration in itertools.product(
            ["complete", "not_required", "blocked", "needs_expansion", None],
            [True, False],
            [[], [{}]],
            [True, False],
            [-1, 0, 6, 7],
        ):
            p = packet(
                expansion(
                    status=status, exhaustive=exhaustive, outstanding_nodes=outstanding
                ),
                [{"iteration_signature": "new"}] if repeated else [],
                iteration,
            )
            self.assertEqual(
                native.build_control_plan(**p), old.build_control_plan(**p)
            )
        # The native early branches do not compare a cap they have bypassed.
        for exp, hist in [
            (expansion(status="complete", outstanding_nodes=[]), []),
            (expansion(exhaustive=False), []),
            (expansion(), [{"iteration_signature": "new"}]),
        ]:
            p = packet(exp, hist, "unused", {})
            self.assertEqual(
                native.build_control_plan(**p), old.build_control_plan(**p)
            )

    def test_cli_emission_and_exception_order(self):
        native, old = source(), oracle()
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            current, previous = directory / "current.json", directory / "previous.json"
            current.write_text(json.dumps(expansion()))
            previous.write_text(json.dumps({"iteration_signature": "new"}))
            for flags in [
                [],
                ["--iteration", "-2", "--max-iterations", "-1"],
                [
                    "--previous-expansion-map",
                    str(previous),
                    "--previous-expansion-map",
                    str(previous),
                ],
            ]:
                observed = []
                for index, module in enumerate([old, native]):
                    log = directory / f"log{index}.jsonl"
                    out = io.StringIO()
                    with redirect_stdout(out):
                        code = module.main(
                            [
                                "--case",
                                "never-called",
                                "--expansion-map",
                                str(current),
                                "--reasoning-log",
                                str(log),
                                *flags,
                            ]
                        )
                    observed.append((code, out.getvalue(), stable_event(log)))
                self.assertEqual(*observed)
                self.assertEqual(observed[0][0], 0)
            for module in [old, native]:
                output = directory / "nested" / "out.json"
                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(
                        module.main(
                            ["--expansion-map", str(current), "--output", str(output)]
                        ),
                        0,
                    )
                self.assertEqual(out.getvalue(), "")
                self.assertEqual(
                    output.read_text(),
                    json.dumps(
                        old.build_control_plan(**packet(expansion())),
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                )
                # A reasoning event is appended before a failed output write.
                log = directory / f"failed-{module.__name__}.jsonl"
                with self.assertRaises(IsADirectoryError):
                    module.main(
                        [
                            "--expansion-map",
                            str(current),
                            "--output",
                            str(directory),
                            "--reasoning-log",
                            str(log),
                        ]
                    )
                self.assertEqual(len(log.read_text().splitlines()), 1)
                with self.assertRaises(SystemExit):
                    module.main([])
            malformed = directory / "malformed.json"
            malformed.write_text("{")
            with self.assertRaises(json.JSONDecodeError):
                native.load_state(
                    {
                        "expansion_map": str(malformed),
                        "previous_expansion_maps": [str(directory / "absent")],
                    }
                )
            with self.assertRaises(FileNotFoundError):
                native.load_state(
                    {
                        "expansion_map": str(current),
                        "previous_expansion_maps": [str(directory / "absent")],
                    }
                )
            with redirect_stdout(io.StringIO()):
                self.assertEqual(
                    native.main(["--self-test"]), old.main(["--self-test"])
                )
        for p, error in [
            (packet(expansion(next_frontier=[None])), AttributeError),
            (packet(expansion(next_frontier=None)), TypeError),
            (packet(expansion(outstanding_nodes=None)), TypeError),
            (packet(expansion(), [None]), AttributeError),
        ]:
            for module in [native, old]:
                with self.assertRaises(error):
                    module.build_control_plan(**deepcopy(p))
        with self.assertRaises(ValueError):
            native.finish_plan(packet(expansion()), "unknown")

    def test_cartographer_result_evidence(self):
        # Directly exercise the shared subprocess result interpreter. No process,
        # provider, scientific compiler, or production cartographer is replaced.
        native = source()
        for code, stdout in [
            (1, json.dumps(expansion())),
            (0, ""),
            (0, "{bad"),
            (0, "{}"),
        ]:
            proc = subprocess.CompletedProcess(
                ["native-cartographer"], code, stdout=stdout, stderr="x" * 2100
            )
            exp = native.cartographer_result("fixture", proc)
            self.assertEqual(exp["status"], "blocked")
            self.assertFalse(exp["exhaustive"])
            self.assertEqual(exp["cartographer_error"]["stdout_tail"], stdout[-2000:])
            self.assertEqual(len(exp["cartographer_error"]["stderr_tail"]), 2000)
            plan = native.build_control_plan(**packet(exp))
            self.assertEqual(
                plan["blockers"],
                ["expansion_map_blocked", "expansion_map_not_exhaustive"],
            )
            self.assertEqual(plan["next_actions"], [])
        self.assertEqual(
            native.cartographer_result(
                "fixture",
                subprocess.CompletedProcess([], 0, json.dumps(expansion()), ""),
            ),
            expansion(),
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
            "sympy-recursive-control",
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
                        "mcp:sympy-recursive-control",
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

            async def allow():
                pass

            async def run(inputs, doc=None):
                w, a = compile(doc) if doc else (compiled, snapshot)
                self.assertTrue(w["runnable"], w["diagnostics"])
                return await execute(w, a, inputs, remote, allow)

            with tempfile.TemporaryDirectory() as tmp:
                directory = Path(tmp)
                current = directory / "current.json"

                def inputs(p, **extra):
                    current.write_text(json.dumps(p["expansion_map"]))
                    paths = []
                    for i, exp in enumerate(p["previous_expansion_maps"]):
                        path = directory / f"prior-{i}.json"
                        path.write_text(json.dumps(exp))
                        paths.append(path.name)
                    return dict(
                        request=dict(
                            case="would-run-if-map-did-not-win",
                            expansion_map=current.name,
                            previous_expansion_maps=paths,
                            iteration=p["iteration"],
                            max_iterations=p["max_iterations"],
                            **extra,
                        ),
                        context=dict(working_directory=str(directory)),
                    )

                for p, status, branch in fixtures():
                    supplied = inputs(p)
                    result = await run(supplied)
                    self.assertEqual(result["status"], "accepted", result)
                    expected = oracle().build_control_plan(**p)
                    self.assertEqual(
                        result["outputs"],
                        dict(
                            plan=expected,
                            exit_code=0,
                            stdout_text=json.dumps(
                                expected, ensure_ascii=False, indent=2
                            )
                            + "\n",
                        ),
                    )
                    self.assertEqual(
                        [c["tool"] for c in result["calls"]],
                        [
                            PREFIX + n
                            for n in ["load_state", "compute_guards", "finish_plan"]
                        ],
                    )
                    self.assertEqual(len(result["calls"]), 3)  # recurse does not loop
                    self.assertTrue(
                        all(
                            c["execution_performed"] and c["status"] == "accepted"
                            for c in result["calls"]
                        )
                    )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["runtime"]["provenance"])
                    self.assertTrue(result["replay_artifacts"])
                    loaded = await remote.call(PREFIX + "load_state", supplied)
                    self.assertEqual(loaded["state"]["iteration"], p["iteration"])
                    self.assertEqual(
                        loaded["state"]["previous_expansion_maps"],
                        p["previous_expansion_maps"],
                    )
                    guarded = await remote.call(PREFIX + "compute_guards", loaded)
                    self.assertEqual(source().choose_branch(guarded["guards"]), branch)
                    finished = await remote.call(
                        PREFIX + "finish_plan", {**loaded, "branch": branch}
                    )
                    self.assertEqual(finished["plan"], expected)
                # Native defaults and optional writes are part of the real tool.
                p = packet(expansion())
                supplied = inputs(
                    p, output="nested/out.json", reasoning_log="events.jsonl"
                )
                del supplied["request"]["iteration"]
                del supplied["request"]["max_iterations"]
                result = await run(supplied)
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(result["outputs"]["stdout_text"], "")
                self.assertEqual(
                    json.loads((directory / "nested/out.json").read_text()),
                    result["outputs"]["plan"],
                )
                event = stable_event(directory / "events.jsonl")
                self.assertEqual(
                    event["step"], "physics_sympy_recursive_repair_control_complete"
                )
                self.assertEqual(event["payload"]["decision"], "recurse")
                for p in [
                    packet(expansion(next_frontier=[None])),
                    packet(expansion(next_frontier=None)),
                    packet(expansion(outstanding_nodes=None)),
                ]:
                    result = await run(inputs(p))
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(len(result["calls"]), 3)
                    self.assertEqual(result["calls"][-1]["status"], "rejected")
                current.write_text("{")
                result = await run(
                    dict(
                        request={"expansion_map": str(current)},
                        context={"working_directory": str(directory)},
                    )
                )
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(len(result["calls"]), 1)
                for request in [
                    {"case": ""},
                    {"expansion_map": ""},
                    {"expansion_map": "absent.json"},
                    {
                        "expansion_map": current.name,
                        "previous_expansion_maps": ["absent.json"],
                    },
                ]:
                    result = await run(
                        dict(
                            request=request,
                            context={"working_directory": str(directory)},
                        )
                    )
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(len(result["calls"]), 1)
                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        PREFIX + "finish_plan",
                        {
                            "state": {**packet(expansion()), "request": {}},
                            "state_json": json.dumps(
                                {**packet(expansion()), "request": {}}
                            ),
                            "branch": "unknown",
                        },
                    )
                # Reasoning log is written before output failure, with no retries.
                result = await run(
                    inputs(
                        packet(expansion()),
                        output=str(directory),
                        reasoning_log="before-failure.jsonl",
                    )
                )
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(
                    len((directory / "before-failure.jsonl").read_text().splitlines()),
                    1,
                )
                for budget in [1, 2]:
                    limited = deepcopy(document)
                    limited["policy"]["limits"]["max_operation_calls"] = budget
                    result = await run(inputs(packet(expansion())), limited)
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
                    await execute(
                        w, a, inputs(packet(expansion())), remote, pending_authorization
                    )
        self.assertFalse(manager.active)


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False).result
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
