#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Registered MCP and real Lunar/PRISM execution with isolated process fixtures."""

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
import hashlib
import importlib.util
import io
import json
import tempfile
import types
import unittest
import yaml
from comprehensive_strict_tools import source_runner
from source_family_workflow_tools import DEFAULTS, register_source_family_tools
from source_family_boundary import install
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute, ExecutionRejected

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_test_family_source_workflow/workflow.yaml"
AUTHORED = (
    "skills/control/workflow-contract-validator/references/source-family.workflow.json"
)
ARGV = ["--module-family", "source", "--json", "--run-id", "source-fixture"]
ARGS = {**DEFAULTS, "run_id": "source-fixture"}


def matrix(modes, family="source"):
    """Input manifests in an isolated root; only compiler processes are replaced."""
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


def oracle(root):
    module = types.ModuleType("source_family_original")
    module.__file__ = str(ROOT / "tests/test_program/run_comprehensive_tests.py")
    exec(
        compile(
            (ROOT / "tests/mcp/fixtures/source_family_original.py.txt").read_text(),
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
    values = {
        r["path"]: (ROOT / r["path"]).read_text() for r in doc["provenance"]["sources"]
    }
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


class SourceFamilyTests(unittest.TestCase):
    def test_canonical_arguments_and_native_invariants(self):
        canonical = json.loads((ROOT / "tests/test_matrix.json").read_text())
        rows = [r for r in canonical["tests"] if r["module_family"] == "source"]
        self.assertEqual(len(rows), 4)
        self.assertEqual([r["timeout_seconds"] for r in rows], [120] * 4)
        self.assertTrue(all(not r.get("optional_dependency") for r in rows))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            (root / "tests").mkdir(parents=True)
            native = source_runner()
            install(native, root)
            data = matrix(["pass"])
            data["tests"][0]["command"] = ["{python}", "fixture"]
            native.MATRIX_FILE.write_text(json.dumps(data))
            args = native.parse_args(ARGV)
            state = native.prepare_checks(args)
            self.assertEqual(
                state["selected"][0]["command"], [native.PYTHON, "fixture"]
            )
            self.assertEqual(state["index"], 0)
            self.assertEqual(state["results"], [])
            self.assertEqual(state["families"], ["source"])
            with self.assertRaisesRegex(ValueError, "unconsumed"):
                native.finalize_checks(state, args)
            broken = deepcopy(state)
            broken["results"] = [{}]
            with self.assertRaisesRegex(ValueError, "cursor"):
                native.advance_check(broken, args)
            native.MATRIX_FILE.write_text(json.dumps(matrix(["pass"])))
            state = native.prepare_checks(args)
            advanced = native.advance_check(state, args)
            self.assertEqual(advanced["index"], 1)
            self.assertEqual(len(advanced["results"]), 1)
            self.assertEqual(state["results"], [])
            with self.assertRaisesRegex(ValueError, "exhausted"):
                native.advance_check(advanced, args)
            missing = matrix(["missing"])["tests"][0]
            self.assertEqual(native.run_check(missing, False)["status"], "skip")
            self.assertEqual(native.run_check(missing, True)["status"], "fail")
            # The source's early branch does not load a matrix at all.
            native.MATRIX_FILE.unlink()
            original = oracle(root)
            early = [*ARGV, "--emit-dependency-map-only"]
            self.assertEqual(
                native.run(native.parse_args(early)),
                original.run(original.parse_args(early)),
            )
            asyncio.run(self.policy_and_snapshot(root, native, original))

    async def policy_and_snapshot(self, root, native, original):
        from mcp.server.fastmcp import FastMCP

        for authorization, allowed in [
            (
                lambda: (_ for _ in ()).throw(PermissionError("readonly")),
                lambda p: True,
            ),
            (lambda: None, lambda p: False),
        ]:
            registry = FastMCP("policy-fixture")
            register_source_family_tools(registry, authorization, allowed)
            with self.assertRaisesRegex(Exception, "readonly|write roots"):
                await registry.call_tool(
                    "mathformer_source_family_enter", {"args": ARGS}
                )
        enabled = [True]

        def authorize():
            if not enabled[0]:
                raise PermissionError("readonly")

        registry = FastMCP("phase-policy")
        register_source_family_tools(registry, authorize)
        entered = (
            await registry.call_tool("mathformer_source_family_enter", {"args": ARGS})
        )[1]
        enabled[0] = False
        with self.assertRaisesRegex(Exception, "readonly"):
            await registry.call_tool(
                "mathformer_source_family_prepare",
                dict(args=ARGS, matrix=matrix(["pass"]), context=entered["context"]),
            )
        enabled[0] = True
        early_args = {**ARGS, "emit_dependency_map_only": True}
        entered = (
            await registry.call_tool(
                "mathformer_source_family_enter", {"args": early_args}
            )
        )[1]
        self.assertTrue(entered["snapshot_only"])
        ports = dict(args=early_args, context=entered["context"])
        report = (await registry.call_tool("mathformer_source_family_snapshot", ports))[
            1
        ]["report"]
        published = (
            await registry.call_tool(
                "mathformer_source_family_publish", dict(**ports, report=report)
            )
        )[1]
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = original.main([*ARGV, "--emit-dependency-map-only"])
        self.assertEqual(code, published["exit_code"])
        self.assertEqual(json.loads(stream.getvalue()), report)
        self.assertEqual(json.loads(published["publication"]["stdout"]), report)
        self.assertFalse(native.MATRIX_FILE.exists())

    def test_registered_lunar_prism_execution(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        doc = yaml.safe_load(Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text())
        self.assertEqual(doc["id"], "hub_test_family_source_workflow")
        self.assertEqual(doc["lifecycle"], "active")
        self.assertEqual(doc, json.loads((ROOT / AUTHORED).read_text()))
        self.assertEqual(
            doc["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 16},
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
            "source_family_normalizer", location
        )
        normalizer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(normalizer)
        self.assertEqual(normalizer.source_family_descriptor(), doc)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            (root / "tests").mkdir(parents=True)
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
                + ";from source_family_boundary import serve;serve("
                + repr(str(root))
                + ")"
            )
            manager = SessionManager()
            failure = None
            async with manager.open(
                "source-family",
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
                                "mcp:source-family",
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
                        data, document=doc, args=ARGS, supplied=None, blocked_file=None
                    ):
                        path.write_text(json.dumps(data))
                        (root / "undeclared.txt").unlink(missing_ok=True)
                        for name in ("deterministic_tests.json", "dependency_map.json"):
                            (root / "artifacts/test_program" / name).unlink(
                                missing_ok=True
                            )
                        (Path(tmp) / "repo-compiler.jsonl").unlink(missing_ok=True)
                        w, a = compiled(document)
                        self.assertTrue(w["runnable"], w["diagnostics"])
                        blocker = (
                            root / "artifacts/test_program" / blocked_file
                            if blocked_file
                            else None
                        )
                        if blocker:
                            blocker.mkdir(parents=True)
                        try:
                            return await execute(
                                w,
                                a,
                                {
                                    "args": args,
                                    "matrix": data if supplied is None else supplied,
                                },
                                remote,
                                authorize,
                            )
                        finally:
                            if blocker:
                                blocker.rmdir()

                    mixed = matrix(["pass", "fail", "pass"])
                    mixed["tests"][1]["module_family"] = "atp"
                    bad = matrix(["fail", "timeout", "write"])
                    expected_exit = matrix(["large", "fail", "pass"])
                    expected_exit["tests"][1]["expected_exit"] = 7
                    del expected_exit["tests"][2]["timeout_seconds"]
                    for data in [
                        matrix(["pass"] * 4),
                        bad,
                        matrix(["pass"], "atp"),
                        mixed,
                        matrix(["missing"]),
                        expected_exit,
                    ]:
                        result = await run(data)
                        self.assertEqual(result["status"], "accepted", result)
                        report = result["outputs"]["report"]
                        rows = [
                            r for r in data["tests"] if r["module_family"] == "source"
                        ]
                        self.assertEqual(
                            [r["check_id"] for r in report["results"]],
                            [r["id"] for r in rows],
                        )
                        self.assertEqual(
                            [c["operation"] for c in result["calls"][:3]],
                            ["enter", "prepare", "pending"],
                        )
                        self.assertEqual(
                            [c["operation"] for c in result["calls"][-2:]],
                            ["finalize", "publish"],
                        )
                        self.assertEqual(
                            len(result["calls"]), 5 + 2 * len(rows) if rows else 6
                        )
                        self.assertEqual(report["summary"]["total"], len(rows))
                        self.assertEqual(report["schema_errors"], [])
                        self.assertTrue((root / report["dependency_map"]).exists())
                        publication = result["outputs"]["publication"]
                        self.assertEqual(json.loads(publication["stdout"]), report)
                        self.assertEqual(
                            json.loads(Path(publication["report_path"]).read_text()),
                            report,
                        )
                        self.assertEqual(
                            result["outputs"]["exit_code"], 0 if report["ok"] else 3
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
                        executed = [r for r in rows if "optional_dependency" not in r]
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
                                [r["status"] for r in report["results"]], ["fail"] * 3
                            )
                            self.assertEqual(
                                report["results"][1]["stderr"], "timeout after 31s"
                            )
                            self.assertEqual(report["results"][1]["stdout"], "partial")
                            self.assertFalse(report["results"][2]["write_audit"]["ok"])
                            self.assertEqual(
                                report["capability_ledger"]["families"]["source"][
                                    "state"
                                ],
                                "executed_with_failures",
                            )
                        if not rows:
                            self.assertEqual(
                                report["capability_ledger"]["families"]["source"][
                                    "state"
                                ],
                                "untested",
                            )
                        if data == matrix(["missing"]):
                            self.assertEqual(
                                report["capability_ledger"]["families"]["source"][
                                    "state"
                                ],
                                "skipped",
                            )
                            self.assertFalse(
                                report["capability_ledger"]["strict_ready"]
                            )
                        if data == expected_exit:
                            self.assertTrue(report["ok"])
                            self.assertEqual(report["results"][1]["returncode"], 7)
                            self.assertLess(len(report["results"][0]["stdout"]), 5000)
                        # Full original main()/publication comparison except elapsed time.
                        (root / "undeclared.txt").unlink(missing_ok=True)
                        stream = io.StringIO()
                        with redirect_stdout(stream):
                            code = original.main(ARGV)
                        self.assertEqual(code, result["outputs"]["exit_code"])
                        self.assertEqual(
                            stable(json.loads(stream.getvalue())), stable(report)
                        )
                    exhausted = deepcopy(doc)
                    exhausted["flow"]["steps"][3]["max_iterations"] = 1
                    result = await run(matrix(["pass", "pass"]), exhausted)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(result["failure_disposition"], "fail")
                    self.assertEqual(
                        sum(c["operation"] == "advance" for c in result["calls"]), 1
                    )
                    self.assertFalse(
                        any(c["operation"] == "finalize" for c in result["calls"])
                    )
                    self.assertFalse(
                        (
                            root / "artifacts/test_program/deterministic_tests.json"
                        ).exists()
                    )
                    # Input admission never silently truncates four selected rows.
                    for data in [
                        matrix(["pass"] * 5),
                        matrix([]),
                        {**matrix(["pass"]), "schema_version": 1},
                    ]:
                        with self.assertRaises(ExecutionRejected):
                            await run(data)
                        self.assertFalse((Path(tmp) / "repo-compiler.jsonl").exists())
                    result = await run(matrix(["pass"]), supplied=matrix(["fail"]))
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]], ["enter", "prepare"]
                    )
                    self.assertFalse((Path(tmp) / "repo-compiler.jsonl").exists())
                    result = await run(matrix(["crash", "pass"]))
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertFalse(
                        any(c["operation"] == "finalize" for c in result["calls"])
                    )
                    self.assertEqual(
                        len(
                            (Path(tmp) / "repo-compiler.jsonl").read_text().splitlines()
                        ),
                        1,
                    )
                    for file, phase in [
                        ("dependency_map.json", "finalize"),
                        ("deterministic_tests.json", "publish"),
                    ]:
                        result = await run(matrix(["pass"]), blocked_file=file)
                        self.assertEqual(result["status"], "failed", result)
                        self.assertIsNone(result["outputs"])
                        self.assertEqual(result["calls"][-1]["operation"], phase)
                        self.assertFalse(
                            (
                                root / "artifacts/test_program/deterministic_tests.json"
                            ).exists()
                        )
                    with self.assertRaises(ExecutionRejected):
                        await run(matrix(["pass"]), args={**ARGS, "profile": "strict"})
                    budget = deepcopy(doc)
                    budget["policy"]["limits"]["max_operation_calls"] = 3
                    result = await run(matrix(["pass"]), budget)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(
                        sum(
                            bool(c.get("transport_call_performed"))
                            for c in result["calls"]
                        ),
                        3,
                    )
                    await self.assert_owned_ports(remote, path)
                except Exception as error:
                    failure = error
            self.assertFalse(manager.active)
            if failure:
                raise failure

    async def assert_owned_ports(self, remote, path):
        data = matrix(["pass"])
        path.write_text(json.dumps(data))
        entered = await remote.call("mathformer_source_family_enter", {"args": ARGS})
        self.assertFalse(entered["snapshot_only"])
        ports = dict(args=ARGS, context=entered["context"])
        with self.assertRaises(MCPConnectionError):
            await remote.call("mathformer_source_family_snapshot", ports)
        prepared = await remote.call(
            "mathformer_source_family_prepare", dict(**ports, matrix=data)
        )
        state = prepared["state"]
        with self.assertRaises(MCPConnectionError):
            await remote.call(
                "mathformer_source_family_finalize", dict(**ports, state=state)
            )
        self.assertTrue(
            (
                await remote.call(
                    "mathformer_source_family_pending",
                    dict(state=state, context=ports["context"]),
                )
            )["pending"]
        )
        forged = deepcopy(state)
        forged["selected"][0]["command"] = ["injected"]
        with self.assertRaises(MCPConnectionError):
            await remote.call(
                "mathformer_source_family_advance", dict(**ports, state=forged)
            )
        with self.assertRaises(MCPConnectionError):
            await remote.call(
                "mathformer_source_family_advance",
                dict(
                    args={**ARGS, "profile": "strict"},
                    context=ports["context"],
                    state=state,
                ),
            )
        updated = (
            await remote.call(
                "mathformer_source_family_advance", dict(**ports, state=state)
            )
        )["state"]
        self.assertEqual(updated["index"], 1)
        for key in ("matrix", "selected", "families"):
            self.assertEqual(updated[key], state[key])
        self.assertEqual(len(updated["results"]), 1)
        with self.assertRaises(MCPConnectionError):
            await remote.call(
                "mathformer_source_family_advance", dict(**ports, state=state)
            )
        self.assertFalse(
            (
                await remote.call(
                    "mathformer_source_family_pending",
                    dict(state=updated, context=ports["context"]),
                )
            )["pending"]
        )
        report = (
            await remote.call(
                "mathformer_source_family_finalize", dict(**ports, state=updated)
            )
        )["report"]
        with self.assertRaises(MCPConnectionError):
            await remote.call(
                "mathformer_source_family_publish",
                dict(**ports, report={**report, "ok": False}),
            )
        self.assertEqual(
            (
                await remote.call(
                    "mathformer_source_family_publish", dict(**ports, report=report)
                )
            )["exit_code"],
            0,
        )
        with self.assertRaises(MCPConnectionError):
            await remote.call(
                "mathformer_source_family_publish", dict(**ports, report=report)
            )
        # The tool's own selection bound also protects direct MCP callers.
        data = matrix(["pass"] * 5)
        path.write_text(json.dumps(data))
        entered = await remote.call("mathformer_source_family_enter", {"args": ARGS})
        with self.assertRaises(MCPConnectionError):
            await remote.call(
                "mathformer_source_family_prepare",
                dict(args=ARGS, matrix=data, context=entered["context"]),
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
