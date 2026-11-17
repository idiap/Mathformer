#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Run native test.runner steps through registered MCP and Lunar/PRISM.

Requires an explicit contract, including before the host installs it. Native
delegates run only in temporary fixture repositories. External compiler and
provider discovery are the only substituted boundaries.
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
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import asdict
import hashlib
import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import yaml

import mathformer as hub
from test_runner_route_tools import (
    ACTION,
    ROUTE,
    selected_match,
    checked_registry,
    check_state,
)
from test_runner_route_boundary import install_external
from test_runner_route_tree import NATIVE_FILES, populate, matrix, records, stable
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_test_runner_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
AUTHORED = "skills/control/workflow-contract-validator/references/test-runner-route.workflow.json"
NATIVE = hub.build_registry()
REGISTRY = {ACTION: hub.action_to_dict(NATIVE[ACTION])}
MATCH = {
    "route": json.loads(
        json.dumps(
            asdict(next(r for r in hub.build_intent_routes() if r.route_id == ROUTE))
        )
    ),
    "score": 23,
    "matched_terms": ["test", "runner"],
}
ORDER = ["initialize", "select", "run_action", "advance", "finish"]


def original():
    scope = dict(vars(hub))
    exec((FIXTURES / "test_runner_route_original.py.txt").read_text(), scope)
    return scope["run_intent_match"]


def snapshot(document):
    paths = {SCHEMA} | {row["path"] for row in document["provenance"]["sources"]}
    values = {path: (ROOT / path).read_text() for path in paths}
    values[DESCRIPTOR] = json.dumps(document)
    return [
        dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )
        for path, text in values.items()
    ]


@contextmanager
def external_fixtures():
    # Restore the two external boundaries and environment on exit. Production
    # has no fixture switch or dependency on this test module.
    with (
        patch.object(subprocess, "run", subprocess.run),
        patch.object(shutil, "which", shutil.which),
        patch.dict(
            os.environ,
            {
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONPATH": os.pathsep.join(
                    [str(FIXTURES / "test_runner_route_startup"), str(FIXTURES)]
                ),
            },
            clear=True,
        ),
    ):
        install_external()
        yield


def clean_run(root):
    shutil.rmtree(root / "artifacts", ignore_errors=True)
    (root / "undeclared.txt").unlink(missing_ok=True)
    for name in ("delegates.jsonl", "compiler.jsonl"):
        (root.parent / name).unlink(missing_ok=True)


def comparable(result):
    result = deepcopy(result)
    for child in result["children"]:
        if child.get("stdout", "").startswith("{"):
            child["stdout"] = stable(json.loads(child["stdout"]))
    return result


class TestRunnerRouteTests(unittest.TestCase):
    maxDiff = None

    def test_generator_identity_provenance_and_native_ports(self):
        document = yaml.safe_load(CONTRACT.read_text())
        spec = importlib.util.spec_from_file_location(
            "runner_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)
        self.assertEqual(generator.test_runner_route_descriptor(), document)
        self.assertEqual(json.loads((ROOT / AUTHORED).read_text()), document)
        self.assertEqual(
            (document["id"], document["aliases"], document["lifecycle"]),
            ("route_test_runner_workflow", [ROUTE], "active"),
        )
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 5},
        )
        self.assertEqual(
            document["policy"]["failure"],
            {"default": "fail", "retry": {"max_attempts": 1, "retryable_codes": []}},
        )
        self.assertEqual(
            document["policy"]["resume"],
            {"mode": "none", "require_matching_definition_and_inputs": True},
        )
        self.assertEqual(document["flow"]["steps"][1]["max_iterations"], 1)
        self.assertTrue(
            any(
                row["path"] == "scripts/mathformer.py"
                and row["selector"] == "run_intent_match"
                for row in document["provenance"]["sources"]
            )
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        self.assertEqual(checked_registry(REGISTRY), {ACTION: NATIVE[ACTION]})
        self.assertEqual(
            NATIVE[ACTION].command, ("{python}", "tests/run_quick.py", "--json")
        )
        self.assertEqual(NATIVE[ACTION].depends_on, ())
        self.assertIsNone(NATIVE[ACTION].timeout_seconds)
        for bad in [
            dict(MATCH, route={"route_id": ROUTE, "action_ids": ["test:docs"]}),
            dict(MATCH, route={**MATCH["route"], "title": "rewritten"}),
        ]:
            with self.assertRaises(ValueError):
                selected_match(bad)
        with self.assertRaises(ValueError):
            check_state({"ok": True, "children": [{"ok": False}]})

    def test_native_leaf_external_compiler_errors_and_timeouts(self):
        # Use actual leaf execution and auditing at the external compiler
        # boundary to cover outer timeout and unexpected launch exceptions.
        with tempfile.TemporaryDirectory() as directory, external_fixtures():
            root = Path(directory) / "repository"
            root.mkdir()
            for mode in ("pass", "fail", "timeout", "write", "artifact", "crash"):
                clean_run(root)
                item = hub.WorkflowAction(
                    ACTION,
                    "fixture compiler",
                    "test",
                    "validation",
                    "writes_artifacts",
                    command=("fixture-test-runner-compiler", mode),
                    timeout_seconds=29,
                    writes=("artifacts/",),
                )
                if mode == "crash":
                    with self.assertRaisesRegex(OSError, "compiler launch failed"):
                        hub.run_leaf_action(
                            item, hub.RunContext(), (), repository_root=root
                        )
                    continue
                child = hub.run_leaf_action(
                    item, hub.RunContext(), (), repository_root=root
                )
                self.assertEqual(child["ok"], mode in ("pass", "artifact"))
                self.assertEqual(len(records(root.parent / "compiler.jsonl")), 1)
                if mode == "timeout":
                    self.assertEqual(
                        (child["status"], child["timeout_seconds"], child["stdout"]),
                        ("timeout", 29, b"partial"),
                    )
                if mode == "write":
                    self.assertEqual(child["status"], "undeclared_writes")
                    self.assertEqual(
                        child["write_audit"]["unexpected_paths"], ["undeclared.txt"]
                    )

    def test_actual_registered_service_ceilings(self):
        async def scenario():
            import mcp_server as server

            args = dict(
                action_id=ACTION,
                registry=REGISTRY,
                context=vars(hub.RunContext()),
                repository_root=str(Path(gettempdir())),
            )
            for readonly, roots, message in [
                (True, None, "read-only"),
                (
                    False,
                    [Path(str(Path(gettempdir()) / "restricted"))],
                    "service roots",
                ),
            ]:
                with (
                    patch.object(server, "_READONLY", readonly),
                    patch.object(server, "_ALLOWED_WRITE_ROOTS", roots),
                ):
                    with self.assertRaisesRegex(Exception, message):
                        await server.mcp.call_tool(
                            "mathformer_test_runner_route_run_action", args
                        )
            self.assertEqual(
                server._cap_unbounded_timeouts({ACTION: NATIVE[ACTION]})[
                    ACTION
                ].timeout_seconds,
                600,
            )

        asyncio.run(scenario())

    def test_real_mcp_lunar_prism_and_original_parity(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(CONTRACT.read_text())
        oracle = original()
        import mcp_server as server

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve() / "repository"
            root.mkdir()
            manager = SessionManager()
            startup = (
                "import sys;sys.dont_write_bytecode=True;sys.path[:0]="
                + repr([str(ROOT / "scripts"), str(FIXTURES), *SITES])
                + ";from test_runner_route_boundary import serve;serve("
                + repr(str(root))
                + ","
                + repr(str(FIXTURES))
                + ")"
            )
            failure = None
            async with manager.open(
                "test-runner-route",
                StdioConfig(
                    command=sys.executable, args=["-c", startup], cwd=str(ROOT)
                ),
                {},
            ) as remote:
                try:
                    tools = [
                        tool.model_dump(by_alias=True, exclude_none=True)
                        for tool in await remote.tools()
                    ]

                    def compile_document(doc, inventory=tools):
                        assets = snapshot(doc)
                        return (
                            compile_workflow(
                                "mcp:test-runner-route",
                                workflow_documents([DESCRIPTOR], assets)[0],
                                inventory,
                            ),
                            assets,
                        )

                    workflow, assets = compile_document(document)
                    self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                    self.assertTrue(workflow["prism_source"])
                    self.assertTrue(workflow["runtime_source"])
                    self.assertEqual(set(workflow["bindings"]), set(ORDER))
                    self.assertFalse(compile_document(document, [])[0]["runnable"])
                    advertised = {tool["name"]: tool for tool in tools}
                    for op in document["operations"].values():
                        binding = op["execution"]["binding"]
                        self.assertEqual(binding["target"], binding["operation"])
                        tool = advertised[binding["target"]]
                        self.assertEqual(
                            set(tool["inputSchema"]["properties"]), set(op["inputs"])
                        )
                        self.assertEqual(
                            set(tool["outputSchema"]["properties"]), set(op["outputs"])
                        )

                    async def authorize():
                        pass

                    async def run(inputs, doc=document):
                        w, a = (
                            (workflow, assets)
                            if doc is document
                            else compile_document(doc)
                        )
                        self.assertTrue(w["runnable"], w["diagnostics"])
                        return await execute(w, a, inputs, remote, authorize)

                    inputs = dict(
                        match=MATCH,
                        registry=REGISTRY,
                        context=vars(hub.RunContext(dry_run=True)),
                        repository_root=str(root),
                    )
                    # Real preflight failure and dry-run, with no delegate launch.
                    for ready in (False, True):
                        if ready:
                            populate(root, ROOT)
                        for dry in (False, True) if not ready else (True,):
                            for keep in (False, True):
                                inputs["context"] = vars(
                                    hub.RunContext(dry_run=dry, keep_going=keep)
                                )
                                expected = oracle(
                                    selected_match(MATCH),
                                    server._cap_unbounded_timeouts(
                                        checked_registry(REGISTRY)
                                    ),
                                    hub.RunContext(**inputs["context"]),
                                    repository_root=root,
                                )
                                result = await run(inputs)
                                self.assertEqual(result["status"], "accepted", result)
                                self.assertEqual(
                                    result["outputs"], {"result": expected}
                                )
                                self.assertEqual(
                                    [call["operation"] for call in result["calls"]],
                                    ORDER,
                                )
                                self.assertEqual(len(expected["children"]), 1)
                                self.assertEqual(expected["ok"], ready)
                    self.assertEqual(records(root.parent / "delegates.jsonl"), [])
                    self.assertFalse((root / "artifacts").exists())
                    for name in NATIVE_FILES:
                        self.assertEqual(
                            (root / name).read_bytes(), (ROOT / name).read_bytes()
                        )
                    # Unchanged wrapper/main/run/advance/finalize/report code,
                    # including ordinary failures followed by later checks.
                    cases = [
                        (["pass", "artifact", "skip"], True),
                        (["fail", "timeout", "pass"], True),
                        (["write", "pass"], True),
                        (["crash", "pass"], True),
                        (["pass"], False),
                    ]
                    for modes, selected in cases:
                        for keep in (False, True):
                            matrix(root, modes, selected=selected)
                            clean_run(root)
                            inputs["context"] = vars(hub.RunContext(keep_going=keep))
                            result = await run(inputs)
                            self.assertEqual(result["status"], "accepted", result)
                            actual = result["outputs"]["result"]
                            self.assertEqual(
                                [call["operation"] for call in result["calls"]], ORDER
                            )
                            self.assertEqual(len(actual["children"]), 1)
                            child = actual["children"][0]
                            delegates = records(root.parent / "delegates.jsonl")
                            self.assertEqual(len(delegates), 1)
                            self.assertEqual(
                                delegates[0]["argv"],
                                [sys.executable, "tests/run_quick.py", "--json"],
                            )
                            self.assertEqual(delegates[0]["timeout"], 600)
                            trace = records(root.parent / "compiler.jsonl")
                            expected_modes = (
                                []
                                if not selected
                                else [m for m in modes if m != "skip"]
                            )
                            if "crash" in modes:
                                expected_modes = expected_modes[
                                    : expected_modes.index("crash") + 1
                                ]
                            self.assertEqual(
                                [r["argv"][1] for r in trace], expected_modes
                            )
                            self.assertEqual(
                                [r["timeout"] for r in trace],
                                [17 if m == "timeout" else 120 for m in expected_modes],
                            )
                            if "crash" in modes:
                                self.assertFalse(child["ok"])
                                self.assertEqual(child["returncode"], 1)
                                self.assertIn(
                                    "fixture compiler launch failed", child["stderr"]
                                )
                                self.assertFalse(
                                    (
                                        root
                                        / "artifacts/test_program/deterministic_tests.json"
                                    ).exists()
                                )
                            else:
                                report = json.loads(child["stdout"])
                                self.assertEqual(
                                    report["families"],
                                    ["control", "environment", "mcp", "source"],
                                )
                                expected_status = {
                                    "pass": "pass",
                                    "artifact": "pass",
                                    "skip": "skip",
                                    "fail": "fail",
                                    "timeout": "fail",
                                    "write": "fail",
                                }
                                self.assertEqual(
                                    [r["status"] for r in report["results"]],
                                    (
                                        [expected_status[m] for m in modes]
                                        if selected
                                        else []
                                    ),
                                )
                                self.assertEqual(
                                    report["summary"]["total"],
                                    len(modes) if selected else 0,
                                )
                                self.assertEqual(report["schema_errors"], [])
                                self.assertEqual(
                                    child["returncode"], 0 if report["ok"] else 3
                                )
                                output = root / "artifacts/test_program"
                                self.assertEqual(
                                    json.loads(
                                        (
                                            output / "deterministic_tests.json"
                                        ).read_text()
                                    ),
                                    report,
                                )
                                self.assertEqual(
                                    len(records(output / "deterministic_tests.jsonl")),
                                    report["summary"]["total"],
                                )
                                self.assertTrue(
                                    (output / "deterministic_tests.xml").exists()
                                )
                                self.assertTrue(
                                    (output / "dependency_map.json").exists()
                                )
                            self.assertEqual(
                                actual["status"],
                                (
                                    "intent_run_completed"
                                    if child["ok"]
                                    else "intent_run_failed"
                                ),
                            )
                            self.assertEqual(actual["ok"], child["ok"])
                            if "write" in modes:
                                self.assertEqual(child["status"], "undeclared_writes")
                                self.assertEqual(
                                    child["write_audit"]["unexpected_paths"],
                                    ["undeclared.txt"],
                                )
                            else:
                                self.assertTrue(child["write_audit"]["ok"])
                            self.assertTrue(result["runtime"]["effect_records"])
                            self.assertTrue(result["runtime"]["provenance"])
                            self.assertTrue(result["replay_artifacts"])
                            clean_run(root)
                            with external_fixtures():
                                expected = oracle(
                                    selected_match(MATCH),
                                    server._cap_unbounded_timeouts(
                                        checked_registry(REGISTRY)
                                    ),
                                    hub.RunContext(**inputs["context"]),
                                    repository_root=root,
                                )
                            self.assertEqual(comparable(actual), comparable(expected))
                    # Bound and call-budget failures use real compiled PRISM.
                    inputs["context"] = vars(hub.RunContext(dry_run=True))
                    exhausted = deepcopy(document)
                    exhausted["flow"]["steps"][1]["until"] = {"literal": False}
                    result = await run(inputs, exhausted)
                    self.assertEqual(
                        (
                            result["status"],
                            result["outputs"],
                            result["failure_disposition"],
                        ),
                        ("failed", None, "fail"),
                    )
                    self.assertEqual(
                        [call["operation"] for call in result["calls"]], ORDER[:-1]
                    )
                    limited = deepcopy(document)
                    limited["policy"]["limits"]["max_operation_calls"] = 4
                    result = await run(inputs, limited)
                    self.assertEqual(
                        (result["status"], result["outputs"]), ("failed", None)
                    )
                    self.assertEqual(
                        sum(
                            bool(c.get("transport_call_performed"))
                            for c in result["calls"]
                        ),
                        4,
                    )
                    # A real tool exception stops the graph without advance,
                    # finish, retry or a fabricated successful child.
                    changed = deepcopy(REGISTRY)
                    changed[ACTION]["command"] = ["unregistered-command"]
                    result = await run({**inputs, "registry": changed})
                    self.assertEqual(
                        (result["status"], result["outputs"]), ("failed", None)
                    )
                    self.assertEqual(
                        [call["operation"] for call in result["calls"]], ORDER[:3]
                    )
                    state = (
                        await remote.call("mathformer_test_runner_route_initialize", {})
                    )["state"]
                    child = {
                        "ok": False,
                        "status": "native_failure",
                        "stdout": "retained",
                    }
                    for keep in (False, True):
                        advanced = await remote.call(
                            "mathformer_test_runner_route_advance",
                            dict(
                                state=state,
                                child=child,
                                context=vars(hub.RunContext(keep_going=keep)),
                                action_count=1,
                            ),
                        )
                        self.assertEqual(
                            advanced,
                            {"state": {"ok": False, "children": [child]}, "done": True},
                        )
                        self.assertEqual(state, {"ok": True, "children": []})
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_test_runner_route_select",
                            dict(state=advanced["state"], match=MATCH),
                        )
                    # Null repository mount retains the native default on dry-run.
                    request = {**inputs, "repository_root": None}
                    result = await run(request)
                    expected = oracle(
                        selected_match(MATCH),
                        server._cap_unbounded_timeouts(checked_registry(REGISTRY)),
                        hub.RunContext(**request["context"]),
                    )
                    self.assertEqual(result["outputs"], {"result": expected})
                except Exception as error:
                    failure = error
            self.assertFalse(manager.active)
            if failure:
                raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
