#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Real native steps, registered MCP tools and Lunar/PRISM compile/execute.

The selected production gates are never launched: isolated mounts exercise
preflight failure and dry-run. Generic native controller process behavior is
tested only at a deterministic external compiler/provider boundary.
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
    str(Path(__file__).parent / "fixtures"),
]
sys.path.extend(str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages"))

import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib.util
import json
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
import yaml

import mathformer as hub
from control_audit_route_tools import (
    ACTION,
    DEPENDENCIES,
    selected_match,
    checked_registry,
)
from control_audit_compiler import install
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_control_audit_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
MATCH = {
    "route": {"route_id": "control.audit", "action_ids": [ACTION]},
    "score": 17,
    "matched_terms": ["workflow", "control", "audit"],
}
REGISTRY = {
    key: hub.action_to_dict(hub.build_registry()[key])
    for key in (ACTION, *DEPENDENCIES)
}


def original():
    scope = dict(vars(hub))
    exec(
        (ROOT / "tests/mcp/fixtures/control_audit_route_original.py.txt").read_text(),
        scope,
    )
    return SimpleNamespace(**scope), scope


def populate(root):
    """Preflight-only mount: empty inputs suffice because every call is dry."""
    for key in DEPENDENCIES:
        for relative in hub.build_registry()[key].required_paths:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch(exist_ok=True)


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


class ControlAuditRouteTests(unittest.TestCase):
    maxDiff = None

    def test_native_generator_and_definition(self):
        path = (
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py"
        )
        spec = importlib.util.spec_from_file_location("control_audit_normalizer", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        document = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(module.control_audit_route_descriptor(), document)
        self.assertEqual(document["id"], "route_control_audit_workflow")
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 23},
        )
        sources = document["provenance"]["sources"]
        self.assertIn("scripts/mathformer.py", [s["path"] for s in sources])
        for row in sources:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        registry = checked_registry(REGISTRY)
        self.assertEqual(registry[ACTION].depends_on, DEPENDENCIES)
        self.assertEqual(len(DEPENDENCIES), 9)
        self.assertFalse(registry[ACTION].command)
        self.assertTrue(
            all(registry[key].timeout_seconds is None for key in DEPENDENCIES)
        )
        self.assertEqual(registry["hub:audit"].command[-2:], ("audit", "--json"))

    def test_original_equivalence_and_native_state(self):
        oracle, _ = original()
        match = selected_match(MATCH)
        native = checked_registry(REGISTRY)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for mounted in [False, True]:
                if mounted:
                    populate(root)
                for keep in [False, True]:
                    context = hub.RunContext(dry_run=True, keep_going=keep)
                    self.assertEqual(
                        hub.run_intent_match(
                            match, native, context, repository_root=root
                        ),
                        oracle.run_intent_match(
                            match, native, context, repository_root=root
                        ),
                    )
                    for seen in [
                        [],
                        [ACTION],
                        [DEPENDENCIES[0]],
                        [DEPENDENCIES[5]],
                        ["caller"],
                    ]:
                        for args in [[], ["--invalid"]]:
                            before = deepcopy(seen)
                            self.assertEqual(
                                hub.run_action(
                                    ACTION,
                                    native,
                                    context,
                                    seen=set(seen),
                                    extra_args=args,
                                    repository_root=root,
                                ),
                                oracle.run_action(
                                    ACTION,
                                    native,
                                    context,
                                    seen=set(seen),
                                    extra_args=args,
                                    repository_root=root,
                                ),
                            )
                            self.assertEqual(seen, before)
                self.assertFalse((root / "artifacts").exists())
        # Full nine visits retain sticky failure, ordered history and copied
        # ancestry. A failure can stop at any position without an extra visit.
        for failed_index in range(9):
            for keep in [False, True]:
                context = hub.RunContext(keep_going=keep)
                state = hub.initialize_dependencies(
                    hub.admit_action(ACTION, native, seen=["caller"])
                )
                initial = deepcopy(state)
                for index in range(9):
                    previous = deepcopy(state)
                    child = {"ok": index != failed_index, "status": str(index)}
                    state, done = hub.advance_dependencies(
                        native[ACTION], state, child, context
                    )
                    self.assertEqual(state["index"], index + 1)
                    self.assertEqual(state["children"], previous["children"] + [child])
                    self.assertEqual(state["ancestry"], sorted([ACTION, "caller"]))
                    self.assertEqual(state["dependencies_ok"], index < failed_index)
                    self.assertEqual(
                        done, index == 8 or (index == failed_index and not keep)
                    )
                    if done:
                        break
                self.assertFalse(hub.finish_dependencies(native[ACTION], state)["ok"])
                self.assertEqual(initial["children"], [])
                self.assertEqual(initial["index"], 0)
                self.assertEqual(
                    len(state["children"]), 9 if keep else failed_index + 1
                )

    def test_compiler_boundary_and_failure_propagation(self):
        # Substitute only a compiler/provider process. Use actual admission,
        # preflight, recursive traversal, captures, sticky state and write audit.
        oracle, scope = original()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for mode in ["success", "fail", "timeout", "write", "crash", "preflight"]:
                leaf = hub.WorkflowAction(
                    "fixture:first",
                    "compiler",
                    "control",
                    "validation",
                    "read_only",
                    command=("fixture-control-compiler", mode),
                    required_paths=("absent",) if mode == "preflight" else (),
                    timeout_seconds=3 if mode == "timeout" else None,
                )
                second = replace(
                    leaf,
                    action_id="fixture:second",
                    command=("fixture-control-compiler", "success"),
                    required_paths=(),
                    timeout_seconds=None,
                )
                parent = replace(
                    hub.build_registry()[ACTION],
                    depends_on=(leaf.action_id, second.action_id),
                )
                registry = {
                    ACTION: parent,
                    leaf.action_id: leaf,
                    second.action_id: second,
                }
                for keep in [False, True]:
                    outputs, histories = [], []
                    for source in [oracle, hub]:
                        (root / "undeclared.txt").unlink(missing_ok=True)
                        old = source.subprocess
                        calls = install(source, root)
                        if source is oracle:
                            scope["subprocess"] = source.subprocess
                        try:
                            if mode == "crash":
                                with self.assertRaisesRegex(
                                    OSError, "compiler launch failed"
                                ):
                                    source.run_intent_match(
                                        selected_match(MATCH),
                                        registry,
                                        hub.RunContext(keep_going=keep),
                                        repository_root=root,
                                    )
                            else:
                                outputs.append(
                                    source.run_intent_match(
                                        selected_match(MATCH),
                                        registry,
                                        hub.RunContext(keep_going=keep),
                                        repository_root=root,
                                    )
                                )
                            histories.append(deepcopy(calls))
                        finally:
                            source.subprocess = old
                            if source is oracle:
                                scope["subprocess"] = old
                    self.assertEqual(histories[0], histories[1])
                    if mode == "crash":
                        self.assertEqual(len(histories[0]), 1)
                        continue
                    self.assertEqual(outputs[0], outputs[1])
                    result = outputs[0]
                    self.assertEqual(result["ok"], mode == "success")
                    sequence = result["children"][0]
                    self.assertEqual(
                        len(sequence["children"]), 2 if keep or mode == "success" else 1
                    )
                    child = sequence["children"][0]
                    if mode == "success":
                        self.assertEqual(child["returncode"], 0)
                        self.assertFalse(json.loads(child["stdout"])["ok"])
                        self.assertTrue(child["ok"])  # exit status, not embedded JSON
                    elif mode == "fail":
                        self.assertEqual(child["returncode"], 7)
                        self.assertEqual(child["stderr"], "compiler stderr")
                    elif mode == "timeout":
                        self.assertEqual(child["status"], "timeout")
                        self.assertEqual(child["stdout"], "partial")
                        self.assertIsNone(child["returncode"])
                        self.assertEqual(histories[0][0]["timeout"], 3)
                    elif mode == "write":
                        self.assertEqual(child["status"], "undeclared_writes")
                        self.assertEqual(
                            child["write_audit"]["unexpected_paths"], ["undeclared.txt"]
                        )
                    else:
                        self.assertEqual(
                            child["preflight_errors"], ["missing required path: absent"]
                        )
                        self.assertNotIn("returncode", child)
            # Both native argument and mutation admission prevent any compiler
            # launch; missing tools are also checked by the native preflight.
            calls = []
            with patch.object(
                hub, "subprocess", SimpleNamespace(run=lambda *a, **k: calls.append(a))
            ):
                for changed, args, error in [
                    (
                        replace(leaf, required_paths=()),
                        ["--x"],
                        "does not accept extra arguments",
                    ),
                    (
                        replace(leaf, required_paths=(), safety="writes_repo"),
                        [],
                        "safety=writes_repo",
                    ),
                    (
                        replace(
                            leaf,
                            required_paths=(),
                            required_tools=("missing-control-audit-fixture-tool",),
                        ),
                        [],
                        "missing required tool",
                    ),
                ]:
                    result = hub.run_leaf_action(
                        changed, hub.RunContext(), args, repository_root=root
                    )
                    self.assertFalse(result["ok"])
                    self.assertIn(error, result["preflight_errors"][0])
            self.assertEqual(calls, [])

    def test_registered_tools_and_real_prism_runtime(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(CONTRACT.read_text())
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        failure = None
        async with manager.open(
            "control-audit-route",
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
                    bound = compile_workflow(
                        "mcp:control-audit-route",
                        workflow_documents([DESCRIPTOR], assets)[0],
                        tools,
                    )
                    self.assertTrue(bound["runnable"], bound["diagnostics"])
                    self.assertTrue(bound["runtime_source"])
                    self.assertTrue(bound["prism_source"])
                    self.assertEqual(set(bound["bindings"]), set(doc["operations"]))
                    return bound, assets

                workflow, assets = compile(document)
                broken = deepcopy(document)
                broken["operations"]["visit"]["execution"]["binding"][
                    "target"
                ] = "absent_control_audit_tool"
                rejected = compile_workflow(
                    "mcp:control-audit-route",
                    workflow_documents([DESCRIPTOR], snapshot(broken))[0],
                    tools,
                )
                self.assertFalse(rejected["runnable"])
                self.assertTrue(rejected["diagnostics"])

                async def authorize():
                    pass

                async def run(inputs, changed=None):
                    compiled, received = (
                        compile(changed) if changed else (workflow, assets)
                    )
                    return await execute(compiled, received, inputs, remote, authorize)

                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory).resolve()
                    base = {
                        "match": MATCH,
                        "registry": REGISTRY,
                        "repository_root": str(root),
                        "context": vars(hub.RunContext(dry_run=True)),
                        "extra_args": [],
                        "seen": [],
                    }
                    for mounted in [False, True]:
                        if mounted:
                            populate(root)
                        # Removing the final leaf prevents git launching on the
                        # empty mount when exercising actual preflight failures.
                        for dry in ([True] if mounted else [False, True]):
                            for keep in [False, True]:
                                inputs = deepcopy(base)
                                inputs["context"].update(dry_run=dry, keep_going=keep)
                                if not dry:
                                    inputs["registry"].pop(DEPENDENCIES[-1])
                                result = await run(inputs)
                                expected = hub.run_intent_match(
                                    selected_match(MATCH),
                                    checked_registry(inputs["registry"]),
                                    hub.RunContext(**inputs["context"]),
                                    repository_root=root,
                                )
                                self.assertEqual(result["status"], "accepted", result)
                                self.assertEqual(
                                    result["outputs"], {"result": expected}
                                )
                                count = len(expected["children"][0]["children"])
                                operations = (
                                    [
                                        "initialize_route",
                                        "admit",
                                        "initialize_dependencies",
                                    ]
                                    + ["visit", "advance"] * count
                                    + ["finish_dependencies", "finish_route"]
                                )
                                self.assertEqual(
                                    [c["operation"] for c in result["calls"]],
                                    operations,
                                )
                                self.assertEqual(
                                    [c["tool"] for c in result["calls"]],
                                    [
                                        "mathformer_control_audit_" + op
                                        for op in operations
                                    ],
                                )
                                self.assertEqual(count, 9 if mounted or keep else 1)
                                self.assertEqual(
                                    result["outputs"]["result"]["ok"], mounted
                                )
                                self.assertTrue(result["runtime"]["effect_records"])
                                self.assertTrue(result["runtime"]["provenance"])
                                self.assertTrue(result["replay_artifacts"])
                                self.assertFalse((root / "artifacts").exists())
                    # Full nine visits hit the normal done guard on the final
                    # iteration, within the exact 23-operation ceiling.
                    inputs = deepcopy(base)
                    good = await run(inputs)
                    self.assertEqual(good["status"], "accepted", good)
                    self.assertTrue(good["outputs"]["result"]["ok"])
                    self.assertEqual(len(good["calls"]), 23)
                    self.assertEqual(good["outputs"]["result"]["route"]["score"], 17)
                    self.assertEqual(
                        good["outputs"]["result"]["route"]["matched_terms"],
                        MATCH["matched_terms"],
                    )
                    # Wire context reaches native admission and dependency
                    # cycle guards. Histories preserve early stop and failure.
                    for seen in [
                        [ACTION],
                        [DEPENDENCIES[0]],
                        [DEPENDENCIES[4]],
                        ["caller"],
                    ]:
                        for keep in [False, True]:
                            for args in [[], ["--invalid"]]:
                                inputs = deepcopy(base)
                                inputs["seen"], inputs["extra_args"] = seen, args
                                inputs["context"]["keep_going"] = keep
                                child = hub.run_action(
                                    ACTION,
                                    checked_registry(REGISTRY),
                                    hub.RunContext(**inputs["context"]),
                                    seen=set(seen),
                                    extra_args=args,
                                    repository_root=root,
                                )
                                state, _ = hub.advance_intent_state(
                                    hub.initialize_intent_state(),
                                    child,
                                    hub.RunContext(**inputs["context"]),
                                    1,
                                )
                                expected = hub.finish_intent_state(
                                    state,
                                    selected_match(MATCH),
                                    checked_registry(REGISTRY),
                                )
                                result = await run(inputs)
                                self.assertEqual(result["status"], "accepted", result)
                                self.assertEqual(
                                    result["outputs"], {"result": expected}
                                )
                                if seen == [ACTION] or args:
                                    self.assertEqual(
                                        [c["operation"] for c in result["calls"]],
                                        [
                                            "initialize_route",
                                            "admit",
                                            "reject",
                                            "carry",
                                            "carry",
                                            "finish_route",
                                        ],
                                    )
                    # Unknown children remain failure data; later successful
                    # children cannot reset aggregate failure under keep-going.
                    for keep in [False, True]:
                        inputs = deepcopy(base)
                        inputs["registry"].pop(DEPENDENCIES[0])
                        inputs["context"]["keep_going"] = keep
                        result = await run(inputs)
                        expected = hub.run_intent_match(
                            selected_match(MATCH),
                            checked_registry(inputs["registry"]),
                            hub.RunContext(**inputs["context"]),
                            repository_root=root,
                        )
                        self.assertEqual(result["outputs"], {"result": expected})
                        self.assertFalse(expected["ok"])
                        self.assertEqual(
                            expected["children"][0]["children"][0]["status"],
                            "unknown_action",
                        )
                        self.assertEqual(
                            len(expected["children"][0]["children"]), 9 if keep else 1
                        )
                        if keep:
                            self.assertTrue(
                                expected["children"][0]["children"][-1]["ok"]
                            )
                    # Missing parent is rejected; just as the original route,
                    # metadata packing then propagates KeyError to the caller.
                    inputs = deepcopy(base)
                    inputs["registry"] = {}
                    with self.assertRaises(KeyError):
                        hub.run_intent_match(
                            selected_match(MATCH),
                            {},
                            hub.RunContext(dry_run=True),
                            repository_root=root,
                        )
                    result = await run(inputs)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]],
                        [
                            "initialize_route",
                            "admit",
                            "reject",
                            "carry",
                            "carry",
                            "finish_route",
                        ],
                    )
                    # Executable caller-supplied registry metadata is refused.
                    inputs = deepcopy(base)
                    inputs["registry"][DEPENDENCIES[0]]["command"] = [
                        "arbitrary-command"
                    ]
                    result = await run(inputs)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]],
                        ["initialize_route", "admit"],
                    )
                    inputs = deepcopy(base)
                    inputs["match"]["route"]["title"] = "forged title"
                    result = await run(inputs)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    # The real runtime enforces budgets and fails closed on
                    # loop exhaustion without running downstream aggregation.
                    for budget in [1, 4, 22]:
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
                    loop = changed["flow"]["steps"][3]
                    loop["max_iterations"] = 1
                    loop["until"] = {"literal": False}
                    result = await run(base, changed)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]],
                        [
                            "initialize_route",
                            "admit",
                            "initialize_dependencies",
                            "visit",
                            "advance",
                        ],
                    )
                    # Invalid cursor fails inside the registered production
                    # tool and prevents advance/finalize. No retries are added.
                    changed = deepcopy(document)
                    visit = changed["flow"]["steps"][3]["body"]["cases"][0]["body"][
                        "steps"
                    ][0]
                    visit["arguments"]["state"] = {
                        "literal": {
                            "index": 9,
                            "children": [],
                            "dependencies_ok": True,
                            "ancestry": [ACTION],
                        }
                    }
                    result = await run(base, changed)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]],
                        [
                            "initialize_route",
                            "admit",
                            "initialize_dependencies",
                            "visit",
                        ],
                    )
                    # A null mount uses the native default. Dry-run prevents
                    # subprocesses even though real repository inputs exist.
                    inputs = deepcopy(base)
                    inputs["repository_root"] = None
                    result = await run(inputs)
                    self.assertEqual(result["status"], "accepted", result)
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
                    timed = deepcopy(document)
                    timed["policy"]["limits"]["wall_time_seconds"] = 1
                    bound, received = compile(timed)

                    async def waiting_authority():
                        await asyncio.Event().wait()

                    with self.assertRaises(TimeoutError):
                        await execute(bound, received, base, remote, waiting_authority)
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
