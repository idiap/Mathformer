#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Offline source/MCP/Lunar tests with real PRISM compilation and execution.

Only separate external compiler fixture actions substitute a process boundary.
The graph actions run unchanged against tiny temporary input trees. No provider,
credentials, production workflow, deployment or promotion is involved.
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
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT / "tests/mcp/fixtures"),
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
from types import SimpleNamespace
import unittest
import yaml

import mathformer as hub
from workflow_graphs_route_tools import (
    ACTIONS,
    ROUTE,
    selected_match,
    checked_registry,
    check_state,
    register_workflow_graphs_route_tools,
)
from workflow_graphs_route_tree import populate, outputs, clear_outputs, SCRIPTS
from reasoning_route_compiler import install
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_workflow_graphs_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
MATCH = {
    "route": {"route_id": ROUTE, "action_ids": list(ACTIONS)},
    "score": 27,
    "matched_terms": ["workflow graphs", "skill integration audit"],
}
REGISTRY = {key: hub.action_to_dict(hub.build_registry()[key]) for key in ACTIONS}


def original():
    scope = dict(vars(hub))
    exec(
        (ROOT / "tests/mcp/fixtures/workflow_graphs_route_original.py.txt").read_text(),
        scope,
    )
    return SimpleNamespace(**scope), scope


def snapshot(document):
    values = {
        row["path"]: (ROOT / row["path"]).read_text()
        for row in document["provenance"]["sources"]
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


class WorkflowGraphsTests(unittest.TestCase):
    maxDiff = None

    def test_authored_generator_identity_policy_and_provenance(self):
        spec = importlib.util.spec_from_file_location(
            "graphs_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        document = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(module.workflow_graphs_route_descriptor(), document)
        self.assertEqual(document["id"], "route_workflow_graphs_workflow")
        self.assertEqual(document["aliases"], [ROUTE])
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 11},
        )
        self.assertEqual(
            document["policy"]["effects"]["filesystem"]["write"],
            ["artifacts/workflow_graphs/", "artifacts/workflow_hub/"],
        )
        self.assertEqual(
            document["policy"]["failure"]["retry"],
            {"max_attempts": 1, "retryable_codes": []},
        )
        self.assertEqual(document["policy"]["resume"]["mode"], "none")
        self.assertEqual(
            document["observability"]["events"],
            ["intent_run_completed", "intent_run_failed"],
        )
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
        native = checked_registry(REGISTRY)
        for key, script in zip(ACTIONS, SCRIPTS):
            self.assertEqual(native[key].command, ("{python}", script, "--json"))
            self.assertFalse(native[key].depends_on)
            self.assertIsNone(native[key].timeout_seconds)
        self.assertEqual(checked_registry({}), {})
        for field in ["command", "writes", "depends_on"]:
            forged = deepcopy(REGISTRY)
            forged[ACTIONS[0]][field] = ["forged"]
            with self.assertRaisesRegex(ValueError, "projection"):
                checked_registry(forged)

    def test_source_equivalence_preflight_dryrun_state_and_real_artifacts(self):
        oracle, _ = original()
        match, native = selected_match(MATCH), checked_registry(REGISTRY)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for ready in [False, True]:
                if ready:
                    populate(root, ROOT)
                for dry in [False, True]:
                    for keep in [False, True]:
                        context = hub.RunContext(
                            dry_run=dry, keep_going=keep, write_report=True
                        )
                        results, files = [], []
                        for source in [oracle, hub]:
                            clear_outputs(root)
                            results.append(
                                source.run_intent_match(
                                    match, native, context, repository_root=root
                                )
                            )
                            files.append(outputs(root))
                        self.assertEqual(*results)
                        self.assertEqual(*files)
                        self.assertEqual(results[0]["ok"], ready)
                        self.assertEqual(
                            len(results[0]["children"]), 3 if ready or keep else 1
                        )
                        if ready and not dry:
                            self.assert_artifacts(root, results[0])
                        else:
                            self.assertFalse(files[0])
            for fail_at in [None, 0, 1, 2]:
                for keep in [False, True]:
                    state = hub.initialize_intent_state()
                    for i in range(3):
                        before = deepcopy(state)
                        self.assertEqual(
                            hub.select_intent_action(state, match), ACTIONS[i]
                        )
                        state, done = hub.advance_intent_state(
                            state,
                            {"ok": i != fail_at, "stdout": str(i)},
                            hub.RunContext(keep_going=keep),
                            3,
                        )
                        self.assertEqual(state["children"][:-1], before["children"])
                        self.assertEqual(done, i == 2 or (i == fail_at and not keep))
                        check_state(state)
                        if done:
                            break
                    self.assertEqual(state["ok"], fail_at is None)
                    self.assertEqual(
                        len(state["children"]),
                        fail_at + 1 if fail_at is not None and not keep else 3,
                    )
            with self.assertRaisesRegex(ValueError, "accumulator"):
                check_state({"ok": False, "children": []})
            with self.assertRaisesRegex(ValueError, "bounds"):
                check_state(
                    {"ok": True, "children": [{"ok": True}] * 3}, selecting=True
                )

    def assert_artifacts(self, root, result):
        files = outputs(root)
        self.assertEqual(
            set(files),
            {
                "workflow_graphs.json",
                "workflow_graphs.html",
                "workflow_layout_plan.json",
                "workflow_skill_integration_audit.json",
                "workflow_skill_integration_audit.md",
            },
        )
        graph = json.loads(files["workflow_graphs.json"])
        plan = json.loads(files["workflow_layout_plan.json"])
        audit = json.loads(files["workflow_skill_integration_audit.json"])
        self.assertIn("fixture-loop", graph["stacks"])
        self.assertEqual(
            [s["skill"] for s in graph["stacks"]["fixture-loop"]["ordered_hooks"]],
            ["first", "second"],
        )
        self.assertEqual(audit["graph"]["summary"], graph["summary"])
        self.assertEqual(audit["summary"]["available_skills"], 5)
        positions = plan["views"]["drilldown"]["stack_layouts"]["fixture-loop"][
            "positions"
        ]
        steps = [
            node["data"]["id"]
            for node in graph["graph"]["elements"]["nodes"]
            if node["data"].get("node_type") == "workflow_step"
            and node["data"].get("stack") == graph["stacks"]["fixture-loop"]["label"]
        ]
        self.assertEqual(len(steps), 2)
        self.assertEqual(
            [positions[node] for node in steps], [{"x": 0, "y": 0}, {"x": 310, "y": 0}]
        )
        self.assertIn(b"Fixture", files["workflow_graphs.html"])
        self.assertEqual(
            [child["action"]["id"] for child in result["children"]], list(ACTIONS)
        )
        for child in result["children"]:
            self.assertEqual(child["returncode"], 0)
            self.assertTrue(child["write_audit"]["ok"])
            self.assertTrue(json.loads(child["stdout"])["ok"])

    def test_registered_tool_service_gates_and_completion_guards(self):
        from mcp.server.fastmcp import FastMCP

        server = FastMCP("graph-service-policy-test")
        calls = []

        def authorize():
            calls.append("authorize")

        def denied(path):
            calls.append(path)
            return False

        register_workflow_graphs_route_tools(server, authorize, denied)
        dispatch = server._tool_manager.get_tool(
            "mathformer_workflow_graphs_execute"
        ).fn
        finish = server._tool_manager.get_tool("mathformer_workflow_graphs_finish").fn
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            populate(root, ROOT)
            for key in ACTIONS:
                with self.assertRaisesRegex(ValueError, "configured service roots"):
                    dispatch(key, vars(hub.RunContext()), REGISTRY, str(root))
                child = dispatch(
                    key, vars(hub.RunContext(dry_run=True)), REGISTRY, str(root)
                )["child"]
                self.assertTrue(child["ok"])
                self.assertEqual(child["status"], "dry_run")
            self.assertEqual(
                calls, ["authorize", root / "artifacts/workflow_graphs/"] * 3
            )
            self.assertFalse(outputs(root))
        for state in [
            hub.initialize_intent_state(),
            {"ok": True, "children": [{"ok": True}]},
        ]:
            with self.assertRaisesRegex(ValueError, "completion"):
                finish(state, MATCH, REGISTRY)
        import mcp_server

        registered = mcp_server.mcp._tool_manager.get_tool(
            "mathformer_workflow_graphs_execute"
        ).fn
        previous = mcp_server._READONLY
        try:
            mcp_server._READONLY = True
            with self.assertRaisesRegex(ValueError, "read-only"):
                registered(ACTIONS[0], vars(hub.RunContext()), REGISTRY, None)
        finally:
            mcp_server._READONLY = previous

    def test_external_compiler_boundary_capture_audit_and_exception_parity(self):
        # The selected route has no model/compiler. Separate fixture actions
        # exercise the generic source subprocess boundary without replacing the
        # graph scripts or their MCP bindings.
        oracle, scope = original()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for mode in ["success", "reject", "write", "launch_error", "timeout"]:
                for position in range(3):
                    for keep in [False, True]:
                        registry = {
                            key: replace(
                                hub.build_registry()[key],
                                required_paths=(),
                                command=(
                                    "fixture-reasoning-compiler",
                                    mode if i == position else "success",
                                ),
                                timeout_seconds=(
                                    3 if mode == "timeout" and i == position else None
                                ),
                            )
                            for i, key in enumerate(ACTIONS)
                        }
                        results, histories = [], []
                        for source in [oracle, hub]:
                            (root / "undeclared.txt").unlink(missing_ok=True)
                            previous = source.subprocess
                            calls = install(source, root)
                            if source is oracle:
                                scope["subprocess"] = source.subprocess
                            try:
                                if mode == "launch_error":
                                    with self.assertRaisesRegex(
                                        OSError, "launch failed"
                                    ):
                                        source.run_intent_match(
                                            selected_match(MATCH),
                                            registry,
                                            hub.RunContext(keep_going=keep),
                                            repository_root=root,
                                        )
                                else:
                                    results.append(
                                        source.run_intent_match(
                                            selected_match(MATCH),
                                            registry,
                                            hub.RunContext(keep_going=keep),
                                            repository_root=root,
                                        )
                                    )
                                histories.append(deepcopy(calls))
                            finally:
                                source.subprocess = previous
                                if source is oracle:
                                    scope["subprocess"] = previous
                        self.assertEqual(*histories)
                        self.assertEqual(
                            len(histories[0]),
                            (
                                position + 1
                                if mode == "launch_error"
                                or (mode != "success" and not keep)
                                else 3
                            ),
                        )
                        if mode == "launch_error":
                            continue
                        self.assertEqual(*results)
                        self.assertEqual(results[0]["ok"], mode == "success")
                        child = results[0]["children"][position]
                        if mode == "write":
                            self.assertEqual(
                                child["write_audit"]["unexpected_paths"],
                                ["undeclared.txt"],
                            )
                        elif mode == "timeout":
                            self.assertEqual(
                                (
                                    child["status"],
                                    child["returncode"],
                                    child["stdout"],
                                    child["stderr"],
                                ),
                                ("timeout", None, "partial", "deadline"),
                            )
                        else:
                            self.assertEqual(
                                child["returncode"], 7 if mode == "reject" else 0
                            )
                            self.assertFalse(
                                json.loads(child["stdout"])["ok"]
                            )  # exit code owns native success

    def test_registered_mcp_lunar_prism_runtime_and_stopping(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        manager = SessionManager()
        error = None
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        async with manager.open(
            "workflow-graphs",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
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
        document = yaml.safe_load(CONTRACT.read_text())
        tools = [
            t.model_dump(by_alias=True, exclude_none=True) for t in await remote.tools()
        ]

        def compile(doc, advertised=tools):
            assets = snapshot(doc)
            docs = workflow_documents([DESCRIPTOR], assets)
            self.assertTrue(docs[0]["validation"]["valid"], docs[0])
            compiled = compile_workflow("workflow-graphs", docs[0], advertised)
            self.assertEqual(compiled["conversion_status"], "converted", compiled)
            self.assertTrue(compiled["prism_source"])
            return compiled, assets

        compiled, assets = compile(document)
        self.assertTrue(compiled["runnable"], compiled["diagnostics"])
        self.assertEqual(compiled["runtime_status"], "ready")
        self.assertTrue(compiled["runtime_source"])
        self.assertEqual(set(compiled["bindings"]), set(document["operations"]))
        for operation in document["operations"].values():
            target = operation["execution"]["binding"]["target"]
            rejected, _ = compile(document, [t for t in tools if t["name"] != target])
            self.assertFalse(rejected["runnable"])

        async def authorize():
            pass

        async def run(inputs, changed=None):
            workflow, received = compile(changed) if changed else (compiled, assets)
            self.assertTrue(workflow["runnable"], workflow["diagnostics"])
            return await execute(workflow, received, inputs, remote, authorize)

        oracle, _ = original()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            base = {
                "context": vars(hub.RunContext()),
                "match": MATCH,
                "registry": REGISTRY,
                "repository_root": str(root),
            }
            for ready in [False, True]:
                if ready:
                    populate(root, ROOT)
                for dry in [False, True]:
                    for keep in [False, True]:
                        inputs = deepcopy(base)
                        inputs["context"].update(dry_run=dry, keep_going=keep)
                        clear_outputs(root)
                        expected = oracle.run_intent_match(
                            selected_match(MATCH),
                            checked_registry(REGISTRY),
                            hub.RunContext(**inputs["context"]),
                            repository_root=root,
                        )
                        files = outputs(root)
                        clear_outputs(root)
                        result = await run(inputs)
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertEqual(result["outputs"], {"result": expected})
                        self.assertEqual(outputs(root), files)
                        count = len(expected["children"])
                        order = (
                            ["initialize"]
                            + ["select", "execute", "advance"] * count
                            + ["finish"]
                        )
                        self.assertEqual(
                            [c["operation"] for c in result["calls"]], order
                        )
                        self.assertEqual(
                            [c["tool"] for c in result["calls"]],
                            ["mathformer_workflow_graphs_" + op for op in order],
                        )
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["replay_artifacts"])
                        if ready and not dry:
                            self.assert_artifacts(root, expected)
                        else:
                            self.assertFalse(files)
            # Remove each native script in turn. Later success cannot clear a
            # failed earlier child, and keep_going controls the precise prefix.
            for position, key in enumerate(ACTIONS):
                populate(root, ROOT)
                (root / REGISTRY[key]["required_paths"][0]).unlink()
                for keep in [False, True]:
                    inputs = deepcopy(base)
                    inputs["context"].update(dry_run=True, keep_going=keep)
                    result = await run(inputs)
                    value = result["outputs"]["result"]
                    self.assertFalse(value["ok"])
                    self.assertEqual(value["status"], "intent_run_failed")
                    self.assertEqual(
                        len(value["children"]), 3 if keep else position + 1
                    )
                    if keep and position < 2:
                        self.assertTrue(value["children"][-1]["ok"])
            populate(root, ROOT)
            # A real local parse failure is captured as a nonzero process exit.
            (root / "skills/SKILL_HOOKS.yaml").unlink()
            for keep in [False, True]:
                clear_outputs(root)
                inputs = deepcopy(base)
                inputs["context"]["keep_going"] = keep
                result = await run(inputs)
                value = result["outputs"]["result"]
                self.assertFalse(value["ok"])
                self.assertEqual(len(value["children"]), 3 if keep else 1)
                self.assertNotEqual(value["children"][0]["returncode"], 0)
                self.assertIn("FileNotFoundError", value["children"][0]["stderr"])
                self.assertTrue(value["children"][0]["write_audit"]["ok"])
            populate(root, ROOT)
            inputs = deepcopy(base)
            inputs["context"]["dry_run"] = True
            for forged in ["registry", "route", "cursor", "missing_registry"]:
                bad = deepcopy(inputs)
                changed = None
                if forged == "registry":
                    bad["registry"][ACTIONS[0]]["command"] = ["arbitrary-command"]
                elif forged == "route":
                    bad["match"]["route"]["title"] = "forged"
                elif forged == "missing_registry":
                    bad["registry"] = {}
                else:
                    changed = deepcopy(document)
                    changed["flow"]["steps"][1]["body"]["steps"][0]["arguments"][
                        "state"
                    ] = {"literal": {"ok": True, "children": [{"ok": True}] * 3}}
                result = await run(bad, changed)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(
                    result["calls"][-1]["operation"],
                    {
                        "registry": "execute",
                        "route": "select",
                        "cursor": "select",
                        "missing_registry": "finish",
                    }[forged],
                )
            unknown = await remote.call(
                "mathformer_workflow_graphs_execute",
                {
                    "action_id": ACTIONS[0],
                    "context": inputs["context"],
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
                        "action_id": ACTIONS[0],
                    }
                },
            )
            for limit in [1, 4, 10]:
                changed = deepcopy(document)
                changed["policy"]["limits"]["max_operation_calls"] = limit
                result = await run(inputs, changed)
                self.assertEqual(result["status"], "failed")
                self.assertIsNone(result["outputs"])
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in result["calls"]
                    ),
                    limit,
                )
            for bound in [1, 2]:
                changed = deepcopy(document)
                changed["flow"]["steps"][1]["max_iterations"] = bound
                result = await run(inputs, changed)
                self.assertEqual(result["status"], "failed")
                self.assertIsNone(result["outputs"])
                self.assertEqual(len(result["calls"]), 1 + 3 * bound)
            changed = deepcopy(document)
            changed["flow"]["steps"][1]["until"] = {"literal": False}
            result = await run(inputs, changed)
            self.assertEqual(result["status"], "failed")
            self.assertIsNone(result["outputs"])
            self.assertEqual(len(result["calls"]), 10)
            timed = deepcopy(document)
            timed["policy"]["limits"]["wall_time_seconds"] = 1
            workflow, received = compile(timed)

            async def waiting_authority():
                await asyncio.Event().wait()

            with self.assertRaises(TimeoutError):
                await execute(workflow, received, inputs, remote, waiting_authority)
            # The actual project can only be reached in dry-run mode here.
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
