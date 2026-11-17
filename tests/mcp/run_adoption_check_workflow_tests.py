#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native controller equivalence and real MCP/PRISM compile-and-execute tests.

Only a deterministic external compiler fixture is launched. The production
adoption commands are exercised in dry-run mode, never launched. There are no
provider calls, credentials, service configuration, or production mock switches.
"""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.path[:0] = [str(LUNAR / "app/backend"), str(ROOT / "scripts"), str(ROOT)]

import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import tempfile
import unittest
import yaml

import mathformer as hub
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

ACTION = "adoption:check"
DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_adoption_check_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
COMPILER = ROOT / "tests/mcp/fixtures/adoption_compiler.py"


def original():
    scope = dict(vars(hub))
    exec(
        (ROOT / "tests/mcp/fixtures/adoption_run_action_original.py.txt").read_text(),
        scope,
    )
    return scope["run_action"]


def asset(path, text):
    return {
        "path": path,
        "content": text,
        "encoding": "text",
        "sha256": hashlib.sha256(text.encode()).hexdigest(),
    }


def snapshot(document):
    paths = {row["path"] for row in document["provenance"]["sources"]} | {SCHEMA}
    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(path, (ROOT / path).read_text()) for path in sorted(paths)
    ]


class AdoptionTests(unittest.TestCase):
    def test_original_equivalence_and_native_guards(self):
        self.assert_state_transition()
        registry = hub.build_registry()
        oracle = original()
        deps = registry[ACTION].depends_on
        self.assertEqual(len(deps), 4)
        for keep in [False, True]:
            context = hub.RunContext(dry_run=True, keep_going=keep)
            for seen in [
                [],
                [ACTION],
                [deps[0]],
                [deps[1]],
                [deps[2]],
                [deps[3]],
                ["unrelated"],
            ]:
                for args in [[], ["--invalid"]]:
                    before = list(seen)
                    result = hub.run_action(
                        ACTION, registry, context, seen=set(seen), extra_args=args
                    )
                    self.assertEqual(
                        result,
                        oracle(
                            ACTION, registry, context, seen=set(seen), extra_args=args
                        ),
                    )
                    self.assertEqual(seen, before)
            self.assertEqual(
                hub.run_action("missing", registry, context),
                oracle("missing", registry, context),
            )
        # Ancestry is copied per recursive call, rather than a completion cache.
        duplicate = dict(registry)
        duplicate[ACTION] = replace(registry[ACTION], depends_on=(deps[0], deps[0]))
        result = hub.run_action(ACTION, duplicate, hub.RunContext(dry_run=True))
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["children"]), 2)
        self.assertEqual(
            result, oracle(ACTION, duplicate, hub.RunContext(dry_run=True))
        )

    def assert_state_transition(self):
        item = hub.build_registry()[ACTION]
        admission = hub.admit_action(ACTION, hub.build_registry(), seen=["caller"])
        state = hub.initialize_dependencies(admission)
        initial = deepcopy(state)
        context = hub.RunContext(keep_going=True)
        for index, ok in enumerate([False, True, True, True]):
            before = deepcopy(state)
            child = {"ok": ok, "status": str(index)}
            state, done = hub.advance_dependencies(item, state, child, context)
            self.assertEqual(state["index"], index + 1)
            self.assertFalse(state["dependencies_ok"])
            self.assertEqual(state["children"], before["children"] + [child])
            self.assertEqual(state["ancestry"], initial["ancestry"])
            self.assertEqual(done, index == 3)
        self.assertEqual(
            initial,
            {
                "index": 0,
                "children": [],
                "dependencies_ok": True,
                "ancestry": [ACTION, "caller"],
            },
        )
        self.assertEqual(
            hub.finish_dependencies(item, state)["status"], "sequence_failed"
        )

    def test_native_leaf_compiler_failures_and_parent_command(self):
        # Registry and repository root are explicit native inputs. Isolate writes
        # while exercising the unmodified subprocess, preflight and audit helpers.
        saved = hub.REPO_ROOT
        try:
            with tempfile.TemporaryDirectory() as directory:
                hub.REPO_ROOT = Path(directory)
                oracle = original()
                base = hub.build_registry()[ACTION]
                for mode, expected in [
                    ("success", "completed"),
                    ("fail", "completed"),
                    ("timeout", "timeout"),
                    ("write", "undeclared_writes"),
                    ("preflight", None),
                ]:
                    leaf = hub.WorkflowAction(
                        "fixture:compiler",
                        "deterministic compiler",
                        "control",
                        "validation",
                        "read_only",
                        command=(hub.PYTHON_TOKEN, str(COMPILER), mode),
                        required_paths=("missing",) if mode == "preflight" else (),
                        timeout_seconds=0.05 if mode == "timeout" else None,
                    )
                    registry = {
                        ACTION: replace(
                            base, depends_on=(leaf.action_id, leaf.action_id)
                        ),
                        leaf.action_id: leaf,
                    }
                    for keep in [False, True]:
                        context = hub.RunContext(keep_going=keep)
                        results = []
                        for runner in [oracle, hub.run_action]:
                            (hub.REPO_ROOT / "undeclared.txt").unlink(missing_ok=True)
                            results.append(runner(ACTION, registry, context))
                        self.assertEqual(*results)
                        result = results[1]
                        success = mode == "success"
                        self.assertEqual(result["ok"], success)
                        self.assertEqual(
                            len(result["children"]), 2 if keep or success else 1
                        )
                        child = result["children"][0]
                        self.assertEqual(child.get("status"), expected)
                        if mode == "fail":
                            self.assertEqual(child["returncode"], 7)
                            self.assertIn("compiler diagnostic: fail", child["stderr"])
                        if mode == "success":
                            self.assertEqual(
                                json.loads(child["stdout"]),
                                {"compiled": True, "mode": mode},
                            )
                            self.assertTrue(child["write_audit"]["ok"])
                        if mode == "write":
                            self.assertEqual(
                                child["write_audit"]["unexpected_paths"],
                                ["undeclared.txt"],
                            )
                        if mode == "preflight":
                            self.assertEqual(
                                child["preflight_errors"],
                                ["missing required path: missing"],
                            )
                            self.assertNotIn("returncode", child)
                    # Shared extraction must retain generic parent-command behavior.
                    registry[ACTION] = replace(
                        registry[ACTION],
                        command=(hub.PYTHON_TOKEN, str(COMPILER), "success"),
                    )
                    (hub.REPO_ROOT / "undeclared.txt").unlink(missing_ok=True)
                    a = oracle(
                        ACTION, registry, hub.RunContext(dry_run=True, keep_going=True)
                    )
                    b = hub.run_action(
                        ACTION, registry, hub.RunContext(dry_run=True, keep_going=True)
                    )
                    self.assertEqual(a, b)
                    self.assertIn("leaf", b)
        finally:
            hub.REPO_ROOT = saved

    def test_real_registered_tools_and_lunar_runtime(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(document["id"], "hub_adoption_check_workflow")
        self.assertEqual(document["policy"]["limits"]["max_operation_calls"], 11)
        assets = snapshot(document)
        manager = SessionManager()
        # Import the actual production MCP registration without main/config.
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        async with manager.open(
            "adoption",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {},
        ) as remote:
            failure = None
            try:
                tools = [
                    tool.model_dump(by_alias=True, exclude_none=True)
                    for tool in await remote.tools()
                ]
                workflow = compile_workflow(
                    "mcp:adoption", workflow_documents([DESCRIPTOR], assets)[0], tools
                )
                self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                self.assertTrue(workflow["runtime_source"])
                self.assertEqual(set(workflow["bindings"]), set(document["operations"]))

                async def authorize():
                    pass

                async def run(inputs, changed=None):
                    if changed is None:
                        return await execute(
                            workflow, assets, inputs, remote, authorize
                        )
                    changed_assets = snapshot(changed)
                    compiled = compile_workflow(
                        "mcp:adoption",
                        workflow_documents([DESCRIPTOR], changed_assets)[0],
                        tools,
                    )
                    self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                    return await execute(
                        compiled, changed_assets, inputs, remote, authorize
                    )

                deps = hub.build_registry()[ACTION].depends_on
                for keep in [False, True]:
                    for seen, args in [
                        ([], []),
                        ([ACTION], []),
                        ([], ["--invalid"]),
                        ([ACTION], ["--invalid"]),
                        ([deps[0]], []),
                        ([deps[1]], []),
                        ([deps[2]], []),
                        ([deps[3]], []),
                        (["unrelated"], []),
                    ]:
                        context = vars(hub.RunContext(dry_run=True, keep_going=keep))
                        inputs = {"context": context, "extra_args": args, "seen": seen}
                        result = await run(inputs)
                        self.assertEqual(result["status"], "accepted", result)
                        expected = original()(
                            ACTION,
                            hub.build_registry(),
                            hub.RunContext(**context),
                            extra_args=args,
                            seen=set(seen),
                        )
                        self.assertEqual(result["outputs"], {"result": expected})
                        count = (
                            2
                            if "children" not in expected
                            else 3 + 2 * len(expected["children"])
                        )
                        self.assertEqual(len(result["calls"]), count)
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["replay_artifacts"])
                        names = [c["operation"] for c in result["calls"]]
                        if "children" in expected:
                            self.assertEqual(
                                names,
                                ["admit", "initialize"]
                                + ["visit_child", "advance"] * len(expected["children"])
                                + ["finish"],
                            )
                        else:
                            self.assertEqual(names, ["admit", "reject"])
                context = vars(hub.RunContext(dry_run=True))
                inputs = {"context": context, "extra_args": [], "seen": []}
                # The native fixed bound completes after four visits, without
                # a fifth attempt or retry. Budget exhaustion remains a failure.
                for budget in [8, 10]:
                    exhausted = deepcopy(document)
                    exhausted["policy"]["limits"]["max_operation_calls"] = budget
                    result = await run(inputs, exhausted)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(
                        sum(
                            bool(c.get("transport_call_performed"))
                            for c in result["calls"]
                        ),
                        budget,
                    )
                    self.assertEqual(
                        sum(
                            c["operation"] == "visit_child"
                            and bool(c.get("transport_call_performed"))
                            for c in result["calls"]
                        ),
                        3 if budget == 8 else 4,
                    )
                # A genuine MCP operation error propagates through PRISM;
                # dependent operations and finalization must never execute.
                broken = deepcopy(document)
                first = broken["flow"]["steps"][1]["cases"][0]["body"]["steps"][1]
                first["arguments"]["state"] = {
                    "literal": {
                        "index": 4,
                        "children": [],
                        "dependencies_ok": True,
                        "ancestry": [ACTION],
                    }
                }
                result = await run(inputs, broken)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(
                    [c["operation"] for c in result["calls"]],
                    ["admit", "initialize", "visit_child"],
                )
                self.assertEqual(result["calls"][-1]["status"], "rejected")
                # Validate leaf interface independently, including actual context.
                admission = await remote.call(
                    "mathformer_adoption_admit", {"extra_args": [], "seen": []}
                )
                state = (
                    await remote.call("mathformer_adoption_initialize", admission)
                )["state"]
                child = (
                    await remote.call(
                        "mathformer_adoption_visit_child",
                        {"state": state, "context": context},
                    )
                )["result"]
                self.assertEqual(child["status"], "dry_run")
                self.assertEqual(
                    child["argv"],
                    hub.resolve_command(hub.build_registry()[deps[0]].command),
                )
                self.assertNotIn("write_audit", child)
                timed = deepcopy(document)
                timed["policy"]["limits"]["wall_time_seconds"] = 1
                timed_assets = snapshot(timed)
                timed_workflow = compile_workflow(
                    "mcp:adoption",
                    workflow_documents([DESCRIPTOR], timed_assets)[0],
                    tools,
                )
                self.assertTrue(
                    timed_workflow["runnable"], timed_workflow["diagnostics"]
                )

                async def wait_for_authority():
                    await asyncio.Event().wait()

                with self.assertRaises(TimeoutError):
                    await execute(
                        timed_workflow, timed_assets, inputs, remote, wait_for_authority
                    )
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure is not None:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
