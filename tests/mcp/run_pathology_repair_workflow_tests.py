#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402 -- bootstrap the host Lunar environment
"""Frozen source oracle, actual MCP registration and real PRISM compilation/runtime.

This planner has no external provider, model, compiler or prover boundary to
substitute. Deterministic report/compiler-input fixtures run only pure planning.
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
import json
import tempfile
import unittest
import yaml
from pathology_repair_tools import source, SOURCE
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_physics_lean_pathology_repair_loop_workflow/workflow.yaml"
AUTHORED = "skills/control/workflow-contract-validator/references/pathology-repair.workflow.json"
PREFIX = "mathformer_pathology_repair_"


def oracle():
    loader = SourceFileLoader(
        "pathology_original",
        str(ROOT / "tests/mcp/fixtures/pathology_repair_original.py.txt"),
    )
    module = importlib.util.module_from_spec(
        importlib.util.spec_from_loader(loader.name, loader)
    )
    loader.exec_module(module)
    return module


def reports(**updates):
    return {
        "monitor_report": {},
        "object_packet": {},
        "workbench_plan": {},
        "repair_plans": [],
        **updates,
    }


def fixtures():
    blocked = reports(
        monitor_report={
            "status": "fail",
            "category_counts": {
                "z": "2",
                "notational_collapse": 1,
                "zero": 0,
                "negative": -1,
            },
        },
        object_packet={"objects": [1, 2], "status": "ready"},
        workbench_plan={
            "status": "library_work_required",
            "items": [
                {"object_class": "operator", "status": "candidate_required"},
                {"object_class": "operator", "status": "candidate_required"},
                {"object_class": "reused", "status": "mathformer_reused"},
            ],
        },
        repair_plans=[
            {
                "style": "physics_lean_notational_collapse_repair_plan",
                "status": "needs_labeling",
                "blockers": ["duplicate", "duplicate", 17],
            },
            {
                "style": "physics_lean_notational_collapse_repair_plan",
                "status": "ready",
            },
            {"style": "custom", "status": "blocked_on_library"},
        ],
    )
    passed = deepcopy(blocked)
    passed["monitor_report"]["status"] = "pass"
    ready = reports(
        monitor_report={"category_counts": {"custom": "1"}},
        repair_plans=[{"style": "custom"}],
        object_packet={"object_count": {"opaque": 1}},
    )
    many = reports(
        monitor_report={"category_counts": {f"c{i}": 1 for i in range(129)}},
        repair_plans=[{"style": f"c{i}"} for i in range(129)],
    )
    return [
        reports(),
        blocked,
        passed,
        ready,
        reports(monitor_report={"category_counts": []}),
        many,
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


class PathologyTests(unittest.TestCase):
    def test_native_equivalence_and_cli(self):
        native, old = source(), oracle()
        for packet in fixtures():
            self.assertEqual(
                native.build_loop_plan(**deepcopy(packet)),
                old.build_loop_plan(**deepcopy(packet)),
            )
        plan = native.build_loop_plan(**fixtures()[1])
        self.assertEqual(plan["active_categories"], ["notational_collapse", "z"])
        self.assertEqual(plan["missing_repair_plans"], ["z"])
        self.assertEqual(
            plan["blockers"],
            [
                "17",
                "custom:blocked_on_library",
                "duplicate",
                "library_object_not_ready:operator",
                "missing_repair_plan:z",
                "physics_lean_notational_collapse_repair_plan:needs_labeling",
            ],
        )
        self.assertEqual(plan["object_count"], 2)
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            argv = []
            for name, value in fixtures()[1].items():
                values = value if name == "repair_plans" else [value]
                flag = (
                    "--repair-plan"
                    if name == "repair_plans"
                    else "--" + name.replace("_", "-")
                )
                for i, v in enumerate(values):
                    p = directory / f"{name}-{i}.json"
                    p.write_text(json.dumps(v))
                    argv.extend([flag, str(p)])
            for args in [
                [],
                argv,
                ["--self-test", "--monitor-report", str(directory / "missing")],
            ]:
                for flags in [[], ["--output", str(directory / "nested/out.json")]]:
                    observed = []
                    for module in [old, native]:
                        stream = io.StringIO()
                        with redirect_stdout(stream):
                            code = module.main(args + flags)
                        observed.append(
                            (
                                code,
                                stream.getvalue(),
                                (
                                    (directory / "nested/out.json").read_bytes()
                                    if flags
                                    else None
                                ),
                            )
                        )
                    self.assertEqual(*observed)

    def test_native_failure_order(self):
        for packet, error in [
            (
                reports(
                    monitor_report={"status": "pass", "category_counts": {"bad": "x"}}
                ),
                ValueError,
            ),
            (reports(workbench_plan={"items": [None]}), AttributeError),
            (reports(repair_plans=[{"blockers": None}]), TypeError),
            (reports(object_packet={"object_count": 5, "objects": None}), TypeError),
        ]:
            for module in [source(), oracle()]:
                with self.assertRaises(error):
                    module.build_loop_plan(**deepcopy(packet))

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
            "pathology",
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
                        "mcp:pathology",
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

            async def run(packet, doc=None):
                w, a = compile(doc) if doc else (compiled, assets)
                self.assertTrue(w["runnable"], w["diagnostics"])
                return await execute(w, a, {"reports": packet}, remote, allow)

            for packet in fixtures():
                result = await run(packet)
                self.assertEqual(result["status"], "accepted", result)
                expected = oracle().build_loop_plan(**packet)
                self.assertEqual(result["outputs"], {"result": expected})
                self.assertEqual(
                    [c["tool"] for c in result["calls"]],
                    [PREFIX + n for n in ["aggregate", "assign_status", "assemble"]],
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
                self.assertEqual(expected["loop_steps"][-1]["status"], "pending")
                self.assertEqual(
                    expected["target_refinement_policy"]["may_edit_target_theorem"],
                    expected["status"] == "ready_for_target_refinement",
                )
                if packet["monitor_report"].get("status") == "pass":
                    self.assertTrue(expected["blockers"])
                    self.assertEqual(expected["status"], "not_required")
                    self.assertEqual(
                        [s["status"] for s in expected["loop_steps"][4:7]],
                        ["not_required"] * 3,
                    )
            # All three tools are exercised directly as well as through bindings.
            packet = fixtures()[1]
            found = await remote.call(PREFIX + "aggregate", {"reports": packet})
            self.assertEqual(
                found["findings"],
                source().aggregate_findings(
                    monitor_report=packet["monitor_report"],
                    workbench_plan=packet["workbench_plan"],
                    repair_plans=packet["repair_plans"],
                ),
            )
            self.assertEqual(
                await remote.call(
                    PREFIX + "assign_status", {"status": "blocked_on_library_or_labels"}
                ),
                {"status": "blocked_on_library_or_labels"},
            )
            self.assertEqual(
                await remote.call(
                    PREFIX + "assemble",
                    {
                        "reports": packet,
                        **found,
                        "status": "blocked_on_library_or_labels",
                    },
                ),
                {"result": oracle().build_loop_plan(**packet)},
            )
            for packet, calls in [
                (
                    reports(
                        monitor_report={
                            "status": "pass",
                            "category_counts": {"bad": "invalid"},
                        }
                    ),
                    1,
                ),
                (reports(workbench_plan={"items": [None]}), 1),
                (reports(repair_plans=[{"blockers": None}]), 1),
                (reports(object_packet={"object_count": 5, "objects": None}), 3),
            ]:
                result = await run(packet)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(len(result["calls"]), calls)
                self.assertEqual(result["calls"][-1]["status"], "rejected")
                self.assertTrue(result["calls"][-1]["error"])
            with self.assertRaises(MCPConnectionError):
                await remote.call(
                    PREFIX + "aggregate",
                    {
                        "reports": reports(
                            monitor_report={"category_counts": {"x": "bad"}}
                        )
                    },
                )
            # Native traversal is unbounded; the host call budget is separate.
            # Exhausting it must stop before the next MCP call, without retries.
            for budget in [1, 2]:
                limited = deepcopy(document)
                limited["policy"]["limits"]["max_operation_calls"] = budget
                result = await run(reports(), limited)
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
                    w, a, {"reports": reports()}, remote, pending_authorization
                )
        self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
