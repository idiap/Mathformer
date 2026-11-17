#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402 - direct test entrypoint configures the Lunar import path first.
"""Actual source steps and registered tools through Lunar/PRISM, with fake Lake only."""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
PYTHON = LUNAR / ".venv/bin/python"
if PYTHON.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(PYTHON), [str(PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.path[:0] = [str(LUNAR / "app/backend"), str(ROOT / "scripts"), str(ROOT)]
import asyncio
from contextlib import redirect_stdout, contextmanager
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
import re
import shutil
import socket
import subprocess
import tempfile
import unittest
import yaml
from recursive_goal_tools import source, SOURCE, register_recursive_goal_tools
from mcp.server.fastmcp import FastMCP
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

FIXTURES = ROOT / "tests/mcp/fixtures"
DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_physics_lean_goal_sample_recursive_0009_workflow/workflow.yaml"
PREFIX = "mathformer_recursive_goal_"
LEAN_FILE = (
    "libraries/MathformerPhysicsLib/Lean/formalphysics_0009/MathformerPhysics.lean"
)


def assets(doc):
    def asset(path, content):
        return dict(
            path=path,
            content=content,
            encoding="text",
            sha256=hashlib.sha256(content.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(doc))] + [
        asset(p, (ROOT / p).read_text())
        for p in dict.fromkeys(row["path"] for row in doc["provenance"]["sources"])
    ]


def context(root):
    return {"repository_root": str(root), "allow_mutating": True}


def argv():
    return [
        "--source-record",
        "artifacts/physics_lean/new_qm_source_only/formalphysics_0009/source_record.json",
        "--json",
        "--lean-file",
        LEAN_FILE,
    ]


def fixture_root(root, mode="silent"):
    root.mkdir()
    # All helper files are the actual checked-out implementations, copied so
    # their repository-relative outputs cannot escape this temporary mount.
    ignore = shutil.ignore_patterns("__pycache__", ".DS_Store", "normalized-workflows")
    for folder in (
        "skills",
        "scripts",
        "backends/sympy",
        "tests/physics_lean",
        "libraries/MathformerPhysicsLib",
    ):
        shutil.copytree(ROOT / folder, root / folder, ignore=ignore, symlinks=True)
    # Legacy skill paths are compatibility aliases used by the original backup.
    for theme in (root / "skills").iterdir():
        if theme.is_dir():
            for skill in theme.iterdir():
                if skill.is_dir() and (skill / "SKILL.md").exists():
                    link = root / "skills" / skill.name
                    if not link.exists():
                        link.symlink_to(skill.relative_to(root / "skills"))
    (root / ".venv").symlink_to(ROOT / ".venv", target_is_directory=True)
    record = (
        root
        / "artifacts/physics_lean/new_qm_source_only/formalphysics_0009/source_record.json"
    )
    record.parent.mkdir(parents=True)
    record.write_text(
        json.dumps(
            {
                "case_id": "formalphysics_0009",
                "question": "Show that for a real scalar x, x = x.",
                "answer": "By reflexivity, x = x.",
                "formal_answer": "WITHHELD SENTINEL",
            }
        )
    )
    (root / "compiler-fixture.json").write_text(json.dumps({"mode": mode}))
    return root


@contextmanager
def compiler_fixture():
    """Enable only the external boundary replacements and restore global APIs."""
    spec = importlib.util.spec_from_file_location(
        "goal_boundary", FIXTURES / "recursive_goal_startup/sitecustomize.py"
    )
    module = importlib.util.module_from_spec(spec)
    previous = subprocess.run, socket.socket.connect, socket.create_connection
    try:
        spec.loader.exec_module(module)
        yield
    finally:
        subprocess.run, socket.socket.connect, socket.create_connection = previous


def baseline(root, original):
    native = source(root)
    if original:
        scope = {"__name__": "recursive_original", "__file__": str(root / SOURCE)}
        exec((FIXTURES / "recursive_goal_original.py.txt").read_text(), scope)
        for key in ("REPO_ROOT", "SKILLS", "LEAN_ROOT", "DEFAULT_ARTIFACT_ROOT"):
            scope[key] = getattr(native, key)
        main = scope["main"]
    else:
        main = native.main
    output = io.StringIO()
    with compiler_fixture(), redirect_stdout(output):
        code = main(argv())
    return code, json.loads(output.getvalue())


def stable(value, root):
    """Ignore source-owned timing fields only; compare all substantive state."""
    if isinstance(value, dict):
        return {
            k: stable(v, root)
            for k, v in value.items()
            if k not in {"duration_seconds", "created_at", "generated_at", "timestamp"}
        }
    if isinstance(value, list):
        return [stable(v, root) for v in value]
    if isinstance(value, str):
        text = value.replace(str(root), "<ROOT>")
        return re.sub(
            r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:\+00:00|Z)",
            "<TIMESTAMP>",
            text,
        )
    return value


class RecursiveGoalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = yaml.safe_load(Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text())
        cls.temp = tempfile.TemporaryDirectory(prefix="recursive-goal-")
        cls.base = Path(cls.temp.name)
        cls.env = {
            "PYTHONPATH": str(FIXTURES / "recursive_goal_startup"),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        cls.oldenv = {k: os.environ.get(k) for k in cls.env}
        os.environ.update(cls.env)

    @classmethod
    def tearDownClass(cls):
        for k, v in cls.oldenv.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        cls.temp.cleanup()

    def test_original_entrypoint_equivalence(self):
        results = []
        for original in (True, False):
            root = fixture_root(self.base / f"baseline-{original}")
            code, payload = baseline(root, original)
            self.assertEqual(code, int(not payload["ok"]))
            self.assertNotIn(
                "WITHHELD SENTINEL",
                (
                    root
                    / "artifacts/physics_lean/recursive_goal_runs/formalphysics_0009/source_text.txt"
                ).read_text(),
            )
            results.append(stable(payload, root))
        self.assertEqual(*results)

    def test_native_guards_and_acceptance(self):
        native = source()
        for value in ({"case_id": "invalid"}, {"case_id": ""}):
            with self.assertRaises(SystemExit):
                native.case_id_from_record(value)
        with self.assertRaises(SystemExit):
            native.source_text_from_record({"question": " ", "answer": "x"})
        with self.assertRaisesRegex(ValueError, "exhausted"):
            native.visit_physics_stage(
                {
                    "pending": [],
                    "source_text": "x",
                    "outputs": {},
                    "stage_reports": {},
                    "python": sys.executable,
                }
            )
        with self.assertRaisesRegex(ValueError, "exhausted"):
            native.visit_repair_plan(
                {
                    "pending": [],
                    "outputs": {},
                    "stage_reports": {},
                    "python": sys.executable,
                    "repair_plan_paths": [],
                }
            )
        reports = {name: {"ok": True} for name in native.REQUIRED_COMPLETENESS_STAGES}
        reports["recursive_control"]["payload_decision"] = "complete"
        self.assertTrue(native.stage_summary(reports)["all_required_stages_ok"])
        self.assertTrue(native.final_acceptance(reports, lean_compile_ok=True)["ok"])
        reports["recursive_control"]["payload_decision"] = "recurse"
        self.assertIn(
            "recursive_control:not_complete:recurse",
            native.final_acceptance(reports, lean_compile_ok=True)["blockers"],
        )
        self.assertIn(
            "lean_compile_failed",
            native.final_acceptance(reports, lean_compile_ok=False)["blockers"],
        )

    def test_native_stage_failure_and_timeout(self):
        root = self.base / "stage-errors"
        root.mkdir()
        native = source(root)
        self.assertEqual(
            native.script("absent-skill", "scripts", "absent.py"),
            "skills/absent-skill/scripts/absent.py",
        )
        (root / "compiler-fixture.json").write_text(json.dumps({"mode": "timeout"}))
        reports = {}
        with compiler_fixture():
            # No source step selects a provider in this one-pass planner.
            # Fail closed if a future change attempts model/provider access.
            with self.assertRaisesRegex(AssertionError, "network access forbidden"):
                socket.create_connection(("provider.invalid", 443))
            with self.assertRaisesRegex(AssertionError, "unexpected external process"):
                subprocess.run(["codex", "exec", "fixture must never launch"])
            report = native.run_stage(
                name="compiler_probe",
                command=["lake", "env", "lean", "probe.lean"],
                output=root / "missing.json",
                reports=reports,
            )
            self.assertTrue(report["timed_out"])
            self.assertEqual(report["returncode"], 124)
            self.assertFalse(report["ok"])
            self.assertEqual(report["stdout_tail"], "compiler timeout")
            # Run the actual native helper CLI with invalid arguments; no
            # stage implementation or report is supplied by the fixture.
            helper = (
                ROOT
                / "skills/physics-lean/physics-lean-execution-interpreter/scripts/interpret_physics_lean_execution.py"
            )
            report = native.run_stage(
                name="invalid_interpreter",
                command=[sys.executable, str(helper), "--unknown-argument"],
                output=root / "missing.json",
                reports=reports,
            )
            self.assertFalse(report["ok"])
            self.assertNotEqual(report["returncode"], 0)
            self.assertFalse(report["timed_out"])
            # Exit zero without producing the promised artifact remains a
            # failed stage, using the real helper's help-only early exit.
            report = native.run_stage(
                name="missing_output",
                command=[sys.executable, str(helper), "--help"],
                output=root / "missing.json",
                reports=reports,
            )
            self.assertEqual(report["returncode"], 0)
            self.assertFalse(report["ok"])
            self.assertEqual(report["path"], "")
        # Silent normalization does not erase the recorded interpreter failure.
        output = root / "lean_execution.json"
        report.update(ok=False, returncode=2)
        state = {
            "outputs": {"lean_execution": str(output)},
            "stage_reports": {"lean_execution": report},
        }
        native.normalize_silent(state)
        self.assertFalse(report["ok"])
        self.assertEqual(report["returncode"], 2)
        self.assertEqual(report["payload_status"], "no_known_diagnostics")
        self.assertEqual(json.loads(output.read_text())["findings"], [])

    def test_authored_generator(self):
        path = (
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py"
        )
        spec = importlib.util.spec_from_file_location("goal_normalizer", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if self.doc["id"] == "route_formalize_physics_lean_goal_sample_0009_workflow":
            generated = [module.recursive_goal_route_descriptor()]
        else:
            generated = [d for d in module.inventory() if d["id"] == self.doc["id"]]
        self.assertEqual(generated, [self.doc])

    def test_controller_branches_and_bound(self):
        path = (
            ROOT
            / "skills/physics-lean/physics-lean-recursive-repair-loop-controller/scripts/control_recursive_repair_loop.py"
        )
        spec = importlib.util.spec_from_file_location("controller", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        expansion = {
            "status": "needs_expansion",
            "exhaustive": True,
            "iteration_signature": "s",
            "outstanding_nodes": [{"id": "n"}],
            "next_frontier": [{"node_id": "n", "action": "repair"}],
        }

        def run(e=expansion, previous=None, iteration=1, maximum=8):
            return mod.build_control_plan(
                expansion_map=e,
                previous_expansion_maps=previous or [],
                iteration=iteration,
                max_iterations=maximum,
            )

        self.assertEqual(run()["decision"], "recurse")
        for e, previous, iteration, maximum, blocker in [
            (expansion, [], 8, 8, "max_iterations_reached:8"),
            (expansion, [], 9, 8, "max_iterations_reached:8"),
            (
                expansion,
                [{"iteration_signature": "s"}],
                2,
                8,
                "repeated_iteration_signature:s",
            ),
            (
                {**expansion, "exhaustive": False},
                [],
                1,
                8,
                "expansion_map_not_exhaustive",
            ),
            ({**expansion, "status": "blocked"}, [], 1, 8, "expansion_map_blocked"),
        ]:
            plan = run(e, previous, iteration, maximum)
            self.assertEqual(plan["decision"], "blocked")
            self.assertIn(blocker, plan["blockers"])
        for status in ("complete", "not_required"):
            plan = run(
                {
                    **expansion,
                    "status": status,
                    "outstanding_nodes": [],
                    "exhaustive": False,
                },
                iteration=8,
            )
            self.assertEqual(plan["decision"], "complete")
            self.assertEqual(plan["next_actions"], [])
        self.assertEqual(
            run({**expansion, "outstanding_nodes": []})["decision"], "complete"
        )

    def test_registration_and_mount_denial(self):
        async def run():
            server = FastMCP("guard")

            def deny(path):
                raise ValueError("service write denied")

            register_recursive_goal_tools(server, deny)
            root = fixture_root(self.base / "denied")
            for ctx in (context(root), {**context(root), "allow_mutating": False}):
                with self.assertRaisesRegex(Exception, "write denied|allow_mutating"):
                    await server.call_tool(
                        PREFIX + "prepare_source", {"argv": argv(), "context": ctx}
                    )
            self.assertFalse(
                (root / "artifacts/physics_lean/recursive_goal_runs").exists()
            )

        asyncio.run(run())
        import mathformer as hub

        audit = hub.audit_control(hub.build_registry())
        self.assertNotIn(
            "scripts/recursive_goal_tools.py", audit["uncontrolled_entrypoints"]
        )
        self.assertNotIn(
            "tests/mcp/run_recursive_goal_workflow_tests.py",
            audit["uncontrolled_entrypoints"],
        )
        self.assertNotIn(
            "tests/mcp/run_recursive_goal_loop_tests.py",
            audit["uncontrolled_entrypoints"],
        )
        self.assertNotIn(
            "tests/mcp/run_recursive_goal_route_tests.py",
            audit["uncontrolled_entrypoints"],
        )

    def test_lunar_runtime(self):
        for row in self.doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        asyncio.run(self.scenarios())

    async def scenarios(self):
        manager = SessionManager()
        async with manager.open(
            "goal",
            StdioConfig(
                command=str(ROOT / ".venv/bin/python"),
                args=[str(FIXTURES / "recursive_goal_server.py"), str(self.base)],
                cwd=str(ROOT),
            ),
            self.env,
        ) as remote:
            tools = [
                t.model_dump(by_alias=True, exclude_none=True)
                for t in await remote.tools()
            ]
            self.assertLessEqual(
                {PREFIX + n for n in self.doc["operations"]},
                {t["name"] for t in tools if t["name"].startswith(PREFIX)},
            )

            def compile(doc, inventory=None):
                received = assets(doc)
                w = compile_workflow(
                    "mcp:goal",
                    workflow_documents([DESCRIPTOR], received)[0],
                    tools if inventory is None else inventory,
                )
                self.assertTrue(w["runnable"], w["diagnostics"])
                self.assertTrue(w["prism_source"])
                self.assertTrue(w["runtime_source"])
                return w, received

            workflow, received = compile(self.doc)
            self.assertFalse(
                compile_workflow(
                    "mcp:goal", workflow_documents([DESCRIPTOR], received)[0], []
                )["runnable"]
            )

            async def allow():
                pass

            # Observe real transport inputs/outputs without replacing a step.
            # This also verifies the loop-carried state, beyond call counts.
            observations = []

            class ObservedRemote:
                tools = remote.tools

                async def call(self, name, arguments):
                    response = await remote.call(name, arguments)
                    observations.append((name, deepcopy(arguments), deepcopy(response)))
                    return response

            async def run(root, doc=None, extra=()):
                w, a = compile(doc) if doc else (workflow, received)
                observations.clear()
                return await execute(
                    w,
                    a,
                    {"argv": argv() + list(extra), "context": context(root)},
                    ObservedRemote(),
                    allow,
                )

            for mode in ("silent", "warning", "failure", "launch_error"):
                print("Full native goal runtime: " + mode, flush=True)
                root = fixture_root(self.base / f"runtime-{mode}", mode)
                result = await run(root)
                if mode == "launch_error":
                    self.assertEqual(result["status"], "failed", str(result)[:4000])
                    self.assertFalse(
                        (
                            root
                            / "artifacts/physics_lean/recursive_goal_runs/formalphysics_0009/recursive_goal_case_run.json"
                        ).exists()
                    )
                    continue
                self.assertEqual(result["status"], "accepted", str(result)[:4000])
                out = result["outputs"]["result"]
                payload = out["payload"]
                reports = payload["stage_reports"]
                self.assertEqual(out["returncode"], int(not payload["ok"]))
                if mode == "silent":
                    self.assertEqual(out["returncode"], 0)
                    self.assertEqual(
                        payload["final_acceptance"], {"ok": True, "blockers": []}
                    )
                original_lean = ROOT / LEAN_FILE
                self.assertEqual(
                    (root / LEAN_FILE).read_bytes(), original_lean.read_bytes()
                )
                physics = [
                    o for o in observations if o[0] == PREFIX + "visit_physics_stage"
                ]
                physics_names = [entry[0] for entry in source().PHYSICS_STAGES]
                for i, (_, inputs, outputs) in enumerate(physics):
                    self.assertEqual(inputs["state"]["pending"], physics_names[i:])
                    self.assertEqual(
                        outputs["state"]["pending"], physics_names[i + 1 :]
                    )
                    self.assertEqual(outputs["done"], i == 6)
                    self.assertIn(physics_names[i], outputs["state"]["stage_reports"])
                repairs = [
                    o for o in observations if o[0] == PREFIX + "visit_repair_plan"
                ]
                repair_names = [entry[0] for entry in source().REPAIR_STAGES]
                for i, (_, inputs, outputs) in enumerate(repairs):
                    self.assertEqual(inputs["state"]["pending"], repair_names[i:])
                    state = outputs["state"]
                    self.assertEqual(state["pending"], repair_names[i + 1 :])
                    self.assertEqual(outputs["done"], i == 3)
                    self.assertEqual(
                        state["repair_plan_paths"],
                        [state["outputs"][n] for n in repair_names[: i + 1]],
                    )
                    self.assertEqual(state["iteration"], 1)
                    self.assertEqual(state["max_iterations"], 8)
                if mode != "silent" and "retain_state" in self.doc["operations"]:
                    _, inputs, outputs = next(
                        o for o in observations if o[0] == PREFIX + "retain_state"
                    )
                    self.assertEqual(inputs["state"], outputs["state"])
                if mode == "failure":
                    self.assertEqual(out["returncode"], 1)
                    self.assertIn(
                        "lean_compile_failed", payload["final_acceptance"]["blockers"]
                    )
                self.assertEqual(
                    json.loads((root / out["report_path"]).read_text()), payload
                )
                rebuilt = json.loads((root / out["source_record_path"]).read_text())
                self.assertNotIn(
                    "derivation_completeness", rebuilt["workflow_stage_reports"]
                )
                self.assertNotIn("case_thoroughness", rebuilt["workflow_stage_reports"])
                self.assertEqual(rebuilt["formal_answer_policy"]["status"], "not_used")
                self.assertEqual(len(reports), 38)
                self.assertEqual(
                    reports["lean_compile"]["returncode"], int(mode == "failure")
                )
                self.assertEqual(reports["mathlib_grounding"]["command"][-1], "--json")
                self.assertIn("derivation_completeness", reports)
                self.assertIn("case_thoroughness", reports)
                names = [c["tool"] for c in result["calls"]]
                expected = (
                    [PREFIX + "prepare_source"]
                    + [PREFIX + "visit_physics_stage"] * 7
                    + [PREFIX + "plan_critique_ground"]
                    + [PREFIX + "visit_repair_plan"] * 4
                    + [PREFIX + "finish_plans", PREFIX + "compile_interpret"]
                )
                if mode == "silent":
                    expected.append(PREFIX + "normalize_silent")
                elif "retain_state" in self.doc["operations"]:
                    expected.append(PREFIX + "retain_state")
                expected.append(PREFIX + "validate_report")
                self.assertEqual(names, expected)
                self.assertEqual(
                    len(names),
                    (
                        17
                        if mode == "silent" or "retain_state" in self.doc["operations"]
                        else 16
                    ),
                )
                self.assertTrue(result["runtime"]["effect_records"])
                self.assertTrue(result["runtime"]["provenance"])
                self.assertTrue(result["replay_artifacts"])
                calls = [
                    json.loads(line)
                    for line in (root / "native_process_calls.jsonl")
                    .read_text()
                    .splitlines()
                ]
                self.assertEqual(
                    next(
                        c["timeout"]
                        for c in calls
                        if "audit_mathlib_grounding.py" in c["argv"][0]
                    ),
                    360,
                )
                self.assertTrue(all(c["timeout"] == 240 for c in calls[:3]))
                self.assertEqual(
                    len((root / "compiler_calls.jsonl").read_text().splitlines()), 1
                )
                ctrl = json.loads(
                    (
                        root
                        / "artifacts/physics_lean/recursive_goal_runs/formalphysics_0009/recursive_control.json"
                    ).read_text()
                )
                self.assertEqual(ctrl["prior_iteration_signatures"], [])
                self.assertEqual(ctrl["iteration"], 1)
                self.assertEqual(ctrl["max_iterations"], 8)
                consistency = reports["consistency_report"]["command"]
                self.assertEqual("--compile-ok" in consistency, mode != "failure")
                self.assertEqual("--realness-ok" in consistency, mode == "silent")
                self.assertIn("--anchor-ok", consistency)
                if mode == "silent":
                    diagnostics = json.loads(
                        (root / reports["lean_execution"]["path"]).read_text()
                    )
                    self.assertEqual(
                        diagnostics,
                        {
                            "status": "no_known_diagnostics",
                            "category_counts": {},
                            "findings": [],
                            "warning_findings": [],
                            "repair_targets": [],
                        },
                    )
                else:
                    self.assertNotEqual(
                        reports["lean_execution"]["payload_status"],
                        "no_known_diagnostics",
                    )
                if mode == "silent":
                    baseline_root = fixture_root(self.base / "runtime-baseline")
                    code, expected_payload = baseline(baseline_root, True)
                    self.assertEqual(
                        stable(payload, root), stable(expected_payload, baseline_root)
                    )
                    # MCP admission rejects paths that zip-based validation
                    # used to ignore after the four native repair entries.
                    complete = next(
                        outputs["state"]
                        for name, _, outputs in observations
                        if name == PREFIX + "finish_plans"
                    )
                    tampered = deepcopy(complete)
                    tampered["repair_plan_paths"].append(
                        str(self.base / "outside.json")
                    )
                    calls_before = (root / "native_process_calls.jsonl").read_bytes()
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            PREFIX + "finish_plans",
                            {"state": tampered, "context": context(root)},
                        )
                    self.assertEqual(
                        (root / "native_process_calls.jsonl").read_bytes(), calls_before
                    )
            # Real PRISM loop exhaustion must stop before planning, even though
            # individual stage calls succeeded or recorded their own failures.
            short = deepcopy(self.doc)
            short["flow"]["steps"][1]["max_iterations"] = 6
            root = fixture_root(self.base / "exhausted")
            result = await run(root, short)
            self.assertEqual(result["status"], "failed", str(result)[:4000])
            self.assertEqual(len(result["calls"]), 7)
            self.assertFalse(
                (
                    root
                    / "artifacts/physics_lean/recursive_goal_runs/formalphysics_0009/lean_workflow_plan.json"
                ).exists()
            )
            short = deepcopy(self.doc)
            short["flow"]["steps"][3]["max_iterations"] = 3
            root = fixture_root(self.base / "repair-exhausted")
            result = await run(root, short)
            self.assertEqual(result["status"], "failed", str(result)[:4000])
            self.assertEqual(len(result["calls"]), 12)
            self.assertFalse(
                (
                    root
                    / "artifacts/physics_lean/recursive_goal_runs/formalphysics_0009/pathology_repair.json"
                ).exists()
            )
            self.assertFalse((root / "compiler_calls.jsonl").exists())
            # Missing user input makes real critics/helpers fail. Their failures
            # are recorded, traversal continues, and the final report returns 1.
            root = fixture_root(self.base / "missing-lean")
            result = await run(root, extra=["--lean-file", "missing.lean"])
            self.assertEqual(result["status"], "accepted", str(result)[:4000])
            output = result["outputs"]["result"]
            self.assertEqual(output["returncode"], 1)
            self.assertFalse(
                output["payload"]["stage_summary"]["all_required_stages_ok"]
            )
            self.assertIn("case_thoroughness", output["payload"]["stage_reports"])
            self.assertEqual(len(result["calls"]), 17)
            # Validation aborts main before any compiler/stage launch, and MCP
            # returns a tool failure without killing the server session.
            root = fixture_root(self.base / "invalid-source")
            record = root / argv()[1]
            record.write_text(
                json.dumps({"case_id": "invalid", "question": "q", "answer": "a"})
            )
            result = await run(root)
            self.assertEqual(result["status"], "failed", str(result)[:4000])
            self.assertEqual(len(result["calls"]), 1)
            self.assertFalse((root / "native_process_calls.jsonl").exists())
            # Real source configuration is passed unchanged; controller cap does
            # not bound or rerun the finite physics/repair traversals.
            root = fixture_root(self.base / "cap")
            result = await run(
                root, extra=["--iteration", "8", "--max-iterations", "8"]
            )
            self.assertEqual(result["status"], "accepted", str(result)[:4000])
            control = result["outputs"]["result"]["payload"]["stage_reports"][
                "recursive_control"
            ]
            payload = json.loads((root / control["path"]).read_text())
            self.assertEqual(payload["iteration"], 8)
            self.assertEqual(payload["max_iterations"], 8)
            self.assertEqual(len(result["calls"]), 17)
        self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
