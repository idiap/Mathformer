#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Offline source parity, registered MCP ports, and real Lunar/PRISM runtime."""

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
from validate_atp_route_tools import (
    ACTION,
    ROUTE,
    selected_match,
    checked_registry,
    check_state,
)
from environment_route_boundary import install_external
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_validate_atp_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
AUTHORED = "skills/control/workflow-contract-validator/references/validate-atp-route.workflow.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
MATCH = {
    "route": {"route_id": ROUTE, "action_ids": [ACTION]},
    "score": 19,
    "matched_terms": ["atp"],
}
ITEM = hub.build_registry()[ACTION]
REGISTRY = {ACTION: hub.action_to_dict(ITEM)}
ORDER = ["initialize", "select_action", "invoke_action", "advance", "finish"]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def original():
    scope = dict(vars(hub))
    exec((FIXTURES / "validate_atp_route_original.py.txt").read_text(), scope)
    return SimpleNamespace(**scope)


def matrix(modes):
    rows = []
    for i, mode in enumerate(modes):
        row = dict(
            id=f"fixture.{i}",
            module_family="atp",
            command=["fixture-environment-compiler", mode],
            owner_skill="fixture",
            hook_id="test.fixture",
            fixture_ids=["external-compiler"],
            test_kind="regression",
            risk_level="low",
            expected_exit=0,
            write_set=["artifacts/"] if mode == "artifact" else [],
        )
        if i:
            row["timeout_seconds"] = 30 + i
        if mode == "missing":
            row["optional_dependency"] = "fixture_missing_provider"
        rows.append(row)
    # A real unselected row proves ATP filtering while retaining matrix order.
    rows.insert(
        1 if rows else 0,
        dict(
            id="fixture.unselected",
            module_family="lean",
            command=["forbidden-unselected-compiler"],
            owner_skill="fixture",
            hook_id="test.fixture",
            fixture_ids=["filter"],
            test_kind="regression",
            risk_level="low",
            write_set=[],
        ),
    )
    return {"schema_version": 2, "tests": rows}


def populate(root, modes=("pass",)):
    for relative in [
        "tests/test_program/run_comprehensive_tests.py",
        "scripts/workflow_write_audit.py",
    ]:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
        assert target.read_bytes() == (ROOT / relative).read_bytes()
    (root / "tests/test_matrix.json").write_text(json.dumps(matrix(modes)))


def reset(root):
    shutil.rmtree(root / "artifacts", ignore_errors=True)
    (root / "undeclared.txt").unlink(missing_ok=True)
    for name in ["compiler.jsonl", "delegate.jsonl"]:
        (root.parent / name).unlink(missing_ok=True)


def clean_env():
    return {
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": os.pathsep.join(
            [str(FIXTURES / "environment_route_startup"), str(FIXTURES)]
        ),
    }


def stable(value):
    if isinstance(value, list):
        return [stable(row) for row in value]
    if isinstance(value, dict):
        return {
            key: stable(item)
            for key, item in value.items()
            if key not in {"duration_seconds", "run_id"}
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


class ATPRouteTests(unittest.TestCase):
    maxDiff = None

    def test_contract_generator_provenance(self):
        document = yaml.safe_load(CONTRACT.read_text())
        generator = load(
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
            "atp_normalizer",
        )
        self.assertEqual(generator.validate_atp_route_descriptor(), document)
        self.assertEqual(json.loads((ROOT / AUTHORED).read_text()), document)
        self.assertEqual(document["id"], "route_validate_atp_workflow")
        self.assertEqual(document["aliases"], [ROUTE])
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 5},
        )
        self.assertEqual(
            document["policy"]["failure"],
            {"default": "fail", "retry": {"max_attempts": 1, "retryable_codes": []}},
        )
        self.assertEqual(document["flow"]["steps"][1]["max_iterations"], 1)
        self.assertIn(
            "scripts/mathformer.py",
            [s["path"] for s in document["provenance"]["sources"]],
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        self.assertEqual(checked_registry(REGISTRY)[ACTION], ITEM)
        self.assertEqual(ITEM.timeout_seconds, 900)

    def test_native_route_parity_stopping_and_exception(self):
        oracle = original()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve() / "repo"
            for ready in [False, True]:
                if ready:
                    populate(root)
                for keep in [False, True]:
                    context = hub.RunContext(dry_run=True, keep_going=keep)
                    actual = hub.run_intent_match(
                        selected_match(MATCH),
                        checked_registry(REGISTRY),
                        context,
                        repository_root=root,
                    )
                    self.assertEqual(
                        actual,
                        oracle.run_intent_match(
                            selected_match(MATCH),
                            checked_registry(REGISTRY),
                            context,
                            repository_root=root,
                        ),
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
            # Real OS boundary failures propagate; no source exception is simulated.
            broken = {ACTION: replace(ITEM, command=(str(root / "missing-compiler"),))}
            for runner in [oracle.run_intent_match, hub.run_intent_match]:
                with self.assertRaises(FileNotFoundError):
                    runner(
                        selected_match(MATCH),
                        broken,
                        hub.RunContext(),
                        repository_root=root,
                    )
            # Actual subprocess timeout with a zero test budget; production stays 900.
            with patch.dict(os.environ, clean_env(), clear=True):
                timed = hub.run_action(
                    ACTION,
                    {ACTION: replace(ITEM, timeout_seconds=0)},
                    hub.RunContext(),
                    repository_root=root,
                )
            self.assertEqual(timed["status"], "timeout")
            self.assertFalse(timed["ok"])
        for keep in [False, True]:
            initial = hub.initialize_intent_state()
            state, done = hub.advance_intent_state(
                initial, {"ok": False}, hub.RunContext(keep_going=keep), 1
            )
            self.assertEqual(initial, {"ok": True, "children": []})
            self.assertEqual(state, {"ok": False, "children": [{"ok": False}]})
            self.assertTrue(done)
            later, _ = hub.advance_intent_state(
                state, {"ok": True}, hub.RunContext(keep_going=True), 2
            )
            self.assertFalse(later["ok"])
            with self.assertRaises(ValueError):
                check_state(state)
            with self.assertRaises(ValueError):
                check_state({"ok": True, "children": [{"ok": False}]}, complete=True)

    def test_native_matrix_state_and_external_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve() / "repo"
            modes = [
                "pass",
                "fail",
                "timeout",
                "missing",
                "write",
                "artifact",
                "large",
                "pass",
            ]
            populate(root, modes)
            runner = load(
                root / "tests/test_program/run_comprehensive_tests.py",
                "atp_matrix_fixture",
            )
            args = runner.parse_args(
                ["--module-family", "atp", "--json", "--run-id", "fixture"]
            )
            # Restore global boundary APIs after installing only external fixtures.
            with (
                patch.object(subprocess, "run", subprocess.run),
                patch.object(shutil, "which", shutil.which),
            ):
                install_external()
                runner.enter_checks(args)
                state = runner.prepare_checks(args)
                self.assertEqual(state["index"], 0)
                self.assertEqual(
                    [r["id"] for r in state["selected"]],
                    [f"fixture.{i}" for i in range(len(modes))],
                )
                with self.assertRaises(ValueError):
                    runner.finalize_checks(state, args)
                while runner.checks_pending(state):
                    previous = deepcopy(state)
                    state = runner.advance_check(state, args)
                    self.assertEqual(state["index"], previous["index"] + 1)
                    self.assertEqual(state["results"][:-1], previous["results"])
                    self.assertEqual(state["selected"], previous["selected"])
                with self.assertRaises(ValueError):
                    runner.advance_check(state, args)
                report = runner.finalize_checks(state, args)
                self.assertEqual(
                    [r["status"] for r in report["results"]],
                    ["pass", "fail", "fail", "skip", "fail", "pass", "pass", "pass"],
                )
                self.assertFalse(report["ok"])
                reset(root)
                replay = runner.run(args)
                self.assertEqual(stable(report), stable(replay))
                self.assertEqual(
                    [
                        r["timeout"]
                        for r in map(
                            json.loads,
                            (root.parent / "compiler.jsonl").read_text().splitlines(),
                        )
                    ],
                    [120, 31, 32, 34, 35, 36, 37],
                )
                self.assertEqual(
                    report["results"][4]["write_audit"]["unexpected_paths"],
                    ["undeclared.txt"],
                )
                self.assertTrue(report["results"][5]["write_audit"]["ok"])
                reset(root)
                populate(root, [])
                empty = runner.prepare_checks(args)
                self.assertFalse(runner.checks_pending(empty))
                self.assertEqual(empty["selected"], [])
                self.assertEqual(
                    runner.finalize_checks(empty, args)["summary"]["total"], 0
                )

    def test_lunar_registered_tools_compile_execute(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(CONTRACT.read_text())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve() / "repo"
            populate(root)
            server = (
                "import sys;sys.dont_write_bytecode=True;sys.path[:0]="
                + repr([str(ROOT / "scripts"), str(ROOT), str(FIXTURES), *SITES])
                + ";from validate_atp_route_boundary import serve;serve("
                + repr(str(root))
                + ","
                + repr(str(FIXTURES))
                + ")"
            )
            manager = SessionManager()
            failure = None
            async with manager.open(
                "validate-atp",
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
                                "mcp:validate-atp",
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
                            (root / "tests/test_matrix.json").unlink()
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
                    self.assertFalse((root.parent / "delegate.jsonl").exists())
                    inputs = deepcopy(base)
                    inputs["context"]["dry_run"] = False
                    for modes in [
                        ["pass", "artifact"],
                        ["fail", "timeout", "missing", "write", "pass"],
                        ["missing"],
                        [],
                        ["crash", "pass"],
                    ]:
                        reset(root)
                        populate(root, modes)
                        result = await run(inputs)
                        self.assertEqual(result["status"], "accepted", result)
                        route = result["outputs"]["result"]
                        child = route["children"][0]
                        self.assertEqual(
                            [c["operation"] for c in result["calls"]], ORDER
                        )
                        self.assertEqual(len(route["children"]), 1)
                        self.assertEqual(
                            child["argv"], [sys.executable, *ITEM.command[1:]]
                        )
                        traces = list(
                            map(
                                json.loads,
                                (root.parent / "delegate.jsonl")
                                .read_text()
                                .splitlines(),
                            )
                        )
                        self.assertEqual(len(traces), 1)
                        self.assertEqual(traces[0]["timeout"], 900)
                        if "crash" in modes:
                            self.assertFalse(route["ok"])
                            self.assertEqual(child["returncode"], 1)
                            self.assertIn(
                                "fixture compiler launch failed", child["stderr"]
                            )
                            self.assertEqual(child["stdout"], "")
                            self.assertFalse(
                                (
                                    root
                                    / "artifacts/test_program/deterministic_tests.json"
                                ).exists()
                            )
                            continue
                        report = json.loads(child["stdout"])
                        self.assertEqual(report["profile"], "workstation")
                        self.assertEqual(report["summary"]["total"], len(modes))
                        self.assertEqual(
                            [r["check_id"] for r in report["results"]],
                            [f"fixture.{i}" for i in range(len(modes))],
                        )
                        self.assertEqual(report["ok"], "fail" not in modes)
                        self.assertEqual(
                            child["returncode"], 3 if "fail" in modes else 0
                        )
                        self.assertEqual(route["ok"], "fail" not in modes)
                        self.assertEqual(
                            json.loads(
                                (
                                    root
                                    / "artifacts/test_program/deterministic_tests.json"
                                ).read_text()
                            ),
                            report,
                        )
                        if "write" in modes:
                            self.assertEqual(child["status"], "undeclared_writes")
                            self.assertEqual(
                                child["write_audit"]["unexpected_paths"],
                                ["undeclared.txt"],
                            )
                            self.assertEqual(
                                [r["status"] for r in report["results"]],
                                ["fail", "fail", "skip", "fail", "pass"],
                            )
                        if modes == ["missing"]:
                            self.assertEqual(report["summary"]["skip"], 1)
                            self.assertTrue(report["ok"])
                        # Compare the unchanged original route using a real delegate
                        # in the same isolated mount and the same external fixtures.
                        reset(root)
                        with patch.dict(os.environ, clean_env(), clear=True):
                            expected = original().run_intent_match(
                                selected_match(MATCH),
                                checked_registry(REGISTRY),
                                hub.RunContext(),
                                repository_root=root,
                            )
                        expected_report = json.loads(expected["children"][0]["stdout"])
                        self.assertEqual(stable(report), stable(expected_report))
                        expected["children"][0]["stdout"] = ""
                        compared = deepcopy(route)
                        compared["children"][0]["stdout"] = ""
                        self.assertEqual(compared, expected)
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
                    result = await run(missing)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual([c["operation"] for c in result["calls"]], ORDER)
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
