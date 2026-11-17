#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Offline native/MCP/Lunar integration over synthetic reasoning-log trees."""

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
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT / "tests/mcp/fixtures"),
]
SITES = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
sys.path.extend(SITES)
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib.util
import json
import re
import tempfile
from types import SimpleNamespace
import unittest
import yaml
import mathformer as hub
from reasoning_logs_route_tools import (
    ACTION,
    ROUTE,
    DEPENDENCIES,
    selected_match,
    checked_registry,
    check_dependencies,
    register_reasoning_logs_route_tools,
)
from reasoning_logs_route_tree import populate
from reasoning_route_compiler import install
from mcp.server.fastmcp import FastMCP
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_control_reasoning_logs_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
DOCUMENT = yaml.safe_load(CONTRACT.read_text())
MATCH = {"route_id": ROUTE, "score": 23, "matched_terms": ["reasoning", "logs"]}
REGISTRY = {
    key: hub.action_to_dict(hub.build_registry()[key])
    for key in (ACTION, *DEPENDENCIES)
}


def original():
    scope = dict(vars(hub))
    exec(
        (ROOT / "tests/mcp/fixtures/reasoning_logs_route_original.py.txt").read_text(),
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


def outcomes(result):
    """Compare native observable decisions; reports contain native clocks/UUIDs."""
    # Summary filenames include the digest of native clock/UUID-bearing logs.
    result = json.loads(
        re.sub(
            r"good-[0-9a-f]{10}\.summary", "good-<digest>.summary", json.dumps(result)
        )
    )
    return {
        "ok": result["ok"],
        "status": result["status"],
        "route": result["route"],
        "children": [
            {
                "ok": c["ok"],
                "status": c["status"],
                "action": c["action"],
                "children": [
                    {
                        k: leaf[k]
                        for k in (
                            "ok",
                            "action",
                            "argv",
                            "dry_run",
                            "preflight_errors",
                            "status",
                            "returncode",
                            "write_audit",
                        )
                        if k in leaf
                    }
                    for leaf in c["children"]
                ],
            }
            for c in result["children"]
        ],
    }


class LogsRouteTests(unittest.TestCase):
    maxDiff = None

    def test_generator_provenance_identity_and_native_registration(self):
        spec = importlib.util.spec_from_file_location(
            "logs_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.reasoning_logs_route_descriptor(), DOCUMENT)
        self.assertEqual(DOCUMENT["id"], "route_control_reasoning_logs_workflow")
        self.assertEqual(DOCUMENT["lifecycle"], "active")
        self.assertEqual(
            DOCUMENT["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 17},
        )
        self.assertEqual(DOCUMENT["policy"]["failure"]["retry"]["max_attempts"], 1)
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
        for s in DOCUMENT["provenance"]["sources"]:
            self.assertEqual(
                s["digest"],
                "sha256:" + hashlib.sha256((ROOT / s["path"]).read_bytes()).hexdigest(),
            )
        native = checked_registry(REGISTRY)
        self.assertEqual(native[ACTION].depends_on, DEPENDENCIES)
        self.assertFalse(native[ACTION].command)
        self.assertTrue(
            all(native[key].timeout_seconds is None for key in DEPENDENCIES)
        )
        self.assertEqual(selected_match(MATCH).route.action_ids, (ACTION,))
        forged = deepcopy(REGISTRY)
        forged[DEPENDENCIES[0]]["command"] = ["forged"]
        with self.assertRaisesRegex(ValueError, "projection"):
            checked_registry(forged)

    def test_native_guards_sticky_state_and_external_compiler_boundary(self):
        item = hub.build_registry()[ACTION]
        for args, seen, status in [
            ((), None, "accepted"),
            (("extra",), None, "extra_args_for_sequence"),
            ((), {ACTION}, "dependency_cycle"),
        ]:
            admission = hub.admit_action(ACTION, hub.build_registry(), args, seen)
            self.assertEqual(admission["status"], status)
            if status != "accepted":
                self.assertFalse(hub.reject_action(ACTION, admission)["ok"])
        self.assertEqual(
            hub.admit_action(ACTION, {}, (), {ACTION})["status"], "unknown_action"
        )
        state = hub.initialize_dependencies(
            hub.admit_action(ACTION, hub.build_registry())
        )
        for i in range(6):
            state, done = hub.advance_dependencies(
                item, state, {"ok": i != 0}, hub.RunContext(keep_going=True)
            )
            check_dependencies(state)
            self.assertEqual(state["index"], i + 1)
            self.assertEqual(len(state["children"]), i + 1)
            self.assertFalse(state["dependencies_ok"])
            self.assertEqual(done, i == 5)
        with self.assertRaisesRegex(ValueError, "out of bounds"):
            check_dependencies(state, visiting=True)
        with self.assertRaisesRegex(ValueError, "accumulator"):
            check_dependencies({**state, "dependencies_ok": True})
        self.assertEqual(
            hub.finish_dependencies(item, state)["status"], "sequence_failed"
        )
        self.assertFalse(
            hub.dependency_command_guard(item, state, hub.RunContext(keep_going=True))
        )
        mutating = replace(item, safety="writes_repo")
        self.assertTrue(hub.preflight(mutating, hub.RunContext(), ()))
        self.assertEqual(hub.preflight(mutating, hub.RunContext(dry_run=True), ()), [])
        self.assertEqual(
            hub.preflight(mutating, hub.RunContext(allow_mutating=True), ()), []
        )
        # Only an external compiler boundary is substituted. Native capture,
        # timeout, preflight and write auditing all execute unchanged.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            saved = hub.subprocess
            try:
                for mode in ["success", "reject", "write", "launch_error", "timeout"]:
                    leaf = replace(
                        hub.build_registry()[DEPENDENCIES[0]],
                        command=("fixture-reasoning-compiler", mode),
                        required_paths=(),
                        timeout_seconds=3 if mode == "timeout" else None,
                    )
                    calls = install(hub, root)
                    if mode == "launch_error":
                        with self.assertRaisesRegex(OSError, "launch failed"):
                            hub.run_action(
                                leaf.action_id,
                                {leaf.action_id: leaf},
                                hub.RunContext(),
                                repository_root=root,
                            )
                    else:
                        result = hub.run_action(
                            leaf.action_id,
                            {leaf.action_id: leaf},
                            hub.RunContext(),
                            repository_root=root,
                        )
                        self.assertEqual(result["ok"], mode == "success")
                        self.assertEqual(
                            result["status"],
                            (
                                "timeout"
                                if mode == "timeout"
                                else (
                                    "undeclared_writes"
                                    if mode == "write"
                                    else "completed"
                                )
                            ),
                        )
                        if mode != "timeout":
                            self.assertEqual(
                                json.loads(result["stdout"])["artifact"]["nodes"],
                                ["input", "check"],
                            )
                            self.assertEqual(
                                result["returncode"], 7 if mode == "reject" else 0
                            )
                    self.assertEqual(
                        calls,
                        [{"argv": list(leaf.command), "timeout": leaf.timeout_seconds}],
                    )
            finally:
                hub.subprocess = saved

    def test_registered_tools_service_policy(self):
        async def scenario():
            server = FastMCP("logs-policy")
            flags = {"allow": False, "path": True}

            def authorize():
                if not flags["allow"]:
                    raise PermissionError("service is read-only")

            register_reasoning_logs_route_tools(
                server, authorize, lambda path: flags["path"]
            )
            state = hub.initialize_dependencies(
                hub.admit_action(ACTION, checked_registry(REGISTRY))
            )
            args = dict(
                action_id=ACTION,
                state={"accepted": True, "dependencies": state, "rejection": None},
                registry=REGISTRY,
                context=vars(hub.RunContext()),
                repository_root=str(Path(gettempdir()) / "logs-policy"),
            )
            for allow, path, message in [
                (False, True, "read-only"),
                (True, False, "service roots"),
            ]:
                flags.update(allow=allow, path=path)
                with self.assertRaisesRegex(Exception, message):
                    await server.call_tool(
                        "mathformer_logs_route_visit_dependency", args
                    )
            args["context"]["dry_run"] = True
            await server.call_tool("mathformer_logs_route_visit_dependency", args)

        asyncio.run(scenario())

    def test_registered_mcp_real_lunar_prism_runtime_and_native_parity(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        manager = SessionManager()
        error = None
        code = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        async with manager.open(
            "logs-route",
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
            compiled = compile_workflow("mcp:logs-route", docs[0], advertised)
            return compiled, assets

        compiled, assets = compile_document(DOCUMENT)
        self.assertTrue(compiled["runnable"], compiled["diagnostics"])
        self.assertEqual(compiled["runtime_status"], "ready")
        self.assertTrue(compiled["prism_source"])
        self.assertTrue(compiled["runtime_source"])
        self.assertEqual(set(compiled["bindings"]), set(DOCUMENT["operations"]))
        rejected, _ = compile_document(
            DOCUMENT,
            [t for t in tools if t["name"] != "mathformer_logs_route_visit_dependency"],
        )
        self.assertFalse(rejected["runnable"])

        async def authorize():
            pass

        async def run(inputs, changed=None):
            workflow, received = (
                compile_document(changed) if changed else (compiled, assets)
            )
            self.assertTrue(workflow["runnable"], workflow["diagnostics"])
            return await execute(workflow, received, inputs, remote, authorize)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            base = dict(
                context=vars(hub.RunContext()),
                match=MATCH,
                registry=REGISTRY,
                repository_root=str(root),
            )
            for ready in [False, True]:
                if ready:
                    populate(root, ROOT)
                for dry in [True, False]:
                    for keep in [False, True]:
                        inputs = deepcopy(base)
                        inputs["context"].update(dry_run=dry, keep_going=keep)
                        # Fresh trees keep preconditions identical for each native comparison.
                        for path in [root / "artifacts"]:
                            if path.exists():
                                import shutil

                                shutil.rmtree(path)
                        result = await run(inputs)
                        if ready and not dry and keep:
                            index = json.loads(
                                result["outputs"]["result"]["children"][0]["children"][
                                    4
                                ]["stdout"]
                            )
                            entry = index["entries"][0]
                            self.assertEqual(
                                entry["log_sha256"],
                                hashlib.sha256(
                                    (root / entry["log_file"]).read_bytes()
                                ).hexdigest(),
                            )
                            summary_file = root / entry["reports"]["summary_json"]
                            self.assertIn(entry["log_sha256"][:10], summary_file.name)
                            summary = json.loads(summary_file.read_text())
                            self.assertTrue(summary["ok"])
                            self.assertEqual(summary["event_count"], 2)
                        if (root / "artifacts").exists():
                            import shutil

                            shutil.rmtree(root / "artifacts")
                        expected = original().run_intent_match(
                            selected_match(MATCH),
                            checked_registry(REGISTRY),
                            hub.RunContext(**inputs["context"]),
                            repository_root=root,
                        )
                        self.assertEqual(result["status"], "accepted", result)
                        actual = result["outputs"]["result"]
                        self.assertEqual(outcomes(actual), outcomes(expected))
                        self.assertEqual(actual["route"]["score"], 23)
                        self.assertEqual(
                            actual["route"]["matched_terms"], MATCH["matched_terms"]
                        )
                        children = actual["children"][0]["children"]
                        count = 6 if keep or (ready and dry) else 3 if ready else 1
                        self.assertEqual(len(children), count)
                        self.assertEqual(actual["ok"], ready and dry)
                        order = (
                            ["initialize_route", "admit", "initialize_dependencies"]
                            + ["visit_dependency", "advance_dependencies"] * count
                            + ["finish_dependencies", "finish_route"]
                        )
                        self.assertEqual(
                            [c["operation"] for c in result["calls"]], order
                        )
                        self.assertEqual(
                            [c["tool"] for c in result["calls"]],
                            ["mathformer_logs_route_" + op for op in order],
                        )
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["replay_artifacts"])
                        if ready and not dry:
                            self.assertTrue(json.loads(children[0]["stdout"])["ok"])
                            self.assertEqual(children[0]["returncode"], 0)
                            self.assertEqual(children[2]["status"], "undeclared_writes")
                            self.assertEqual(children[2]["returncode"], 0)
                            if keep:
                                self.assertEqual(children[4]["returncode"], 0)
                                index = json.loads(children[4]["stdout"])
                                self.assertEqual(index["log_count"], 1)
                                self.assertTrue(index["ok"])
                                self.assertTrue(json.loads(children[5]["stdout"])["ok"])
                                self.assertEqual(children[5]["returncode"], 0)
                                self.assertFalse(actual["ok"])
            # Assert transported state and immutable ordered histories through
            # the registered interfaces, including the exact sixth-item stop.
            admission = await remote.call(
                "mathformer_logs_route_admit",
                {"action_id": ACTION, "registry": REGISTRY},
            )
            seeded = await remote.call(
                "mathformer_logs_route_initialize_dependencies", admission
            )
            state = seeded["state"]
            self.assertEqual(
                state["dependencies"],
                {
                    "index": 0,
                    "children": [],
                    "dependencies_ok": True,
                    "ancestry": [ACTION],
                },
            )
            for index in range(6):
                before = deepcopy(state)
                child = await remote.call(
                    "mathformer_logs_route_visit_dependency",
                    dict(
                        action_id=ACTION,
                        state=state,
                        context=vars(hub.RunContext(dry_run=True)),
                        registry=REGISTRY,
                        repository_root=str(root),
                    ),
                )
                advanced = await remote.call(
                    "mathformer_logs_route_advance_dependencies",
                    dict(
                        action_id=ACTION,
                        state=state,
                        child=child["result"],
                        context=vars(hub.RunContext(dry_run=True)),
                        registry=REGISTRY,
                    ),
                )
                self.assertEqual(state, before)
                state = advanced["state"]
                self.assertEqual(state["dependencies"]["index"], index + 1)
                self.assertEqual(
                    state["dependencies"]["children"],
                    before["dependencies"]["children"] + [child["result"]],
                )
                self.assertTrue(state["dependencies"]["dependencies_ok"])
                self.assertEqual(advanced["done"], index == 5)
            with self.assertRaisesRegex(Exception, "MCP server rejected"):
                await remote.call(
                    "mathformer_logs_route_visit_dependency",
                    dict(
                        action_id=ACTION,
                        state=state,
                        context=vars(hub.RunContext(dry_run=True)),
                        registry=REGISTRY,
                        repository_root=str(root),
                    ),
                )
            finished = await remote.call(
                "mathformer_logs_route_finish_dependencies",
                dict(action_id=ACTION, state=state, registry=REGISTRY),
            )
            self.assertEqual(
                finished["result"]["children"], state["dependencies"]["children"]
            )
            self.assertEqual(finished["result"]["status"], "sequence_completed")
            # A real subprocess failure (101 is the native smoke threshold)
            # propagates as result data and respects both stopping policies.
            with tempfile.TemporaryDirectory() as small:
                small_root = Path(small).resolve()
                populate(small_root, ROOT, count=100)
                for keep in [False, True]:
                    inputs = deepcopy(base)
                    inputs["repository_root"] = str(small_root)
                    inputs["context"]["keep_going"] = keep
                    result = await run(inputs)
                    actual = result["outputs"]["result"]
                    children = actual["children"][0]["children"]
                    self.assertEqual(result["status"], "accepted")
                    self.assertFalse(actual["ok"])
                    self.assertEqual(actual["status"], "intent_run_failed")
                    self.assertEqual(len(children), 6 if keep else 1)
                    self.assertEqual(children[0]["returncode"], 3)
                    self.assertEqual(children[0]["status"], "completed")
                    self.assertFalse(
                        json.loads(children[0]["stdout"])["checks"][
                            "coverage_has_all_skills"
                        ]
                    )
                    if keep:
                        self.assertTrue(children[-1]["ok"])
                        self.assertTrue(children[4]["write_audit"]["ok"])
            # writes_artifacts is permitted by native policy without allow_mutating.
            inputs = deepcopy(base)
            inputs["context"].update(
                dry_run=True, allow_mutating=False, keep_going=True
            )
            result = await run(inputs)
            children = result["outputs"]["result"]["children"][0]["children"]
            self.assertEqual(len(children), 6)
            self.assertTrue(all(child["ok"] for child in children))
            self.assertEqual(children[4]["preflight_errors"], [])
            # Empty registry takes the real rejection branch then preserves the
            # original entrypoint's missing-metadata KeyError at finalization.
            inputs = deepcopy(base)
            inputs["context"]["dry_run"] = True
            inputs["registry"] = {}
            with self.assertRaises(KeyError):
                original().run_intent_match(
                    selected_match(MATCH),
                    {},
                    hub.RunContext(dry_run=True),
                    repository_root=root,
                )
            result = await run(inputs)
            self.assertEqual(result["status"], "failed")
            self.assertIsNone(result["outputs"])
            self.assertEqual(
                [c["operation"] for c in result["calls"]],
                [
                    "initialize_route",
                    "admit",
                    "reject",
                    "retain_rejection",
                    "finish_dependencies",
                    "finish_route",
                ],
            )
            # Missing one leaf is native result data and respects early stop.
            inputs = deepcopy(base)
            inputs["context"]["dry_run"] = True
            del inputs["registry"][DEPENDENCIES[1]]
            result = await run(inputs)
            children = result["outputs"]["result"]["children"][0]["children"]
            self.assertEqual(len(children), 2)
            self.assertEqual(children[1]["status"], "unknown_action")
            # Shape-valid registry/route forgery and cursor corruption fail tools.
            for kind in ["registry", "route", "cursor"]:
                inputs = deepcopy(base)
                inputs["context"]["dry_run"] = True
                changed = None
                if kind == "registry":
                    inputs["registry"][ACTION]["depends_on"] = []
                elif kind == "route":
                    inputs["match"]["route_id"] = "forged"
                else:
                    changed = deepcopy(DOCUMENT)
                    changed["flow"]["steps"][3]["body"]["cases"][0]["body"]["steps"][0][
                        "arguments"
                    ]["state"] = {
                        "literal": {
                            "accepted": True,
                            "dependencies": {
                                "index": 6,
                                "children": [],
                                "dependencies_ok": True,
                                "ancestry": [ACTION],
                            },
                            "rejection": None,
                        }
                    }
                if kind == "route":
                    with self.assertRaisesRegex(Exception, "payload does not satisfy"):
                        await run(inputs, changed)
                    with self.assertRaisesRegex(Exception, "MCP server rejected"):
                        await remote.call(
                            "mathformer_logs_route_initialize_route",
                            {"match": inputs["match"]},
                        )
                    continue
                result = await run(inputs, changed)
                self.assertEqual(result["status"], "failed")
                self.assertIsNone(result["outputs"])
            inputs = deepcopy(base)
            inputs["context"]["dry_run"] = True
            # Six is an exact natural bound. Five exhausts before finalization.
            changed = deepcopy(DOCUMENT)
            changed["flow"]["steps"][3]["max_iterations"] = 5
            result = await run(inputs, changed)
            self.assertEqual(result["status"], "failed")
            self.assertIsNone(result["outputs"])
            self.assertEqual(
                sum(c["operation"] == "visit_dependency" for c in result["calls"]), 5
            )
            for cap in [1, 16]:
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
            changed = deepcopy(DOCUMENT)
            changed["policy"]["limits"]["wall_time_seconds"] = 1
            timed, received = compile_document(changed)

            async def waiting_authority():
                await asyncio.Event().wait()

            with self.assertRaises(TimeoutError):
                await execute(timed, received, inputs, remote, waiting_authority)
            # Default mount is safe to inspect only via native dry-run.
            inputs["repository_root"] = None
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
