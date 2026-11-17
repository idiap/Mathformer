#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native controller equivalence and real MCP/PRISM compile-and-execute tests.

Only a deterministic external compiler fixture is launched. The production
readiness commands are exercised in dry-run mode, never launched. There are no
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

ACTION = "control:reasoning-log-consumer-readiness"
DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_control_reasoning_log_consumer_readiness_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/readiness-interface.schema.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
COMPILER = ROOT / "tests/mcp/fixtures/adoption_compiler.py"


def original():
    scope = dict(vars(hub))
    exec((ROOT / "tests/mcp/fixtures/readiness_original.py.txt").read_text(), scope)
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


class ReadinessTests(unittest.TestCase):
    def test_original_equivalence_and_native_guards(self):
        self.assert_state_transition()
        registry = hub.build_registry()
        oracle = original()
        deps = registry[ACTION].depends_on
        self.assertEqual(len(deps), 6)
        for keep in [False, True]:
            context = hub.RunContext(dry_run=True, keep_going=keep)
            for seen in [[], [ACTION], *([dep] for dep in deps), ["unrelated"]]:
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
        for index, ok in enumerate([False] + [True] * 5):
            before = deepcopy(state)
            child = {"ok": ok, "status": str(index)}
            state, done = hub.advance_dependencies(item, state, child, context)
            self.assertEqual(state["index"], index + 1)
            self.assertFalse(state["dependencies_ok"])
            self.assertEqual(state["children"], before["children"] + [child])
            self.assertEqual(state["ancestry"], initial["ancestry"])
            self.assertEqual(done, index == 5)
        self.assertEqual(
            initial,
            {
                "index": 0,
                "children": [],
                "dependencies_ok": True,
                "ancestry": sorted([ACTION, "caller"]),
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
        self.assertTrue(
            any(
                row["path"] == "scripts/mathformer.py"
                and row.get("selector") == "run_action"
                for row in document["provenance"]["sources"]
            )
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        self.assertEqual(
            document["id"], "hub_control_reasoning_log_consumer_readiness_workflow"
        )
        self.assertEqual(document["policy"]["limits"]["max_operation_calls"], 16)
        assets = snapshot(document)
        manager = SessionManager()
        # Import the actual production MCP registration without main/config.
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        async with manager.open(
            "readiness",
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
                    "mcp:readiness", workflow_documents([DESCRIPTOR], assets)[0], tools
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
                        "mcp:readiness",
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
                        *(([dep], []) for dep in deps),
                        (["unrelated"], []),
                    ]:
                        context = vars(hub.RunContext(dry_run=True, keep_going=keep))
                        inputs = {
                            "context": context,
                            "request": {
                                "action_id": ACTION,
                                "extra_args": args,
                                "seen": seen,
                            },
                        }
                        result = await run(inputs)
                        self.assertEqual(
                            result["status"],
                            "accepted",
                            {"calls": result["calls"], "mode": locals().get("mode")},
                        )
                        expected = original()(
                            ACTION,
                            hub.build_registry(),
                            hub.RunContext(**context),
                            extra_args=args,
                            seen=set(seen),
                        )
                        self.assertEqual(result["outputs"], {"result": expected})
                        count = (
                            4
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
                                + ["visit", "advance"] * len(expected["children"])
                                + ["finish"],
                            )
                        else:
                            self.assertEqual(
                                names, ["admit", "reject", "carry", "carry"]
                            )
                context = vars(hub.RunContext(dry_run=True))
                inputs = {
                    "context": context,
                    "request": {"action_id": ACTION, "extra_args": [], "seen": []},
                }
                # The native fixed bound completes after six visits, without
                # a seventh attempt or retry. Budget exhaustion remains a failure.
                for budget in [12, 14]:
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
                            c["operation"] == "visit"
                            and bool(c.get("transport_call_performed"))
                            for c in result["calls"]
                        ),
                        5 if budget == 12 else 6,
                    )
                # A genuine MCP operation error propagates through PRISM;
                # dependent operations and finalization must never execute.
                broken = deepcopy(document)
                first = broken["flow"]["steps"][2]["body"]["cases"][0]["body"]["steps"][
                    0
                ]
                first["arguments"]["state"] = {
                    "literal": {
                        "index": 6,
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
                    ["admit", "initialize", "visit"],
                )
                self.assertEqual(result["calls"][-1]["status"], "rejected")
                # Validate leaf interface independently, including actual context.
                admission = await remote.call(
                    "mathformer_readiness_admit",
                    {"request": {"action_id": ACTION, "extra_args": [], "seen": []}},
                )
                state = (
                    await remote.call("mathformer_readiness_initialize", admission)
                )["state"]
                child = (
                    await remote.call(
                        "mathformer_readiness_visit",
                        {"state": state, "context": context},
                    )
                )["child"]
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
                    "mcp:readiness",
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

    def test_external_boundary_through_registered_tools_and_prism(self):
        asyncio.run(self.external_scenario())

    async def external_scenario(self):
        document = yaml.safe_load(CONTRACT.read_text())
        manager = SessionManager()
        for mode in ["success", "fail", "write", "timeout"]:
            with tempfile.TemporaryDirectory() as directory:
                async with manager.open(
                    "control-fixture",
                    StdioConfig(
                        command=sys.executable,
                        args=[
                            str(
                                ROOT / "tests/mcp/fixtures/readiness_boundary_server.py"
                            ),
                            mode,
                            directory,
                        ],
                        cwd=str(ROOT),
                    ),
                    {},
                ) as remote:
                    try:
                        tools = [
                            tool.model_dump(by_alias=True, exclude_none=True)
                            for tool in await remote.tools()
                        ]
                        assets = snapshot(document)
                        workflow = compile_workflow(
                            "mcp:control-fixture",
                            workflow_documents([DESCRIPTOR], assets)[0],
                            tools,
                        )
                        self.assertTrue(workflow["runnable"], workflow["diagnostics"])

                        async def authorize():
                            pass

                        for keep in [False, True]:
                            context = vars(hub.RunContext(keep_going=keep))
                            inputs = {
                                "context": context,
                                "request": {
                                    "action_id": ACTION,
                                    "extra_args": [],
                                    "seen": [],
                                },
                            }
                            result = await execute(
                                workflow, assets, inputs, remote, authorize
                            )
                            self.assertEqual(
                                result["status"],
                                "accepted",
                                {
                                    "calls": result["calls"],
                                    "mode": locals().get("mode"),
                                },
                            )
                            expected = await remote.call("fixture_original", inputs)
                            self.assertEqual(result["outputs"], expected)
                            native = expected["result"]
                            count = 6 if mode == "success" or keep else 3
                            self.assertEqual(len(native["children"]), count)
                            self.assertEqual(native["ok"], mode == "success")
                            self.assertEqual(len(result["calls"]), 3 + 2 * count)
                            self.assertTrue(result["runtime"]["provenance"])
                            self.assertTrue(result["runtime"]["effect_records"])
                            if mode == "fail":
                                self.assertEqual(native["children"][2]["returncode"], 7)
                                self.assertEqual(
                                    native["children"][2]["stderr"],
                                    "deterministic compiler diagnostic",
                                )
                            if mode == "timeout":
                                self.assertEqual(
                                    native["children"][2]["status"], "timeout"
                                )
                                self.assertEqual(
                                    native["children"][2]["stdout"], "partial"
                                )
                                self.assertEqual(
                                    native["children"][2]["stderr"], "compiler timeout"
                                )
                            if mode == "write":
                                self.assertEqual(
                                    native["children"][2]["status"], "undeclared_writes"
                                )
                                self.assertEqual(
                                    native["children"][2]["write_audit"][
                                        "unexpected_paths"
                                    ],
                                    ["undeclared.txt"],
                                )
                        # A deliberately smaller graph bound must fail, with no
                        # finalization or fabricated success at exhaustion.
                        short = deepcopy(document)
                        short["flow"]["steps"][2]["max_iterations"] = 2
                        short_assets = snapshot(short)
                        compiled = compile_workflow(
                            "mcp:control-fixture",
                            workflow_documents([DESCRIPTOR], short_assets)[0],
                            tools,
                        )
                        self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                        exhausted = await execute(
                            compiled,
                            short_assets,
                            {
                                "context": vars(hub.RunContext(dry_run=True)),
                                "request": {
                                    "action_id": ACTION,
                                    "extra_args": [],
                                    "seen": [],
                                },
                            },
                            remote,
                            authorize,
                        )
                        self.assertEqual(exhausted["status"], "failed", exhausted)
                        self.assertIsNone(exhausted["outputs"])
                        self.assertEqual(
                            [c["operation"] for c in exhausted["calls"]],
                            [
                                "admit",
                                "initialize",
                                "visit",
                                "advance",
                                "visit",
                                "advance",
                            ],
                        )
                        self.assertEqual(exhausted["failure_disposition"], "fail")
                    except Exception:
                        import traceback

                        traceback.print_exc()
                        raise
        self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
