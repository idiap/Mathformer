#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Offline native route, registered MCP ports and actual Lunar/PRISM runtime."""

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
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT / "tests/mcp/fixtures"),
]
SITES = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
sys.path.extend(SITES)

import asyncio
from contextlib import redirect_stdout
from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib.util
from io import StringIO
import json
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import yaml

import mathformer as hub
from physics_isabelle_route_tools import (
    ACTION,
    ROUTE,
    selected_match,
    checked_registry,
    check_state,
    register_physics_isabelle_route_tools,
)
from physics_isabelle_route_tree import LEAF, SOURCES, ARTIFACTS, CASES, populate
from reasoning_route_compiler import install
from mcp.server.fastmcp import FastMCP
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_formalize_physics_isabelle_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
MATCH = {"score": 19, "matched_terms": ["physics", "isabelle"]}
REGISTRY = {ACTION: hub.action_to_dict(hub.build_registry()[ACTION])}
ORDER = ["initialize", "select_action", "execute_action", "advance", "finish"]


def original():
    scope = dict(vars(hub))
    exec(
        (
            ROOT / "tests/mcp/fixtures/physics_isabelle_route_original.py.txt"
        ).read_text(),
        scope,
    )
    return SimpleNamespace(**scope)


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


class PhysicsIsabelleRouteTests(unittest.TestCase):
    maxDiff = None

    def test_authored_contract_identity_policies_and_source_digests(self):
        spec = importlib.util.spec_from_file_location(
            "physics_isabelle_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        document = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(module.physics_isabelle_route_descriptor(), document)
        self.assertEqual(document["id"], "route_formalize_physics_isabelle_workflow")
        self.assertEqual(document["aliases"], [ROUTE])
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 5},
        )
        self.assertEqual(document["policy"]["failure"]["retry"]["max_attempts"], 1)
        self.assertEqual(document["policy"]["effects"]["network"], [])
        self.assertEqual(list(document["operations"]), ORDER)
        self.assertTrue(
            any(
                row["path"] == "scripts/mathformer.py"
                and row["selector"] == "run_intent_match"
                for row in document["provenance"]["sources"]
            )
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        item = checked_registry(REGISTRY)[ACTION]
        self.assertEqual(item.command, ("{python}", LEAF))
        self.assertIsNone(item.timeout_seconds)
        self.assertEqual(item.depends_on, ())
        self.assertFalse(item.allows_extra_args)
        self.assertEqual(item.safety, "writes_repo")
        self.assertEqual(selected_match(MATCH).route.action_ids, (ACTION,))
        self.assertEqual(checked_registry({}), {})

    def test_native_controller_history_stopping_and_exhaustion(self):
        oracle = original()
        native, match = checked_registry(REGISTRY), selected_match(MATCH)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # Missing required source produces real preflight failure, no process.
            for actions in [(), (ACTION,), (ACTION, ACTION)]:
                selected = replace(
                    match, route=replace(match.route, action_ids=actions)
                )
                for keep in [False, True]:
                    outputs = [
                        fn(
                            selected,
                            native,
                            hub.RunContext(keep_going=keep),
                            repository_root=root,
                        )
                        for fn in (hub.run_intent_match, oracle.run_intent_match)
                    ]
                    self.assertEqual(*outputs)
                    self.assertEqual(
                        len(outputs[0]["children"]),
                        len(actions) if keep else min(1, len(actions)),
                    )
        for keep in [False, True]:
            initial = hub.initialize_intent_state()
            state, done = hub.advance_intent_state(
                initial, {"ok": False}, hub.RunContext(keep_going=keep), 1
            )
            self.assertEqual(initial, {"ok": True, "children": []})
            self.assertTrue(done)
            check_state(state)
            with self.assertRaises(ValueError):
                check_state(state, selecting=True)
            state, done = hub.advance_intent_state(
                initial, {"ok": False}, hub.RunContext(keep_going=keep), 2
            )
            self.assertEqual(done, not keep)
            state, done = hub.advance_intent_state(
                state, {"ok": True}, hub.RunContext(keep_going=keep), 2
            )
            self.assertEqual(
                state, {"ok": False, "children": [{"ok": False}, {"ok": True}]}
            )
            self.assertTrue(done)

    def test_actual_generator_steps_main_order_output_and_io_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            leaf = populate(root, ROOT)
            self.assertEqual(tuple(leaf.CASES), CASES)
            state = leaf.initialize([])
            self.assertEqual(
                state, {"cursor": 0, "promote_lib": False, "generated": []}
            )
            for cursor, case in enumerate(CASES):
                files = leaf.write_case_at(cursor, state["promote_lib"])
                self.assertIsNone(files["lib_theory"])
                self.assertIsNone(files["lib_root"])
                self.assertIn(
                    "Synthetic source " + case,
                    Path(files["artifact_theory"]).read_text(),
                )
                self.assertIn(
                    'imports Complex_Main "HOL-Analysis.Analysis"',
                    Path(files["artifact_theory"]).read_text(),
                )
                self.assertIn(
                    leaf.CASES[case]["body"], Path(files["artifact_theory"]).read_text()
                )
                self.assertIn(
                    f'session Mathformer_Isabelle_{case} = "HOL-Analysis"',
                    Path(files["artifact_root"]).read_text(),
                )
                prior = deepcopy(state)
                state, done = leaf.advance(state, files)
                self.assertEqual(prior["cursor"], cursor)
                self.assertEqual(len(prior["generated"]), 2 * cursor)
                self.assertEqual(state["cursor"], cursor + 1)
                self.assertFalse(state["promote_lib"])
                self.assertEqual(done, cursor == 7)
            expected = [
                str(ARTIFACTS / case / name)
                for case in CASES
                for name in ("MathformerPhysics.thy", "ROOT")
            ]
            self.assertEqual(state["generated"], expected)
            before = {path: (root / path).read_bytes() for path in expected}
            with (
                patch.object(sys, "argv", [LEAF]),
                redirect_stdout(StringIO()) as output,
            ):
                self.assertEqual(leaf.main(), 0)
            self.assertEqual(output.getvalue().splitlines(), expected)
            self.assertEqual(
                before, {path: (root / path).read_bytes() for path in expected}
            )
            for cursor in [-1, 8]:
                with self.assertRaisesRegex(IndexError, "exhausted"):
                    leaf.write_case_at(cursor, False)
            self.assertFalse((root / "libraries").exists())
        # A read error aborts before the third write, with no final path listing.
        for mode in ["read", "write"]:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                leaf = populate(root, ROOT)
                case = CASES[2]
                if mode == "read":
                    (root / SOURCES / f'{leaf.CASES[case]["rank"]}_{case}.tex').unlink()
                    error = FileNotFoundError
                else:
                    (root / ARTIFACTS / case / "ROOT").mkdir(parents=True)
                    error = IsADirectoryError
                with (
                    patch.object(sys, "argv", [LEAF]),
                    redirect_stdout(StringIO()) as output,
                ):
                    with self.assertRaises(error):
                        leaf.main()
                self.assertEqual(output.getvalue(), "")
                self.assertTrue((root / ARTIFACTS / CASES[1] / "ROOT").exists())
                self.assertFalse((root / ARTIFACTS / CASES[3]).exists())
                self.assertFalse((root / "libraries").exists())

    def test_shared_controller_external_compiler_boundary(self):
        # This route never invokes a compiler. Qualify its shared controller's
        # capture/timeout/launch-error behavior at a separate external boundary.
        native = SimpleNamespace(**vars(hub))
        calls_root = tempfile.TemporaryDirectory()
        self.addCleanup(calls_root.cleanup)
        root = Path(calls_root.name).resolve()
        calls = install(native, root)
        for mode in ["accept", "reject", "timeout", "launch_error"]:
            item = replace(
                hub.build_registry()[ACTION],
                command=("fixture-reasoning-compiler", mode),
                timeout_seconds=13,
            )
            payload = {"argv": list(item.command)}
            with patch.object(hub, "subprocess", native.subprocess):
                if mode == "launch_error":
                    with self.assertRaisesRegex(OSError, "launch failed"):
                        hub.launch_leaf_boundary(item, payload, repository_root=root)
                    continue
                result = hub.launch_leaf_boundary(item, payload, repository_root=root)
                self.assertEqual(result["ok"], mode == "accept")
                self.assertEqual(
                    result["status"], "timeout" if mode == "timeout" else "completed"
                )
                if mode == "timeout":
                    self.assertIsNone(result["returncode"])
                    self.assertEqual(result["timeout_seconds"], 13)
                    self.assertEqual(result["stdout"], "partial")
                else:
                    self.assertEqual(result["returncode"], 7 if mode == "reject" else 0)
                    self.assertEqual(
                        json.loads(result["stdout"])["diagnostics"][0]["code"],
                        "fixture_type_error",
                    )
        self.assertEqual([c["timeout"] for c in calls], [13] * 4)

    def test_service_authority_and_bad_state(self):
        async def checks():
            permissions = {"write": False, "paths": True}

            def authorize():
                if not permissions["write"]:
                    raise PermissionError("service is read-only")

            seen = []

            def path_allowed(path):
                seen.append(path)
                return permissions["paths"]

            server = FastMCP("physics-isabelle-authority")
            register_physics_isabelle_route_tools(server, authorize, path_allowed)
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                args = {
                    "action_id": ACTION,
                    "context": vars(hub.RunContext()),
                    "registry": REGISTRY,
                    "repository_root": directory,
                }
                for write, paths, error in [
                    (False, True, "read-only"),
                    (True, False, "service roots"),
                ]:
                    permissions.update(write=write, paths=paths)
                    with self.assertRaisesRegex(Exception, error):
                        await server.call_tool(
                            "mathformer_physics_isabelle_route_execute_action", args
                        )
                permissions.update(write=True, paths=True)
                await server.call_tool(
                    "mathformer_physics_isabelle_route_execute_action", args
                )
                self.assertIn(root / ARTIFACTS, seen)
                self.assertIn(root / REGISTRY[ACTION]["writes"][0], seen)
                args["context"]["dry_run"] = True
                permissions.update(write=False, paths=False)
                await server.call_tool(
                    "mathformer_physics_isabelle_route_execute_action", args
                )
                for suffix, args in [
                    (
                        "finish",
                        {
                            "state": {"ok": True, "children": []},
                            "match": MATCH,
                            "registry": REGISTRY,
                        },
                    ),
                    (
                        "advance",
                        {
                            "state": {"ok": False, "children": []},
                            "child": {"ok": True},
                            "context": vars(hub.RunContext()),
                        },
                    ),
                ]:
                    with self.assertRaisesRegex(
                        Exception, "exactly one observation|inconsistent"
                    ):
                        await server.call_tool(
                            "mathformer_physics_isabelle_route_" + suffix, args
                        )
                self.assertEqual(list(root.iterdir()), [])

        asyncio.run(checks())

    def test_registered_mcp_real_lunar_prism_execution(self):
        asyncio.run(self.connected())

    async def connected(self):
        manager = SessionManager()
        # Forward only the real copied generator process. Reject every model,
        # compiler or prover process; no simulated source implementation exists.
        server = """import sys, subprocess
sys.path.insert(0, "scripts")
from mcp_server import mcp
run = subprocess.run
def guarded(argv, **kwargs):
    assert argv == [sys.executable, "scripts/generate_formalphysics_extra_isabelle.py"], argv
    assert kwargs["timeout"] is None
    assert str(kwargs["cwd"]) != str(__import__("mathformer").REPO_ROOT)
    return run(argv, **kwargs)
subprocess.run = guarded
mcp.run(transport="stdio")
"""
        failure = None
        async with manager.open(
            "physics-isabelle-route",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {"PYTHONPATH": os.pathsep.join(SITES), "PYTHONDONTWRITEBYTECODE": "1"},
        ) as remote:
            try:
                await self.connected_checks(remote)
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure is not None:
            raise failure

    async def connected_checks(self, remote):
        document = yaml.safe_load(CONTRACT.read_text())
        tools = [
            tool.model_dump(by_alias=True, exclude_none=True)
            for tool in await remote.tools()
        ]

        def compile(doc):
            assets = snapshot(doc)
            workflow = workflow_documents([DESCRIPTOR], assets)[0]
            self.assertTrue(workflow["validation"]["valid"], workflow)
            compiled = compile_workflow("mcp:physics-isabelle-route", workflow, tools)
            self.assertTrue(compiled["runnable"], compiled["diagnostics"])
            self.assertEqual(compiled["runtime_status"], "ready")
            self.assertTrue(compiled["prism_source"])
            self.assertTrue(compiled["runtime_source"])
            self.assertEqual(set(compiled["bindings"]), set(ORDER))
            return compiled, assets

        compiled, assets = compile(document)
        missing = [
            t
            for t in tools
            if t["name"] != "mathformer_physics_isabelle_route_execute_action"
        ]
        self.assertFalse(
            compile_workflow(
                "mcp:physics-isabelle-route",
                workflow_documents([DESCRIPTOR], assets)[0],
                missing,
            )["runnable"]
        )

        async def authorize():
            pass

        async def run(inputs, changed=None):
            graph, received = compile(changed) if changed else (compiled, assets)
            return await execute(graph, received, inputs, remote, authorize)

        for scenario in ["preflight", "generation", "read_error", "write_error"]:
            with (
                self.subTest(scenario=scenario),
                tempfile.TemporaryDirectory() as directory,
            ):
                root = Path(directory).resolve()
                if scenario != "preflight":
                    leaf = populate(root, ROOT)
                    if scenario == "read_error":
                        case = CASES[2]
                        (
                            root / SOURCES / f'{leaf.CASES[case]["rank"]}_{case}.tex'
                        ).unlink()
                    elif scenario == "write_error":
                        (root / ARTIFACTS / CASES[2] / "ROOT").mkdir(parents=True)
                base = {
                    "context": vars(hub.RunContext()),
                    "match": MATCH,
                    "registry": REGISTRY,
                    "repository_root": str(root),
                }
                for allow in [False, True]:
                    for dry in [True, False]:
                        for keep in [False, True]:
                            inputs = deepcopy(base)
                            inputs["context"].update(
                                allow_mutating=allow, dry_run=dry, keep_going=keep
                            )
                            result = await run(inputs)
                            self.assertEqual(result["status"], "accepted", result)
                            output = result["outputs"]["result"]
                            expected = original().run_intent_match(
                                selected_match(MATCH),
                                checked_registry(REGISTRY),
                                hub.RunContext(**inputs["context"]),
                                repository_root=root,
                            )
                            self.assertEqual(output, expected)
                            self.assertEqual(
                                [c["operation"] for c in result["calls"]], ORDER
                            )
                            self.assertEqual(
                                [c["tool"] for c in result["calls"]],
                                [
                                    "mathformer_physics_isabelle_route_" + op
                                    for op in ORDER
                                ],
                            )
                            self.assertEqual(len(output["children"]), 1)
                            self.assertEqual(output["route"]["score"], MATCH["score"])
                            self.assertEqual(
                                output["route"]["matched_terms"], MATCH["matched_terms"]
                            )
                            child = output["children"][0]
                            self.assertEqual(
                                output["ok"], scenario != "preflight" and dry
                            )
                            self.assertEqual(
                                output["status"],
                                (
                                    "intent_run_completed"
                                    if output["ok"]
                                    else "intent_run_failed"
                                ),
                            )
                            if scenario == "preflight" or (not allow and not dry):
                                self.assertTrue(child["preflight_errors"])
                                self.assertNotIn("returncode", child)
                            elif dry:
                                self.assertEqual(child["status"], "dry_run")
                                self.assertNotIn("returncode", child)
                            else:
                                self.assertEqual(child["argv"], [sys.executable, LEAF])
                                self.assertEqual(
                                    child["returncode"],
                                    0 if scenario == "generation" else 1,
                                )
                                self.assertEqual(child["status"], "undeclared_writes")
                                self.assertFalse(child["write_audit"]["ok"])
                                self.assertEqual(
                                    child["write_audit"]["declared_paths"], []
                                )
                                count = (
                                    16
                                    if scenario == "generation"
                                    else 4 if scenario == "read_error" else 5
                                )
                                self.assertEqual(
                                    len(child["write_audit"]["unexpected_paths"]), count
                                )
                                if scenario == "generation":
                                    paths = [
                                        str(ARTIFACTS / case / name)
                                        for case in CASES
                                        for name in ("MathformerPhysics.thy", "ROOT")
                                    ]
                                    self.assertEqual(
                                        child["stdout"].splitlines(), paths
                                    )
                                    self.assertTrue(
                                        all((root / path).exists() for path in paths)
                                    )
                                else:
                                    self.assertEqual(child["stdout"], "")
                                    self.assertIn(
                                        (
                                            "FileNotFoundError"
                                            if scenario == "read_error"
                                            else "IsADirectoryError"
                                        ),
                                        child["stderr"],
                                    )
                                    self.assertFalse(
                                        (root / ARTIFACTS / CASES[3]).exists()
                                    )
                            self.assertFalse((root / "libraries").exists())
                            self.assertTrue(result["runtime"]["effect_records"])
                            self.assertTrue(result["runtime"]["provenance"])
                            self.assertTrue(result["replay_artifacts"])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            populate(root, ROOT)
            base = {
                "context": vars(hub.RunContext(dry_run=True)),
                "match": MATCH,
                "registry": REGISTRY,
                "repository_root": str(root),
            }
            for forged in ["registry", "cursor", "missing_registry"]:
                inputs, changed = deepcopy(base), None
                if forged == "registry":
                    inputs["registry"][ACTION]["command"] = ["forged"]
                elif forged == "missing_registry":
                    inputs["registry"] = {}
                    with self.assertRaises(KeyError):
                        original().run_intent_match(
                            selected_match(MATCH),
                            {},
                            hub.RunContext(dry_run=True),
                            repository_root=root,
                        )
                else:
                    changed = deepcopy(document)
                    changed["flow"]["steps"][1]["body"]["steps"][0]["arguments"][
                        "state"
                    ] = {"literal": {"ok": True, "children": [{"ok": True}]}}
                result = await run(inputs, changed)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(
                    result["calls"][-1]["operation"],
                    (
                        "execute_action"
                        if forged == "registry"
                        else (
                            "finish"
                            if forged == "missing_registry"
                            else "select_action"
                        )
                    ),
                )
            unknown = await remote.call(
                "mathformer_physics_isabelle_route_execute_action",
                {
                    "action_id": ACTION,
                    "context": base["context"],
                    "registry": {},
                    "repository_root": str(root),
                },
            )
            self.assertEqual(
                unknown,
                {
                    "child": {
                        "ok": False,
                        "status": "unknown_action",
                        "action_id": ACTION,
                    }
                },
            )
            for limit in [1, 3, 4]:
                changed = deepcopy(document)
                changed["policy"]["limits"]["max_operation_calls"] = limit
                result = await run(base, changed)
                self.assertEqual(result["status"], "failed")
                self.assertIsNone(result["outputs"])
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in result["calls"]
                    ),
                    limit,
                )
            changed = deepcopy(document)
            changed["flow"]["steps"][1]["until"] = {"literal": False}
            result = await run(base, changed)
            self.assertEqual(result["status"], "failed")
            self.assertIsNone(result["outputs"])
            self.assertEqual([c["operation"] for c in result["calls"]], ORDER[:-1])
            base["repository_root"] = None
            result = await run(base)
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


if __name__ == "__main__":
    program = unittest.main(verbosity=2, exit=False)
    result = program.result
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
