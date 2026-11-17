#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Alias contract qualification using real registered native stages and Lunar."""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.dont_write_bytecode = True
sys.path[:0] = [str(LUNAR / "app/backend"), str(ROOT / "scripts"), str(ROOT)]
import asyncio
import importlib.util
import json
import tempfile
import unittest
import run_physics_release_gate_workflow_tests as shared
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute


class PhysicsLibReleaseTests(shared.ReleaseTests):
    expected_id = "hub_physics_lib_release_gate_workflow"

    def test_identity_policy_and_generator(self):
        doc = self.document
        self.assertEqual(doc["aliases"], ["physics-lib:release-gate"])
        self.assertEqual(
            doc["extensions"]["mathformer.source"]["native_id"],
            "physics-lib:release-gate",
        )
        authored = (
            ROOT
            / "skills/control/workflow-contract-validator/references/physics-lib-release-gate.workflow.json"
        )
        self.assertEqual(json.loads(authored.read_text()), doc)
        # Inspect the actual generator; never regenerate host-owned YAML/catalog.
        path = (
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py"
        )
        spec = importlib.util.spec_from_file_location(
            "release_contract_generator", path
        )
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)
        generated = next(
            item for item in generator.inventory() if item["id"] == self.expected_id
        )
        self.assertEqual(generated, doc)

    def test_source_read_failure_stops_before_assessment(self):
        asyncio.run(self.stopping_case("success"))

    def test_service_readonly_policy_prevents_compiler_launch(self):
        asyncio.run(self.stopping_case("readonly"))

    async def stopping_case(self, mode):
        async def allow():
            pass

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            shared.prepare(root, "success")
            if mode != "readonly":
                (root / "libraries/MathformerPhysicsLib.lean").unlink()
            manager = SessionManager()
            config = StdioConfig(
                command=sys.executable,
                args=[
                    "-B",
                    str(ROOT / "tests/mcp/fixtures/physics_release_server.py"),
                    mode,
                    str(root),
                ],
                cwd=str(ROOT),
            )
            async with shared.session(manager, config) as remote:
                tools = [
                    tool.model_dump(by_alias=True, exclude_none=True)
                    for tool in await remote.tools()
                ]
                assets = shared.snapshot(self.document)
                compiled = compile_workflow(
                    "mcp:release",
                    workflow_documents([assets[0]["path"]], assets)[0],
                    tools,
                )
                self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                output = root / "never-written.json"
                result = await execute(
                    compiled, assets, {"output": str(output)}, remote, allow
                )
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(
                    [call["operation"] for call in result["calls"]],
                    (
                        ["build_public_root"]
                        if mode == "readonly"
                        else [
                            "build_public_root",
                            "check_coherence",
                            "check_lean_version",
                            "imported_files",
                        ]
                    ),
                )
                self.assertFalse(output.exists())
                if mode == "readonly":
                    self.assertFalse((root / "commands.jsonl").exists())
                    self.assertEqual(result["calls"][0]["status"], "rejected")
                else:
                    self.assertEqual(
                        [
                            row[1]
                            for row in map(
                                json.loads,
                                (root / "commands.jsonl").read_text().splitlines(),
                            )
                        ],
                        [900, 180, 30],
                    )
            self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
