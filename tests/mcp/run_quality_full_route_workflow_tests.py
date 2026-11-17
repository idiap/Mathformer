#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Source parity, registered MCP ports and real Lunar/PRISM execution.

No production quality commands run. Dry runs and absent native registry entries
exercise repository controls; unchanged comprehensive source executes on a tiny
temporary matrix. Only external compiler/provider boundaries are substituted.
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
import xml.etree.ElementTree as ET
import yaml

import mathformer as hub
from quality_full_route_tools import (
    ACTION,
    ROUTE,
    selected_match,
    checked_registry,
    register_quality_full_route_tools,
)
from control_audit_compiler import install
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_quality_full_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
AUTHORED = "skills/control/workflow-contract-validator/references/quality-full-route.workflow.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
MATCH = {
    "route": {"route_id": ROUTE, "action_ids": [ACTION]},
    "score": 19.5,
    "matched_terms": ["full", "quality"],
}
NATIVE = hub.build_registry()
KEYS = [ACTION, "control:all", *NATIVE["control:all"].depends_on, "test:comprehensive"]
REGISTRY = {key: hub.action_to_dict(NATIVE[key]) for key in KEYS}


def original():
    scope = dict(vars(hub))
    exec((FIXTURES / "quality_full_route_original.py.txt").read_text(), scope)
    return SimpleNamespace(**scope)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def matrix(modes):
    return {
        "schema_version": 2,
        "tests": [
            dict(
                id=f"fixture.{i}",
                module_family=["lean", "atp", "control"][i % 3],
                command=["fixture-environment-compiler", mode],
                owner_skill="fixture",
                hook_id="test.fixture",
                fixture_ids=["external-compiler"],
                test_kind="regression",
                risk_level="low",
                timeout_seconds=31 + i,
                expected_exit=0,
                write_set=["artifacts/"] if mode == "artifact" else [],
                **(
                    {"optional_dependency": "fixture_missing_provider"}
                    if mode == "missing"
                    else {}
                ),
            )
            for i, mode in enumerate(modes)
        ],
    }


def populate(root):
    # Required paths are preflight inputs, never executable substitutes. All
    # control runs against these placeholders are dry; the delegate is copied.
    for key in KEYS:
        for relative in NATIVE[key].required_paths:
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.touch(exist_ok=True)
    for relative in [
        "tests/test_program/run_comprehensive_tests.py",
        "scripts/workflow_write_audit.py",
    ]:
        shutil.copyfile(ROOT / relative, root / relative)
        assert (root / relative).read_bytes() == (ROOT / relative).read_bytes()
    (root / "tests/test_matrix.json").write_text(json.dumps(matrix(["pass"])))


def reset(root):
    shutil.rmtree(root / "artifacts", ignore_errors=True)
    (root / "undeclared.txt").unlink(missing_ok=True)
    for name in ["compiler.jsonl", "delegate.jsonl"]:
        (root.parent / name).unlink(missing_ok=True)


def clean_env():
    return {
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": os.pathsep.join(
            [str(FIXTURES / "quality_full_route_startup"), str(FIXTURES)]
        ),
    }


def stable(value):
    if isinstance(value, list):
        return [stable(item) for item in value]
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if key in {"duration_seconds", "run_id"}:
                continue
            if key == "stdout" and isinstance(item, str) and item.startswith("{"):
                try:
                    item = json.loads(item)
                except ValueError:
                    pass
            result[key] = stable(item)
        return result
    return value


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


class QualityRouteTests(unittest.TestCase):
    maxDiff = None

    def test_identity_generator_and_source_parity(self):
        document = yaml.safe_load(CONTRACT.read_text())
        generator = load(
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
            "quality_route_normalizer",
        )
        self.assertEqual(generator.quality_full_route_descriptor(), document)
        self.assertEqual(json.loads((ROOT / AUTHORED).read_text()), document)
        self.assertEqual(document["id"], "route_quality_full_workflow")
        self.assertEqual(document["aliases"], [ROUTE])
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 16},
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
            {
                "path": "scripts/mathformer.py",
                "selector": "run_intent_match",
                "digest": "sha256:"
                + hashlib.sha256(
                    (ROOT / "scripts/mathformer.py").read_bytes()
                ).hexdigest(),
            },
            document["provenance"]["sources"],
        )
        self.assertEqual(checked_registry(REGISTRY), {key: NATIVE[key] for key in KEYS})
        native, match, oracle = (
            checked_registry(REGISTRY),
            selected_match(MATCH),
            original(),
        )
        self.assertEqual(
            native[ACTION].depends_on, ("control:all", "test:comprehensive")
        )
        self.assertFalse(native[ACTION].command)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            for ready in [False, True]:
                if ready:
                    populate(root)
                for keep in [False, True]:
                    ctx = hub.RunContext(dry_run=True, keep_going=keep)
                    self.assertEqual(
                        hub.run_intent_match(match, native, ctx, repository_root=root),
                        oracle.run_intent_match(
                            match, native, ctx, repository_root=root
                        ),
                    )
                    for seen in [
                        [],
                        [ACTION],
                        ["control:all"],
                        ["test:comprehensive"],
                        ["caller"],
                    ]:
                        for args in [[], ["--invalid"]]:
                            self.assertEqual(
                                hub.run_action(
                                    ACTION,
                                    native,
                                    ctx,
                                    seen=set(seen),
                                    extra_args=args,
                                    repository_root=root,
                                ),
                                oracle.run_action(
                                    ACTION,
                                    native,
                                    ctx,
                                    seen=set(seen),
                                    extra_args=args,
                                    repository_root=root,
                                ),
                            )
            self.assertFalse((root / "artifacts").exists())

    def test_native_external_compiler_failure_paths(self):
        # Synthetic external compiler declarations exercise the very same
        # native controllers; no native quality subprocess is replaced.
        oracle = original()
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
                    for runner in [oracle.run_intent_match, hub.run_intent_match]:
                        (root / "undeclared.txt").unlink(missing_ok=True)
                        # Patch only subprocess.run, retain native globals and
                        # use a fixture that rejects every non-compiler command.
                        holder = SimpleNamespace()
                        calls = install(holder, root)
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
                        if keep and mode != "pass":
                            self.assertTrue(child["children"][1]["ok"])
                            self.assertFalse(child["ok"])
                        if mode == "timeout":
                            self.assertEqual(child["children"][0]["stdout"], "partial")
                            self.assertEqual(child["children"][0]["status"], "timeout")
                        if mode == "write":
                            self.assertEqual(
                                child["children"][0]["write_audit"]["unexpected_paths"],
                                ["undeclared.txt"],
                            )

    def test_registered_service_policy(self):
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
            mcp = FastMCP("quality-route-policy")
            register_quality_full_route_tools(mcp, authorize, allowed)
            with tempfile.TemporaryDirectory() as temp:
                args = dict(
                    state={
                        "index": 1,
                        "children": [{"ok": True}],
                        "dependencies_ok": True,
                        "ancestry": [ACTION],
                    },
                    context=vars(hub.RunContext()),
                    registry=REGISTRY,
                    mount={"repository_root": temp},
                )
                with self.assertRaisesRegex(Exception, message):
                    await mcp.call_tool(
                        "mathformer_quality_route_visit_dependency", args
                    )
                args["context"]["dry_run"] = True
                await mcp.call_tool("mathformer_quality_route_visit_dependency", args)

    def test_real_registered_lunar_prism_execution(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(CONTRACT.read_text())
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve() / "repo"
            populate(root)
            server = (
                "import sys;sys.dont_write_bytecode=True;sys.path[:0]="
                + repr([str(ROOT / "scripts"), str(ROOT), str(FIXTURES), *SITES])
                + ";from quality_full_route_boundary import serve;serve("
                + repr(str(root))
                + ","
                + repr(str(FIXTURES))
                + ")"
            )
            manager, failure = SessionManager(), None
            async with manager.open(
                "quality-route",
                StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
                {},
            ) as remote:
                try:
                    tools = [
                        tool.model_dump(by_alias=True, exclude_none=True)
                        for tool in await remote.tools()
                    ]

                    def compile_document(doc, inventory=None):
                        assets = snapshot(doc)
                        workflow = compile_workflow(
                            "mcp:quality-route",
                            workflow_documents([DESCRIPTOR], assets)[0],
                            tools if inventory is None else inventory,
                        )
                        return workflow, assets

                    workflow, assets = compile_document(document)
                    self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                    self.assertTrue(workflow["prism_source"])
                    self.assertTrue(workflow["runtime_source"])
                    self.assertEqual(
                        set(workflow["bindings"]), set(document["operations"])
                    )
                    self.assertFalse(compile_document(document, [])[0]["runnable"])
                    broken = deepcopy(document)
                    broken["operations"]["visit_dependency"]["execution"]["binding"][
                        "target"
                    ] = "absent_quality_tool"
                    self.assertFalse(compile_document(broken)[0]["runnable"])
                    advertised = {tool["name"]: tool for tool in tools}
                    for operation in document["operations"].values():
                        binding = operation["execution"]["binding"]
                        self.assertEqual(binding["target"], binding["operation"])
                        tool = advertised[binding["target"]]
                        self.assertEqual(
                            set(tool["inputSchema"]["properties"]),
                            set(operation["inputs"]),
                        )
                        self.assertEqual(
                            set(tool["outputSchema"]["properties"]),
                            set(operation["outputs"]),
                        )

                    async def authorize():
                        pass

                    base = dict(
                        match=MATCH,
                        registry=REGISTRY,
                        context=vars(hub.RunContext(dry_run=True)),
                        mount={"repository_root": str(root)},
                    )

                    async def run(inputs=base, changed=document):
                        bound, received = compile_document(changed)
                        self.assertTrue(bound["runnable"], bound["diagnostics"])
                        return await execute(bound, received, inputs, remote, authorize)

                    # Full exact bound: nine control children, two quality
                    # children and one route child; no native process launch.
                    result = await run()
                    self.assertEqual(result["status"], "accepted", result)
                    expected = original().run_intent_match(
                        selected_match(MATCH),
                        checked_registry(REGISTRY),
                        hub.RunContext(dry_run=True),
                        repository_root=root,
                    )
                    self.assertEqual(result["outputs"], {"result": expected})
                    self.assertTrue(expected["ok"])
                    self.assertEqual(
                        len(expected["children"][0]["children"][0]["children"]), 9
                    )
                    order = [
                        "initialize_route",
                        "admit_quality",
                        "initialize_dependencies",
                        "visit_dependency",
                        "advance_dependencies",
                        "visit_dependency",
                        "advance_dependencies",
                        "finish_quality",
                        "advance_route",
                        "finish_route",
                    ]
                    self.assertEqual([c["operation"] for c in result["calls"]], order)
                    self.assertFalse((root.parent / "delegate.jsonl").exists())
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["runtime"]["provenance"])
                    self.assertTrue(result["replay_artifacts"])
                    # Missing real preflight input stops control and then
                    # quality; keep-going exhausts both finite native lists.
                    (root / NATIVE["hub:audit"].required_paths[0]).unlink()
                    for keep in [False, True]:
                        inputs = deepcopy(base)
                        inputs["context"]["keep_going"] = keep
                        result = await run(inputs)
                        expected = original().run_intent_match(
                            selected_match(MATCH),
                            checked_registry(REGISTRY),
                            hub.RunContext(**inputs["context"]),
                            repository_root=root,
                        )
                        self.assertEqual(result["outputs"], {"result": expected})
                        self.assertFalse(expected["ok"])
                        quality = expected["children"][0]
                        self.assertEqual(len(quality["children"]), 2 if keep else 1)
                        self.assertEqual(
                            len(quality["children"][0]["children"]), 9 if keep else 1
                        )
                        self.assertEqual(len(result["calls"]), 10 if keep else 8)
                    populate(root)
                    # Unknown control leaves preserve native failures while
                    # keep-going reaches the real comprehensive subprocess.
                    selected = {
                        key: REGISTRY[key]
                        for key in [ACTION, "control:all", "test:comprehensive"]
                    }
                    inputs = deepcopy(base)
                    inputs["registry"] = selected
                    inputs["context"].update(dry_run=False, keep_going=True)
                    for modes in [
                        ["pass", "artifact"],
                        ["fail", "timeout", "write", "pass"],
                        ["missing"],
                        ["large", "fail", "pass"],
                    ]:
                        reset(root)
                        data = matrix(modes)
                        if modes[0] == "large":
                            data["tests"][1]["expected_exit"] = 7
                            del data["tests"][2]["timeout_seconds"]
                        (root / "tests/test_matrix.json").write_text(json.dumps(data))
                        result = await run(inputs)
                        self.assertEqual(result["status"], "accepted", result)
                        route = result["outputs"]["result"]
                        quality = route["children"][0]
                        control, child = quality["children"]
                        self.assertEqual(
                            [c["status"] for c in control["children"]],
                            ["unknown_action"] * 9,
                        )
                        self.assertFalse(quality["ok"])
                        self.assertFalse(route["ok"])
                        self.assertEqual(route["route"]["score"], MATCH["score"])
                        self.assertEqual(
                            route["route"]["matched_terms"], MATCH["matched_terms"]
                        )
                        self.assertEqual(
                            [c["operation"] for c in result["calls"]], order
                        )
                        self.assertEqual(
                            child["argv"],
                            [sys.executable, *NATIVE["test:comprehensive"].command[1:]],
                        )
                        report = json.loads(child["stdout"])
                        self.assertEqual(
                            report["families"],
                            sorted(
                                load(
                                    root
                                    / "tests/test_program/run_comprehensive_tests.py",
                                    "quality_report_runner",
                                ).MODULE_FAMILIES
                            ),
                        )
                        self.assertEqual(report["summary"]["total"], len(modes))
                        self.assertEqual(
                            [r["check_id"] for r in report["results"]],
                            [r["id"] for r in data["tests"]],
                        )
                        self.assertEqual(report["schema_errors"], [])
                        self.assertEqual(child["returncode"], 0 if report["ok"] else 3)
                        outputs = root / "artifacts/test_program"
                        self.assertEqual(
                            json.loads(
                                (outputs / "deterministic_tests.json").read_text()
                            ),
                            report,
                        )
                        self.assertEqual(
                            [
                                json.loads(line)
                                for line in (outputs / "deterministic_tests.jsonl")
                                .read_text()
                                .splitlines()
                            ],
                            report["results"],
                        )
                        self.assertEqual(
                            len(
                                ET.parse(outputs / "deterministic_tests.xml")
                                .getroot()
                                .findall("testcase")
                            ),
                            len(modes),
                        )
                        self.assertTrue((outputs / "dependency_map.json").exists())
                        ledger = root.parent / "compiler.jsonl"
                        self.assertEqual(
                            (
                                [
                                    json.loads(line)
                                    for line in ledger.read_text().splitlines()
                                ]
                                if ledger.exists()
                                else []
                            ),
                            [
                                dict(
                                    command=row["command"],
                                    timeout=row.get("timeout_seconds", 120),
                                )
                                for row in data["tests"]
                                if "optional_dependency" not in row
                            ],
                        )
                        self.assertEqual(
                            json.loads((root.parent / "delegate.jsonl").read_text())[
                                "timeout"
                            ],
                            3600,
                        )
                        if "write" in modes:
                            self.assertEqual(
                                [r["status"] for r in report["results"]],
                                ["fail", "fail", "fail", "pass"],
                            )
                            self.assertEqual(report["results"][1]["stdout"], "partial")
                            self.assertEqual(child["status"], "undeclared_writes")
                            self.assertEqual(
                                child["write_audit"]["unexpected_paths"],
                                ["undeclared.txt"],
                            )
                        else:
                            self.assertTrue(report["ok"])
                            self.assertTrue(child["ok"])
                        if modes == ["missing"]:
                            self.assertEqual(report["results"][0]["status"], "skip")
                        reset(root)
                        with patch.dict(os.environ, clean_env(), clear=True):
                            expected = original().run_intent_match(
                                selected_match(MATCH),
                                checked_registry(selected),
                                hub.RunContext(**inputs["context"]),
                                repository_root=root,
                            )
                        self.assertEqual(stable(route), stable(expected))
                    # Early stop forbids delegate dispatch, even when its input
                    # is invalid. Unexpected compiler exceptions abort its
                    # subprocess and propagate as native nonzero child data.
                    reset(root)
                    (root / "tests/test_matrix.json").write_text("{}")
                    inputs["context"]["keep_going"] = False
                    result = await run(inputs)
                    self.assertEqual(
                        len(result["outputs"]["result"]["children"][0]["children"]), 1
                    )
                    self.assertFalse((root.parent / "delegate.jsonl").exists())
                    inputs["context"]["keep_going"] = True
                    for data, error in [
                        (matrix(["crash", "pass"]), "fixture compiler launch failed"),
                        (matrix([]), "at least one executable test row"),
                    ]:
                        reset(root)
                        (root / "tests/test_matrix.json").write_text(json.dumps(data))
                        result = await run(inputs)
                        self.assertEqual(result["status"], "accepted", result)
                        child = result["outputs"]["result"]["children"][0]["children"][
                            1
                        ]
                        self.assertFalse(child["ok"])
                        self.assertIn(error, child["stderr"])
                        self.assertFalse(
                            (
                                root / "artifacts/test_program/deterministic_tests.json"
                            ).exists()
                        )
                    # Native rejection is recorded before finish requires the
                    # absent registry metadata, exactly as the entrypoint does.
                    inputs = deepcopy(base)
                    inputs["registry"] = {}
                    result = await run(inputs)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]],
                        [
                            "initialize_route",
                            "admit_quality",
                            "reject_quality",
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
                    # Exact port-level state history, copied ancestry, sticky
                    # failure and exhaustion, including cycle observations.
                    admission = {
                        "accepted": True,
                        "status": "accepted",
                        "ancestry": [ACTION, "control:all", "caller"],
                    }
                    state = (
                        await remote.call(
                            "mathformer_quality_route_initialize_dependencies",
                            {"admission": admission},
                        )
                    )["state"]
                    child = (
                        await remote.call(
                            "mathformer_quality_route_visit_dependency",
                            dict(
                                state=state,
                                context=base["context"],
                                registry=REGISTRY,
                                mount=base["mount"],
                            ),
                        )
                    )["child"]
                    self.assertEqual(
                        child,
                        hub.reject_action(
                            "control:all",
                            hub.admit_action(
                                "control:all", NATIVE, seen=admission["ancestry"]
                            ),
                        ),
                    )
                    ctx = vars(hub.RunContext(dry_run=True, keep_going=True))
                    for i, child in enumerate([child, {"ok": True}]):
                        before = deepcopy(state)
                        advanced = await remote.call(
                            "mathformer_quality_route_advance_dependencies",
                            dict(
                                state=state, child=child, context=ctx, registry=REGISTRY
                            ),
                        )
                        state = advanced["state"]
                        self.assertEqual(
                            state["children"], before["children"] + [child]
                        )
                        self.assertEqual(state["index"], i + 1)
                        self.assertEqual(state["ancestry"], admission["ancestry"])
                        self.assertFalse(state["dependencies_ok"])
                        self.assertEqual(advanced["done"], i == 1)
                    self.assertFalse(
                        (
                            await remote.call(
                                "mathformer_quality_route_finish_quality",
                                dict(state=state, registry=REGISTRY),
                            )
                        )["child"]["ok"]
                    )
                    # Real PRISM exhaustion, call budgets and invalid cursor
                    # terminate execution; no retry or fabricated output.
                    for budget in [1, 7, 9]:
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
                    deps = changed["flow"]["steps"][1]["body"]["steps"][2]
                    deps["max_iterations"] = 1
                    result = await run(base, changed)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]], order[:5]
                    )
                    self.assertIsNone(result["outputs"])
                    changed = deepcopy(document)
                    changed["flow"]["steps"][1]["until"] = {"literal": False}
                    result = await run(base, changed)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]], order[:-1]
                    )
                    for port in ["match", "registry"]:
                        inputs = deepcopy(base)
                        if port == "match":
                            inputs[port]["route"]["title"] = "forged"
                        else:
                            inputs[port][ACTION]["command"] = ["arbitrary-command"]
                        result = await run(inputs)
                        self.assertEqual(result["status"], "failed", result)
                        self.assertEqual(len(result["calls"]), 2)
                    populate(root)
                    changed = deepcopy(document)
                    visit = changed["flow"]["steps"][1]["body"]["steps"][2]["body"][
                        "cases"
                    ][0]["body"]["steps"][0]
                    visit["arguments"]["state"] = {
                        "literal": {
                            "index": 2,
                            "children": [{"ok": True}, {"ok": True}],
                            "dependencies_ok": True,
                            "ancestry": [ACTION],
                        }
                    }
                    result = await run(base, changed)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]], order[:4]
                    )
                    # Actual server write-root check precedes comprehensive.
                    inputs = deepcopy(base)
                    inputs["context"]["dry_run"] = False
                    inputs["registry"] = {
                        key: selected[key] for key in [ACTION, "test:comprehensive"]
                    }
                    inputs["context"]["keep_going"] = True
                    inputs["mount"]["repository_root"] = str(root.parent / "outside")
                    result = await run(inputs)
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
    program = unittest.main(verbosity=2, exit=False)
    result = program.result
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
