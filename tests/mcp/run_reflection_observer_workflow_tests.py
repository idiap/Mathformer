#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Offline fixtures through native observer, production MCP and real Lunar/PRISM.

This source has no provider/compiler boundary: none is substituted. The real
PRISM parser, checker, compiler and runtime execute file-fixture observations.
WORKFLOW_CONTRACT_PATH must explicitly select the candidate or installed contract.
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
import yaml

from reflection_observer_tools import source
from mcp_connections.client import SessionManager
from mcp_connections.client import MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/loop/loop_reflection_testing_loop_workflow/workflow.yaml"
PREFIX = "mathformer_reflection_"
HOOKS = ROOT / "skills/SKILL_HOOKS.yaml"


def document():
    return yaml.safe_load(Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text())


def snapshot(doc, descriptor=DESCRIPTOR):
    def asset(path, text):
        return {
            "path": path,
            "content": text,
            "encoding": "text",
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
        }

    return [asset(descriptor, json.dumps(doc))] + [
        asset(row["path"], (ROOT / row["path"]).read_text())
        for row in doc["provenance"]["sources"]
    ]


def oracle():
    path = ROOT / "tests/mcp/fixtures/reflection_observer_original.py.txt"
    spec = importlib.util.spec_from_loader(
        "reflection_observer_oracle",
        SourceFileLoader("reflection_observer_oracle", str(path)),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.REPO_ROOT = ROOT
    return module


def canonical(value):
    # Native clock metadata and generated call IDs differ between invocations.
    # Round-trip tuples exactly as MCP/JSON does, without discarding evidence.
    value = json.loads(json.dumps(value))

    def clean(item):
        if isinstance(item, dict):
            return {
                key: clean(val)
                for key, val in item.items()
                if key not in {"generated_at_utc", "created_at_utc", "skill_call_id"}
            }
        if isinstance(item, list):
            return [clean(val) for val in item]
        return item

    return clean(value)


def events(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines()]


def event_evidence(path):
    return [{"step": e["step"], "payload": e["payload"]} for e in events(path)]


def fixture_report():
    return {
        "suite": "deterministic-observer-fixture",
        "summary": {
            "passed": True,
            "case_count": 1,
            "compatibility_score": 100,
            "max_difficulty_score": 10,
        },
        "cases": [
            {
                "id": "kept",
                "lean_theorem_present": True,
                "static_latex_review": {"passed": True, "warnings": []},
                "difficulty": {"ok": True, "score": 10},
            }
        ],
    }


class ReflectionObserverTests(unittest.TestCase):
    identity = "loop_reflection_testing_loop_workflow"
    descriptor = DESCRIPTOR
    authored = "skills/control/workflow-contract-validator/references/reflection-observer.workflow.json"

    def setUp(self):
        self.native = source()
        self.original = oracle()
        self.temp = tempfile.TemporaryDirectory(prefix="reflection-fixture-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.report = self.directory / "report.json"
        self.log = self.directory / "input.jsonl"
        self.out = self.directory / "packet.json"
        self.observer = self.directory / "observer.jsonl"
        self.baseline = self.directory / "baseline.json"
        self.monitor = self.directory / "monitor.json"
        self.report.write_text(json.dumps(fixture_report()))
        # A genuine structured source event is fixture input to the real strict
        # validator and summarizer. No log-validation result is stubbed.
        self.native.append_event(
            self.log,
            step="reflective_refinement_loop_start",
            payload={"report_file": "deterministic-fixture"},
        )
        self.assertTrue(
            self.native.validate_reasoning_log(self.log, hooks_file=HOOKS, strict=True)[
                "ok"
            ]
        )

    def argv(self, *extra):
        return [
            "--report-file",
            str(self.report),
            "--reasoning-log-file",
            str(self.log),
            "--hooks-file",
            str(HOOKS),
            "--output-file",
            str(self.out),
            "--observer-reasoning-log-file",
            str(self.observer),
            *extra,
        ]

    def test_original_entrypoint_equivalence_and_native_failure_order(self):
        for label in (
            "passed",
            "failed",
            "baseline",
            "critic",
            "slice_zero",
            "slice_negative",
            "text",
            "missing_baseline_path",
        ):
            with self.subTest(label=label):
                report = fixture_report()
                extra = []
                if label == "failed":
                    report["summary"]["passed"] = False
                if label == "baseline":
                    self.baseline.write_text(
                        json.dumps(
                            {
                                "successful_cases": {"lost": True},
                                "metrics": {"compatibility_score": 101},
                            }
                        )
                    )
                    extra += ["--baseline-file", str(self.baseline), "--write-baseline"]
                if label == "critic":
                    self.monitor.write_text(
                        json.dumps(
                            {
                                "monotonicity_comparison": {
                                    "regressions": [{"measure": "risk"}]
                                }
                            }
                        )
                    )
                    extra += ["--reference-free-monitor-file", str(self.monitor)]
                if label.startswith("slice_"):
                    report["cases"][0]["static_latex_review"]["warnings"] = [
                        "fixture warning"
                    ]
                    extra += [
                        "--max-opportunities",
                        "0" if label == "slice_zero" else "-1",
                    ]
                if label == "missing_baseline_path":
                    extra += ["--write-baseline"]
                if label != "text":
                    extra += ["--json"]
                self.report.write_text(json.dumps(report))
                baseline_before = (
                    self.baseline.read_bytes() if self.baseline.exists() else None
                )
                argv = self.argv(*extra)
                outcomes = []
                for runner in (self.original.main, self.native.main):
                    self.out.unlink(missing_ok=True)
                    self.observer.unlink(missing_ok=True)
                    if baseline_before is not None:
                        self.baseline.write_bytes(baseline_before)
                    console = io.StringIO()
                    error = None
                    with redirect_stdout(console):
                        try:
                            code = runner(argv)
                        except ValueError as exc:
                            error, code = str(exc), None
                    packet = json.loads(self.out.read_text())
                    baseline = (
                        json.loads(self.baseline.read_text())
                        if self.baseline.exists()
                        else None
                    )
                    stdout = (
                        json.loads(console.getvalue())
                        if "--json" in extra and not error
                        else console.getvalue()
                    )
                    outcomes.append(
                        canonical(
                            [
                                code,
                                error,
                                packet,
                                baseline,
                                stdout,
                                event_evidence(self.observer),
                            ]
                        )
                    )
                self.assertEqual(outcomes[0], outcomes[1])
                if label == "missing_baseline_path":
                    self.assertEqual(
                        outcomes[1][1], "--write-baseline requires --baseline-file"
                    )
                    self.assertNotIn(
                        "reflective_refinement_loop_complete",
                        [e["step"] for e in events(self.observer)],
                    )
        # Both entrypoints preserve argparse's native successful and error stops.
        for argv, expected in [(["--help"], 0), (["--unknown-option"], 2)]:
            for runner in (self.original.main, self.native.main):
                with (
                    redirect_stdout(io.StringIO()),
                    redirect_stderr(io.StringIO()),
                    self.assertRaises(SystemExit) as stopped,
                ):
                    runner(argv)
                self.assertEqual(stopped.exception.code, expected)

    def test_service_write_guards(self):
        # Configure real service policies and invoke the registered tool through
        # actual stdio MCP. No fake registry or source callback is substituted.
        async def scenario():
            for setting in (
                "server._READONLY=True",
                "server.apply_runtime_config(allowed_write_roots=[])",
            ):
                manager = SessionManager()
                script = (
                    'import sys;sys.path.insert(0,"scripts");'
                    "import mcp_server as server;" + setting + ";"
                    'server.mcp.run(transport="stdio")'
                )
                python = ROOT / ".venv/bin/python"
                async with manager.open(
                    "reflection-policy",
                    StdioConfig(
                        command=str(python) if python.exists() else sys.executable,
                        args=["-c", script],
                        cwd=str(ROOT),
                    ),
                    {},
                ) as remote:
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(PREFIX + "load", {"argv": self.argv()})
                    # Help terminates before write authorization or file access.
                    halted = await remote.call(PREFIX + "load", {"argv": ["--help"]})
                    self.assertTrue(halted["loaded"]["halted"])
                self.assertFalse(manager.active)
                self.assertFalse(self.observer.exists())
                self.assertFalse(self.out.exists())

        asyncio.run(scenario())

    def test_registered_tools_compile_and_execute(self):
        asyncio.run(self.runtime_scenario())

    async def runtime_scenario(self):
        doc = document()
        self.assertEqual(doc["id"], self.identity)
        self.assertEqual(doc["lifecycle"], "active")
        self.assertEqual(doc["policy"]["limits"]["max_operation_calls"], 6)
        self.assertEqual(doc["policy"]["failure"]["retry"]["max_attempts"], 1)
        authored = ROOT / self.authored
        self.assertEqual(doc, json.loads(authored.read_text()))
        for row in doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        # Production registration is used, without starting a configured service,
        # reading credentials, selecting models or invoking external processes.
        server_python = ROOT / ".venv/bin/python"
        async with manager.open(
            "reflection",
            StdioConfig(
                command=(
                    str(server_python) if server_python.exists() else sys.executable
                ),
                args=["-c", server],
                cwd=str(ROOT),
            ),
            {},
        ) as remote:
            failure = None
            try:
                tools = [
                    tool.model_dump(by_alias=True, exclude_none=True)
                    for tool in await remote.tools()
                ]

                def compile(selected=doc, inventory=tools):
                    assets = snapshot(selected, self.descriptor)
                    workflow = workflow_documents([self.descriptor], assets)[0]
                    return (
                        compile_workflow("mcp:reflection", workflow, inventory),
                        assets,
                    )

                compiled, assets = compile()
                self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                self.assertTrue(compiled["runtime_source"])
                self.assertEqual(set(compiled["bindings"]), set(doc["operations"]))
                self.assertFalse(compile(inventory=[])[0]["runnable"])

                async def authorize():
                    pass

                async def run(extra=(), selected=doc, argv=None):
                    self.out.unlink(missing_ok=True)
                    self.observer.unlink(missing_ok=True)
                    workflow, received = (
                        (compiled, assets) if selected is doc else compile(selected)
                    )
                    return await execute(
                        workflow,
                        received,
                        {"argv": self.argv(*extra) if argv is None else argv},
                        remote,
                        authorize,
                    )

                def call_names(result):
                    return [
                        call["tool"].removeprefix(PREFIX) for call in result["calls"]
                    ]

                def assert_packet(result, code):
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(result["outputs"]["exit_code"], code)
                    packet = result["outputs"]["packet"]
                    self.assertEqual(json.loads(self.out.read_text()), packet)
                    self.assertEqual(
                        call_names(result),
                        [
                            "load",
                            "observe",
                            "propose",
                            "pack",
                            "persist",
                            (
                                "finish_with_baseline"
                                if self.native.prepare_reflection(self.last_argv)[
                                    "write_baseline"
                                ]
                                else "finish"
                            ),
                        ],
                    )
                    self.assertEqual(
                        packet["todos"],
                        self.native.build_todos(packet["opportunities"]),
                    )
                    self.assertEqual(
                        len(events(self.observer)), 4 + len(packet["opportunities"])
                    )
                    indices = [e["event_index"] for e in events(self.observer)]
                    # The native logger retains its process-local counter even
                    # when a caller removes a file between separate invocations.
                    self.assertGreaterEqual(indices[0], 1)
                    self.assertEqual(
                        indices, list(range(indices[0], indices[0] + len(indices)))
                    )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["replay_artifacts"])
                    return packet

                async def check(extra=(), code=0):
                    self.last_argv = self.argv(*extra)
                    return assert_packet(await run(extra), code)

                with redirect_stdout(io.StringIO()):
                    self.assertEqual(self.original.main(self.argv("--json")), 0)
                expected_packet = json.loads(self.out.read_text())
                expected_events = event_evidence(self.observer)
                packet = await check(["--json"])
                self.assertEqual(canonical(packet), canonical(expected_packet))
                self.assertEqual(
                    canonical(event_evidence(self.observer)), canonical(expected_events)
                )
                self.assertTrue(packet["ok"])
                self.assertEqual(
                    [o["id"] for o in packet["opportunities"]],
                    ["expand-regression-suite"],
                )
                self.assertFalse(packet["baseline_comparison"]["baseline_present"])
                self.assertIsNone(packet["reference_free_monitor"])
                self.assertEqual(packet["reasoning_event_summary"]["event_count"], 1)
                self.assertEqual(len(packet["gate_decision"]["checks"]), 4)
                self.assertTrue(
                    all(
                        isinstance(c, str)
                        for c in packet["monotonicity_contract"]["required_commands"]
                    )
                )
                history = events(self.observer)
                repeated = await execute(
                    compiled, assets, {"argv": self.argv("--json")}, remote, authorize
                )
                self.assertEqual(repeated["status"], "accepted", repeated)
                appended = events(self.observer)
                self.assertEqual(appended[: len(history)], history)
                self.assertEqual(len(appended), 2 * len(history))
                self.assertEqual(
                    appended[len(history)]["event_index"],
                    history[-1]["event_index"] + 1,
                )
                self.assertEqual(
                    canonical(repeated["outputs"]["packet"]), canonical(packet)
                )
                # No optional existing file means no comparison, including explicit
                # missing paths. These calls emit strings, never regression commands.
                packet = await check(
                    [
                        "--baseline-file",
                        str(self.baseline),
                        "--reference-free-monitor-file",
                        str(self.monitor),
                    ]
                )
                self.assertFalse(packet["baseline_comparison"]["baseline_present"])
                self.assertFalse(self.baseline.exists())
                self.assertFalse(self.monitor.exists())
                # Exact transported state is used by later registered tools, not read
                # back from a possibly changed report file. Direct MCP tools share the
                # same source functions as the compiled path.
                loaded = (
                    await remote.call(
                        PREFIX + "load", {"argv": self.argv("--max-opportunities", "0")}
                    )
                )["loaded"]
                changed = fixture_report()
                changed["summary"]["passed"] = False
                self.report.write_text(json.dumps(changed))
                observed = (await remote.call(PREFIX + "observe", {"loaded": loaded}))[
                    "observation"
                ]
                self.assertEqual(observed["log_validation"]["ok"], True)
                proposed = (
                    await remote.call(
                        PREFIX + "propose", {"loaded": loaded, "observation": observed}
                    )
                )["opportunities"]
                self.assertEqual(proposed, [])
                packed = (
                    await remote.call(
                        PREFIX + "pack",
                        {
                            "loaded": loaded,
                            "observation": observed,
                            "opportunities": proposed,
                        },
                    )
                )["packet"]
                self.assertTrue(packed["ok"])
                self.report.write_text(json.dumps(fixture_report()))
                # Baseline snapshot state is explicit cross-invocation data. Difficulty
                # >5 is advisory; lost successes and lower compatibility block the gate.
                self.baseline.write_text(
                    json.dumps(
                        {
                            "successful_cases": {"kept": True},
                            "metrics": {
                                "compatibility_score": 100,
                                "max_difficulty_score": 5,
                            },
                        }
                    )
                )
                self.monitor.write_text(
                    json.dumps(
                        {"monotonicity_comparison": {"regressions": ["ignored"]}}
                    )
                )
                packet = await check(
                    [
                        "--baseline-file",
                        str(self.baseline),
                        "--reference-free-monitor-file",
                        str(self.monitor),
                    ]
                )
                self.assertEqual(packet["baseline_comparison"]["warnings"], [])
                self.baseline.write_text(
                    json.dumps(
                        {
                            "successful_cases": {"kept": True},
                            "metrics": {
                                "compatibility_score": 100,
                                "max_difficulty_score": 4,
                            },
                        }
                    )
                )
                packet = await check(["--baseline-file", str(self.baseline)])
                self.assertEqual(len(packet["baseline_comparison"]["warnings"]), 1)
                self.baseline.write_text(
                    json.dumps(
                        {
                            "successful_cases": {"kept": True, "lost": True},
                            "metrics": {"compatibility_score": 101},
                        }
                    )
                )
                self.monitor.write_text(
                    json.dumps(
                        {
                            "summary": {"regression_count": 1},
                            "monotonicity_comparison": {
                                "regressions": ["ignored", {"measure": "risk"}]
                            },
                            "measures": {"confidence": {"score": 40}},
                        }
                    )
                )
                failing = fixture_report()
                failing["summary"]["passed"] = False
                failing["cases"][0]["static_latex_review"]["warnings"] = [
                    "fixture warning"
                ]
                failing["backend"] = "sympy"
                failing["validation_criteria"] = {"assumption_fidelity": False}
                failing["cases"][0]["hierarchy_navigation"] = {
                    "ok": True,
                    "matching_module_count": 0,
                }
                failing["cases"][0]["concept_map"] = {
                    "ok": True,
                    "summary": {"fixture": {"top_candidate": {"kind": "hint"}}},
                }
                failing["cases"][0]["difficulty"]["max_difficulty_score"] = 35
                failing["expected_declaration_checks"] = {
                    "ok": True,
                    "checks": {"fixture": True},
                }
                self.report.write_text(json.dumps(failing))
                self.log.write_text("{malformed-json\n")
                full = await check(
                    [
                        "--baseline-file",
                        str(self.baseline),
                        "--reference-free-monitor-file",
                        str(self.monitor),
                    ],
                    3,
                )
                self.assertFalse(full["ok"])
                self.assertEqual(len(full["gate_decision"]["blocking_failures"]), 4)
                self.assertEqual(len(full["baseline_comparison"]["regressions"]), 2)
                self.assertEqual(len(full["opportunities"]), 8)
                unbounded = await check(
                    [
                        "--baseline-file",
                        str(self.baseline),
                        "--reference-free-monitor-file",
                        str(self.monitor),
                        "--max-opportunities",
                        "99",
                    ],
                    3,
                )
                opportunities = unbounded["opportunities"]
                self.assertEqual(len(opportunities), 9)
                self.assertEqual(full["opportunities"], opportunities[:8])
                self.assertEqual(
                    [o["priority"] for o in opportunities],
                    sorted(o["priority"] for o in opportunities),
                )
                self.assertEqual(
                    [o["id"] for o in opportunities[:3]],
                    [
                        "sympy-validation-refinement",
                        "reasoning-log-schema-repair",
                        "reference-free-regression-repair",
                    ],
                )
                self.assertTrue(
                    all(
                        o["apply_mode"] == "manual_review_required"
                        for o in opportunities
                    )
                )
                for cap in (0, 1, -1, 8):
                    limited = await check(
                        [
                            "--baseline-file",
                            str(self.baseline),
                            "--reference-free-monitor-file",
                            str(self.monitor),
                            "--max-opportunities",
                            str(cap),
                        ],
                        3,
                    )
                    self.assertEqual(limited["opportunities"], opportunities[:cap])
                # Baseline is persisted even on a failed gate and reflects the report,
                # not previous successes. The packet still records pre-write evidence.
                packet = await check(
                    [
                        "--baseline-file",
                        str(self.baseline),
                        "--reference-free-monitor-file",
                        str(self.monitor),
                        "--write-baseline",
                    ],
                    3,
                )
                baseline = json.loads(self.baseline.read_text())
                self.assertEqual(baseline["successful_cases"], {"kept": True})
                self.assertFalse(baseline["metrics"]["passed"])
                self.assertIn("lost", packet["monotonicity_contract"]["preserve_cases"])
                # No iterations or retries are invented: each normal run is six calls.
                # The missing baseline-path error occurs after packet persistence.
                failed = await run(["--write-baseline"])
                self.assertEqual(failed["status"], "failed", failed)
                self.assertEqual(len(failed["calls"]), 6)
                self.assertIsNone(failed["outputs"])
                self.assertTrue(self.out.exists())
                self.assertNotIn(
                    "reflective_refinement_loop_complete",
                    [e["step"] for e in events(self.observer)],
                )
                # Native data/I/O errors propagate at the same phase; no later writes.
                self.monitor.write_text("[]")
                failed = await run(["--reference-free-monitor-file", str(self.monitor)])
                self.assertEqual(failed["status"], "failed")
                self.assertEqual(call_names(failed), ["load"])
                self.assertEqual(len(events(self.observer)), 1)
                self.assertFalse(self.out.exists())
                self.baseline.write_text("{bad")
                failed = await run(["--baseline-file", str(self.baseline)])
                self.assertEqual(failed["status"], "failed")
                self.assertEqual(call_names(failed), ["load"])
                self.report.write_text("[]")
                failed = await run()
                self.assertEqual(failed["status"], "failed")
                self.assertEqual(call_names(failed), ["load"])
                self.report.unlink()
                failed = await run()
                self.assertEqual(failed["status"], "failed")
                self.assertEqual(call_names(failed), ["load"])
                self.report.write_text(json.dumps(fixture_report()))
                # Native packet-write failure blocks baseline and completion, with
                # prior source-owned events retained for inspection.
                blocker = self.directory / "blocker"
                blocker.write_text("file")
                failed = await run(["--output-file", str(blocker / "packet.json")])
                self.assertEqual(failed["status"], "failed")
                self.assertEqual(
                    call_names(failed),
                    ["load", "observe", "propose", "pack", "persist"],
                )
                failed = await run(
                    [
                        "--baseline-file",
                        str(blocker / "baseline.json"),
                        "--write-baseline",
                    ]
                )
                self.assertEqual(failed["status"], "failed")
                self.assertEqual(len(failed["calls"]), 6)
                self.assertTrue(self.out.exists())
                self.assertNotIn(
                    "reflective_refinement_loop_complete",
                    [e["step"] for e in events(self.observer)],
                )
                # Native help stops before I/O; invalid parsing fails once, no retry.
                result = await run(argv=["--help"])
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(result["outputs"], {"packet": None, "exit_code": 0})
                self.assertEqual(call_names(result), ["load", "help"])
                self.assertFalse(self.observer.exists())
                self.assertFalse(self.out.exists())
                result = await run(argv=["--max-opportunities", "invalid"])
                self.assertEqual(result["status"], "failed")
                self.assertEqual(call_names(result), ["load"])
                self.assertFalse(self.observer.exists())
                # Real host budget exhaustion after five calls never fabricates a
                # successful finish or overwrites the explicit baseline state.
                budget = deepcopy(doc)
                budget["policy"]["limits"]["max_operation_calls"] = 5
                result = await run(selected=budget)
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(len(result["calls"]), 6)
                self.assertEqual(result["calls"][-1]["status"], "rejected")
                self.assertIn("budget", json.dumps(result).lower())
                self.assertIsNone(result["outputs"])
                self.assertTrue(self.out.exists())
                self.assertNotIn(
                    "reflective_refinement_loop_complete",
                    [e["step"] for e in events(self.observer)],
                )
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure is not None:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
