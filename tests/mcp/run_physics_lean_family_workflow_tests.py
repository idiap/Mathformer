#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Real registered MCP, Lunar and PRISM execution; no live scientific backends."""

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
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT),
    str(ROOT / "tests/mcp/fixtures"),
]
SITES = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
sys.path.extend(SITES)
import asyncio
from contextlib import redirect_stdout
from copy import deepcopy
from dataclasses import replace
from functools import partial
import hashlib
import importlib.util
import io
import json
import tempfile
import types
import unittest
import yaml
import mathformer as hub
import physics_lean_family_tools as ports
from comprehensive_strict_tools import source_runner
from physics_lean_family_boundary import install, worker
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute, ExecutionRejected

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_test_family_physics_lean_workflow/workflow.yaml"
AUTHORED = "skills/control/workflow-contract-validator/references/physics-lean-family.workflow.json"
INTERFACE = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
ARGV = ["--module-family", "physics_lean", "--json"]
CONTEXT = dict(
    dry_run=False,
    json_output=False,
    keep_going=False,
    allow_mutating=False,
    write_report=False,
)


def matrix(modes, family="physics_lean"):
    return {
        "schema_version": 2,
        "tests": [
            dict(
                id=f"fixture.{i}",
                module_family=family,
                command=["fixture-compiler", mode],
                owner_skill="fixture",
                hook_id="test.fixture",
                fixture_ids=["compiler"],
                test_kind="regression",
                risk_level="low",
                timeout_seconds=30 + i,
                expected_exit=0,
                write_set=[],
                **(
                    {"optional_dependency": "fixture_missing_provider"}
                    if mode == "missing"
                    else {}
                ),
            )
            for i, mode in enumerate(modes)
        ],
    }


def initialize(root, data):
    (root / "tests/test_program").mkdir(parents=True, exist_ok=True)
    (root / "tests/test_program/run_comprehensive_tests.py").write_text(
        "# source path preflight fixture\n"
    )
    (root / "tests/test_matrix.json").write_text(json.dumps(data))


def oracle(root):
    module = types.ModuleType("physics_lean_family_original")
    module.__file__ = str(ROOT / "tests/test_program/run_comprehensive_tests.py")
    exec(
        compile(
            (
                ROOT / "tests/mcp/fixtures/physics_lean_family_original.py.txt"
            ).read_text(),
            module.__file__,
            "exec",
        ),
        module.__dict__,
    )
    install(module, root)
    return module


def stable(report):
    report = deepcopy(report)
    for row in report["results"]:
        row.pop("duration_seconds")
    return report


def snapshot(doc):
    paths = {r["path"] for r in doc["provenance"]["sources"]} | {INTERFACE}
    values = {p: (ROOT / p).read_text() for p in paths}
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


class PhysicsLeanFamilyTests(unittest.TestCase):
    def test_native_source_invariants_and_original_entrypoint(self):
        canonical = json.loads((ROOT / "tests/test_matrix.json").read_text())
        rows = [r for r in canonical["tests"] if r["module_family"] == "physics_lean"]
        self.assertEqual(len(rows), 11)
        self.assertEqual(
            hashlib.sha256((ROOT / ports.SCOPE["matrix"]).read_bytes()).hexdigest(),
            ports.SCOPE["sha256"],
        )
        self.assertTrue(all(30 <= r["timeout_seconds"] <= 180 for r in rows))
        self.assertTrue(all(not r.get("optional_dependency") for r in rows))
        item = hub.build_registry()[ports.ACTION]
        self.assertEqual(
            item.command,
            (
                "{python}",
                "tests/test_program/run_comprehensive_tests.py",
                "--module-family",
                "physics_lean",
                "--json",
            ),
        )
        self.assertEqual(item.timeout_seconds, 900)
        self.assertEqual(item.depends_on, ())
        self.assertFalse(item.allows_extra_args)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            initialize(root, matrix(["pass"]))
            native = source_runner()
            install(native, root)
            args = native.parse_args([*ARGV, "--run-id", "fixture"])
            native.enter_checks(args)
            state = native.prepare_checks(args)
            self.assertEqual(state["index"], 0)
            self.assertEqual(state["results"], [])
            self.assertEqual(state["families"], ["physics_lean"])
            with self.assertRaisesRegex(ValueError, "unconsumed"):
                native.finalize_checks(state, args)
            broken = deepcopy(state)
            broken["results"] = [{}]
            with self.assertRaisesRegex(ValueError, "cursor"):
                native.advance_check(broken, args)
            advanced = native.advance_check(state, args)
            self.assertEqual(advanced["index"], 1)
            self.assertEqual(len(advanced["results"]), 1)
            self.assertEqual(state["results"], [])
            with self.assertRaisesRegex(ValueError, "exhausted"):
                native.advance_check(advanced, args)
            missing = matrix(["missing"])["tests"][0]
            self.assertEqual(native.run_check(missing, False)["status"], "skip")
            self.assertEqual(native.run_check(missing, True)["status"], "fail")
            original = oracle(root)
            early = [*ARGV, "--emit-dependency-map-only", "--run-id", "fixture"]
            native.MATRIX_FILE.unlink()
            self.assertEqual(
                native.run(native.parse_args(early)),
                original.run(original.parse_args(early)),
            )

    def test_authorization_and_real_process_deadline(self):
        from mcp.server.fastmcp import FastMCP

        async def policy(root):
            native = source_runner()
            install(native, root)
            for authorization, allowed in [
                (
                    lambda: (_ for _ in ()).throw(PermissionError("readonly")),
                    lambda p: True,
                ),
                (lambda: None, lambda p: False),
            ]:
                registry = FastMCP("policy-fixture")
                service = ports.register_physics_lean_family_tools(
                    registry, authorization, allowed
                )
                try:
                    with self.assertRaisesRegex(Exception, "readonly|write roots"):
                        await registry.call_tool(
                            "mathformer_physics_lean_family_prepare_boundary",
                            dict(context=CONTEXT, extra_args=[]),
                        )
                    self.assertFalse(service.sessions)
                finally:
                    service.close()
            enabled = [True]

            def authorize():
                if not enabled[0]:
                    raise PermissionError("readonly")

            service = ports.PhysicsLeanFamilyTools(authorize)
            boundary = service.call(
                "prepare_boundary", dict(context=CONTEXT, extra_args=[])
            )
            enabled[0] = False
            with self.assertRaisesRegex(PermissionError, "readonly"):
                service.call(
                    "prepare_checks",
                    dict(
                        scope=ports.SCOPE,
                        boundary=boundary["boundary"],
                        runtime=boundary["runtime"],
                    ),
                )
            enabled[0] = True
            service.close()
            # Test the actual supervisor timer against a blocking external compiler.
            # A short test item exercises the same implementation as the 900s item.
            original_worker = ports._worker
            ports._worker = partial(worker, root=str(root))
            service = ports.PhysicsLeanFamilyTools()
            try:
                item = replace(hub.build_registry()[ports.ACTION], timeout_seconds=2)
                boundary = hub.prepare_leaf_boundary(
                    item, hub.RunContext(**CONTEXT), [], repository_root=root
                )
                scope = dict(item=item, native=boundary, root=root)
                service.sessions["deadline"] = scope
                service.start(scope)
                self.assertIsNotNone(service.receive(scope, "prepare_checks"))
                self.assertTrue(service.receive(scope, "checks_pending"))
                self.assertIsNone(service.receive(scope, "advance_check"))
                self.assertEqual(
                    scope["terminal"], dict(status="timeout", returncode=None)
                )
                scope["process"].join(timeout=2)
                self.assertFalse(scope["process"].is_alive())
                result = service.finish("deadline", scope)["result"]
                self.assertEqual(result["status"], "timeout")
                self.assertFalse(result["ok"])
                self.assertIsNone(result["returncode"])
                self.assertEqual(result["timeout_seconds"], 2)
                self.assertEqual(result["stdout"], "")
                self.assertTrue(result["write_audit"]["ok"])
                self.assertFalse(service.sessions)
            finally:
                service.close()
                ports._worker = original_worker

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            initialize(root, matrix(["hang"]))
            asyncio.run(policy(root))

    def test_registered_lunar_prism_execution(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        doc = yaml.safe_load(Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text())
        self.assertEqual(doc["id"], "hub_test_family_physics_lean_workflow")
        self.assertEqual(doc["lifecycle"], "active")
        self.assertEqual(doc, json.loads((ROOT / AUTHORED).read_text()))
        self.assertEqual(
            doc["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 27},
        )
        self.assertIn(
            "tests/test_program/run_comprehensive_tests.py",
            [r["path"] for r in doc["provenance"]["sources"]],
        )
        for row in doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        location = (
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py"
        )
        spec = importlib.util.spec_from_file_location(
            "physics_lean_family_normalizer", location
        )
        normalizer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(normalizer)
        self.assertEqual(
            next(d for d in normalizer.inventory() if d["id"] == doc["id"]), doc
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            initialize(root, matrix(["pass"]))
            path = root / "tests/test_matrix.json"
            original = oracle(root)
            server = (
                "import sys;sys.dont_write_bytecode=True;sys.path[:0]="
                + repr(
                    [
                        str(ROOT / "scripts"),
                        str(ROOT / "tests/mcp/fixtures"),
                        str(ROOT),
                        *SITES,
                    ]
                )
                + ";from physics_lean_family_boundary import serve;serve("
                + repr(str(root))
                + ")"
            )
            manager = SessionManager()
            failure = None
            async with manager.open(
                "physics-lean-family",
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
                        return (
                            compile_workflow(
                                "mcp:physics-lean-family",
                                workflow_documents([DESCRIPTOR], assets)[0],
                                tools if inventory is None else inventory,
                            ),
                            assets,
                        )

                    workflow, assets = compiled(doc)
                    self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                    self.assertTrue(workflow["runtime_source"])
                    self.assertEqual(set(workflow["bindings"]), set(doc["operations"]))
                    self.assertFalse(compiled(doc, [])[0]["runnable"])

                    async def authorize():
                        pass

                    async def run(
                        data,
                        document=doc,
                        context=CONTEXT,
                        extra_args=None,
                        missing=False,
                        snapshot_blocked=False,
                    ):
                        initialize(root, data)
                        if missing:
                            path.unlink()
                        (root / "undeclared.txt").unlink(missing_ok=True)
                        for name in ("deterministic_tests.json", "dependency_map.json"):
                            p = root / "artifacts/test_program" / name
                            if p.is_dir():
                                p.rmdir()
                            else:
                                p.unlink(missing_ok=True)
                        if snapshot_blocked:
                            (root / "artifacts/test_program/dependency_map.json").mkdir(
                                parents=True
                            )
                        (Path(tmp) / "repo-compiler.jsonl").unlink(missing_ok=True)
                        w, a = compiled(document)
                        self.assertTrue(w["runnable"], w["diagnostics"])
                        return await execute(
                            w,
                            a,
                            dict(
                                context=context,
                                extra_args=extra_args or [],
                                scope=ports.SCOPE,
                            ),
                            remote,
                            authorize,
                        )

                    mixed = matrix(["pass", "fail", "pass"])
                    mixed["tests"][1]["module_family"] = "atp"
                    bad = matrix(
                        ["fail", "timeout", "write", "missing", "large", "pass", "fail"]
                    )
                    bad["tests"][-1]["expected_exit"] = 7
                    del bad["tests"][-1]["timeout_seconds"]
                    for data in [
                        matrix(["pass"] * 11),
                        bad,
                        matrix(["pass"], "atp"),
                        mixed,
                        matrix(["missing"]),
                    ]:
                        result = await run(data)
                        self.assertEqual(result["status"], "accepted", result)
                        hub_result = result["outputs"]["result"]
                        report = json.loads(hub_result["stdout"])
                        expected_rows = [
                            r
                            for r in data["tests"]
                            if r["module_family"] == "physics_lean"
                        ]
                        self.assertEqual(
                            [r["check_id"] for r in report["results"]],
                            [r["id"] for r in expected_rows],
                        )
                        self.assertEqual(
                            [c["operation"] for c in result["calls"][:3]],
                            ["prepare_boundary", "prepare_checks", "checks_pending"],
                        )
                        self.assertEqual(
                            [c["operation"] for c in result["calls"][-2:]],
                            ["finalize_checks", "publish_and_audit"],
                        )
                        self.assertEqual(
                            len(result["calls"]),
                            5 + 2 * len(expected_rows) if expected_rows else 6,
                        )
                        self.assertEqual(report["summary"]["total"], len(expected_rows))
                        self.assertEqual(report["schema_errors"], [])
                        self.assertTrue((root / report["dependency_map"]).exists())
                        self.assertEqual(
                            json.loads(
                                (
                                    root
                                    / "artifacts/test_program/deterministic_tests.json"
                                ).read_text()
                            ),
                            report,
                        )
                        self.assertEqual(
                            hub_result["returncode"], 0 if report["ok"] else 3
                        )
                        self.assertEqual(
                            hub_result["ok"],
                            report["ok"] and hub_result["write_audit"]["ok"],
                        )
                        self.assertFalse(
                            (
                                root
                                / "artifacts/test_program/deterministic_tests.jsonl"
                            ).exists()
                        )
                        self.assertFalse(
                            (
                                root / "artifacts/test_program/deterministic_tests.xml"
                            ).exists()
                        )
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["replay_artifacts"])
                        ledger_path = Path(tmp) / "repo-compiler.jsonl"
                        ledger = (
                            [
                                json.loads(s)
                                for s in ledger_path.read_text().splitlines()
                            ]
                            if ledger_path.exists()
                            else []
                        )
                        executed = [
                            r for r in expected_rows if "optional_dependency" not in r
                        ]
                        self.assertEqual(
                            ledger,
                            [
                                dict(
                                    command=r["command"],
                                    timeout=r.get("timeout_seconds", 120),
                                )
                                for r in executed
                            ],
                        )
                        if data == bad:
                            self.assertEqual(
                                [r["status"] for r in report["results"]],
                                [
                                    "fail",
                                    "fail",
                                    "fail",
                                    "skip",
                                    "pass",
                                    "pass",
                                    "pass",
                                ],
                            )
                            self.assertEqual(
                                report["results"][1]["stderr"], "timeout after 31s"
                            )
                            self.assertEqual(report["results"][1]["stdout"], "partial")
                            self.assertFalse(report["results"][2]["write_audit"]["ok"])
                            self.assertEqual(hub_result["status"], "undeclared_writes")
                            self.assertIn(
                                "undeclared.txt",
                                hub_result["write_audit"]["unexpected_paths"],
                            )
                            self.assertLess(len(report["results"][4]["stdout"]), 5000)
                            self.assertEqual(
                                report["capability_ledger"]["families"]["physics_lean"][
                                    "state"
                                ],
                                "executed_with_failures",
                            )
                        if not expected_rows:
                            self.assertEqual(
                                report["capability_ledger"]["families"]["physics_lean"][
                                    "state"
                                ],
                                "untested",
                            )
                        if data == matrix(["missing"]):
                            self.assertEqual(
                                report["capability_ledger"]["families"]["physics_lean"][
                                    "state"
                                ],
                                "skipped",
                            )
                        (root / "undeclared.txt").unlink(missing_ok=True)
                        stream = io.StringIO()
                        with redirect_stdout(stream):
                            code = original.main([*ARGV, "--run-id", report["run_id"]])
                        self.assertEqual(code, hub_result["returncode"])
                        self.assertEqual(
                            stable(json.loads(stream.getvalue())), stable(report)
                        )
                    # Preflight failures precede dry-run. Neither starts a runner.
                    for context, extra, missing in [
                        ({**CONTEXT, "dry_run": True}, [], False),
                        ({**CONTEXT, "dry_run": True}, ["forbidden"], True),
                        (CONTEXT, ["forbidden"], False),
                        (CONTEXT, [], True),
                    ]:
                        result = await run(
                            matrix(["pass"]),
                            context=context,
                            extra_args=extra,
                            missing=missing,
                        )
                        self.assertEqual(result["status"], "accepted", result)
                        value = result["outputs"]["result"]
                        expected = hub.prepare_leaf_boundary(
                            hub.build_registry()[ports.ACTION],
                            hub.RunContext(**context),
                            extra,
                            repository_root=root,
                        )["payload"]
                        self.assertEqual(value, expected)
                        self.assertNotIn("write_audit", value)
                        self.assertFalse((Path(tmp) / "repo-compiler.jsonl").exists())
                        self.assertFalse(
                            (
                                root / "artifacts/test_program/deterministic_tests.json"
                            ).exists()
                        )
                    exhausted = deepcopy(doc)
                    exhausted["flow"]["steps"][2]["max_iterations"] = 1
                    result = await run(matrix(["pass", "pass"]), exhausted)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(result["failure_disposition"], "fail")
                    self.assertEqual(
                        sum(c["operation"] == "advance_check" for c in result["calls"]),
                        1,
                    )
                    self.assertFalse(
                        any(
                            c["operation"] == "finalize_checks" for c in result["calls"]
                        )
                    )
                    # Invalid input files abort the real runner; no fabricated report.
                    for data in [
                        matrix(["pass"] * 12),
                        matrix([]),
                        {**matrix(["pass"]), "schema_version": 1},
                        {"schema_version": 2, "tests": ["bad row"]},
                        matrix(["crash", "pass"]),
                    ]:
                        result = await run(data)
                        self.assertEqual(result["status"], "accepted", result)
                        value = result["outputs"]["result"]
                        self.assertFalse(value["ok"])
                        self.assertEqual(value["returncode"], 1)
                        self.assertIn("Traceback", value["stderr"])
                        self.assertEqual(value["stdout"], "")
                        self.assertTrue(value["write_audit"]["ok"])
                        self.assertFalse(
                            any(
                                c["operation"]
                                in ("finalize_checks", "publish_and_audit")
                                for c in result["calls"]
                            )
                        )
                        self.assertFalse(
                            (
                                root / "artifacts/test_program/deterministic_tests.json"
                            ).exists()
                        )
                        if data == matrix(["crash", "pass"]):
                            self.assertEqual(
                                len(
                                    (Path(tmp) / "repo-compiler.jsonl")
                                    .read_text()
                                    .splitlines()
                                ),
                                1,
                            )
                        else:
                            self.assertFalse(
                                (Path(tmp) / "repo-compiler.jsonl").exists()
                            )
                    result = await run(matrix(["pass"]), snapshot_blocked=True)
                    self.assertFalse(result["outputs"]["result"]["ok"])
                    self.assertEqual(result["outputs"]["result"]["returncode"], 1)
                    self.assertEqual(
                        [c["operation"] for c in result["calls"][-2:]],
                        ["finalize_checks", "complete_failure"],
                    )
                    self.assertFalse(
                        (
                            root / "artifacts/test_program/deterministic_tests.json"
                        ).exists()
                    )
                    budget = deepcopy(doc)
                    budget["policy"]["limits"]["max_operation_calls"] = 2
                    result = await run(matrix(["pass"]), budget)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(
                        sum(
                            bool(c.get("transport_call_performed"))
                            for c in result["calls"]
                        ),
                        2,
                    )
                    with self.assertRaises(ExecutionRejected):
                        await execute(
                            workflow,
                            assets,
                            dict(context=CONTEXT, extra_args=[], scope={}),
                            remote,
                            authorize,
                        )
                    # Assert actual MCP tools enforce owned state and invocation phases.
                    initialize(root, matrix(["pass"]))
                    entered = await remote.call(
                        "mathformer_physics_lean_family_prepare_boundary",
                        dict(context=CONTEXT, extra_args=[]),
                    )
                    args = dict(
                        boundary=entered["boundary"], runtime=entered["runtime"]
                    )
                    progress = (
                        await remote.call(
                            "mathformer_physics_lean_family_prepare_checks",
                            dict(**args, scope=ports.SCOPE),
                        )
                    )["progress"]
                    runtime = dict(runtime=entered["runtime"])
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_physics_lean_family_finalize_checks",
                            dict(**runtime, progress=progress),
                        )
                    progress = (
                        await remote.call(
                            "mathformer_physics_lean_family_checks_pending",
                            dict(**runtime, progress=progress),
                        )
                    )["progress"]
                    forged = deepcopy(progress)
                    forged["state"]["selected"][0]["command"] = ["injected"]
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_physics_lean_family_advance_check",
                            dict(**runtime, progress=forged),
                        )
                    updated = (
                        await remote.call(
                            "mathformer_physics_lean_family_advance_check",
                            dict(**runtime, progress=progress),
                        )
                    )["progress"]
                    self.assertEqual(updated["state"]["index"], 1)
                    for name in ("matrix", "selected", "families"):
                        self.assertEqual(
                            updated["state"][name], progress["state"][name]
                        )
                    self.assertEqual(len(updated["state"]["results"]), 1)
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_physics_lean_family_advance_check",
                            dict(**runtime, progress=progress),
                        )
                    updated = (
                        await remote.call(
                            "mathformer_physics_lean_family_checks_pending",
                            dict(**runtime, progress=updated),
                        )
                    )["progress"]
                    self.assertFalse(updated["pending"])
                    report = (
                        await remote.call(
                            "mathformer_physics_lean_family_finalize_checks",
                            dict(**runtime, progress=updated),
                        )
                    )["report"]
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_physics_lean_family_publish_and_audit",
                            dict(**args, report={**report, "ok": False}),
                        )
                    published = await remote.call(
                        "mathformer_physics_lean_family_publish_and_audit",
                        dict(**args, report=report),
                    )
                    self.assertEqual(published["result"]["returncode"], 0)
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_physics_lean_family_publish_and_audit",
                            dict(**args, report=report),
                        )
                except Exception as error:
                    failure = error
            self.assertFalse(manager.active)
            if failure:
                raise failure


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(PhysicsLeanFamilyTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun and not result.skipped else 1
    )
