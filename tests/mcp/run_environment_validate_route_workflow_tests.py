#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Actual native environment processes, MCP bindings and Lunar/PRISM execution.

Only external compiler/provider processes are substituted. Temporary repositories
contain unchanged runner/audit sources and synthetic matrix inputs. No
production workflows, installed compilers, credentials or providers are used.
"""

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
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT),
    str(FIXTURES),
]
SITES = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
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
from environment_validate_route_tools import (
    ACTION,
    ROUTE,
    selected_match,
    checked_registry,
    register_environment_validate_route_tools,
)
from environment_route_boundary import install_external
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_environment_validate_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
AUTHORED = "skills/control/workflow-contract-validator/references/environment-validate-route.workflow.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
MATCH = {
    "route": {"route_id": ROUTE, "action_ids": [ACTION]},
    "score": 17.5,
    "matched_terms": ["environment", "validate"],
}
REGISTRY = {ACTION: hub.action_to_dict(hub.build_registry()[ACTION])}
ORDER = ["initialize", "select", "execute", "advance", "finish"]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def original():
    scope = dict(vars(hub))
    exec((FIXTURES / "environment_validate_route_original.py.txt").read_text(), scope)
    return SimpleNamespace(**scope)


def matrix(modes):
    rows = []
    for index, mode in enumerate(modes):
        rows.append(
            dict(
                id=f"fixture.{index}",
                module_family="environment",
                command=["fixture-environment-compiler", mode],
                owner_skill="fixture",
                hook_id="test.fixture",
                fixture_ids=["external-compiler"],
                test_kind="regression",
                risk_level="low",
                timeout_seconds=30 + index,
                expected_exit=0,
                write_set=["artifacts/"] if mode == "artifact" else [],
                **(
                    {"optional_dependency": "fixture_missing_provider"}
                    if mode == "missing"
                    else {}
                ),
            )
        )
    return {"schema_version": 2, "tests": rows}


def populate(root):
    for name in [
        "tests/test_program/run_comprehensive_tests.py",
        "scripts/workflow_write_audit.py",
        "tests/environment/run_dependency_lock_contract.py",
    ]:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
        assert target.read_bytes() == (ROOT / name).read_bytes()
    (root / "tests/test_matrix.json").write_text(json.dumps(matrix(["pass"])))


def reset(root):
    shutil.rmtree(root / "artifacts", ignore_errors=True)
    (root / "undeclared.txt").unlink(missing_ok=True)
    for name in ["compiler.jsonl", "native-children.jsonl", "uv-mode.txt"]:
        (root.parent / name).unlink(missing_ok=True)


def clean_env():
    return {
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": os.pathsep.join(
            [str(FIXTURES / "environment_route_startup"), str(FIXTURES)]
        ),
    }


def stable(value):
    """Only native nondeterministic time fields differ between real processes."""
    if isinstance(value, list):
        return [stable(item) for item in value]
    if isinstance(value, dict):
        return {
            key: stable(item)
            for key, item in value.items()
            if key not in {"duration_seconds", "run_id"}
        }
    return value


def stable_route(value):
    value = deepcopy(value)
    child = value["children"][0]
    if child.get("stdout"):
        child["stdout"] = stable(json.loads(child["stdout"]))
    return value


def snapshot(document):
    values = {
        row["path"]: (ROOT / row["path"]).read_text()
        for row in document["provenance"]["sources"]
    }
    values[SCHEMA] = (ROOT / SCHEMA).read_text()
    values[DESCRIPTOR] = json.dumps(document)
    return [
        dict(
            path=path,
            content=content,
            encoding="text",
            sha256=hashlib.sha256(content.encode()).hexdigest(),
        )
        for path, content in values.items()
    ]


class EnvironmentRouteTests(unittest.TestCase):
    maxDiff = None

    def test_identity_generator_provenance_and_native_state(self):
        document = yaml.safe_load(CONTRACT.read_text())
        generator = load(
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
            "environment_normalizer",
        )
        self.assertEqual(generator.environment_validate_route_descriptor(), document)
        self.assertEqual(document, json.loads((ROOT / AUTHORED).read_text()))
        self.assertEqual(document["id"], "route_environment_validate_workflow")
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
        self.assertEqual(list(document["operations"]), ORDER)
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        self.assertTrue(
            any(
                row["path"] == "scripts/mathformer.py"
                and row["selector"] == "run_intent_match"
                for row in document["provenance"]["sources"]
            )
        )
        item = checked_registry(REGISTRY)[ACTION]
        full_registry = hub.build_registry()
        self.assertEqual(
            checked_registry(
                {key: hub.action_to_dict(value) for key, value in full_registry.items()}
            ),
            full_registry,
        )
        self.assertEqual(
            item.command,
            (
                "{python}",
                "tests/test_program/run_comprehensive_tests.py",
                "--module-family",
                "environment",
                "--json",
            ),
        )
        self.assertEqual(item.timeout_seconds, 900)
        oracle, match, native = (
            original(),
            selected_match(MATCH),
            checked_registry(REGISTRY),
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            for ready in [False, True]:
                if ready:
                    populate(root)
                for keep in [False, True]:
                    context = hub.RunContext(dry_run=True, keep_going=keep)
                    result = hub.run_intent_match(
                        match, native, context, repository_root=root
                    )
                    self.assertEqual(
                        result,
                        oracle.run_intent_match(
                            match, native, context, repository_root=root
                        ),
                    )
                    self.assertEqual(result["ok"], ready)
                    self.assertEqual(len(result["children"]), 1)
                    state = hub.initialize_intent_state()
                    before = deepcopy(state)
                    child = {"ok": ready, "status": "fixture"}
                    updated, done = hub.advance_intent_state(state, child, context, 1)
                    self.assertEqual(state, before)
                    self.assertTrue(done)
                    self.assertEqual(updated, {"ok": ready, "children": [child]})
                self.assertFalse((root / "artifacts").exists())
            # Native sticky failure generalizes beyond this one-action route.
            state, done = hub.advance_intent_state(
                {"ok": False, "children": [{"ok": False}]},
                {"ok": True},
                hub.RunContext(keep_going=True),
                2,
            )
            self.assertFalse(state["ok"])
            self.assertTrue(done)

    def test_native_runner_cursor_and_external_failure_boundaries(self):
        # Exercise the actual delegated cursor without changing its algorithm.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            populate(root)
            data = matrix(["fail", "missing", "timeout", "pass"])
            (root / "tests/test_matrix.json").write_text(json.dumps(data))
            runner = load(
                root / "tests/test_program/run_comprehensive_tests.py",
                "environment_cursor_test",
            )
            old_run, old_which = subprocess.run, shutil.which
            with patch.dict(os.environ, {}, clear=True):
                install_external()
                try:
                    args = runner.parse_args(["--module-family", "environment"])
                    self.assertFalse(runner.enter_checks(args))
                    state = runner.prepare_checks(args)
                    self.assertEqual(state["matrix"], state["selected"])
                    self.assertEqual(state["families"], ["environment"])
                    with self.assertRaisesRegex(ValueError, "unconsumed"):
                        runner.finalize_checks(state, args)
                    for index in range(4):
                        before = deepcopy(state)
                        self.assertTrue(runner.checks_pending(state))
                        state = runner.advance_check(state, args)
                        self.assertEqual(state["index"], index + 1)
                        self.assertEqual(state["results"][:-1], before["results"])
                        self.assertEqual(before["index"], index)
                    self.assertFalse(runner.checks_pending(state))
                    self.assertEqual(
                        [r["status"] for r in state["results"]],
                        ["fail", "skip", "fail", "pass"],
                    )
                    with self.assertRaisesRegex(ValueError, "exhausted"):
                        runner.advance_check(state, args)
                    report = runner.finalize_checks(state, args)
                    self.assertFalse(report["ok"])
                    self.assertEqual(report["summary"]["total"], 4)
                    self.assertEqual(
                        runner.run_check(data["tests"][1], True)["status"], "fail"
                    )
                    # No artificial two-row limit is imposed by this route.
                    self.assertEqual(state["index"], len(state["selected"]))
                    broken = deepcopy(state)
                    broken["results"][0].pop("regression_fingerprint")
                    self.assertFalse(runner.finalize_checks(broken, args)["ok"])
                    strict = runner.parse_args(
                        ["--module-family", "environment", "--profile", "strict"]
                    )
                    strict_report = runner.run(strict)
                    self.assertEqual(strict_report["results"][1]["status"], "fail")
                    # Early snapshot does not load an invalid matrix or run checks.
                    runner.MATRIX_FILE.write_text("{}")
                    early = runner.run(
                        runner.parse_args(["--emit-dependency-map-only", "--json"])
                    )
                    self.assertTrue(early["ok"])
                    self.assertEqual(
                        early["results"][0]["check_id"],
                        "environment.dependency_map.write",
                    )
                    self.assertEqual(early["summary"]["total"], 1)
                    self.assertTrue((root / early["results"][0]["stdout"]).exists())
                    # Native launch timeout capture and unexpected-error path,
                    # substituting an external compiler command only.
                    item = replace(
                        hub.build_registry()[ACTION],
                        command=("fixture-environment-compiler", "timeout"),
                        timeout_seconds=2,
                        required_paths=(),
                    )
                    timed = hub.run_leaf_action(
                        item, hub.RunContext(), [], repository_root=root
                    )
                    self.assertEqual(timed["status"], "timeout")
                    self.assertEqual(timed["stdout"], b"partial")
                    self.assertFalse(timed["ok"])
                    with self.assertRaisesRegex(OSError, "compiler launch failed"):
                        hub.run_leaf_action(
                            replace(
                                item, command=("fixture-environment-compiler", "crash")
                            ),
                            hub.RunContext(),
                            [],
                            repository_root=root,
                        )
                finally:
                    subprocess.run, shutil.which = old_run, old_which

    def test_registered_policy_admission(self):
        asyncio.run(self.policy())

    async def policy(self):
        from mcp.server.fastmcp import FastMCP

        for authorize, allowed, message in [
            (
                lambda: (_ for _ in ()).throw(PermissionError("readonly")),
                lambda p: True,
                "readonly",
            ),
            (lambda: None, lambda p: False, "service roots"),
        ]:
            mcp = FastMCP("environment-policy")
            register_environment_validate_route_tools(mcp, authorize, allowed)
            with tempfile.TemporaryDirectory() as directory:
                kwargs = dict(
                    action_id=ACTION,
                    registry=REGISTRY,
                    mount={"repository_root": directory},
                    context=vars(hub.RunContext()),
                )
                with self.assertRaisesRegex(Exception, message):
                    await mcp.call_tool("mathformer_environment_route_execute", kwargs)
                kwargs["context"]["dry_run"] = True
                await mcp.call_tool("mathformer_environment_route_execute", kwargs)

    def test_registered_lunar_prism_execution(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(CONTRACT.read_text())
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve() / "repo"
            populate(root)
            server = (
                "import sys;sys.dont_write_bytecode=True;sys.path[:0]="
                + repr([str(ROOT / "scripts"), str(FIXTURES), str(ROOT), *SITES])
                + ";from environment_route_boundary import serve;serve("
                + repr(str(root))
                + ","
                + repr(str(FIXTURES))
                + ")"
            )
            manager, failure = SessionManager(), None
            async with manager.open(
                "environment-route",
                StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
                {},
            ) as remote:
                try:
                    tools = [
                        t.model_dump(by_alias=True, exclude_none=True)
                        for t in await remote.tools()
                    ]

                    def compiled(doc, inventory=None):
                        assets = snapshot(doc)
                        bound = compile_workflow(
                            "mcp:environment-route",
                            workflow_documents([DESCRIPTOR], assets)[0],
                            tools if inventory is None else inventory,
                        )
                        return bound, assets

                    workflow, assets = compiled(document)
                    self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                    self.assertTrue(workflow["prism_source"])
                    self.assertTrue(workflow["runtime_source"])
                    self.assertEqual(set(workflow["bindings"]), set(ORDER))
                    self.assertFalse(compiled(document, [])[0]["runnable"])
                    broken = deepcopy(document)
                    broken["operations"]["execute"]["execution"]["binding"][
                        "target"
                    ] = "absent_environment_tool"
                    self.assertFalse(compiled(broken)[0]["runnable"])
                    advertised = {tool["name"]: tool for tool in tools}
                    for operation in document["operations"].values():
                        binding = operation["execution"]["binding"]
                        self.assertEqual(binding["operation"], binding["target"])
                        tool = advertised[binding["target"]]
                        self.assertEqual(
                            set(tool["inputSchema"]["properties"]),
                            set(operation["inputs"]),
                        )
                        self.assertEqual(
                            set(tool["outputSchema"]["properties"]),
                            set(operation["outputs"]),
                        )

                    async def authorize():
                        pass

                    base = dict(
                        match=MATCH,
                        registry=REGISTRY,
                        context=vars(hub.RunContext()),
                        mount={"repository_root": str(root)},
                    )

                    async def run(inputs=base, doc=document):
                        bound, received = compiled(doc)
                        self.assertTrue(bound["runnable"], bound["diagnostics"])
                        return await execute(bound, received, inputs, remote, authorize)

                    empty_selection = matrix(["crash"])
                    empty_selection["tests"][0]["module_family"] = "atp"
                    cases = [
                        matrix(["pass", "artifact"]),
                        matrix(["fail", "timeout", "write", "pass"]),
                        matrix(["missing"]),
                        empty_selection,
                        matrix(["large", "fail", "pass"]),
                    ]
                    cases[-1]["tests"][1]["expected_exit"] = 7
                    del cases[-1]["tests"][2]["timeout_seconds"]
                    filtered = matrix(["pass", "crash", "pass"])
                    filtered["tests"][1]["module_family"] = "atp"
                    cases.append(filtered)
                    for data in cases:
                        reset(root)
                        (root / "tests/test_matrix.json").write_text(json.dumps(data))
                        result = await run()
                        self.assertEqual(result["status"], "accepted", result)
                        route = result["outputs"]["result"]
                        child = route["children"][0]
                        self.assertEqual(
                            [c["operation"] for c in result["calls"]], ORDER
                        )
                        self.assertEqual(
                            [c["tool"] for c in result["calls"]],
                            ["mathformer_environment_route_" + op for op in ORDER],
                        )
                        self.assertEqual(len(route["children"]), 1)
                        self.assertEqual(route["route"]["score"], MATCH["score"])
                        self.assertEqual(
                            route["route"]["matched_terms"], MATCH["matched_terms"]
                        )
                        self.assertEqual(
                            child["argv"],
                            [
                                sys.executable,
                                "tests/test_program/run_comprehensive_tests.py",
                                "--module-family",
                                "environment",
                                "--json",
                            ],
                        )
                        self.assertTrue(child["stdout"], child)
                        report = json.loads(child["stdout"])
                        rows = [
                            r
                            for r in data["tests"]
                            if r["module_family"] in {"environment"}
                        ]
                        self.assertEqual(report["families"], ["environment"])
                        self.assertEqual(report["summary"]["total"], len(rows))
                        self.assertEqual(
                            [r["check_id"] for r in report["results"]],
                            [r["id"] for r in rows],
                        )
                        self.assertEqual(report["schema_errors"], [])
                        self.assertEqual(child["returncode"], 0 if report["ok"] else 3)
                        self.assertEqual(route["ok"], report["ok"])
                        self.assertEqual(
                            route["status"],
                            (
                                "intent_run_completed"
                                if route["ok"]
                                else "intent_run_failed"
                            ),
                        )
                        report_root = root / "artifacts/test_program"
                        self.assertEqual(
                            json.loads(
                                (report_root / "deterministic_tests.json").read_text()
                            ),
                            report,
                        )
                        self.assertTrue((report_root / "dependency_map.json").exists())
                        ledger = root.parent / "compiler.jsonl"
                        self.assertEqual(
                            (
                                [json.loads(s) for s in ledger.read_text().splitlines()]
                                if ledger.exists()
                                else []
                            ),
                            [
                                dict(
                                    command=r["command"],
                                    timeout=r.get("timeout_seconds", 120),
                                )
                                for r in rows
                                if "optional_dependency" not in r
                            ],
                        )
                        if any(r["command"][1] == "write" for r in rows):
                            self.assertEqual(
                                [r["status"] for r in report["results"]],
                                ["fail", "fail", "fail", "pass"],
                            )
                            self.assertEqual(report["results"][1]["stdout"], "partial")
                            self.assertEqual(
                                report["results"][1]["stderr"], "timeout after 31s"
                            )
                            self.assertEqual(child["status"], "undeclared_writes")
                            self.assertEqual(
                                child["write_audit"]["unexpected_paths"],
                                ["undeclared.txt"],
                            )
                        if rows and rows[0]["command"][1] == "missing":
                            self.assertEqual(report["results"][0]["status"], "skip")
                            self.assertTrue(report["ok"])
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["replay_artifacts"])
                        # Same real subprocess/delegate/report/audit path through
                        # the frozen entrypoint; compare all non-time output data.
                        reset(root)
                        with patch.dict(os.environ, clean_env(), clear=True):
                            expected = original().run_intent_match(
                                selected_match(MATCH),
                                checked_registry(REGISTRY),
                                hub.RunContext(),
                                repository_root=root,
                            )
                        self.assertEqual(stable_route(route), stable_route(expected))
                    # Canonical matrix rows run from byte-identical source copies.
                    # Only uv's external compiler boundary is substituted.
                    canonical = json.loads(
                        (ROOT / "tests/test_matrix.json").read_text()
                    )
                    canonical["tests"] = [
                        r
                        for r in canonical["tests"]
                        if r["module_family"] == "environment"
                    ]
                    self.assertEqual(
                        [r["id"] for r in canonical["tests"]],
                        [
                            "environment.dependency_map",
                            "environment.dependency_lock.contract",
                        ],
                    )
                    for uv_mode in [None, "pass", "fail"]:
                        reset(root)
                        (root / "tests/test_matrix.json").write_text(
                            json.dumps(canonical)
                        )
                        (root / "pyproject.toml").write_text(
                            "\n".join(
                                f"{profile} = []"
                                for profile in [
                                    "physics",
                                    "mcp",
                                    "documents",
                                    "providers",
                                    "knowledge-base",
                                ]
                            )
                        )
                        (root / "uv.lock").write_text(
                            'requires-python = ">=3.11"\n'
                            + "\n".join(
                                f'name = "{package}"'
                                for package in [
                                    "sympy",
                                    "mcp",
                                    "docling",
                                    "openai",
                                    "anthropic",
                                    "huggingface-hub",
                                ]
                            )
                        )
                        if uv_mode:
                            (root.parent / "uv-mode.txt").write_text(uv_mode)
                        result = await run()
                        self.assertEqual(result["status"], "accepted", result)
                        route = result["outputs"]["result"]
                        child = route["children"][0]
                        report = json.loads(child["stdout"])
                        self.assertEqual(
                            [r["check_id"] for r in report["results"]],
                            [r["id"] for r in canonical["tests"]],
                        )
                        self.assertEqual(
                            [r["status"] for r in report["results"]],
                            ["pass", "skip" if uv_mode is None else uv_mode],
                        )
                        self.assertEqual(
                            child["returncode"], 3 if uv_mode == "fail" else 0
                        )
                        self.assertEqual(route["ok"], uv_mode != "fail")
                        self.assertTrue(child["write_audit"]["ok"])
                        self.assertEqual(
                            json.loads(report["results"][0]["stdout"])["summary"][
                                "total"
                            ],
                            1,
                        )
                        launches = [
                            json.loads(line)
                            for line in (root.parent / "native-children.jsonl")
                            .read_text()
                            .splitlines()
                        ]
                        self.assertEqual(
                            [row["timeout"] for row in launches],
                            [120, 30] if uv_mode else [120],
                        )
                        if uv_mode:
                            lock_report = json.loads(report["results"][1]["stdout"])
                            self.assertEqual(
                                lock_report["cases"]["lock_current"], uv_mode == "pass"
                            )
                            self.assertEqual(lock_report["ok"], uv_mode == "pass")
                    # Preflight and dry-run do not launch the delegate.
                    reset(root)
                    (root / "tests/test_matrix.json").unlink()
                    for dry in [False, True]:
                        for keep in [False, True]:
                            inputs = deepcopy(base)
                            inputs["context"].update(dry_run=dry, keep_going=keep)
                            result = await run(inputs)
                            expected = hub.run_intent_match(
                                selected_match(MATCH),
                                checked_registry(REGISTRY),
                                hub.RunContext(**inputs["context"]),
                                repository_root=root,
                            )
                            self.assertEqual(result["outputs"], {"result": expected})
                            self.assertEqual(len(result["calls"]), 5)
                            self.assertFalse(expected["ok"])
                            self.assertFalse((root / "artifacts").exists())
                    populate(root)
                    inputs = deepcopy(base)
                    inputs["context"]["dry_run"] = True
                    result = await run(inputs)
                    self.assertTrue(result["outputs"]["result"]["ok"])
                    self.assertEqual(
                        result["outputs"]["result"]["children"][0]["status"], "dry_run"
                    )
                    # Empty mount preserves the default repository with no run.
                    inputs["mount"] = {}
                    result = await run(inputs)
                    self.assertEqual(
                        result["outputs"],
                        {
                            "result": hub.run_intent_match(
                                selected_match(MATCH),
                                checked_registry(REGISTRY),
                                hub.RunContext(dry_run=True),
                            )
                        },
                    )
                    # Real inner unexpected launch failure becomes a nonzero
                    # native delegate exit, preserved as negative child data.
                    reset(root)
                    (root / "tests/test_matrix.json").write_text(
                        json.dumps(matrix(["crash", "pass"]))
                    )
                    result = await run()
                    self.assertEqual(result["status"], "accepted", result)
                    child = result["outputs"]["result"]["children"][0]
                    self.assertFalse(child["ok"])
                    self.assertIn("fixture compiler launch failed", child["stderr"])
                    self.assertEqual(
                        len((root.parent / "compiler.jsonl").read_text().splitlines()),
                        1,
                    )
                    reset(root)
                    (root / "tests/test_matrix.json").write_text(json.dumps(matrix([])))
                    result = await run()
                    self.assertEqual(result["status"], "accepted", result)
                    child = result["outputs"]["result"]["children"][0]
                    self.assertFalse(child["ok"])
                    self.assertIn("at least one executable test row", child["stderr"])
                    self.assertFalse((root.parent / "compiler.jsonl").exists())
                    # Missing registry metadata propagates at finish, after the
                    # native unknown_action observation has been accumulated.
                    inputs = deepcopy(base)
                    inputs["registry"] = {}
                    result = await run(inputs)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual([c["operation"] for c in result["calls"]], ORDER)
                    # Reject forged commands and route metadata at their bound
                    # operation, without any retry or downstream completion.
                    for port in ["registry", "match"]:
                        inputs = deepcopy(base)
                        if port == "registry":
                            inputs[port][ACTION]["command"] = ["arbitrary-command"]
                        else:
                            inputs[port]["route"]["title"] = "forged title"
                        result = await run(inputs)
                        self.assertEqual(result["status"], "failed", result)
                        self.assertIsNone(result["outputs"])
                        self.assertEqual(
                            len(result["calls"]), 3 if port == "registry" else 2
                        )
                    # All budgets/exhaustion are enforced by the real PRISM
                    # runtime; force exhaustion only in a changed test graph.
                    inputs = deepcopy(base)
                    inputs["context"]["dry_run"] = True
                    for budget in [1, 4]:
                        changed = deepcopy(document)
                        changed["policy"]["limits"]["max_operation_calls"] = budget
                        result = await run(inputs, changed)
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
                    result = await run(inputs, changed)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]], ORDER[:-1]
                    )
                    self.assertIsNone(result["outputs"])
                    changed = deepcopy(document)
                    changed["flow"]["steps"][1]["body"]["steps"][0]["arguments"][
                        "state"
                    ] = {"literal": {"ok": True, "children": [{"ok": True}]}}
                    result = await run(inputs, changed)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(len(result["calls"]), 2)
                    # The service mount check precedes any native process.
                    inputs["context"]["dry_run"] = False
                    inputs["mount"]["repository_root"] = str(root.parent / "outside")
                    result = await run(inputs)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(len(result["calls"]), 3)
                    timed = deepcopy(document)
                    timed["policy"]["limits"]["wall_time_seconds"] = 1
                    bound, received = compiled(timed)

                    async def waiting_authority():
                        await asyncio.Event().wait()

                    with self.assertRaises(TimeoutError):
                        await execute(bound, received, base, remote, waiting_authority)
                except Exception as error:
                    failure = error
            self.assertFalse(manager.active)
            if failure:
                raise failure


if __name__ == "__main__":
    program = unittest.main(verbosity=2, exit=False)
    result = program.result
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
