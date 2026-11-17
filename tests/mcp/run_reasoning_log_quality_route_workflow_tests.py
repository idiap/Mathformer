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
from reasoning_log_quality_route_tools import (
    ACTION,
    ROUTE,
    selected_match,
    checked_registry,
    check_state,
    register_reasoning_log_quality_route_tools,
)
from reasoning_log_quality_tree import AUDITOR, FIXTURES, populate, auditor, events
from reasoning_route_compiler import install
from mcp.server.fastmcp import FastMCP
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_control_reasoning_log_quality_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
MATCH = {
    "route": {"route_id": ROUTE, "action_ids": [ACTION]},
    "score": 23,
    "matched_terms": ["reasoning", "log", "quality"],
}
REGISTRY = {ACTION: hub.action_to_dict(hub.build_registry()[ACTION])}
ORDER = ["initialize", "select", "run_action", "advance", "finish"]


def original():
    scope = dict(vars(hub))
    exec(
        (
            ROOT / "tests/mcp/fixtures/reasoning_log_quality_route_original.py.txt"
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


class QualityRouteTests(unittest.TestCase):
    maxDiff = None

    def test_generator_identity_policy_and_provenance(self):
        spec = importlib.util.spec_from_file_location(
            "quality_route_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        document = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(module.reasoning_log_quality_route_descriptor(), document)
        self.assertEqual(document["id"], "route_control_reasoning_log_quality_workflow")
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 5},
        )
        self.assertEqual(document["policy"]["failure"]["retry"]["max_attempts"], 1)
        self.assertEqual(document["policy"]["effects"]["network"], [])
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
        self.assertEqual(item.command, ("{python}", AUDITOR, "--self-test", "--json"))
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
                        self.assertEqual(actual, expected)
                        self.assertEqual(len(actual["children"]), 1)
                        self.assertEqual(actual["ok"], ready and dry)
                        if ready and not dry:
                            self.assertEqual(
                                actual["children"][0]["status"], "undeclared_writes"
                            )
                            self.assertEqual(actual["children"][0]["returncode"], 0)
                            self.assertTrue(
                                json.loads(actual["children"][0]["stdout"])["ok"]
                            )
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
        state, _ = hub.advance_intent_state(
            {"ok": False, "children": [{"ok": False}]},
            {"ok": True},
            hub.RunContext(keep_going=True),
            2,
        )
        self.assertFalse(
            state["ok"]
        )  # failure remains sticky in shared native accumulator

    def test_source_auditor_full_accumulation_readiness_and_advisory_bounds(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            populate(root, ROOT)
            source = auditor(root)
            hooks = root / "skills/SKILL_HOOKS.yaml"
            good, bad = root / "good.jsonl", root / "bad.jsonl"
            good.write_text("".join(json.dumps(e) + "\n" for e in events(257)))
            bad.write_text(
                json.dumps(
                    {
                        "event_index": 1,
                        "step": "skill_application_complete",
                        "payload": {},
                    }
                )
                + "\n"
            )
            report = source.audit_logs([good, bad], hooks_file=hooks)
            self.assertEqual(report["event_count"], 258)
            self.assertEqual([log["event_count"] for log in report["logs"]], [257, 1])
            self.assertFalse(report["ok"])
            self.assertFalse(report["consumer_readiness"]["ready"])
            self.assertIn(
                "missing_skill_application", [f["code"] for f in report["findings"]]
            )
            report = source.audit_logs([good], hooks_file=hooks)
            self.assertTrue(report["ok"])
            self.assertTrue(report["consumer_readiness"]["ready"])
            for dimension in source.QUALITY_DIMENSIONS:
                self.assertEqual(report["quality_scores"][dimension], 1)
            self.assertFalse(
                source.audit_logs([], hooks_file=hooks)["consumer_readiness"]["ready"]
            )
            rows = events()
            app = rows[0]["payload"]["skill_application"]
            app.update(intent="i" * 181, human_summary="s" * 321)
            app["inputs"] = {"long": "x" * 8193}
            good.write_text("".join(json.dumps(e) + "\n" for e in rows))
            report = source.audit_logs([good], hooks_file=hooks)
            self.assertTrue(report["ok"])  # advisory findings are not blocking
            self.assertFalse(report["consumer_readiness"]["ready"])
            self.assertTrue(
                {"intent_too_long", "human_summary_too_long", "payload_too_large"}
                <= {f["code"] for f in report["findings"]}
            )
            self.assertEqual(report["quality_scores"]["concise"], 0.5)
            # Readiness threshold is inclusive at 0.95 and requires events.
            for count, ready in [(20, True), (19, False)]:
                rows = events(count)
                rows[0]["payload"]["skill_application"]["intent"] = "i" * 181
                good.write_text("".join(json.dumps(e) + "\n" for e in rows))
                report = source.audit_logs([good], hooks_file=hooks)
                self.assertTrue(report["ok"])
                self.assertEqual(report["consumer_readiness"]["ready"], ready)
                self.assertEqual(
                    report["quality_scores"]["concise"], (count - 1) / count
                )
            # Exercise the real self-test's negative-fixture verification gate.
            parsed = source.parse_and_guard(
                ["--self-test", "--json"], {"fixture_directory": str(root / FIXTURES)}
            )
            selection = source.prepare_fixtures(parsed["request"])["selection"]
            report = source.audit_selected(parsed["request"], selection)["report"]
            self.assertTrue(
                source.verify_bad(parsed["request"], selection, deepcopy(report))[
                    "report"
                ]["ok"]
            )
            (root / FIXTURES / "bad.jsonl").write_bytes(
                (root / FIXTURES / "good.jsonl").read_bytes()
            )
            failed = source.verify_bad(parsed["request"], selection, report)["report"]
            self.assertFalse(failed["ok"])
            self.assertFalse(failed["self_test"]["bad_has_high_findings"])
            self.assertEqual(
                source.emit(parsed["request"], failed)["result"]["exit_code"], 3
            )

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

    def test_registered_service_write_policy(self):
        async def scenario():
            server = FastMCP("quality-restrictions")
            permissions = {"allowed": False, "path": True}

            def authorize():
                if not permissions["allowed"]:
                    raise PermissionError("service is read-only")

            register_reasoning_log_quality_route_tools(
                server, authorize, lambda path: permissions["path"]
            )
            with tempfile.TemporaryDirectory() as directory:
                arguments = {
                    "action_id": ACTION,
                    "registry": REGISTRY,
                    "repository_root": directory,
                    "context": vars(hub.RunContext()),
                }
                for allowed, path, message in [
                    (False, True, "read-only"),
                    (True, False, "service roots"),
                ]:
                    permissions.update(allowed=allowed, path=path)
                    with self.assertRaisesRegex(Exception, message):
                        await server.call_tool(
                            "mathformer_quality_route_run_action", arguments
                        )
                arguments["registry"] = {}
                output = await server.call_tool(
                    "mathformer_quality_route_run_action", arguments
                )
                self.assertIn("unknown_action", str(output))

        asyncio.run(scenario())

    def test_registered_mcp_and_real_lunar_prism_runtime(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(CONTRACT.read_text())
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        async with manager.open(
            "quality-route",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {"PYTHONPATH": os.pathsep.join(SITES), "PYTHONDONTWRITEBYTECODE": "1"},
        ) as remote:
            tools = [
                t.model_dump(by_alias=True, exclude_none=True)
                for t in await remote.tools()
            ]

            def compile(doc):
                assets = snapshot(doc)
                compiled = compile_workflow(
                    "mcp:quality-route",
                    workflow_documents([DESCRIPTOR], assets)[0],
                    tools,
                )
                self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                self.assertTrue(compiled["prism_source"])
                self.assertTrue(compiled["runtime_source"])
                self.assertEqual(set(compiled["bindings"]), set(doc["operations"]))
                return compiled, assets

            compiled, assets = compile(document)
            missing = [
                t for t in tools if t["name"] != "mathformer_quality_route_run_action"
            ]
            rejected = compile_workflow(
                "mcp:quality-route",
                workflow_documents([DESCRIPTOR], assets)[0],
                missing,
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
                            self.assertEqual(result["outputs"], {"result": expected})
                            self.assertEqual(
                                [c["operation"] for c in result["calls"]], ORDER
                            )
                            self.assertEqual(
                                [c["tool"] for c in result["calls"]],
                                ["mathformer_quality_route_" + op for op in ORDER],
                            )
                            self.assertEqual(len(expected["children"]), 1)
                            self.assertEqual(expected["ok"], ready and dry)
                            self.assertEqual(expected["route"]["score"], MATCH["score"])
                            self.assertEqual(
                                expected["route"]["matched_terms"],
                                MATCH["matched_terms"],
                            )
                            child = expected["children"][0]
                            if ready and not dry:
                                report = json.loads(child["stdout"])
                                self.assertTrue(report["ok"])
                                self.assertEqual(report["event_count"], 2)
                                self.assertTrue(report["self_test"]["good_ok"])
                                self.assertTrue(
                                    report["self_test"]["bad_has_high_findings"]
                                )
                                self.assertIn(
                                    "secret_looking_value",
                                    report["self_test"]["bad_finding_codes"],
                                )
                                self.assertTrue(report["consumer_readiness"]["ready"])
                                self.assertEqual(child["returncode"], 0)
                                self.assertEqual(
                                    child["argv"],
                                    [sys.executable, AUDITOR, "--self-test", "--json"],
                                )
                                self.assertEqual(child["status"], "undeclared_writes")
                                self.assertEqual(
                                    child["write_audit"]["unexpected_paths"],
                                    [
                                        str(FIXTURES / "bad.jsonl"),
                                        str(FIXTURES / "good.jsonl"),
                                    ],
                                )
                                self.assertTrue(
                                    (root / FIXTURES / "bad.jsonl").is_file()
                                )
                                self.assertEqual(
                                    len(
                                        (root / FIXTURES / "good.jsonl")
                                        .read_text()
                                        .splitlines()
                                    ),
                                    2,
                                )
                            self.assertTrue(result["runtime"]["effect_records"])
                            self.assertTrue(result["runtime"]["provenance"])
                            self.assertTrue(result["replay_artifacts"])
                # Audit rejection preserves JSON diagnostics and process exit 3.
                hooks = root / "skills/SKILL_HOOKS.yaml"
                hooks.write_text("hooks:\n  - id: different.hook\n")
                result = await run(base)
                self.assertEqual(result["status"], "accepted", result)
                child = result["outputs"]["result"]["children"][0]
                self.assertEqual(child["returncode"], 3)
                self.assertFalse(result["outputs"]["result"]["ok"])
                report = json.loads(child["stdout"])
                self.assertFalse(report["self_test"]["good_ok"])
                self.assertTrue(report["self_test"]["bad_has_high_findings"])
                self.assertIn(
                    "unknown_hook_id", {f["code"] for f in report["findings"]}
                )
                self.assertEqual([c["operation"] for c in result["calls"]], ORDER)
                populate(root, ROOT)
                # Native parser/IO failure is captured exactly once as child data.
                bad = root / FIXTURES / "bad.jsonl"
                bad.unlink()
                bad.mkdir()
                for keep in [False, True]:
                    inputs = deepcopy(base)
                    inputs["context"]["keep_going"] = keep
                    result = await run(inputs)
                    self.assertEqual(result["status"], "accepted", result)
                    output = result["outputs"]["result"]
                    self.assertFalse(output["ok"])
                    self.assertEqual(output["status"], "intent_run_failed")
                    self.assertNotEqual(output["children"][0]["returncode"], 0)
                    self.assertIn("IsADirectoryError", output["children"][0]["stderr"])
                    self.assertEqual([c["operation"] for c in result["calls"]], ORDER)
                bad.rmdir()
                for forged in ["registry", "match", "cursor", "missing_registry"]:
                    inputs, changed = deepcopy(base), None
                    inputs["context"]["dry_run"] = True
                    if forged == "registry":
                        inputs["registry"][ACTION]["command"] = ["forged-command"]
                    elif forged == "match":
                        inputs["match"]["route"]["title"] = "forged title"
                    elif forged == "missing_registry":
                        inputs["registry"] = {}
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
                    "mathformer_quality_route_run_action",
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
                            bool(c.get("transport_call_performed"))
                            for c in result["calls"]
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
        self.assertFalse(manager.active)


if __name__ == "__main__":
    program = unittest.main(verbosity=2, exit=False)
    result = program.result
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
