#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native source equivalence and registered MCP/Lunar/PRISM runtime tests."""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT / "tests/mcp/fixtures"),
]
import asyncio
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import yaml
from sympy_wiki_tools import source
from sympy_wiki_process import install
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_sympy_wiki_workflow/workflow.yaml"


def oracle():
    loader = SourceFileLoader(
        "sympy_wiki_oracle", str(ROOT / "tests/mcp/fixtures/sympy_wiki_original.py.txt")
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    module.REPO_ROOT = ROOT
    module.PYTHON = source().PYTHON
    return module


def snapshot(document):
    def asset(path, text):
        return {
            "path": path,
            "content": text,
            "encoding": "text",
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
        }

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(row["path"], (ROOT / row["path"]).read_text())
        for row in document["provenance"]["sources"]
    ]


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="wiki-fixture-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_original_equivalence(self):
        native = source()
        for mode, count, code in [
            ("success", 11, 0),
            ("fail", 4, 1),
            ("timeout", 3, None),
            ("launch", 2, None),
        ]:
            root = self.root / ("wiki-fixture-" + mode)
            reports = []
            plans = []
            prints = []
            for module in (oracle(), native):
                calls = install(module)
                stream = io.StringIO()
                with (
                    patch.object(
                        sys, "argv", ["wiki", "--artifact-root", str(root), "--json"]
                    ),
                    redirect_stdout(stream),
                ):
                    if code is None:
                        with self.assertRaises((subprocess.TimeoutExpired, OSError)):
                            module.main()
                        self.assertFalse((root / "e2e_report.json").exists())
                    else:
                        self.assertEqual(module.main(), code)
                        reports.append(
                            json.loads((root / "e2e_report.json").read_text())
                        )
                        (root / "e2e_report.json").unlink()
                plans.append(calls)
                prints.append(stream.getvalue())
                self.assertEqual(len(calls), count)
            self.assertEqual(plans[0], plans[1])
            self.assertEqual(prints[0], prints[1])
            self.assertEqual(reports[:1], reports[1:])
            if reports:
                report = reports[0]
                self.assertEqual(len(report["results"]), count)
                self.assertTrue(
                    all(
                        len(r["stdout"]) <= 4000 and len(r["stderr"]) <= 4000
                        for r in report["results"]
                    )
                )
                self.assertTrue(all(r["duration_ms"] == 0 for r in report["results"]))
                self.assertEqual(report["ok"], code == 0)
                if code:
                    self.assertEqual(report["results"][-1]["returncode"], 7)
                    self.assertEqual(len(report["results"][-1]["stdout"]), 4000)
                    self.assertEqual(len(report["results"][-1]["stderr"]), 4000)
                if count == 11:
                    self.assertIn("--self-test", plans[0][1])
                    self.assertEqual(
                        plans[0][8][plans[0][8].index("--max-n") + 1], "100"
                    )

    def test_real_registered_mcp_and_prism(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_sympy_wiki_workflow")
        self.assertEqual(document["lifecycle"], "active")
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        # Only the subprocess boundary is replaced, in test code. Production
        # registrations and all four shared source blocks remain unchanged.
        server = 'import sys;sys.path[:0]=["scripts","tests/mcp/fixtures"];from mcp.server.fastmcp import FastMCP;from sympy_wiki_tools import source,register_sympy_wiki_tools;mcp=FastMCP("wiki-test");register_sympy_wiki_tools(mcp);from sympy_wiki_process import install;install(source());mcp.run(transport="stdio")'
        manager = SessionManager()
        async with manager.open(
            "wiki",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {},
        ) as remote:
            failure = None
            try:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile(doc, inventory=None):
                    assets = snapshot(doc)
                    workflow = workflow_documents([DESCRIPTOR], assets)[0]
                    (
                        self.assertTrue(workflow["valid"], workflow)
                        if "valid" in workflow
                        else None
                    )
                    compiled = compile_workflow(
                        "mcp:wiki", workflow, tools if inventory is None else inventory
                    )
                    return compiled, assets

                compiled, assets = compile(document)
                self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                self.assertTrue(compiled["runtime_source"])
                self.assertEqual(set(compiled["bindings"]), set(document["operations"]))
                self.assertFalse(compile(document, [])[0]["runnable"])

                async def authorize():
                    pass

                async def run(mode, doc=None):
                    selected, received = compile(doc) if doc else (compiled, assets)
                    # Fixture call counter is per server session; subprocess fixture
                    # indexes are relative to each root, as independent native runs.
                    root = self.root / ("wiki-fixture-" + mode)
                    result = await execute(
                        selected,
                        received,
                        {"options": {"artifact_root": str(root), "json": True}},
                        remote,
                        authorize,
                    )
                    return result, root

                for mode, count, code in [
                    ("success", 11, 0),
                    ("fail", 4, 1),
                    ("timeout", 3, None),
                    ("launch", 2, None),
                ]:
                    result, root = await run(mode)
                    if code is None:
                        self.assertEqual(result["status"], "failed", result)
                        self.assertIsNone(result["outputs"])
                        self.assertFalse((root / "e2e_report.json").exists())
                        self.assertEqual(len(result["calls"]), 2 * count)
                        self.assertEqual(result["calls"][-1]["status"], "rejected")
                    else:
                        self.assertEqual(result["status"], "accepted", result)
                        completion = result["outputs"]["completion"]
                        report = json.loads((root / "e2e_report.json").read_text())
                        self.assertEqual(
                            completion,
                            {
                                "report": report,
                                "report_path": str(root / "e2e_report.json"),
                                "exit_code": code,
                            },
                        )
                        self.assertEqual(len(report["results"]), count)
                        self.assertEqual(report["ok"], code == 0)
                        if code == 0:
                            consistency = json.loads(
                                Path(report["artifacts"]["consistency"]).read_text()
                            )
                            self.assertTrue(consistency["ok"], consistency)
                            self.assertTrue(
                                Path(report["artifacts"]["markdown"]).is_file()
                            )
                            self.assertTrue(Path(report["artifacts"]["html"]).is_file())
                            numeric = json.loads(
                                Path(report["artifacts"]["counterexamples"]).read_text()
                            )
                            self.assertTrue(numeric["ok"], numeric)
                        self.assertEqual(len(result["calls"]), 2 + 2 * count)
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["replay_artifacts"])
                bounded = deepcopy(document)
                bounded["flow"]["steps"][1]["max_iterations"] = 2
                result, root = await run("exhausted", bounded)
                self.assertEqual(result["status"], "failed", result)
                self.assertFalse((root / "e2e_report.json").exists())
                self.assertEqual(len(result["calls"]), 5)
                limited = deepcopy(document)
                limited["policy"]["limits"]["max_operation_calls"] = 2
                result, root = await run("budget", limited)
                self.assertEqual(result["status"], "failed", result)
                self.assertFalse((root / "e2e_report.json").exists())
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
