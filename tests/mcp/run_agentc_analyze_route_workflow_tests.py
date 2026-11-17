#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Real native steps, production MCP registration and Lunar PRISM execution.

All launches use disposable repositories. The analyzer is tested only with its
native missing mandatory argument (no reports, models or provers). The generic
controller additionally uses the deterministic external compiler fixture.
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
sys.path[:0] = [str(LUNAR / "app/backend"), str(ROOT / "scripts")]
sys.path.extend(str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages"))

import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib.util
import json
import shutil
import tempfile
import unittest
from unittest.mock import patch
import yaml

import mathformer as hub
from agentc_analyze_route_tools import selected_match
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_agentc_analyze_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
ANALYZER = "skills/autoformalization/autoformalization-agentc/scripts/analyze_logs.py"
COMPILER = ROOT / "tests/mcp/fixtures/adoption_compiler.py"
MATCH = {"score": 13, "matched_terms": ["analyze", "agentc logs"]}


def original():
    scope = dict(vars(hub))
    exec(
        (ROOT / "tests/mcp/fixtures/agentc_analyze_route_original.py.txt").read_text(),
        scope,
    )
    return scope["run_intent_match"]


def populate(mount):
    """Mount the actual analyzer and its real sibling; no report inputs exist."""
    for path in [ANALYZER, str(Path(ANALYZER).with_name("agentc.py"))]:
        target = mount / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, target)


def snapshot(document):
    def asset(path, content):
        return {
            "path": path,
            "content": content,
            "encoding": "text",
            "sha256": hashlib.sha256(content.encode()).hexdigest(),
        }

    paths = {SCHEMA} | {row["path"] for row in document["provenance"]["sources"]}
    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(path, (ROOT / path).read_text()) for path in sorted(paths)
    ]


class AgentCAnalyzeRouteTests(unittest.TestCase):
    maxDiff = None

    def test_original_equivalence_and_native_exhaustion(self):
        registry = hub.build_registry()
        match = selected_match(MATCH)
        self.assertEqual(match.route.action_ids, ("agentc:analyze-logs",))
        self.assertFalse(registry[match.route.action_ids[0]].depends_on)
        self.assertIsNone(registry[match.route.action_ids[0]].timeout_seconds)
        with tempfile.TemporaryDirectory() as directory:
            mount = Path(directory).resolve()
            with patch.object(hub, "REPO_ROOT", mount):
                for mounted in [False, True]:
                    if mounted:
                        populate(mount)
                    for dry in [False, True]:
                        for keep in [False, True]:
                            context = hub.RunContext(dry_run=dry, keep_going=keep)
                            expected = original()(match, registry, context)
                            result = hub.run_intent_match(
                                match, registry, context, repository_root=mount
                            )
                            self.assertEqual(result, expected)
                            self.assertEqual(len(result["children"]), 1)
                            child = result["children"][0]
                            self.assertEqual(
                                child["argv"],
                                hub.resolve_command(
                                    registry["agentc:analyze-logs"].command
                                ),
                            )
                            self.assertEqual(result["ok"], mounted and dry)
                            if mounted and not dry:
                                self.assertEqual(child["returncode"], 2)
                                self.assertIn("--report-file", child["stderr"])
                                self.assertEqual(child["stdout"], "")
                                self.assertTrue(child["write_audit"]["ok"])
                            else:
                                self.assertNotIn("returncode", child)
                self.assertFalse((mount / "artifacts").exists())
                # Exercise the shared generic route controller through a compiler
                # boundary, retaining native early-stop and keep-going semantics.
                for mode in ["success", "fail", "write", "timeout", "preflight"]:
                    first = hub.WorkflowAction(
                        "fixture:first",
                        "compiler",
                        "test",
                        "validation",
                        "read_only",
                        command=(hub.PYTHON_TOKEN, str(COMPILER), mode),
                        required_paths=("absent",) if mode == "preflight" else (),
                        timeout_seconds=0.05 if mode == "timeout" else None,
                    )
                    second = replace(
                        first,
                        action_id="fixture:second",
                        required_paths=(),
                        command=(hub.PYTHON_TOKEN, str(COMPILER), "success"),
                        timeout_seconds=None,
                    )
                    fixture_registry = {
                        first.action_id: first,
                        second.action_id: second,
                    }
                    fixture_match = replace(
                        match,
                        route=replace(match.route, action_ids=tuple(fixture_registry)),
                    )
                    for keep in [False, True]:
                        observations = []
                        for runner in [original(), hub.run_intent_match]:
                            (mount / "undeclared.txt").unlink(missing_ok=True)
                            observations.append(
                                runner(
                                    fixture_match,
                                    fixture_registry,
                                    hub.RunContext(keep_going=keep),
                                )
                            )
                        self.assertEqual(*observations)
                        result = observations[1]
                        self.assertEqual(result["ok"], mode == "success")
                        self.assertEqual(
                            len(result["children"]),
                            2 if keep or mode == "success" else 1,
                        )
                        self.assertEqual(
                            result["children"][-1]["ok"], mode == "success" or keep
                        )
                        child = result["children"][0]
                        if mode == "fail":
                            self.assertEqual(child["returncode"], 7)
                        if mode == "write":
                            self.assertEqual(child["status"], "undeclared_writes")
                            self.assertEqual(
                                child["write_audit"]["unexpected_paths"],
                                ["undeclared.txt"],
                            )
                        if mode == "timeout":
                            self.assertEqual(child["status"], "timeout")
                        if mode == "preflight":
                            self.assertEqual(
                                child["preflight_errors"],
                                ["missing required path: absent"],
                            )
                # A successful later child cannot erase an earlier failure.
                state = hub.initialize_intent_state()
                before = deepcopy(state)
                state, done = hub.advance_intent_state(
                    state, {"ok": False}, hub.RunContext(keep_going=True), 2
                )
                self.assertFalse(done)
                state, done = hub.advance_intent_state(
                    state, {"ok": True}, hub.RunContext(keep_going=True), 2
                )
                self.assertTrue(done)
                self.assertFalse(state["ok"])
                self.assertEqual(before, {"ok": True, "children": []})
                # Empty routes remain successful; no synthetic visit is added.
                empty = replace(match, route=replace(match.route, action_ids=()))
                self.assertEqual(
                    hub.run_intent_match(empty, registry, hub.RunContext()),
                    original()(empty, registry, hub.RunContext()),
                )
                invalid = replace(
                    first,
                    required_paths=(),
                    command=(
                        str(Path(gettempdir()) / "nonexistent-agentc-route-executable"),
                    ),
                )
                with self.assertRaises(FileNotFoundError):
                    hub.run_intent_match(
                        replace(
                            match,
                            route=replace(match.route, action_ids=(invalid.action_id,)),
                        ),
                        {invalid.action_id: invalid},
                        hub.RunContext(),
                    )

    def test_native_generator_retains_authored_route(self):
        path = (
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py"
        )
        spec = importlib.util.spec_from_file_location("agentc_route_normalizer", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        route = module.agentc_analyze_route_descriptor()
        supplied = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(route, supplied)

    def test_registered_mcp_and_real_prism_runtime(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "route_agentc_analyze_workflow")
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 4},
        )
        self.assertEqual(document["flow"]["steps"][1]["max_iterations"], 1)
        self.assertEqual(document["flow"]["steps"][1]["on_exhausted"], "fail")
        self.assertIn(
            "scripts/mathformer.py",
            [row["path"] for row in document["provenance"]["sources"]],
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        failure = None
        async with manager.open(
            "agentc-route",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {
                "PYTHONPATH": os.pathsep.join(
                    str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")
                )
            },
        ) as remote:
            try:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile(doc):
                    assets = snapshot(doc)
                    workflow = compile_workflow(
                        "mcp:agentc-route",
                        workflow_documents([DESCRIPTOR], assets)[0],
                        tools,
                    )
                    self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                    self.assertTrue(workflow["runtime_source"])
                    self.assertEqual(set(workflow["bindings"]), set(doc["operations"]))
                    return workflow, assets

                workflow, assets = compile(document)

                async def authorize():
                    pass

                async def run(inputs, changed=None):
                    bound, received = (
                        compile(changed) if changed else (workflow, assets)
                    )
                    return await execute(bound, received, inputs, remote, authorize)

                with tempfile.TemporaryDirectory() as directory:
                    mount = Path(directory).resolve()
                    for mounted in [False, True]:
                        if mounted:
                            populate(mount)
                        for dry in [True, False]:
                            for keep in [False, True]:
                                context = vars(
                                    hub.RunContext(dry_run=dry, keep_going=keep)
                                )
                                inputs = {
                                    "context": context,
                                    "match": MATCH,
                                    "repository_root": str(mount),
                                }
                                result = await run(inputs)
                                self.assertEqual(result["status"], "accepted", result)
                                expected = hub.run_intent_match(
                                    selected_match(MATCH),
                                    hub.build_registry(),
                                    hub.RunContext(**context),
                                    repository_root=mount,
                                )
                                self.assertEqual(
                                    result["outputs"], {"result": expected}
                                )
                                self.assertEqual(
                                    [c["operation"] for c in result["calls"]],
                                    [
                                        "initialize",
                                        "invoke_action",
                                        "advance",
                                        "finish",
                                    ],
                                )
                                self.assertEqual(
                                    [c["tool"] for c in result["calls"]],
                                    [
                                        "mathformer_agentc_analyze_route_" + op
                                        for op in [
                                            "initialize",
                                            "invoke_action",
                                            "advance",
                                            "finish",
                                        ]
                                    ],
                                )
                                self.assertEqual(len(expected["children"]), 1)
                                self.assertTrue(result["runtime"]["effect_records"])
                                self.assertTrue(result["runtime"]["provenance"])
                                self.assertTrue(result["replay_artifacts"])
                                self.assertFalse((mount / "artifacts").exists())
                    # Both budget and operation errors stop dependent work with
                    # no retry, extra visit or successful final output.
                    for budget in [1, 2, 3]:
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
                    advance = changed["flow"]["steps"][1]["body"]["steps"][1]
                    advance["arguments"]["state"] = {
                        "literal": {"ok": False, "children": []}
                    }
                    result = await run(inputs, changed)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]],
                        ["initialize", "invoke_action", "advance"],
                    )
                    # Force the otherwise unreachable exhaustion guard via a
                    # test-only definition; the real runtime must reject it.
                    changed = deepcopy(document)
                    changed["flow"]["steps"][1]["until"] = {"literal": False}
                    result = await run(inputs, changed)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(
                        sum(c["operation"] == "invoke_action" for c in result["calls"]),
                        1,
                    )
                    self.assertFalse(
                        any(c["operation"] == "finish" for c in result["calls"])
                    )
                    timed = deepcopy(document)
                    timed["policy"]["limits"]["wall_time_seconds"] = 1
                    bound, received = compile(timed)

                    async def waiting_authority():
                        await asyncio.Event().wait()

                    with self.assertRaises(TimeoutError):
                        await execute(
                            bound, received, inputs, remote, waiting_authority
                        )
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure:
            raise failure
        # Run the production registration with its real service restrictions.
        # No tool, provider or controller implementation is replaced.
        for settings in [
            "service._READONLY=True",
            'service._ALLOWED_WRITE_ROOTS=[service.hub.REPO_ROOT / "blocked-fixture-root"]',
        ]:
            restricted = (
                'import sys;sys.path.insert(0,"scripts");import mcp_server as service;'
                + settings
                + ';service.mcp.run(transport="stdio")'
            )
            failure = None
            async with manager.open(
                "restricted",
                StdioConfig(
                    command=sys.executable, args=["-c", restricted], cwd=str(ROOT)
                ),
                {
                    "PYTHONPATH": os.pathsep.join(
                        str(p)
                        for p in (ROOT / ".venv/lib").glob("python*/site-packages")
                    )
                },
            ) as remote:
                try:
                    with tempfile.TemporaryDirectory() as directory:
                        mount = Path(directory).resolve()
                        populate(mount)
                        inputs = {
                            "context": vars(hub.RunContext(dry_run=True)),
                            "match": MATCH,
                            "repository_root": str(mount),
                        }
                        result = await execute(
                            workflow, assets, inputs, remote, authorize
                        )
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertTrue(result["outputs"]["result"]["ok"])
                        inputs["context"]["dry_run"] = False
                        result = await execute(
                            workflow, assets, inputs, remote, authorize
                        )
                        self.assertEqual(result["status"], "failed", result)
                        self.assertIsNone(result["outputs"])
                        self.assertEqual(
                            [c["operation"] for c in result["calls"]],
                            ["initialize", "invoke_action"],
                        )
                        self.assertFalse((mount / "artifacts").exists())
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
