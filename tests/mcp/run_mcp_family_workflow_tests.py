#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Real registered MCP ports and Lunar/PRISM execution, without live backends."""

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
from mcp_family_workflow_tools import INVOCATION, register_mcp_family_tools
from mcp_family_boundary import install
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute, ExecutionRejected

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_test_family_mcp_workflow/workflow.yaml"
AUTHORED = (
    "skills/control/workflow-contract-validator/references/mcp-family.workflow.json"
)
ARGV = ["--module-family", "mcp", "--json"]


def matrix(modes, family="mcp"):
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
    module = types.ModuleType("mcp_family_original")
    module.__file__ = str(ROOT / "tests/test_program/run_comprehensive_tests.py")
    exec(
        compile(
            (ROOT / "tests/mcp/fixtures/mcp_family_original.py.txt").read_text(),
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
        p: (ROOT / p).read_text()
        for p in {r["path"] for r in doc["provenance"]["sources"]}
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


class MCPFamilyTests(unittest.TestCase):
    def test_native_invariants_and_original_early_return(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            (root / "tests").mkdir(parents=True)
            native = source_runner()
            install(native, root)
            native.MATRIX_FILE.write_text(json.dumps(matrix(["pass"])))
            args = native.parse_args([*ARGV, "--run-id", "fixture"])
            state = native.prepare_checks(args)
            self.assertEqual(state["index"], 0)
            self.assertEqual(state["results"], [])
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
            native.MATRIX_FILE.unlink()
            original = oracle(root)
            early = [*ARGV, "--emit-dependency-map-only", "--run-id", "fixture"]
            self.assertEqual(
                native.run(native.parse_args(early)),
                original.run(original.parse_args(early)),
            )
            # Both service checks happen before the native artifact write.
            from mcp.server.fastmcp import FastMCP

            async def check_policy():
                for authorization, allowed in [
                    (
                        lambda: (_ for _ in ()).throw(PermissionError("readonly")),
                        lambda p: True,
                    ),
                    (lambda: None, lambda p: False),
                ]:
                    registry = FastMCP("policy-fixture")
                    register_mcp_family_tools(registry, authorization, allowed)
                    tool = (await registry.list_tools())[0]
                    self.assertEqual(tool.name, "mathformer_mcp_family_enter")
                    with self.assertRaises(Exception) as error:
                        await registry.call_tool(tool.name, {"invocation": INVOCATION})
                    self.assertRegex(str(error.exception), "readonly|write roots")

            asyncio.run(check_policy())

    def test_registered_lunar_prism_execution(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        doc = yaml.safe_load(Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text())
        self.assertEqual(doc["id"], "hub_test_family_mcp_workflow")
        self.assertEqual(doc["lifecycle"], "active")
        self.assertEqual(doc, json.loads((ROOT / AUTHORED).read_text()))
        for row in doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        # Exercise the native generator without writing YAML or the host catalog.
        location = (
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py"
        )
        spec = importlib.util.spec_from_file_location("mcp_family_normalizer", location)
        normalizer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(normalizer)
        self.assertEqual(
            next(d for d in normalizer.inventory() if d["id"] == doc["id"]), doc
        )
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
                + ";from mcp_family_boundary import serve;serve("
                + repr(str(root))
                + ")"
            )
            manager = SessionManager()
            failure = None
            async with manager.open(
                "mcp-family",
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
                                "mcp:mcp-family",
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

                    async def run(data, document=doc, invocation=INVOCATION):
                        path.write_text(json.dumps(data))
                        (root / "undeclared.txt").unlink(missing_ok=True)
                        for name in ("deterministic_tests.json", "dependency_map.json"):
                            (root / "artifacts/test_program" / name).unlink(
                                missing_ok=True
                            )
                        (Path(tmp) / "repo-compiler.jsonl").unlink(missing_ok=True)
                        w, a = compiled(document)
                        self.assertTrue(w["runnable"], w["diagnostics"])
                        return await execute(
                            w, a, {"invocation": invocation}, remote, authorize
                        )

                    mixed = matrix(["pass", "fail", "pass"])
                    mixed["tests"][1]["module_family"] = "atp"
                    bad = matrix(
                        ["fail", "timeout", "write", "missing", "large", "pass", "fail"]
                    )
                    bad["tests"][-1]["expected_exit"] = 7
                    del bad["tests"][-1]["timeout_seconds"]  # native fallback 120
                    for data in [
                        matrix(["pass"] * 97),
                        bad,
                        matrix(["pass"], "atp"),
                        mixed,
                        matrix(["missing"]),
                    ]:
                        result = await run(data)
                        self.assertEqual(result["status"], "accepted", result)
                        report = result["outputs"]["report"]
                        expected_rows = [
                            r for r in data["tests"] if r["module_family"] == "mcp"
                        ]
                        self.assertEqual(
                            [r["check_id"] for r in report["results"]],
                            [r["id"] for r in expected_rows],
                        )
                        self.assertEqual(
                            [c["operation"] for c in result["calls"][:3]],
                            ["enter", "prepare", "cursor_guard"],
                        )
                        self.assertEqual(
                            [c["operation"] for c in result["calls"][-2:]],
                            ["finalize", "publish"],
                        )
                        self.assertEqual(
                            len(result["calls"]),
                            5 + 2 * len(expected_rows) if expected_rows else 6,
                        )
                        self.assertEqual(report["summary"]["total"], len(expected_rows))
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
                            self.assertLess(len(report["results"][4]["stdout"]), 5000)
                            self.assertEqual(
                                report["capability_ledger"]["families"]["mcp"]["state"],
                                "executed_with_failures",
                            )
                        if not expected_rows:
                            self.assertEqual(
                                report["capability_ledger"]["families"]["mcp"]["state"],
                                "untested",
                            )
                        if data == matrix(["missing"]):
                            self.assertEqual(
                                report["capability_ledger"]["families"]["mcp"]["state"],
                                "skipped",
                            )
                            self.assertFalse(
                                report["capability_ledger"]["strict_ready"]
                            )
                        # Compare full original CLI reports except elapsed time.
                        (root / "undeclared.txt").unlink(missing_ok=True)
                        stream = io.StringIO()
                        with redirect_stdout(stream):
                            code = original.main([*ARGV, "--run-id", report["run_id"]])
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
                    # Admission is distinct from native bounds; no truncated run.
                    for data in [
                        matrix(["pass"] * 98),
                        matrix([]),
                        {**matrix(["pass"]), "schema_version": 1},
                        {"schema_version": 2, "tests": ["bad row"]},
                    ]:
                        result = await run(data)
                        self.assertEqual(result["status"], "failed", result)
                        self.assertIsNone(result["outputs"])
                        self.assertEqual(len(result["calls"]), 2)
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
                    with self.assertRaises(ExecutionRejected):
                        await run(
                            matrix(["pass"]),
                            invocation={**INVOCATION, "profile": "strict"},
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
                    # Actual advertised tools reject replay, state/command injection,
                    # out-of-order calls, invocation changes and report mutation.
                    path.write_text(json.dumps(matrix(["pass"])))
                    context = (
                        await remote.call(
                            "mathformer_mcp_family_enter", {"invocation": INVOCATION}
                        )
                    )["context"]
                    ports = dict(invocation=INVOCATION, context=context)
                    state = (await remote.call("mathformer_mcp_family_prepare", ports))[
                        "state"
                    ]
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_mcp_family_finalize", dict(**ports, state=state)
                        )
                    self.assertTrue(
                        (
                            await remote.call(
                                "mathformer_mcp_family_cursor_guard",
                                dict(state=state, context=context),
                            )
                        )["pending"]
                    )
                    forged = deepcopy(state)
                    forged["selected"][0]["command"] = ["injected"]
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_mcp_family_advance", dict(**ports, state=forged)
                        )
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_mcp_family_advance",
                            dict(
                                invocation={**INVOCATION, "profile": "strict"},
                                context=context,
                                state=state,
                            ),
                        )
                    updated = (
                        await remote.call(
                            "mathformer_mcp_family_advance", dict(**ports, state=state)
                        )
                    )["state"]
                    self.assertEqual(updated["index"], 1)
                    self.assertEqual(updated["matrix"], state["matrix"])
                    self.assertEqual(updated["selected"], state["selected"])
                    self.assertEqual(updated["families"], state["families"])
                    self.assertEqual(len(updated["results"]), 1)
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_mcp_family_advance", dict(**ports, state=state)
                        )
                    self.assertFalse(
                        (
                            await remote.call(
                                "mathformer_mcp_family_cursor_guard",
                                dict(state=updated, context=context),
                            )
                        )["pending"]
                    )
                    report = (
                        await remote.call(
                            "mathformer_mcp_family_finalize",
                            dict(**ports, state=updated),
                        )
                    )["report"]
                    forged = {**report, "ok": False}
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_mcp_family_publish",
                            dict(**ports, report=forged),
                        )
                    published = await remote.call(
                        "mathformer_mcp_family_publish", dict(**ports, report=report)
                    )
                    self.assertEqual(published["exit_code"], 0)
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_mcp_family_publish",
                            dict(**ports, report=report),
                        )
                except Exception as error:
                    failure = error
            self.assertFalse(manager.active)
            if failure:
                raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
