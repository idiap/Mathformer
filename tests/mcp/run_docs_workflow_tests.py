#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic docs wrapper parity and real registered MCP/PRISM execution."""

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
from types import SimpleNamespace
import unittest
import yaml
from comprehensive_workflow_boundary import install
from comprehensive_strict_tools import source_runner
from docs_workflow_tools import docs_source
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_test_docs_workflow/workflow.yaml"


def snapshot(document):
    values = {
        r["path"]: (ROOT / r["path"]).read_text()
        for r in document["provenance"]["sources"]
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


def matrix(modes, families=None):
    families = families or ["docs"] * len(modes)
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


def original():
    module = type(sys)("_docs_original")
    module.__file__ = str(ROOT / "tests/run_docs.py")
    exec(
        compile(
            (ROOT / "tests/mcp/fixtures/docs_original.py.txt").read_text(),
            module.__file__,
            "exec",
        ),
        module.__dict__,
    )
    return module


class DocsTests(unittest.TestCase):
    def test_wrapper_parity_and_native_report(self):
        old, wrapper, native = original(), docs_source(), source_runner()
        for flags in (
            [],
            ["--json"],
            ["--fail-on-warning"],
            ["--json", "--fail-on-warning"],
        ):
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                (root / "tests").mkdir()
                (root / "tests/test_matrix.json").write_text(
                    json.dumps(
                        matrix(
                            ["fail", "timeout", "missing", "pass"],
                            ["docs", "mathformerlib", "docs", "docs"],
                        )
                    )
                )
                install(native, root)
                reports = []
                for module in (old, wrapper):
                    calls = []

                    def delegate(command, cwd):
                        calls.append((command, cwd))
                        return native.main(command[2:])

                    module.subprocess = SimpleNamespace(call=delegate)
                    module.REPO_ROOT = root
                    saved = sys.argv
                    sys.argv = ["run_docs.py", *flags]
                    stream = io.StringIO()
                    try:
                        with redirect_stdout(stream):
                            code = module.main()
                    finally:
                        sys.argv = saved
                    reports.append(
                        (
                            code,
                            calls,
                            stream.getvalue(),
                            (
                                native.ARTIFACT_ROOT / "deterministic_tests.json"
                            ).read_text(),
                        )
                    )
                self.assertEqual(reports[0], reports[1])
                self.assertEqual(len(reports[0][1]), 1)
                self.assertEqual(code, 3)
                self.assertEqual(json.loads(reports[0][3])["summary"]["total"], 4)
        # The wrapper returns any child exit status, without translating or retrying.
        for module in (old, wrapper):
            module.subprocess = SimpleNamespace(call=lambda *a, **k: 19)
            saved = sys.argv
            sys.argv = ["run_docs.py"]
            try:
                self.assertEqual(module.main(), 19)
            finally:
                sys.argv = saved

    def test_registered_tools_lunar_prism(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_test_docs_workflow")
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
                + ";from comprehensive_workflow_boundary import serve;serve("
                + repr(str(root))
                + ")"
            )
            manager = SessionManager()
            failure = None
            async with manager.open(
                "docs",
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
                                "mcp:docs",
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

                    async def run(data, flags=None, doc=None):
                        path.write_text(json.dumps(data))
                        (root / "undeclared.txt").unlink(missing_ok=True)
                        c, a = compile_doc(doc) if doc else (compiled, assets)
                        return await execute(
                            c,
                            a,
                            {"matrix": data, "argv": flags or []},
                            remote,
                            authorize,
                        )

                    for modes, families, flags, statuses in [
                        (
                            ["pass", "pass", "fail"],
                            ["mathformerlib", "docs", "unselected"],
                            ["--json"],
                            ["pass", "pass"],
                        ),
                        (
                            ["fail", "timeout", "write", "missing", "pass"],
                            None,
                            [],
                            ["fail", "fail", "fail", "skip", "pass"],
                        ),
                        (
                            ["missing", "pass"],
                            None,
                            ["--fail-on-warning"],
                            ["fail", "pass"],
                        ),
                        (["pass"], ["unselected"], [], []),
                    ]:
                        result = await run(matrix(modes, families), flags)
                        self.assertEqual(result["status"], "accepted", result)
                        report = result["outputs"]["report"]
                        self.assertEqual(
                            [r["status"] for r in report["results"]], statuses
                        )
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
                            report["results"],
                            [
                                json.loads(line)
                                for line in (
                                    root
                                    / "artifacts/test_program/deterministic_tests.jsonl"
                                )
                                .read_text()
                                .splitlines()
                            ],
                        )
                        self.assertTrue(
                            (root / "artifacts/test_program/deterministic_tests.xml")
                            .read_text()
                            .startswith("<testsuite")
                        )
                        self.assertEqual(
                            result["outputs"]["exit_code"],
                            3 if "fail" in statuses else 0,
                        )
                        self.assertEqual(
                            sum(c["operation"] == "advance" for c in result["calls"]),
                            len(statuses),
                        )
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["replay_artifacts"])
                    exact = deepcopy(document)
                    exact["flow"]["steps"][3]["max_iterations"] = 2
                    self.assertEqual(
                        (await run(matrix(["pass", "pass"]), doc=exact))["status"],
                        "accepted",
                    )
                    exhausted = deepcopy(exact)
                    exhausted["flow"]["steps"][3]["max_iterations"] = 1
                    result = await run(matrix(["pass", "pass"]), doc=exhausted)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]],
                        ["parse", "prepare", "guard", "advance", "guard"],
                    )
                    result = await run(matrix(["crash", "pass"]))
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]],
                        ["parse", "prepare", "guard", "advance"],
                    )
                    self.assertIsNone(result["outputs"])
                    output = root / "artifacts/test_program/deterministic_tests.json"
                    output.unlink()
                    output.mkdir()
                    result = await run(matrix(["pass"]))
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(result["calls"][-1]["operation"], "publish")
                    output.rmdir()
                    data = matrix(["timeout", "pass"])
                    del data["tests"][0]["timeout_seconds"]
                    result = await run(data)
                    self.assertEqual(
                        result["outputs"]["report"]["results"][0]["stderr"],
                        "timeout after 120s",
                    )
                    data = matrix(["fail"])
                    data["tests"][0]["expected_exit"] = 7
                    self.assertEqual(
                        (await run(data))["outputs"]["report"]["results"][0]["status"],
                        "pass",
                    )
                    budget = deepcopy(document)
                    budget["policy"]["limits"]["max_operation_calls"] = 1
                    result = await run(matrix(["pass"]), doc=budget)
                    self.assertEqual(result["status"], "failed")
                    self.assertIn("budget", str(result).lower())
                    # Real tools reject forged commands/history, incorrect order and replay.
                    parsed = await remote.call("mathformer_docs_parse", {"argv": []})
                    args = parsed["args"]
                    self.assertEqual(args["module_family"], ["docs", "mathformerlib"])
                    self.assertEqual(args["profile"], "workstation")
                    data = matrix(["pass", "pass"])
                    path.write_text(json.dumps(data))
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_docs_prepare",
                            {"matrix": matrix(["fail"]), "args": args},
                        )
                    prepared = await remote.call(
                        "mathformer_docs_prepare", {"matrix": data, "args": args}
                    )
                    state = prepared["state"]
                    self.assertEqual(state["index"], 0)
                    self.assertEqual(state["results"], [])
                    self.assertEqual(state["selected"], data["tests"])
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_docs_finalize", {"state": state, "args": args}
                        )
                    self.assertFalse(
                        (
                            await remote.call(
                                "mathformer_docs_guard", {"state": state, "args": args}
                            )
                        )["done"]
                    )
                    forged = deepcopy(state)
                    forged["selected"][0]["command"] = ["forged"]
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_docs_advance", {"state": forged, "args": args}
                        )
                    advanced = await remote.call(
                        "mathformer_docs_advance", {"state": state, "args": args}
                    )
                    self.assertEqual(advanced["state"]["index"], 1)
                    self.assertEqual(advanced["state"]["matrix"], state["matrix"])
                    self.assertEqual(
                        [r["check_id"] for r in advanced["state"]["results"]],
                        ["fixture.0"],
                    )
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_docs_advance", {"state": state, "args": args}
                        )
                    args = (await remote.call("mathformer_docs_parse", {"argv": []}))[
                        "args"
                    ]
                    data = matrix(["pass"] * 10001)
                    path.write_text(json.dumps(data))
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_docs_prepare", {"matrix": data, "args": args}
                        )
                except Exception as error:
                    failure = error
            self.assertFalse(manager.active)
            if failure:
                raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
