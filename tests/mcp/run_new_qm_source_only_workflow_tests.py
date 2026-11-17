#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native source, full MCP registration, Lunar PRISM compiler/runtime fixtures.

Only the external compiler is replaced. Actual native helpers, packet writers,
controller, completeness checks, report logic and tool bindings execute. There
are no provider calls in this runner. Original source is frozen as a test oracle.
"""

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
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import yaml
from new_qm_source_only_tools import SOURCE, source
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_physics_lean_new_qm_source_only_batch_workflow/workflow.yaml"
AUTHORED = "skills/control/workflow-contract-validator/references/new-qm-source-only.workflow.json"
FIXTURES = ROOT / "tests/mcp/fixtures"
PREFIX = "mathformer_new_qm_"
ACK = "--acknowledge-deprecated-batch-scaffold"


def assets(doc):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(doc))] + [
        asset(p, (ROOT / p).read_text())
        for p in dict.fromkeys(r["path"] for r in doc["provenance"]["sources"])
    ]


def fixture_root(root, doc, mode="pass"):
    root.mkdir()
    for row in doc["provenance"]["sources"]:
        path = row["path"]
        if path.endswith(".py"):
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / path, target)
    # The skill ledger discovers contracts, it does not execute listed skills.
    for md in (ROOT / "skills").glob("*/*/SKILL.md"):
        target = root / md.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(md, target)
    # Minimal native Lean library input for the real grounding inventory; no
    # theorem prover or imported Foundations are built in these tests.
    foundations = root / "MathformerPhysicsLib/Lean/Foundations"
    foundations.mkdir(parents=True)
    (foundations / "Fixture.lean").write_text(
        "import Mathlib\nnamespace Fixture\ndef anchor (x : Nat) := x\nend Fixture\n"
    )
    (foundations.parent / "Foundations.lean").write_text(
        "import MathformerPhysicsLib.Lean.Foundations.Fixture\n"
    )
    # Native paths historically use both spellings; mirror via a directory
    # symlink just as the repository exposes its canonical library surface.
    library = root / "libraries/MathformerPhysicsLib/Lean"
    library.parent.mkdir(parents=True, exist_ok=True)
    library.symlink_to(root / "MathformerPhysicsLib/Lean", target_is_directory=True)
    dataset = root / "data/benchmarks/formal_science/FormalPhysics.json"
    dataset.parent.mkdir(parents=True)
    dataset.write_text(
        json.dumps(
            [
                {
                    "field": "Quantum Mechanics",
                    "question": f"Derive state {i}. -/ operator relation",
                    "answer": f"Use source derivation {i}.",
                    "solution": "FORBIDDEN_DATASET_LEAN_SENTINEL",
                    "lean_solution": "FORBIDDEN_DATASET_LEAN_SENTINEL",
                }
                for i in range(57)
            ]
        )
    )
    (root / "compiler-fixture.json").write_text(json.dumps({"mode": mode}))
    return root


def context(root, allow=True):
    return dict(repository_root=str(root), allow_mutating=allow)


def files(root):
    paths = list((root / "artifacts").rglob("*")) + list(
        (root / "MathformerPhysicsLib/Lean").glob("formalphysics_*/*")
    )
    paths += [root / "native_process_calls.jsonl", root / "compiler_calls.jsonl"]
    return {str(p.relative_to(root)): p.read_text() for p in paths if p.is_file()}


def canonical(value, root):
    def normalized(v):
        if isinstance(v, dict):
            return {k: normalized(x) for k, x in v.items() if k != "duration_seconds"}
        if isinstance(v, (list, tuple)):
            return [normalized(x) for x in v]
        if isinstance(v, str):
            try:
                return normalized(json.loads(v))
            except (ValueError, TypeError):
                # Runtime and oracle use separate virtual environments. Normalize
                # only that interpreter identity and helper wall-clock durations.
                text = re.sub(
                    r"duration_seconds[^:]*:\s*[0-9.]+",
                    "duration_seconds: <DURATION>",
                    v,
                )
                for executable in (str(ROOT / ".venv/bin/python"), str(PYTHON)):
                    text = text.replace(executable, "<PYTHON>")
                return text.replace(str(root), "<ROOT>")
        return v

    return json.dumps(normalized(value), sort_keys=True)


def baseline(root, argv, original=True):
    native = source(root)
    if original:
        scope = {"__name__": "new_qm_original", "__file__": str(ROOT / SOURCE)}
        exec((FIXTURES / "new_qm_source_only_original.py.txt").read_text(), scope)
        for key, value in vars(native).items():
            if isinstance(value, Path):
                scope[key] = value
        main = scope["main"]
    else:
        main = native.main
    spec = importlib.util.spec_from_file_location(
        "new_qm_compiler_fixture", FIXTURES / "new_qm_startup/sitecustomize.py"
    )
    fixture = importlib.util.module_from_spec(spec)
    previous = subprocess.run
    spec.loader.exec_module(fixture)
    output = io.StringIO()
    try:
        with (
            patch.object(sys, "argv", ["qm", *argv]),
            redirect_stdout(output),
            redirect_stderr(io.StringIO()),
        ):
            try:
                result = main()
            except (
                SystemExit,
                RuntimeError,
                OSError,
                ValueError,
                IndexError,
                subprocess.TimeoutExpired,
            ) as error:
                result = (type(error).__name__, str(error))
    finally:
        subprocess.run = previous
    return result, output.getvalue(), files(root)


class NewQMTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = yaml.safe_load(Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text())
        cls.temp = tempfile.TemporaryDirectory(prefix="new-qm-runtime-")
        cls.base = Path(cls.temp.name)
        cls.env = {
            "PYTHONPATH": str(FIXTURES / "new_qm_startup"),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        cls.oldenv = {key: os.environ.get(key) for key in cls.env}
        os.environ.update(cls.env)

    @classmethod
    def tearDownClass(cls):
        for key, value in cls.oldenv.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        cls.temp.cleanup()

    def test_original_entrypoint_equivalence(self):
        for label, argv, mode in [
            ("ungated", [ACK, "--json"], "pass"),
            ("gated", [ACK, "--run-gates", "--json"], "pass"),
            ("human", [ACK], "pass"),
            ("compile_failure", [ACK, "--run-gates"], "compile_failure"),
            ("missing_ack", [], "pass"),
            ("invalid_argv", [ACK, "--bad-flag"], "pass"),
            ("timeout", [ACK, "--run-gates"], "timeout"),
        ]:
            outcomes = []
            for original in (True, False):
                root = fixture_root(
                    self.base / f"equivalence-{label}-{original}", self.doc, mode
                )
                result = baseline(root, argv, original)
                if label in ("ungated", "human"):
                    self.assertEqual(result[0], 0)
                elif label in ("gated", "compile_failure"):
                    self.assertEqual(result[0], 1)
                else:
                    self.assertIsInstance(result[0], tuple)
                outcomes.append(canonical(result, root))
            self.assertEqual(*outcomes, label)

    def test_inventory_and_control(self):
        self.assertEqual(self.doc, json.loads((ROOT / AUTHORED).read_text()))
        spec = importlib.util.spec_from_file_location(
            "new_qm_inventory",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(
            [row for row in module.inventory() if row["id"] == self.doc["id"]],
            [self.doc],
        )
        import mathformer as hub

        audit = hub.audit_control(hub.build_registry())
        self.assertNotIn(
            "scripts/new_qm_source_only_tools.py", audit["uncontrolled_entrypoints"]
        )
        self.assertNotIn(
            "tests/mcp/run_new_qm_source_only_workflow_tests.py",
            audit["uncontrolled_entrypoints"],
        )
        self.assertEqual(self.doc["lifecycle"], "active")
        for row in self.doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )

    def test_registered_lunar_runtime(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        manager = SessionManager()
        async with manager.open(
            "new-qm",
            StdioConfig(
                command=str(ROOT / ".venv/bin/python"),
                args=[str(FIXTURES / "new_qm_server.py"), str(self.base)],
                cwd=str(ROOT),
            ),
            self.env,
        ) as remote:
            try:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]
                self.assertEqual(
                    {PREFIX + name for name in self.doc["operations"]},
                    {t["name"] for t in tools if t["name"].startswith(PREFIX)},
                )

                def compile(doc):
                    received = assets(doc)
                    selected = workflow_documents([DESCRIPTOR], received)[0]
                    w = compile_workflow("mcp:new-qm", selected, tools)
                    self.assertTrue(w["runnable"], w["diagnostics"])
                    self.assertTrue(w["prism_source"])
                    self.assertTrue(w["runtime_source"])
                    return w, received

                workflow, received = compile(self.doc)
                self.assertEqual(set(workflow["bindings"]), set(self.doc["operations"]))
                self.assertFalse(
                    compile_workflow(
                        "mcp:new-qm", workflow_documents([DESCRIPTOR], received)[0], []
                    )["runnable"]
                )

                async def allow():
                    pass

                async def run(root, argv=None, doc=None, ctx=None):
                    w, a = compile(doc) if doc else (workflow, received)
                    return await execute(
                        w,
                        a,
                        {
                            "argv": [ACK, "--json"] if argv is None else argv,
                            "context": ctx or context(root),
                        },
                        remote,
                        allow,
                    )

                for mode, gated in [
                    ("pass", False),
                    ("pass", True),
                    ("compile_failure", True),
                    ("timeout", True),
                    ("launch_error", True),
                ]:
                    label = f"{mode}-{gated}"
                    print("  Lunar fixture: " + label, flush=True)
                    root = fixture_root(self.base / f"runtime-{label}", self.doc, mode)
                    argv = [ACK, "--json"] + (["--run-gates"] if gated else [])
                    result = await run(root, argv)
                    if mode in ("timeout", "launch_error"):
                        self.assertEqual(result["status"], "failed", str(result)[:2000])
                        self.assertEqual(
                            result["calls"][-1]["tool"], PREFIX + "compile"
                        )
                        self.assertEqual(len(result["calls"]), 4)
                        self.assertIsNone(result["outputs"])
                        self.assertFalse(
                            (
                                root
                                / "artifacts/physics_lean/new_qm_source_only/batch_report.json"
                            ).exists()
                        )
                        continue
                    self.assertEqual(result["status"], "accepted", str(result)[:3000])
                    out = result["outputs"]
                    self.assertEqual(out["summary"]["case_count"], 20)
                    self.assertEqual(out["exit_code"], int(gated))
                    self.assertEqual(out["summary"]["ok"], not gated)
                    self.assertEqual(
                        [c["source_index"] for c in out["summary"]["cases"]],
                        source().SELECTED_CASES,
                    )
                    expected_root = fixture_root(
                        self.base / f"baseline-{label}", self.doc, mode
                    )
                    code, stdout, snapshot = baseline(expected_root, argv)
                    self.assertEqual(code, out["exit_code"])
                    self.assertEqual(
                        canonical(json.loads(stdout), expected_root),
                        canonical(out["summary"], root),
                    )
                    self.assertEqual(
                        canonical(snapshot, expected_root), canonical(files(root), root)
                    )
                    self.assertEqual(
                        json.loads((root / out["report_path"]).read_text()),
                        out["summary"],
                    )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["runtime"]["provenance"])
                    self.assertTrue(result["replay_artifacts"])
                    calls = (
                        [PREFIX + "generate"]
                        + (
                            [
                                PREFIX + n
                                for n in (
                                    "initial_plan",
                                    "compile",
                                    "completeness",
                                    "repair_plans",
                                    "final_plan",
                                )
                            ]
                            if gated
                            else []
                        )
                        + [PREFIX + "append_case"]
                    )
                    self.assertEqual(
                        [c["tool"] for c in result["calls"]],
                        [PREFIX + "initialize"]
                        + calls * 20
                        + [PREFIX + "grounding_audit", PREFIX + "report"],
                    )
                    self.assertEqual(len(result["calls"]), 143 if gated else 43)
                    self.assertNotIn("FORBIDDEN_DATASET_LEAN_SENTINEL", json.dumps(out))
                    generated = [
                        v for p, v in files(root).items() if "formalphysics_" in p
                    ]
                    self.assertFalse(
                        any("FORBIDDEN_DATASET_LEAN_SENTINEL" in v for v in generated)
                    )
                    helpers = [
                        json.loads(x)
                        for x in (root / "native_process_calls.jsonl")
                        .read_text()
                        .splitlines()
                    ]
                    self.assertEqual(
                        sum(
                            Path(c[0]).name == "control_recursive_repair_loop.py"
                            for c in helpers
                        ),
                        20 if gated else 0,
                    )
                    for command in helpers:
                        if Path(command[0]).name == "control_recursive_repair_loop.py":
                            self.assertEqual(
                                command[command.index("--iteration") + 1], "1"
                            )
                            self.assertEqual(
                                command[command.index("--max-iterations") + 1], "8"
                            )
                            self.assertFalse(any("history" in arg for arg in command))
                    if gated:
                        cc = [
                            json.loads(x)
                            for x in (root / "compiler_calls.jsonl")
                            .read_text()
                            .splitlines()
                        ]
                        self.assertEqual(
                            len(cc), 40
                        )  # direct compile plus final-plan compile
                        self.assertTrue(all(c["timeout"] == 240 for c in cc))
                        self.assertFalse(
                            out["summary"]["cases"][0]["completeness"]["json"]["ok"]
                        )
                        self.assertEqual(
                            out["summary"]["cases"][0]["lean_compile"]["ok"],
                            mode != "compile_failure",
                        )
                    else:
                        self.assertFalse((root / "compiler_calls.jsonl").exists())
                        self.assertTrue(
                            all(
                                "lean_compile" not in c for c in out["summary"]["cases"]
                            )
                        )
                # Actual finite loop reaches done on append 20; shortened bounds fail
                # before audit/report rather than silently accepting partial work.
                bounded = deepcopy(self.doc)
                bounded["flow"]["steps"][1]["max_iterations"] = 1
                root = fixture_root(self.base / "bounded", self.doc)
                result = await run(root, doc=bounded)
                self.assertEqual(result["status"], "failed")
                self.assertEqual(result["failure_disposition"], "fail")
                self.assertEqual(len(result["calls"]), 3)
                self.assertFalse(
                    (
                        root
                        / "artifacts/physics_lean/new_qm_source_only/batch_report.json"
                    ).exists()
                )
                budget = deepcopy(self.doc)
                budget["policy"]["limits"]["max_operation_calls"] = 2
                root = fixture_root(self.base / "budget", self.doc)
                result = await run(root, doc=budget)
                self.assertEqual(result["status"], "failed")
                self.assertFalse(
                    result["calls"][-1].get("transport_call_performed", False)
                )
                self.assertIn("budget", result["calls"][-1]["error"])
                for label in (
                    "no_ack",
                    "argv",
                    "denied",
                    "outside",
                    "missing",
                    "malformed",
                    "short",
                    "not_qm",
                    "write_error",
                ):
                    root = fixture_root(self.base / label, self.doc)
                    argv = [ACK, "--json"]
                    ctx = context(root)
                    count = 1
                    if label == "no_ack":
                        argv = []
                    if label == "argv":
                        argv += ["--unknown"]
                    if label == "denied":
                        ctx = context(root, False)
                    if label == "outside":
                        ctx = context(self.base.parent)
                    dataset = root / "data/benchmarks/formal_science/FormalPhysics.json"
                    if label == "missing":
                        dataset.unlink()
                    if label == "malformed":
                        dataset.write_text("{")
                    if label == "short":
                        dataset.write_text("[]")
                        count = 2
                    if label == "not_qm":
                        data = json.loads(dataset.read_text())
                        data[9]["field"] = "Mechanics"
                        dataset.write_text(json.dumps(data))
                        count = 4
                    if label == "write_error":
                        p = root / "MathformerPhysicsLib/Lean/formalphysics_0004"
                        p.write_text("blocked")
                        count = 2
                    result = await run(root, argv, ctx=ctx)
                    self.assertEqual(result["status"], "failed", label)
                    self.assertEqual(len(result["calls"]), count, label)
                    self.assertIsNone(result["outputs"])
                    self.assertFalse((root / "compiler_calls.jsonl").exists())
                    self.assertFalse(
                        (
                            root
                            / "artifacts/physics_lean/new_qm_source_only/batch_report.json"
                        ).exists()
                    )
                for label, filename, last, count in (
                    ("initial_failure", "goal_plan_initial.json", "initial_plan", 3),
                    ("map_failure", "repair_expansion_map.json", "repair_plans", 6),
                    (
                        "controller_failure",
                        "recursive_control_plan.json",
                        "repair_plans",
                        6,
                    ),
                ):
                    root = fixture_root(self.base / label, self.doc)
                    directory = (
                        root
                        / "artifacts/physics_lean/new_qm_source_only/formalphysics_0004"
                    )
                    (directory / filename).mkdir(parents=True)
                    result = await run(root, [ACK, "--json", "--run-gates"])
                    self.assertEqual(result["status"], "failed", label)
                    self.assertEqual(result["calls"][-1]["tool"], PREFIX + last)
                    self.assertEqual(len(result["calls"]), count)
                    self.assertIsNone(result["outputs"])
                    self.assertFalse((directory.parent / "batch_report.json").exists())
                await self.direct_steps(remote, compile, allow)
            except Exception:
                import traceback

                traceback.print_exc()
                raise
        self.assertFalse(manager.active)

    async def direct_steps(self, remote, compile, allow):
        root = fixture_root(self.base / "direct", self.doc)
        ctx = context(root)

        async def call(name, **args):
            return await remote.call(PREFIX + name, args)

        packet = await call("initialize", argv=[ACK], context=ctx)
        state = packet["state"]
        histories = [deepcopy(state)]
        work = None
        for index in range(20):
            work = (await call("generate", state=state, context=ctx))["work"]
            self.assertEqual(
                set(work["result"]),
                {
                    "case_id",
                    "source_index",
                    "lean_path",
                    "source_record",
                    "required_terms",
                },
            )
            ledger = root / work["paths"]["packets"]["skill_ledger"]
            self.assertGreater(json.loads(ledger.read_text())["skill_count"], 0)
            packet = await call("append_case", state=state, work=work)
            self.assertEqual(packet["done"], index == 19)
            self.assertEqual(packet["state"]["cases"][:-1], state["cases"])
            state = packet["state"]
            histories.append(deepcopy(state))
        self.assertEqual([s["position"] for s in histories], list(range(21)))
        with self.assertRaises(MCPConnectionError):
            await call("generate", state=state, context=ctx)
        with self.assertRaises(MCPConnectionError):
            await call("append_case", state=state, work=work)
        altered = deepcopy(work)
        altered["paths"]["lean"] = "../escape.lean"
        with self.assertRaises(MCPConnectionError):
            await call("compile", work=altered, context=ctx)
        # Native check=True failures abort the owning tool, with no controller
        # launch after a failed cartographer. Fail via actual missing/invalid
        # files, never by replacing planner/cartographer/controller functions.
        first = (await call("generate", state=histories[0], context=ctx))["work"]
        lean = root / first["paths"]["lean"]
        original = lean.read_text()
        lean.unlink()
        with self.assertRaises(MCPConnectionError):
            await call("initial_plan", work=first, context=ctx)
        # The final plan uses check=False and records its nonzero missing-file
        # result. Its nested compile fixture fails on missing input in child,
        # and Python propagates as a nonzero child exit, not a replaced helper.
        final = (await call("final_plan", work=first, context=ctx))["work"]
        self.assertFalse(final["result"]["goal_plan_after_gates"]["ok"])
        lean.write_text(original)
        monitor = root / first["paths"]["packets"]["monitor"]
        original_monitor = monitor.read_text()
        monitor.write_text("{")
        before = (root / "native_process_calls.jsonl").read_text().splitlines()
        with self.assertRaises(MCPConnectionError):
            await call("repair_plans", work=first, context=ctx)
        after = (root / "native_process_calls.jsonl").read_text().splitlines()
        self.assertEqual(len(after) - len(before), 1)
        self.assertIn("map_repair_expansion.py", after[-1])
        monitor.write_text(original_monitor)
        # Controller failure after a real successful cartographer: native
        # output cannot replace a directory with a JSON file.
        control = (
            root
            / "artifacts/physics_lean/new_qm_source_only/formalphysics_0004/recursive_control_plan.json"
        )
        control.mkdir()
        with self.assertRaises(MCPConnectionError):
            await call("repair_plans", work=first, context=ctx)
        calls = (root / "native_process_calls.jsonl").read_text().splitlines()
        self.assertIn("control_recursive_repair_loop.py", calls[-1])
        self.assertTrue(control.with_name("repair_expansion_map.json").is_file())
        # Audit nonzero is recorded and ignored by native success, without
        # replacing the audit implementation: its requested output is a dir.
        audit_path = (
            root
            / "artifacts/physics_lean/new_qm_source_only/mathlib_grounding_audit.json"
        )
        audit_path.mkdir()
        audit = (await call("grounding_audit", state=state, context=ctx))["audit"]
        self.assertFalse(audit["ok"])
        result = await call("report", state=state, audit=audit, context=ctx)
        self.assertTrue(result["summary"]["ok"])
        self.assertEqual(result["exit_code"], 0)
        # Feed typed result fixtures to the real reporting tail through Lunar
        # to cover truth identity and the exact native all(...) predicate. The
        # full gated workflow above supplies actual failing checker outcomes.
        doc = deepcopy(self.doc)
        doc["inputs"].update(
            state={"type": "BatchState"}, audit={"type": "CommandResult"}
        )
        doc["flow"]["steps"] = [doc["flow"]["steps"][-1]]
        doc["flow"]["steps"][0]["arguments"].update(
            state={"ref": "inputs.state"}, audit={"ref": "inputs.audit"}
        )
        w, a = compile(doc)
        for label, compile_ok, check_ok, payload, expected in [
            ("pass", True, True, {"ok": True}, True),
            ("compile", False, True, {"ok": True}, False),
            ("checker", True, False, {"ok": True}, False),
            ("false", True, True, {"ok": False}, False),
            ("truth_identity", True, True, {"ok": 1}, False),
            ("null", True, True, None, False),
        ]:
            s = deepcopy(state)
            s["run_gates"] = True
            for case in s["cases"]:
                case.update(
                    lean_compile={"ok": True},
                    completeness={"ok": True, "json": {"ok": True}},
                    goal_plan_after_gates={"ok": False},
                )
            s["cases"][0].update(
                lean_compile={"ok": compile_ok},
                completeness={"ok": check_ok, "json": payload},
            )
            result = await execute(
                w,
                a,
                {"argv": [], "context": ctx, "state": s, "audit": audit},
                remote,
                allow,
            )
            self.assertEqual(result["status"], "accepted", str(result)[:2000])
            self.assertEqual(result["outputs"]["summary"]["ok"], expected, label)
            self.assertEqual(result["outputs"]["exit_code"], int(not expected))
            self.assertFalse(result["outputs"]["summary"]["mathlib_grounding_audit_ok"])
        # Invalid report destination propagates I/O failure through real tool.
        target = root / "artifacts/physics_lean/new_qm_source_only/batch_report.json"
        target.unlink()
        target.mkdir()
        with self.assertRaises(MCPConnectionError):
            await call("report", state=state, audit=audit, context=ctx)


if __name__ == "__main__":
    unittest.main(verbosity=2)
