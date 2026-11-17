#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Runnable RFDE route bindings through the real MCP and Lunar/PRISM runtime."""

from tempfile import gettempdir

# ruff: noqa: E402
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
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
from dataclasses import asdict
import hashlib
import importlib.util
import json
import tempfile
import unittest
from unittest.mock import patch
import yaml

import mathformer as hub
from rfde_route_tools import ACTION, ROUTE, selected_match, checked_registry
from rfde_route_boundary import install_hub
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute, ExecutionRejected

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_rfde_evaluate_workflow/workflow.yaml"
AUTHORED = (
    "skills/control/workflow-contract-validator/references/rfde-route.workflow.json"
)
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
NATIVE = hub.build_registry()
REGISTRY = {ACTION: hub.action_to_dict(NATIVE[ACTION])}
route = next(row for row in hub.build_intent_routes() if row.route_id == ROUTE)
MATCH = {
    "route": json.loads(json.dumps(asdict(route))),
    "score": 19,
    "matched_terms": ["reference-free"],
}


def original():
    scope = dict(vars(hub))
    exec((FIXTURES / "rfde_route_original.py.txt").read_text(), scope)
    return scope["run_intent_match"]


def snapshot(doc):
    paths = {SCHEMA} | {r["path"] for r in doc["provenance"]["sources"]}
    values = {path: (ROOT / path).read_text() for path in paths}
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


def populate(root, modes=("pass", "pass", "pass")):
    """Canonical RFDE order and timeouts, with external compiler fixture inputs."""
    for relative in NATIVE[ACTION].required_paths:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=True)
    matrix = json.loads((ROOT / "tests/test_matrix.json").read_text())
    rows = [r for r in matrix["tests"] if r["module_family"] == "rfde"]
    assert len(rows) == len(modes) == 3
    for row, mode in zip(rows, modes):
        row["command"] = ["fixture-compiler", mode]
    # Nonselected rows must never reach the external boundary.
    rows.insert(
        1,
        {
            **deepcopy(rows[0]),
            "id": "fixture.not-selected",
            "module_family": "atp",
            "command": ["forbidden-process"],
        },
    )
    (root / "tests/test_matrix.json").write_text(
        json.dumps({"schema_version": 2, "tests": rows})
    )
    (root.parent / "boundary.json").write_text('{"outer":"delegate"}')
    return [r for r in rows if r["module_family"] == "rfde"]


def stable(value):
    """Discard only source-owned wall-clock observations for oracle comparison."""
    value = deepcopy(value)
    child = value["children"][0]
    if child.get("stdout", "").startswith("{"):
        report = json.loads(child["stdout"])
        report.pop("run_id")
        for row in report["results"]:
            row.pop("duration_seconds")
        child["stdout"] = report
    return value


class RFDERouteTests(unittest.TestCase):
    maxDiff = None

    def test_identity_generator_provenance(self):
        doc = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(doc["id"], "route_rfde_evaluate_workflow")
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
        self.assertEqual(json.loads((ROOT / AUTHORED).read_text()), doc)
        spec = importlib.util.spec_from_file_location(
            "rfde_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)
        self.assertEqual(generator.rfde_route_descriptor(), doc)
        self.assertEqual(checked_registry(REGISTRY), {ACTION: NATIVE[ACTION]})
        audit = hub.audit_control(NATIVE)
        self.assertFalse(
            {
                "scripts/rfde_route_tools.py",
                "tests/mcp/run_rfde_route_workflow_tests.py",
            }
            & set(audit["uncontrolled_entrypoints"])
        )

    def test_source_state_and_original_entrypoint(self):
        oracle = original()
        for keep in [False, True]:
            context = hub.RunContext(keep_going=keep)
            state = hub.initialize_intent_state()
            for child in [{"ok": True}, {"ok": False}, {}]:
                updated, done = hub.advance_intent_state(state, child, context, 1)
                self.assertTrue(done)
                self.assertEqual(
                    updated, {"ok": bool(child.get("ok", False)), "children": [child]}
                )
                self.assertEqual(state, {"ok": True, "children": []})
            # General source helper remains sticky and honors early stop for
            # multi-action callers; specialization does not change its behavior.
            failed, done = hub.advance_intent_state(state, {"ok": False}, context, 2)
            self.assertEqual(done, not keep)
            updated, done = hub.advance_intent_state(failed, {"ok": True}, context, 2)
            self.assertFalse(updated["ok"])
            self.assertTrue(done)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve() / "repo"
            root.mkdir()
            for mode in ["pass", "fail", "timeout", "write", "crash"]:
                results, traces = [], []
                for runner in [oracle, hub.run_intent_match]:
                    populate(root, (mode, "pass", "pass"))
                    (root / "undeclared.txt").unlink(missing_ok=True)
                    with patch.object(hub, "subprocess", hub.subprocess):
                        process = install_hub(hub, root)
                        if mode == "crash":
                            with self.assertRaisesRegex(
                                OSError, "compiler launch failed"
                            ):
                                runner(
                                    selected_match(MATCH),
                                    checked_registry(REGISTRY),
                                    hub.RunContext(),
                                    repository_root=root,
                                )
                        else:
                            results.append(
                                stable(
                                    runner(
                                        selected_match(MATCH),
                                        checked_registry(REGISTRY),
                                        hub.RunContext(),
                                        repository_root=root,
                                    )
                                )
                            )
                        traces.append(process.calls)
                self.assertEqual(*traces)
                self.assertEqual(len(traces[0]), 1)
                if results:
                    self.assertEqual(*results)
                    self.assertEqual(results[0]["ok"], mode == "pass")
                    self.assertEqual(
                        len(results[0]["children"][0]["stdout"]["results"]), 3
                    )

    def test_actual_registered_service_policy(self):
        async def run():
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
                            "mathformer_rfde_route_execute_action", args
                        )

        asyncio.run(run())

    def test_real_mcp_lunar_prism(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        doc = yaml.safe_load(CONTRACT.read_text())
        oracle = original()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve() / "repo"
            root.mkdir()
            startup = (
                "import sys;sys.dont_write_bytecode=True;sys.path[:0]="
                + repr([str(ROOT / "scripts"), str(FIXTURES), str(ROOT), *SITES])
                + ";from rfde_route_boundary import serve;serve("
                + repr(str(root))
                + ")"
            )
            manager = SessionManager()
            failure = None
            async with manager.open(
                "rfde-route",
                StdioConfig(
                    command=sys.executable, args=["-c", startup], cwd=str(ROOT)
                ),
                {},
            ) as remote:
                try:
                    tools = [
                        t.model_dump(by_alias=True, exclude_none=True)
                        for t in await remote.tools()
                    ]

                    def compile_document(document, inventory=tools):
                        assets = snapshot(document)
                        workflow = compile_workflow(
                            "mcp:rfde-route",
                            workflow_documents([DESCRIPTOR], assets)[0],
                            inventory,
                        )
                        return workflow, assets

                    workflow, assets = compile_document(doc)
                    self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                    self.assertTrue(workflow["prism_source"])
                    self.assertTrue(workflow["runtime_source"])
                    self.assertEqual(set(workflow["bindings"]), set(doc["operations"]))
                    self.assertFalse(compile_document(doc, [])[0]["runnable"])
                    advertised = {t["name"]: t for t in tools}
                    for op in doc["operations"].values():
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

                    async def run(inputs, document=doc):
                        w, a = (
                            (workflow, assets)
                            if document is doc
                            else compile_document(document)
                        )
                        self.assertTrue(w["runnable"], w["diagnostics"])
                        return await execute(w, a, inputs, remote, authorize)

                    inputs = dict(
                        match=MATCH,
                        registry=REGISTRY,
                        context=vars(hub.RunContext()),
                        repository_root=str(root),
                    )
                    expected_calls = [
                        "initialize",
                        "select_action",
                        "execute_action",
                        "advance",
                        "finish",
                    ]
                    # Both missing-path preflight and ready dry-run return
                    # without touching even the substituted process boundary.
                    for ready in [False, True]:
                        if ready:
                            populate(root)
                        for dry in [True] if ready else [False, True]:
                            inputs["context"]["dry_run"] = dry
                            result = await run(inputs)
                            expected = oracle(
                                selected_match(MATCH),
                                checked_registry(REGISTRY),
                                hub.RunContext(**inputs["context"]),
                                repository_root=root,
                            )
                            self.assertEqual(result["status"], "accepted", result)
                            self.assertEqual(result["outputs"], {"result": expected})
                            self.assertEqual(
                                [c["operation"] for c in result["calls"]],
                                expected_calls,
                            )
                            self.assertFalse((Path(tmp) / "delegate.jsonl").exists())
                    self.assertFalse((root / "artifacts").exists())
                    inputs["context"]["dry_run"] = False
                    for mode in ["pass", "fail", "timeout", "write", "large", "crash"]:
                        for keep in [False, True]:
                            rows = populate(root, (mode, "pass", "pass"))
                            (root / "undeclared.txt").unlink(missing_ok=True)
                            for name in ["delegate.jsonl", "repo-compiler.jsonl"]:
                                (Path(tmp) / name).unlink(missing_ok=True)
                            inputs["context"]["keep_going"] = keep
                            result = await run(inputs)
                            self.assertEqual(
                                len(
                                    (Path(tmp) / "delegate.jsonl")
                                    .read_text()
                                    .splitlines()
                                ),
                                1,
                            )
                            ledger = [
                                json.loads(s)
                                for s in (Path(tmp) / "repo-compiler.jsonl")
                                .read_text()
                                .splitlines()
                            ]
                            self.assertEqual(
                                ledger,
                                [
                                    dict(
                                        command=r["command"],
                                        timeout=r["timeout_seconds"],
                                    )
                                    for r in rows[: 1 if mode == "crash" else 3]
                                ],
                            )
                            self.assertEqual(
                                [r["timeout_seconds"] for r in rows], [180, 240, 120]
                            )
                            if mode == "crash":
                                self.assertEqual(result["status"], "failed", result)
                                self.assertIsNone(result["outputs"])
                                self.assertEqual(
                                    [c["operation"] for c in result["calls"]],
                                    expected_calls[:3],
                                )
                                continue
                            self.assertEqual(result["status"], "accepted", result)
                            output = result["outputs"]["result"]
                            self.assertEqual(
                                [c["operation"] for c in result["calls"]],
                                expected_calls,
                            )
                            self.assertEqual(len(output["children"]), 1)
                            self.assertEqual(output["ok"], mode in ["pass", "large"])
                            child = output["children"][0]
                            self.assertEqual(
                                child["returncode"], 0 if output["ok"] else 3
                            )
                            report = json.loads(child["stdout"])
                            self.assertEqual(
                                [r["check_id"] for r in report["results"]],
                                [r["id"] for r in rows],
                            )
                            self.assertEqual(report["summary"]["total"], 3)
                            self.assertEqual(report["schema_errors"], [])
                            self.assertEqual(report["results"][1]["status"], "pass")
                            self.assertEqual(report["results"][2]["status"], "pass")
                            self.assertEqual(
                                json.loads(
                                    (
                                        root
                                        / "artifacts/test_program/deterministic_tests.json"
                                    ).read_text()
                                ),
                                report,
                            )
                            self.assertTrue((root / report["dependency_map"]).exists())
                            if mode == "timeout":
                                self.assertEqual(
                                    report["results"][0]["stderr"], "timeout after 180s"
                                )
                                self.assertEqual(
                                    report["results"][0]["stdout"], "partial"
                                )
                            if mode == "write":
                                self.assertEqual(child["status"], "undeclared_writes")
                                self.assertEqual(
                                    child["write_audit"]["unexpected_paths"],
                                    ["undeclared.txt"],
                                )
                            if mode == "large":
                                self.assertLess(
                                    len(report["results"][0]["stdout"]), 5000
                                )
                            self.assertTrue(result["runtime"]["effect_records"])
                            self.assertTrue(result["runtime"]["provenance"])
                            self.assertTrue(result["replay_artifacts"])
                            # Compare the frozen selected source, including its
                            # real downstream execution, on identical inputs.
                            (root / "undeclared.txt").unlink(missing_ok=True)
                            with patch.object(hub, "subprocess", hub.subprocess):
                                install_hub(hub, root)
                                expected = oracle(
                                    selected_match(MATCH),
                                    checked_registry(REGISTRY),
                                    hub.RunContext(**inputs["context"]),
                                    repository_root=root,
                                )
                            self.assertEqual(stable(output), stable(expected))
                    for outer in ["timeout", "crash"]:
                        populate(root)
                        (Path(tmp) / "boundary.json").write_text(
                            json.dumps({"outer": outer})
                        )
                        result = await run(inputs)
                        if outer == "crash":
                            self.assertEqual(result["status"], "failed")
                            self.assertEqual(
                                result["calls"][-1]["operation"], "execute_action"
                            )
                        else:
                            self.assertEqual(result["status"], "accepted", result)
                            child = result["outputs"]["result"]["children"][0]
                            self.assertEqual(
                                (
                                    child["ok"],
                                    child["status"],
                                    child["returncode"],
                                    child["timeout_seconds"],
                                ),
                                (False, "timeout", None, 900),
                            )
                            self.assertEqual(child["stdout"], "partial RFDE")
                    populate(root)
                    inputs["context"]["dry_run"] = True
                    exhausted = deepcopy(doc)
                    exhausted["flow"]["steps"][1]["until"] = {"literal": False}
                    result = await run(inputs, exhausted)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(result["failure_disposition"], "fail")
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]], expected_calls[:-1]
                    )
                    budget = deepcopy(doc)
                    budget["policy"]["limits"]["max_operation_calls"] = 4
                    result = await run(inputs, budget)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(
                        sum(
                            bool(c.get("transport_call_performed"))
                            for c in result["calls"]
                        ),
                        4,
                    )
                    result = await run({**inputs, "registry": {}})
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(result["calls"][-1]["operation"], "finish")
                    forged = deepcopy(REGISTRY)
                    forged[ACTION]["command"] = ["injected"]
                    result = await run({**inputs, "registry": forged})
                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(result["calls"][-1]["operation"], "execute_action")
                    state = (await remote.call("mathformer_rfde_route_initialize", {}))[
                        "state"
                    ]
                    for keep in [False, True]:
                        advanced = await remote.call(
                            "mathformer_rfde_route_advance",
                            dict(
                                state=state,
                                child={"ok": False},
                                action_count=1,
                                context={**inputs["context"], "keep_going": keep},
                            ),
                        )
                        self.assertEqual(
                            advanced,
                            {
                                "state": {"ok": False, "children": [{"ok": False}]},
                                "done": True,
                            },
                        )
                        with self.assertRaises(MCPConnectionError):
                            await remote.call(
                                "mathformer_rfde_route_select_action",
                                dict(state=advanced["state"], match=MATCH),
                            )
                    self.assertEqual(state, {"ok": True, "children": []})
                    # Omitted context mount uses the native repository default;
                    # dry-run prevents a production process or artifact write.
                    request = {
                        k: v for k, v in inputs.items() if k != "repository_root"
                    }
                    result = await run(request)
                    expected = oracle(
                        selected_match(MATCH),
                        checked_registry(REGISTRY),
                        hub.RunContext(**request["context"]),
                    )
                    self.assertEqual(result["outputs"], {"result": expected})
                    with self.assertRaises(ExecutionRejected):
                        await run(
                            {
                                **inputs,
                                "match": {
                                    **MATCH,
                                    "route": {
                                        "route_id": "other",
                                        "action_ids": [ACTION],
                                    },
                                },
                            }
                        )
                except Exception as error:
                    failure = error
            self.assertFalse(manager.active)
            if failure:
                raise failure


if __name__ == "__main__":
    program = unittest.main(verbosity=2, exit=False)
    result = program.result
    sys.exit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
