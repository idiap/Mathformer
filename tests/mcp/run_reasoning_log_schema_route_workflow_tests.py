#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native source, registered MCP tools and real Lunar/PRISM integration tests.

Audits use copied native sources with synthetic temporary inputs. There are no
model/provider calls, credentials, external compilers or production runs.
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
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib.util
import json
import tempfile
from types import SimpleNamespace
import unittest
import yaml

import mathformer as hub
from reasoning_log_schema_route_tools import (
    ACTION,
    ROUTE,
    selected_match,
    checked_registry,
    check_state,
)
from reasoning_log_schema_tree import SELF_TEST, populate
from reasoning_route_compiler import install
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_control_reasoning_log_schema_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
MATCH = {
    "route": {"route_id": ROUTE, "action_ids": [ACTION]},
    "score": 23,
    "matched_terms": ["reasoning", "log", "schema"],
}
REGISTRY = {ACTION: hub.action_to_dict(hub.build_registry()[ACTION])}
ORDER = ["initialize", "select", "run_action", "advance", "finish"]


def original():
    scope = dict(vars(hub))
    exec(
        (
            ROOT / "tests/mcp/fixtures/reasoning_log_schema_route_original.py.txt"
        ).read_text(),
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


def comparable(result):
    # Native timestamps/UUIDs affect rendered HTML length. Compare every other
    # field, and independently verify real rendering and byte counts below.
    result = deepcopy(result)
    for child in result["children"]:
        if child.get("stdout") and child.get("returncode") == 0:
            report = json.loads(child["stdout"])
            report["render_summary"].pop("html_bytes")
            child["stdout"] = report
    return result


class SchemaRouteTests(unittest.TestCase):
    maxDiff = None

    def test_generator_identity_policy_and_provenance(self):
        spec = importlib.util.spec_from_file_location(
            "schema_route_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        document = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(module.reasoning_log_schema_route_descriptor(), document)
        self.assertEqual(document["id"], "route_control_reasoning_log_schema_workflow")
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 5},
        )
        self.assertEqual(document["policy"]["failure"]["retry"]["max_attempts"], 1)
        self.assertEqual(document["policy"]["effects"]["network"], [])
        self.assertEqual(
            document["policy"]["effects"]["filesystem"]["write"],
            ["temporary_self_test_directory"],
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
        self.assertEqual(item.command, ("{python}", SELF_TEST, "--json"))
        self.assertIsNone(item.timeout_seconds)
        self.assertEqual(item.writes, ())
        self.assertEqual(item.safety, "read_only")
        self.assertEqual(selected_match(MATCH).route.action_ids, (ACTION,))
        self.assertEqual(checked_registry({}), {})
        full = {
            key: hub.action_to_dict(value)
            for key, value in hub.build_registry().items()
        }
        self.assertEqual(checked_registry(full), hub.build_registry())

    def test_native_entrypoint_equivalence_and_single_action_stop(self):
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
                        self.assertEqual(comparable(actual), comparable(expected))
                        self.assertEqual(len(actual["children"]), 1)
                        self.assertEqual(actual["ok"], ready)
                        if ready and not dry:
                            self.assertEqual(
                                actual["children"][0]["status"], "completed"
                            )
                            self.assertEqual(actual["children"][0]["returncode"], 0)
                            self.assertTrue(
                                json.loads(actual["children"][0]["stdout"])["ok"]
                            )
                            self.assertTrue(actual["children"][0]["write_audit"]["ok"])
        for keep in [False, True]:
            for child in [{"ok": True}, {"ok": False}, {}]:
                state = hub.initialize_intent_state()
                advanced, done = hub.advance_intent_state(
                    state, child, hub.RunContext(keep_going=keep), 1
                )
                self.assertEqual(state, {"ok": True, "children": []})
                self.assertEqual(
                    advanced, {"ok": bool(child.get("ok")), "children": [child]}
                )
                self.assertTrue(done)
                check_state(advanced)
                with self.assertRaises(ValueError):
                    check_state(advanced, selecting=True)
        with self.assertRaisesRegex(ValueError, "inconsistent"):
            check_state({"ok": True, "children": [{"ok": False}]})
        state, _ = hub.advance_intent_state(
            {"ok": False, "children": [{"ok": False}]},
            {"ok": True},
            hub.RunContext(keep_going=True),
            2,
        )
        self.assertFalse(state["ok"])

    def test_actual_self_test_steps_thresholds_and_cleanup(self):
        spec = importlib.util.spec_from_file_location(
            "_schema_route_self_test", ROOT / SELF_TEST
        )
        source = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(source)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            populate(root, ROOT)
            with tempfile.TemporaryDirectory() as fixture_dir:
                fixture = source.create_fixture(Path(fixture_dir))
                events = [
                    json.loads(line)
                    for line in Path(fixture["log_file"]).read_text().splitlines()
                ]
                self.assertEqual(len(events), 3)
                self.assertEqual(
                    [event["step"] for event in events],
                    [
                        "skill_application_start",
                        "skill_application_evidence_recorded",
                        "skill_application_complete",
                    ],
                )
                self.assertTrue(
                    all(
                        event["payload"]["skill_application"]["skill_call_id"]
                        == fixture["skill_call_id"]
                        for event in events
                    )
                )
                validation = source.validate_fixture(fixture, root)
                self.assertTrue(validation["ok"])
                rendered = source.render_fixture(fixture, validation)
                self.assertEqual(rendered["summary"]["event_count"], 3)
                self.assertEqual(rendered["summary"]["skill_invocation_count"], 1)
                self.assertEqual(
                    Path(fixture["rendered_file"]).read_text(), rendered["markdown"]
                )
                self.assertEqual(
                    Path(fixture["html_file"]).read_text(), rendered["html"]
                )
                self.assertEqual(
                    len(Path(fixture["html_file"]).read_bytes()),
                    rendered["summary"]["html_bytes"],
                )
                coverage = source.audit_fixture_coverage(root)
                report = source.finish_fixture(validation, rendered, coverage)
                self.assertTrue(report["ok"])
                self.assertTrue(all(report["checks"].values()))
            self.assertFalse(Path(fixture["log_file"]).exists())
            # Configure only the standard library's scratch location. Every
            # source step, including the TemporaryDirectory manager, is real.
            scratch = root / "scratch"
            scratch.mkdir()
            saved_tempdir = tempfile.tempdir
            tempfile.tempdir = str(scratch)
            try:
                for count, hook, wrapper, failed_check in [
                    (101, True, True, None),
                    (100, True, True, "coverage_has_all_skills"),
                    (0, True, True, "coverage_has_all_skills"),
                    (101, False, True, "validation_ok"),
                    (101, True, False, "coverage_ok"),
                ]:
                    populate(root, ROOT, count=count, known_hook=hook, wrapper=wrapper)
                    report = source.run_self_test(root)
                    self.assertEqual(report["ok"], failed_check is None)
                    if failed_check:
                        self.assertFalse(report["checks"][failed_check])
                    self.assertEqual(report["coverage_summary"]["skill_count"], count)
                    self.assertEqual(report["render_summary"]["event_count"], 3)
                    self.assertTrue(report["checks"]["render_has_evidence"])
                    self.assertTrue(report["checks"]["html_render_has_filters"])
                    self.assertEqual(list(scratch.iterdir()), [])
                # Failure during real validation propagates, with scope cleanup.
                (root / "skills/SKILL_HOOKS.yaml").write_bytes(bytes([255]))
                with self.assertRaises(UnicodeDecodeError):
                    source.run_self_test(root)
                self.assertEqual(list(scratch.iterdir()), [])
            finally:
                tempfile.tempdir = saved_tempdir

    def test_external_compiler_capture_timeout_write_audit_and_launch_error(self):
        # This separate test-only compiler action exercises the shared boundary;
        # it never replaces the selected auditor or its production registration.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            saved = hub.subprocess
            for mode in ["success", "reject", "write", "launch_error", "timeout"]:
                item = replace(
                    hub.build_registry()[ACTION],
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
                            )  # native process status wins
                        if mode == "reject":
                            self.assertEqual(child["returncode"], 7)
                        if mode == "write":
                            self.assertEqual(
                                child["write_audit"]["unexpected_paths"],
                                ["undeclared.txt"],
                            )
                        if mode == "timeout":
                            self.assertEqual(child["stdout"], "partial")
                            self.assertEqual(child["stderr"], "deadline")
                            self.assertIsNone(child["returncode"])
                    self.assertEqual(
                        calls,
                        [
                            {
                                "argv": ["fixture-reasoning-compiler", mode],
                                "timeout": item.timeout_seconds,
                            }
                        ],
                    )
                finally:
                    hub.subprocess = saved
                    (root / "undeclared.txt").unlink(missing_ok=True)

    def test_registered_mcp_and_real_lunar_prism_runtime(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        manager = SessionManager()
        failure = None
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        async with manager.open(
            "schema-route",
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
            self.assertEqual(len(documents), 1)
            self.assertTrue(documents[0]["validation"]["valid"], documents[0])
            compiled = compile_workflow("mcp:schema-route", documents[0], tools)
            self.assertTrue(compiled["runnable"], compiled["diagnostics"])
            self.assertEqual(compiled["runtime_status"], "ready")
            self.assertTrue(compiled["prism_source"])
            self.assertTrue(compiled["runtime_source"])
            self.assertEqual(set(compiled["bindings"]), set(doc["operations"]))
            return compiled, assets

        compiled, assets = compile(document)
        missing = [
            t for t in tools if t["name"] != "mathformer_schema_route_run_action"
        ]
        rejected = compile_workflow(
            "mcp:schema-route", workflow_documents([DESCRIPTOR], assets)[0], missing
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
                        result = await run(inputs)
                        expected = original().run_intent_match(
                            selected_match(MATCH),
                            checked_registry(REGISTRY),
                            hub.RunContext(**inputs["context"]),
                            repository_root=root,
                        )
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertEqual(
                            comparable(result["outputs"]["result"]),
                            comparable(expected),
                        )
                        self.assertEqual(
                            [c["operation"] for c in result["calls"]], ORDER
                        )
                        self.assertEqual(
                            [c["tool"] for c in result["calls"]],
                            ["mathformer_schema_route_" + op for op in ORDER],
                        )
                        self.assertEqual(len(expected["children"]), 1)
                        self.assertEqual(expected["ok"], ready)
                        self.assertEqual(expected["route"]["score"], MATCH["score"])
                        self.assertEqual(
                            expected["route"]["matched_terms"], MATCH["matched_terms"]
                        )
                        child = expected["children"][0]
                        if ready and not dry:
                            report = json.loads(child["stdout"])
                            self.assertTrue(report["ok"])
                            self.assertTrue(all(report["checks"].values()))
                            self.assertEqual(report["render_summary"]["event_count"], 3)
                            self.assertEqual(
                                report["render_summary"]["skill_invocation_count"], 1
                            )
                            self.assertEqual(
                                report["coverage_summary"]["skill_count"], 101
                            )
                            self.assertGreater(
                                report["render_summary"]["html_bytes"], 0
                            )
                            self.assertEqual(child["returncode"], 0)
                            self.assertEqual(
                                child["argv"], [sys.executable, SELF_TEST, "--json"]
                            )
                            self.assertEqual(child["status"], "completed")
                            self.assertEqual(
                                child["write_audit"]["unexpected_paths"], []
                            )
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["replay_artifacts"])
                        self.assertFalse((root / "artifacts").exists())
            for count, hook, wrapper, check in [
                (100, True, True, "coverage_has_all_skills"),
                (101, False, True, "validation_ok"),
                (101, True, False, "coverage_ok"),
            ]:
                populate(root, ROOT, count=count, known_hook=hook, wrapper=wrapper)
                for keep in [False, True]:
                    inputs = deepcopy(base)
                    inputs["context"]["keep_going"] = keep
                    result = await run(inputs)
                    self.assertEqual(result["status"], "accepted", result)
                    output = result["outputs"]["result"]
                    child = output["children"][0]
                    self.assertEqual(output["status"], "intent_run_failed")
                    self.assertFalse(output["ok"])
                    self.assertEqual(child["returncode"], 3)
                    self.assertEqual(child["status"], "completed")
                    self.assertTrue(child["write_audit"]["ok"])
                    report = json.loads(child["stdout"])
                    self.assertFalse(report["checks"][check])
                    self.assertEqual(report["render_summary"]["event_count"], 3)
                    self.assertEqual(report["coverage_summary"]["skill_count"], count)
                    self.assertEqual([c["operation"] for c in result["calls"]], ORDER)
            populate(root, ROOT)
            (root / "skills/SKILL_HOOKS.yaml").write_bytes(bytes([255]))
            result = await run(base)
            self.assertEqual(result["status"], "accepted", result)
            child = result["outputs"]["result"]["children"][0]
            self.assertNotEqual(child["returncode"], 0)
            self.assertIn("UnicodeDecodeError", child["stderr"])
            self.assertFalse(result["outputs"]["result"]["ok"])
            self.assertEqual([c["operation"] for c in result["calls"]], ORDER)
            populate(root, ROOT)
            for forged in ["registry", "match", "cursor", "missing_registry"]:
                inputs, changed = deepcopy(base), None
                inputs["context"]["dry_run"] = True
                if forged == "registry":
                    inputs["registry"][ACTION]["command"] = ["forged-command"]
                elif forged == "match":
                    inputs["match"]["route"]["title"] = "forged title"
                elif forged == "missing_registry":
                    inputs["registry"] = {}
                    with self.assertRaises(KeyError):
                        original().run_intent_match(
                            selected_match(MATCH),
                            {},
                            hub.RunContext(dry_run=True),
                            repository_root=root,
                        )
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
                    (
                        "run_action"
                        if forged == "registry"
                        else "finish" if forged == "missing_registry" else "select"
                    ),
                )
            unknown = await remote.call(
                "mathformer_schema_route_run_action",
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
            timed = deepcopy(document)
            timed["policy"]["limits"]["wall_time_seconds"] = 1
            workflow, received = compile(timed)

            async def waiting_authority():
                await asyncio.Event().wait()

            with self.assertRaises(TimeoutError):
                await execute(workflow, received, inputs, remote, waiting_authority)
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


if __name__ == "__main__":
    program = unittest.main(verbosity=2, exit=False)
    result = program.result
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
