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
from quality_strict_route_tools import ACTION, ROUTE, selected_match, checked_registry
from control_audit_compiler import install
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_quality_strict_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
AUTHORED = "skills/control/workflow-contract-validator/references/quality-strict-route.workflow.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
MATCH = {
    "route": {"route_id": ROUTE, "action_ids": [ACTION]},
    "score": 19.5,
    "matched_terms": ["full", "quality"],
}
NATIVE = hub.build_registry()
KEYS = [
    ACTION,
    "control:all",
    *NATIVE["control:all"].depends_on,
    "test:comprehensive-strict",
]
REGISTRY = {key: hub.action_to_dict(NATIVE[key]) for key in KEYS}


def original():
    scope = dict(vars(hub))
    exec((FIXTURES / "quality_strict_route_original.py.txt").read_text(), scope)
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


class StrictRouteTests(unittest.TestCase):
    maxDiff = None

    def test_source_and_authored_contract(self):
        document = yaml.safe_load(CONTRACT.read_text())
        generator = load(
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
            "strict_normalizer",
        )
        self.assertEqual(generator.quality_strict_route_descriptor(), document)
        self.assertEqual(json.loads((ROOT / AUTHORED).read_text()), document)
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 5},
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
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for keep in [False, True]:
                context = hub.RunContext(dry_run=True, keep_going=keep)
                native = checked_registry(REGISTRY)
                self.assertEqual(
                    hub.run_intent_match(
                        selected_match(MATCH), native, context, repository_root=root
                    ),
                    original().run_intent_match(
                        selected_match(MATCH), native, context, repository_root=root
                    ),
                )
                for seen in [set(), {ACTION}, {"caller"}]:
                    for extra in [[], ["--bad"]]:
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
        for keep in [False, True]:
            state = hub.initialize_intent_state()
            state, done = hub.advance_intent_state(
                state, {"ok": False}, hub.RunContext(keep_going=keep), 1
            )
            self.assertEqual(state, {"ok": False, "children": [{"ok": False}]})
            self.assertTrue(done)

    def test_native_compiler_boundary(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
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
                    results, traces = [], []
                    for runner in [original().run_intent_match, hub.run_intent_match]:
                        (root / "undeclared.txt").unlink(missing_ok=True)
                        holder = SimpleNamespace()
                        calls = install(holder, root)
                        with patch.object(hub.subprocess, "run", holder.subprocess.run):
                            if mode == "crash":
                                with self.assertRaises(OSError):
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
                        traces.append(calls)
                    self.assertEqual(*traces)
                    self.assertEqual(
                        len(traces[0]),
                        2 if mode == "pass" or (keep and mode != "crash") else 1,
                    )
                    if results:
                        self.assertEqual(*results)
                        self.assertEqual(results[0]["ok"], mode == "pass")
                        if mode == "timeout":
                            self.assertEqual(
                                results[0]["children"][0]["children"][0]["status"],
                                "timeout",
                            )
                        if mode == "write":
                            self.assertEqual(
                                results[0]["children"][0]["children"][0]["write_audit"][
                                    "unexpected_paths"
                                ],
                                ["undeclared.txt"],
                            )

    def test_lunar_registered_execution(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(CONTRACT.read_text())
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve() / "repo"
            populate(root)
            server = (
                "import sys;sys.dont_write_bytecode=True;sys.path[:0]="
                + repr([str(ROOT / "scripts"), str(ROOT), str(FIXTURES), *SITES])
                + ";from quality_strict_route_boundary import serve;serve("
                + repr(str(root))
                + ","
                + repr(str(FIXTURES))
                + ")"
            )
            manager = SessionManager()
            failure = None
            async with manager.open(
                "strict-route",
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
                                "mcp:strict-route",
                                workflow_documents([DESCRIPTOR], assets)[0],
                                tools if inventory is None else inventory,
                            ),
                            assets,
                        )

                    bound, assets = compile_document(document)
                    self.assertTrue(bound["runnable"], bound["diagnostics"])
                    self.assertTrue(bound["prism_source"])
                    self.assertTrue(bound["runtime_source"])
                    self.assertFalse(compile_document(document, [])[0]["runnable"])
                    inventory = {t["name"]: t for t in tools}
                    for op in document["operations"].values():
                        tool = inventory[op["execution"]["binding"]["target"]]
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
                        "initialize",
                        "select",
                        "execute_action",
                        "advance",
                        "finish",
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
                                [c["operation"] for c in result["calls"]], order
                            )
                            self.assertEqual(
                                len(expected["children"][0]["children"]),
                                2 if ready or keep else 1,
                            )
                            self.assertTrue(result["runtime"]["effect_records"])
                            self.assertTrue(result["runtime"]["provenance"])
                    populate(root)
                    # Real strict delegate in a temporary mount with only external
                    # compiler/provider boundaries substituted by sitecustomize.
                    inputs = deepcopy(base)
                    inputs["registry"] = {
                        k: REGISTRY[k]
                        for k in [ACTION, "control:all", "test:comprehensive-strict"]
                    }
                    inputs["context"].update(dry_run=False, keep_going=True)
                    families = sorted(
                        load(
                            root / "tests/test_program/run_comprehensive_tests.py",
                            "strict_test_runner",
                        ).MODULE_FAMILIES
                    )
                    for modes in [
                        ["pass"],
                        ["fail", "timeout", "write", "pass"],
                        ["missing"],
                        [],
                        ["pass"] * len(families),
                    ]:
                        reset(root)
                        data = matrix(modes)
                        complete = len(modes) == len(families)
                        if complete:
                            for row, family in zip(data["tests"], families):
                                row["module_family"] = family
                        (root / "tests/test_matrix.json").write_text(json.dumps(data))
                        result = await run(inputs)
                        self.assertEqual(result["status"], "accepted", result)
                        route = result["outputs"]["result"]
                        control, child = route["children"][0]["children"]
                        self.assertFalse(route["ok"])
                        self.assertEqual(
                            [c["status"] for c in control["children"]],
                            ["unknown_action"] * 9,
                        )
                        self.assertEqual(
                            child["argv"],
                            [
                                sys.executable,
                                *NATIVE["test:comprehensive-strict"].command[1:],
                            ],
                        )
                        if not modes:
                            self.assertEqual(child["returncode"], 1)
                            self.assertIn(
                                "must contain at least one executable test row",
                                child["stderr"],
                            )
                            self.assertEqual(child["stdout"], "")
                            continue
                        self.assertTrue(child["stdout"], (modes, child))
                        report = json.loads(child["stdout"])
                        self.assertEqual(report["profile"], "strict")
                        self.assertEqual(report["ok"], complete)
                        self.assertEqual(
                            report["capability_ledger"]["strict_ready"], complete
                        )
                        self.assertEqual(report["summary"]["total"], len(modes))
                        self.assertEqual(
                            [r["check_id"] for r in report["results"]],
                            [r["id"] for r in data["tests"]],
                        )
                        self.assertEqual(child["returncode"], 0 if complete else 3)
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
                        if "missing" in modes:
                            self.assertEqual(report["summary"]["fail"], 1)
                            self.assertEqual(
                                report["capability_ledger"][
                                    "unavailable_selected_dependencies"
                                ],
                                ["fixture_missing_provider"],
                            )
                        output = root / "artifacts/test_program"
                        self.assertEqual(
                            json.loads(
                                (output / "deterministic_tests.json").read_text()
                            ),
                            report,
                        )
                        self.assertEqual(
                            len(
                                ET.parse(output / "deterministic_tests.xml")
                                .getroot()
                                .findall("testcase")
                            ),
                            len(modes),
                        )
                    for budget in [1, 3, 4]:
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
                            inputs[port][ACTION]["command"] = ["forged"]
                        result = await run(inputs)
                        self.assertEqual(result["status"], "failed", result)
                    inputs = deepcopy(base)
                    inputs["context"]["dry_run"] = False
                    inputs["mount"]["repository_root"] = str(root.parent / "outside")
                    result = await run(inputs)
                    self.assertEqual(result["status"], "failed", result)
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
