#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Offline selected Lean route: native parity, real MCP and Lunar/PRISM runtime."""

from tempfile import gettempdir

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
    str(FIXTURES),
    str(ROOT),
]
sys.path.extend(SITES)

import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib.util
import json
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import yaml

import mathformer as hub
from lean_route_tools import (
    ACTION,
    ROUTE,
    checked_registry,
    selected_match,
    check_state,
    state_wire,
    register_lean_route_tools,
)
from lean_route_compiler import install, populate
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute, ExecutionRejected

BASE = "skills/control/workflow-contract-validator/references/normalized-workflows/"
DESCRIPTOR = BASE + "route/route_formalize_lean_workflow/workflow.yaml"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
MATCH = {
    "route": {"route_id": ROUTE, "action_ids": [ACTION]},
    "score": 21,
    "matched_terms": ["lean", "mathlib"],
}
REGISTRY = {ACTION: hub.action_to_dict(hub.build_registry()[ACTION])}
ORDER = ["initialize", "select", "run_action", "advance", "finish"]
TOOLS = [
    "mathformer_lean_route_" + ("run" if name == "run_action" else name)
    for name in ORDER
]


def original():
    scope = dict(vars(hub))
    exec((FIXTURES / "lean_route_original.py.txt").read_text(), scope)
    return SimpleNamespace(**scope)


def snapshot(document):
    values = {
        row["path"]: (ROOT / row["path"]).read_text()
        for row in document["provenance"]["sources"]
    }
    for schema in ["hub-interface.schema.json", "lean-build-interface.schema.json"]:
        values[BASE + schema] = (ROOT / (BASE + schema)).read_text()
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


def ledger(root):
    path = root.parent / "compiler-calls.jsonl"
    return (
        [json.loads(line) for line in path.read_text().splitlines()]
        if path.exists()
        else []
    )


class LeanRouteTests(unittest.TestCase):
    maxDiff = None

    def test_authored_generator_identity_policies_and_provenance(self):
        spec = importlib.util.spec_from_file_location(
            "lean_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        document = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(module.lean_route_descriptor(), document)
        self.assertEqual(document["id"], "route_formalize_lean_workflow")
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
        self.assertEqual(
            document["policy"]["effects"]["filesystem"]["write"],
            [".lake/", "artifacts/workflow_hub/"],
        )
        self.assertEqual(document["flow"]["steps"][1]["max_iterations"], 1)
        self.assertEqual(document["flow"]["steps"][1]["on_exhausted"], "fail")
        self.assertTrue(
            any(
                r["path"] == "scripts/mathformer.py"
                and r["selector"] == "run_intent_match"
                for r in document["provenance"]["sources"]
            )
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        # Every schema-advertised partial registry projection resolves source-owned code.
        fields = document["types"]["Registry"]["schema"]["properties"][ACTION][
            "required"
        ]
        minimal = {ACTION: {key: REGISTRY[ACTION][key] for key in fields}}
        self.assertEqual(checked_registry(minimal), checked_registry(REGISTRY))

    def test_native_parity_stopping_and_sticky_state(self):
        match, native = selected_match(MATCH), checked_registry(REGISTRY)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve() / "repo"
            with patch.object(hub, "subprocess"), patch.object(hub, "shutil"):
                install(hub, root)
                oracle = original()
                for mode in [
                    "success",
                    "reject",
                    "missing",
                    "timeout",
                    "write",
                    "crash",
                ]:
                    for ready in [True, False]:
                        for dry in [True, False]:
                            for keep in [True, False]:
                                observed = []
                                for run in [
                                    oracle.run_intent_match,
                                    hub.run_intent_match,
                                ]:
                                    populate(root, mode, ready)
                                    try:
                                        value = state_wire(
                                            run(
                                                match,
                                                native,
                                                hub.RunContext(
                                                    dry_run=dry, keep_going=keep
                                                ),
                                                repository_root=root,
                                            )
                                        )
                                    except OSError as error:
                                        value = ("launch_error", str(error))
                                    observed.append((value, ledger(root)))
                                self.assertEqual(*observed)
                                self.assertEqual(
                                    len(observed[0][1]),
                                    int(ready and not dry and mode != "missing"),
                                )
                # Exercise native empty, early-stop and keep-going behavior without launching.
                populate(root, ready=False)
                for actions in [(), (ACTION,), (ACTION, ACTION)]:
                    custom = replace(
                        match, route=replace(match.route, action_ids=actions)
                    )
                    for keep in [False, True]:
                        context = hub.RunContext(keep_going=keep)
                        actual = hub.run_intent_match(
                            custom, native, context, repository_root=root
                        )
                        self.assertEqual(
                            actual,
                            oracle.run_intent_match(
                                custom, native, context, repository_root=root
                            ),
                        )
                        self.assertEqual(
                            len(actual["children"]),
                            len(actions) if keep else min(len(actions), 1),
                        )
        for keep in [False, True]:
            initial = hub.initialize_intent_state()
            state, done = hub.advance_intent_state(
                initial, {"ok": False}, hub.RunContext(keep_going=keep), 1
            )
            self.assertEqual(initial, {"ok": True, "children": []})
            self.assertTrue(done)
            check_state(state)
            with self.assertRaisesRegex(ValueError, "bounds"):
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

    def test_registered_service_authority(self):
        asyncio.run(self.authority())

    async def authority(self):
        from mcp.server.fastmcp import FastMCP

        def deny():
            raise ValueError("read-only service")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve() / "repo"
            populate(root)
            with patch.object(hub, "subprocess"), patch.object(hub, "shutil"):
                install(hub, root)
                for authorize, allowed, message in [
                    (deny, lambda p: True, "read-only"),
                    (lambda: None, lambda p: False, "outside configured service roots"),
                ]:
                    server = FastMCP("lean authority")
                    register_lean_route_tools(server, authorize, allowed)
                    arguments = dict(
                        action_id=ACTION,
                        registry=REGISTRY,
                        context=vars(hub.RunContext()),
                        repository_root=str(root),
                    )
                    with self.assertRaisesRegex(Exception, message):
                        await server.call_tool(TOOLS[2], arguments)
                    arguments["context"]["dry_run"] = True
                    await server.call_tool(TOOLS[2], arguments)
                for tool, arguments in [
                    (
                        TOOLS[4],
                        dict(
                            state={"ok": True, "children": []},
                            match=MATCH,
                            registry=REGISTRY,
                        ),
                    ),
                    (
                        TOOLS[3],
                        dict(
                            state={"ok": False, "children": []},
                            child={"ok": True},
                            context=vars(hub.RunContext()),
                            action_count=1,
                        ),
                    ),
                ]:
                    with self.assertRaisesRegex(
                        Exception, "exactly one observation|inconsistent"
                    ):
                        await server.call_tool(tool, arguments)
                self.assertEqual(ledger(root), [])

    def test_registered_mcp_lunar_prism_execution(self):
        asyncio.run(self.connected())

    async def connected(self):
        document = yaml.safe_load(CONTRACT.read_text())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve() / "repo"
            populate(root)
            server = (
                "import sys;sys.dont_write_bytecode=True;sys.path[:0]="
                + repr([str(ROOT / "scripts"), str(FIXTURES), str(ROOT), *SITES])
                + ";from lean_route_compiler import serve;serve("
                + repr(str(root))
                + ")"
            )
            manager, failure = SessionManager(), None
            async with manager.open(
                "lean-route",
                StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
                {"PYTHONDONTWRITEBYTECODE": "1"},
            ) as remote:
                try:
                    tools = [
                        tool.model_dump(by_alias=True, exclude_none=True)
                        for tool in await remote.tools()
                    ]
                    self.assertTrue(set(TOOLS) <= {t["name"] for t in tools})

                    def compile(doc, inventory=None):
                        assets = snapshot(doc)
                        workflow = workflow_documents([DESCRIPTOR], assets)[0]
                        self.assertTrue(workflow["validation"]["valid"], workflow)
                        return (
                            compile_workflow(
                                "mcp:lean-route",
                                workflow,
                                tools if inventory is None else inventory,
                            ),
                            assets,
                        )

                    bound, assets = compile(document)
                    self.assertTrue(bound["runnable"], bound["diagnostics"])
                    self.assertEqual(bound["runtime_status"], "ready")
                    self.assertTrue(bound["prism_source"])
                    self.assertTrue(bound["runtime_source"])
                    self.assertEqual(set(bound["bindings"]), set(ORDER))
                    self.assertFalse(
                        compile(document, [t for t in tools if t["name"] != TOOLS[2]])[
                            0
                        ]["runnable"]
                    )

                    async def authorize():
                        pass

                    async def run(inputs, changed=None):
                        graph, received = (
                            compile(changed) if changed else (bound, assets)
                        )
                        self.assertTrue(graph["runnable"], graph["diagnostics"])
                        return await execute(graph, received, inputs, remote, authorize)

                    base = dict(
                        match=MATCH,
                        registry=REGISTRY,
                        context=vars(hub.RunContext()),
                        repository_root=str(root),
                    )
                    for mode in [
                        "success",
                        "reject",
                        "timeout",
                        "write",
                        "missing",
                        "crash",
                    ]:
                        for ready in [True, False]:
                            for dry in [False, True]:
                                for keep in [False, True]:
                                    populate(root, mode, ready)
                                    inputs = deepcopy(base)
                                    inputs["context"].update(
                                        dry_run=dry, keep_going=keep
                                    )
                                    result = await run(inputs)
                                    launches = int(
                                        ready and not dry and mode != "missing"
                                    )
                                    self.assertEqual(
                                        ledger(root),
                                        [
                                            dict(
                                                argv=["lake", "build"],
                                                cwd=str(root),
                                                timeout=1200,
                                            )
                                        ]
                                        * launches,
                                    )
                                    if mode == "crash" and launches:
                                        self.assertEqual(
                                            result["status"], "failed", result
                                        )
                                        self.assertIsNone(result["outputs"])
                                        self.assertEqual(
                                            [c["operation"] for c in result["calls"]],
                                            ORDER[:3],
                                        )
                                        self.assertEqual(
                                            result["calls"][-1]["status"], "rejected"
                                        )
                                        self.assertEqual(
                                            result["calls"][-1]["error"],
                                            "The MCP server rejected the operation",
                                        )
                                        continue
                                    self.assertEqual(
                                        result["status"], "accepted", result
                                    )
                                    self.assertEqual(
                                        [c["operation"] for c in result["calls"]], ORDER
                                    )
                                    self.assertEqual(
                                        [c["tool"] for c in result["calls"]], TOOLS
                                    )
                                    route = result["outputs"]["result"]
                                    child = route["children"][0]
                                    self.assertEqual(len(route["children"]), 1)
                                    expected_ok = (
                                        ready
                                        and mode != "missing"
                                        and (dry or mode == "success")
                                    )
                                    self.assertEqual(route["ok"], expected_ok)
                                    self.assertEqual(
                                        route["status"],
                                        (
                                            "intent_run_completed"
                                            if expected_ok
                                            else "intent_run_failed"
                                        ),
                                    )
                                    self.assertEqual(
                                        route["route"]["score"], MATCH["score"]
                                    )
                                    self.assertEqual(
                                        route["route"]["matched_terms"],
                                        MATCH["matched_terms"],
                                    )
                                    self.assertEqual(child["argv"], ["lake", "build"])
                                    self.assertEqual(child["action"], REGISTRY[ACTION])
                                    if not ready:
                                        self.assertIn(
                                            "missing required path: lakefile.toml",
                                            child["preflight_errors"],
                                        )
                                        self.assertIn(
                                            "missing required path: lean-toolchain",
                                            child["preflight_errors"],
                                        )
                                    if mode == "missing":
                                        self.assertIn(
                                            "missing required tool on PATH: lake",
                                            child["preflight_errors"],
                                        )
                                    if launches:
                                        self.assertEqual(
                                            child["status"],
                                            {
                                                "write": "undeclared_writes",
                                                "timeout": "timeout",
                                            }.get(mode, "completed"),
                                        )
                                        if mode == "timeout":
                                            self.assertEqual(
                                                child["stdout"],
                                                {"base64": "cGFydGlhbP8="},
                                            )
                                            self.assertEqual(
                                                child["stderr"],
                                                {"base64": "ZGVhZGxpbmU="},
                                            )
                                            self.assertIsNone(child["returncode"])
                                            self.assertEqual(
                                                child["timeout_seconds"], 1200
                                            )
                                        else:
                                            self.assertEqual(
                                                child["returncode"],
                                                7 if mode == "reject" else 0,
                                            )
                                            self.assertEqual(
                                                child["stdout"],
                                                "Fixture.lean: compiled\n",
                                            )
                                            self.assertEqual(
                                                (
                                                    root
                                                    / ".lake/build/lib/Fixture.olean"
                                                ).read_bytes(),
                                                b"fixture compiler artifact",
                                            )
                                        self.assertEqual(
                                            child["write_audit"]["ok"], mode != "write"
                                        )
                                        if mode == "write":
                                            self.assertEqual(
                                                child["write_audit"][
                                                    "unexpected_paths"
                                                ],
                                                ["undeclared.txt"],
                                            )
                                    elif ready and mode != "missing":
                                        self.assertEqual(child["status"], "dry_run")
                                    self.assertTrue(result["runtime"]["effect_records"])
                                    self.assertTrue(result["runtime"]["provenance"])
                                    self.assertTrue(result["replay_artifacts"])
                                    # Compare full outputs and audits against the frozen selected source.
                                    populate(root, mode, ready)
                                    with (
                                        patch.object(hub, "subprocess"),
                                        patch.object(hub, "shutil"),
                                    ):
                                        install(hub, root)
                                        expected = state_wire(
                                            original().run_intent_match(
                                                selected_match(MATCH),
                                                checked_registry(REGISTRY),
                                                hub.RunContext(**inputs["context"]),
                                                repository_root=root,
                                            )
                                        )
                                    self.assertEqual(route, expected)
                    populate(root)
                    inputs = deepcopy(base)
                    inputs["context"]["dry_run"] = True
                    # Optional context mount omission preserves the native default, with preflight only.
                    del inputs["repository_root"]
                    result = await run(inputs)
                    with patch.object(
                        hub,
                        "shutil",
                        SimpleNamespace(
                            which=lambda tool: str(
                                Path(gettempdir())
                                / "mathformer-test-fixtures/fixture/lake"
                            )
                        ),
                    ):
                        expected = hub.run_intent_match(
                            selected_match(MATCH),
                            checked_registry(REGISTRY),
                            hub.RunContext(dry_run=True),
                        )
                    self.assertEqual(result["outputs"], {"result": expected})
                    self.assertEqual(ledger(root), [])
                    inputs = deepcopy(base)
                    inputs["context"]["dry_run"] = True
                    for port in ["registry", "match"]:
                        forged = deepcopy(inputs)
                        if port == "registry":
                            forged[port][ACTION]["summary"] = "forged metadata"
                        else:
                            forged[port]["route"]["title"] = "forged title"
                        result = await run(forged)
                        self.assertEqual(result["status"], "failed", result)
                        self.assertIsNone(result["outputs"])
                        self.assertLessEqual(len(result["calls"]), 3)
                    # Executable command tampering is rejected even before MCP dispatch.
                    forged = deepcopy(inputs)
                    forged["registry"][ACTION]["command"] = ["forged-command"]
                    with self.assertRaisesRegex(
                        ExecutionRejected, "workflow inputs.registry"
                    ):
                        await run(forged)
                    with self.assertRaises(Exception):
                        await remote.call(
                            TOOLS[2],
                            dict(
                                action_id=ACTION,
                                registry=forged["registry"],
                                context=inputs["context"],
                                repository_root=str(root),
                            ),
                        )
                    # Missing action is native failure data at the tool boundary.
                    child = await remote.call(
                        TOOLS[2],
                        dict(
                            action_id=ACTION,
                            registry={},
                            context=inputs["context"],
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
                    for budget in [1, 3, 4]:
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
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]], ORDER[:-1]
                    )
                    changed = deepcopy(document)
                    changed["flow"]["steps"][1]["body"]["steps"][0]["arguments"][
                        "state"
                    ] = {"literal": {"ok": True, "children": [{"ok": True}]}}
                    result = await run(inputs, changed)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(len(result["calls"]), 2)
                    inputs["context"]["dry_run"] = False
                    inputs["repository_root"] = str(root.parent / "outside")
                    result = await run(inputs)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(len(result["calls"]), 3)
                    self.assertEqual(ledger(root), [])
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
