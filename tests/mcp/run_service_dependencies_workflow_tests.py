#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic native equivalence and real MCP/PRISM execution, without providers."""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.path[:0] = [str(LUNAR / "app/backend"), str(ROOT / "scripts")]
import asyncio
from copy import deepcopy
import hashlib
import json
import tempfile
import unittest
import yaml
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute
import probe_mcp_service_dependencies as native

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_mcp_service_dependencies_workflow/workflow.yaml"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])


def asset(path, text):
    return {
        "path": path,
        "content": text,
        "encoding": "text",
        "sha256": hashlib.sha256(text.encode()).hexdigest(),
    }


def snapshot(document):
    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(row["path"], (ROOT / row["path"]).read_text())
        for row in document["provenance"]["sources"]
    ]


class DependencyTests(unittest.TestCase):
    def test_scan_state_and_parser(self):
        from unittest.mock import patch

        state = native.initialize_scans()["packages"]
        original = deepcopy(state)
        with patch.object(native.importlib.metadata, "version", return_value="fixture"):
            for index in range(10):
                previous = deepcopy(state)
                state = native.package_next(state)
                self.assertEqual(state["cursor"], index + 1)
                self.assertEqual(state["rows"][:-1], previous["rows"])
                self.assertEqual(state["done"], index == 9)
            with self.assertRaises(ValueError):
                native.package_next(state)
        self.assertEqual(original, {"cursor": 0, "rows": [], "done": False})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "req"
            self.assertEqual(native.parse_requirements(path), [])
            path.write_text(
                "# comment\n\n  mcp>=1  \nhttpx # inline\n"
                + "\n".join("entry" + str(i) for i in range(1000))
            )
            entries = native.parse_requirements(path)
            self.assertEqual(entries[:2], ["mcp>=1", "httpx # inline"])
            self.assertEqual(len(entries), 1002)
            path.write_bytes(b"\xff")
            with self.assertRaises(UnicodeDecodeError):
                native.parse_requirements(path)

    def test_real_lunar_and_registered_tools(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        import ast

        registration = ast.parse((ROOT / "scripts/mcp_server.py").read_text())
        self.assertTrue(
            any(
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "register_service_dependency_tools"
                and isinstance(node.args[0], ast.Name)
                and node.args[0].id == "mcp"
                for node in ast.walk(registration)
            )
        )
        document = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(document["id"], "hub_mcp_service_dependencies_workflow")
        self.assertEqual(document["policy"]["limits"]["max_operation_calls"], 20)
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        for mode in [
            "ready",
            "blocked",
            "optional",
            "missing_file",
            "error",
            "invalid_utf8",
        ]:
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "requirements-mcp-service.txt"
                if mode != "missing_file":
                    path.write_bytes(
                        b"\xff"
                        if mode == "invalid_utf8"
                        else b"# fixture\n\n mcp>=1 \nhttpx # inline\n"
                    )
                async with manager.open(
                    "dependencies",
                    StdioConfig(
                        command=sys.executable,
                        args=[
                            str(
                                ROOT
                                / "tests/mcp/fixtures/service_dependencies_server.py"
                            ),
                            mode,
                            directory,
                        ],
                        cwd=str(ROOT),
                    ),
                    {},
                ) as remote:
                    try:
                        tools = [
                            t.model_dump(by_alias=True, exclude_none=True)
                            for t in await remote.tools()
                        ]

                        async def authorize():
                            pass

                        async def run(doc):
                            assets = snapshot(doc)
                            compiled = compile_workflow(
                                "mcp:dependencies",
                                workflow_documents([DESCRIPTOR], assets)[0],
                                tools,
                            )
                            self.assertTrue(
                                compiled["runnable"], compiled["diagnostics"]
                            )
                            self.assertTrue(compiled["runtime_source"])
                            self.assertEqual(
                                set(compiled["bindings"]), set(doc["operations"])
                            )
                            return await execute(
                                compiled, assets, {}, remote, authorize
                            )

                        await remote.call("fixture_seen", {"reset": True})
                        result = await run(document)
                        if mode in ["error", "invalid_utf8"]:
                            self.assertEqual(result["status"], "failed", result)
                            self.assertIsNone(result["outputs"])
                            self.assertEqual(
                                [c["operation"] for c in result["calls"]],
                                (
                                    ["initialize", "package_next", "package_next"]
                                    if mode == "error"
                                    else ["initialize"]
                                    + ["package_next"] * 10
                                    + ["tool_next"] * 6
                                    + ["classify", "requirements"]
                                ),
                            )
                            self.assertEqual(result["calls"][-1]["status"], "rejected")
                            continue
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertEqual(len(result["calls"]), 20)
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["replay_artifacts"])
                        actual_seen = (await remote.call("fixture_seen", {}))["seen"]
                        oracle = await remote.call("fixture_original", {})
                        self.assertEqual(
                            result["outputs"], {"report": oracle["report"]}
                        )
                        self.assertEqual(oracle["exit_code"], 0)
                        self.assertEqual(actual_seen, oracle["seen"])
                        self.assertEqual(
                            actual_seen,
                            [
                                ["package", m["distribution"]]
                                for m in native.PYTHON_PACKAGES.values()
                            ]
                            + [["tool", n] for n in native.EXTERNAL_TOOLS],
                        )
                        report = result["outputs"]["report"]
                        self.assertTrue(report["ok"])
                        self.assertEqual(report["ready"], mode != "blocked")
                        self.assertEqual(
                            len(report["missing_required"]),
                            3 if mode == "blocked" else 0,
                        )
                        self.assertEqual(
                            report["requirements"],
                            (
                                []
                                if mode == "missing_file"
                                else ["mcp>=1", "httpx # inline"]
                            ),
                        )
                        if mode == "ready":
                            for index, bound in [(1, 9), (2, 5)]:
                                short = deepcopy(document)
                                short["flow"]["steps"][index]["max_iterations"] = bound
                                failed = await run(short)
                                self.assertEqual(failed["status"], "failed")
                                self.assertIsNone(failed["outputs"])
                                self.assertEqual(failed["failure_disposition"], "fail")
                                self.assertEqual(
                                    len(failed["calls"]),
                                    1 + bound + (10 if index == 2 else 0),
                                )
                            budget = deepcopy(document)
                            budget["policy"]["limits"]["max_operation_calls"] = 19
                            failed = await run(budget)
                            self.assertEqual(failed["status"], "failed")
                            self.assertIsNone(failed["outputs"])
                    except Exception:
                        import traceback

                        traceback.print_exc()
                        raise
        self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
