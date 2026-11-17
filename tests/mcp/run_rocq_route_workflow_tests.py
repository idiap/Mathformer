#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Offline native Rocq route, real registered MCP ports and Lunar/PRISM."""

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
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT / "tests/mcp/fixtures"),
]
SITES = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
sys.path.extend(SITES)
BOUNDARY = ROOT / "tests/mcp/fixtures/rocq_route_boundary"
os.environ["PYTHONPATH"] = os.pathsep.join([str(BOUNDARY), *SITES])

import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib.util
import json
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import yaml

import mathformer as hub
from rocq_route_tools import (
    ACTION,
    ROUTE,
    selected_match,
    checked_registry,
    check_state,
    register_rocq_route_tools,
)
from rocq_route_tree import populate, stable, LEAF, DRAFT, CHECK
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_formalize_rocq_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
MATCH = {
    "route": {"route_id": ROUTE, "action_ids": [ACTION]},
    "score": 19,
    "matched_terms": ["rocq", "proof scripts"],
}
REGISTRY = {ACTION: hub.action_to_dict(hub.build_registry()[ACTION])}
ORDER = ["initialize", "select", "run", "advance", "finish"]


def original():
    scope = dict(vars(hub))
    exec((ROOT / "tests/mcp/fixtures/rocq_route_original.py.txt").read_text(), scope)
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
            "path": p,
            "content": v,
            "encoding": "text",
            "sha256": hashlib.sha256(v.encode()).hexdigest(),
        }
        for p, v in values.items()
    ]


class RocqRouteTests(unittest.TestCase):
    maxDiff = None

    def test_generator_identity_policy_and_provenance(self):
        spec = importlib.util.spec_from_file_location(
            "rocq_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        document = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(module.rocq_route_descriptor(), document)
        self.assertEqual(document["id"], "route_formalize_rocq_workflow")
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
            document["policy"]["effects"]["filesystem"]["write"],
            ["artifacts/rocq_wiki_level/", "artifacts/workflow_hub/"],
        )
        self.assertEqual(document["flow"]["steps"][1]["max_iterations"], 1)
        self.assertEqual(set(document["operations"]), set(ORDER))
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
        item = checked_registry(REGISTRY)[ACTION]
        self.assertEqual(item.command, ("{python}", LEAF, "--json"))
        self.assertIsNone(item.timeout_seconds)
        self.assertFalse(item.depends_on)
        self.assertFalse(item.allows_extra_args)
        self.assertEqual(selected_match(MATCH).route.action_ids, (ACTION,))

    def test_native_control_stopping_sticky_failure_and_bounds(self):
        oracle = original()
        native, match = checked_registry(REGISTRY), selected_match(MATCH)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            # No process exists at this mount: actual preflight and dry-run only.
            for ready in [False, True]:
                if ready:
                    (root / LEAF).parent.mkdir(parents=True)
                    (root / LEAF).write_text('raise AssertionError("must not launch")')
                for keep in [False, True]:
                    context = hub.RunContext(dry_run=True, keep_going=keep)
                    self.assertEqual(
                        hub.run_intent_match(
                            match, native, context, repository_root=root
                        ),
                        oracle.run_intent_match(
                            match, native, context, repository_root=root
                        ),
                    )
            # Exercise the native route iterator (including zero-action and early stop).
            for actions in [(), (ACTION,), (ACTION, ACTION)]:
                custom = replace(match, route=replace(match.route, action_ids=actions))
                for keep in [False, True]:
                    results = []
                    for executor in [oracle.run_intent_match, hub.run_intent_match]:
                        result = executor(
                            custom,
                            native,
                            hub.RunContext(keep_going=keep),
                            repository_root=root / "absent",
                        )
                        self.assertEqual(
                            len(result["children"]),
                            len(actions) if keep else min(1, len(actions)),
                        )
                        results.append(result)
                    self.assertEqual(*results)
        for keep in [False, True]:
            initial = hub.initialize_intent_state()
            state, done = hub.advance_intent_state(
                initial, {"ok": False}, hub.RunContext(keep_going=keep), 1
            )
            self.assertEqual(initial, {"ok": True, "children": []})
            self.assertTrue(done)
            check_state(state)
            with self.assertRaises(ValueError):
                check_state(state, selecting=True)
            state, done = hub.advance_intent_state(
                initial, {"ok": False}, hub.RunContext(keep_going=keep), 2
            )
            self.assertEqual(done, not keep)
            state, done = hub.advance_intent_state(
                state, {"ok": True}, hub.RunContext(keep_going=keep), 2
            )
            self.assertFalse(state["ok"])
            self.assertEqual(state["children"], [{"ok": False}, {"ok": True}])
            self.assertTrue(done)

    def test_registered_service_authority_and_state_validation(self):
        async def checks():
            from mcp.server.fastmcp import FastMCP

            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)

                def deny():
                    raise ValueError("service is read-only")

                for authorize, allowed, message in [
                    (deny, lambda path: True, "read-only"),
                    (
                        lambda: None,
                        lambda path: False,
                        "outside configured service roots",
                    ),
                ]:
                    server = FastMCP("authority fixture")
                    register_rocq_route_tools(server, authorize, allowed)
                    with self.assertRaisesRegex(Exception, message):
                        await server.call_tool(
                            "mathformer_rocq_route_run",
                            {
                                "action_id": ACTION,
                                "registry": REGISTRY,
                                "context": vars(hub.RunContext()),
                                "repository_root": str(root),
                            },
                        )
                    # Dry-run retains native preflight without requiring write authority.
                    await server.call_tool(
                        "mathformer_rocq_route_run",
                        {
                            "action_id": ACTION,
                            "registry": REGISTRY,
                            "context": vars(hub.RunContext(dry_run=True)),
                            "repository_root": str(root),
                        },
                    )
                for tool, arguments in [
                    (
                        "finish",
                        {
                            "state": {"ok": True, "children": []},
                            "match": MATCH,
                            "registry": REGISTRY,
                        },
                    ),
                    (
                        "advance",
                        {
                            "state": {"ok": False, "children": []},
                            "child": {"ok": True},
                            "context": vars(hub.RunContext()),
                            "action_count": 1,
                        },
                    ),
                ]:
                    with self.assertRaisesRegex(
                        Exception, "requires exactly one observation|inconsistent"
                    ):
                        await server.call_tool(
                            "mathformer_rocq_route_" + tool, arguments
                        )
                self.assertEqual(list(root.iterdir()), [])

        asyncio.run(checks())

    def test_native_suite_aggregation_and_command_bounds(self):
        spec = importlib.util.spec_from_file_location("rocq_suite_fixture", ROOT / LEAF)
        suite = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(suite)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            prepared = suite.prepare_suite(
                output_dir=output, require_compiler=False, timeout_sec=120
            )
            for invalid in ["", "not-json", "[]", '{"ok":1}']:
                result = suite.aggregate_suite(
                    prepared,
                    {"ok": True, "stdout": invalid},
                    {"ok": True, "stdout": invalid},
                )
                self.assertFalse(result["ok"])
                self.assertFalse(result["checks"]["draft_report_ok"])
                self.assertFalse(result["checks"]["execution_report_ok"])
                self.assertFalse(result["checks"]["all_files_produced"])
                self.assertFalse(result["checks"]["all_theorems_seen"])
            self.assertNotIn("--require-compiler", prepared["execution_cmd"])
            self.assertIn(
                "--require-compiler",
                suite.suite_context(
                    output_dir=output, require_compiler=True, timeout_sec=120
                )["execution_cmd"],
            )

    def test_checker_completes_both_passes_and_missing_compiler_policy(self):
        # Deterministic boundary only; actual structural validation and aggregation.
        sys.path.insert(0, str(ROOT))
        from backends.rocq.MathformerRocq import autoformalize as backend

        spec = importlib.util.spec_from_file_location(
            "rocq_checker_fixture", ROOT / CHECK
        )
        checker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(checker)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ["A.v", "B.v"]:
                (root / name).write_text("Theorem bad : True. Proof. admit. Admitted.")
            seen = []

            def compiler(argv, **kwargs):
                # Every structural read completes before any compiler invocation.
                seen.append(Path(argv[-1]).name)
                self.assertEqual(kwargs["timeout"], 120)
                return SimpleNamespace(returncode=0, stdout="fixture", stderr="")

            with (
                patch.object(
                    backend,
                    "find_rocq_compiler",
                    return_value={
                        "prefix": [
                            str(
                                Path(gettempdir())
                                / "mathformer-test-fixtures/fixture/rocq"
                            ),
                            "compile",
                        ]
                    },
                ),
                patch.object(
                    backend,
                    "subprocess",
                    SimpleNamespace(
                        run=compiler, TimeoutExpired=hub.subprocess.TimeoutExpired
                    ),
                ),
            ):
                report = checker.run_validation(
                    path=root,
                    compiler_bin=None,
                    timeout_sec=120,
                    require_compiler=False,
                )
            self.assertEqual(seen, ["A.v", "B.v"])
            self.assertFalse(report["ok"])
            self.assertFalse(report["structural_ok"])
            self.assertEqual(len(report["validations"]), 2)
            self.assertEqual(len(report["external_checks"]), 2)
            # Native templates rather than canned checker data.
            latex = ROOT / "tests/latex/wiki_level/contrapositive.tex"
            for file in root.glob("*.v"):
                file.unlink()
            backend.draft_case(
                latex_file=latex,
                case_id="wiki_contrapositive",
                output_file=root / "A.v",
            )
            with patch.object(backend, "find_rocq_compiler", return_value=None):
                for required in [False, True]:
                    report = checker.run_validation(
                        path=root,
                        compiler_bin=None,
                        timeout_sec=120,
                        require_compiler=required,
                    )
                    self.assertEqual(report["ok"], not required)
                    self.assertTrue(report["structural_ok"])
                    self.assertFalse(report["compiler_available"])
                    self.assertTrue(report["external_checks"][0]["skipped"])

    def test_registered_mcp_real_lunar_execution(self):
        asyncio.run(self.connected())

    async def connected(self):
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        async with manager.open(
            "rocq-route",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {"PYTHONPATH": os.environ["PYTHONPATH"], "PYTHONDONTWRITEBYTECODE": "1"},
        ) as remote:
            tools = [
                tool.model_dump(by_alias=True, exclude_none=True)
                for tool in await remote.tools()
            ]
            document = yaml.safe_load(CONTRACT.read_text())

            def compile(doc):
                assets = snapshot(doc)
                workflow = workflow_documents([DESCRIPTOR], assets)[0]
                self.assertTrue(workflow["validation"]["valid"], workflow)
                compiled = compile_workflow("mcp:rocq-route", workflow, tools)
                self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                self.assertEqual(compiled["runtime_status"], "ready")
                self.assertTrue(compiled["prism_source"])
                self.assertTrue(compiled["runtime_source"])
                self.assertEqual(set(compiled["bindings"]), set(ORDER))
                return compiled, assets

            compiled, assets = compile(document)
            missing = [
                tool for tool in tools if tool["name"] != "mathformer_rocq_route_run"
            ]
            self.assertFalse(
                compile_workflow(
                    "mcp:rocq-route",
                    workflow_documents([DESCRIPTOR], assets)[0],
                    missing,
                )["runnable"]
            )

            async def authorize():
                pass

            async def run(inputs, changed=None):
                graph, received = compile(changed) if changed else (compiled, assets)
                return await execute(graph, received, inputs, remote, authorize)

            scenarios = [
                ({}, True),
                ({"compiler": "missing"}, True),
                ({"compiler": "reject"}, False),
                ({"compiler": "timeout"}, False),
                ({"compiler": "crash"}, False),
                ({"compiler": "write"}, False),
                ({"draft_failure": True}, False),
                ({"subset": True}, False),
                ({"extra_bad": True}, False),
                ({"ready": False}, False),
            ]
            for options, success in scenarios:
                with (
                    self.subTest(options=options),
                    tempfile.TemporaryDirectory() as directory,
                ):
                    root = Path(directory).resolve()
                    output = populate(root, ROOT, **options)
                    base = {
                        "context": vars(hub.RunContext()),
                        "match": MATCH,
                        "registry": REGISTRY,
                        "repository_root": str(root),
                    }
                    for keep in [False, True]:
                        inputs = deepcopy(base)
                        inputs["context"]["keep_going"] = keep
                        for dry in [True, False]:
                            inputs["context"]["dry_run"] = dry
                            result = await run(inputs)
                            self.assertEqual(result["status"], "accepted", result)
                            self.assertEqual(
                                [c["operation"] for c in result["calls"]], ORDER
                            )
                            envelope = result["outputs"]["result"]
                            self.assertEqual(len(envelope["children"]), 1)
                            self.assertEqual(envelope["route"]["score"], MATCH["score"])
                            self.assertEqual(
                                envelope["route"]["matched_terms"],
                                MATCH["matched_terms"],
                            )
                            expected_ok = options.get("ready", True) if dry else success
                            self.assertEqual(envelope["ok"], expected_ok)
                            self.assertEqual(
                                envelope["status"],
                                (
                                    "intent_run_completed"
                                    if expected_ok
                                    else "intent_run_failed"
                                ),
                            )
                            child = envelope["children"][0]
                            if not options.get("ready", True):
                                self.assertTrue(child["preflight_errors"])
                                self.assertNotIn("returncode", child)
                            elif dry:
                                self.assertEqual(child["status"], "dry_run")
                                self.assertNotIn("returncode", child)
                            else:
                                self.assertEqual(
                                    child["argv"], [sys.executable, LEAF, "--json"]
                                )
                                report = json.loads(child["stdout"])
                                self.assertEqual(
                                    set(report["steps"]), {"draft", "execution"}
                                )
                                self.assertIn("generated_at_utc", report)
                                self.assertIn("duration_ms", report["steps"]["draft"])
                                self.assertFalse(report["require_compiler"])
                                if options.get("compiler") == "write":
                                    self.assertTrue(report["ok"])
                                    self.assertEqual(child["returncode"], 0)
                                    self.assertEqual(
                                        child["status"], "undeclared_writes"
                                    )
                                    self.assertEqual(
                                        child["write_audit"]["unexpected_paths"],
                                        ["undeclared.txt"],
                                    )
                                    (root / "undeclared.txt").unlink()
                                else:
                                    self.assertEqual(
                                        child["returncode"], 0 if success else 1
                                    )
                                    self.assertTrue(child["write_audit"]["ok"])
                                calls = [
                                    json.loads(line)
                                    for line in (output / "fixture-calls.jsonl")
                                    .read_text()
                                    .splitlines()
                                ]
                                index = max(
                                    i
                                    for i, c in enumerate(calls)
                                    if len(c["argv"]) > 1 and c["argv"][1] == LEAF
                                )
                                current = calls[index:]
                                self.assertEqual(
                                    [c["argv"][1] for c in current[:3]],
                                    [LEAF, DRAFT, CHECK],
                                )
                                self.assertEqual(
                                    [c["timeout"] for c in current[:3]],
                                    [None, 120, 120],
                                )
                                self.assertEqual(
                                    current[2]["argv"][-3:],
                                    ["--timeout-sec", "120", "--json"],
                                )
                                check = report["steps"]["execution"]["parsed"]
                                if options.get("draft_failure"):
                                    self.assertFalse(report["steps"]["draft"]["ok"])
                                    self.assertEqual(check["file_count"], 0)
                                    self.assertFalse(check["ok"])
                                elif options.get("compiler") == "crash":
                                    self.assertIsNone(check)
                                    self.assertIn(
                                        "fixture compiler launch failed",
                                        report["steps"]["execution"]["stderr"],
                                    )
                                else:
                                    count = (
                                        1
                                        if options.get("subset")
                                        else 6 if options.get("extra_bad") else 5
                                    )
                                    self.assertEqual(check["file_count"], count)
                                    self.assertEqual(len(check["validations"]), count)
                                    self.assertEqual(
                                        len(check["external_checks"]), count
                                    )
                                    self.assertEqual(
                                        json.loads(
                                            (
                                                output / "wiki_level_execution.json"
                                            ).read_text()
                                        ),
                                        check,
                                    )
                                    compiler_calls = current[3:]
                                    self.assertEqual(
                                        len(compiler_calls),
                                        (
                                            0
                                            if options.get("compiler") == "missing"
                                            else count
                                        ),
                                    )
                                    self.assertEqual(
                                        [c["timeout"] for c in compiler_calls],
                                        [120] * len(compiler_calls),
                                    )
                                    self.assertEqual(
                                        [
                                            Path(c["argv"][-1]).name
                                            for c in compiler_calls
                                        ],
                                        (
                                            []
                                            if not compiler_calls
                                            else sorted(
                                                p.name for p in output.glob("*.v")
                                            )
                                        ),
                                    )
                                    if options.get("compiler") == "missing":
                                        self.assertFalse(check["compiler_available"])
                                        self.assertTrue(
                                            all(
                                                c["ok"] and c["skipped"]
                                                for c in check["external_checks"]
                                            )
                                        )
                                    if options.get("compiler") == "timeout":
                                        self.assertTrue(
                                            all(
                                                c["timeout"] and not c["ok"]
                                                for c in check["external_checks"]
                                            )
                                        )
                                        self.assertEqual(
                                            check["external_checks"][0]["stdout"],
                                            "partial compile",
                                        )
                                    if options.get("extra_bad"):
                                        self.assertFalse(check["structural_ok"])
                                        self.assertTrue(check["external_ok"])
                                    if options.get("subset"):
                                        self.assertFalse(report["steps"]["draft"]["ok"])
                                        self.assertTrue(check["ok"])
                                        self.assertFalse(
                                            report["checks"]["all_files_produced"]
                                        )
                                        self.assertFalse(
                                            report["checks"]["all_theorems_seen"]
                                        )
                                    if options == {}:
                                        self.assertTrue(all(report["checks"].values()))
                                        self.assertEqual(
                                            len(list(output.glob("*.vo"))), 5
                                        )
                                if not options.get("draft_failure") and not options.get(
                                    "subset"
                                ):
                                    draft = report["steps"]["draft"]["parsed"]
                                    self.assertTrue(draft["ok"])
                                    self.assertEqual(
                                        json.loads(
                                            (
                                                output / "wiki_level_draft.json"
                                            ).read_text()
                                        ),
                                        draft,
                                    )
                                    for file in output.glob("Autoformalized*.v"):
                                        self.assertIn("Qed.", file.read_text())
                                        self.assertNotIn("Admitted.", file.read_text())
                            self.assertTrue(result["runtime"]["effect_records"])
                            self.assertTrue(result["runtime"]["provenance"])
                            self.assertTrue(result["replay_artifacts"])
                    # Compare complete native envelope, retaining audit and report data.
                    if options in [
                        {},
                        {"compiler": "missing"},
                        {"draft_failure": True},
                    ]:
                        expected = original().run_intent_match(
                            selected_match(MATCH),
                            checked_registry(REGISTRY),
                            hub.RunContext(),
                            repository_root=root,
                        )
                        actual = await run(base)
                        self.assertEqual(
                            stable(actual["outputs"]["result"]), stable(expected)
                        )
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                populate(root, ROOT)
                base = {
                    "context": vars(hub.RunContext(dry_run=True)),
                    "match": MATCH,
                    "registry": REGISTRY,
                    "repository_root": str(root),
                }
                for kind in ["registry", "match", "cursor"]:
                    inputs, changed = deepcopy(base), None
                    if kind == "registry":
                        inputs["registry"][ACTION]["command"] = ["forged"]
                    elif kind == "match":
                        inputs["match"]["route"]["title"] = "forged"
                    else:
                        changed = deepcopy(document)
                        changed["flow"]["steps"][1]["body"]["steps"][0]["arguments"][
                            "state"
                        ] = {"literal": {"ok": True, "children": [{"ok": True}]}}
                    result = await run(inputs, changed)
                    self.assertEqual(result["status"], "failed")
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(
                        result["calls"][-1]["operation"],
                        "run" if kind == "registry" else "select",
                    )
                child = await remote.call(
                    "mathformer_rocq_route_run",
                    {
                        "action_id": ACTION,
                        "registry": {},
                        "context": base["context"],
                        "repository_root": str(root),
                    },
                )
                self.assertEqual(
                    child,
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
                    result = await run(base, changed)
                    self.assertEqual(result["status"], "failed")
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
                result = await run(base, changed)
                self.assertEqual(result["status"], "failed")
                self.assertIsNone(result["outputs"])
                self.assertEqual([c["operation"] for c in result["calls"]], ORDER[:-1])
        self.assertFalse(manager.active)


if __name__ == "__main__":
    program = unittest.main(verbosity=2, exit=False)
    result = program.result
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
