#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Actual registered MCP tools and Lunar/PRISM compilation and execution.

Canonical quality actions are dry-run or preflight-only. Synthetic compiler
declarations exercise native leaf execution; only that external boundary is
substituted. No providers, credentials or production quality commands are used.
"""

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
SITES = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
FIXTURES = ROOT / "tests/mcp/fixtures"
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT),
    str(FIXTURES),
]
sys.path.extend(SITES)

import asyncio
from copy import deepcopy
from dataclasses import asdict, replace
import hashlib
import importlib.util
import json
import tempfile
import unittest
from unittest.mock import patch
import yaml

import mathformer as hub
from quality_smoke_route_tools import ACTION, ROUTE, checked_registry, selected_match
from quality_smoke_route_compiler import Compiler
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_quality_smoke_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
AUTHORED = "skills/control/workflow-contract-validator/references/quality-smoke-route.workflow.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
NATIVE = hub.build_registry()
route = next(row for row in hub.build_intent_routes() if row.route_id == ROUTE)
MATCH = {
    "route": json.loads(json.dumps(asdict(route))),
    "score": 23,
    "matched_terms": ["compact", "quality"],
}
KEYS = [ACTION, *NATIVE[ACTION].depends_on, *NATIVE["control:all"].depends_on]
REGISTRY = {key: hub.action_to_dict(NATIVE[key]) for key in KEYS}


def original():
    scope = dict(vars(hub))
    exec((FIXTURES / "quality_smoke_route_original.py.txt").read_text(), scope)
    return scope


def snapshot(document):
    paths = {SCHEMA} | {row["path"] for row in document["provenance"]["sources"]}
    values = {path: (ROOT / path).read_text() for path in paths}
    values[DESCRIPTOR] = json.dumps(document)
    return [
        dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )
        for path, text in values.items()
    ]


def populate(root):
    # Preflight-only inputs: no placeholder is ever executed.
    for key in KEYS:
        for relative in NATIVE[key].required_paths:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch(exist_ok=True)


class QualitySmokeRouteTests(unittest.TestCase):
    maxDiff = None

    def test_identity_provenance_and_generator(self):
        document = yaml.safe_load(CONTRACT.read_text())
        spec = importlib.util.spec_from_file_location(
            "smoke_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)
        self.assertEqual(generator.quality_smoke_route_descriptor(), document)
        self.assertEqual(json.loads((ROOT / AUTHORED).read_text()), document)
        self.assertEqual(document["id"], "route_quality_smoke_workflow")
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
        self.assertEqual(checked_registry(REGISTRY), {key: NATIVE[key] for key in KEYS})
        self.assertEqual(len(NATIVE["control:all"].depends_on), 9)
        self.assertEqual(
            NATIVE[ACTION].depends_on,
            ("control:all", "test:quick", "test:docs", "rocq:wiki-suite", "kb:e2e"),
        )

    def test_native_compiler_outcomes_and_source_parity(self):
        oracle = original()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for mode in ["pass", "fail", "timeout", "write", "artifact", "crash"]:
                for keep in [False, True]:
                    registry = {
                        ACTION: replace(
                            NATIVE[ACTION],
                            depends_on=("fixture:first", "fixture:second"),
                        )
                    }
                    for key, outcome in [("first", mode), ("second", "pass")]:
                        registry["fixture:" + key] = hub.WorkflowAction(
                            "fixture:" + key,
                            "external compiler",
                            "quality",
                            "validation",
                            "writes_artifacts",
                            command=("fixture-quality-compiler", outcome),
                            writes=("artifacts/",),
                            timeout_seconds=31,
                        )
                    results, traces = [], []
                    for runner in [oracle["run_intent_match"], hub.run_intent_match]:
                        (root / "undeclared.txt").unlink(missing_ok=True)
                        (root / "artifacts/compiled.json").unlink(missing_ok=True)
                        fixture = Compiler(root)
                        with patch.object(hub.subprocess, "run", fixture):
                            if mode == "crash":
                                with self.assertRaisesRegex(
                                    OSError, "compiler launch failed"
                                ):
                                    runner(
                                        selected_match(MATCH),
                                        registry,
                                        hub.RunContext(keep_going=keep),
                                        repository_root=root,
                                    )
                            else:
                                results.append(
                                    runner(
                                        selected_match(MATCH),
                                        registry,
                                        hub.RunContext(keep_going=keep),
                                        repository_root=root,
                                    )
                                )
                        traces.append(fixture.calls)
                    self.assertEqual(*traces)
                    self.assertEqual(
                        len(traces[0]),
                        (
                            2
                            if mode in ["pass", "artifact"]
                            or (keep and mode != "crash")
                            else 1
                        ),
                    )
                    if results:
                        self.assertEqual(*results)
                        result = results[0]
                        ok = mode in ["pass", "artifact"]
                        self.assertEqual(result["ok"], ok)
                        self.assertEqual(
                            result["status"],
                            "intent_run_completed" if ok else "intent_run_failed",
                        )
                        action = result["children"][0]
                        self.assertEqual(action["ok"], ok)
                        self.assertEqual(len(action["children"]), len(traces[0]))
                        if keep and not ok:
                            self.assertTrue(action["children"][1]["ok"])
                            self.assertEqual(action["status"], "sequence_failed")
                        leaf = action["children"][0]
                        if mode == "fail":
                            self.assertEqual(
                                (leaf["returncode"], leaf["stderr"]),
                                (7, "compiler stderr"),
                            )
                        if mode == "timeout":
                            self.assertEqual(
                                (
                                    leaf["status"],
                                    leaf["timeout_seconds"],
                                    leaf["stdout"],
                                ),
                                ("timeout", 31, "partial"),
                            )
                        if mode == "write":
                            self.assertEqual(leaf["status"], "undeclared_writes")
                            self.assertEqual(
                                leaf["write_audit"]["unexpected_paths"],
                                ["undeclared.txt"],
                            )
                        if mode in ["pass", "artifact"]:
                            self.assertFalse(json.loads(leaf["stdout"])["ok"])
                            self.assertTrue(
                                leaf["ok"]
                            )  # native exit status, not embedded claims
                            self.assertTrue(leaf["write_audit"]["ok"])
            for runner in [oracle["run_action"], hub.run_action]:
                for seen, args, expected in [
                    ([ACTION], ["x"], "dependency_cycle"),
                    ([], ["x"], "extra_args_for_sequence"),
                ]:
                    self.assertEqual(
                        runner(
                            ACTION,
                            NATIVE,
                            hub.RunContext(dry_run=True),
                            seen=set(seen),
                            extra_args=args,
                        )["status"],
                        expected,
                    )
                cyclic = {ACTION: replace(NATIVE[ACTION], depends_on=(ACTION,))}
                self.assertEqual(
                    runner(ACTION, cyclic, hub.RunContext())["children"][0]["cycle"],
                    [ACTION],
                )
                self.assertEqual(
                    runner(ACTION, {}, hub.RunContext())["status"], "unknown_action"
                )

    def test_actual_registered_service_ceilings(self):
        asyncio.run(self.service_ceilings())

    async def service_ceilings(self):
        import mcp_server as server

        args = dict(
            action_id=ACTION,
            registry=REGISTRY,
            context=vars(hub.RunContext()),
            repository_root=str(Path(gettempdir())),
        )
        for readonly, roots, message in [
            (True, None, "read-only"),
            (False, [Path(str(Path(gettempdir()) / "restricted"))], "service roots"),
        ]:
            with (
                patch.object(server, "_READONLY", readonly),
                patch.object(server, "_ALLOWED_WRITE_ROOTS", roots),
            ):
                with self.assertRaisesRegex(Exception, message):
                    await server.mcp.call_tool(
                        "mathformer_quality_smoke_route_execute_action", args
                    )
        self.assertEqual(
            server._cap_unbounded_timeouts({key: NATIVE[key] for key in KEYS})[
                "test:quick"
            ].timeout_seconds,
            600,
        )

    def test_real_mcp_lunar_prism(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(CONTRACT.read_text())
        oracle = original()["run_intent_match"]
        import mcp_server as server

        manager = SessionManager()
        startup = (
            "import os,sys;sys.dont_write_bytecode=True;os.environ.clear();"
            'os.environ["PYTHONDONTWRITEBYTECODE"]="1";sys.path[:0]='
            + repr([str(ROOT / "scripts"), *SITES])
            + ';from mcp_server import mcp;mcp.run(transport="stdio")'
        )
        failure = None
        async with manager.open(
            "quality-smoke-route",
            StdioConfig(command=sys.executable, args=["-c", startup], cwd=str(ROOT)),
            {},
        ) as remote:
            try:
                tools = [
                    tool.model_dump(by_alias=True, exclude_none=True)
                    for tool in await remote.tools()
                ]

                def compile_document(doc, inventory=tools):
                    assets = snapshot(doc)
                    return (
                        compile_workflow(
                            "mcp:quality-smoke-route",
                            workflow_documents([DESCRIPTOR], assets)[0],
                            inventory,
                        ),
                        assets,
                    )

                workflow, assets = compile_document(document)
                self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                self.assertTrue(workflow["prism_source"])
                self.assertTrue(workflow["runtime_source"])
                self.assertEqual(set(workflow["bindings"]), set(document["operations"]))
                self.assertFalse(compile_document(document, [])[0]["runnable"])
                advertised = {row["name"]: row for row in tools}
                for op in document["operations"].values():
                    binding = op["execution"]["binding"]
                    self.assertEqual(binding["target"], binding["operation"])
                    interface = advertised[binding["target"]]
                    self.assertEqual(
                        set(interface["inputSchema"]["properties"]), set(op["inputs"])
                    )
                    self.assertEqual(
                        set(interface["outputSchema"]["properties"]), set(op["outputs"])
                    )

                async def authorize():
                    pass

                async def run(inputs, doc=document):
                    w, a = (
                        (workflow, assets) if doc is document else compile_document(doc)
                    )
                    self.assertTrue(w["runnable"], w["diagnostics"])
                    return await execute(w, a, inputs, remote, authorize)

                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory).resolve()
                    for ready in [False, True]:
                        if ready:
                            populate(root)
                        for keep in [False, True]:
                            for missing in [None, *NATIVE[ACTION].depends_on]:
                                registry = {
                                    key: value
                                    for key, value in REGISTRY.items()
                                    if key != missing
                                }
                                inputs = dict(
                                    match=MATCH,
                                    registry=registry,
                                    context=vars(
                                        hub.RunContext(dry_run=True, keep_going=keep)
                                    ),
                                    repository_root=str(root),
                                )
                                expected = oracle(
                                    selected_match(MATCH),
                                    server._cap_unbounded_timeouts(
                                        checked_registry(registry)
                                    ),
                                    hub.RunContext(**inputs["context"]),
                                    repository_root=root,
                                )
                                result = await run(inputs)
                                self.assertEqual(result["status"], "accepted", result)
                                self.assertEqual(
                                    result["outputs"], {"result": expected}
                                )
                                self.assertEqual(
                                    [c["operation"] for c in result["calls"]],
                                    [
                                        "initialize",
                                        "select",
                                        "execute_action",
                                        "advance",
                                        "finish",
                                    ],
                                )
                                self.assertEqual(len(expected["children"]), 1)
                                self.assertLessEqual(
                                    len(expected["children"][0]["children"]), 5
                                )
                                if keep:
                                    self.assertEqual(
                                        len(expected["children"][0]["children"]), 5
                                    )
                                self.assertTrue(result["runtime"]["effect_records"])
                                self.assertTrue(result["runtime"]["provenance"])
                                self.assertTrue(result["replay_artifacts"])
                    self.assertFalse((root / "artifacts").exists())
                    inputs = dict(
                        match=MATCH,
                        registry=REGISTRY,
                        context=vars(hub.RunContext(dry_run=True, keep_going=True)),
                        repository_root=str(root),
                    )
                    self.assertTrue((await run(inputs))["outputs"]["result"]["ok"])
                    # Completed on iteration one, including failure; no exhaustion
                    # is reachable for the declared immutable route. Force the
                    # predicate false to verify real PRISM exhaustion behavior.
                    exhausted = deepcopy(document)
                    exhausted["flow"]["steps"][1]["until"] = {"literal": False}
                    result = await run(inputs, exhausted)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]],
                        ["initialize", "select", "execute_action", "advance"],
                    )
                    self.assertEqual(result["failure_disposition"], "fail")
                    budget = deepcopy(document)
                    budget["policy"]["limits"]["max_operation_calls"] = 4
                    result = await run(inputs, budget)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(
                        sum(
                            bool(c.get("transport_call_performed"))
                            for c in result["calls"]
                        ),
                        4,
                    )
                    # Unknown top-level action produces native failure data, then
                    # source finish raises KeyError for missing route metadata.
                    result = await run({**inputs, "registry": {}})
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(result["calls"][-1]["operation"], "finish")
                    broken = deepcopy(REGISTRY)
                    broken[ACTION]["command"] = ["arbitrary-command"]
                    result = await run({**inputs, "registry": broken})
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(result["calls"][-1]["operation"], "execute_action")
                    state = (
                        await remote.call(
                            "mathformer_quality_smoke_route_initialize", {}
                        )
                    )["state"]
                    advanced = await remote.call(
                        "mathformer_quality_smoke_route_advance",
                        dict(
                            state=state,
                            child={"ok": False, "status": "native_failure"},
                            context=inputs["context"],
                        ),
                    )
                    self.assertEqual(
                        advanced,
                        {
                            "state": {
                                "ok": False,
                                "children": [{"ok": False, "status": "native_failure"}],
                            },
                            "done": True,
                        },
                    )
                    self.assertEqual(state, {"ok": True, "children": []})
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_quality_smoke_route_select",
                            dict(state=advanced["state"], match=MATCH),
                        )
                    # Optional repository mount preserves the native default.
                    request = {
                        key: value
                        for key, value in inputs.items()
                        if key != "repository_root"
                    }
                    result = await run(request)
                    expected = oracle(
                        selected_match(MATCH),
                        server._cap_unbounded_timeouts(checked_registry(REGISTRY)),
                        hub.RunContext(**request["context"]),
                    )
                    self.assertEqual(result["outputs"], {"result": expected})
                # Empty mount exercises actual recursive preflight without launch.
                with tempfile.TemporaryDirectory() as directory:
                    inputs["repository_root"] = directory
                    inputs["context"]["dry_run"] = False
                    # repo:diff-check has no required paths. Omit it explicitly;
                    # every remaining leaf must reject on a missing path.
                    inputs["registry"] = {
                        key: value
                        for key, value in REGISTRY.items()
                        if key != "repo:diff-check"
                    }
                    self.assertTrue(
                        all(
                            item["required_paths"]
                            for item in inputs["registry"].values()
                            if item["command"]
                        )
                    )
                    for keep in [False, True]:
                        inputs["context"]["keep_going"] = keep
                        result = await run(inputs)
                        expected = oracle(
                            selected_match(MATCH),
                            server._cap_unbounded_timeouts(
                                checked_registry(inputs["registry"])
                            ),
                            hub.RunContext(**inputs["context"]),
                            repository_root=Path(directory).resolve(),
                        )
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertEqual(result["outputs"], {"result": expected})
                        self.assertFalse(expected["ok"])
                        self.assertEqual(
                            len(expected["children"][0]["children"]), 5 if keep else 1
                        )
                    timed = deepcopy(document)
                    timed["policy"]["limits"]["wall_time_seconds"] = 1
                    w, a = compile_document(timed)
                    self.assertTrue(w["runnable"], w["diagnostics"])

                    async def stalled_authority():
                        await asyncio.Event().wait()

                    with self.assertRaises(TimeoutError):
                        await execute(w, a, inputs, remote, stalled_authority)
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
