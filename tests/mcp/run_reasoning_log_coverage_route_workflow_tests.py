#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Real native/MCP/Lunar tests, using synthetic repository data only.

No provider exists in the selected route. Only a separate external compiler
boundary is substituted to exercise launch errors, timeouts and write audits.
The selected auditor itself always uses its real source implementation.
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
import subprocess
from types import SimpleNamespace
import tempfile
import unittest
import yaml

import mathformer as hub
from reasoning_log_coverage_route_tools import (
    ACTION,
    ROUTE,
    checked_registry,
    selected_match,
)
from reasoning_log_coverage_tree import AUDITOR, WRAPPER, populate, load_auditor
from reasoning_route_compiler import install
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_control_reasoning_log_coverage_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
MATCH = {
    "route": {"route_id": ROUTE, "action_ids": [ACTION]},
    "score": 23,
    "matched_terms": ["reasoning", "log", "coverage"],
}
REGISTRY = {ACTION: hub.action_to_dict(hub.build_registry()[ACTION])}


def original():
    scope = dict(vars(hub))
    exec(
        (
            ROOT / "tests/mcp/fixtures/reasoning_log_coverage_original.py.txt"
        ).read_text(),
        scope,
    )
    return SimpleNamespace(**scope), scope


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


class CoverageTests(unittest.TestCase):
    maxDiff = None

    def test_definition_generator_native_argv_and_digests(self):
        spec = importlib.util.spec_from_file_location(
            "coverage_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        document = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(module.reasoning_log_coverage_route_descriptor(), document)
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 6},
        )
        self.assertEqual(document["policy"]["failure"]["retry"]["max_attempts"], 1)
        self.assertIn(
            "scripts/mathformer.py",
            [r["path"] for r in document["provenance"]["sources"]],
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        action = checked_registry(REGISTRY)[ACTION]
        self.assertEqual(action.command[1:], (AUDITOR, "--strict", "--json"))
        self.assertIsNone(action.timeout_seconds)
        self.assertEqual(selected_match(MATCH).route.action_ids, (ACTION,))

    def test_uncapped_scans_and_native_classification(self):
        auditor = load_auditor(ROOT)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # Exercise more than the small runtime fixture and exhaust both
            # native collections; neither loop has a generated scan cap.
            report = populate(root, ROOT, wrapper=False, count=13, scripts=11)
            prepared = auditor.prepare_scan(root / "skills", root)
            state = prepared["state"]
            visited = []
            while state["cursor"] < len(state["pending"]):
                opened = auditor.open_skill(state)
                current = opened["state"]
                self.assertEqual(opened["has_scripts"], bool(current["scripts"]))
                while current["cursor"] < len(current["scripts"]):
                    before = current["cursor"]
                    step = auditor.inspect_script(current)
                    current = step["state"]
                    self.assertEqual(current["cursor"], before + 1)
                    self.assertEqual(
                        step["done"], current["cursor"] == len(current["scripts"])
                    )
                visited.append(current["name"])
                step = auditor.commit_skill(current)
                state = step["state"]
                self.assertEqual(step["done"], state["cursor"] == len(state["pending"]))
            self.assertEqual(auditor.aggregate_scan(state), report)
            self.assertEqual(
                visited,
                ["agent-only", "fallback", "hook-only"]
                + [f"skill-{i:02}" for i in range(13)],
            )
            self.assertEqual(report["skill_count"], 16)
            self.assertEqual(report["script_count"], 143)
            self.assertEqual(report["missing_skill_count"], 13)
            self.assertFalse(report["ok"])
            self.assertEqual(report["native_logged_script_count"], 78)
            self.assertEqual(report["wrapper_logged_script_count"], 0)
            self.assertEqual(
                report["logging_class_counts"],
                {"agent-logged": 2, "workflow-only": 1, "missing": 13},
            )
            self.assertTrue(report["scripts"][0]["registered_runtime"])
            # Script presence dominates native markers when wrapper is absent.
            self.assertTrue(
                all(
                    s["logging_class"] == "missing"
                    for s in report["skills"]
                    if s["script_count"]
                )
            )
            process = subprocess.run(
                [sys.executable, str(root / AUDITOR), "--strict", "--json"],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(process.returncode, 3)
            self.assertEqual(json.loads(process.stdout), report)
            self.assertEqual(process.stderr, "")
            wrapper = root / WRAPPER
            wrapper.parent.mkdir(parents=True, exist_ok=True)
            wrapper.write_text("# presence only\n")
            report = auditor.audit(root / "skills", root)
            self.assertTrue(report["ok"])
            self.assertEqual(report["wrapper_logged_script_count"], 65)
            self.assertEqual(report["logging_class_counts"]["script-logged"], 13)
            # Main's strict-native option also retains source JSON and exit 3.
            process = subprocess.run(
                [
                    sys.executable,
                    str(root / AUDITOR),
                    "--strict",
                    "--require-native-script-logging",
                    "--json",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(process.returncode, 3)
            expected = dict(report, ok=False)
            self.assertEqual(json.loads(process.stdout), expected)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "skills").mkdir()
            (root / "skills/SKILL_HOOKS.yaml").write_text("hooks:\n")
            prepared = auditor.prepare_scan(root / "skills", root)
            self.assertFalse(prepared["has_skills"])
            self.assertEqual(auditor.audit(root / "skills", root)["skill_count"], 0)

    def test_original_equivalence_and_external_compiler_failure_boundary(self):
        oracle, scope = original()
        match = selected_match(MATCH)
        native = checked_registry(REGISTRY)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for ready in [False, True]:
                if ready:
                    populate(root, ROOT)
                for dry in [False, True]:
                    for keep in [False, True]:
                        context = hub.RunContext(dry_run=dry, keep_going=keep)
                        expected = oracle.run_intent_match(
                            match, native, context, repository_root=root
                        )
                        actual = hub.run_intent_match(
                            match, native, context, repository_root=root
                        )
                        self.assertEqual(actual, expected)
                        self.assertEqual(len(actual["children"]), 1)
                        self.assertEqual(actual["ok"], ready)
            # These actions are test-only external compiler declarations;
            # selected production registration is never replaced or mocked.
            for mode in ["success", "reject", "write", "launch_error", "timeout"]:
                item = replace(
                    native[ACTION],
                    command=("fixture-reasoning-compiler", mode),
                    required_paths=(),
                    timeout_seconds=3 if mode == "timeout" else None,
                )
                calls = install(hub, root)
                try:
                    if mode == "launch_error":
                        with self.assertRaisesRegex(
                            OSError, "fixture compiler launch failed"
                        ):
                            hub.run_leaf_action(
                                item, hub.RunContext(), (), repository_root=root
                            )
                        continue
                    child = hub.run_leaf_action(
                        item, hub.RunContext(), (), repository_root=root
                    )
                    self.assertEqual(child["ok"], mode == "success")
                    self.assertEqual(
                        child["status"],
                        {"write": "undeclared_writes", "timeout": "timeout"}.get(
                            mode, "completed"
                        ),
                    )
                    self.assertEqual(
                        calls,
                        [
                            {
                                "argv": ["fixture-reasoning-compiler", mode],
                                "timeout": item.timeout_seconds,
                            }
                        ],
                    )
                    if mode == "success":
                        self.assertFalse(json.loads(child["stdout"])["ok"])
                        self.assertEqual(child["returncode"], 0)
                    if mode == "reject":
                        self.assertEqual(child["returncode"], 7)
                    if mode == "write":
                        self.assertEqual(
                            child["write_audit"]["unexpected_paths"], ["undeclared.txt"]
                        )
                    if mode == "timeout":
                        self.assertEqual(child["stdout"], "partial")
                        self.assertIsNone(child["returncode"])
                finally:
                    hub.subprocess = scope["subprocess"]
                    (root / "undeclared.txt").unlink(missing_ok=True)

    def test_registered_tools_real_lunar_prism_compile_and_execute(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(CONTRACT.read_text())
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        async with manager.open(
            "coverage-route",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {"PYTHONPATH": os.pathsep.join(SITES), "PYTHONDONTWRITEBYTECODE": "1"},
        ) as remote:
            tools = [
                tool.model_dump(by_alias=True, exclude_none=True)
                for tool in await remote.tools()
            ]

            def compile(doc):
                assets = snapshot(doc)
                compiled = compile_workflow(
                    "mcp:coverage-route",
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
            broken["operations"]["execute_audit"]["execution"]["binding"][
                "target"
            ] = "missing_coverage_tool"
            rejected = compile_workflow(
                "mcp:coverage-route",
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
                    "context": vars(hub.RunContext()),
                    "match": MATCH,
                    "registry": REGISTRY,
                    "repository_root": str(root),
                }
                expected_report = None
                for ready in [False, True]:
                    if ready:
                        expected_report = populate(root, ROOT)
                    for dry in [False, True]:
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
                            operation = (
                                "execute_audit"
                                if ready and not dry
                                else "return_boundary"
                            )
                            operations = [
                                "initialize",
                                "select_action",
                                "prepare_action",
                                operation,
                                "advance",
                                "finish",
                            ]
                            self.assertEqual(
                                [c["operation"] for c in result["calls"]], operations
                            )
                            self.assertEqual(
                                [c["tool"] for c in result["calls"]],
                                [
                                    "mathformer_coverage_route_" + op
                                    for op in operations
                                ],
                            )
                            self.assertEqual(len(expected["children"]), 1)
                            self.assertEqual(expected["ok"], ready)
                            self.assertEqual(expected["route"]["score"], MATCH["score"])
                            self.assertEqual(
                                expected["route"]["matched_terms"],
                                MATCH["matched_terms"],
                            )
                            child = expected["children"][0]
                            if ready and not dry:
                                self.assertEqual(
                                    json.loads(child["stdout"]), expected_report
                                )
                                self.assertEqual(child["returncode"], 0)
                                self.assertEqual(child["stderr"], "")
                                self.assertTrue(child["write_audit"]["ok"])
                            self.assertTrue(result["runtime"]["effect_records"])
                            self.assertTrue(result["runtime"]["provenance"])
                            self.assertTrue(result["replay_artifacts"])
                            self.assertFalse((root / "artifacts").exists())

                # Source exceptions in the real subprocess propagate as native
                # nonzero child data, then finish preserves sticky failure.
                (root / AUDITOR).unlink()
                for keep in [False, True]:
                    inputs = deepcopy(base)
                    inputs["context"]["keep_going"] = keep
                    result = await run(inputs)
                    self.assertEqual(result["status"], "accepted", result)
                    output = result["outputs"]["result"]
                    self.assertFalse(output["ok"])
                    self.assertEqual(output["status"], "intent_run_failed")
                    self.assertEqual(output["children"][0]["returncode"], 2)
                    self.assertTrue(output["children"][0]["stderr"])
                    self.assertEqual(len(result["calls"]), 6)
                populate(root, ROOT)

                # Registered prepare/execute retain before/after snapshots over
                # JSON transport. A changed source file fails the native audit.
                prepared = await remote.call(
                    "mathformer_coverage_route_prepare_action",
                    {
                        "action_id": ACTION,
                        "context": base["context"],
                        "registry": REGISTRY,
                        "repository_root": str(root),
                    },
                )
                self.assertTrue(prepared["boundary"]["execute"])
                self.assertTrue(prepared["boundary"]["snapshot"])
                (root / "unexpected.txt").write_text("changed after prepare\n")
                child = await remote.call(
                    "mathformer_coverage_route_execute_audit",
                    {
                        **prepared,
                        "context": base["context"],
                        "registry": REGISTRY,
                        "repository_root": str(root),
                    },
                )
                self.assertFalse(child["child"]["ok"])
                self.assertEqual(child["child"]["status"], "undeclared_writes")
                self.assertEqual(
                    child["child"]["write_audit"]["unexpected_paths"],
                    ["unexpected.txt"],
                )
                (root / "unexpected.txt").unlink()

                inputs = deepcopy(base)
                inputs["registry"] = {}
                result = await run(inputs)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(
                    [c["operation"] for c in result["calls"]],
                    [
                        "initialize",
                        "select_action",
                        "prepare_action",
                        "return_boundary",
                        "advance",
                        "finish",
                    ],
                )
                # Admission data is preserved before native metadata lookup fails.
                boundary = await remote.call(
                    "mathformer_coverage_route_prepare_action",
                    {
                        "action_id": ACTION,
                        "context": base["context"],
                        "registry": {},
                        "repository_root": str(root),
                    },
                )
                self.assertEqual(
                    boundary,
                    {
                        "boundary": {
                            "execute": False,
                            "payload": {
                                "ok": False,
                                "status": "unknown_action",
                                "action_id": ACTION,
                            },
                            "snapshot": {},
                        }
                    },
                )

                for forged in ["registry", "match", "cursor"]:
                    inputs = deepcopy(base)
                    changed = None
                    if forged == "registry":
                        inputs["registry"][ACTION]["command"] = ["forged-command"]
                    elif forged == "match":
                        inputs["match"]["route"]["title"] = "forged title"
                    else:
                        changed = deepcopy(document)
                        changed["flow"]["steps"][1]["body"]["steps"][0]["arguments"][
                            "state"
                        ] = {"literal": {"ok": True, "children": [{"ok": True}]}}
                    result = await run(inputs, changed)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(
                        result["calls"][-1]["operation"],
                        "prepare_action" if forged == "registry" else "select_action",
                    )

                for limit in [1, 3, 5]:
                    changed = deepcopy(document)
                    changed["policy"]["limits"]["max_operation_calls"] = limit
                    inputs = deepcopy(base)
                    inputs["context"]["dry_run"] = True
                    result = await run(inputs, changed)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(
                        sum(
                            bool(c.get("transport_call_performed"))
                            for c in result["calls"]
                        ),
                        limit,
                    )
                changed = deepcopy(document)
                changed["flow"]["steps"][1]["until"] = {"literal": False}
                inputs = deepcopy(base)
                inputs["context"]["dry_run"] = True
                result = await run(inputs, changed)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(result["calls"][-1]["operation"], "advance")
                # Default mount is safe to exercise only through dry-run.
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
