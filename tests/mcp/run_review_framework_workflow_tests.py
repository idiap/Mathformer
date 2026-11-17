#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Real MCP bindings, PRISM parser/checker/compiler/runtime and native equivalence.

Canonical actions run only as dry runs or reject at real preflight. A test-only
compiler boundary supplies deterministic subprocess outcomes to native leaves;
no production command, provider, credential or theorem prover is invoked.
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

sys.path.extend(str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages"))

import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib.util
import json
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import yaml

import mathformer as hub
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

ACTION = "review:autoformalization-framework"
DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_review_autoformalization_framework_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])


def original():
    scope = dict(vars(hub))
    exec(
        (ROOT / "tests/mcp/fixtures/review_framework_original.py.txt").read_text(),
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


class CompilerFixture:
    """Substitute only the external compiler boundary of test registry leaves."""

    def __init__(self, root, mode):
        self.root, self.mode, self.calls = root, mode, []

    def __call__(self, argv, **kwargs):
        self.calls.append((list(argv), dict(kwargs)))
        assert argv in [["fixture-compiler", "first"], ["fixture-compiler", "second"]]
        assert kwargs == dict(
            cwd=self.root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
        )
        if argv[-1] == "first":
            if self.mode == "launch":
                raise OSError("deterministic compiler launch failure")
            if self.mode == "timeout":
                raise subprocess.TimeoutExpired(
                    argv, 120, output="partial", stderr="timeout diagnostic"
                )
            if self.mode == "write":
                (self.root / "undeclared.txt").write_text("compiler output")
            if self.mode == "fail":
                return subprocess.CompletedProcess(
                    argv, 7, "partial", "compiler diagnostic"
                )
        return subprocess.CompletedProcess(
            argv, 0, json.dumps({"compiled": argv[-1]}), ""
        )


class ReviewFrameworkTests(unittest.TestCase):
    def test_authored_generator_preserves_contract(self):
        document = yaml.safe_load(CONTRACT.read_text())
        authored = (
            ROOT
            / "skills/control/workflow-contract-validator/references/review-framework.workflow.json"
        )
        self.assertEqual(json.loads(authored.read_text()), document)
        path = (
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py"
        )
        spec = importlib.util.spec_from_file_location("review_generator", path)
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)
        generated = next(d for d in generator.inventory() if d["id"] == document["id"])
        self.assertEqual(generated, document)
        self.assertEqual(document["aliases"], [ACTION])
        self.assertEqual(
            document["extensions"]["mathformer.composition"]["ordered_dependencies"],
            ["control:all", "test:docs", "mathformerphysicslib:release-gate"],
        )

    def test_native_controller_compiler_boundary(self):
        registry = hub.build_registry()
        self.assertEqual(
            registry[ACTION].depends_on,
            ("control:all", "test:docs", "mathformerphysicslib:release-gate"),
        )
        self.assertFalse(registry[ACTION].command)
        self.assertIsNone(registry[ACTION].timeout_seconds)
        self.assertEqual(
            registry["mathformerphysicslib:release-gate"].timeout_seconds, 1200
        )
        oracle = original()
        for keep in [False, True]:
            context = hub.RunContext(dry_run=True, keep_going=keep)
            for seen in [[], [ACTION], ["control:all"], ["test:quick"], ["caller"]]:
                for args in [[], ["--invalid"]]:
                    self.assertEqual(
                        hub.run_action(
                            ACTION, registry, context, seen=set(seen), extra_args=args
                        ),
                        oracle(
                            ACTION, registry, context, seen=set(seen), extra_args=args
                        ),
                    )
        self.assertEqual(
            hub.run_action("missing", registry, hub.RunContext()),
            {"ok": False, "status": "unknown_action", "action_id": "missing"},
        )
        # Native controller, leaf preflight, captured output, timeout, write audit
        # and unexpected exception propagation all execute unmodified.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            leaves = [
                hub.WorkflowAction(
                    "fixture:" + name,
                    "compiler fixture",
                    "quality",
                    "validation",
                    "read_only",
                    command=("fixture-compiler", name),
                    timeout_seconds=120,
                )
                for name in ["first", "second"]
            ]
            test_registry = {
                ACTION: replace(
                    registry[ACTION], depends_on=tuple(x.action_id for x in leaves)
                ),
                **{x.action_id: x for x in leaves},
            }
            for mode in ["success", "fail", "timeout", "write", "launch"]:
                for keep in [False, True]:
                    results, traces = [], []
                    for runner in [oracle, hub.run_action]:
                        (root / "undeclared.txt").unlink(missing_ok=True)
                        boundary = CompilerFixture(root, mode)
                        with patch.object(hub.subprocess, "run", boundary):
                            if mode == "launch":
                                with self.assertRaisesRegex(
                                    OSError, "compiler launch failure"
                                ):
                                    runner(
                                        ACTION,
                                        test_registry,
                                        hub.RunContext(keep_going=keep),
                                        repository_root=root,
                                    )
                            else:
                                results.append(
                                    runner(
                                        ACTION,
                                        test_registry,
                                        hub.RunContext(keep_going=keep),
                                        repository_root=root,
                                    )
                                )
                        traces.append(boundary.calls)
                    self.assertEqual(*traces)
                    if mode == "launch":
                        self.assertEqual(len(traces[0]), 1)
                        continue
                    self.assertEqual(*results)
                    result = results[0]
                    self.assertEqual(result["ok"], mode == "success")
                    self.assertEqual(
                        len(result["children"]), 2 if keep or mode == "success" else 1
                    )
                    self.assertEqual(len(traces[0]), len(result["children"]))
                    if keep and mode != "success":
                        self.assertTrue(result["children"][1]["ok"])
                        self.assertEqual(result["status"], "sequence_failed")
                    child = result["children"][0]
                    if mode == "fail":
                        self.assertEqual(
                            (child["returncode"], child["stdout"], child["stderr"]),
                            (7, "partial", "compiler diagnostic"),
                        )
                    if mode == "timeout":
                        self.assertEqual(
                            (
                                child["status"],
                                child["timeout_seconds"],
                                child["stdout"],
                            ),
                            ("timeout", 120, "partial"),
                        )
                    if mode == "write":
                        self.assertEqual(child["status"], "undeclared_writes")
                        self.assertEqual(
                            child["write_audit"]["unexpected_paths"], ["undeclared.txt"]
                        )
                    if mode == "success":
                        self.assertTrue(child["write_audit"]["ok"])
                        self.assertEqual(
                            json.loads(child["stdout"]), {"compiled": "first"}
                        )

    def test_service_guard(self):
        import mcp_server as server

        registry = hub.build_registry()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(server, "_READONLY", True):
                with self.assertRaisesRegex(ValueError, "read-only"):
                    server._review_framework_guard(
                        vars(hub.RunContext()), root, registry
                    )
                server._review_framework_guard(
                    vars(hub.RunContext(dry_run=True)), root, registry
                )
            with (
                patch.object(server, "_READONLY", False),
                patch.object(server, "_ALLOWED_WRITE_ROOTS", [root / "restricted"]),
            ):
                with self.assertRaisesRegex(
                    PermissionError, "outside configured service roots"
                ):
                    server._review_framework_guard(
                        vars(hub.RunContext()), root, registry
                    )

    def test_canonical_registry_external_compiler_through_mcp(self):
        asyncio.run(self.compiler_scenario())

    async def compiler_scenario(self):
        document = yaml.safe_load(CONTRACT.read_text())

        async def authorize():
            pass

        for mode in ["success", "fail", "timeout", "write", "exception"]:
            with tempfile.TemporaryDirectory() as directory:
                Path(directory)
                manager = SessionManager()
                config = StdioConfig(
                    command=sys.executable,
                    args=[
                        str(
                            ROOT
                            / "tests/mcp/fixtures/review_framework_boundary_server.py"
                        ),
                        mode,
                        directory,
                    ],
                    cwd=str(ROOT),
                )
                async with manager.open("review-compiler", config, {}) as remote:
                    tools = [
                        t.model_dump(by_alias=True, exclude_none=True)
                        for t in await remote.tools()
                    ]
                    assets = snapshot(document)
                    selected = workflow_documents([DESCRIPTOR], assets)[0]
                    compiled = compile_workflow("mcp:review-compiler", selected, tools)
                    self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                    for keep in [False, True]:
                        await remote.call("fixture_reset", {})
                        context = vars(hub.RunContext(keep_going=keep))
                        result = await execute(
                            compiled,
                            assets,
                            {
                                "context": context,
                                "extra_args": [],
                                "seen": [],
                                "repository_root": directory,
                            },
                            remote,
                            authorize,
                        )
                        calls = (await remote.call("fixture_ledger", {}))["calls"]
                        if mode == "exception":
                            self.assertEqual(result["status"], "failed", result)
                            self.assertIsNone(result["outputs"])
                            self.assertEqual(result["calls"][-1]["operation"], "visit")
                            self.assertEqual(calls[-1]["action"], "test:docs")
                            continue
                        self.assertEqual(result["status"], "accepted", result)
                        expected = await remote.call(
                            "fixture_original", {"context": context}
                        )
                        self.assertEqual(result["outputs"], expected)
                        self.assertEqual(
                            calls, (await remote.call("fixture_ledger", {}))["calls"]
                        )
                        output = result["outputs"]["result"]
                        self.assertEqual(output["ok"], mode == "success")
                        self.assertEqual(
                            len(output["children"]),
                            2 if mode == "fail" and not keep else 3,
                        )
                        self.assertEqual(
                            [r["action"] for r in calls][-1],
                            (
                                "test:docs"
                                if mode == "fail" and not keep
                                else "mathformerphysicslib:release-gate"
                            ),
                        )
                        self.assertEqual(
                            len(result["calls"]),
                            7 if mode == "fail" and not keep else 9,
                        )
                        if mode == "fail":
                            child = output["children"][1]
                            self.assertEqual(
                                (child["returncode"], child["stdout"], child["stderr"]),
                                (7, "partial", "documentation diagnostic"),
                            )
                            if keep:
                                self.assertTrue(output["children"][2]["ok"])
                        if mode == "timeout":
                            child = output["children"][2]
                            self.assertEqual(
                                (
                                    child["status"],
                                    child["timeout_seconds"],
                                    child["stdout"],
                                ),
                                ("timeout", 1200, "partial build"),
                            )
                        if mode == "write":
                            child = output["children"][2]
                            self.assertEqual(child["status"], "undeclared_writes")
                            self.assertEqual(
                                child["write_audit"]["unexpected_paths"],
                                ["undeclared.txt"],
                            )
                        if mode == "success":
                            self.assertTrue(
                                all(
                                    c["write_audit"]["ok"]
                                    for c in output["children"][1:]
                                )
                            )
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["replay_artifacts"])
                self.assertFalse(manager.active)

    def test_registered_mcp_and_real_lunar(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(
            document["id"], "hub_review_autoformalization_framework_workflow"
        )
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 9},
        )
        self.assertTrue(
            any(
                row["path"] == "scripts/mathformer.py"
                for row in document["provenance"]["sources"]
            )
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        assets = snapshot(document)
        manager = SessionManager()
        server = (
            "import sys;sys.path.extend("
            + repr([str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")])
            + ');sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        )
        async with manager.open(
            "review-framework",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {},
        ) as remote:
            failure = None
            try:
                tools = [
                    tool.model_dump(by_alias=True, exclude_none=True)
                    for tool in await remote.tools()
                ]

                def compile_document(changed):
                    received = snapshot(changed)
                    compiled = compile_workflow(
                        "mcp:review-framework",
                        workflow_documents([DESCRIPTOR], received)[0],
                        tools,
                    )
                    self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                    self.assertTrue(compiled["runtime_source"])
                    self.assertEqual(
                        set(compiled["bindings"]), set(document["operations"])
                    )
                    return compiled, received

                workflow, assets = compile_document(document)

                async def authorize():
                    pass

                async def run(inputs, changed=None):
                    compiled, received = (
                        (workflow, assets)
                        if changed is None
                        else compile_document(changed)
                    )
                    return await execute(compiled, received, inputs, remote, authorize)

                def inputs(seen=(), args=(), keep=False, root=ROOT, dry=True):
                    return {
                        "context": vars(hub.RunContext(dry_run=dry, keep_going=keep)),
                        "extra_args": list(args),
                        "seen": list(seen),
                        "repository_root": str(root),
                    }

                # Full bound, both rejection guards, each child cycle, early stop and
                # sticky failure followed by later successes; all real tools.
                for keep in [False, True]:
                    for seen, args in [
                        ([], []),
                        ([ACTION], []),
                        ([], ["--invalid"]),
                        ([ACTION], ["--invalid"]),
                        (["control:all"], []),
                        (["test:docs"], []),
                        (["mathformerphysicslib:release-gate"], []),
                        (["caller"], []),
                    ]:
                        request = inputs(seen, args, keep)
                        result = await run(request)
                        expected = original()(
                            ACTION,
                            hub.build_registry(),
                            hub.RunContext(**request["context"]),
                            extra_args=args,
                            seen=set(seen),
                            repository_root=ROOT,
                        )
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertEqual(result["outputs"], {"result": expected})
                        names = [c["operation"] for c in result["calls"]]
                        if "children" in expected:
                            self.assertEqual(
                                names,
                                ["admit", "initialize"]
                                + ["visit", "advance"] * len(expected["children"])
                                + ["finish"],
                            )
                            self.assertLessEqual(len(expected["children"]), 3)
                            if keep:
                                self.assertEqual(len(expected["children"]), 3)
                                self.assertEqual(len(result["calls"]), 9)
                        else:
                            self.assertEqual(
                                names, ["admit", "reject", "carry", "carry"]
                            )
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["replay_artifacts"])
                request = inputs(keep=True)
                request.pop("extra_args")
                request.pop("seen")
                request["repository_root"] = None
                result = await run(request)
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(
                    result["outputs"]["result"],
                    hub.run_action(
                        ACTION,
                        hub.build_registry(),
                        hub.RunContext(**request["context"]),
                    ),
                )
                # Explicit mount is used for actual preflight too; both recursive
                # control and the test leaves fail before any subprocess can launch.
                with tempfile.TemporaryDirectory() as directory:
                    for keep in [False, True]:
                        request = inputs(
                            seen=["control:all"],
                            keep=keep,
                            root=Path(directory),
                            dry=False,
                        )
                        expected = hub.run_action(
                            ACTION,
                            hub.build_registry(),
                            hub.RunContext(**request["context"]),
                            repository_root=Path(directory).resolve(),
                            seen={"control:all"},
                        )
                        result = await run(request)
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertEqual(result["outputs"], {"result": expected})
                        self.assertFalse(expected["ok"])
                        self.assertEqual(len(expected["children"]), 3 if keep else 1)
                        self.assertEqual(
                            expected["children"][0]["status"], "dependency_cycle"
                        )
                        if keep:
                            self.assertTrue(expected["children"][1]["preflight_errors"])
                request = inputs()
                for budget in [7, 8]:
                    smaller = deepcopy(document)
                    smaller["policy"]["limits"]["max_operation_calls"] = budget
                    result = await run(request, smaller)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(
                        sum(
                            bool(c.get("transport_call_performed"))
                            for c in result["calls"]
                        ),
                        budget,
                    )
                short = deepcopy(document)
                short["flow"]["steps"][2]["max_iterations"] = 1
                result = await run(request, short)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(
                    [c["operation"] for c in result["calls"]],
                    ["admit", "initialize", "visit", "advance"],
                )
                self.assertEqual(result["failure_disposition"], "fail")
                # Index 3 is a valid terminal state but cannot be visited again.
                broken = deepcopy(document)
                visit = broken["flow"]["steps"][2]["body"]["cases"][0]["body"]["steps"][
                    0
                ]
                visit["arguments"]["state"] = {
                    "literal": {
                        "index": 3,
                        "children": [],
                        "dependencies_ok": True,
                        "ancestry": [ACTION],
                    }
                }
                result = await run(request, broken)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(
                    [c["operation"] for c in result["calls"]],
                    ["admit", "initialize", "visit"],
                )
                self.assertEqual(result["calls"][-1]["status"], "rejected")
                # Observe the real loop-carried data across registered MCP ports.
                admission = await remote.call(
                    "mathformer_review_framework_admit",
                    {"extra_args": [], "seen": ["caller"]},
                )
                state = (
                    await remote.call(
                        "mathformer_review_framework_initialize", admission
                    )
                )["state"]
                initial = deepcopy(state)
                context = vars(hub.RunContext(dry_run=True, keep_going=True))
                for i, ok in enumerate([False, True, True]):
                    advanced = await remote.call(
                        "mathformer_review_framework_advance",
                        {"state": state, "child": {"ok": ok}, "context": context},
                    )
                    state = advanced["state"]
                    self.assertEqual(state["index"], i + 1)
                    self.assertEqual(
                        state["children"], [{"ok": False}, *([{"ok": True}] * i)]
                    )
                    self.assertFalse(state["dependencies_ok"])
                    self.assertEqual(state["ancestry"], initial["ancestry"])
                    self.assertEqual(advanced["done"], i == 2)
                finished = await remote.call(
                    "mathformer_review_framework_finish", {"state": state}
                )
                self.assertEqual(finished["result"]["status"], "sequence_failed")
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure is not None:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
