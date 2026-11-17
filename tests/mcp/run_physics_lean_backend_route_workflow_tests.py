#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native route/MCP/Lunar/PRISM fixtures; no external scientific execution."""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != python.parent.parent.resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.path[:0] = [
    str(ROOT),
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT / "tests/mcp/fixtures"),
    str(ROOT / "tests/mcp"),
]
SITES = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
sys.path.extend(SITES)

import asyncio
from copy import deepcopy
import hashlib
import importlib.util
import json
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import yaml
import mathformer as hub
from physics_lean_backend_route_tools import (
    ACTION,
    ROUTE,
    selected_match,
    checked_registry,
    check_state,
    register_physics_lean_backend_route_tools,
)
from backend_suite_boundary import stage, install
from run_physics_backend_suite_workflow_tests import BackendSuiteTests
from mcp.server.fastmcp import FastMCP
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_validate_physics_lean_backend_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
MATCH = {"score": 21, "matched_terms": ["Lean", "physics"]}
REGISTRY = {ACTION: hub.action_to_dict(hub.build_registry()[ACTION])}
ORDER = ["initialize", "select", "run_action", "advance", "finish"]
LEAF = "tests/physics_lean/run_lean_physics_backend_suite.py"


def original():
    scope = dict(vars(hub))
    exec(
        (
            ROOT / "tests/mcp/fixtures/physics_lean_backend_route_original.py.txt"
        ).read_text(),
        scope,
    )
    return SimpleNamespace(**scope)


def populate(root, mode):
    if mode == "preflight":
        return
    stage(root, mode)
    for path in [LEAF, "tests/physics_lean/run_grounded_sample_thoroughness.py"]:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, target)


def snapshot(document):
    values = {
        row["path"]: (ROOT / row["path"]).read_text()
        for row in document["provenance"]["sources"]
    }
    values[SCHEMA] = (ROOT / SCHEMA).read_text()
    values[DESCRIPTOR] = json.dumps(document)
    return [
        {
            "path": path,
            "content": content,
            "encoding": "text",
            "sha256": hashlib.sha256(content.encode()).hexdigest(),
        }
        for path, content in values.items()
    ]


class NativeSuiteTests(BackendSuiteTests):
    # Reuse genuine suite/controller equivalence and recursion fixtures. The hub
    # contract test belongs to its separate descriptor, not this route.
    test_lunar_registered_workflow = None
    test_registration_policy = None


class RouteTests(unittest.TestCase):
    maxDiff = None

    def test_contract_and_native_cursor(self):
        spec = importlib.util.spec_from_file_location(
            "backend_route_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        document = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(document, module.physics_lean_backend_route_descriptor())
        self.assertEqual(document["id"], "route_validate_physics_lean_backend_workflow")
        self.assertEqual(document["aliases"], [ROUTE])
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 5},
        )
        self.assertEqual(document["policy"]["failure"]["retry"]["max_attempts"], 1)
        self.assertEqual(list(document["operations"]), ORDER)
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        for keep in [False, True]:
            initial = hub.initialize_intent_state()
            state, done = hub.advance_intent_state(
                initial, {"ok": False}, hub.RunContext(keep_going=keep), 1
            )
            self.assertEqual(initial, {"ok": True, "children": []})
            self.assertTrue(done)
            with self.assertRaisesRegex(ValueError, "out of bounds"):
                check_state(state, selecting=True)
            self.assertEqual(
                hub.select_intent_action(initial, selected_match(MATCH)), ACTION
            )
        with self.assertRaises(ValueError):
            checked_registry({ACTION: {}})
        self.assertIsNone(checked_registry(REGISTRY)[ACTION].timeout_seconds)

    def test_service_authority(self):
        async def checks():
            server = FastMCP("backend-route-authority")

            def deny():
                raise PermissionError("read-only")

            register_physics_lean_backend_route_tools(server, deny, lambda p: False)
            args = {
                "action": ACTION,
                "context": vars(hub.RunContext()),
                "registry": REGISTRY,
                "repository_root": None,
            }
            with self.assertRaisesRegex(Exception, "read-only"):
                await server.call_tool(
                    "mathformer_physics_lean_backend_route_run_action", args
                )
            args["context"]["dry_run"] = True
            await server.call_tool(
                "mathformer_physics_lean_backend_route_run_action", args
            )
            paths = FastMCP("backend-route-paths")
            register_physics_lean_backend_route_tools(
                paths, lambda: None, lambda p: False
            )
            args["context"]["dry_run"] = False
            with self.assertRaisesRegex(Exception, "service roots"):
                await paths.call_tool(
                    "mathformer_physics_lean_backend_route_run_action", args
                )

        asyncio.run(checks())

    def test_lunar_mcp_execution(self):
        asyncio.run(self.connected())

    async def connected(self):
        document = yaml.safe_load(CONTRACT.read_text())
        for mode in [
            "preflight",
            "success",
            "compile_failure",
            "boolean_failure",
            "child_failure",
            "compiler_exception",
            "regression_failure",
            "thoroughness_failure",
            "bad_json",
            "launch_error",
        ]:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                populate(root, mode)
                manager = SessionManager()
                failure = None
                async with manager.open(
                    "backend-route",
                    StdioConfig(
                        command=sys.executable,
                        args=[
                            "tests/mcp/fixtures/physics_lean_backend_route_server.py",
                            directory,
                            mode,
                        ],
                        cwd=str(ROOT),
                    ),
                    {
                        "PYTHONPATH": os.pathsep.join(SITES),
                        "PYTHONDONTWRITEBYTECODE": "1",
                    },
                ) as remote:
                    try:
                        tools = [
                            t.model_dump(by_alias=True, exclude_none=True)
                            for t in await remote.tools()
                        ]

                        def compile(doc, inventory=tools):
                            assets = snapshot(doc)
                            workflow = workflow_documents([DESCRIPTOR], assets)[0]
                            self.assertTrue(workflow["validation"]["valid"], workflow)
                            compiled = compile_workflow(
                                "mcp:backend-route", workflow, inventory
                            )
                            return compiled, assets

                        compiled, assets = compile(document)
                        self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                        self.assertEqual(compiled["runtime_status"], "ready")
                        self.assertTrue(compiled["prism_source"])
                        self.assertTrue(compiled["runtime_source"])
                        self.assertEqual(set(compiled["bindings"]), set(ORDER))
                        self.assertFalse(compile(document, [])[0]["runnable"])

                        async def allow():
                            pass

                        async def run(inputs, doc=None):
                            graph, received = (
                                compile(doc) if doc else (compiled, assets)
                            )
                            self.assertTrue(graph["runnable"], graph["diagnostics"])
                            return await execute(graph, received, inputs, remote, allow)

                        base = {
                            "context": vars(hub.RunContext()),
                            "match": MATCH,
                            "registry": REGISTRY,
                            "repository_root": directory,
                        }
                        variants = (
                            [
                                (True, False, False),
                                (True, True, True),
                                (False, False, False),
                                (False, False, True),
                            ]
                            if mode == "success"
                            else [(False, False, False)]
                        )
                        prior_calls = 0
                        for dry, allow_mutating, keep in variants:
                            inputs = deepcopy(base)
                            inputs["context"].update(
                                dry_run=dry,
                                allow_mutating=allow_mutating,
                                keep_going=keep,
                            )
                            for output in [
                                "backend_suite",
                                "derivation_completeness_regression",
                                "grounded_sample_thoroughness",
                            ]:
                                shutil.rmtree(
                                    root / "artifacts/physics_lean" / output,
                                    ignore_errors=True,
                                )
                            result = await run(inputs)
                            # Run the original selected controller against the identical
                            # native scripts and compiler fixture, never a fake action.
                            boundary = SimpleNamespace(
                                subprocess=__import__("subprocess")
                            )
                            ledger = install(boundary, root, mode)
                            native_run = boundary.subprocess.run

                            def invoke(argv, **kwargs):
                                if mode == "launch_error":
                                    raise OSError("fixture launch failed")
                                return native_run(argv, **kwargs)

                            boundary.subprocess.run = invoke
                            with patch.object(hub, "subprocess", boundary.subprocess):
                                if mode == "launch_error":
                                    with self.assertRaisesRegex(
                                        OSError, "launch failed"
                                    ):
                                        original().run_intent_match(
                                            selected_match(MATCH),
                                            checked_registry(REGISTRY),
                                            hub.RunContext(**inputs["context"]),
                                            repository_root=root,
                                        )
                                    self.assertEqual(result["status"], "failed", result)
                                    self.assertIsNone(result["outputs"])
                                    self.assertEqual(
                                        result["calls"][-1]["operation"], "run_action"
                                    )
                                    continue
                                # Restore the same initial output history for the oracle.
                                for output in [
                                    "backend_suite",
                                    "derivation_completeness_regression",
                                    "grounded_sample_thoroughness",
                                ]:
                                    shutil.rmtree(
                                        root / "artifacts/physics_lean" / output,
                                        ignore_errors=True,
                                    )
                                expected = original().run_intent_match(
                                    selected_match(MATCH),
                                    checked_registry(REGISTRY),
                                    hub.RunContext(**inputs["context"]),
                                    repository_root=root,
                                )
                            self.assertEqual(
                                result["status"], "accepted", result.get("calls")
                            )
                            actual = result["outputs"]["result"]
                            self.assertEqual(actual, expected)
                            observed_calls = (await remote.call("fixture_ledger", {}))[
                                "calls"
                            ]
                            self.assertEqual(observed_calls[prior_calls:], ledger)
                            prior_calls = len(observed_calls)
                            self.assertEqual(
                                [c["operation"] for c in result["calls"]], ORDER
                            )
                            self.assertEqual(actual["route"], expected["route"])
                            self.assertEqual(len(actual["children"]), 1)
                            child = actual["children"][0]
                            oracle = expected["children"][0]
                            for key in [
                                "action",
                                "argv",
                                "cwd",
                                "dry_run",
                                "preflight_errors",
                                "returncode",
                                "stdout",
                                "stderr",
                            ]:
                                self.assertEqual(child.get(key), oracle.get(key), key)
                            self.assertEqual(actual["ok"], child["ok"])
                            self.assertEqual(
                                actual["status"],
                                (
                                    "intent_run_completed"
                                    if child["ok"]
                                    else "intent_run_failed"
                                ),
                            )
                            self.assertTrue(result["runtime"]["effect_records"])
                            self.assertTrue(result["replay_artifacts"])
                            if mode == "preflight":
                                self.assertTrue(child["preflight_errors"])
                                self.assertNotIn("returncode", child)
                            elif dry:
                                self.assertEqual(child["status"], "dry_run")
                            elif mode in [
                                "success",
                                "compile_failure",
                                "boolean_failure",
                            ]:
                                report = json.loads(child["stdout"])
                                self.assertEqual(report["ok"], mode == "success")
                                self.assertEqual(report["artifact_status"], "candidate")
                                self.assertFalse(report["release_ok"])
                                self.assertEqual(len(report["adversarial"]["cases"]), 5)
                                self.assertEqual(
                                    child["returncode"], 0 if report["ok"] else 1
                                )
                                if mode == "success":
                                    self.assertEqual(
                                        child["status"], "undeclared_writes"
                                    )
                                    self.assertFalse(child["write_audit"]["ok"])
                            else:
                                self.assertEqual(child["returncode"], 1)
                                self.assertEqual(child["stdout"], "")
                        calls = (await remote.call("fixture_ledger", {}))["calls"]
                        if mode not in ["preflight", "launch_error"]:
                            self.assertEqual(calls[0], [sys.executable, LEAF, "--json"])
                            recursion = [
                                c
                                for c in calls
                                if "control_recursive_repair_loop.py" in " ".join(c)
                            ]
                            if mode == "success":
                                self.assertEqual(len(recursion), 2)
                                self.assertEqual(
                                    recursion[0][-6:-2],
                                    ["--iteration", "1", "--max-iterations", "6"],
                                )
                        if mode != "preflight":
                            continue
                        # Dry-run needs a staged tree; no compiler runs for these bounds.
                        populate(root, "success")
                        base["context"]["dry_run"] = True
                        for limit in [1, 3, 4]:
                            changed = deepcopy(document)
                            changed["policy"]["limits"]["max_operation_calls"] = limit
                            result = await run(base, changed)
                            self.assertEqual(result["status"], "failed")
                            self.assertIsNone(result["outputs"])
                            self.assertEqual(
                                sum(
                                    bool(c.get("transport_call_performed"))
                                    for c in result["calls"]
                                ),
                                limit,
                            )
                        changed = deepcopy(document)
                        changed["flow"]["steps"][1]["until"] = {"literal": False}
                        result = await run(base, changed)
                        self.assertEqual(result["status"], "failed")
                        self.assertEqual(
                            [c["operation"] for c in result["calls"]], ORDER[:-1]
                        )
                        forged = deepcopy(base)
                        forged["registry"][ACTION]["command"] = ["forged"]
                        result = await run(forged)
                        self.assertEqual(result["status"], "failed")
                        self.assertEqual(result["calls"][-1]["operation"], "run_action")
                    except Exception as exc:
                        failure = exc
                self.assertFalse(manager.active)
                if failure is not None:
                    raise failure


if __name__ == "__main__":
    # Load only the selected classes, not the imported base's other contract.
    suite = unittest.TestSuite(
        unittest.defaultTestLoader.loadTestsFromTestCase(c)
        for c in [NativeSuiteTests, RouteTests]
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
