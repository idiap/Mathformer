#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic native suite, original controller parity and Lunar/PRISM execution."""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
FIXTURES = ROOT / "tests/mcp/fixtures"
SITES = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT),
    str(FIXTURES),
]
sys.path.extend(SITES)

import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib.util
import json
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import yaml

import mathformer as hub
from lean_fixture_route_tools import (
    ACTION,
    ROUTE,
    selected_match,
    checked_registry,
    check_state,
)
from lean_fixture_boundary import install_external
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute, ExecutionRejected

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_validate_lean_fixture_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
AUTHORED = "skills/control/workflow-contract-validator/references/lean-fixture-route.workflow.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
MATCH = {
    "route": {"route_id": ROUTE, "action_ids": [ACTION]},
    "score": 19,
    "matched_terms": ["wiki level"],
}
ITEM = hub.build_registry()[ACTION]
REGISTRY = {ACTION: hub.action_to_dict(ITEM)}
ORDER = ["initialize", "select", "run", "advance", "finish"]
SCRIPT = "tests/wiki_level/run_suite.py"
SKILLS = [
    "control/reasoning-log-schema-guardian",
    "autoformalization/proof-expansion-difficulty-estimator",
    "mathlib/informal-proof-mathlib-concepts",
    "mathlib/mathlib-concept-ontology-manager",
    "mathlib/mathlib-hierarchy-navigator",
    "mathlib/mathlib-compatibility-auditor",
]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def original():
    scope = dict(vars(hub))
    exec((FIXTURES / "lean_fixture_route_original.py.txt").read_text(), scope)
    return SimpleNamespace(**scope)


def populate(root, count=2, bad_static=False, missing_theorem=False):
    root.mkdir(parents=True, exist_ok=True)
    target = root / SCRIPT
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / SCRIPT, target)
    for skill in SKILLS:
        source = ROOT / "skills" / skill
        dest = root / "skills" / skill
        shutil.copytree(
            source,
            dest,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
    assert target.read_bytes() == (ROOT / SCRIPT).read_bytes()
    fixture_mathlib = root / ".lake/packages/mathlib/Mathlib/Data/Fixture.lean"
    fixture_mathlib.parent.mkdir(parents=True, exist_ok=True)
    fixture_mathlib.write_text("theorem fixture_true : True := by trivial\n")
    latex = root / "tests/latex/wiki_level"
    latex.mkdir(parents=True, exist_ok=True)
    gold = "import Mathlib.Data.Fixture\n" + "\n".join(
        f"theorem case_{i} : True := by trivial"
        for i in range(count)
        if not (missing_theorem and i == 0)
    )
    (root / "gold.lean").write_text(gold + "\n")
    cases = []
    for i in range(count):
        row = dict(
            id=f"fixture.{i}",
            latex_file=f"tests/latex/wiki_level/{i}.tex",
            lean_theorem=f"case_{i}",
            concepts=["fixture"],
            difficulty="low",
            expected_mathlib_declarations=["fixture_true", "fixture_true"],
        )
        text = (
            "% mathformer-case-id: fixture."
            + str(i)
            + "\n% expected-lean-name: case_"
            + str(i)
            + "\n% controlled-suite: wiki_level_latex_to_lean\n"
            + "\\begin{theorem}The fixture proposition is true.\\end{theorem}\n"
            + "\\begin{proof}It follows by the fixture theorem.\\end{proof}\n\\section*{Lean Target}\n"
        )
        if bad_static and i == 0:
            text = text.replace("\\begin{proof}", "")
        (latex / f"{i}.tex").write_text(text)
        cases.append(row)
    (latex / "manifest.json").write_text(
        json.dumps(
            dict(
                suite="deterministic-fixture",
                gold_lean_file="gold.lean",
                gold_expected_imports=["Mathlib.Data.Fixture"],
                cases=cases,
            )
        )
    )
    (root.parent / "compiler-mode").write_text("pass")


def reset(root):
    shutil.rmtree(root / "artifacts", ignore_errors=True)
    (root / "undeclared.txt").unlink(missing_ok=True)
    for name in ["native.jsonl", "compiler.jsonl"]:
        (root.parent / name).unlink(missing_ok=True)


def clean_env():
    return {
        "PATH": os.environ.get("PATH", os.defpath),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": os.pathsep.join(
            [str(FIXTURES / "lean_fixture_startup"), str(FIXTURES)]
        ),
    }


def stable(value):
    if isinstance(value, list):
        return [stable(row) for row in value]
    if isinstance(value, dict):
        return {
            key: stable(item)
            for key, item in value.items()
            if key
            not in {
                "duration_ms",
                "duration_seconds",
                "generated_at_utc",
                "timestamp",
                "run_id",
            }
        }
    return value


def snapshot(document):
    paths = {SCHEMA} | {row["path"] for row in document["provenance"]["sources"]}
    values = {path: (ROOT / path).read_text() for path in paths}
    values[DESCRIPTOR] = json.dumps(document)
    return [
        dict(
            path=p,
            content=c,
            encoding="text",
            sha256=hashlib.sha256(c.encode()).hexdigest(),
        )
        for p, c in values.items()
    ]


class LeanFixtureRouteTests(unittest.TestCase):
    maxDiff = None

    def test_authored_contract_and_native_capability(self):
        document = yaml.safe_load(CONTRACT.read_text())
        generator = load(
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
            "lean_fixture_normalizer",
        )
        self.assertEqual(generator.lean_fixture_route_descriptor(), document)
        self.assertEqual(json.loads((ROOT / AUTHORED).read_text()), document)
        self.assertEqual(document["id"], "route_validate_lean_fixture_workflow")
        self.assertEqual(document["aliases"], [ROUTE])
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 5},
        )
        self.assertEqual(
            document["policy"]["failure"]["retry"],
            {"max_attempts": 1, "retryable_codes": []},
        )
        self.assertEqual(document["flow"]["steps"][1]["max_iterations"], 1)
        self.assertEqual(document["flow"]["steps"][1]["on_exhausted"], "fail")
        self.assertEqual(document["observability"]["receipts"], "required")
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        self.assertIn(
            "scripts/mathformer.py",
            [s["path"] for s in document["provenance"]["sources"]],
        )
        self.assertEqual(checked_registry(REGISTRY)[ACTION], ITEM)
        self.assertEqual(ITEM.timeout_seconds, 300)
        self.assertFalse(ITEM.depends_on)
        self.assertEqual(ITEM.command, ("{python}", SCRIPT, "--json"))

    def test_original_route_parity_and_stopping(self):
        oracle = original()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve() / "repo"
            for ready in [False, True]:
                if ready:
                    populate(root)
                for keep in [False, True]:
                    context = hub.RunContext(dry_run=True, keep_going=keep)
                    args = selected_match(MATCH), checked_registry(REGISTRY), context
                    actual = hub.run_intent_match(*args, repository_root=root)
                    self.assertEqual(
                        actual, oracle.run_intent_match(*args, repository_root=root)
                    )
                    self.assertEqual(actual["ok"], ready)
                    self.assertEqual(len(actual["children"]), 1)
            for actions in [(), (ACTION,), (ACTION, ACTION)]:
                match = replace(
                    selected_match(MATCH),
                    route=replace(selected_match(MATCH).route, action_ids=actions),
                )
                for keep in [False, True]:
                    args = (
                        match,
                        checked_registry(REGISTRY),
                        hub.RunContext(keep_going=keep),
                    )
                    actual = hub.run_intent_match(
                        *args, repository_root=root / "absent"
                    )
                    self.assertEqual(
                        actual,
                        oracle.run_intent_match(*args, repository_root=root / "absent"),
                    )
                    self.assertEqual(
                        len(actual["children"]),
                        len(actions) if keep else min(1, len(actions)),
                    )
            for runner in [oracle.run_intent_match, hub.run_intent_match]:
                with self.assertRaises(KeyError):
                    runner(
                        selected_match(MATCH),
                        {},
                        hub.RunContext(dry_run=True),
                        repository_root=root,
                    )
                # OS launch errors propagate through the unchanged native boundary.
                with self.assertRaises(FileNotFoundError):
                    runner(
                        selected_match(MATCH),
                        {
                            ACTION: replace(
                                ITEM, command=(str(root / "missing-compiler"),)
                            )
                        },
                        hub.RunContext(),
                        repository_root=root,
                    )
            # A zero fixture action timeout exercises native timeout packing and audit.
            with patch.dict(os.environ, clean_env(), clear=True):
                child = hub.run_action(
                    ACTION,
                    {ACTION: replace(ITEM, timeout_seconds=0)},
                    hub.RunContext(),
                    repository_root=root,
                )
            self.assertEqual(child["status"], "timeout")
            self.assertFalse(child["ok"])
        for keep in [False, True]:
            initial = hub.initialize_intent_state()
            state, done = hub.advance_intent_state(
                initial, {"ok": False}, hub.RunContext(keep_going=keep), 1
            )
            self.assertEqual(initial, {"ok": True, "children": []})
            self.assertEqual(state, {"ok": False, "children": [{"ok": False}]})
            self.assertTrue(done)
            state, _ = hub.advance_intent_state(
                state, {"ok": True}, hub.RunContext(keep_going=True), 2
            )
            self.assertFalse(state["ok"])
            with self.assertRaises(ValueError):
                check_state(state)
        with self.assertRaises(ValueError):
            check_state({"ok": True, "children": [{"ok": False}]}, complete=True)

    def test_native_suite_steps_skips_empty_and_uncaught(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve() / "repo"
            populate(root, count=3, bad_static=True, missing_theorem=True)
            suite = load(root / SCRIPT, "lean_fixture_suite")
            argv = [
                "--manifest",
                str(root / "tests/latex/wiki_level/manifest.json"),
                "--output-dir",
                str(root / "artifacts/wiki_level_suite"),
                "--no-reasoning-log",
                "--skip-concept-map",
                "--skip-hierarchy",
                "--skip-declaration-checks",
            ]
            args = suite.parse_args(argv)
            cwd = Path.cwd()
            try:
                os.chdir(root)
                with (
                    patch.dict(os.environ, clean_env(), clear=True),
                    patch.object(subprocess, "run", subprocess.run),
                    patch.object(shutil, "which", shutil.which),
                ):
                    install_external()
                    prepared = suite.prepare_suite(args)
                    session, state = prepared["session"], prepared["state"]
                    self.assertEqual(
                        state, {"cursor": 0, "cases": [], "expected_declarations": []}
                    )
                    for cursor in range(3):
                        before = deepcopy(state)
                        result = suite.advance_case(session, state)
                        self.assertEqual(state, before)
                        state = result["state"]
                        self.assertEqual(state["cursor"], cursor + 1)
                        self.assertEqual(state["cases"][:-1], before["cases"])
                        self.assertEqual(result["done"], cursor == 2)
                    self.assertEqual(
                        [c["id"] for c in state["cases"]],
                        ["fixture.0", "fixture.1", "fixture.2"],
                    )
                    self.assertEqual(
                        state["expected_declarations"], ["fixture_true"] * 6
                    )
                    self.assertFalse(state["cases"][0]["static_latex_review"]["passed"])
                    self.assertFalse(state["cases"][0]["lean_theorem_present"])
                    self.assertTrue(
                        all(
                            c["concept_map"] is None
                            and c["hierarchy_navigation"] is None
                            for c in state["cases"]
                        )
                    )
                    with self.assertRaises(IndexError):
                        suite.advance_case(session, state)
                    report = suite.finish_suite(
                        session,
                        state,
                        suite.compile_suite_gold(session),
                        suite.audit_suite(session),
                        suite.skipped_declarations(),
                    )
                    self.assertFalse(report["summary"]["passed"])
                    self.assertEqual(
                        report["expected_declaration_checks"]["checked_count"], 0
                    )
                    self.assertEqual(stable(report), stable(suite.run_suite(args)))
                    reset(root)
                    populate(root, count=0)
                    empty = suite.run_suite(args)
                    self.assertEqual(empty["cases"], [])
                    self.assertEqual(empty["summary"]["case_count"], 0)
                    self.assertTrue(empty["summary"]["passed"])
                    # Missing source input aborts before any compiler call or final report.
                    reset(root)
                    populate(root, count=2)
                    (root / "tests/latex/wiki_level/0.tex").unlink()
                    with self.assertRaises(FileNotFoundError):
                        suite.run_suite(args)
                    self.assertFalse(
                        (root / "artifacts/wiki_level_suite/report.json").exists()
                    )
                    self.assertFalse((root.parent / "compiler.jsonl").exists())
                    # The native route supplies no numerical case admission cap.
                    populate(root, count=257)
                    uncapped = suite.prepare_suite(args)
                    self.assertEqual(len(uncapped["session"]["manifest"]["cases"]), 257)
                    self.assertTrue(uncapped["has_cases"])
                    self.assertEqual(uncapped["state"]["cursor"], 0)
            finally:
                os.chdir(cwd)

    def test_registered_tools_real_lunar_compile_execute(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(CONTRACT.read_text())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve() / "repo"
            populate(root)
            server = (
                "import sys;sys.dont_write_bytecode=True;sys.path[:0]="
                + repr([str(ROOT / "scripts"), str(ROOT), str(FIXTURES), *SITES])
                + ";from lean_fixture_boundary import serve;serve("
                + repr(str(root))
                + ","
                + repr(str(FIXTURES))
                + ")"
            )
            manager = SessionManager()
            failure = None
            async with manager.open(
                "lean-fixture",
                StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
                {},
            ) as remote:
                try:
                    tools = [
                        t.model_dump(by_alias=True, exclude_none=True)
                        for t in await remote.tools()
                    ]

                    def compile_document(doc, inventory=None):
                        assets = snapshot(doc)
                        return (
                            compile_workflow(
                                "mcp:lean-fixture",
                                workflow_documents([DESCRIPTOR], assets)[0],
                                tools if inventory is None else inventory,
                            ),
                            assets,
                        )

                    workflow, assets = compile_document(document)
                    self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                    self.assertTrue(workflow["prism_source"])
                    self.assertTrue(workflow["runtime_source"])
                    self.assertFalse(compile_document(document, [])[0]["runnable"])
                    inventory = {t["name"]: t for t in tools}
                    for op in document["operations"].values():
                        tool = inventory[op["execution"]["binding"]["target"]]
                        self.assertEqual(
                            set(tool["inputSchema"]["properties"]), set(op["inputs"])
                        )
                        self.assertEqual(
                            set(tool["outputSchema"]["properties"]), set(op["outputs"])
                        )

                    async def authorize():
                        pass

                    base = dict(
                        match=MATCH,
                        registry=REGISTRY,
                        context=vars(hub.RunContext(dry_run=True)),
                        repository_root=str(root),
                    )

                    async def run(inputs=base, doc=document):
                        bound, received = compile_document(doc)
                        self.assertTrue(bound["runnable"], bound["diagnostics"])
                        return await execute(bound, received, inputs, remote, authorize)

                    for ready in [True, False]:
                        if not ready:
                            (root / SCRIPT).unlink()
                        for keep in [False, True]:
                            inputs = deepcopy(base)
                            inputs["context"]["keep_going"] = keep
                            result = await run(inputs)
                            self.assertEqual(result["status"], "accepted", result)
                            expected = original().run_intent_match(
                                selected_match(MATCH),
                                checked_registry(REGISTRY),
                                hub.RunContext(**inputs["context"]),
                                repository_root=root,
                            )
                            self.assertEqual(result["outputs"], {"result": expected})
                            self.assertEqual(expected["ok"], ready)
                            self.assertEqual(
                                [c["operation"] for c in result["calls"]], ORDER
                            )
                            self.assertTrue(result["runtime"]["effect_records"])
                            self.assertTrue(result["runtime"]["provenance"])
                    self.assertFalse((root.parent / "native.jsonl").exists())
                    inputs = deepcopy(base)
                    inputs["context"]["dry_run"] = False
                    for mode, count in [
                        ("pass", 2),
                        ("pass", 0),
                        ("fail", 2),
                        ("timeout", 2),
                        ("declaration-missing", 2),
                        ("write", 1),
                        ("crash", 2),
                    ]:
                        reset(root)
                        populate(root, count=count)
                        (root.parent / "compiler-mode").write_text(mode)
                        for keep in [False, True]:
                            inputs["context"]["keep_going"] = keep
                            result = await run(inputs)
                            self.assertEqual(result["status"], "accepted", result)
                            route = result["outputs"]["result"]
                            child = route["children"][0]
                            self.assertEqual(
                                [c["operation"] for c in result["calls"]], ORDER
                            )
                            self.assertEqual(len(route["children"]), 1)
                            self.assertEqual(
                                child["argv"], [sys.executable, SCRIPT, "--json"]
                            )
                            trace = list(
                                map(
                                    json.loads,
                                    (root.parent / "native.jsonl")
                                    .read_text()
                                    .splitlines(),
                                )
                            )
                            self.assertEqual(
                                trace[0], {"script": SCRIPT, "timeout": 300}
                            )
                            if mode == "crash":
                                self.assertFalse(route["ok"])
                                self.assertIn(
                                    "fixture compiler launch failed", child["stderr"]
                                )
                                self.assertEqual(child["returncode"], 1)
                                self.assertFalse(
                                    (
                                        root / "artifacts/wiki_level_suite/report.json"
                                    ).exists()
                                )
                                break
                            report = json.loads(child["stdout"])
                            self.assertEqual(report["summary"]["case_count"], count)
                            self.assertEqual(
                                [c["id"] for c in report["cases"]],
                                [f"fixture.{i}" for i in range(count)],
                            )
                            self.assertEqual(
                                report["summary"]["passed"],
                                mode in {"pass", "write"},
                                report,
                            )
                            self.assertTrue(
                                all(
                                    c["concept_map"] is not None
                                    and c["hierarchy_navigation"] is not None
                                    for c in report["cases"]
                                )
                            )
                            self.assertEqual(
                                report["expected_declaration_checks"]["checked_count"],
                                int(count > 0),
                            )
                            self.assertEqual(
                                json.loads(
                                    (
                                        root / "artifacts/wiki_level_suite/report.json"
                                    ).read_text()
                                ),
                                report,
                            )
                            events = list(
                                map(
                                    json.loads,
                                    (
                                        root
                                        / "artifacts/wiki_level_suite/reasoning.jsonl"
                                    )
                                    .read_text()
                                    .splitlines(),
                                )
                            )
                            self.assertEqual(events[0]["step"], "workflow_start")
                            self.assertEqual(events[-1]["step"], "workflow_complete")
                            self.assertEqual(
                                sum(
                                    e["step"] == "latex_expansion_review_suite_complete"
                                    for e in events
                                ),
                                count,
                            )
                            if mode == "write":
                                self.assertEqual(child["status"], "undeclared_writes")
                                self.assertIn(
                                    "undeclared.txt",
                                    child["write_audit"]["unexpected_paths"],
                                )
                                self.assertFalse(route["ok"])
                            if mode not in {"pass", "write"}:
                                self.assertFalse(route["ok"])
                                self.assertEqual(route["status"], "intent_run_failed")
                                self.assertEqual(child["returncode"], 1)
                            if count == 0:
                                self.assertTrue(route["ok"])
                            elif mode == "pass":
                                # The native cold concept index write is undeclared by this
                                # action. Preserve that failure instead of widening authority.
                                self.assertEqual(child["status"], "undeclared_writes")
                                self.assertIn(
                                    "artifacts/mathlib_decl_index.json",
                                    child["write_audit"]["unexpected_paths"],
                                )
                                self.assertFalse(route["ok"])
                            if mode == "timeout":
                                self.assertFalse(report["lean_execution"]["ok"])
                                self.assertEqual(
                                    report["lean_execution"]["returncode"], None
                                )
                            if mode == "declaration-missing":
                                self.assertFalse(
                                    report["expected_declaration_checks"]["ok"]
                                )
                            # Every real native script is executed once in source order.
                            expected_scripts = [SCRIPT]
                            for _ in range(count):
                                expected_scripts.extend(
                                    [
                                        "skills/autoformalization/proof-expansion-difficulty-estimator/scripts/estimate_proof_expansion_difficulty.py",
                                        "skills/mathlib/informal-proof-mathlib-concepts/scripts/map_mathlib_concepts.py",
                                        "skills/mathlib/mathlib-hierarchy-navigator/scripts/navigate_mathlib_hierarchy.py",
                                    ]
                                )
                            expected_scripts.append(
                                "skills/mathlib/mathlib-compatibility-auditor/scripts/check_mathlib_compat.py"
                            )
                            self.assertEqual(
                                [t["script"] for t in trace], expected_scripts
                            )
                            self.assertEqual(
                                [t["timeout"] for t in trace],
                                [300] + [60, 600, 60] * count + [120],
                            )
                            compiler_trace = list(
                                map(
                                    json.loads,
                                    (root.parent / "compiler.jsonl")
                                    .read_text()
                                    .splitlines(),
                                )
                            )
                            self.assertEqual(
                                sum(t["path"] == "gold.lean" for t in compiler_trace), 2
                            )
                            self.assertEqual(
                                [
                                    t["timeout"]
                                    for t in compiler_trace
                                    if t["path"] == "gold.lean"
                                ],
                                [120, None],
                            )
                            self.assertEqual(
                                sum(
                                    t["path"].endswith(
                                        "expected_declaration_checks.lean"
                                    )
                                    for t in compiler_trace
                                ),
                                int(count > 0),
                            )
                            # Replay the frozen source controller with identical fixture input.
                            reset(root)
                            with patch.dict(os.environ, clean_env(), clear=True):
                                expected = original().run_intent_match(
                                    selected_match(MATCH),
                                    checked_registry(REGISTRY),
                                    hub.RunContext(keep_going=keep),
                                    repository_root=root,
                                )
                            self.assertEqual(
                                stable(report),
                                stable(json.loads(expected["children"][0]["stdout"])),
                            )
                            expected["children"][0]["stdout"] = ""
                            compared = deepcopy(route)
                            compared["children"][0]["stdout"] = ""
                            self.assertEqual(stable(compared), stable(expected))
                            if mode == "pass" and count > 0:
                                warm = await run(inputs)
                                self.assertEqual(warm["status"], "accepted", warm)
                                self.assertTrue(warm["outputs"]["result"]["ok"], warm)
                                self.assertEqual(
                                    warm["outputs"]["result"]["status"],
                                    "intent_run_completed",
                                )
                            reset(root)
                    # Budget and loop exhaustion fail through the real PRISM runtime.
                    for budget in [1, 4]:
                        changed = deepcopy(document)
                        changed["policy"]["limits"]["max_operation_calls"] = budget
                        result = await run(base, changed)
                        self.assertEqual(result["status"], "failed", result)
                        self.assertIsNone(result["outputs"])
                        self.assertEqual(
                            sum(
                                bool(c.get("transport_call_performed"))
                                for c in result["calls"]
                            ),
                            budget,
                        )
                    changed = deepcopy(document)
                    changed["flow"]["steps"][1]["until"] = {"literal": False}
                    result = await run(base, changed)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]], ORDER[:-1]
                    )
                    self.assertIsNone(result["outputs"])
                    # Malformed metadata never acquires a native executable capability.
                    for port in ["match", "registry", "repository_root"]:
                        tampered = deepcopy(inputs)
                        if port == "match":
                            tampered["match"]["route"]["title"] = "forged"
                        elif port == "registry":
                            tampered["registry"][ACTION]["command"] = ["forged"]
                        else:
                            tampered["repository_root"] = str(root.parent / "outside")
                        result = await run(tampered)
                        self.assertEqual(result["status"], "failed", result)
                    missing = deepcopy(base)
                    missing["registry"] = {}
                    with self.assertRaises(ExecutionRejected):
                        await run(missing)
                    # The callable native port still returns unknown_action as data;
                    # packing an absent registry action raises the source KeyError.
                    unknown = await remote.call(
                        "mathformer_lean_fixture_route_invoke_action",
                        dict(
                            action_id=ACTION,
                            registry={},
                            context=base["context"],
                            repository_root=str(root),
                        ),
                    )
                    self.assertEqual(unknown["child"]["status"], "unknown_action")
                    self.assertFalse(unknown["child"]["ok"])
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_lean_fixture_route_finish",
                            dict(
                                state={"ok": False, "children": [unknown["child"]]},
                                match=MATCH,
                                registry={},
                            ),
                        )
                except Exception as error:
                    failure = error
            self.assertFalse(manager.active)
            if failure:
                raise failure


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False).result
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
