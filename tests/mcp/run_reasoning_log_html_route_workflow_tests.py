#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Exercise native steps, registered MCP bindings and real Lunar/PRISM runtime.

All renderer execution uses copied native sources and synthetic temporary logs.
No production workflow, provider, credential, theorem prover or promotion runs.
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
from types import SimpleNamespace
import tempfile
import unittest
import yaml

import mathformer as hub
from reasoning_log_html_route_tools import (
    ACTION,
    ROUTE,
    checked_registry,
    selected_match,
    check_state,
    register_reasoning_log_html_route_tools,
)
from reasoning_log_html_tree import LOG, RENDERER, populate, write_log
from reasoning_route_compiler import install
from mcp.server.fastmcp import FastMCP
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_control_reasoning_log_html_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
MATCH = {
    "route": {"route_id": ROUTE, "action_ids": [ACTION]},
    "score": 23,
    "matched_terms": ["reasoning", "log", "html"],
}
REGISTRY = {ACTION: hub.action_to_dict(hub.build_registry()[ACTION])}
ORDER = ["initialize", "select_action", "execute_action", "advance", "finish"]


def original():
    scope = dict(vars(hub))
    exec(
        (
            ROOT / "tests/mcp/fixtures/reasoning_log_html_route_original.py.txt"
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


class HtmlRouteTests(unittest.TestCase):
    maxDiff = None

    def test_generator_native_identity_and_source_digests(self):
        spec = importlib.util.spec_from_file_location(
            "html_route_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        document = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(module.reasoning_log_html_route_descriptor(), document)
        self.assertEqual(document["id"], "route_control_reasoning_log_html_workflow")
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
        action = checked_registry(REGISTRY)[ACTION]
        self.assertEqual(action.command, ("{python}", RENDERER))
        self.assertIsNone(action.timeout_seconds)
        self.assertEqual(action.writes, ("artifacts/",))
        self.assertEqual(selected_match(MATCH).route.action_ids, (ACTION,))

    def test_frozen_entrypoint_equivalence_and_single_action_stop(self):
        oracle = original()
        native, match = checked_registry(REGISTRY), selected_match(MATCH)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for ready in [False, True]:
                if ready:
                    populate(root, ROOT)
                    write_log(root)
                for dry in [True, False]:
                    for keep in [False, True]:
                        context = hub.RunContext(dry_run=dry, keep_going=keep)
                        output = root / LOG.with_suffix(".html")
                        output.unlink(missing_ok=True)
                        expected = oracle.run_intent_match(
                            match, native, context, repository_root=root
                        )
                        html = output.read_text() if output.exists() else None
                        output.unlink(missing_ok=True)
                        actual = hub.run_intent_match(
                            match, native, context, repository_root=root
                        )
                        self.assertEqual(actual, expected)
                        self.assertEqual(
                            output.read_text() if output.exists() else None, html
                        )
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
                self.assertTrue(done)  # exact route bound, even under keep-going
                check_state(advanced)
                with self.assertRaises(ValueError):
                    check_state(advanced, selecting=True)
                self.assertEqual(
                    hub.finish_intent_state(advanced, match, native)["status"],
                    "intent_run_completed" if child.get("ok") else "intent_run_failed",
                )

    def test_external_compiler_boundary_capture_audit_and_errors(self):
        # Only this separate generic compiler capability is substituted. The
        # actual renderer binding and registry stay native in all route tests.
        previous = hub.subprocess
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
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
                            self.assertFalse(json.loads(child["stdout"])["ok"])
                            self.assertEqual(child["returncode"], 0)
                        elif mode == "reject":
                            self.assertEqual(child["returncode"], 7)
                            self.assertEqual(
                                child["stderr"], "fixture compiler diagnostic"
                            )
                        elif mode == "write":
                            self.assertEqual(
                                child["write_audit"]["unexpected_paths"],
                                ["undeclared.txt"],
                            )
                        else:
                            self.assertEqual(child["stdout"], "partial")
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
                    hub.subprocess = previous
                    (root / "undeclared.txt").unlink(missing_ok=True)

    def test_service_write_restrictions(self):
        async def scenario():
            server = FastMCP("html-policy-test")
            permissions = {"allowed": False, "path": True}

            def authorize():
                if not permissions["allowed"]:
                    raise ValueError("service read-only policy")

            register_reasoning_log_html_route_tools(
                server, authorize, lambda p: permissions["path"]
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
                            "mathformer_html_route_execute_action", arguments
                        )
                # Native admission still returns unknown-action data.
                arguments["registry"] = {}
                result = await server.call_tool(
                    "mathformer_html_route_execute_action", arguments
                )
                self.assertIn("unknown_action", str(result))

        asyncio.run(scenario())

    def test_registered_mcp_and_real_lunar_prism_runtime(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(CONTRACT.read_text())
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        async with manager.open(
            "html-route",
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
                    "mcp:html-route", workflow_documents([DESCRIPTOR], assets)[0], tools
                )
                self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                self.assertTrue(compiled["prism_source"])
                self.assertTrue(compiled["runtime_source"])
                self.assertEqual(set(compiled["bindings"]), set(doc["operations"]))
                return compiled, assets

            compiled, assets = compile(document)
            missing = [
                t for t in tools if t["name"] != "mathformer_html_route_execute_action"
            ]
            rejected = compile_workflow(
                "mcp:html-route", workflow_documents([DESCRIPTOR], assets)[0], missing
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
                            output = root / LOG.with_suffix(".html")
                            output.unlink(missing_ok=True)
                            result = await run(inputs)
                            html = output.read_text() if output.exists() else None
                            output.unlink(missing_ok=True)
                            expected = hub.run_intent_match(
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
                                ["mathformer_html_route_" + op for op in ORDER],
                            )
                            self.assertEqual(len(expected["children"]), 1)
                            self.assertEqual(expected["ok"], ready)
                            self.assertEqual(expected["route"]["score"], MATCH["score"])
                            self.assertEqual(
                                expected["route"]["matched_terms"],
                                MATCH["matched_terms"],
                            )
                            if ready and not dry:
                                self.assertEqual(output.read_text(), html)
                                self.assertIn("Inspect &lt;evidence&gt;", html)
                                self.assertIn("Finished &amp; checked", html)
                                child = expected["children"][0]
                                self.assertEqual(child["returncode"], 0)
                                self.assertEqual(
                                    child["argv"], [sys.executable, RENDERER]
                                )
                                self.assertEqual(child["stdout"], str(output) + "\n")
                                self.assertTrue(child["write_audit"]["ok"])
                            self.assertTrue(result["runtime"]["effect_records"])
                            self.assertTrue(result["runtime"]["provenance"])
                            self.assertTrue(result["replay_artifacts"])
                # Finite traversals have no event-count cap: preserve all input
                # lines, invocation history, escaped HTML and validation findings.
                write_log(root, count=257)
                result = await run(base)
                self.assertTrue(result["outputs"]["result"]["ok"])
                html = (root / LOG.with_suffix(".html")).read_text()
                self.assertEqual(html.count('class="timeline-row'), 257)
                write_log(root, content="\n{}\n[]\ninvalid-json\n")
                for keep in [False, True]:
                    inputs = deepcopy(base)
                    inputs["context"]["keep_going"] = keep
                    result = await run(inputs)
                    self.assertEqual(result["status"], "accepted", result)
                    output = result["outputs"]["result"]
                    self.assertFalse(output["ok"])
                    self.assertEqual(output["status"], "intent_run_failed")
                    self.assertEqual(len(output["children"]), 1)
                    self.assertEqual(output["children"][0]["returncode"], 2)
                    self.assertTrue(output["children"][0]["write_audit"]["ok"])
                    html = (root / LOG.with_suffix(".html")).read_text()
                    self.assertIn("Validation Findings", html)
                    self.assertIn("invalid_json", html)
                # Missing default creates native fixtures in this mount only.
                (root / LOG).unlink()
                result = await run(base)
                self.assertTrue(result["outputs"]["result"]["ok"])
                self.assertEqual(len((root / LOG).read_text().splitlines()), 2)
                self.assertTrue((root / LOG.with_name("bad.jsonl")).exists())
                # An input read error is captured once, never retried, then
                # propagated through sticky route failure with stderr intact.
                (root / LOG).unlink()
                (root / LOG).mkdir()
                result = await run(base)
                self.assertEqual(result["status"], "accepted", result)
                self.assertFalse(result["outputs"]["result"]["ok"])
                child = result["outputs"]["result"]["children"][0]
                self.assertNotEqual(child["returncode"], 0)
                self.assertIn("IsADirectoryError", child["stderr"])
                self.assertEqual(len(result["calls"]), 5)
                (root / LOG).rmdir()
                write_log(root)
                # Output errors likewise remain source-owned captured failures.
                output = root / LOG.with_suffix(".html")
                output.unlink()
                output.mkdir()
                result = await run(base)
                self.assertFalse(result["outputs"]["result"]["ok"])
                self.assertIn(
                    "IsADirectoryError",
                    result["outputs"]["result"]["children"][0]["stderr"],
                )
                output.rmdir()
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
                            "execute_action"
                            if forged == "registry"
                            else (
                                "finish"
                                if forged == "missing_registry"
                                else "select_action"
                            )
                        ),
                    )
                inputs = deepcopy(base)
                inputs["context"]["dry_run"] = True
                unknown = await remote.call(
                    "mathformer_html_route_execute_action",
                    {
                        "action_id": ACTION,
                        "context": inputs["context"],
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
