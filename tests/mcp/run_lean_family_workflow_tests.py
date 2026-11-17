#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native Lean steps through registered MCP and real Lunar/PRISM execution.

Only external compiler and dependency discovery boundaries are substituted.
The canonical runner, schema gates, audits, ledger and publication execute for real
in a temporary repository. There are no scientific or model calls.
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
    str(ROOT),
    str(ROOT / "tests/mcp/fixtures"),
]
APPLICATION_SITES = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
sys.path.extend(APPLICATION_SITES)
import asyncio
from copy import deepcopy
import contextlib
import hashlib
import io
import json
import tempfile
import types
import unittest
import yaml
from comprehensive_workflow_boundary import install
from comprehensive_strict_tools import source_runner
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_test_family_lean_workflow/workflow.yaml"
from lean_family_workflow_tools import FIXED

DOMAIN = {"max_selected_rows": 4096}


def matrix(modes, family="lean"):
    return {
        "schema_version": 2,
        "tests": [
            {
                "id": f"fixture.{i}",
                "module_family": family,
                "command": ["fixture-compiler", mode],
                "owner_skill": "fixture",
                "hook_id": "test.fixture",
                "fixture_ids": ["deterministic-compiler"],
                "test_kind": "regression",
                "risk_level": "low",
                "timeout_seconds": [120, 120, 240, 300, 120][i % 5],
                "expected_exit": 0,
                "write_set": [],
                **(
                    {"optional_dependency": "fixture_dependency_unavailable"}
                    if mode == "missing"
                    else {}
                ),
            }
            for i, mode in enumerate(modes)
        ],
    }


def snapshot(document):
    values = {
        p: (ROOT / p).read_text()
        for p in {r["path"] for r in document["provenance"]["sources"]}
    }
    values[DESCRIPTOR] = json.dumps(document)
    return [
        {
            "path": p,
            "content": s,
            "encoding": "text",
            "sha256": hashlib.sha256(s.encode()).hexdigest(),
        }
        for p, s in values.items()
    ]


class LeanFamilyTests(unittest.TestCase):
    def test_native_cursor_invariants(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "tests").mkdir()
            native = source_runner()
            install(native, root)
            native.MATRIX_FILE.write_text(json.dumps(matrix(["pass"])))
            args = native.parse_args(["--module-family", "lean", "--json"])
            state = native.prepare_checks(args)
            with self.assertRaisesRegex(ValueError, "unconsumed"):
                native.finalize_checks(state, args)
            broken = deepcopy(state)
            broken["results"] = [{}]
            with self.assertRaisesRegex(ValueError, "cursor"):
                native.advance_check(broken, args)
            state = native.advance_check(state, args)
            with self.assertRaisesRegex(ValueError, "exhausted"):
                native.advance_check(state, args)
            missing = matrix(["missing"])["tests"][0]
            self.assertEqual(native.run_check(missing, False)["status"], "skip")
            self.assertEqual(native.run_check(missing, True)["status"], "fail")

    def test_native_bound_and_early_report(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "tests").mkdir()
            native = source_runner()
            install(native, root)
            native.MATRIX_FILE.write_text(json.dumps(matrix(["missing"] * 4096)))
            args = native.parse_args(["--module-family", "lean", "--json"])
            state = native.prepare_checks(args)
            self.assertEqual(len(state["selected"]), 4096)
            for index in range(4096):
                state = native.advance_check(state, args)
                self.assertEqual(state["index"], index + 1)
            self.assertEqual(
                native.finalize_checks(state, args)["summary"]["skip"], 4096
            )
            with self.assertRaisesRegex(ValueError, "exhausted"):
                native.advance_check(state, args)
            # Early return needs no matrix at all and still publishes normally.
            native.MATRIX_FILE.unlink()
            oracle = types.ModuleType("lean_snapshot_original")
            oracle.__file__ = str(
                ROOT / "tests/test_program/run_comprehensive_tests.py"
            )
            exec(
                compile(
                    (
                        ROOT / "tests/mcp/fixtures/lean_family_original.py.txt"
                    ).read_text(),
                    oracle.__file__,
                    "exec",
                ),
                oracle.__dict__,
            )
            install(oracle, root)
            argv = [
                "--module-family",
                "lean",
                "--emit-dependency-map-only",
                "--json",
                "--write-jsonl",
                "--write-junit",
            ]
            outputs = []
            for module in (native, oracle):
                stream = io.StringIO()
                with contextlib.redirect_stdout(stream):
                    code = module.main(argv)
                outputs.append((code, stream.getvalue()))
            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual(outputs[0][0], 0)
            self.assertEqual(json.loads(outputs[0][1])["families"], ["environment"])
            self.assertTrue(
                (root / "artifacts/test_program/deterministic_tests.jsonl").is_file()
            )
            self.assertTrue(
                (root / "artifacts/test_program/deterministic_tests.xml").is_file()
            )

    def test_registered_lunar_execution_and_source_parity(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_test_family_lean_workflow")
        self.assertEqual(document["lifecycle"], "active")
        authored = (
            ROOT
            / "skills/control/workflow-contract-validator/references/lean-family.workflow.json"
        )
        self.assertEqual(document, json.loads(authored.read_text()))
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "tests").mkdir()
            path = root / "tests/test_matrix.json"
            oracle = types.ModuleType("lean_original")
            oracle.__file__ = str(
                ROOT / "tests/test_program/run_comprehensive_tests.py"
            )
            exec(
                compile(
                    (
                        ROOT / "tests/mcp/fixtures/lean_family_original.py.txt"
                    ).read_text(),
                    oracle.__file__,
                    "exec",
                ),
                oracle.__dict__,
            )
            install(oracle, root)
            server = (
                "import sys;sys.dont_write_bytecode=True;sys.path[:0]="
                + repr(
                    [
                        str(ROOT / "scripts"),
                        str(ROOT / "tests/mcp/fixtures"),
                        str(ROOT),
                        *APPLICATION_SITES,
                    ]
                )
                + ";from comprehensive_workflow_boundary import serve;serve("
                + repr(str(root))
                + ")"
            )
            manager = SessionManager()
            failure = None
            async with manager.open(
                "lean-family",
                StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
                {},
            ) as remote:
                try:
                    tools = [
                        t.model_dump(by_alias=True, exclude_none=True)
                        for t in await remote.tools()
                    ]

                    def compile_doc(doc, inventory=None):
                        assets = snapshot(doc)
                        compiled = compile_workflow(
                            "mcp:lean-family",
                            workflow_documents([DESCRIPTOR], assets)[0],
                            tools if inventory is None else inventory,
                        )
                        return compiled, assets

                    compiled, assets = compile_doc(document)
                    self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                    self.assertTrue(compiled["runtime_source"])
                    self.assertEqual(
                        set(compiled["bindings"]),
                        set(document["operations"]) - {"snapshot"},
                    )
                    self.assertIn(
                        "mathformer_lean_family_snapshot", {t["name"] for t in tools}
                    )
                    self.assertFalse(compile_doc(document, [])[0]["runnable"])

                    async def authorize():
                        pass

                    async def run(data, doc=None):
                        path.write_text(json.dumps(data))
                        (root / "undeclared.txt").unlink(missing_ok=True)
                        c, a = compile_doc(doc) if doc else (compiled, assets)
                        self.assertTrue(c["runnable"], c["diagnostics"])
                        return await execute(
                            c, a, {"args": FIXED, "domain": DOMAIN}, remote, authorize
                        )

                    mixed = matrix(["pass", "fail", "pass"])
                    mixed["tests"][1]["module_family"] = "atp"
                    for data in [
                        matrix(["pass"] * 5),
                        matrix(["fail", "timeout", "write", "missing", "pass"]),
                        matrix(["missing"]),
                        matrix(["pass"], "atp"),
                        mixed,
                    ]:
                        result = await run(data)
                        self.assertEqual(result["status"], "accepted", result)
                        report = result["outputs"]["report"]
                        code = result["outputs"]["exit_code"]
                        expected = [
                            r["id"]
                            for r in data["tests"]
                            if r["module_family"] == "lean"
                        ]
                        self.assertEqual(
                            [r["check_id"] for r in report["results"]], expected
                        )
                        self.assertEqual(
                            sum(c["operation"] == "advance" for c in result["calls"]),
                            len(expected),
                        )
                        self.assertEqual(
                            len(result["calls"]), len(expected) + 4 if expected else 5
                        )
                        self.assertEqual(report["schema_errors"], [])
                        self.assertTrue((root / report["dependency_map"]).is_file())
                        self.assertEqual(
                            json.loads(
                                (
                                    root
                                    / "artifacts/test_program/deterministic_tests.json"
                                ).read_text()
                            ),
                            report,
                        )
                        self.assertEqual(code, 0 if report["ok"] else 3)
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["replay_artifacts"])
                        if data["tests"][0]["command"][-1] == "fail":
                            self.assertEqual(
                                [r["status"] for r in report["results"]],
                                ["fail", "fail", "fail", "skip", "pass"],
                            )
                            self.assertEqual(
                                report["results"][1]["stderr"], "timeout after 120s"
                            )
                            self.assertFalse(report["results"][2]["write_audit"]["ok"])
                        (root / "undeclared.txt").unlink(missing_ok=True)
                        stream = io.StringIO()
                        with contextlib.redirect_stdout(stream):
                            code = oracle.main(["--module-family", "lean", "--json"])
                        self.assertEqual(report, json.loads(stream.getvalue()))
                        self.assertEqual(code, code)
                    exhausted = deepcopy(document)
                    exhausted["flow"]["steps"][2]["max_iterations"] = 1
                    result = await run(matrix(["pass", "pass"]), exhausted)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(
                        sum(c["operation"] == "advance" for c in result["calls"]), 1
                    )
                    self.assertFalse(
                        any(c["operation"] == "finalize" for c in result["calls"])
                    )
                    result = await run(matrix(["pass"] * 4097))
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]], ["enter", "prepare"]
                    )
                    bad = matrix(["pass"])
                    bad["schema_version"] = 1
                    self.assertEqual((await run(bad))["status"], "failed")
                    with self.assertRaisesRegex(ValueError, "schema_version 2"):
                        oracle.main(["--module-family", "lean", "--json"])
                    result = await run(matrix(["crash", "pass"]))
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]],
                        ["enter", "prepare", "advance"],
                    )
                    with self.assertRaisesRegex(
                        OSError, "fixture compiler launch failed"
                    ):
                        oracle.main(["--module-family", "lean", "--json"])
                    expected = matrix(["fail"])
                    expected["tests"][0]["expected_exit"] = 7
                    self.assertTrue((await run(expected))["outputs"]["report"]["ok"])
                    # A real publication I/O error propagates through MCP and PRISM.
                    publication_path = (
                        root / "artifacts/test_program/deterministic_tests.json"
                    )
                    publication_path.unlink()
                    publication_path.mkdir()
                    result = await run(matrix(["pass"]))
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(result["calls"][-1]["operation"], "publish")
                    publication_path.rmdir()
                    budget = deepcopy(document)
                    budget["policy"]["limits"]["max_operation_calls"] = 1
                    self.assertEqual(
                        (await run(matrix(["pass"]), budget))["status"], "failed"
                    )
                    # Exact domain bound is admitted through the registered prepare tool.
                    path.write_text(json.dumps(matrix(["missing"] * 4096)))
                    ctx = (
                        await remote.call(
                            "mathformer_lean_family_enter", {"args": FIXED}
                        )
                    )["context"]
                    bound = await remote.call(
                        "mathformer_lean_family_prepare",
                        {"args": FIXED, "domain": DOMAIN, "context": ctx},
                    )
                    self.assertEqual(len(bound["state"]["selected"]), 4096)
                    self.assertFalse(bound["done"])
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_lean_family_snapshot",
                            dict(args=FIXED, context=ctx),
                        )
                    path.write_text(json.dumps(matrix(["pass"])))
                    entered = await remote.call(
                        "mathformer_lean_family_enter", {"args": FIXED}
                    )
                    context = entered["context"]
                    prepared = await remote.call(
                        "mathformer_lean_family_prepare",
                        {"args": FIXED, "domain": DOMAIN, "context": context},
                    )
                    state = prepared["state"]
                    ports = dict(state=state, args=FIXED, context=context)
                    self.assertFalse(prepared["done"])
                    with self.assertRaises(MCPConnectionError):
                        await remote.call("mathformer_lean_family_finalize", ports)
                    forged = deepcopy(state)
                    forged["selected"][0]["command"] = ["forged"]
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_lean_family_advance", {**ports, "state": forged}
                        )
                    advanced = await remote.call(
                        "mathformer_lean_family_advance", ports
                    )
                    self.assertTrue(advanced["done"])
                    self.assertEqual(advanced["state"]["index"], 1)
                    self.assertEqual(advanced["state"]["matrix"], state["matrix"])
                    with self.assertRaises(MCPConnectionError):
                        await remote.call("mathformer_lean_family_advance", ports)
                    ports["state"] = advanced["state"]
                    report = (
                        await remote.call("mathformer_lean_family_finalize", ports)
                    )["report"]
                    with self.assertRaises(MCPConnectionError):
                        await remote.call("mathformer_lean_family_finalize", ports)
                    forged = deepcopy(report)
                    forged["ok"] = False
                    pub = dict(args=FIXED, context=context, report=report)
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_lean_family_publish", {**pub, "report": forged}
                        )
                    await remote.call("mathformer_lean_family_publish", pub)
                    with self.assertRaises(MCPConnectionError):
                        await remote.call("mathformer_lean_family_publish", pub)
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_lean_family_enter",
                            {"args": {**FIXED, "json": False}},
                        )
                    # Exhausted, failed contexts cannot be replayed after a native exception.
                    path.write_text(json.dumps(matrix(["crash"])))
                    ctx = (
                        await remote.call(
                            "mathformer_lean_family_enter", {"args": FIXED}
                        )
                    )["context"]
                    st = (
                        await remote.call(
                            "mathformer_lean_family_prepare",
                            {"args": FIXED, "domain": DOMAIN, "context": ctx},
                        )
                    )["state"]
                    for _ in range(2):
                        with self.assertRaises(MCPConnectionError):
                            await remote.call(
                                "mathformer_lean_family_advance",
                                dict(args=FIXED, context=ctx, state=st),
                            )
                except Exception as error:
                    failure = error
            self.assertFalse(manager.active)
            if failure:
                raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
