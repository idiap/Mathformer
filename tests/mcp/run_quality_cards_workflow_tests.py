#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic native/MCP/Lunar fixtures, with no provider or compiler substitutes.

This source has no external model or compiler boundary. The real PRISM compiler
and runtime are used; only filesystem input contexts are supplied as fixtures.
"""

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
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import tempfile
import unittest
from unittest.mock import patch
import yaml
from quality_card_tools import source, register_quality_card_tools
from mcp.server.fastmcp import FastMCP
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute, ExecutionRejected

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_meta_skills_quality_cards_workflow/workflow.yaml"
FIELDS = [
    "deterministic_boundary",
    "generative_boundary",
    "epistemic_risks",
    "necessary_conditions",
    "representation_contract",
    "validation_oracles",
    "failure_modes",
]


def original():
    path = ROOT / "tests/mcp/fixtures/quality_cards_original.py.txt"
    spec = importlib.util.spec_from_loader(
        "quality_cards_oracle", SourceFileLoader("quality_cards_oracle", str(path))
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def valid_card():
    return {
        "subject_type": "skill",
        "skill_path": "skills/present",
        **{key: ["python never_execute_this.py"] for key in FIELDS},
        "promotion_gate": {"blocking_conditions": ["unverified"], "required": True},
    }


def snapshot(document):
    def asset(path, content):
        return {
            "path": path,
            "content": content,
            "encoding": "text",
            "sha256": hashlib.sha256(content.encode()).hexdigest(),
        }

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(row["path"], (ROOT / row["path"]).read_text())
        for row in document["provenance"]["sources"]
    ]


class QualityCardTests(unittest.TestCase):
    def setUp(self):
        base = ROOT / "artifacts/workflow_hub"
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(
            prefix="quality-cards-fixture-", dir=base
        )
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.native = source()

    def context(self, name, cards):
        root = self.directory / name
        (root / "meta_skills/schemas").mkdir(parents=True)
        (root / "meta_skills/quality_cards").mkdir()
        (root / "skills/present").mkdir(parents=True)
        schema = {
            "required": ["subject_type", "skill_path", *FIELDS, "promotion_gate"],
            "allowed_subject_types": ["skill", "workflow"],
            "promotion_gate_required": ["blocking_conditions", "required"],
        }
        (root / "meta_skills/schemas/skill_quality_card.schema.json").write_text(
            json.dumps(schema)
        )
        for name, data in cards.items():
            path = root / "meta_skills/quality_cards" / name
            path.write_text(json.dumps(data))
        return root

    def output(self, root):
        return root / "artifacts/meta_skills/skill_quality_card_validation.json"

    def invoke(self, module, root, cli=False):
        with patch.multiple(
            module,
            REPO_ROOT=root,
            SCHEMA_PATH=root / "meta_skills/schemas/skill_quality_card.schema.json",
            CARD_ROOT=root / "meta_skills/quality_cards",
            OUTPUT_PATH=self.output(root),
        ):
            if cli:
                stream = io.StringIO()
                with (
                    patch.object(sys, "argv", ["quality-cards", "--json"]),
                    redirect_stdout(stream),
                ):
                    code = module.main()
                return code, stream.getvalue()
            return module.run()

    def test_native_equivalence_accumulation_early_return_and_cli(self):
        bad = valid_card()
        bad.update(
            subject_type="invalid",
            deterministic_boundary=[],
            promotion_gate={},
            validation_oracles=["echo must_not_run"],
        )
        root = self.context(
            "equivalence", {"z.yaml": valid_card(), "b.yaml": bad, "a.yaml": {}}
        )
        expected = self.invoke(original(), root)
        before = self.output(root).read_bytes()
        actual = self.invoke(self.native, root)
        self.assertEqual(actual, expected)
        self.assertEqual(self.output(root).read_bytes(), before)
        self.assertEqual(
            [r["path"] for r in actual["results"]],
            ["meta_skills/quality_cards/" + s for s in ["a.yaml", "b.yaml", "z.yaml"]],
        )
        self.assertTrue(actual["results"][-1]["ok"])
        self.assertTrue(
            all(f["code"] == "missing_field" for f in actual["results"][0]["findings"])
        )
        self.assertEqual(
            self.invoke(self.native, root, True), self.invoke(original(), root, True)
        )
        self.assertEqual(self.invoke(self.native, root, True)[0], 1)
        good = self.context("good-cli", {"one.yaml": valid_card()})
        self.assertEqual(self.invoke(self.native, good, True)[0], 0)
        empty = self.context("empty-native", {})
        self.assertEqual(
            self.invoke(self.native, empty), self.invoke(original(), empty)
        )
        self.assertFalse(self.invoke(self.native, empty)["ok"])

    def test_native_error_paths_and_field_checks(self):
        for label, value, error in [
            ("parse", None, json.JSONDecodeError),
            ("type", 1, TypeError),
        ]:
            root = self.context(
                label, {"a.yaml": valid_card(), "b.yaml": value, "c.yaml": valid_card()}
            )
            if label == "parse":
                (root / "meta_skills/quality_cards/b.yaml").write_text("{")
            for module in (original(), self.native):
                with self.assertRaises(error):
                    self.invoke(module, root)
                self.assertFalse(self.output(root).exists())
        card = valid_card()
        card.update(skill_path="missing", promotion_gate=[], validation_oracles=[7])
        root = self.context("oracle-type", {"one.yaml": card})
        for module in (original(), self.native):
            with self.assertRaises(AttributeError):
                self.invoke(module, root)
        card["validation_oracles"] = ["bad"]
        (root / "meta_skills/quality_cards/one.yaml").write_text(json.dumps(card))
        result = self.invoke(self.native, root)
        self.assertEqual(result, self.invoke(original(), root))
        self.assertEqual(
            [f["code"] for f in result["findings"]],
            [
                "missing_skill_path",
                "promotion_gate_not_object",
                "oracle_not_python_command",
            ],
        )

    def test_write_policy(self):
        from mcp.shared.memory import create_connected_server_and_client_session

        async def scenario():
            root = self.context("readonly", {"a.yaml": valid_card()})

            def denied(path):
                raise ValueError("service is read-only")

            mcp = FastMCP("readonly-fixture")
            register_quality_card_tools(mcp, denied)
            async with create_connected_server_and_client_session(
                mcp._mcp_server
            ) as session:
                initialized = await session.call_tool(
                    "mathformer_quality_cards_initialize",
                    {"repository_root": str(root), "discovered_card_count": 1},
                )
                state = initialized.structuredContent["state"]
                next_result = await session.call_tool(
                    "mathformer_quality_cards_validate_next", {"state": state}
                )
                result = await session.call_tool(
                    "mathformer_quality_cards_write_report",
                    {"state": next_result.structuredContent["state"]},
                )
                self.assertTrue(result.isError)
                self.assertIn("read-only", str(result))
                self.assertFalse(self.output(root).exists())

        asyncio.run(scenario())

    def test_real_mcp_lunar_compilation_execution_and_bounds(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_meta_skills_quality_cards_workflow")
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(document["policy"]["limits"]["max_operation_calls"], 10002)
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp.server.fastmcp import FastMCP;from quality_card_tools import register_quality_card_tools;mcp=FastMCP("quality-cards");register_quality_card_tools(mcp);mcp.run(transport="stdio")'
        failure = None
        async with manager.open(
            "quality-cards",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {},
        ) as remote:
            try:
                tools = [
                    tool.model_dump(by_alias=True, exclude_none=True)
                    for tool in await remote.tools()
                ]

                def compile(doc, inventory=None):
                    assets = snapshot(doc)
                    selected = workflow_documents([DESCRIPTOR], assets)[0]
                    qualified = compile_workflow(
                        "mcp:quality-cards",
                        selected,
                        tools if inventory is None else inventory,
                    )
                    return qualified, assets

                workflow, assets = compile(document)
                self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                self.assertTrue(workflow["runtime_source"])
                self.assertEqual(set(workflow["bindings"]), set(document["operations"]))
                self.assertFalse(compile(document, [])[0]["runnable"])

                async def authorize():
                    pass

                async def run(root, count, doc=None):
                    compiled, received = compile(doc) if doc else (workflow, assets)
                    return await execute(
                        compiled,
                        received,
                        {"repository_root": str(root), "discovered_card_count": count},
                        remote,
                        authorize,
                    )

                for label, cards in [
                    ("success", {"z.yaml": valid_card(), "a.yaml": valid_card()}),
                    ("findings", {"a.yaml": {}, "z.yaml": valid_card()}),
                    ("empty", {}),
                ]:
                    root = self.context("runtime-" + label, cards)
                    expected = self.invoke(original(), root)
                    expected_bytes = self.output(root).read_bytes()
                    self.output(root).unlink()
                    result = await run(root, len(cards))
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(result["outputs"], {"result": expected})
                    self.assertEqual(self.output(root).read_bytes(), expected_bytes)
                    self.assertEqual(
                        [c["tool"] for c in result["calls"]],
                        ["mathformer_quality_cards_initialize"]
                        + (
                            ["mathformer_quality_cards_validate_next"] * len(cards)
                            if cards
                            else ["mathformer_quality_cards_empty"]
                        )
                        + ["mathformer_quality_cards_write_report"],
                    )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["replay_artifacts"])
                root = self.context("mismatch", {"a.yaml": valid_card()})
                for count in (0, 2):
                    result = await run(root, count)
                    self.assertNotEqual(result["status"], "accepted", result)
                    self.assertFalse(self.output(root).exists())
                with self.assertRaises(ExecutionRejected):
                    await run(root, 10001)
                for label, bad in [("parse", "{"), ("type", "1")]:
                    root = self.context(
                        "runtime-" + label, {"a.yaml": valid_card(), "b.yaml": {}}
                    )
                    (root / "meta_skills/quality_cards/b.yaml").write_text(bad)
                    result = await run(root, 2)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(len(result["calls"]), 3)
                    self.assertEqual(result["calls"][-1]["status"], "rejected")
                    self.assertFalse(self.output(root).exists())
                root = self.context("write-failure", {"a.yaml": valid_card()})
                self.output(root).mkdir(parents=True)
                result = await run(root, 1)
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(len(result["calls"]), 3)
                self.assertEqual(result["calls"][-1]["status"], "rejected")
                bounded = deepcopy(document)
                bounded["flow"]["steps"][1]["max_iterations"] = 1
                root = self.context("last-bound", {"a.yaml": valid_card()})
                self.assertEqual((await run(root, 1, bounded))["status"], "accepted")
                root = self.context(
                    "exhaustion", {"a.yaml": valid_card(), "b.yaml": valid_card()}
                )
                result = await run(root, 2, bounded)
                self.assertEqual(result["status"], "failed", result)
                self.assertIn("exhaust", str(result).lower())
                self.assertEqual(len(result["calls"]), 2)
                self.assertFalse(self.output(root).exists())
                budget = deepcopy(document)
                budget["policy"]["limits"]["max_operation_calls"] = 1
                result = await run(root, 2, budget)
                self.assertEqual(result["status"], "failed", result)
                self.assertIn("budget", str(result).lower())
                self.assertFalse(self.output(root).exists())
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
