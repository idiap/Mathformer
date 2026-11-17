#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Offline native, registered MCP and real Lunar/PRISM contract execution."""

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
from copy import deepcopy
from dataclasses import asdict, replace
import hashlib
import json
import tempfile
from types import SimpleNamespace
import unittest
import yaml
import mathformer as hub
from workflow_router_route_tools import (
    ACTION,
    ROUTE,
    selected_match,
    checked_registry,
    check_state,
)
from workflow_router_route_tree import (
    populate,
    load_router,
    coverage_snapshot,
    LEAF,
    LOG,
)
from reasoning_route_compiler import install
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_workflow_router_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
DOCUMENT = yaml.safe_load(CONTRACT.read_text())
MATCH = {
    "route": json.loads(
        json.dumps(
            asdict(next(r for r in hub.build_intent_routes() if r.route_id == ROUTE))
        )
    ),
    "score": 23,
    "matched_terms": ["workflow", "router"],
}
REGISTRY = {ACTION: hub.action_to_dict(hub.build_registry()[ACTION])}
ORDER = ["initialize", "select", "execute", "advance", "finish"]


def original():
    scope = dict(vars(hub))
    exec(
        (ROOT / "tests/mcp/fixtures/workflow_router_route_original.py.txt").read_text(),
        scope,
    )
    return SimpleNamespace(**scope)


def snapshot(document):
    values = {
        s["path"]: (ROOT / s["path"]).read_text()
        for s in document["provenance"]["sources"]
    }
    values[SCHEMA] = (ROOT / SCHEMA).read_text()
    values[DESCRIPTOR] = json.dumps(document)
    return [
        dict(
            path=p,
            content=t,
            encoding="text",
            sha256=hashlib.sha256(t.encode()).hexdigest(),
        )
        for p, t in values.items()
    ]


class WorkflowRouterRouteTests(unittest.TestCase):
    maxDiff = None

    def test_generator_identity_policy_provenance_and_native_state(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "router_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.workflow_router_route_descriptor(), DOCUMENT)
        self.assertEqual(DOCUMENT["id"], "route_workflow_router_workflow")
        self.assertEqual(DOCUMENT["aliases"], [ROUTE])
        self.assertEqual(DOCUMENT["lifecycle"], "active")
        self.assertEqual(
            DOCUMENT["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 5},
        )
        self.assertEqual(
            DOCUMENT["policy"]["failure"]["retry"],
            {"max_attempts": 1, "retryable_codes": []},
        )
        self.assertEqual(DOCUMENT["policy"]["resume"]["mode"], "none")
        self.assertEqual(
            DOCUMENT["policy"]["effects"],
            {
                "filesystem": {
                    "read": ["repository", "native_runtime_inputs"],
                    "write": [],
                },
                "network": [],
                "external_write": [],
            },
        )
        self.assertIn(
            {
                "path": "scripts/mathformer.py",
                "selector": "run_intent_match",
                "digest": "sha256:"
                + hashlib.sha256(
                    (ROOT / "scripts/mathformer.py").read_bytes()
                ).hexdigest(),
            },
            DOCUMENT["provenance"]["sources"],
        )
        for row in DOCUMENT["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        item = checked_registry(REGISTRY)[ACTION]
        self.assertEqual(item.command, ("{python}", LEAF, "--audit-coverage", "--json"))
        self.assertFalse(item.depends_on)
        self.assertFalse(item.writes)
        self.assertIsNone(item.timeout_seconds)
        self.assertEqual(checked_registry({}), {})
        for keep in [False, True]:
            for child in [{"ok": True}, {"ok": False}, {}]:
                state = hub.initialize_intent_state()
                updated, done = hub.advance_intent_state(
                    state, child, hub.RunContext(keep_going=keep), 1
                )
                self.assertEqual(state, {"ok": True, "children": []})
                self.assertEqual(
                    updated, {"ok": bool(child.get("ok")), "children": [child]}
                )
                self.assertTrue(done)
                check_state(updated)
                with self.assertRaisesRegex(ValueError, "bounds"):
                    check_state(updated, selecting=True)
        with self.assertRaisesRegex(ValueError, "accumulator"):
            check_state({"ok": True, "children": [{"ok": False}]})
        for field in ["command", "depends_on", "writes"]:
            forged = deepcopy(REGISTRY)
            forged[ACTION][field] = ["forged"]
            with self.assertRaisesRegex(ValueError, "projection"):
                checked_registry(forged)

    def test_real_coverage_traversal_states_blockers_and_finite_completion(self):
        module = load_router(ROOT)
        context = coverage_snapshot()
        report = module.build_coverage_report(deepcopy(context))
        self.assertFalse(report["ok"])
        self.assertEqual(
            report["blockers"],
            [
                "missing_family_route_coverage",
                "unknown_route_action_refs",
                "routes_without_actions",
            ],
        )
        self.assertEqual(report["missing_families"], ["gamma"])
        self.assertEqual(report["covered_families"], ["alpha", "beta", "delta"])
        self.assertEqual(
            report["unknown_action_refs"],
            [{"route_id": "first", "action_id": "missing"}],
        )
        self.assertEqual(report["routes_without_actions"], ["empty"])
        self.assertEqual(
            [r["route_id"] for r in report["routes"]], ["first", "empty", "last"]
        )
        self.assertEqual(report["routes"][0]["families"], ["alpha", "beta", "delta"])
        self.assertEqual(report["routes"][1]["families"], [])
        initialized = module.initialize_coverage(context=deepcopy(context))
        self.assertTrue(initialized["has_routes"])
        state = initialized["state"]
        visits = []
        for index, route in enumerate(context["routes"]):
            self.assertEqual(state["route_index"], index)
            begun = module.begin_coverage_route(state)
            self.assertEqual(begun["has_actions"], bool(route["action_ids"]))
            self.assertEqual(state["action_index"], 0)
            self.assertEqual(state["route_families"], [])
            for action_index, action in enumerate(route["action_ids"]):
                visits.append(action)
                advanced = module.visit_coverage_action(state)
                self.assertEqual(state["action_index"], action_index + 1)
                self.assertEqual(
                    advanced["actions_done"],
                    action_index + 1 == len(route["action_ids"]),
                )
            finished = module.finish_coverage_route(state)
            self.assertEqual(
                finished["routes_done"], index + 1 == len(context["routes"])
            )
        self.assertEqual(visits, ["b", "a", "a", "test:family:delta", "missing", "b"])
        self.assertEqual((state["phase"], state["route_index"]), ("done", 3))
        self.assertEqual(module.finalize_coverage(state), report)
        empty = module.build_coverage_report({"registry": {}, "routes": []})
        self.assertTrue(empty["ok"])
        self.assertEqual(empty["route_count"], 0)
        missing = module.build_coverage_report(
            {"registry": context["registry"], "routes": []}
        )
        self.assertEqual(missing["missing_families"], ["alpha", "beta", "gamma"])
        success = deepcopy(context)
        success["routes"][0]["action_ids"] = [
            "a",
            "b",
            "uncovered",
            "test:family:delta",
        ]
        success["routes"].pop(1)
        self.assertTrue(module.build_coverage_report(success)["ok"])
        domain = {"route_cap": 10000, "actions_per_route_cap": 10000}
        self.assertEqual(
            module.initialize_coverage(domain, context)["state"]["routes"],
            context["routes"],
        )
        for over in [
            {"registry": {}, "routes": [context["routes"][1]] * 10001},
            {
                "registry": {},
                "routes": [{**context["routes"][0], "action_ids": ["a"] * 10001}],
            },
        ]:
            with self.assertRaisesRegex(ValueError, "exceeds"):
                module.initialize_coverage(domain, over)
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            module.initialize_coverage({"route_cap": 1}, context)
        # Native CLI path has no optional caps; all source collections are exhausted.
        native_report = module.build_coverage_report()
        self.assertEqual(native_report["route_count"], len(hub.build_intent_routes()))
        self.assertTrue(native_report["ok"], native_report)

    def test_original_entrypoint_order_early_stop_and_sticky_failure(self):
        oracle = original()
        native = checked_registry(REGISTRY)
        match = selected_match(MATCH)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for keep in [False, True]:
                for dry in [False, True]:
                    context = hub.RunContext(dry_run=dry, keep_going=keep)
                    expected = oracle.run_intent_match(
                        match, native, context, repository_root=root
                    )
                    self.assertEqual(
                        hub.run_intent_match(
                            match, native, context, repository_root=root
                        ),
                        expected,
                    )
                    self.assertFalse(expected["ok"])
                    self.assertEqual(len(expected["children"]), 1)
                    # Repeated real preflight failures expose generic stop/continue
                    # semantics without launching a process or replacing a step.
                    repeated = hub.IntentMatch(
                        replace(match.route, action_ids=(ACTION, ACTION)),
                        match.score,
                        match.matched_terms,
                    )
                    results = [
                        source.run_intent_match(
                            repeated, native, context, repository_root=root
                        )
                        for source in [oracle, hub]
                    ]
                    self.assertEqual(*results)
                    self.assertEqual(len(results[0]["children"]), 2 if keep else 1)
                    self.assertFalse(results[0]["ok"])
        state, done = hub.advance_intent_state(
            hub.initialize_intent_state(),
            {"ok": False},
            hub.RunContext(keep_going=True),
            2,
        )
        self.assertFalse(done)
        state, done = hub.advance_intent_state(
            state, {"ok": True}, hub.RunContext(keep_going=True), 2
        )
        self.assertTrue(done)
        self.assertFalse(state["ok"])
        self.assertEqual(state["children"], [{"ok": False}, {"ok": True}])

    def test_deterministic_external_compiler_boundary(self):
        # This route has no provider/compiler dependency. Test the generic native
        # launcher separately, substituting only an external compiler process.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            saved = hub.subprocess
            try:
                for mode in ["success", "reject", "write", "launch_error", "timeout"]:
                    (root / "undeclared.txt").unlink(missing_ok=True)
                    leaf = replace(
                        hub.build_registry()[ACTION],
                        command=("fixture-reasoning-compiler", mode),
                        required_paths=(),
                        timeout_seconds=3 if mode == "timeout" else None,
                    )
                    calls = install(hub, root)
                    if mode == "launch_error":
                        with self.assertRaisesRegex(OSError, "launch failed"):
                            hub.run_action(
                                ACTION,
                                {ACTION: leaf},
                                hub.RunContext(),
                                repository_root=root,
                            )
                    else:
                        result = hub.run_action(
                            ACTION,
                            {ACTION: leaf},
                            hub.RunContext(),
                            repository_root=root,
                        )
                        self.assertEqual(result["ok"], mode == "success")
                        self.assertEqual(
                            result["status"],
                            {"timeout": "timeout", "write": "undeclared_writes"}.get(
                                mode, "completed"
                            ),
                        )
                        if mode == "timeout":
                            self.assertEqual(
                                (
                                    result["returncode"],
                                    result["stdout"],
                                    result["stderr"],
                                ),
                                (None, "partial", "deadline"),
                            )
                        else:
                            self.assertEqual(
                                json.loads(result["stdout"])["artifact"]["nodes"],
                                ["input", "check"],
                            )
                            self.assertEqual(
                                result["returncode"], 7 if mode == "reject" else 0
                            )
                        if mode == "write":
                            self.assertEqual(
                                result["write_audit"]["unexpected_paths"],
                                ["undeclared.txt"],
                            )
                    self.assertEqual(
                        calls,
                        [{"argv": list(leaf.command), "timeout": leaf.timeout_seconds}],
                    )
            finally:
                hub.subprocess = saved

    def test_registered_mcp_real_lunar_compile_runtime_and_original_parity(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        manager = SessionManager()
        error = None
        code = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        async with manager.open(
            "workflow-router-route",
            StdioConfig(command=sys.executable, args=["-c", code], cwd=str(ROOT)),
            {"PYTHONPATH": os.pathsep.join(SITES), "PYTHONDONTWRITEBYTECODE": "1"},
        ) as remote:
            try:
                await self.connected(remote)
            except Exception as exc:
                error = exc
        self.assertFalse(manager.active)
        if error:
            raise error

    async def connected(self, remote):
        tools = [
            t.model_dump(by_alias=True, exclude_none=True) for t in await remote.tools()
        ]

        def compile_document(document, advertised=tools):
            assets = snapshot(document)
            docs = workflow_documents([DESCRIPTOR], assets)
            self.assertEqual(len(docs), 1)
            self.assertTrue(docs[0]["validation"]["valid"], docs[0])
            compiled = compile_workflow("workflow-router-route", docs[0], advertised)
            self.assertEqual(compiled["conversion_status"], "converted", compiled)
            self.assertTrue(compiled["prism_source"])
            self.assertTrue(compiled["graph"])
            return compiled, assets

        compiled, assets = compile_document(DOCUMENT)
        self.assertTrue(compiled["runnable"], compiled["diagnostics"])
        self.assertEqual(compiled["runtime_status"], "ready")
        for operation in ORDER:
            target = DOCUMENT["operations"][operation]["execution"]["binding"]["target"]
            unavailable, _ = compile_document(
                DOCUMENT, [t for t in tools if t["name"] != target]
            )
            self.assertFalse(unavailable["runnable"])

        async def authorize():
            pass

        async def run(inputs, changed=None):
            c, a = compile_document(changed) if changed else (compiled, assets)
            self.assertTrue(c["runnable"], c["diagnostics"])
            return await execute(c, a, inputs, remote, authorize)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            base = {
                "context": vars(hub.RunContext()),
                "match": MATCH,
                "registry": REGISTRY,
                "repository_root": str(root),
            }
            for ready in [False, True]:
                populate(root, ROOT) if ready else None
                for dry in [False, True]:
                    for keep in [False, True]:
                        inputs = deepcopy(base)
                        inputs["context"].update(dry_run=dry, keep_going=keep)
                        before = hub.snapshot_repository(root)
                        result = await run(inputs)
                        expected = original().run_intent_match(
                            selected_match(MATCH),
                            checked_registry(REGISTRY),
                            hub.RunContext(**inputs["context"]),
                            repository_root=root,
                        )
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertEqual(result["outputs"], {"result": expected})
                        actual = result["outputs"]["result"]
                        child = actual["children"][0]
                        self.assertEqual(len(actual["children"]), 1)
                        self.assertEqual(
                            [c["operation"] for c in result["calls"]], ORDER
                        )
                        self.assertEqual(
                            [c["tool"] for c in result["calls"]],
                            ["mathformer_workflow_router_" + op for op in ORDER],
                        )
                        self.assertEqual(actual["ok"], ready)
                        self.assertEqual(actual["route"]["score"], MATCH["score"])
                        self.assertEqual(
                            actual["route"]["matched_terms"], MATCH["matched_terms"]
                        )
                        self.assertEqual(hub.snapshot_repository(root), before)
                        self.assertEqual(
                            child["argv"],
                            [sys.executable, LEAF, "--audit-coverage", "--json"],
                        )
                        if ready and not dry:
                            self.assertTrue(child["stdout"], child)
                            report = json.loads(child["stdout"])
                            self.assertEqual(child["returncode"], 0)
                            self.assertTrue(report["ok"])
                            self.assertEqual(
                                report, load_router(ROOT).build_coverage_report()
                            )
                            self.assertTrue(child["write_audit"]["ok"])
                        elif ready:
                            self.assertEqual(child["status"], "dry_run")
                            self.assertNotIn("returncode", child)
                        else:
                            self.assertTrue(child["preflight_errors"])
                            self.assertNotIn("returncode", child)
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["replay_artifacts"])
            # Real missing-import exception becomes a captured unsuccessful
            # subprocess result; no retry and no scientific workflow is launched.
            (root / LOG).unlink()
            result = await run(base)
            child = result["outputs"]["result"]["children"][0]
            self.assertNotEqual(child["returncode"], 0)
            self.assertIn("ModuleNotFoundError", child["stderr"])
            self.assertFalse(result["outputs"]["result"]["ok"])
            self.assertEqual([c["operation"] for c in result["calls"]], ORDER)
            for kind in ["registry", "route", "cursor", "missing_registry"]:
                inputs = deepcopy(base)
                inputs["context"]["dry_run"] = True
                changed = None
                if kind == "registry":
                    inputs["registry"][ACTION]["command"] = ["forged"]
                elif kind == "route":
                    inputs["match"]["route"]["title"] = "forged"
                elif kind == "missing_registry":
                    inputs["registry"] = {}
                    with self.assertRaises(KeyError):
                        original().run_intent_match(
                            selected_match(MATCH),
                            {},
                            hub.RunContext(dry_run=True),
                            repository_root=root,
                        )
                else:
                    changed = deepcopy(DOCUMENT)
                    changed["flow"]["steps"][1]["body"]["steps"][0]["arguments"][
                        "state"
                    ] = {"literal": {"ok": True, "children": [{"ok": True}]}}
                result = await run(inputs, changed)
                self.assertEqual(result["status"], "failed")
                self.assertIsNone(result["outputs"])
                self.assertEqual(
                    result["calls"][-1]["operation"],
                    {
                        "registry": "execute",
                        "route": "select",
                        "cursor": "select",
                        "missing_registry": "finish",
                    }[kind],
                )
            unknown = await remote.call(
                "mathformer_workflow_router_execute",
                {
                    "action_id": ACTION,
                    "context": vars(hub.RunContext(dry_run=True)),
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
            populate(root, ROOT)
            inputs = deepcopy(base)
            inputs["context"]["dry_run"] = True
            changed = deepcopy(DOCUMENT)
            changed["flow"]["steps"][1]["until"] = {"literal": False}
            result = await run(inputs, changed)
            self.assertEqual(result["status"], "failed")
            self.assertIsNone(result["outputs"])
            self.assertEqual([c["operation"] for c in result["calls"]], ORDER[:-1])
            for cap in [1, 4]:
                changed = deepcopy(DOCUMENT)
                changed["policy"]["limits"]["max_operation_calls"] = cap
                result = await run(inputs, changed)
                self.assertEqual(result["status"], "failed")
                self.assertIsNone(result["outputs"])
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in result["calls"]
                    ),
                    cap,
                )
            timed = deepcopy(DOCUMENT)
            timed["policy"]["limits"]["wall_time_seconds"] = 1
            workflow, received = compile_document(timed)

            async def waiting_authority():
                await asyncio.Event().wait()

            with self.assertRaises(TimeoutError):
                await execute(workflow, received, inputs, remote, waiting_authority)
            for omitted in [False, True]:
                inputs["repository_root"] = None
                if omitted:
                    inputs.pop("repository_root")
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


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False).result
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
