#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native ATP stages through registered MCP and the real Lunar/PRISM runtime."""

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
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
import tempfile
import unittest
import yaml
from comprehensive_workflow_boundary import install
from comprehensive_strict_tools import source_runner
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_test_family_atp_workflow/workflow.yaml"


def matrix(modes, family="atp"):
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
                "timeout_seconds": 2,
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
    paths = {r["path"] for r in document["provenance"]["sources"]}
    values = {p: (ROOT / p).read_text() for p in paths}
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


def arguments(native):
    return {
        k: str(v) if isinstance(v, Path) else v
        for k, v in vars(
            native.parse_args(
                ["--module-family", "atp", "--json", "--run-id", "fixture"]
            )
        ).items()
    }


class ATPFamilyTests(unittest.TestCase):
    def test_registered_lunar_prism(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_test_family_atp_workflow")
        self.assertEqual(document["lifecycle"], "active")
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
            native = source_runner()
            install(native, root)
            args = arguments(native)
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
                "atp-family",
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
                        c = compile_workflow(
                            "mcp:atp-family",
                            workflow_documents([DESCRIPTOR], assets)[0],
                            tools if inventory is None else inventory,
                        )
                        return c, assets

                    compiled, assets = compile_doc(document)
                    self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                    self.assertTrue(compiled["runtime_source"])
                    self.assertEqual(
                        set(compiled["bindings"]), set(document["operations"])
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
                            c, a, {"manifest": data, "args": args}, remote, authorize
                        )

                    for data in [
                        matrix(["pass"]),
                        matrix(["fail", "timeout", "write", "missing", "pass"]),
                        matrix(["pass"], "control"),
                    ]:
                        result = await run(data)
                        self.assertEqual(result["status"], "accepted", result)
                        report = result["outputs"]["report"]
                        self.assertEqual(
                            report,
                            json.loads(
                                (
                                    root
                                    / "artifacts/test_program/deterministic_tests.json"
                                ).read_text()
                            ),
                        )
                        self.assertEqual(
                            result["outputs"]["exit_code"], 0 if report["ok"] else 3
                        )
                        expected = [
                            r["id"]
                            for r in data["tests"]
                            if r["module_family"] == "atp"
                        ]
                        self.assertEqual(
                            [r["check_id"] for r in report["results"]], expected
                        )
                        self.assertEqual(
                            sum(c["operation"] == "advance" for c in result["calls"]),
                            len(expected),
                        )
                        if len(expected) == 5:
                            self.assertEqual(
                                [r["status"] for r in report["results"]],
                                ["fail", "fail", "fail", "skip", "pass"],
                            )
                            self.assertIn("timeout", report["results"][1]["stderr"])
                            self.assertFalse(report["results"][2]["write_audit"]["ok"])
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["runtime"]["provenance"])
                        # Identical boundary inputs exercise original run/main ordering and output.
                        (root / "undeclared.txt").unlink(missing_ok=True)
                        stream = io.StringIO()
                        with redirect_stdout(stream):
                            code = native.main(
                                [
                                    "--module-family",
                                    "atp",
                                    "--json",
                                    "--run-id",
                                    "fixture",
                                ]
                            )
                        self.assertEqual(json.loads(stream.getvalue()), report)
                        self.assertEqual(code, result["outputs"]["exit_code"])
                    exact = deepcopy(document)
                    exact["flow"]["steps"][2]["max_iterations"] = 2
                    self.assertEqual(
                        (await run(matrix(["pass", "pass"]), exact))["status"],
                        "accepted",
                    )
                    exhausted = deepcopy(exact)
                    exhausted["flow"]["steps"][2]["max_iterations"] = 1
                    result = await run(matrix(["pass", "pass"]), exhausted)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertFalse(
                        any(c["operation"] == "finalize" for c in result["calls"])
                    )
                    result = await run(matrix(["crash", "pass"]))
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]],
                        ["prepare", "guard", "advance"],
                    )
                    output = root / "artifacts/test_program/deterministic_tests.json"
                    output.unlink()
                    output.mkdir()
                    result = await run(matrix(["pass"]))
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(result["calls"][-1]["operation"], "publish")
                    output.rmdir()
                    default = matrix(["timeout", "pass"])
                    del default["tests"][0]["timeout_seconds"]
                    result = await run(default)
                    self.assertEqual(
                        result["outputs"]["report"]["results"][0]["stderr"],
                        "timeout after 120s",
                    )
                    expected = matrix(["fail"])
                    expected["tests"][0]["expected_exit"] = 7
                    self.assertTrue((await run(expected))["outputs"]["report"]["ok"])
                    data = matrix(["pass", "pass"])
                    path.write_text(json.dumps(data))
                    prepared = await remote.call(
                        "mathformer_atp_family_prepare",
                        {"manifest": data, "args": args},
                    )
                    state, context = prepared["state"], prepared["context"]
                    self.assertEqual(state["index"], 0)
                    self.assertEqual(state["results"], [])
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_atp_family_finalize",
                            {"state": state, "args": args, "context": context},
                        )
                    await remote.call(
                        "mathformer_atp_family_guard",
                        {"state": state, "context": context},
                    )
                    forged = deepcopy(state)
                    forged["selected"][0]["command"] = ["forged"]
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_atp_family_advance",
                            {"state": forged, "args": args, "context": context},
                        )
                    advanced = await remote.call(
                        "mathformer_atp_family_advance",
                        {"state": state, "args": args, "context": context},
                    )
                    self.assertEqual(advanced["state"]["index"], 1)
                    self.assertEqual(
                        advanced["state"]["results"][0]["check_id"], "fixture.0"
                    )
                    self.assertEqual(advanced["state"]["matrix"], state["matrix"])
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_atp_family_advance",
                            {"state": state, "args": args, "context": context},
                        )
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_atp_family_prepare",
                            {"manifest": matrix(["fail"]), "args": args},
                        )
                    too_many = matrix(["pass"] * 1025)
                    path.write_text(json.dumps(too_many))
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_atp_family_prepare",
                            {"manifest": too_many, "args": args},
                        )
                    budget = deepcopy(document)
                    budget["policy"]["limits"]["max_operation_calls"] = 1
                    self.assertEqual(
                        (await run(matrix(["pass"]), budget))["status"], "failed"
                    )
                except Exception as error:
                    failure = error
            self.assertFalse(manager.active)
            if failure:
                raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
