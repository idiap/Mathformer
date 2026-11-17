#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic filesystem fixtures, production MCP tools, real Lunar/PRISM runtime."""

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
import importlib.util
from importlib.machinery import SourceFileLoader
import json
import tempfile
import unittest
import yaml
from mcp_boundary_tools import source
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_meta_skills_mcp_boundary_workflow/workflow.yaml"
DENIALS = [
    "per_generated_skill_mcp_tools",
    "direct_draft_skill_execution",
    "skill_environment_api_key_loading",
]


def oracle():
    path = ROOT / "tests/mcp/fixtures/mcp_boundary_original.py.txt"
    spec = importlib.util.spec_from_loader(
        "boundary_original", SourceFileLoader("boundary_original", str(path))
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def configure(module, root):
    module.REPO_ROOT = root
    module.WORKFLOW_ACTIONS = root / "meta_skills/registry/workflow_actions.yaml"
    module.OUTPUT_PATH = root / "artifacts/mcp/meta_skill_service_self_test.json"


def fixture(root, rows, good=True):
    data = {
        "workflow_actions": rows,
        "allowed_mcp_tools": ["mathformer_fixture"],
        "denied_surfaces": DENIALS if good else [],
    }
    path = root / "meta_skills/registry/workflow_actions.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))
    server = root / "scripts/mcp_server.py"
    server.parent.mkdir(exist_ok=True)
    server.write_text(
        "def mathformer_fixture(): pass\ndef mathformer_fixture(): pass\n"
        if good
        else "def mathformer_other(): pass\n"
    )
    if good:
        docs = root / "config/README.md"
        docs.parent.mkdir(exist_ok=True)
        docs.write_bytes(b"CONFIG/ central API KEY\xff")
    return data


def snapshot(doc):
    def asset(path, text):
        return {
            "path": path,
            "content": text,
            "encoding": "text",
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
        }

    return [asset(DESCRIPTOR, json.dumps(doc))] + [
        asset(r["path"], (ROOT / r["path"]).read_text())
        for r in doc["provenance"]["sources"]
    ]


class BoundaryTests(unittest.TestCase):
    def test_original_entrypoint_and_shared_steps(self):
        native, original = source(), oracle()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            saved = (native.REPO_ROOT, native.WORKFLOW_ACTIONS, native.OUTPUT_PATH)
            try:
                for good, rows in [
                    (True, []),
                    (
                        True,
                        [
                            {
                                "action_id": "meta-skills:mcp-boundary",
                                "draft_skill_execution": "denied",
                            }
                        ],
                    ),
                    (
                        True,
                        [
                            {
                                "action_id": "meta-skills:mcp-boundary",
                                "draft_skill_execution": "denied",
                            }
                        ]
                        * 1024,
                    ),
                    (
                        False,
                        [
                            {"action_id": "absent"},
                            {"action_id": "meta-skills:mcp-boundary"},
                        ],
                    ),
                ]:
                    fixture(root, rows, good)
                    if not good:
                        (root / "config/README.md").unlink()
                    configure(native, root)
                    configure(original, root)
                    expected = original.run()
                    original_bytes = original.OUTPUT_PATH.read_bytes()
                    self.assertEqual(native.run(), expected)
                    self.assertEqual(native.OUTPUT_PATH.read_bytes(), original_bytes)
                    self.assertEqual(expected["ok"], good)
                    if not good:
                        self.assertEqual(
                            [f["code"] for f in expected["findings"]],
                            [
                                "unknown_meta_workflow_action",
                                "draft_skill_execution_not_denied",
                                "draft_skill_execution_not_denied",
                                "mcp_tool_set_mismatch",
                                "config_api_key_docs_missing",
                                "missing_denied_surfaces",
                            ],
                        )
                # Both entrypoints terminate on invalid JSON before registry or write.
                native.WORKFLOW_ACTIONS.write_text("{")
                for module in (original, native):
                    with self.assertRaises(json.JSONDecodeError):
                        module.run()
            finally:
                native.REPO_ROOT, native.WORKFLOW_ACTIONS, native.OUTPUT_PATH = saved

    def test_registered_tools_and_real_lunar(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        doc = yaml.safe_load(Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text())
        self.assertEqual(doc["id"], "hub_meta_skills_mcp_boundary_workflow")
        self.assertEqual(doc["lifecycle"], "active")
        for row in doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        base = ROOT / "artifacts/workflow_hub"
        base.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix="boundary-fixture-", dir=base
        ) as temporary:
            root = Path(temporary)
            manager = SessionManager()
            server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
            async with manager.open(
                "boundary",
                StdioConfig(
                    command=str(ROOT / ".venv/bin/python"),
                    args=["-c", server],
                    cwd=str(ROOT),
                ),
                {},
            ) as remote:
                failure = None
                try:
                    tools = [
                        t.model_dump(by_alias=True, exclude_none=True)
                        for t in await remote.tools()
                    ]

                    def compile(document, inventory=tools):
                        assets = snapshot(document)
                        result = compile_workflow(
                            "mcp:boundary",
                            workflow_documents([DESCRIPTOR], assets)[0],
                            inventory,
                        )
                        return result, assets

                    workflow, assets = compile(doc)
                    self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                    self.assertTrue(workflow["runtime_source"])
                    self.assertEqual(set(workflow["bindings"]), set(doc["operations"]))
                    self.assertFalse(compile(doc, [])[0]["runnable"])

                    async def authorize():
                        pass

                    async def run(document=doc):
                        selected, received = compile(document)
                        return await execute(
                            selected,
                            received,
                            {
                                "scope": {"max_workflow_actions": 1024},
                                "repository_root": str(root),
                            },
                            remote,
                            authorize,
                        )

                    original = oracle()
                    configure(original, root)
                    for good, rows in [
                        (True, []),
                        (
                            True,
                            [
                                {
                                    "action_id": "meta-skills:mcp-boundary",
                                    "draft_skill_execution": "denied",
                                }
                            ],
                        ),
                        (
                            False,
                            [{"action_id": "absent"}, {"action_id": "also-absent"}],
                        ),
                    ]:
                        fixture(root, rows, good)
                        if not good:
                            (root / "config/README.md").unlink()
                        expected = original.run()
                        expected_bytes = original.OUTPUT_PATH.read_bytes()
                        original.OUTPUT_PATH.unlink()
                        result = await run()
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertEqual(result["outputs"], {"result": expected})
                        self.assertEqual(
                            original.OUTPUT_PATH.read_bytes(), expected_bytes
                        )
                        self.assertEqual(
                            [c["tool"] for c in result["calls"]],
                            ["mathformer_boundary_load"]
                            + (
                                ["mathformer_boundary_action"] * len(rows)
                                if rows
                                else ["mathformer_boundary_empty"]
                            )
                            + [
                                "mathformer_boundary_tools",
                                "mathformer_boundary_docs",
                                "mathformer_boundary_denials",
                                "mathformer_boundary_write",
                            ],
                        )
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["replay_artifacts"])
                    fixture(root, [{"action_id": "absent"}, {"action_id": "another"}])
                    original.OUTPUT_PATH.unlink()
                    exhausted = deepcopy(doc)
                    exhausted["flow"]["steps"][1]["max_iterations"] = 1
                    failed = await run(exhausted)
                    self.assertEqual(failed["status"], "failed", failed)
                    self.assertIsNone(failed["outputs"])
                    self.assertEqual(len(failed["calls"]), 2)
                    self.assertFalse(original.OUTPUT_PATH.exists())
                    bounded = deepcopy(doc)
                    bounded["policy"]["limits"]["max_operation_calls"] = 2
                    failed = await run(bounded)
                    self.assertEqual(failed["status"], "failed")
                    self.assertIn("budget", str(failed).lower())
                    self.assertFalse(original.OUTPUT_PATH.exists())
                    # Real IO/parse/write exceptions propagate with no downstream calls or retries.
                    original.WORKFLOW_ACTIONS.write_text("{")
                    failed = await run()
                    self.assertEqual(failed["status"], "failed")
                    self.assertEqual(len(failed["calls"]), 1)
                    fixture(root, [])
                    original.OUTPUT_PATH.mkdir()
                    failed = await run()
                    self.assertEqual(failed["status"], "failed")
                    self.assertEqual(len(failed["calls"]), 6)
                    self.assertEqual(failed["calls"][-1]["status"], "rejected")
                    original.OUTPUT_PATH.rmdir()
                    fixture(root, [{}] * 1025)
                    failed = await run()
                    self.assertEqual(failed["status"], "failed")
                    self.assertEqual(len(failed["calls"]), 1)
                    self.assertFalse(original.OUTPUT_PATH.exists())
                    # Exercise the exact terminal cursor in the production tool. Earlier
                    # rows have already been accumulated; the 1024th row must return done.
                    answer = await remote.call(
                        "mathformer_boundary_action",
                        {
                            "data": {"workflow_actions": [{}] * 1024},
                            "registry": [],
                            "state": {
                                "cursor": 1023,
                                "findings": [{"severity": "error", "code": "prior"}],
                            },
                        },
                    )
                    self.assertTrue(answer["done"])
                    self.assertEqual(answer["state"]["cursor"], 1024)
                    self.assertEqual(
                        [f["code"] for f in answer["findings"]],
                        [
                            "prior",
                            "unknown_meta_workflow_action",
                            "draft_skill_execution_not_denied",
                        ],
                    )
                except Exception as error:
                    failure = error
            self.assertFalse(manager.active)
            if failure:
                raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
