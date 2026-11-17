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
from reasoning_log_summary_route_tools import (
    ACTION,
    ROUTE,
    selected_match,
    checked_registry,
    check_state,
    register_reasoning_log_summary_route_tools,
)
from reasoning_log_summary_tree import (
    SUMMARIZER,
    LOGS,
    FIXTURES,
    populate,
    summarizer,
    events,
    write_log,
)
from reasoning_route_compiler import install
from mcp.server.fastmcp import FastMCP
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_control_reasoning_log_summary_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
MATCH = {
    "route_id": ROUTE,
    "score": 23,
    "matched_terms": ["reasoning", "log", "summary"],
}
REGISTRY = {ACTION: hub.action_to_dict(hub.build_registry()[ACTION])}
ORDER = ["initialize", "select", "execute_action", "advance", "finish"]


def original():
    scope = dict(vars(hub))
    exec(
        (
            ROOT / "tests/mcp/fixtures/reasoning_log_summary_route_original.py.txt"
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


class SummaryRouteTests(unittest.TestCase):
    maxDiff = None

    def test_generator_identity_policy_and_provenance(self):
        spec = importlib.util.spec_from_file_location(
            "summary_route_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        document = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(module.reasoning_log_summary_route_descriptor(), document)
        self.assertEqual(document["id"], "route_control_reasoning_log_summary_workflow")
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
        self.assertEqual(item.command, ("{python}", SUMMARIZER, "--json"))
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

    def test_native_entrypoint_and_accumulator(self):
        oracle = original()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for ready in [False, True]:
                if ready:
                    populate(root, ROOT)
                    write_log(root)
                for dry in [False, True]:
                    for keep in [False, True]:
                        context = hub.RunContext(dry_run=dry, keep_going=keep)
                        expected = oracle.run_intent_match(
                            selected_match(MATCH),
                            checked_registry(REGISTRY),
                            context,
                            repository_root=root,
                        )
                        actual = hub.run_intent_match(
                            selected_match(MATCH),
                            checked_registry(REGISTRY),
                            context,
                            repository_root=root,
                        )
                        self.assertEqual(actual, expected)
                        self.assertEqual(len(actual["children"]), 1)
                        self.assertEqual(actual["ok"], ready)
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

    def test_real_leaf_traversal_defaults_validation_quality_and_output(self):
        from contextlib import redirect_stdout
        from io import StringIO

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            populate(root, ROOT)
            leaf = summarizer(root)
            self.assertEqual(leaf.default_log_file(), root / LOGS[0])
            # Last existing candidate wins only when earlier candidates are absent.
            for index in [2, 1, 0]:
                write_log(root, index=index)
                self.assertEqual(leaf.default_log_file(), root / LOGS[index])
            log = root / LOGS[0]
            hooks = root / "skills/SKILL_HOOKS.yaml"
            rows = events(3)
            a, b, c = [row["payload"]["skill_application"] for row in rows]
            a.update(
                status="failed",
                artifacts={"same": "first"},
                decision={"choice": "a"},
                risks=["r"],
                next_action="next",
            )
            b.update(
                artifacts={"same": "second", "new": "value"},
                decision={"choice": "a"},
                risks=["r"],
                next_action="next",
            )
            c.update(
                run_id="other",
                skill="other-skill",
                decision={"choice": "c"},
                risks=[],
                next_action="",
            )
            write_log(root, rows)
            report = leaf.summarize(log, hooks_file=hooks)
            self.assertEqual(report["event_count"], 3)
            self.assertEqual(
                [row["status"] for row in report["timeline"]],
                ["failed", "complete", "complete"],
            )
            self.assertEqual(report["skills"], ["fixture-skill", "other-skill"])
            self.assertEqual(report["hooks"], ["control.reasoning_log_schema"])
            self.assertEqual(report["run_ids"], ["fixture-run", "other"])
            self.assertIsNone(report["run_id"])
            self.assertEqual(report["artifacts"], {"same": "first", "new": "value"})
            self.assertEqual(report["decisions"], [{"choice": "a"}, {"choice": "c"}])
            self.assertEqual(report["risks"], [["r"]])
            self.assertEqual(report["next_actions"], ["next"])
            loaded = leaf.load_events(log)
            state = leaf.initialize_summary(loaded)
            self.assertFalse(state["empty"])
            for index in range(3):
                advanced = leaf.advance_summary(loaded, state["state"])
                self.assertEqual(advanced["state"]["cursor"], index + 1)
                self.assertEqual(advanced["done"], index == 2)
            self.assertEqual(
                leaf.finish_summary(
                    log, loaded, {"ok": True}, {"ok": True}, state["state"]
                )["ok"],
                True,
            )
            for validation, quality in [(False, True), (True, False), (False, False)]:
                self.assertFalse(
                    leaf.finish_summary(
                        log, loaded, {"ok": validation}, {"ok": quality}, state["state"]
                    )["ok"]
                )
            self.assertTrue(leaf.initialize_summary([])["empty"])
            write_log(root, [])
            empty = leaf.summarize(log, hooks_file=hooks)
            self.assertEqual(empty["event_count"], 0)
            self.assertEqual(empty["timeline"], [])
            self.assertEqual(empty["artifacts"], {})
            self.assertIsNone(empty["run_id"])
            # The native leaf traverses >10000 events; the staged MCP loader's
            # cap does not govern this route or its direct leaf.
            write_log(root, events(10001))
            report = leaf.summarize(log, hooks_file=hooks)
            self.assertEqual(report["event_count"], 10001)
            self.assertEqual(len(report["timeline"]), 10001)
            self.assertTrue(report["ok"])
            self.assertEqual(report["run_id"], "fixture-run")
            # Malformed input becomes a timeline event, then both audits fail.
            log.write_text("not-json\n")
            report = leaf.summarize(log, hooks_file=hooks)
            self.assertEqual(report["timeline"][0]["step"], "invalid_json")
            self.assertFalse(report["ok"])
            self.assertFalse(report["validation"]["ok"])
            self.assertFalse(report["quality"]["ok"])
            output = root / "direct/summary.json"
            with redirect_stdout(StringIO()) as printed:
                self.assertEqual(
                    leaf.main(["--log-file", str(log), "--output-file", str(output)]), 3
                )
            self.assertEqual(printed.getvalue(), "")
            self.assertEqual(json.loads(output.read_text()), report)
            write_log(root)
            with redirect_stdout(StringIO()) as printed:
                self.assertEqual(leaf.main(["--json"]), 0)
            self.assertEqual(json.loads(printed.getvalue())["event_count"], 2)
            for path in LOGS:
                (root / path).unlink()
            with redirect_stdout(StringIO()) as printed:
                self.assertEqual(leaf.main(["--json"]), 0)
            self.assertEqual(json.loads(printed.getvalue())["event_count"], 2)
            self.assertTrue((root / FIXTURES / "bad.jsonl").exists())

    def test_service_authority(self):
        async def scenario():
            server = FastMCP("summary-restrictions")
            permissions = {"allowed": False, "path": True}

            def authorize():
                if not permissions["allowed"]:
                    raise PermissionError("service is read-only")

            register_reasoning_log_summary_route_tools(
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
                            "mathformer_summary_route_execute_action", arguments
                        )
                arguments["registry"] = {}
                output = await server.call_tool(
                    "mathformer_summary_route_execute_action", arguments
                )
                self.assertIn("unknown_action", str(output))

        asyncio.run(scenario())

    def test_registered_mcp_lunar_prism_execution(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        manager = SessionManager()
        failure = None
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        async with manager.open(
            "summary-route",
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
            compiled = compile_workflow("mcp:summary-route", documents[0], tools)
            self.assertTrue(compiled["runnable"], compiled["diagnostics"])
            self.assertEqual(compiled["runtime_status"], "ready")
            self.assertTrue(compiled["prism_source"])
            self.assertTrue(compiled["runtime_source"])
            self.assertEqual(set(compiled["bindings"]), set(doc["operations"]))
            return compiled, assets

        compiled, assets = compile(document)
        missing = [
            t for t in tools if t["name"] != "mathformer_summary_route_execute_action"
        ]
        rejected = compile_workflow(
            "mcp:summary-route", workflow_documents([DESCRIPTOR], assets)[0], missing
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
                    write_log(root)
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
                            ["mathformer_summary_route_" + op for op in ORDER],
                        )
                        self.assertEqual(len(expected["children"]), 1)
                        self.assertEqual(expected["ok"], ready)
                        self.assertEqual(expected["route"]["score"], MATCH["score"])
                        self.assertEqual(
                            expected["route"]["matched_terms"], MATCH["matched_terms"]
                        )
                        if ready and not dry:
                            child = expected["children"][0]
                            report = json.loads(child["stdout"])
                            self.assertTrue(report["ok"])
                            self.assertEqual(report["event_count"], 2)
                            self.assertEqual(report["run_id"], "fixture-run")
                            self.assertEqual(child["returncode"], 0)
                            self.assertEqual(
                                child["argv"], [sys.executable, SUMMARIZER, "--json"]
                            )
                            self.assertTrue(child["write_audit"]["ok"])
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["replay_artifacts"])
            # Fallbacks, fixture creation, empty input and quality/schema failure
            # all travel through the real registered action and subprocess.
            for index in [1, 2]:
                for path in LOGS:
                    (root / path).unlink(missing_ok=True)
                write_log(root, index=index)
                result = await run(base)
                report = json.loads(
                    result["outputs"]["result"]["children"][0]["stdout"]
                )
                self.assertTrue(result["outputs"]["result"]["ok"])
                self.assertEqual(report["log_file"], LOGS[index].as_posix())
            for path in LOGS:
                (root / path).unlink(missing_ok=True)
            result = await run(base)
            output = result["outputs"]["result"]
            self.assertFalse(output["ok"])
            child = output["children"][0]
            self.assertEqual(child["returncode"], 0)
            self.assertEqual(child["status"], "undeclared_writes")
            self.assertEqual(
                child["write_audit"]["unexpected_paths"],
                [str(FIXTURES / "bad.jsonl"), str(FIXTURES / "good.jsonl")],
            )
            self.assertTrue(json.loads(child["stdout"])["ok"])
            # The next invocation reads the existing fixtures, without writing.
            result = await run(base)
            self.assertTrue(result["outputs"]["result"]["ok"])
            for rows in [[], events(257)]:
                write_log(root, rows)
                result = await run(base)
                child = result["outputs"]["result"]["children"][0]
                report = json.loads(child["stdout"])
                self.assertEqual(report["event_count"], len(rows))
                self.assertEqual(len(report["timeline"]), len(rows))
                self.assertTrue(child["write_audit"]["ok"])
            (root / LOGS[0]).write_text("invalid-json\n")
            for keep in [False, True]:
                inputs = deepcopy(base)
                inputs["context"]["keep_going"] = keep
                result = await run(inputs)
                output = result["outputs"]["result"]
                self.assertFalse(output["ok"])
                self.assertEqual(output["status"], "intent_run_failed")
                child = output["children"][0]
                self.assertEqual(child["returncode"], 3)
                self.assertFalse(json.loads(child["stdout"])["ok"])
                self.assertEqual([c["operation"] for c in result["calls"]], ORDER)
            # Native unexpected IO errors remain subprocess failure data.
            (root / LOGS[0]).unlink()
            (root / LOGS[0]).mkdir()
            result = await run(base)
            self.assertEqual(result["status"], "accepted", result)
            self.assertFalse(result["outputs"]["result"]["ok"])
            self.assertIn(
                "IsADirectoryError",
                result["outputs"]["result"]["children"][0]["stderr"],
            )
            (root / LOGS[0]).rmdir()
            write_log(root)
            for forged in ["registry", "cursor", "missing_registry"]:
                inputs, changed = deepcopy(base), None
                inputs["context"]["dry_run"] = True
                if forged == "registry":
                    inputs["registry"][ACTION]["command"] = ["forged-command"]
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
                        "execute_action"
                        if forged == "registry"
                        else "finish" if forged == "missing_registry" else "select"
                    ),
                )
            with self.assertRaisesRegex(Exception, "MCP server rejected"):
                await remote.call(
                    "mathformer_summary_route_select",
                    {
                        "state": {"ok": True, "children": []},
                        "match": {**MATCH, "route_id": "forged"},
                    },
                )
            unknown = await remote.call(
                "mathformer_summary_route_execute_action",
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
