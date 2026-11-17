#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native source, real registered MCP and Lunar/PRISM integration tests.

No production gate is run. Isolated mounts exercise real preflight and dry-run;
only external compiler processes in separate fixture actions are substituted.
The compiler/provider is absent from the selected route, so no model is needed.
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
from types import SimpleNamespace
import tempfile
import unittest
import yaml

import mathformer as hub
from reasoning_flow_route_tools import (
    ACTIONS,
    selected_match,
    checked_registry,
    check_state,
)
from reasoning_route_compiler import install
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_control_reasoning_flow_language_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
MATCH = {
    "route": {
        "route_id": "control.reasoning.flow.language",
        "action_ids": list(ACTIONS),
    },
    "score": 19,
    "matched_terms": ["reasoning", "flow", "language"],
}
REGISTRY = {key: hub.action_to_dict(hub.build_registry()[key]) for key in ACTIONS}


def original():
    scope = dict(vars(hub))
    exec(
        (ROOT / "tests/mcp/fixtures/reasoning_flow_route_original.py.txt").read_text(),
        scope,
    )
    return SimpleNamespace(**scope), scope


def populate(root, keys=ACTIONS):
    for key in keys:
        for relative in hub.build_registry()[key].required_paths:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch(exist_ok=True)


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


class ReasoningFlowRouteTests(unittest.TestCase):
    maxDiff = None

    def test_definition_generator_and_source_digests(self):
        path = (
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py"
        )
        spec = importlib.util.spec_from_file_location(
            "reasoning_route_normalizer", path
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        document = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(module.reasoning_flow_route_descriptor(), document)
        self.assertEqual(
            document["id"], "route_control_reasoning_flow_language_workflow"
        )
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 8},
        )
        self.assertEqual(document["policy"]["effects"]["filesystem"]["write"], [])
        self.assertEqual(document["policy"]["failure"]["retry"]["max_attempts"], 1)
        self.assertIn(
            "scripts/mathformer.py",
            [s["path"] for s in document["provenance"]["sources"]],
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        native = checked_registry(REGISTRY)
        self.assertEqual(
            native[ACTIONS[0]].command[2:],
            ("examples/reasoning_flows", "--strict", "--check-registries", "--json"),
        )
        self.assertEqual(native[ACTIONS[1]].command[2:], ("--check", "--json"))
        self.assertTrue(all(native[key].timeout_seconds is None for key in ACTIONS))
        self.assertEqual(selected_match(MATCH).route.action_ids, ACTIONS)

    def test_original_equivalence_and_ordered_state(self):
        oracle, _scope = original()
        native = checked_registry(REGISTRY)
        match = selected_match(MATCH)
        for available in [(), ACTIONS[:1], ACTIONS]:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                populate(root, available)
                for keep in [False, True]:
                    # No process can run: these are dry-run calls.
                    context = hub.RunContext(dry_run=True, keep_going=keep)
                    expected = oracle.run_intent_match(
                        match, native, context, repository_root=root
                    )
                    actual = hub.run_intent_match(
                        match, native, context, repository_root=root
                    )
                    self.assertEqual(actual, expected)
                    self.assertEqual(
                        len(actual["children"]), 2 if available or keep else 1
                    )
        for fail_at in [None, 0, 1]:
            for keep in [False, True]:
                context = hub.RunContext(keep_going=keep)
                state = hub.initialize_intent_state()
                for index in range(2):
                    before = deepcopy(state)
                    self.assertEqual(
                        hub.select_intent_action(state, match), ACTIONS[index]
                    )
                    child = {"ok": index != fail_at, "stdout": str(index)}
                    state, done = hub.advance_intent_state(state, child, context, 2)
                    self.assertEqual(state["children"], before["children"] + [child])
                    self.assertEqual(
                        before["children"],
                        [] if index == 0 else [{"ok": fail_at != 0, "stdout": "0"}],
                    )
                    self.assertEqual(
                        done, index == 1 or (index == fail_at and not keep)
                    )
                    check_state(state)
                    if done:
                        break
                result = hub.finish_intent_state(state, match, native)
                self.assertEqual(result["ok"], fail_at is None)
                self.assertEqual(
                    len(result["children"]), 1 if fail_at == 0 and not keep else 2
                )
                if fail_at == 0 and keep:
                    self.assertTrue(result["children"][1]["ok"])
                    self.assertFalse(result["ok"])

    def test_compiler_boundary_native_capture_audit_and_exceptions(self):
        oracle, scope = original()
        match = selected_match(MATCH)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for mode in ["success", "reject", "write", "launch_error", "timeout"]:
                for position in [0, 1]:
                    for keep in [False, True]:
                        registry = {
                            key: replace(
                                hub.build_registry()[key],
                                command=(
                                    "fixture-reasoning-compiler",
                                    mode if i == position else "success",
                                ),
                                required_paths=(),
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
                                        OSError, "fixture compiler launch failed"
                                    ):
                                        source.run_intent_match(
                                            match,
                                            registry,
                                            hub.RunContext(keep_going=keep),
                                            repository_root=root,
                                        )
                                else:
                                    results.append(
                                        source.run_intent_match(
                                            match,
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
                        self.assertEqual(histories[0], histories[1])
                        self.assertEqual(
                            len(histories[0]),
                            (
                                position + 1
                                if mode == "launch_error"
                                or (mode != "success" and not keep)
                                else 2
                            ),
                        )
                        if mode == "launch_error":
                            continue
                        self.assertEqual(results[0], results[1])
                        result = results[0]
                        self.assertEqual(result["ok"], mode == "success")
                        child = result["children"][position]
                        if mode == "success":
                            self.assertTrue(child["ok"])
                            self.assertFalse(json.loads(child["stdout"])["ok"])
                            self.assertEqual(child["returncode"], 0)
                        elif mode == "reject":
                            self.assertEqual(child["returncode"], 7)
                            self.assertEqual(
                                child["stderr"], "fixture compiler diagnostic"
                            )
                        elif mode == "write":
                            self.assertEqual(child["status"], "undeclared_writes")
                            self.assertEqual(
                                child["write_audit"]["unexpected_paths"],
                                ["undeclared.txt"],
                            )
                        else:
                            self.assertEqual(child["status"], "timeout")
                            self.assertEqual(child["stdout"], "partial")
                            self.assertIsNone(child["returncode"])
                            self.assertEqual(histories[0][position]["timeout"], 3)

    def test_real_registered_mcp_and_lunar_prism_runtime(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(CONTRACT.read_text())
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        async with manager.open(
            "reasoning-route",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {"PYTHONPATH": os.pathsep.join(SITES), "PYTHONDONTWRITEBYTECODE": "1"},
        ) as remote:
            tools = [
                t.model_dump(by_alias=True, exclude_none=True)
                for t in await remote.tools()
            ]

            def compile(doc):
                assets = snapshot(doc)
                compiled = compile_workflow(
                    "mcp:reasoning-route",
                    workflow_documents([DESCRIPTOR], assets)[0],
                    tools,
                )
                self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                self.assertTrue(compiled["prism_source"])
                self.assertTrue(compiled["runtime_source"])
                self.assertEqual(set(compiled["bindings"]), set(doc["operations"]))
                return compiled, assets

            compiled, assets = compile(document)
            broken = deepcopy(document)
            broken["operations"]["run_action"]["execution"]["binding"][
                "target"
            ] = "missing_reasoning_tool"
            rejected = compile_workflow(
                "mcp:reasoning-route",
                workflow_documents([DESCRIPTOR], snapshot(broken))[0],
                tools,
            )
            self.assertFalse(rejected["runnable"])
            self.assertTrue(rejected["diagnostics"])

            async def authorize():
                pass

            async def run(inputs, changed=None):
                workflow, received = compile(changed) if changed else (compiled, assets)
                return await execute(workflow, received, inputs, remote, authorize)

            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                base = {
                    "match": MATCH,
                    "registry": REGISTRY,
                    "repository_root": str(root),
                    "context": vars(hub.RunContext(dry_run=True)),
                }
                for available in [(), ACTIONS[:1], ACTIONS]:
                    populate(root, available)
                    # Live execution is allowed only for preflight failure on
                    # the empty mount; actual production scripts never launch.
                    for dry in ([False, True] if not available else [True]):
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
                            self.assertEqual(result["status"], "accepted", result)
                            self.assertEqual(result["outputs"], {"result": expected})
                            count = len(expected["children"])
                            operations = (
                                ["initialize"]
                                + ["select_action", "run_action", "advance"] * count
                                + ["finish"]
                            )
                            self.assertEqual(
                                [c["operation"] for c in result["calls"]], operations
                            )
                            self.assertEqual(
                                [c["tool"] for c in result["calls"]],
                                [
                                    "mathformer_reasoning_route_" + op
                                    for op in operations
                                ],
                            )
                            self.assertEqual(count, 2 if available or keep else 1)
                            self.assertEqual(expected["ok"], available == ACTIONS)
                            self.assertTrue(result["runtime"]["effect_records"])
                            self.assertTrue(result["runtime"]["provenance"])
                            self.assertTrue(result["replay_artifacts"])
                            self.assertFalse((root / "artifacts").exists())
                success = await run(base)
                self.assertEqual(len(success["calls"]), 8)
                self.assertEqual(
                    success["outputs"]["result"]["route"]["score"], MATCH["score"]
                )
                self.assertEqual(
                    success["outputs"]["result"]["route"]["matched_terms"],
                    MATCH["matched_terms"],
                )
                self.assertEqual(
                    [
                        c["action"]["id"]
                        for c in success["outputs"]["result"]["children"]
                    ],
                    list(ACTIONS),
                )
                self.assertTrue(success["outputs"]["result"]["ok"])

                # A later successful dry-run cannot erase an earlier preflight
                # failure: remove a path only required by the first action.
                missing = root / "skills/OUTPUT_TYPES.yaml"
                missing.unlink()
                for keep in [False, True]:
                    inputs = deepcopy(base)
                    inputs["context"]["keep_going"] = keep
                    result = await run(inputs)
                    expected = hub.run_intent_match(
                        selected_match(MATCH),
                        checked_registry(REGISTRY),
                        hub.RunContext(**inputs["context"]),
                        repository_root=root,
                    )
                    self.assertEqual(result["outputs"], {"result": expected})
                    self.assertFalse(expected["ok"])
                    self.assertEqual(len(expected["children"]), 2 if keep else 1)
                    self.assertEqual(
                        expected["children"][0]["preflight_errors"],
                        ["missing required path: skills/OUTPUT_TYPES.yaml"],
                    )
                    if keep:
                        self.assertTrue(expected["children"][1]["ok"])
                populate(root)

                # Failure data reaches native finish, whose missing metadata
                # KeyError propagates as a runtime failure without retry.
                for removed in ACTIONS:
                    for keep in [False, True]:
                        inputs = deepcopy(base)
                        inputs["registry"].pop(removed)
                        inputs["context"]["keep_going"] = keep
                        with self.assertRaises(KeyError):
                            hub.run_intent_match(
                                selected_match(MATCH),
                                checked_registry(inputs["registry"]),
                                hub.RunContext(**inputs["context"]),
                                repository_root=root,
                            )
                        result = await run(inputs)
                        self.assertEqual(result["status"], "failed", result)
                        self.assertIsNone(result["outputs"])
                        self.assertEqual(result["calls"][-1]["operation"], "finish")
                        self.assertEqual(
                            len(result["calls"]),
                            5 if removed == ACTIONS[0] and not keep else 8,
                        )
                for forged in ["registry", "match", "cursor"]:
                    inputs = deepcopy(base)
                    changed = None
                    if forged == "registry":
                        inputs["registry"][ACTIONS[0]]["command"] = [
                            "arbitrary-command"
                        ]
                    elif forged == "match":
                        inputs["match"]["route"]["title"] = "forged route title"
                    else:
                        changed = deepcopy(document)
                        changed["flow"]["steps"][1]["body"]["steps"][0]["arguments"][
                            "state"
                        ] = {
                            "literal": {
                                "ok": True,
                                "children": [{"ok": True}, {"ok": True}],
                            }
                        }
                    result = await run(inputs, changed)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]],
                        (
                            ["initialize", "select_action", "run_action"]
                            if forged == "registry"
                            else ["initialize", "select_action"]
                        ),
                    )
                for budget in [1, 4, 7]:
                    changed = deepcopy(document)
                    changed["policy"]["limits"]["max_operation_calls"] = budget
                    result = await run(base, changed)
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
                changed["flow"]["steps"][1]["max_iterations"] = 1
                result = await run(base, changed)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(
                    [c["operation"] for c in result["calls"]],
                    ["initialize", "select_action", "run_action", "advance"],
                )
                timed = deepcopy(document)
                timed["policy"]["limits"]["wall_time_seconds"] = 1
                workflow, received = compile(timed)

                async def waiting_authority():
                    await asyncio.Event().wait()

                with self.assertRaises(TimeoutError):
                    await execute(workflow, received, base, remote, waiting_authority)
                inputs = deepcopy(base)
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
        self.assertFalse(manager.active)


if __name__ == "__main__":
    program = unittest.main(verbosity=2, exit=False)
    result = program.result
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
