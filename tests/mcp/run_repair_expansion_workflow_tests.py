#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402 -- use the host's real Lunar/PRISM environment
"""Frozen mapper oracle, registered MCP tools, and real Lunar/PRISM execution.

The mapper is a pure evidence planner: no provider/model or external theorem
compiler boundary exists. JSON evidence and contract input/budget variants are
our deterministic fixtures; no production steps are replaced or simulated.
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
import itertools
import json
import tempfile
import unittest
import yaml

from repair_expansion_tools import source, SOURCE
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_physics_lean_repair_expansion_map_workflow/workflow.yaml"
AUTHORED = "skills/control/workflow-contract-validator/references/repair-expansion.workflow.json"
ORIGINAL = ROOT / "tests/mcp/fixtures/repair_expansion_original.py.txt"
PREFIX = "mathformer_repair_expansion_"


def oracle():
    loader = SourceFileLoader("expansion_original", str(ORIGINAL))
    module = importlib.util.module_from_spec(
        importlib.util.spec_from_loader(loader.name, loader)
    )
    loader.exec_module(module)
    return module


def packets(**updates):
    return {
        **dict(
            monitor_report={},
            object_packet={},
            workbench_plan={},
            repair_loop={},
            generative_repair={},
            repair_plans=[],
        ),
        **updates,
    }


def fixtures():
    n = source()
    p = n.fixture_packets()
    yield packets()
    yield packets(monitor_report={"status": "pass"})
    yield packets(
        monitor_report={"status": "fail", "findings": [{"category": "ignored"}]}
    )
    yield packets(
        monitor_report={
            "status": "fail",
            "category_counts": None,
            "findings": [
                None,
                {"category": "a.b"},
                {"category": "a.b"},
                {"category": "z"},
            ],
        }
    )
    yield packets(
        monitor_report={"category_counts": {"positive": "2", "zero": 0, "negative": -1}}
    )
    yield packets(
        repair_loop={"active_categories": []},
        monitor_report={"category_counts": {"ignored": 1}},
    )
    yield packets(repair_loop={"active_categories": ["z", "a", "z", 4]})
    yield p
    yield {**p, "object_packet": {}}
    yield {**p, "repair_plans": []}
    yield {**p, "workbench_plan": {}}
    yield {**p, "generative_repair": {}}
    yield {**p, "generative_repair": {"status": "pending"}}
    yield {
        **p,
        "repair_loop": {
            **p["repair_loop"],
            "target_refinement_policy": {"may_edit_target_theorem": "truthy"},
        },
    }
    # Duplicate indices retain their last value. Explicitly blocked workbench
    # entries are terminal; blocked pathology plans remain outstanding.
    yield {
        **p,
        "repair_plans": [
            p["repair_plans"][0],
            {**p["repair_plans"][0], "status": "ready", "blockers": []},
        ],
        "workbench_plan": {
            "items": [
                None,
                {"object_class": "commutator", "status": "pending"},
                {
                    "object_class": "commutator",
                    "status": "explicitly_blocked",
                    "repair_surface": {"z": "α", "a": 1},
                },
            ]
        },
    }
    many = [f"object{i:03d}" for i in range(137)]
    yield packets(
        monitor_report={"status": "pass"},
        object_packet={"objects": [{"object_class": c} for c in reversed(many)]},
        workbench_plan={
            "items": [{"object_class": c, "status": "complete"} for c in many]
        },
    )


def snapshot(doc):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(doc))] + [
        asset(r["path"], (ROOT / r["path"]).read_text())
        for r in doc["provenance"]["sources"]
    ]


class ExpansionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="repair-expansion-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.native, self.old = source(), oracle()

    def files(self, p):
        args = []
        for key, value in p.items():
            if key == "repair_plans":
                for i, plan in enumerate(value):
                    name = f"plan{i}.json"
                    (self.directory / name).write_text(
                        json.dumps(plan, ensure_ascii=False)
                    )
                    args += ["--repair-plan", name]
            else:
                name = key + ".json"
                (self.directory / name).write_text(
                    json.dumps(value, ensure_ascii=False)
                )
                args += ["--" + key.replace("_", "-"), name]
        return args

    def absolute(self, argv):
        return [str(self.directory / a) if not a.startswith("--") else a for a in argv]

    def cli(self, module, argv):
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = module.main(argv)
        return code, stream.getvalue()

    def test_frozen_source_branches_finite_bounds_and_bytes(self):
        self.assertEqual(
            hashlib.sha256(ORIGINAL.read_bytes()).hexdigest(),
            "3519c73936c5eb22eb50c9e6a09de14daab9c93b3af8a15eb40439a6a3c17b1f",
        )
        for p in fixtures():
            before = deepcopy(p)
            result = self.native.build_map(**p)
            expected = self.old.build_map(**p)
            self.assertEqual(result, expected)
            self.assertEqual(p, before)
            self.assertEqual(
                json.dumps(result, ensure_ascii=False),
                json.dumps(expected, ensure_ascii=False),
            )
            self.assertEqual(
                result["iteration_signature"],
                self.old.stable_signature(result["iteration_signature_payload"]),
            )
            self.assertEqual(
                result["recursive_rerun_gates"], self.old.RECURSIVE_RERUN_GATES
            )
            self.assertEqual(
                [x["node_id"] for x in result["next_frontier"]],
                [x["id"] for x in result["outstanding_nodes"]],
            )
            state = self.native.seed_map(p)
            for function in [
                self.native.expand_categories,
                self.native.expand_objects,
                self.native.append_policies,
            ]:
                saved = deepcopy(state)
                advanced = function(state)
                self.assertEqual(state, saved)
                self.assertEqual(
                    advanced["nodes"][: len(state["nodes"])], state["nodes"]
                )
                state = advanced
            assessment = self.native.assess_map(state)
            self.assertEqual(state["nodes"], result["nodes"])
            self.assertEqual(assessment["outstanding"], result["outstanding_nodes"])
            args = self.absolute(self.files(p))
            self.assertEqual(self.cli(self.native, args), self.cli(self.old, args))
        base = self.native.fixture_packets()
        for (
            repair_status,
            blockers,
            wb_status,
            gen_status,
            may_edit,
        ) in itertools.product(
            ["ready", "not_required", "complete", "blocked", "present"],
            [[], ["why", 2]],
            sorted(self.native.TERMINAL_WORKBENCH_STATUSES | {"pending"}),
            ["ready", "not_required", "complete", "present", "missing", "pending"],
            [True, False],
        ):
            p = deepcopy(base)
            p["monitor_report"]["status"] = "pass"
            p["repair_plans"][0].update(status=repair_status, blockers=blockers)
            p["workbench_plan"]["items"][0]["status"] = wb_status
            p["generative_repair"]["status"] = gen_status
            p["repair_loop"]["target_refinement_policy"][
                "may_edit_target_theorem"
            ] = may_edit
            actual = self.native.build_map(**p)
            self.assertEqual(actual, self.old.build_map(**p))
            self.assertEqual(actual["exhaustive"], gen_status != "missing")
            terminal = (
                repair_status in self.native.TERMINAL_REPAIR_STATUSES
                and not blockers
                and wb_status in self.native.TERMINAL_WORKBENCH_STATUSES
                and gen_status in self.native.TERMINAL_GENERATIVE_STATUSES
                and may_edit
            )
            self.assertEqual(
                actual["status"], "not_required" if terminal else "needs_expansion"
            )
        # Coverage is complete despite outstanding library/target obligations.
        self.assertTrue(self.native.build_map(**base)["exhaustive"])
        self.assertEqual(self.native.build_map(**base)["status"], "needs_expansion")
        many = self.native.build_map(**list(fixtures())[-1])
        self.assertEqual(len(many["coverage"]["detected_object_classes"]), 137)
        self.assertEqual(len(many["nodes"]), 277)
        self.assertEqual(many["outstanding_nodes"], [])
        for args in [
            [],
            ["--self-test", "--monitor-report", str(self.directory / "absent")],
        ]:
            self.assertEqual(self.cli(self.native, args), self.cli(self.old, args))
            target = self.directory / "nested/map.json"
            out = []
            for module in [self.old, self.native]:
                result = self.cli(module, args + ["--output", str(target)])
                out.append((result, target.read_bytes()))
            self.assertEqual(*out)
        for module in [self.old, self.native]:
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as e:
                module.main(["--unknown"])
            self.assertEqual(e.exception.code, 2)
            for p, error in [
                (
                    packets(monitor_report={"category_counts": {"x": "invalid"}}),
                    ValueError,
                ),
                (packets(workbench_plan={"items": None}), TypeError),
                (
                    packets(repair_loop={"target_refinement_policy": None}),
                    AttributeError,
                ),
                (packets(generative_repair={"probe_prompts": None}), TypeError),
            ]:
                with self.assertRaises(error):
                    module.build_map(**p)

    def test_registered_tools_compile_execute_and_failures(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        doc = yaml.safe_load(Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text())
        self.assertEqual(doc["id"], "hub_physics_lean_repair_expansion_map_workflow")
        self.assertEqual(doc["lifecycle"], "active")
        self.assertEqual(doc, json.loads((ROOT / AUTHORED).read_text()))
        from normalize_workflows_tools import source as generator

        generated = next(
            row for row in generator().inventory() if row["id"] == doc["id"]
        )
        self.assertEqual(doc, generated)
        for row in doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        self.assertIn(SOURCE, [row["path"] for row in doc["provenance"]["sources"]])
        self.assertTrue(
            all(
                op["execution"]["mode"] == "deterministic"
                for op in doc["operations"].values()
            )
        )
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        failure = None
        async with manager.open(
            "repair-expansion",
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

                def compile(document, inventory=None):
                    assets = snapshot(document)
                    w = workflow_documents([DESCRIPTOR], assets)[0]
                    return (
                        compile_workflow(
                            "mcp:repair-expansion",
                            w,
                            tools if inventory is None else inventory,
                        ),
                        assets,
                    )

                workflow, assets = compile(doc)
                self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                self.assertEqual(workflow["runtime_status"], "ready")
                self.assertTrue(workflow["prism_source"])
                self.assertTrue(workflow["runtime_source"])
                self.assertEqual(set(workflow["bindings"]), set(doc["operations"]))
                self.assertFalse(compile(doc, [])[0]["runnable"])
                context = {
                    "working_directory": str(self.directory),
                    "program_name": Path(sys.argv[0]).name,
                }

                async def allow():
                    pass

                async def run(argv, document=None):
                    w, a = (
                        compile(document)
                        if document is not None
                        else (workflow, assets)
                    )
                    self.assertTrue(w["runnable"], w["diagnostics"])
                    return await execute(
                        w, a, {"extra_args": argv, "context": context}, remote, allow
                    )

                for p in fixtures():
                    argv = self.files(p)
                    expected = self.old.build_map(**p)
                    result = await run(argv)
                    self.assertEqual(result["status"], "accepted", result)
                    text = json.dumps(expected, ensure_ascii=False, indent=2)
                    self.assertEqual(
                        result["outputs"],
                        {
                            "expansion": expected,
                            "exit_code": 0,
                            "stdout_text": text + "\n",
                            "json_text": text,
                        },
                    )
                    self.assertEqual(
                        [c["tool"] for c in result["calls"]],
                        [
                            PREFIX + n
                            for n in [
                                "load",
                                "seed",
                                "expand_categories",
                                "expand_objects",
                                "append_policies",
                                "assess",
                                "assign_status",
                                "finish",
                            ]
                        ],
                    )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["runtime"]["provenance"])
                    self.assertTrue(result["replay_artifacts"])
                for argv in [[], ["--self-test", "--monitor-report", "absent"]]:
                    result = await run(argv)
                    self.assertEqual(result["status"], "accepted", result)
                    expected = self.cli(self.old, self.absolute(argv))
                    self.assertEqual(
                        (
                            result["outputs"]["exit_code"],
                            result["outputs"]["stdout_text"],
                        ),
                        expected,
                    )
                    result = await run(argv + ["--output", "runtime/map.json"])
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(result["outputs"]["stdout_text"], "")
                    self.assertEqual(
                        (self.directory / "runtime/map.json").read_text(),
                        result["outputs"]["json_text"] + "\n",
                    )
                result = await run(["--help", "--monitor-report", "absent"])
                self.assertEqual(result["status"], "accepted", result)
                self.assertIsNone(result["outputs"]["expansion"])
                self.assertEqual(
                    [c["tool"] for c in result["calls"]],
                    [PREFIX + "load", PREFIX + "help"],
                )
                with (
                    redirect_stdout(io.StringIO()) as stream,
                    self.assertRaises(SystemExit) as e,
                ):
                    self.old.main(["--help"])
                self.assertEqual(e.exception.code, 0)
                self.assertEqual(result["outputs"]["stdout_text"], stream.getvalue())
                # All three source status assignments remain callable. 'complete'
                # is a redundant guard fallback because a non-pass monitor is
                # itself outstanding; inject only compiler input to reach it.
                fallback = deepcopy(doc)
                normal = fallback["flow"]["steps"][1]["default"]["steps"]
                normal[-2]["cases"][0]["when"] = {"literal": False}
                normal[-2]["cases"][1]["when"] = {"literal": False}
                result = await run([], fallback)
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(result["outputs"]["expansion"]["status"], "complete")
                self.assertTrue(result["outputs"]["expansion"]["outstanding_nodes"])
                # Force actual shared assertion failure by compiler literal input.
                asserting = deepcopy(doc)
                asserting["flow"]["steps"][1]["default"]["steps"][-1]["arguments"][
                    "options"
                ] = {
                    "literal": {
                        "self_test": True,
                        "output": None,
                        "early_exit": False,
                        "stdout_text": "",
                    }
                }
                result = await run([], asserting)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                (self.directory / "bad.json").write_text("{bad")
                (self.directory / "utf8.json").write_bytes(b"\xff")
                # Error ordering stays source-owned; first missing monitor wins.
                failures = [
                    (["--unknown"], 1),
                    (["--monitor-report", "missing", "--object-packet", "bad.json"], 1),
                    (["--monitor-report", "bad.json"], 1),
                    (["--monitor-report", "utf8.json"], 1),
                    (
                        self.files(
                            packets(monitor_report={"category_counts": {"x": "bad"}})
                        ),
                        2,
                    ),
                    (["--output", str(self.directory)], 8),
                ]
                for argv, count in failures:
                    result = await run(argv)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(len(result["calls"]), count)
                for p, count in [
                    (packets(object_packet={"objects": None}), 2),
                    (
                        {
                            **self.native.fixture_packets(),
                            "repair_plans": [
                                {"style": "notational_collapse", "blockers": None}
                            ],
                        },
                        3,
                    ),
                    (
                        {
                            **self.native.fixture_packets(),
                            "workbench_plan": {
                                "items": [
                                    {
                                        "object_class": "commutator",
                                        "existing_hits": None,
                                    }
                                ]
                            },
                        },
                        4,
                    ),
                    (packets(generative_repair={"probe_prompts": None}), 5),
                    (packets(repair_loop={"target_refinement_policy": None}), 5),
                ]:
                    argv = self.files(p)
                    with self.assertRaises((TypeError, AttributeError)):
                        self.cli(self.old, self.absolute(argv))
                    result = await run(argv)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(len(result["calls"]), count)
                # Serialized and typed evidence must agree at every boundary.
                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        PREFIX + "seed", {"packets": packets(), "packets_json": "{}"}
                    )
                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        PREFIX + "help", {"options": {"early_exit": False}}
                    )
                budget = deepcopy(doc)
                budget["policy"]["limits"]["max_operation_calls"] = 7
                result = await run([], budget)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in result["calls"]
                    ),
                    7,
                )
                self.assertIn("budget", str(result).lower())
                timed = deepcopy(doc)
                timed["policy"]["limits"]["wall_time_seconds"] = 1
                w, a = compile(timed)

                async def pending():
                    await asyncio.Event().wait()

                with self.assertRaises(TimeoutError):
                    await execute(
                        w, a, {"extra_args": [], "context": context}, remote, pending
                    )
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure:
            raise failure


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(ExpansionTests)
    )
    sys.exit(
        0 if result.wasSuccessful() and result.testsRun and not result.skipped else 1
    )
