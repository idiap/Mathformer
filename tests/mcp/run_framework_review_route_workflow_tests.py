#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native source parity, registered MCP interfaces and real Lunar/PRISM runtime.

Run with LUNAR_PLATFORM_ROOT and WORKFLOW_CONTRACT_PATH explicitly supplied.
Only external compiler/provider process boundaries are substituted. No source
workflow runs against production artifacts; all mounts and outputs are temporary.
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
FIXTURES = ROOT / "tests/mcp/fixtures"
SITES = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT),
    str(FIXTURES),
]
sys.path.extend(SITES)

import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib.util
import json
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import yaml

import mathformer as hub
from framework_review_route_tools import (
    ACTION,
    ROUTE,
    DEPENDENCIES,
    selected_match,
    checked_registry,
    register_framework_review_route_tools,
)
from control_audit_compiler import install as install_compiler
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_review_autoformalization_framework_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
AUTHORED = "skills/control/workflow-contract-validator/references/framework-review-route.workflow.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
MATCH = {
    "route": {"route_id": ROUTE, "action_ids": [ACTION]},
    "score": 19.5,
    "matched_terms": ["framework", "review"],
}
NATIVE_WHICH = shutil.which
NATIVE = hub.build_registry()
KEYS = [ACTION, *DEPENDENCIES, *NATIVE["control:all"].depends_on]
REGISTRY = {key: hub.action_to_dict(NATIVE[key]) for key in KEYS}
COHERENCE = "skills/mathformerphysicslib/mathformerphysicslib-coherence-gate/scripts/gate_coherence.py"
COMMON = "skills/mathformerphysicslib/mathformerphysicslib-coherence-inventory-builder/scripts/coherence_common.py"
REPORT = "artifacts/physics_lean/release_gate/report.json"


def original():
    scope = dict(vars(hub))
    exec((FIXTURES / "framework_review_original.py.txt").read_text(), scope)
    return SimpleNamespace(**scope)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def modes(root, **overrides):
    data = dict(build="pass", version="pass", docs="pass")
    data.update(overrides)
    (root.parent / "compiler-mode.json").write_text(json.dumps(data))
    for log in ["processes.jsonl"]:
        (root.parent / log).unlink(missing_ok=True)
    (root / "undeclared.txt").unlink(missing_ok=True)
    shutil.rmtree(root / "artifacts", ignore_errors=True)


def populate(root):
    # Control preflight paths are placeholders used ONLY for dry runs. Live
    # scenarios omit those registry entries rather than substitute native steps.
    for key in KEYS:
        for relative in NATIVE[key].required_paths:
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.touch(exist_ok=True)
    for relative in [
        "tests/physics_lean/run_mathformerphysicslib_release_gate.py",
        "libraries/MathformerPhysicsLib/release_status.py",
        COHERENCE,
        COMMON,
        "tests/run_docs.py",
        "tests/test_program/run_comprehensive_tests.py",
        "scripts/workflow_write_audit.py",
    ]:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
        assert target.read_bytes() == (ROOT / relative).read_bytes()
    for relative, content in {
        "libraries/MathformerPhysicsLib.lean": "import Fixture.Module\n",
        "Fixture/Module.lean": "-- compiler fixture input\n",
        "lake-manifest.json": '{"fixture":true}',
        "MathformerPhysicsLib/MANIFEST.json": '{"backends":{"Lean":{"foundations":{}}}}',
        "MathformerPhysicsLib/Lean/Foundations.lean": "-- fixture index\n",
    }.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    matrix = {
        "schema_version": 2,
        "tests": [
            dict(
                id="fixture.docs.provider",
                module_family="docs",
                command=["fixture-framework-provider", "compile"],
                owner_skill="fixture",
                hook_id="test.fixture",
                fixture_ids=["external-provider"],
                test_kind="regression",
                risk_level="low",
                timeout_seconds=17,
                expected_exit=0,
                write_set=[],
            )
        ],
    }
    (root / "tests/test_matrix.json").write_text(json.dumps(matrix))
    modes(root)


def snapshot(document):
    paths = {SCHEMA} | {row["path"] for row in document["provenance"]["sources"]}
    values = {path: (ROOT / path).read_text() for path in paths}
    values[DESCRIPTOR] = json.dumps(document)
    return [
        dict(
            path=path,
            content=content,
            encoding="text",
            sha256=hashlib.sha256(content.encode()).hexdigest(),
        )
        for path, content in values.items()
    ]


class FrameworkReviewTests(unittest.TestCase):
    maxDiff = None

    def test_identity_provenance_and_native_parity(self):
        document = yaml.safe_load(CONTRACT.read_text())
        generator = load(
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
            "framework_normalizer",
        )
        self.assertEqual(generator.framework_review_route_descriptor(), document)
        self.assertEqual(json.loads((ROOT / AUTHORED).read_text()), document)
        self.assertEqual(
            document["id"], "route_review_autoformalization_framework_workflow"
        )
        self.assertEqual(document["aliases"], [ROUTE])
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 12},
        )
        self.assertEqual(
            document["policy"]["failure"],
            {"default": "fail", "retry": {"max_attempts": 1, "retryable_codes": []}},
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        self.assertIn(
            "scripts/mathformer.py",
            [s["path"] for s in document["provenance"]["sources"]],
        )
        self.assertEqual(checked_registry(REGISTRY), {k: NATIVE[k] for k in KEYS})
        with (
            tempfile.TemporaryDirectory() as temp,
            patch.object(
                hub.shutil,
                "which",
                lambda name: (
                    str(Path(gettempdir()) / "mathformer-test-fixtures/fixture/lake")
                    if name == "lake"
                    else NATIVE_WHICH(name)
                ),
            ),
        ):
            root = Path(temp).resolve()
            for ready in [False, True]:
                if ready:
                    populate(root)
                for keep in [False, True]:
                    context = hub.RunContext(dry_run=True, keep_going=keep)
                    native, match = checked_registry(REGISTRY), selected_match(MATCH)
                    self.assertEqual(
                        hub.run_intent_match(
                            match, native, context, repository_root=root
                        ),
                        original().run_intent_match(
                            match, native, context, repository_root=root
                        ),
                    )
                    for seen in [set(), {ACTION}, {"control:all"}, {"caller"}]:
                        for extra in [[], ["--bad"]]:
                            before = seen.copy()
                            self.assertEqual(
                                hub.run_action(
                                    ACTION,
                                    native,
                                    context,
                                    seen=seen,
                                    extra_args=extra,
                                    repository_root=root,
                                ),
                                original().run_action(
                                    ACTION,
                                    native,
                                    context,
                                    seen=seen,
                                    extra_args=extra,
                                    repository_root=root,
                                ),
                            )
                            self.assertEqual(seen, before)
            self.assertFalse((root / "artifacts").exists())
        # Actual unknown/cycle/extra-arg guard precedence and distinct outcomes.
        for registry, seen, extra, status in [
            ({}, {ACTION}, ["bad"], "unknown_action"),
            (NATIVE, {ACTION}, ["bad"], "dependency_cycle"),
            (NATIVE, set(), ["bad"], "extra_args_for_sequence"),
        ]:
            result = hub.run_action(
                ACTION, registry, hub.RunContext(), seen=seen, extra_args=extra
            )
            self.assertEqual(result["status"], status)
            self.assertFalse(result["ok"])

    def test_external_compiler_failure_propagation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            for mode in ["pass", "fail", "timeout", "write", "crash"]:
                for keep in [False, True]:
                    registry = {
                        ACTION: replace(
                            NATIVE[ACTION],
                            depends_on=("fixture:first", "fixture:second"),
                        )
                    }
                    for name, command in [("first", mode), ("second", "pass")]:
                        registry["fixture:" + name] = hub.WorkflowAction(
                            "fixture:" + name,
                            "compiler fixture",
                            "quality",
                            "validation",
                            "read_only",
                            command=("fixture-control-compiler", command),
                            timeout_seconds=120,
                        )
                    outcomes, traces = [], []
                    for runner in [original().run_intent_match, hub.run_intent_match]:
                        (root / "undeclared.txt").unlink(missing_ok=True)
                        holder = SimpleNamespace()
                        calls = install_compiler(holder, root)
                        with patch.object(hub.subprocess, "run", holder.subprocess.run):
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
                                outcomes.append(
                                    runner(
                                        selected_match(MATCH),
                                        registry,
                                        hub.RunContext(keep_going=keep),
                                        repository_root=root,
                                    )
                                )
                        traces.append(calls)
                    self.assertEqual(*traces)
                    self.assertEqual(
                        len(traces[0]),
                        2 if mode == "pass" or (keep and mode != "crash") else 1,
                    )
                    if outcomes:
                        self.assertEqual(*outcomes)
                        child = outcomes[0]["children"][0]
                        self.assertEqual(child["ok"], mode == "pass")
                        self.assertEqual(len(child["children"]), len(traces[0]))
                        if mode == "timeout":
                            self.assertEqual(child["children"][0]["status"], "timeout")
                            self.assertEqual(child["children"][0]["stdout"], "partial")
                        if mode == "write":
                            self.assertEqual(
                                child["children"][0]["write_audit"]["unexpected_paths"],
                                ["undeclared.txt"],
                            )
                        if keep and mode not in ["pass", "crash"]:
                            self.assertTrue(child["children"][1]["ok"])
                            self.assertFalse(child["ok"])

    def test_service_policy(self):
        asyncio.run(self.policy())

    async def policy(self):
        from mcp.server.fastmcp import FastMCP

        for authorize, allowed, message in [
            (
                lambda: (_ for _ in ()).throw(PermissionError("readonly")),
                lambda p: True,
                "readonly",
            ),
            (lambda: None, lambda p: False, "service roots"),
        ]:
            mcp = FastMCP("framework-policy")
            register_framework_review_route_tools(mcp, authorize, allowed)
            args = dict(
                state={
                    "index": 2,
                    "children": [{"ok": True}] * 2,
                    "dependencies_ok": True,
                    "ancestry": [ACTION],
                },
                context=vars(hub.RunContext()),
                registry=REGISTRY,
                mount={
                    "repository_root": str(
                        Path(gettempdir()) / "fixture-framework-policy"
                    )
                },
            )
            with self.assertRaisesRegex(Exception, message):
                await mcp.call_tool(
                    "mathformer_framework_review_visit_dependency", args
                )
            args["context"]["dry_run"] = True
            await mcp.call_tool("mathformer_framework_review_visit_dependency", args)

    def test_real_lunar_registered_execution(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(CONTRACT.read_text())
        with (
            tempfile.TemporaryDirectory() as temp,
            patch.object(
                hub.shutil,
                "which",
                lambda name: (
                    str(Path(gettempdir()) / "mathformer-test-fixtures/fixture/lake")
                    if name == "lake"
                    else NATIVE_WHICH(name)
                ),
            ),
        ):
            root = Path(temp).resolve() / "repo"
            populate(root)
            server = (
                "import sys;sys.dont_write_bytecode=True;sys.path[:0]="
                + repr([str(ROOT / "scripts"), str(ROOT), str(FIXTURES), *SITES])
                + ";from framework_review_boundary import serve;serve("
                + repr(str(root))
                + ","
                + repr(str(FIXTURES))
                + ")"
            )
            manager = SessionManager()
            failure = None
            async with manager.open(
                "framework-review",
                StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
                {},
            ) as remote:
                try:
                    tools = [
                        t.model_dump(by_alias=True, exclude_none=True)
                        for t in await remote.tools()
                    ]

                    def compile_document(doc, inventory=None):
                        assets = snapshot(doc)
                        return (
                            compile_workflow(
                                "mcp:framework-review",
                                workflow_documents([DESCRIPTOR], assets)[0],
                                tools if inventory is None else inventory,
                            ),
                            assets,
                        )

                    bound, assets = compile_document(document)
                    self.assertTrue(bound["runnable"], bound["diagnostics"])
                    self.assertTrue(bound["prism_source"])
                    self.assertTrue(bound["runtime_source"])
                    self.assertEqual(
                        set(bound["bindings"]), set(document["operations"])
                    )
                    self.assertFalse(compile_document(document, [])[0]["runnable"])
                    broken = deepcopy(document)
                    broken["operations"]["visit_dependency"]["execution"]["binding"][
                        "target"
                    ] = "absent_tool"
                    self.assertFalse(compile_document(broken)[0]["runnable"])
                    inventory = {t["name"]: t for t in tools}
                    for op in document["operations"].values():
                        binding = op["execution"]["binding"]
                        self.assertEqual(binding["target"], binding["operation"])
                        tool = inventory[binding["target"]]
                        self.assertEqual(
                            set(tool["inputSchema"]["properties"]), set(op["inputs"])
                        )
                        self.assertEqual(
                            set(tool["outputSchema"]["properties"]), set(op["outputs"])
                        )

                    async def authorize():
                        pass

                    base = dict(
                        match=MATCH,
                        registry=REGISTRY,
                        context=vars(hub.RunContext(dry_run=True)),
                        mount={"repository_root": str(root)},
                    )

                    async def run(inputs=base, doc=document):
                        workflow, received = compile_document(doc)
                        self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                        return await execute(
                            workflow, received, inputs, remote, authorize
                        )

                    order = [
                        "initialize_route",
                        "select_and_admit",
                        "initialize_dependencies",
                        "visit_dependency",
                        "advance_dependencies",
                        "visit_dependency",
                        "advance_dependencies",
                        "visit_dependency",
                        "advance_dependencies",
                        "finish_dependencies",
                        "advance_route",
                        "finish_route",
                    ]
                    for ready in [True, False]:
                        if not ready:
                            (root / NATIVE["hub:audit"].required_paths[0]).unlink()
                        for keep in [False, True]:
                            inputs = deepcopy(base)
                            inputs["context"]["keep_going"] = keep
                            result = await run(inputs)
                            self.assertEqual(result["status"], "accepted", result)
                            expected = original().run_intent_match(
                                selected_match(MATCH),
                                checked_registry(REGISTRY),
                                hub.RunContext(**inputs["context"]),
                                repository_root=root,
                            )
                            self.assertEqual(result["outputs"], {"result": expected})
                            self.assertEqual(expected["ok"], ready)
                            self.assertEqual(
                                len(expected["children"][0]["children"]),
                                3 if ready or keep else 1,
                            )
                            self.assertEqual(
                                len(expected["children"][0]["children"][0]["children"]),
                                9 if ready or keep else 1,
                            )
                            self.assertEqual(
                                [c["operation"] for c in result["calls"]],
                                order if ready or keep else order[:5] + order[-3:],
                            )
                            self.assertTrue(result["runtime"]["effect_records"])
                            self.assertTrue(result["runtime"]["provenance"])
                            self.assertTrue(result["replay_artifacts"])
                    self.assertFalse((root.parent / "processes.jsonl").exists())
                    populate(root)
                    # Live native Python only in isolated fixture. The first
                    # control failure cannot be cleared by successful docs or release.
                    inputs = deepcopy(base)
                    inputs["registry"] = {
                        k: REGISTRY[k] for k in [ACTION, *DEPENDENCIES]
                    }
                    inputs["context"].update(dry_run=False, keep_going=True)
                    cases = [
                        ({}, True),
                        ({"build": "fail"}, False),
                        ({"build": "timeout"}, False),
                        ({"version": "fail"}, False),
                        ({"build": "write"}, True),
                        ({"build": "artifact"}, True),
                        ({"docs": "fail"}, True),
                    ]
                    for overrides, release_ok in cases:
                        modes(root, **overrides)
                        result = await run(inputs)
                        self.assertEqual(result["status"], "accepted", result)
                        route = result["outputs"]["result"]
                        parent = route["children"][0]
                        control, docs, release = parent["children"]
                        self.assertFalse(route["ok"])
                        self.assertFalse(parent["ok"])
                        self.assertEqual(
                            [c["status"] for c in control["children"]],
                            ["unknown_action"] * 9,
                        )
                        self.assertEqual(
                            docs["ok"], overrides.get("docs") != "fail", docs
                        )
                        self.assertEqual(
                            release["argv"],
                            [
                                sys.executable,
                                *NATIVE["mathformerphysicslib:release-gate"].command[
                                    1:
                                ],
                            ],
                        )
                        self.assertTrue(release["stdout"], release)
                        report = json.loads(release["stdout"])
                        self.assertEqual(
                            report, json.loads((root / REPORT).read_text())
                        )
                        self.assertEqual(report["release_ok"], release_ok)
                        self.assertEqual(release["returncode"], 0 if release_ok else 1)
                        self.assertEqual(
                            report["public_root_sha256"],
                            hashlib.sha256(
                                (
                                    root / "libraries/MathformerPhysicsLib.lean"
                                ).read_bytes()
                            ).hexdigest(),
                        )
                        self.assertEqual(
                            report["imported_modules"],
                            [
                                {
                                    "path": "Fixture/Module.lean",
                                    "sha256": hashlib.sha256(
                                        (root / "Fixture/Module.lean").read_bytes()
                                    ).hexdigest(),
                                }
                            ],
                        )
                        self.assertEqual(
                            report["lake_manifest_sha256"],
                            hashlib.sha256(
                                (root / "lake-manifest.json").read_bytes()
                            ).hexdigest(),
                        )
                        self.assertEqual(
                            report["build"]["command"],
                            ["lake", "build", "MathformerPhysicsLib"],
                        )
                        self.assertEqual(
                            report["lean_version"]["command"],
                            ["lake", "env", "lean", "--version"],
                        )
                        self.assertTrue(report["coherence"]["ok"])
                        trace = [
                            json.loads(line)
                            for line in (root.parent / "processes.jsonl")
                            .read_text()
                            .splitlines()
                        ]
                        self.assertEqual(
                            [row["timeout"] for row in trace],
                            [None, 17, 1200, 900, 180, 30],
                        )
                        self.assertEqual(
                            [row["command"][0] for row in trace[-3:]],
                            ["lake", sys.executable, "lake"],
                        )
                        if overrides.get("build") == "timeout":
                            self.assertTrue(report["build"]["timeout"])
                            self.assertEqual(
                                report["build"]["stdout"], "partial compiler output"
                            )
                        if overrides.get("build") == "write":
                            self.assertFalse(release["ok"])
                            self.assertEqual(release["status"], "undeclared_writes")
                            self.assertEqual(
                                release["write_audit"]["unexpected_paths"],
                                ["undeclared.txt"],
                            )
                        else:
                            self.assertEqual(release["ok"], release_ok)
                            self.assertTrue(release["write_audit"]["ok"])
                    # Native deterministic coherence failure is real data, not a
                    # substituted gate. Build/version still execute in order.
                    modes(root)
                    (root / "MathformerPhysicsLib/MANIFEST.json").unlink()
                    result = await run(inputs)
                    release = result["outputs"]["result"]["children"][0]["children"][2]
                    report = json.loads(release["stdout"])
                    self.assertFalse(report["coherence"]["ok"])
                    self.assertFalse(report["release_ok"])
                    self.assertIn("coherence_release_blocked", report["blockers"])
                    populate(root)
                    # Launch errors propagate through real release main and the
                    # native leaf exit, without retry or fabricated report.
                    modes(root, build="crash")
                    result = await run(inputs)
                    release = result["outputs"]["result"]["children"][0]["children"][2]
                    self.assertFalse(release["ok"])
                    self.assertIn("fixture compiler launch failed", release["stderr"])
                    self.assertFalse((root / REPORT).exists())
                    # Rejected top-level registry metadata has the original
                    # KeyError at finish; inspect its rejection history first.
                    result = await run({**base, "registry": {}})
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]],
                        [
                            "initialize_route",
                            "select_and_admit",
                            "reject_review",
                            "carry_rejection",
                            "carry_rejection",
                            "advance_route",
                            "finish_route",
                        ],
                    )
                    with self.assertRaises(KeyError):
                        original().run_intent_match(
                            selected_match(MATCH),
                            {},
                            hub.RunContext(dry_run=True),
                            repository_root=root,
                        )
                    # Registered MCP step histories and copied ancestry.
                    admission = {
                        "accepted": True,
                        "status": "accepted",
                        "ancestry": [ACTION, "control:all", "caller"],
                    }
                    state = (
                        await remote.call(
                            "mathformer_framework_review_initialize_dependencies",
                            {"admission": admission},
                        )
                    )["state"]
                    cycle = (
                        await remote.call(
                            "mathformer_framework_review_visit_dependency",
                            dict(
                                state=state,
                                context=base["context"],
                                registry=REGISTRY,
                                mount=base["mount"],
                            ),
                        )
                    )["child"]
                    self.assertEqual(
                        cycle,
                        hub.reject_action(
                            "control:all",
                            hub.admit_action(
                                "control:all", NATIVE, seen=admission["ancestry"]
                            ),
                        ),
                    )
                    for i, child in enumerate([cycle, {"ok": True}, {"ok": True}]):
                        before = deepcopy(state)
                        advanced = await remote.call(
                            "mathformer_framework_review_advance_dependencies",
                            dict(
                                state=state,
                                child=child,
                                context={**base["context"], "keep_going": True},
                                registry=REGISTRY,
                            ),
                        )
                        state = advanced["state"]
                        self.assertEqual(
                            state["children"], before["children"] + [child]
                        )
                        self.assertEqual(state["index"], i + 1)
                        self.assertFalse(state["dependencies_ok"])
                        self.assertEqual(state["ancestry"], admission["ancestry"])
                        self.assertEqual(advanced["done"], i == 2)
                    self.assertFalse(
                        (
                            await remote.call(
                                "mathformer_framework_review_finish_dependencies",
                                dict(state=state, registry=REGISTRY),
                            )
                        )["child"]["ok"]
                    )
                    populate(root)
                    for budget in [1, 7, 11]:
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
                    changed["flow"]["steps"][1]["body"]["steps"][2][
                        "max_iterations"
                    ] = 2
                    result = await run(base, changed)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]], order[:7]
                    )
                    changed = deepcopy(document)
                    changed["flow"]["steps"][1]["until"] = {"literal": False}
                    result = await run(base, changed)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]], order[:-1]
                    )
                    for port in ["match", "registry"]:
                        bad = deepcopy(base)
                        if port == "match":
                            bad[port]["route"]["title"] = "forged"
                        else:
                            bad[port][ACTION]["command"] = ["forged"]
                        result = await run(bad)
                        self.assertEqual(result["status"], "failed", result)
                        self.assertEqual(len(result["calls"]), 2)
                    changed = deepcopy(document)
                    visit = changed["flow"]["steps"][1]["body"]["steps"][2]["body"][
                        "cases"
                    ][0]["body"]["steps"][0]
                    visit["arguments"]["state"] = {
                        "literal": {
                            "index": 3,
                            "children": [{"ok": True}] * 3,
                            "dependencies_ok": True,
                            "ancestry": [ACTION],
                        }
                    }
                    result = await run(base, changed)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]], order[:4]
                    )
                    bad = deepcopy(inputs)
                    bad["mount"]["repository_root"] = str(root.parent / "outside")
                    result = await run(bad)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]], order[:6]
                    )
                    timed = deepcopy(document)
                    timed["policy"]["limits"]["wall_time_seconds"] = 1
                    bound, received = compile_document(timed)

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
    result = unittest.main(verbosity=2, exit=False).result
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
