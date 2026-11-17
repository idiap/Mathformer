#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native route, real governance fixture processes, MCP and Lunar/PRISM tests."""

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
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT),
    str(FIXTURES),
]
sys.path.extend(str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages"))

import asyncio
from copy import deepcopy
import hashlib
import importlib.util
import json
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import yaml

import mathformer as hub
from meta_help_route_tools import ACTION, ROUTE, selected_match, checked_registry
from meta_help_route_tree import populate, reset
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_meta_skills_help_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
AUTHORED = "skills/control/workflow-contract-validator/references/meta-help-route.workflow.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
MATCH = {
    "route": {"route_id": ROUTE, "action_ids": [ACTION]},
    "score": 17,
    "matched_terms": ["meta", "skills"],
}
REGISTRY = {ACTION: hub.action_to_dict(hub.build_registry()[ACTION])}
ORDER = ["initialize", "select_action", "invoke_action", "advance", "finish"]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def original():
    scope = dict(vars(hub))
    exec((FIXTURES / "meta_help_route_original.py.txt").read_text(), scope)
    return SimpleNamespace(**scope)


def snapshot(doc):
    values = {
        r["path"]: (ROOT / r["path"]).read_text() for r in doc["provenance"]["sources"]
    }
    values[SCHEMA] = (ROOT / SCHEMA).read_text()
    values[DESCRIPTOR] = json.dumps(doc)
    return [
        dict(
            path=p,
            content=s,
            encoding="text",
            sha256=hashlib.sha256(s.encode()).hexdigest(),
        )
        for p, s in values.items()
    ]


class MetaHelpTests(unittest.TestCase):
    maxDiff = None

    def test_identity_provenance_generator_and_source_state(self):
        doc = yaml.safe_load(CONTRACT.read_text())
        generator = load(
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
            "meta_help_generator",
        )
        self.assertEqual(doc, generator.meta_help_route_descriptor())
        self.assertEqual(doc, json.loads((ROOT / AUTHORED).read_text()))
        self.assertEqual(doc["id"], "route_meta_skills_help_workflow")
        self.assertEqual(doc["aliases"], [ROUTE])
        self.assertEqual(doc["lifecycle"], "active")
        self.assertEqual(list(doc["operations"]), ORDER)
        self.assertEqual(
            doc["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 5},
        )
        self.assertEqual(
            doc["policy"]["failure"],
            {"default": "fail", "retry": {"max_attempts": 1, "retryable_codes": []}},
        )
        self.assertTrue(
            any(
                r["path"] == "scripts/mathformer.py"
                and r["selector"] == "run_intent_match"
                for r in doc["provenance"]["sources"]
            )
        )
        for row in doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        native = checked_registry(REGISTRY)
        self.assertIsNone(native[ACTION].timeout_seconds)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for ready in [False, True]:
                if ready:
                    populate(ROOT, root)
                for keep in [False, True]:
                    context = hub.RunContext(dry_run=True, keep_going=keep)
                    result = hub.run_intent_match(
                        selected_match(MATCH), native, context, repository_root=root
                    )
                    self.assertEqual(
                        result,
                        original().run_intent_match(
                            selected_match(MATCH), native, context, repository_root=root
                        ),
                    )
                    self.assertEqual(result["ok"], ready)
                    self.assertEqual(len(result["children"]), 1)
                    initial = hub.initialize_intent_state()
                    child = {"ok": ready}
                    updated, done = hub.advance_intent_state(initial, child, context, 1)
                    self.assertEqual(initial, {"ok": True, "children": []})
                    self.assertEqual(updated, {"ok": ready, "children": [child]})
                    self.assertTrue(done)
            self.assertFalse((root / "artifacts").exists())
        # Preserve the general native early-stop and sticky-failure semantics.
        for keep in [False, True]:
            state, done = hub.advance_intent_state(
                hub.initialize_intent_state(), {}, hub.RunContext(keep_going=keep), 2
            )
            self.assertEqual(done, not keep)
            self.assertFalse(state["ok"])
            state, done = hub.advance_intent_state(
                state, {"ok": True}, hub.RunContext(keep_going=keep), 2
            )
            self.assertTrue(done)
            self.assertFalse(state["ok"])

    def test_native_suite_cursor_and_real_process_error(self):
        suite = load(
            ROOT / "tests/meta_skills/run_meta_skill_suite.py", "meta_help_suite_test"
        )
        self.assertEqual(len(suite.COMMANDS), 10)
        state = suite.initialize_results()
        for index, command in enumerate(suite.COMMANDS):
            self.assertEqual(suite.select_command(state), command)
            before = deepcopy(state)
            result = suite.append_and_test(
                state, {"ok": index != 1, "command": command}
            )
            self.assertEqual(state, before)
            state = result["results"]
            self.assertEqual(result["done"], index == 9)
        with self.assertRaises(IndexError):
            suite.select_command(state)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "suite.json"
            payload = suite.aggregate_write_return(state, output)
            self.assertEqual(payload["summary"], {"pass": 9, "fail": 1})
            self.assertFalse(payload["ok"])
            self.assertEqual(json.loads(output.read_text()), payload)
            # Actual OS launch failure: no fake native step or subprocess runner.
            suite.PYTHON = str(root / "absent-python")
            suite.OUTPUT_PATH = root / "never-written.json"
            with self.assertRaises(FileNotFoundError):
                suite.run_suite()
            self.assertFalse(suite.OUTPUT_PATH.exists())

    def test_external_compiler_response_fixtures(self):
        """Only an explicit external compiler boundary is substituted here.

        Route execution above uses the real ten native commands. This focused
        test sends deterministic process responses through the actual capture,
        parsing, success predicate and timeout propagation implementation.
        """
        suite = load(
            ROOT / "tests/meta_skills/run_meta_skill_suite.py", "meta_help_capture_test"
        )
        parts = ["fixture-compiler.py", "--json"]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()

            def boundary(command, **kwargs):
                self.assertEqual(command, [sys.executable, *parts])
                self.assertEqual(
                    kwargs,
                    dict(
                        cwd=root,
                        text=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=180,
                    ),
                )
                return subprocess.CompletedProcess(
                    command, response[0], response[1], response[2]
                )

            for response, expected in [
                ((0, '{"ok": true, "compiler": "fixture"}', ""), True),
                ((0, '{"ok": false}', "diagnostic"), False),
                ((7, '{"ok": true}', "compile failed"), False),
                ((0, "x" * 5000, "e" * 5000), True),
            ]:
                with patch.object(
                    suite,
                    "subprocess",
                    SimpleNamespace(run=boundary, PIPE=subprocess.PIPE),
                ):
                    check = suite.run_command(parts, root)
                self.assertEqual(check["ok"], expected)
                self.assertEqual(check["command"], [sys.executable, *parts])
                self.assertEqual(check["stdout"], response[1][-4000:])
                self.assertEqual(check["stderr"], response[2][-4000:])
                self.assertEqual(
                    check["payload"],
                    (
                        json.loads(response[1])
                        if response[1].startswith("{")
                        else {"stdout": response[1]}
                    ),
                )
            for error in [
                subprocess.TimeoutExpired([sys.executable, *parts], 180),
                OSError("compiler launch failed"),
            ]:

                def failing_boundary(command, **kwargs):
                    boundary(command, **kwargs)
                    raise error

                with patch.object(
                    suite,
                    "subprocess",
                    SimpleNamespace(run=failing_boundary, PIPE=subprocess.PIPE),
                ):
                    with self.assertRaises(type(error)):
                        suite.run_command(parts, root)

    def test_real_mcp_and_lunar(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        doc = yaml.safe_load(CONTRACT.read_text())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve() / "repo"
            root.mkdir()
            populate(ROOT, root)
            sites = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
            server = (
                'import sys;sys.dont_write_bytecode=True;sys.path[:0]=["scripts","tests/mcp/fixtures"];'
                f"sys.path.extend({sites!r});"
                f"from meta_help_route_tree import serve;serve({str(root)!r})"
            )
            manager, failure = SessionManager(), None
            async with manager.open(
                "meta-help",
                StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
                {},
            ) as remote:
                try:
                    tools = [
                        t.model_dump(by_alias=True, exclude_none=True)
                        for t in await remote.tools()
                    ]

                    def compiled(document, inventory=None):
                        assets = snapshot(document)
                        workflow = workflow_documents([DESCRIPTOR], assets)[0]
                        return (
                            compile_workflow(
                                "mcp:meta-help",
                                workflow,
                                tools if inventory is None else inventory,
                            ),
                            assets,
                        )

                    workflow, assets = compiled(doc)
                    self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                    self.assertTrue(workflow["runtime_source"])
                    self.assertTrue(workflow["prism_source"])
                    self.assertEqual(set(workflow["bindings"]), set(ORDER))
                    self.assertFalse(compiled(doc, [])[0]["runnable"])
                    base = dict(
                        match=MATCH,
                        registry=REGISTRY,
                        context=vars(hub.RunContext()),
                        mount={"repository_root": str(root)},
                    )

                    async def authorize():
                        pass

                    async def run(inputs=None, document=None):
                        bound, received = compiled(document or doc)
                        self.assertTrue(bound["runnable"], bound["diagnostics"])
                        return await execute(
                            bound, received, inputs or base, remote, authorize
                        )

                    # Run the actual fixed ten-command suite on synthetic inputs.
                    # A failed check still reaches all later checks and aggregation.
                    result = await run()
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual([c["operation"] for c in result["calls"]], ORDER)
                    route = result["outputs"]["result"]
                    self.assertEqual(len(route["children"]), 1)
                    child = route["children"][0]
                    self.assertEqual(
                        child["argv"],
                        [
                            sys.executable,
                            "tests/meta_skills/run_meta_skill_suite.py",
                            "--json",
                        ],
                    )
                    self.assertEqual(child["status"], "completed")
                    report = json.loads(child["stdout"])
                    suite = load(
                        ROOT / "tests/meta_skills/run_meta_skill_suite.py",
                        "meta_help_suite_order",
                    )
                    self.assertEqual(
                        [r["command"] for r in report["results"]],
                        [[sys.executable, *c] for c in suite.COMMANDS],
                    )
                    self.assertEqual(report["check_count"], 10)
                    self.assertEqual(
                        report["summary"]["pass"] + report["summary"]["fail"], 10
                    )
                    self.assertGreater(report["summary"]["fail"], 0)
                    self.assertFalse(route["ok"])
                    self.assertEqual(route["status"], "intent_run_failed")
                    self.assertEqual(child["returncode"], 1)
                    self.assertEqual(
                        json.loads(
                            (
                                root / "artifacts/meta_skills/meta_skill_suite.json"
                            ).read_text()
                        ),
                        report,
                    )
                    self.assertTrue(child["write_audit"]["ok"], child["write_audit"])
                    self.assertEqual(route["route"]["score"], MATCH["score"])
                    self.assertEqual(
                        route["route"]["matched_terms"], MATCH["matched_terms"]
                    )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["runtime"]["provenance"])
                    self.assertTrue(result["replay_artifacts"])
                    # Source write auditing detects a redirected suite output.
                    reset(root)
                    output = root / "artifacts/meta_skills/meta_skill_suite.json"
                    output.parent.mkdir(parents=True)
                    output.symlink_to(root / "undeclared.txt")
                    result = await run()
                    child = result["outputs"]["result"]["children"][0]
                    self.assertEqual(child["status"], "undeclared_writes")
                    self.assertEqual(
                        child["write_audit"]["unexpected_paths"], ["undeclared.txt"]
                    )
                    self.assertFalse(child["ok"])
                    # An aggregation I/O exception makes the native process fail;
                    # earlier source-owned reports survive and no retry occurs.
                    reset(root)
                    (root / "undeclared.txt").unlink()
                    output.mkdir(parents=True)
                    result = await run()
                    child = result["outputs"]["result"]["children"][0]
                    self.assertNotEqual(child["returncode"], 0)
                    self.assertEqual(child["stdout"], "")
                    self.assertIn("IsADirectoryError", child["stderr"])
                    self.assertTrue(
                        (
                            root / "artifacts/meta_skills/task_registry_validation.json"
                        ).exists()
                    )
                    # Preflight rejection and dry-run return child data normally.
                    reset(root)
                    source = root / "tests/meta_skills/run_meta_skill_suite.py"
                    source.unlink()
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
                            self.assertEqual(result["outputs"], {"result": expected})
                            self.assertFalse(expected["ok"])
                            self.assertEqual(len(result["calls"]), 5)
                            self.assertFalse((root / "artifacts").exists())
                    source.write_bytes(
                        (
                            ROOT / "tests/meta_skills/run_meta_skill_suite.py"
                        ).read_bytes()
                    )
                    inputs = deepcopy(base)
                    inputs["context"]["dry_run"] = True
                    result = await run(inputs)
                    self.assertTrue(result["outputs"]["result"]["ok"])
                    self.assertEqual(
                        result["outputs"]["result"]["children"][0]["status"], "dry_run"
                    )
                    inputs["mount"] = {}
                    result = await run(inputs)
                    expected = hub.run_intent_match(
                        selected_match(MATCH),
                        checked_registry(REGISTRY),
                        hub.RunContext(dry_run=True),
                    )
                    self.assertEqual(result["outputs"], {"result": expected})
                    # Unknown registry action is failure data until finish tries
                    # to enrich the route metadata, exactly as in the native path.
                    inputs = deepcopy(base)
                    inputs["registry"] = {}
                    result = await run(inputs)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(len(result["calls"]), 5)
                    for port in ["registry", "match"]:
                        inputs = deepcopy(base)
                        if port == "registry":
                            inputs[port][ACTION]["command"] = ["unregistered-command"]
                        else:
                            inputs[port]["route"]["title"] = "forged"
                        result = await run(inputs)
                        self.assertEqual(result["status"], "failed", result)
                        self.assertEqual(
                            len(result["calls"]), 3 if port == "registry" else 2
                        )
                    inputs = deepcopy(base)
                    inputs["context"]["dry_run"] = True
                    for budget in [1, 4]:
                        bounded = deepcopy(doc)
                        bounded["policy"]["limits"]["max_operation_calls"] = budget
                        result = await run(inputs, bounded)
                        self.assertEqual(result["status"], "failed", result)
                        self.assertIsNone(result["outputs"])
                        self.assertEqual(
                            sum(
                                bool(c.get("transport_call_performed"))
                                for c in result["calls"]
                            ),
                            budget,
                        )
                    exhausted = deepcopy(doc)
                    exhausted["flow"]["steps"][1]["until"] = {"literal": False}
                    result = await run(inputs, exhausted)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]], ORDER[:-1]
                    )
                    self.assertIsNone(result["outputs"])
                    stale = deepcopy(doc)
                    stale["flow"]["steps"][1]["body"]["steps"][0]["arguments"][
                        "state"
                    ] = {"literal": {"ok": True, "children": [{"ok": True}]}}
                    result = await run(inputs, stale)
                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(len(result["calls"]), 2)
                    inputs["context"]["dry_run"] = False
                    inputs["mount"]["repository_root"] = str(root.parent / "outside")
                    result = await run(inputs)
                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(len(result["calls"]), 3)
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
