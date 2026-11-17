#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Execute canonical fixture matrices via actual registered MCP and Lunar/PRISM."""

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
from comprehensive_strict_boundary import install
from comprehensive_strict_tools import source_runner
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_test_comprehensive_strict_workflow/workflow.yaml"


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


def original():
    module = type(sys)("_comprehensive_original")
    module.__file__ = str(ROOT / "tests/test_program/run_comprehensive_tests.py")
    exec(
        compile(
            (
                ROOT / "tests/mcp/fixtures/comprehensive_strict_original.py.txt"
            ).read_text(),
            module.__file__,
            "exec",
        ),
        module.__dict__,
    )
    return module


def matrix(modes, families=None):
    families = families or ["control"] * len(modes)
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
            for i, (mode, family) in enumerate(zip(modes, families))
        ],
    }


class ComprehensiveTests(unittest.TestCase):
    def test_entrypoint_parity(self):
        old, native = original(), source_runner()
        for modes, families in [
            (["pass"], None),
            (["fail", "timeout", "write", "missing", "pass"], None),
            (["pass"], ["unselected"]),
            (["pass"] * len(native.MODULE_FAMILIES), sorted(native.MODULE_FAMILIES)),
        ]:
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                (root / "tests").mkdir()
                (root / "tests/test_matrix.json").write_text(
                    json.dumps(matrix(modes, families))
                )
                reports = []
                for module in (old, native):
                    install(module, root)
                    (root / "undeclared.txt").unlink(missing_ok=True)
                    stream = io.StringIO()
                    with redirect_stdout(stream):
                        code = module.main(
                            [
                                "--module-family",
                                "all",
                                "--profile",
                                "strict",
                                "--run-id",
                                "fixture",
                                "--write-jsonl",
                                "--write-junit",
                                "--json",
                            ]
                        )
                    report = json.loads(stream.getvalue())
                    reports.append(
                        (
                            code,
                            report,
                            (
                                root / "artifacts/test_program/deterministic_tests.xml"
                            ).read_text(),
                        )
                    )
                self.assertEqual(reports[0], reports[1])
                self.assertEqual(
                    reports[1][1]["summary"]["total"],
                    0 if families == ["unselected"] else len(modes),
                )
                self.assertEqual(
                    reports[1][0],
                    0 if families == sorted(native.MODULE_FAMILIES) else 3,
                )
        # Native pre-traversal rejection and exception propagation are unchanged.
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "tests").mkdir()
            path = root / "tests/test_matrix.json"
            for value in (
                {"schema_version": 1, "tests": [{}]},
                {"schema_version": 2, "tests": []},
            ):
                path.write_text(json.dumps(value))
                for module in (old, native):
                    install(module, root)
                    with self.assertRaises(ValueError):
                        module.run(module.parse_args(["--profile", "strict"]))
            path.write_text(json.dumps(matrix(["crash", "pass"])))
            for module in (old, native):
                install(module, root)
                with self.assertRaises(OSError):
                    module.run(module.parse_args(["--profile", "strict"]))

    def test_registered_tools_lunar_prism(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_test_comprehensive_strict_workflow")
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
                + ";from comprehensive_strict_boundary import serve;serve("
                + repr(str(root))
                + ")"
            )
            manager = SessionManager()
            failure = None
            async with manager.open(
                "comprehensive-strict",
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
                        selected = workflow_documents([DESCRIPTOR], assets)[0]
                        return (
                            compile_workflow(
                                "mcp:comprehensive-strict",
                                selected,
                                tools if inventory is None else inventory,
                            ),
                            assets,
                        )

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
                        return await execute(
                            c,
                            a,
                            {"matrix": data, "context": {"run_id": "fixture"}},
                            remote,
                            authorize,
                        )

                    for data in [
                        matrix(
                            ["pass"] * len(source_runner().MODULE_FAMILIES),
                            sorted(source_runner().MODULE_FAMILIES),
                        ),
                        matrix(["fail", "timeout", "write", "missing", "pass"]),
                        matrix(["pass"], ["unselected"]),
                    ]:
                        result = await run(data)
                        self.assertEqual(result["status"], "accepted", result)
                        report = result["outputs"]["report"]
                        outcome = result["outputs"]["outcome"]
                        self.assertEqual(report, json.loads(outcome["stdout"]))
                        self.assertEqual(
                            report,
                            json.loads((root / outcome["json_report"]).read_text()),
                        )
                        self.assertEqual(
                            report["results"],
                            [
                                json.loads(line)
                                for line in (root / outcome["jsonl_report"])
                                .read_text()
                                .splitlines()
                            ],
                        )
                        self.assertTrue(
                            (root / outcome["junit_report"])
                            .read_text()
                            .startswith("<testsuite")
                        )
                        self.assertEqual(outcome["exit_code"], 0 if report["ok"] else 3)
                        self.assertEqual(
                            [r["check_id"] for r in report["results"]],
                            [
                                r["id"]
                                for r in data["tests"]
                                if r["module_family"] in source_runner().MODULE_FAMILIES
                            ],
                        )
                        if data["tests"][0]["command"][1] == "fail":
                            self.assertEqual(
                                [r["status"] for r in report["results"]],
                                ["fail"] * 4 + ["pass"],
                            )
                            self.assertIn("undeclared", report["results"][2]["stderr"])
                            self.assertIn("timeout", report["results"][1]["stderr"])
                            self.assertEqual(report["summary"]["fail"], 4)
                        self.assertEqual(
                            sum(
                                c["operation"] == "check_next" for c in result["calls"]
                            ),
                            len(report["results"]),
                        )
                        self.assertEqual(
                            report["ok"],
                            len(data["tests"]) == len(source_runner().MODULE_FAMILIES),
                        )
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["replay_artifacts"])
                    # Exact loop bound succeeds; one fewer cannot publish partial results.
                    exact = deepcopy(document)
                    exact["flow"]["steps"][1]["max_iterations"] = 2
                    self.assertEqual(
                        (await run(matrix(["pass", "pass"]), exact))["status"],
                        "accepted",
                    )
                    exhausted = deepcopy(exact)
                    exhausted["flow"]["steps"][1]["max_iterations"] = 1
                    result = await run(matrix(["pass", "pass"]), exhausted)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]],
                        ["prepare", "check_next"],
                    )
                    result = await run(matrix(["crash", "pass"]))
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]],
                        ["prepare", "check_next"],
                    )
                    self.assertEqual(result["calls"][-1]["status"], "rejected")
                    # Native publication failure propagates after all checks and aggregation.
                    output = root / "artifacts/test_program/deterministic_tests.json"
                    output.unlink()
                    output.mkdir()
                    result = await run(matrix(["pass"]))
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]],
                        ["prepare", "check_next", "finalize", "publish"],
                    )
                    self.assertEqual(result["calls"][-1]["status"], "rejected")
                    output.rmdir()
                    # The default timeout is passed through to the compiler boundary.
                    default_timeout = matrix(["timeout", "pass"])
                    del default_timeout["tests"][0]["timeout_seconds"]
                    result = await run(default_timeout)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(
                        result["outputs"]["report"]["results"][0]["stderr"],
                        "timeout after 120s",
                    )
                    nonzero = matrix(["fail"])
                    nonzero["tests"][0]["expected_exit"] = 7
                    result = await run(nonzero)
                    self.assertEqual(
                        result["outputs"]["report"]["results"][0]["status"], "pass"
                    )
                    # Matrix assertion prevents substituting arbitrary caller commands.
                    path.write_text(json.dumps(matrix(["pass"])))
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_comprehensive_strict_prepare",
                            {
                                "matrix": matrix(["fail"]),
                                "context": {"run_id": "fixture"},
                            },
                        )
                    budget = deepcopy(document)
                    budget["policy"]["limits"]["max_operation_calls"] = 1
                    result = await run(matrix(["pass"]), budget)
                    self.assertEqual(result["status"], "failed")
                    self.assertIn("budget", str(result).lower())
                except Exception as error:
                    failure = error
            self.assertFalse(manager.active)
            if failure:
                raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
