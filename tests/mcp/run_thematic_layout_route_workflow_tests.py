#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Real native route, registered MCP tools, Lunar compiler and PRISM runtime.

All layout executions use synthetic temporary trees with an unmodified native
leaf. The only substituted process is a separate test-only external compiler;
no providers, credentials, theorem provers or production workflows are used.
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
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT / "tests/mcp/fixtures"),
]
SITES = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
sys.path.extend(SITES)

import asyncio
from contextlib import redirect_stdout
from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib.util
import io
import json
import tempfile
from types import SimpleNamespace
import unittest
import yaml

import mathformer as hub
import organize_repository_layout as layout
from thematic_layout_route_tools import (
    ACTION,
    ROUTE,
    selected_match,
    checked_registry,
    check_state,
)
from thematic_layout_tree import populate, put
from reasoning_route_compiler import install
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_control_thematic_layout_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
MATCH = {
    "route": {"route_id": ROUTE, "action_ids": [ACTION]},
    "score": 23,
    "matched_terms": ["thematic", "layout"],
}
REGISTRY = {ACTION: hub.action_to_dict(hub.build_registry()[ACTION])}
ORDER = ["initialize", "select", "run", "advance", "finish"]


def original():
    scope = dict(vars(hub))
    exec(
        (ROOT / "tests/mcp/fixtures/thematic_layout_route_original.py.txt").read_text(),
        scope,
    )
    return SimpleNamespace(**scope)


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


class ThematicRouteTests(unittest.TestCase):
    maxDiff = None

    def test_generator_identity_bindings_policy_and_provenance(self):
        spec = importlib.util.spec_from_file_location(
            "thematic_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        document = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(module.thematic_layout_route_descriptor(), document)
        self.assertEqual(document["id"], "route_control_thematic_layout_workflow")
        self.assertEqual(document["aliases"], [ROUTE])
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 5},
        )
        self.assertEqual(
            document["policy"]["failure"],
            {"default": "fail", "retry": {"max_attempts": 1, "retryable_codes": []}},
        )
        self.assertEqual(
            document["policy"]["effects"],
            {
                "filesystem": {
                    "read": ["repository", "native_runtime_inputs"],
                    "write": ["artifacts/workflow_hub/"],
                },
                "network": [],
                "external_write": [],
            },
        )
        self.assertEqual(set(document["operations"]), set(ORDER))
        self.assertTrue(
            any(
                r["path"] == "scripts/mathformer.py"
                and r["selector"] == "run_intent_match"
                for r in document["provenance"]["sources"]
            )
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        item = checked_registry(REGISTRY)[ACTION]
        self.assertEqual(
            item.command,
            ("{python}", "scripts/organize_repository_layout.py", "--json"),
        )
        self.assertIsNone(item.timeout_seconds)
        self.assertEqual(item.writes, ())
        self.assertEqual(item.depends_on, ())
        self.assertEqual(selected_match(MATCH).route.action_ids, (ACTION,))
        self.assertEqual(checked_registry({}), {})

    def test_original_entrypoint_equivalence_and_accumulator(self):
        oracle = original()
        native, match = checked_registry(REGISTRY), selected_match(MATCH)
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
                        if ready and not dry:
                            self.assertTrue(
                                json.loads(actual["children"][0]["stdout"])["ok"]
                            )
                self.assertFalse((root / "artifacts").exists())
        for keep in [False, True]:
            for child in [{"ok": True}, {"ok": False}, {}]:
                state = hub.initialize_intent_state()
                updated, done = hub.advance_intent_state(
                    state, child, hub.RunContext(keep_going=keep), 1
                )
                self.assertEqual(state, {"ok": True, "children": []})
                self.assertEqual(
                    updated, {"ok": bool(child.get("ok", False)), "children": [child]}
                )
                self.assertTrue(done)  # first child reaches the exact native bound
                check_state(updated)
                with self.assertRaises(ValueError):
                    check_state(updated, selecting=True)
            # Generic source helper also preserves sticky failure under keep-going.
            state, done = hub.advance_intent_state(
                hub.initialize_intent_state(),
                {"ok": False},
                hub.RunContext(keep_going=keep),
                2,
            )
            self.assertEqual(done, not keep)
            state, done = hub.advance_intent_state(
                state, {"ok": True}, hub.RunContext(keep_going=keep), 2
            )
            self.assertFalse(state["ok"])
            self.assertTrue(done)
        with self.assertRaisesRegex(ValueError, "inconsistent"):
            check_state({"ok": False, "children": []})

    def test_actual_leaf_classifications_failure_accumulation_and_no_repair(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            populate(root, ROOT)
            self.assertTrue(layout.build_report(root)["ok"])
            alias = next(iter(layout.expected_views(root)))
            canonical = layout.expected_views(root)[alias]
            alias.unlink()
            self.assertEqual(layout.inspect_view(alias, canonical), "missing")
            alias.write_text("occupied")
            self.assertEqual(layout.inspect_view(alias, canonical), "occupied")
            alias.unlink()
            alias.symlink_to("wrong-target")
            self.assertEqual(layout.inspect_view(alias, canonical), "wrong_target")
            put(root, "skills/wrong/lean-misplaced/SKILL.md")
            put(root, "skills/flat/SKILL.md")
            put(root, "scripts/unclassified.py")
            put(root, "tests/unclassified.py")
            put(root, "docs/unclassified.md")
            (root / "docs/architecture").rmdir()
            (root / "backends/lean/Main.lean").unlink()
            (root / "libraries/MathformerLib.lean").unlink()
            put(root, "Main.lean")
            report = layout.build_report(root)
            self.assertFalse(report["ok"])
            self.assertEqual(
                report["invalid_views"][alias.relative_to(root).as_posix()],
                "wrong_target",
            )
            self.assertEqual(
                report["misclassified_skills"], ["skills/wrong/lean-misplaced"]
            )
            self.assertEqual(report["flat_skills"], ["flat"])
            for key, expected in {
                "unclassified_root_scripts": ["unclassified.py"],
                "unclassified_root_tests": ["unclassified.py"],
                "unclassified_root_docs": ["unclassified.md"],
                "missing_doc_themes": ["architecture"],
                "missing_backend_components": ["lean/Main.lean"],
                "missing_library_components": ["MathformerLib.lean"],
                "legacy_component_roots": ["Main.lean"],
                "root_lean_files": ["Main.lean"],
            }.items():
                self.assertEqual(report[key], expected)
            before = hub.snapshot_repository(root)
            stream = io.StringIO()
            with redirect_stdout(stream):
                self.assertEqual(layout.main(["--json"], root), 1)
            self.assertEqual(json.loads(stream.getvalue()), report)
            self.assertEqual(hub.snapshot_repository(root), before)
            self.assertTrue(alias.is_symlink())
            self.assertEqual(
                layout.inspect_view(alias, root / "absent"), "missing_canonical"
            )
            put(root, "skills/unknown/not-classified/SKILL.md")
            with self.assertRaisesRegex(ValueError, "no thematic classification"):
                layout.build_report(root)

    def test_deterministic_external_compiler_boundary(self):
        # A separate test-only compiler action exercises native capture and
        # write audits. It never replaces the selected production leaf.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            saved = hub.subprocess
            try:
                for mode in ["success", "reject", "write", "launch_error", "timeout"]:
                    item = replace(
                        hub.build_registry()[ACTION],
                        command=("fixture-reasoning-compiler", mode),
                        required_paths=(),
                        timeout_seconds=3 if mode == "timeout" else None,
                    )
                    calls = install(hub, root)
                    if mode == "launch_error":
                        with self.assertRaisesRegex(OSError, "compiler launch failed"):
                            hub.run_leaf_action(
                                item, hub.RunContext(), (), repository_root=root
                            )
                    else:
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
                        if mode == "success":
                            self.assertFalse(
                                json.loads(child["stdout"])["ok"]
                            )  # exit code owns success
                        elif mode == "reject":
                            self.assertEqual(child["returncode"], 7)
                        elif mode == "write":
                            self.assertEqual(
                                child["write_audit"]["unexpected_paths"],
                                ["undeclared.txt"],
                            )
                        elif mode == "timeout":
                            self.assertEqual(
                                (child["returncode"], child["stdout"], child["stderr"]),
                                (None, "partial", "deadline"),
                            )
                    self.assertEqual(
                        calls,
                        [{"argv": list(item.command), "timeout": item.timeout_seconds}],
                    )
                    (root / "undeclared.txt").unlink(missing_ok=True)
            finally:
                hub.subprocess = saved

    def test_registered_mcp_real_lunar_compile_execute_and_failure_paths(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        manager = SessionManager()
        failure = None
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        async with manager.open(
            "thematic-route",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {"PYTHONPATH": os.pathsep.join(SITES), "PYTHONDONTWRITEBYTECODE": "1"},
        ) as remote:
            try:
                await self.connected_scenario(remote)
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure is not None:
            raise failure

    async def connected_scenario(self, remote):
        document = yaml.safe_load(CONTRACT.read_text())
        tools = [
            t.model_dump(by_alias=True, exclude_none=True) for t in await remote.tools()
        ]

        def compile(doc):
            assets = snapshot(doc)
            documents = workflow_documents([DESCRIPTOR], assets)
            self.assertTrue(documents[0]["validation"]["valid"], documents[0])
            compiled = compile_workflow("mcp:thematic-route", documents[0], tools)
            self.assertTrue(compiled["runnable"], compiled["diagnostics"])
            self.assertEqual(compiled["runtime_status"], "ready")
            self.assertTrue(compiled["prism_source"])
            self.assertTrue(compiled["runtime_source"])
            self.assertEqual(set(compiled["bindings"]), set(ORDER))
            return compiled, assets

        compiled, assets = compile(document)
        missing = [t for t in tools if t["name"] != "mathformer_thematic_route_run"]
        rejected = compile_workflow(
            "mcp:thematic-route", workflow_documents([DESCRIPTOR], assets)[0], missing
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
            for ready in [False, True]:
                if ready:
                    populate(root, ROOT)
                for dry in [False, True]:
                    for keep in [False, True]:
                        inputs = deepcopy(base)
                        inputs["context"].update(dry_run=dry, keep_going=keep)
                        before = hub.snapshot_repository(root)
                        result = await run(inputs)
                        expected = original().run_intent_match(
                            selected_match(MATCH),
                            checked_registry(REGISTRY),
                            hub.RunContext(**inputs["context"]),
                            repository_root=root,
                        )
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertEqual(result["outputs"], {"result": expected})
                        self.assertEqual(
                            [c["operation"] for c in result["calls"]], ORDER
                        )
                        self.assertEqual(
                            [c["tool"] for c in result["calls"]],
                            ["mathformer_thematic_route_" + op for op in ORDER],
                        )
                        self.assertEqual(len(expected["children"]), 1)
                        self.assertEqual(expected["ok"], ready)
                        self.assertEqual(expected["route"]["score"], MATCH["score"])
                        self.assertEqual(
                            expected["route"]["matched_terms"], MATCH["matched_terms"]
                        )
                        child = expected["children"][0]
                        if ready and not dry:
                            self.assertEqual(child["returncode"], 0)
                            self.assertEqual(
                                child["argv"],
                                [
                                    sys.executable,
                                    "scripts/organize_repository_layout.py",
                                    "--json",
                                ],
                            )
                            self.assertEqual(
                                json.loads(child["stdout"]), layout.build_report(root)
                            )
                            self.assertEqual(
                                child["write_audit"]["unexpected_paths"], []
                            )
                        elif ready:
                            self.assertEqual(child["status"], "dry_run")
                            self.assertNotIn("returncode", child)
                        else:
                            self.assertTrue(child["preflight_errors"])
                            self.assertNotIn("returncode", child)
                        self.assertEqual(hub.snapshot_repository(root), before)
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["replay_artifacts"])
            alias = next(iter(layout.expected_views(root)))
            alias.unlink()
            for keep in [False, True]:
                inputs = deepcopy(base)
                inputs["context"]["keep_going"] = keep
                result = await run(inputs)
                self.assertEqual(result["status"], "accepted", result)
                output = result["outputs"]["result"]
                self.assertEqual(output["status"], "intent_run_failed")
                self.assertFalse(output["ok"])
                self.assertEqual(len(output["children"]), 1)
                child = output["children"][0]
                self.assertEqual(child["returncode"], 1)
                self.assertEqual(
                    json.loads(child["stdout"])["invalid_views"][
                        alias.relative_to(root).as_posix()
                    ],
                    "missing",
                )
                self.assertTrue(child["write_audit"]["ok"])
                self.assertFalse(alias.exists())  # route never supplies --apply
                self.assertEqual([c["operation"] for c in result["calls"]], ORDER)
            put(root, "skills/unknown/not-classified/SKILL.md")
            result = await run(base)
            child = result["outputs"]["result"]["children"][0]
            self.assertNotEqual(child["returncode"], 0)
            self.assertIn(
                "ValueError: skill has no thematic classification", child["stderr"]
            )
            self.assertFalse(result["outputs"]["result"]["ok"])
            self.assertEqual([c["operation"] for c in result["calls"]], ORDER)
            for forged in ["registry", "match", "cursor"]:
                inputs, changed = deepcopy(base), None
                inputs["context"]["dry_run"] = True
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
                    "run" if forged == "registry" else "select",
                )
            unknown = await remote.call(
                "mathformer_thematic_route_run",
                {
                    "action_id": ACTION,
                    "context": vars(hub.RunContext(dry_run=True)),
                    "registry": {},
                    "repository_root": str(root),
                },
            )
            self.assertEqual(
                unknown,
                {
                    "child": {
                        "ok": False,
                        "status": "unknown_action",
                        "action_id": ACTION,
                    }
                },
            )
            inputs = deepcopy(base)
            inputs["context"]["dry_run"] = True
            for limit in [1, 3, 4]:
                changed = deepcopy(document)
                changed["policy"]["limits"]["max_operation_calls"] = limit
                result = await run(inputs, changed)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in result["calls"]
                    ),
                    limit,
                )
            changed = deepcopy(document)
            changed["flow"]["steps"][1]["until"] = {"literal": False}
            result = await run(inputs, changed)
            self.assertEqual(result["status"], "failed", result)
            self.assertIsNone(result["outputs"])
            self.assertEqual([c["operation"] for c in result["calls"]], ORDER[:-1])
            # Null and omitted optional mounts retain the source default. Only
            # dry-run is permitted to touch the actual project in this suite.
            for omitted in [False, True]:
                inputs["repository_root"] = None
                if omitted:
                    inputs.pop("repository_root")
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


if __name__ == "__main__":
    program = unittest.main(verbosity=2, exit=False)
    result = program.result
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
