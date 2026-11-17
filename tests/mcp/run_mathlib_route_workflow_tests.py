#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Offline registered mathlib route through the real Lunar/PRISM runtime."""

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
    str(ROOT),
]
SITES = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
sys.path.extend(SITES)

import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib.util
import json
import tempfile
import unittest
import yaml

import mathformer as hub
from mathlib_route_tools import (
    ACTION,
    ROUTE,
    selected_match,
    checked_registry,
    check_state,
    register_mathlib_route_tools,
)
from mathlib_route_tree import LEAF, matrix, populate, clean, stable
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute, ExecutionRejected

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_mathlib_grounding_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
MATCH = {
    "route": {"route_id": ROUTE, "action_ids": [ACTION]},
    "score": 19,
    "matched_terms": ["mathlib", "grounding"],
}
REGISTRY = {ACTION: hub.action_to_dict(hub.build_registry()[ACTION])}
ORDER = ["initialize", "select", "execute", "advance", "finish"]


def original():
    scope = dict(vars(hub))
    exec((ROOT / "tests/mcp/fixtures/mathlib_route_original.py.txt").read_text(), scope)
    return scope["run_intent_match"]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def snapshot(document):
    values = {
        row["path"]: (ROOT / row["path"]).read_text()
        for row in document["provenance"]["sources"]
    }
    values[SCHEMA] = (ROOT / SCHEMA).read_text()
    values[DESCRIPTOR] = json.dumps(document)
    return [
        {
            "path": p,
            "content": v,
            "encoding": "text",
            "sha256": hashlib.sha256(v.encode()).hexdigest(),
        }
        for p, v in values.items()
    ]


class MathlibRouteTests(unittest.TestCase):
    maxDiff = None

    def test_authored_generator_identity_policy_provenance(self):
        normalizer = load(
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
            "mathlib_normalizer",
        )
        document = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(normalizer.mathlib_route_descriptor(), document)
        # Exercise this route's generator without requiring unrelated in-progress
        # repository descriptors to have globally unique aliases.
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(document["aliases"], [ROUTE])
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 5},
        )
        self.assertEqual(document["policy"]["failure"]["retry"]["max_attempts"], 1)
        self.assertEqual(document["flow"]["steps"][1]["max_iterations"], 1)
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        self.assertTrue(
            any(
                s["path"] == "scripts/mathformer.py"
                and s["selector"] == "run_intent_match"
                for s in document["provenance"]["sources"]
            )
        )

    def test_shared_source_state_and_original_early_stop(self):
        native, match = checked_registry(REGISTRY), selected_match(MATCH)
        with tempfile.TemporaryDirectory() as directory:
            for actions in [(), (ACTION,), (ACTION, ACTION)]:
                custom = replace(match, route=replace(match.route, action_ids=actions))
                for keep in [False, True]:
                    results = [
                        function(
                            custom,
                            native,
                            hub.RunContext(keep_going=keep),
                            repository_root=Path(directory) / "absent",
                        )
                        for function in [original(), hub.run_intent_match]
                    ]
                    self.assertEqual(*results)
                    self.assertEqual(
                        len(results[0]["children"]),
                        len(actions) if keep else min(1, len(actions)),
                    )
        for keep in [False, True]:
            initial = hub.initialize_intent_state()
            failed = {"ok": False, "status": "fixture"}
            state, done = hub.advance_intent_state(
                initial, failed, hub.RunContext(keep_going=keep), 1
            )
            self.assertEqual(initial, {"ok": True, "children": []})
            self.assertEqual(state, {"ok": False, "children": [failed]})
            self.assertTrue(done)
            check_state(state)
            with self.assertRaises(ValueError):
                check_state(state, selecting=True)
            state, done = hub.advance_intent_state(
                initial, failed, hub.RunContext(keep_going=keep), 2
            )
            self.assertEqual(done, not keep)
            state, done = hub.advance_intent_state(
                state, {"ok": True}, hub.RunContext(keep_going=keep), 2
            )
            self.assertFalse(state["ok"])
            self.assertEqual(state["children"], [failed, {"ok": True}])
            self.assertTrue(done)

    def test_actual_delegated_cursor_exhaustion_and_history(self):
        # The generic fixture substitutes only external dependency/compiler
        # boundaries, leaving every selected native runner step intact.
        from rfde_family_boundary import install

        native = load(ROOT / LEAF, "mathlib_cursor")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            populate(root, ROOT, matrix(["fail", "pass"] * 6))
            install(native, root)
            args = native.parse_args(["--module-family", "mathlib", "--json"])
            self.assertFalse(native.enter_checks(args))
            state = native.prepare_checks(args)
            self.assertEqual(state["index"], 0)
            self.assertEqual(state["results"], [])
            self.assertEqual(
                len(state["selected"]), 12
            )  # no imported family-contract cap
            with self.assertRaises(ValueError):
                native.finalize_checks(state, args)
            while native.checks_pending(state):
                prior = deepcopy(state)
                state = native.advance_check(state, args)
                self.assertEqual(state["index"], prior["index"] + 1)
                self.assertEqual(state["selected"], prior["selected"])
                self.assertEqual(state["matrix"], prior["matrix"])
                self.assertEqual(state["results"][:-1], prior["results"])
            with self.assertRaises(ValueError):
                native.advance_check(state, args)
            report = native.finalize_checks(state, args)
            self.assertEqual(
                report["summary"],
                {"pass": 6, "fail": 6, "skip": 0, "warn": 0, "total": 12},
            )
            self.assertFalse(report["ok"])
            self.assertEqual(report["schema_errors"], [])

    def test_service_authority_and_state_guards(self):
        async def checks():
            from mcp.server.fastmcp import FastMCP

            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)

                def deny():
                    raise ValueError("service is read-only")

                for authorize, allowed, message in [
                    (deny, lambda path: True, "read-only"),
                    (
                        lambda: None,
                        lambda path: False,
                        "outside configured service roots",
                    ),
                ]:
                    server = FastMCP("authority fixture")
                    register_mathlib_route_tools(server, authorize, allowed)
                    ports = dict(
                        action_id=ACTION,
                        registry=REGISTRY,
                        context=vars(hub.RunContext()),
                        repository_root=str(root),
                    )
                    with self.assertRaisesRegex(Exception, message):
                        await server.call_tool(
                            "mathformer_mathlib_route_execute", ports
                        )
                    ports["context"]["dry_run"] = True
                    await server.call_tool("mathformer_mathlib_route_execute", ports)
                for tool, arguments in [
                    (
                        "finish",
                        dict(
                            state={"ok": True, "children": []},
                            match=MATCH,
                            registry=REGISTRY,
                        ),
                    ),
                    (
                        "advance",
                        dict(
                            state={"ok": False, "children": []},
                            child={"ok": True},
                            context=vars(hub.RunContext()),
                            action_count=1,
                        ),
                    ),
                    (
                        "advance",
                        dict(
                            state={"ok": True, "children": []},
                            child={"ok": True},
                            context=vars(hub.RunContext()),
                            action_count=2,
                        ),
                    ),
                ]:
                    with self.assertRaises(Exception):
                        await server.call_tool(
                            "mathformer_mathlib_route_" + tool, arguments
                        )
                self.assertEqual(list(root.iterdir()), [])

        asyncio.run(checks())

    def test_registered_mcp_lunar_compile_and_execute(self):
        asyncio.run(self.connected())

    async def connected(self):
        document = yaml.safe_load(CONTRACT.read_text())
        manager = SessionManager()
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            server = (
                "import sys;sys.path[:0]="
                + repr([str(ROOT / "scripts"), str(ROOT / "tests/mcp/fixtures")])
                + ";from mathlib_route_service import serve;serve("
                + repr(str(base))
                + ")"
            )
            env = {
                "PYTHONPATH": os.pathsep.join(
                    [str(ROOT / "tests/mcp/fixtures/mathlib_route_boundary"), *SITES]
                ),
                "PYTHONDONTWRITEBYTECODE": "1",
            }
            failure = None
            async with manager.open(
                "mathlib-route",
                StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
                env,
            ) as remote:
                try:
                    tools = [
                        tool.model_dump(by_alias=True, exclude_none=True)
                        for tool in await remote.tools()
                    ]

                    def compile(doc):
                        assets = snapshot(doc)
                        workflow = workflow_documents([DESCRIPTOR], assets)[0]
                        self.assertTrue(workflow["validation"]["valid"], workflow)
                        compiled = compile_workflow(
                            "mcp:mathlib-route", workflow, tools
                        )
                        self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                        self.assertEqual(compiled["runtime_status"], "ready")
                        self.assertTrue(compiled["prism_source"])
                        self.assertTrue(compiled["runtime_source"])
                        self.assertEqual(set(compiled["bindings"]), set(ORDER))
                        return compiled, assets

                    compiled, assets = compile(document)
                    absent = [
                        tool
                        for tool in tools
                        if tool["name"] != "mathformer_mathlib_route_execute"
                    ]
                    self.assertFalse(
                        compile_workflow(
                            "mcp:mathlib-route",
                            workflow_documents([DESCRIPTOR], assets)[0],
                            absent,
                        )["runnable"]
                    )

                    async def authorize():
                        pass

                    async def run(inputs, changed=None):
                        graph, received = (
                            compile(changed) if changed else (compiled, assets)
                        )
                        return await execute(graph, received, inputs, remote, authorize)

                    selected = matrix(["pass", "fail", "pass"])
                    selected["tests"][1]["module_family"] = "atp"
                    expected_exit = matrix(["large", "fail", "pass"])
                    expected_exit["tests"][1]["expected_exit"] = 7
                    del expected_exit["tests"][2]["timeout_seconds"]
                    scenarios = [
                        (matrix(["pass", "pass"]), True, True),
                        (matrix(["fail", "timeout", "pass"]), False, True),
                        (matrix(["missing", "pass"]), True, True),
                        (matrix(["missing"]), True, True),
                        (matrix(["write", "pass"]), False, True),
                        (matrix(["crash", "pass"]), False, True),
                        (matrix(["pass"], "atp"), True, True),
                        (matrix(["pass"]), False, False),
                        (selected, True, True),
                        (expected_exit, True, True),
                        (matrix(["pass"] * 12), True, True),
                    ]
                    for index, (data, success, ready) in enumerate(scenarios):
                        root = base / f"case-{index}"
                        populate(root, ROOT, data, ready=ready)
                        ports = dict(
                            context=vars(hub.RunContext()),
                            match=MATCH,
                            registry=REGISTRY,
                            repository_root=str(root),
                        )
                        for keep in [False, True]:
                            ports["context"]["keep_going"] = keep
                            for dry in [True, False]:
                                with self.subTest(case=index, keep=keep, dry=dry):
                                    clean(root)
                                    ports["context"]["dry_run"] = dry
                                    result = await run(ports)
                                    self.assertEqual(
                                        result["status"], "accepted", result
                                    )
                                    self.assertEqual(
                                        [c["operation"] for c in result["calls"]], ORDER
                                    )
                                    envelope = result["outputs"]["result"]
                                    self.assertEqual(len(envelope["children"]), 1)
                                    self.assertEqual(
                                        envelope["route"]["score"], MATCH["score"]
                                    )
                                    self.assertEqual(
                                        envelope["route"]["matched_terms"],
                                        MATCH["matched_terms"],
                                    )
                                    ok = ready if dry else success
                                    self.assertEqual(envelope["ok"], ok, envelope)
                                    self.assertEqual(
                                        envelope["status"],
                                        (
                                            "intent_run_completed"
                                            if ok
                                            else "intent_run_failed"
                                        ),
                                    )
                                    child = envelope["children"][0]
                                    if not ready:
                                        self.assertTrue(child["preflight_errors"])
                                        self.assertNotIn("returncode", child)
                                    elif dry:
                                        self.assertEqual(child["status"], "dry_run")
                                        self.assertNotIn("returncode", child)
                                    else:
                                        calls = [
                                            json.loads(line)
                                            for line in root.with_suffix(".calls.jsonl")
                                            .read_text()
                                            .splitlines()
                                        ]
                                        self.assertEqual(
                                            calls[0],
                                            {
                                                "argv": [
                                                    sys.executable,
                                                    LEAF,
                                                    "--module-family",
                                                    "mathlib",
                                                    "--json",
                                                ],
                                                "timeout": 900,
                                            },
                                        )
                                        compiler = [
                                            c
                                            for c in calls
                                            if c["argv"][0] == "fixture-compiler"
                                        ]
                                        rows = [
                                            r
                                            for r in data["tests"]
                                            if r["module_family"] == "mathlib"
                                        ]
                                        executed = [
                                            r
                                            for r in rows
                                            if "optional_dependency" not in r
                                        ]
                                        if any(
                                            r["command"][1] == "crash" for r in rows
                                        ):
                                            self.assertEqual(child["returncode"], 1)
                                            self.assertEqual(child["stdout"], "")
                                            self.assertIn(
                                                "fixture compiler launch failed",
                                                child["stderr"],
                                            )
                                            self.assertEqual(len(compiler), 1)
                                            self.assertFalse(
                                                (
                                                    root
                                                    / "artifacts/test_program/deterministic_tests.json"
                                                ).exists()
                                            )
                                        else:
                                            self.assertEqual(
                                                compiler,
                                                [
                                                    {
                                                        "argv": r["command"],
                                                        "timeout": r.get(
                                                            "timeout_seconds", 120
                                                        ),
                                                    }
                                                    for r in executed
                                                ],
                                            )
                                            report = json.loads(child["stdout"])
                                            self.assertEqual(
                                                report["families"], ["mathlib"]
                                            )
                                            self.assertEqual(
                                                report["profile"], "workstation"
                                            )
                                            self.assertEqual(
                                                [
                                                    r["check_id"]
                                                    for r in report["results"]
                                                ],
                                                [r["id"] for r in rows],
                                            )
                                            self.assertEqual(
                                                report["schema_errors"], []
                                            )
                                            self.assertEqual(
                                                report["summary"]["total"], len(rows)
                                            )
                                            self.assertEqual(
                                                child["returncode"], 0 if success else 3
                                            )
                                            self.assertEqual(
                                                json.loads(
                                                    (
                                                        root
                                                        / "artifacts/test_program/deterministic_tests.json"
                                                    ).read_text()
                                                ),
                                                report,
                                            )
                                            self.assertTrue(
                                                (
                                                    root / report["dependency_map"]
                                                ).exists()
                                            )
                                            if not rows:
                                                self.assertEqual(
                                                    report["capability_ledger"][
                                                        "families"
                                                    ]["mathlib"]["state"],
                                                    "untested",
                                                )
                                            if data == matrix(["missing"]):
                                                self.assertEqual(
                                                    report["summary"]["skip"], 1
                                                )
                                                self.assertFalse(
                                                    report["capability_ledger"][
                                                        "strict_ready"
                                                    ]
                                                )
                                            if data == matrix(
                                                ["fail", "timeout", "pass"]
                                            ):
                                                self.assertEqual(
                                                    [
                                                        r["status"]
                                                        for r in report["results"]
                                                    ],
                                                    ["fail", "fail", "pass"],
                                                )
                                                self.assertEqual(
                                                    report["results"][1]["stdout"],
                                                    "partial compile",
                                                )
                                                self.assertEqual(
                                                    report["results"][1]["stderr"],
                                                    "timeout after 31s",
                                                )
                                            if data == expected_exit:
                                                self.assertLess(
                                                    len(report["results"][0]["stdout"]),
                                                    5000,
                                                )
                                                self.assertEqual(
                                                    report["results"][1]["returncode"],
                                                    7,
                                                )
                                        if any(
                                            r["command"][1] == "write" for r in rows
                                        ):
                                            self.assertEqual(
                                                child["status"], "undeclared_writes"
                                            )
                                            self.assertEqual(
                                                child["write_audit"][
                                                    "unexpected_paths"
                                                ],
                                                ["undeclared.txt"],
                                            )
                                        else:
                                            self.assertTrue(child["write_audit"]["ok"])
                                    if dry or not ready:
                                        self.assertFalse(
                                            root.with_suffix(".calls.jsonl").exists()
                                        )
                                    self.assertTrue(result["runtime"]["effect_records"])
                                    self.assertTrue(result["runtime"]["provenance"])
                                    self.assertTrue(result["replay_artifacts"])
                        # Compare original controller on identical inputs and clean
                        # mounts; only native timing/run identifiers are normalized.
                        if index in [0, 1, 2, 4, 6, 7]:
                            ports["context"] = vars(hub.RunContext())
                            clean(root)
                            expected = await remote.call(
                                "fixture_mathlib_original", ports
                            )
                            clean(root)
                            actual = await run(ports)
                            self.assertEqual(
                                stable(actual["outputs"]["result"]), stable(expected)
                            )

                    root = base / "guards"
                    populate(root, ROOT, matrix(["pass"]))
                    ports = dict(
                        context=vars(hub.RunContext(dry_run=True)),
                        match=MATCH,
                        registry=REGISTRY,
                        repository_root=str(root),
                    )
                    for key in ["registry", "match", "cursor"]:
                        supplied, changed = deepcopy(ports), None
                        if key == "registry":
                            supplied["registry"][ACTION]["command"] = ["injected"]
                        elif key == "match":
                            supplied["match"]["route"]["title"] = "injected"
                        else:
                            changed = deepcopy(document)
                            changed["flow"]["steps"][1]["body"]["steps"][0][
                                "arguments"
                            ]["state"] = {
                                "literal": {"ok": True, "children": [{"ok": True}]}
                            }
                        result = await run(supplied, changed)
                        self.assertEqual(result["status"], "failed")
                        self.assertIsNone(result["outputs"])
                        self.assertEqual(
                            result["calls"][-1]["operation"],
                            "execute" if key == "registry" else "select",
                        )
                    supplied = {**ports, "registry": {}}
                    result = await run(supplied)
                    # Native run_action returns failure data, but native finish
                    # raises KeyError when enriching an absent registry action.
                    self.assertEqual(result["status"], "failed")
                    self.assertIsNone(result["outputs"])
                    self.assertEqual([c["operation"] for c in result["calls"]], ORDER)
                    child = await remote.call(
                        "mathformer_mathlib_route_execute",
                        dict(
                            action_id=ACTION,
                            registry={},
                            context=ports["context"],
                            repository_root=str(root),
                        ),
                    )
                    self.assertEqual(
                        child,
                        {
                            "child": {
                                "ok": False,
                                "status": "unknown_action",
                                "action_id": ACTION,
                            }
                        },
                    )
                    with self.assertRaises(MCPConnectionError):
                        await remote.call("fixture_mathlib_original", supplied)
                    for limit in [1, 3, 4]:
                        changed = deepcopy(document)
                        changed["policy"]["limits"]["max_operation_calls"] = limit
                        result = await run(ports, changed)
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
                    result = await run(ports, changed)
                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]], ORDER[:-1]
                    )
                    self.assertIsNone(result["outputs"])
                    self.assertFalse(root.with_suffix(".calls.jsonl").exists())
                    with self.assertRaises(ExecutionRejected):
                        await run(
                            {
                                **ports,
                                "match": {
                                    **MATCH,
                                    "route": {
                                        "route_id": ROUTE,
                                        "action_ids": [ACTION, ACTION],
                                    },
                                },
                            }
                        )
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_mathlib_route_select",
                            dict(
                                state={"ok": True, "children": [{"ok": True}]},
                                match=MATCH,
                            ),
                        )
                except Exception as error:
                    failure = error
            if failure:
                raise failure
        self.assertFalse(manager.active)


if __name__ == "__main__":
    program = unittest.main(verbosity=2, exit=False)
    result = program.result
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
