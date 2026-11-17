#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Real native self-tests, MCP bindings, Lunar compiler and PRISM execution.

No selected Python step is substituted. Fixtures copy its source, keep selected
commands intact, and vary matrix inputs. Only separate external provider and
compiler tests substitute process boundaries. No live model/prover is launched.
"""

from tempfile import gettempdir

# ruff: noqa: E402
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"]).resolve()
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.dont_write_bytecode = True
SITES = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
FIXTURES = ROOT / "tests/mcp/fixtures"
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
import tempfile
import unittest
from unittest.mock import patch
import yaml

import mathformer as hub
from textbook_route_tools import (
    ACTION,
    ROUTE,
    selected_match,
    checked_registry,
    check_state,
)
from textbook_route_fixture import populate, environment, external_process
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute, ExecutionRejected

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_textbook_autoformalization_workflow/workflow.yaml"
AUTHORED = (
    "skills/control/workflow-contract-validator/references/textbook-route.workflow.json"
)
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"]).resolve()
NATIVE = hub.build_registry()
REGISTRY = {ACTION: hub.action_to_dict(NATIVE[ACTION])}
MATCH = {
    "route": {"route_id": ROUTE, "action_ids": [ACTION]},
    "score": 23,
    "matched_terms": ["textbook autoformalization"],
}
ORDER = ["initialize", "select", "execute", "advance", "finish"]


def original():
    scope = dict(vars(hub))
    exec((FIXTURES / "textbook_route_original.py.txt").read_text(), scope)
    return scope["run_intent_match"]


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


def stable(value):
    """Normalize only the source-owned runtime clock, including JSON stdout."""
    if isinstance(value, dict):
        return {
            k: stable(v)
            for k, v in value.items()
            if k not in {"run_id", "duration_seconds"}
        }
    if isinstance(value, list):
        return [stable(v) for v in value]
    if isinstance(value, str) and value.startswith("{"):
        try:
            return stable(json.loads(value))
        except ValueError:
            pass
    return value


class TextbookRouteTests(unittest.TestCase):
    maxDiff = None

    def test_identity_generator_provenance_and_controls(self):
        doc = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(doc, json.loads((ROOT / AUTHORED).read_text()))
        self.assertEqual(doc["id"], "route_textbook_autoformalization_workflow")
        self.assertEqual(doc["aliases"], [ROUTE])
        self.assertEqual(doc["lifecycle"], "active")
        self.assertEqual(
            doc["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 5},
        )
        self.assertEqual(
            doc["policy"]["failure"],
            {"default": "fail", "retry": {"max_attempts": 1, "retryable_codes": []}},
        )
        self.assertEqual(doc["policy"]["effects"]["network"], [])
        self.assertEqual(
            doc["policy"]["effects"]["filesystem"]["write"],
            ["artifacts/", "artifacts/workflow_hub/"],
        )
        self.assertEqual(doc["flow"]["steps"][1]["max_iterations"], 1)
        self.assertEqual(doc["flow"]["steps"][1]["on_exhausted"], "fail")
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
        spec = importlib.util.spec_from_file_location(
            "textbook_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)
        self.assertEqual(generator.textbook_route_descriptor(), doc)
        self.assertEqual(checked_registry(REGISTRY), {ACTION: NATIVE[ACTION]})
        audit = hub.audit_control(NATIVE)
        self.assertFalse(
            {
                "scripts/textbook_route_tools.py",
                "tests/mcp/run_textbook_route_workflow_tests.py",
                "tests/mcp/fixtures/textbook_route_fixture.py",
                "tests/mcp/fixtures/textbook_route_startup/sitecustomize.py",
            }
            & set(audit["uncontrolled_entrypoints"])
        )

    def test_native_states_and_external_boundaries(self):
        initial = hub.initialize_intent_state()
        self.assertEqual(initial, {"ok": True, "children": []})
        for keep in [False, True]:
            context = hub.RunContext(keep_going=keep)
            for child in [{"ok": True}, {"ok": False}, {}]:
                state, done = hub.advance_intent_state(initial, child, context, 1)
                self.assertTrue(done)
                self.assertEqual(
                    state, {"ok": bool(child.get("ok", False)), "children": [child]}
                )
                with self.assertRaisesRegex(ValueError, "bounds"):
                    check_state(state, selecting=True)
            failed, done = hub.advance_intent_state(initial, {"ok": False}, context, 2)
            self.assertEqual(done, not keep)
            state, done = hub.advance_intent_state(failed, {"ok": True}, context, 2)
            self.assertTrue(done)
            self.assertFalse(state["ok"])
        self.assertEqual(initial["children"], [])
        with self.assertRaisesRegex(ValueError, "inconsistent"):
            check_state({"ok": True, "children": [{"ok": False}]})
        # A distinct external compiler input exercises run_action's actual
        # capture/audit/timeout and the frozen route's exception propagation.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            action = replace(
                NATIVE[ACTION], command=("fixture-compiler",), required_paths=()
            )
            registry = {ACTION: action}
            for mode in ["success", "reject", "timeout", "write", "crash"]:
                observed = []
                for runner in [original(), hub.run_intent_match]:
                    (root / "undeclared.txt").unlink(missing_ok=True)
                    with patch.object(hub, "subprocess", hub.subprocess):
                        calls = external_process(hub, root, mode)
                        if mode == "crash":
                            with self.assertRaisesRegex(
                                OSError, "compiler launch failure"
                            ):
                                runner(
                                    selected_match(MATCH),
                                    registry,
                                    hub.RunContext(),
                                    repository_root=root,
                                )
                        else:
                            result = runner(
                                selected_match(MATCH),
                                registry,
                                hub.RunContext(),
                                repository_root=root,
                            )
                            observed.append(result)
                            child = result["children"][0]
                            self.assertEqual(result["ok"], mode == "success")
                            self.assertEqual(
                                child["status"],
                                {
                                    "timeout": "timeout",
                                    "write": "undeclared_writes",
                                }.get(mode, "completed"),
                            )
                            if mode == "timeout":
                                self.assertEqual(
                                    (
                                        child["stdout"],
                                        child["stderr"],
                                        child["timeout_seconds"],
                                    ),
                                    ("partial", "deadline", 900),
                                )
                            elif mode == "write":
                                self.assertEqual(
                                    child["write_audit"]["unexpected_paths"],
                                    ["undeclared.txt"],
                                )
                            else:
                                self.assertEqual(
                                    child["returncode"], 7 if mode == "reject" else 0
                                )
                                self.assertEqual(child["stdout"], "typed fixture IR")
                        self.assertEqual(
                            calls, [{"command": ["fixture-compiler"], "timeout": 900}]
                        )
                if observed:
                    self.assertEqual(*observed)
            # Exercise the actual textbook provider adapter without running a
            # production batch. The fixture writes its output-schema response.
            source = (
                ROOT
                / "skills/latex-textbook/textbook-autoformalization-batch-orchestrator/scripts/run_textbook_autoformalization_batch.py"
            )
            spec = importlib.util.spec_from_file_location("textbook_provider", source)
            native = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(native)
            native.REPO_ROOT = root
            for mode in ["success", "reject", "timeout", "crash"]:
                output = root / mode
                output.mkdir()
                calls = external_process(native, root, mode)
                if mode in ["timeout", "crash"]:
                    error = (
                        native.subprocess.TimeoutExpired
                        if mode == "timeout"
                        else OSError
                    )
                    with self.assertRaises(error):
                        native.run_codex_generation(
                            {"job_id": "fixture"},
                            "source theorem",
                            output,
                            model=None,
                            timeout_sec=11,
                        )
                else:
                    result = native.run_codex_generation(
                        {"job_id": "fixture"},
                        "source theorem",
                        output,
                        model=None,
                        timeout_sec=11,
                    )
                    self.assertEqual(result["ok"], mode == "success")
                    self.assertEqual(result["parsed"]["status"], "draft_generated")
                    self.assertIn("fixture", result["parsed"]["lean_code"])
                    self.assertTrue(Path(result["last_message_file"]).is_file())
                self.assertEqual(len(calls), 1)
                self.assertEqual(calls[0]["timeout"], 11)

    def test_actual_registered_service_policy(self):
        async def run():
            import mcp_server as server

            arguments = dict(
                action=ACTION,
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
                            "mathformer_textbook_route_execute", arguments
                        )

        asyncio.run(run())

    def test_real_mcp_lunar_prism(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        doc = yaml.safe_load(CONTRACT.read_text())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve() / "repo"
            root.mkdir()
            startup = (
                "import sys;sys.dont_write_bytecode=True;sys.path[:0]="
                + repr([str(ROOT / "scripts"), str(FIXTURES), str(ROOT), *SITES])
                + ";from textbook_route_fixture import serve;serve("
                + repr(str(root))
                + ")"
            )
            manager, failure = SessionManager(), None
            async with manager.open(
                "textbook-route",
                StdioConfig(
                    command=sys.executable, args=["-c", startup], cwd=str(ROOT)
                ),
                {},
            ) as remote:
                try:
                    await self.connected(remote, root, doc)
                except Exception as error:
                    failure = error
            self.assertFalse(manager.active)
            if failure is not None:
                raise failure

    async def connected(self, remote, root, doc):
        tools = [
            t.model_dump(by_alias=True, exclude_none=True) for t in await remote.tools()
        ]

        def compile_document(document, inventory=tools):
            assets = snapshot(document)
            record = workflow_documents([DESCRIPTOR], assets)[0]
            self.assertTrue(record["validation"]["valid"], record)
            return compile_workflow("mcp:textbook-route", record, inventory), assets

        workflow, assets = compile_document(doc)
        self.assertTrue(workflow["runnable"], workflow["diagnostics"])
        self.assertEqual(workflow["runtime_status"], "ready")
        self.assertTrue(workflow["prism_source"])
        self.assertTrue(workflow["runtime_source"])
        self.assertEqual(set(workflow["bindings"]), set(doc["operations"]))
        self.assertFalse(
            compile_document(
                doc,
                [t for t in tools if t["name"] != "mathformer_textbook_route_execute"],
            )[0]["runnable"]
        )
        advertised = {t["name"]: t for t in tools}
        for name, op in doc["operations"].items():
            binding = op["execution"]["binding"]
            self.assertEqual(binding["target"], "mathformer_textbook_route_" + name)
            self.assertEqual(binding["target"], binding["operation"])
            tool = advertised[binding["target"]]
            self.assertEqual(set(tool["inputSchema"]["properties"]), set(op["inputs"]))
            self.assertEqual(
                set(tool["outputSchema"]["properties"]), set(op["outputs"])
            )

        async def authorize():
            pass

        async def run(inputs, document=doc):
            w, a = (workflow, assets) if document is doc else compile_document(document)
            self.assertTrue(w["runnable"], w["diagnostics"])
            return await execute(w, a, inputs, remote, authorize)

        inputs = dict(
            match=MATCH,
            registry=REGISTRY,
            context=vars(hub.RunContext()),
            repository_root=str(root),
        )
        # Preflight and dry-run must not start any process or write any report.
        for ready, dry in [(False, False), (False, True), (True, True)]:
            if ready:
                populate(root, ROOT)
            inputs["context"]["dry_run"] = dry
            result = await run(inputs)
            expected = original()(
                selected_match(MATCH),
                checked_registry(REGISTRY),
                hub.RunContext(**inputs["context"]),
                repository_root=root,
            )
            self.assertEqual(result["outputs"], {"result": expected})
            self.assertEqual([c["operation"] for c in result["calls"]], ORDER)
            self.assertFalse((root.parent / "processes.jsonl").exists())
            self.assertFalse((root / "artifacts").exists())
        inputs["context"]["dry_run"] = False
        for case, keep in [
            ("success", False),
            ("failure", False),
            ("failure", True),
            ("empty", False),
            ("invalid", False),
        ]:
            rows = populate(root, ROOT, case)
            inputs["context"]["keep_going"] = keep
            ledger = root.parent / "processes.jsonl"
            ledger.unlink(missing_ok=True)
            result = await run(inputs)
            self.assertEqual(result["status"], "accepted", result)
            self.assertEqual([c["operation"] for c in result["calls"]], ORDER)
            self.assertEqual(
                [c["tool"] for c in result["calls"]],
                ["mathformer_textbook_route_" + n for n in ORDER],
            )
            output = result["outputs"]["result"]
            self.assertEqual(output["ok"], case in ["success", "empty"])
            self.assertEqual(len(output["children"]), 1)
            child = output["children"][0]
            self.assertEqual(
                child["argv"],
                [
                    sys.executable,
                    "tests/test_program/run_comprehensive_tests.py",
                    "--module-family",
                    "textbook",
                    "--json",
                ],
            )
            self.assertEqual(child["cwd"], str(root))
            self.assertEqual(child["action"]["timeout_seconds"], 900)
            self.assertTrue(child["write_audit"]["ok"])
            if case == "invalid":
                self.assertEqual(child["returncode"], 1)
                self.assertIn("schema-bearing object", child["stderr"])
            else:
                trace = [json.loads(s) for s in ledger.read_text().splitlines()]
                checks = [r for r in trace if r["command"][1] != "-c"]
                self.assertEqual(
                    checks,
                    (
                        []
                        if case == "empty"
                        else [
                            {
                                "command": [sys.executable, *r["command"][1:]],
                                "timeout": r["timeout_seconds"],
                            }
                            for r in rows
                        ]
                    ),
                )
                report = json.loads(child["stdout"])
                self.assertEqual(report["families"], ["textbook"])
                self.assertEqual(
                    report["summary"]["total"], 0 if case == "empty" else 4
                )
                self.assertEqual(report["summary"]["skip"], 0)
                self.assertEqual(report["schema_errors"], [])
                self.assertEqual(child["returncode"], 3 if case == "failure" else 0)
                self.assertEqual(
                    json.loads(
                        (
                            root / "artifacts/test_program/deterministic_tests.json"
                        ).read_text()
                    ),
                    report,
                )
                self.assertTrue((root / report["dependency_map"]).is_file())
                dependency = json.loads((root / report["dependency_map"]).read_text())
                self.assertFalse(
                    any(v["available"] for v in dependency["providers"].values())
                )
                if case != "empty":
                    self.assertEqual(
                        [r["check_id"] for r in report["results"]],
                        [r["id"] for r in rows],
                    )
                    self.assertEqual(
                        [r["status"] for r in report["results"]],
                        (
                            ["fail", "pass", "pass", "pass"]
                            if case == "failure"
                            else ["pass"] * 4
                        ),
                    )
                    summaries = [
                        json.loads(r["stdout"])["summary"] for r in report["results"]
                    ]
                    self.assertEqual(summaries[0]["unit_count"], 3)
                    self.assertEqual(summaries[1]["bundle_count"], 1)
                    self.assertEqual(summaries[2]["job_count"], 2)
                    self.assertEqual(
                        summaries[3]["status_counts"],
                        {"blocked_no_generative_provider": 1},
                    )
            # Original and bound route receive identical filesystem and env.
            # Clear source-owned reports so both write audits observe creation.
            import shutil

            shutil.rmtree(root / "artifacts", ignore_errors=True)
            with patch.dict(os.environ, environment(root), clear=True):
                expected = original()(
                    selected_match(MATCH),
                    checked_registry(REGISTRY),
                    hub.RunContext(**inputs["context"]),
                    repository_root=root,
                )
            self.assertEqual(stable(output), stable(expected))
            self.assertTrue(result["runtime"]["effect_records"])
            self.assertTrue(result["runtime"]["provenance"])
            self.assertTrue(result["replay_artifacts"])
            self.assertFalse((root / "artifacts/workflow_hub").exists())
            shutil.rmtree(root / "artifacts", ignore_errors=True)
        populate(root, ROOT)
        inputs["context"]["dry_run"] = True
        exhausted = deepcopy(doc)
        exhausted["flow"]["steps"][1]["until"] = {"literal": False}
        result = await run(inputs, exhausted)
        self.assertEqual(result["status"], "failed", result)
        self.assertIsNone(result["outputs"])
        self.assertEqual(result["failure_disposition"], "fail")
        self.assertEqual([c["operation"] for c in result["calls"]], ORDER[:-1])
        budget = deepcopy(doc)
        budget["policy"]["limits"]["max_operation_calls"] = 4
        result = await run(inputs, budget)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(
            sum(bool(c.get("transport_call_performed")) for c in result["calls"]), 4
        )
        forged = deepcopy(REGISTRY)
        forged[ACTION]["command"] = ["injected"]
        result = await run({**inputs, "registry": forged})
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["calls"][-1]["operation"], "execute")
        result = await run({**inputs, "registry": {}})
        self.assertEqual(
            result["status"], "failed"
        )  # native finish cannot pack an absent registry entry
        self.assertEqual(result["calls"][-1]["operation"], "finish")
        state = (await remote.call("mathformer_textbook_route_initialize", {}))["state"]
        for keep in [False, True]:
            advanced = await remote.call(
                "mathformer_textbook_route_advance",
                dict(
                    state=state,
                    child={"ok": False},
                    action_count=1,
                    context={**inputs["context"], "keep_going": keep},
                ),
            )
            self.assertEqual(
                advanced,
                {"state": {"ok": False, "children": [{"ok": False}]}, "done": True},
            )
            with self.assertRaises(MCPConnectionError):
                await remote.call(
                    "mathformer_textbook_route_select",
                    dict(state=advanced["state"], match=MATCH),
                )
        # Null mount must use the real default only in dry-run.
        result = await run({**inputs, "repository_root": None})
        expected = original()(
            selected_match(MATCH),
            checked_registry(REGISTRY),
            hub.RunContext(**inputs["context"]),
        )
        self.assertEqual(result["outputs"], {"result": expected})
        with self.assertRaises(ExecutionRejected):
            await run(
                {
                    **inputs,
                    "match": {
                        **MATCH,
                        "route": {"route_id": "other", "action_ids": [ACTION]},
                    },
                }
            )


if __name__ == "__main__":
    program = unittest.main(verbosity=2, exit=False)
    result = program.result
    sys.exit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
