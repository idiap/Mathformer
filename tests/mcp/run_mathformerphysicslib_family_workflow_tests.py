#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Real MCP, Lunar compiler and PRISM runtime over isolated native runner fixtures.

This runner has no model boundary. Only named compiler invocations and provider
availability are substituted by the test-only external boundary fixture.
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
SITES = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
sys.path.extend(SITES)
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
from mathformerphysicslib_family_tools import ARGV
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_test_family_mathformerphysicslib_workflow/workflow.yaml"


def matrix(modes, family="mathformerphysicslib"):
    return {
        "schema_version": 2,
        "tests": [
            {
                "id": f"fixture.{i}",
                "module_family": family,
                "command": ["fixture-compiler", mode],
                "owner_skill": "fixture",
                "hook_id": "test.fixture",
                "fixture_ids": ["compiler"],
                "test_kind": "regression",
                "risk_level": "low",
                "timeout_seconds": 30 + i,
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


def snapshot(doc):
    values = {
        p: (ROOT / p).read_text()
        for p in {r["path"] for r in doc["provenance"]["sources"]}
    }
    values[DESCRIPTOR] = json.dumps(doc)
    return [
        {
            "path": p,
            "content": s,
            "encoding": "text",
            "sha256": hashlib.sha256(s.encode()).hexdigest(),
        }
        for p, s in values.items()
    ]


def oracle(root):
    module = types.ModuleType("physicslib_original")
    module.__file__ = str(ROOT / "tests/test_program/run_comprehensive_tests.py")
    exec(
        compile(
            (
                ROOT / "tests/mcp/fixtures/mathformerphysicslib_family_original.py.txt"
            ).read_text(),
            module.__file__,
            "exec",
        ),
        module.__dict__,
    )
    install(module, root)
    return module


class PhysicsLibraryTests(unittest.TestCase):
    def test_native_invariants_and_snapshot_parity(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "tests").mkdir()
            native = source_runner()
            install(native, root)
            native.MATRIX_FILE.write_text(json.dumps(matrix(["pass"])))
            args = native.parse_args(ARGV)
            state = native.prepare_checks(args)
            with self.assertRaisesRegex(ValueError, "unconsumed"):
                native.finalize_checks(state, args)
            broken = deepcopy(state)
            broken["index"] = 1
            with self.assertRaisesRegex(ValueError, "cursor"):
                native.advance_check(broken, args)
            state = native.advance_check(state, args)
            self.assertEqual(state["index"], len(state["results"]))
            with self.assertRaisesRegex(ValueError, "exhausted"):
                native.advance_check(state, args)
            missing = matrix(["missing"])["tests"][0]
            self.assertEqual(native.run_check(missing, False)["status"], "skip")
            self.assertEqual(native.run_check(missing, True)["status"], "fail")
            native.MATRIX_FILE.unlink()
            results = []
            for module in (native, oracle(root)):
                stream = io.StringIO()
                with contextlib.redirect_stdout(stream):
                    code = module.main(
                        [
                            *ARGV,
                            "--emit-dependency-map-only",
                            "--write-jsonl",
                            "--write-junit",
                        ]
                    )
                results.append((code, stream.getvalue()))
            self.assertEqual(results[0], results[1])
            self.assertEqual(results[0][0], 0)
            self.assertEqual(json.loads(results[0][1])["families"], ["environment"])
            self.assertTrue(
                (root / "artifacts/test_program/deterministic_tests.xml").exists()
            )
            self.assertTrue(
                (root / "artifacts/test_program/deterministic_tests.jsonl").exists()
            )

    def test_registered_lunar_prism_execution(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        doc = yaml.safe_load(Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text())
        self.assertEqual(doc["id"], "hub_test_family_mathformerphysicslib_workflow")
        self.assertEqual(doc["lifecycle"], "active")
        self.assertEqual(
            doc,
            json.loads(
                (
                    ROOT
                    / "skills/control/workflow-contract-validator/references/mathformerphysicslib-family.workflow.json"
                ).read_text()
            ),
        )
        for row in doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "tests").mkdir()
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
                + ";from comprehensive_workflow_boundary import serve;serve("
                + repr(str(root))
                + ")"
            )
            manager = SessionManager()
            failure = None
            async with manager.open(
                "physicslib",
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
                        w = compile_workflow(
                            "mcp:physicslib",
                            workflow_documents([DESCRIPTOR], assets)[0],
                            tools if inventory is None else inventory,
                        )
                        return w, assets

                    workflow, assets = compiled(doc)
                    self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                    self.assertTrue(workflow["runtime_source"])
                    self.assertEqual(set(workflow["bindings"]), set(doc["operations"]))
                    self.assertFalse(compiled(doc, [])[0]["runnable"])

                    async def authorize():
                        pass

                    async def run(data, document=doc, count=None):
                        path.write_text(json.dumps(data))
                        (root / "undeclared.txt").unlink(missing_ok=True)
                        w, a = compiled(document)
                        self.assertTrue(w["runnable"], w["diagnostics"])
                        n = sum(
                            r["module_family"] == "mathformerphysicslib"
                            for r in data["tests"]
                        )
                        return await execute(
                            w,
                            a,
                            {
                                "invocation": {
                                    "argv": ARGV,
                                    "selected_row_count": n if count is None else count,
                                }
                            },
                            remote,
                            authorize,
                        )

                    mixed = matrix(["pass", "fail", "pass"])
                    mixed["tests"][1]["module_family"] = "atp"
                    for data in [
                        matrix(["pass"] * 15),
                        matrix(["fail", "timeout", "write", "missing", "pass"]),
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
                            if r["module_family"] == "mathformerphysicslib"
                        ]
                        self.assertEqual(
                            [r["check_id"] for r in report["results"]], expected
                        )
                        self.assertEqual(
                            sum(c["operation"] == "advance" for c in result["calls"]),
                            len(expected),
                        )
                        self.assertEqual(
                            len(result["calls"]),
                            2 * len(expected) + 6 if expected else 7,
                        )
                        self.assertEqual(report["schema_errors"], [])
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
                        self.assertEqual(code, 0 if report["ok"] else 3)
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["replay_artifacts"])
                        if len(expected) == 5:
                            self.assertEqual(
                                [r["status"] for r in report["results"]],
                                ["fail", "fail", "fail", "skip", "pass"],
                            )
                            self.assertEqual(
                                report["results"][1]["stderr"], "timeout after 31s"
                            )
                            self.assertFalse(report["results"][2]["write_audit"]["ok"])
                        (root / "undeclared.txt").unlink(missing_ok=True)
                        stream = io.StringIO()
                        with contextlib.redirect_stdout(stream):
                            original_code = original.main(ARGV)
                        self.assertEqual(code, original_code)
                        self.assertEqual(report, json.loads(stream.getvalue()))
                    exhausted = deepcopy(doc)
                    exhausted["flow"]["steps"][4]["max_iterations"] = 1
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
                    result = await run(matrix(["missing"] * 16), count=15)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]],
                        ["parse", "enter", "prepare"],
                    )
                    result = await run(matrix(["pass"]), count=0)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]],
                        ["parse", "enter", "prepare"],
                    )
                    for data in [
                        matrix(["crash", "pass"]),
                        matrix([]),
                        {**matrix(["pass"]), "schema_version": 1},
                    ]:
                        result = await run(data)
                        self.assertEqual(result["status"], "failed", result)
                        self.assertIsNone(result["outputs"])
                        self.assertFalse(
                            any(c["operation"] == "publish" for c in result["calls"])
                        )
                        with self.assertRaises((OSError, ValueError)):
                            original.main(ARGV)
                    budget = deepcopy(doc)
                    budget["policy"]["limits"]["max_operation_calls"] = 1
                    self.assertEqual(
                        (await run(matrix(["pass"]), budget))["status"], "failed"
                    )
                    publication = (
                        root / "artifacts/test_program/deterministic_tests.json"
                    )
                    publication.unlink()
                    publication.mkdir()
                    result = await run(matrix(["pass"]))
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(result["calls"][-1]["operation"], "publish")
                    publication.rmdir()
                    # Advertised tools reject modified arguments, state and replay.
                    path.write_text(json.dumps(matrix(["pass"])))
                    parsed = await remote.call(
                        "mathformer_physicslib_parse",
                        {"invocation": {"argv": ARGV, "selected_row_count": 1}},
                    )
                    ports = dict(args=parsed["args"], context=parsed["context"])
                    await remote.call("mathformer_physicslib_enter", ports)
                    state = (await remote.call("mathformer_physicslib_prepare", ports))[
                        "state"
                    ]
                    await remote.call(
                        "mathformer_physicslib_cursor_guard",
                        dict(state=state, context=parsed["context"]),
                    )
                    forged = deepcopy(state)
                    forged["selected"][0]["command"] = ["forged"]
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_physicslib_advance", dict(**ports, state=forged)
                        )
                    advanced = (
                        await remote.call(
                            "mathformer_physicslib_advance", dict(**ports, state=state)
                        )
                    )["state"]
                    self.assertEqual(advanced["index"], 1)
                    self.assertEqual(advanced["matrix"], state["matrix"])
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_physicslib_advance", dict(**ports, state=state)
                        )
                    self.assertFalse(
                        (
                            await remote.call(
                                "mathformer_physicslib_cursor_guard",
                                dict(state=advanced, context=parsed["context"]),
                            )
                        )["remaining"]
                    )
                    report = (
                        await remote.call(
                            "mathformer_physicslib_finalize",
                            dict(**ports, state=advanced),
                        )
                    )["report"]
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_physicslib_publish",
                            dict(**ports, report={**report, "ok": False}),
                        )
                    await remote.call(
                        "mathformer_physicslib_publish", dict(**ports, report=report)
                    )
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_physicslib_publish",
                            dict(**ports, report=report),
                        )
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_physicslib_parse",
                            {"invocation": {"argv": ARGV, "selected_row_count": 16}},
                        )
                except Exception as error:
                    failure = error
            self.assertFalse(manager.active)
            if failure:
                raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
