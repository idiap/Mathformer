#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native filesystem fixtures through registered MCP and real Lunar/PRISM."""

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
import json
import tempfile
import unittest
from unittest.mock import patch
import yaml
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute
from generated_lifecycle_tools import source, register_generated_lifecycle_tools

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_meta_skills_generated_lifecycle_workflow/workflow.yaml"
DOCUMENT = yaml.safe_load(Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text())


def asset(path, text):
    return dict(
        path=path,
        content=text,
        encoding="text",
        sha256=hashlib.sha256(text.encode()).hexdigest(),
    )


def fixture(root, mode):
    schema_path = root / "meta_skills/schemas/generated_skill_lifecycle.schema.json"
    schema_path.parent.mkdir(parents=True)
    schema = json.loads((ROOT / schema_path.relative_to(root)).read_text())
    schema_path.write_text(json.dumps(schema))
    base = root / "meta_skills/registry/generated_skills"
    base.mkdir(parents=True)
    if mode == "empty":
        return
    for name in ["z_valid", "a_first", "m_middle"]:
        folder = base / name
        folder.mkdir()
        data = {key: [] for key in schema["required"]}
        data.update(
            state="task_local_validated",
            promotion_gate={key: False for key in schema["promotion_gate_required"]},
        )
        data["promotion_gate"].update(
            target_state="task_local_validated",
            required_repeated_use_count=2,
            observed_repeated_use_count=0,
        )
        for artifact in schema["required_artifacts_for_task_local_validation"]:
            (folder / artifact).write_text("{}")
        if mode == "findings" and name == "a_first":
            data = {}  # Early return must suppress artifact/defect/gate checks.
            (folder / "seeded_defect_result.json").write_text("{broken")
        if mode == "findings" and name == "m_middle":
            data.update(
                state="draft",
                promotion_gate={"target_state": "promoted", "allowed": True},
            )
            (folder / "SKILL.md").unlink()
            (folder / "seeded_defect_result.json").write_text(
                '{"accepted_defect":true}'
            )
        if mode == "invalid_state" and name == "a_first":
            data["state"] = "unknown"
        (folder / "lifecycle.json").write_text(
            "{broken"
            if mode == "malformed" and name == "m_middle"
            else json.dumps(data)
        )


def native_run(root):
    module = source()
    with patch.multiple(
        module,
        REPO_ROOT=root,
        SCHEMA_PATH=root / "meta_skills/schemas/generated_skill_lifecycle.schema.json",
        GENERATED_ROOT=root / "meta_skills/registry/generated_skills",
        OUTPUT_PATH=root
        / "artifacts/meta_skills/generated_skill_lifecycle_validation.json",
    ):
        return module.run()


def original_run(root):
    # Frozen pre-extraction entrypoint is an independent behavioral oracle.
    from importlib.machinery import SourceFileLoader

    loader = SourceFileLoader(
        "_lifecycle_original",
        str(ROOT / "tests/mcp/fixtures/generated_lifecycle_original.py.txt"),
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    original = importlib.util.module_from_spec(spec)
    loader.exec_module(original)
    with patch.multiple(
        original,
        REPO_ROOT=root,
        SCHEMA_PATH=root / "meta_skills/schemas/generated_skill_lifecycle.schema.json",
        GENERATED_ROOT=root / "meta_skills/registry/generated_skills",
        OUTPUT_PATH=root
        / "artifacts/meta_skills/generated_skill_lifecycle_validation.json",
    ):
        return original.run()


class LifecycleTests(unittest.TestCase):
    def test_native_states_bounds_and_write_guard(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            fixture(root, "findings")
            context = {"repo_root": str(root)}
            native = source()
            with self.assertRaisesRegex(ValueError, "bound"):
                native.prepare(context, 2)
            prepared = native.prepare(context, 3)
            state = prepared["state"]
            for index in range(3):
                previous = deepcopy(state)
                findings = native.validate_record(prepared["schema"], state, context)[
                    "findings"
                ]
                advanced = native.accumulate(state, findings, context)
                self.assertEqual(state, previous)
                state = advanced["state"]
                self.assertEqual(state["cursor"], index + 1)
                self.assertEqual(advanced["done"], index == 2)
            with self.assertRaises(IndexError):
                native.validate_record(prepared["schema"], state, context)
            report = native.write_report(state, context)["report"]
            self.assertFalse(report["ok"])
            self.assertEqual(report["results"][-1]["findings"], [])
            self.assertEqual(
                {f["code"] for f in report["results"][0]["findings"]}, {"missing_field"}
            )
            self.assertEqual(
                {f["code"] for f in report["results"][1]["findings"]},
                {
                    "missing_lifecycle_artifact",
                    "seeded_defect_accepted",
                    "promotion_gate_missing_field",
                    "promotion_without_repeated_use",
                    "draft_promotion_gate_open",
                },
            )
            # Native run has no adapter cap; no production files are touched.
            self.assertEqual(native_run(root), report)
            from mcp.server.fastmcp import FastMCP

            server = FastMCP("guard")

            def deny():
                raise PermissionError("readonly")

            register_generated_lifecycle_tools(server, deny)

            async def guarded():
                response = await server.call_tool(
                    "mathformer_generated_lifecycle_write_report",
                    {"state": state, "context": context},
                )
                return response

            # FastMCP propagates the write guard as a ToolError.
            with self.assertRaisesRegex(Exception, "readonly"):
                asyncio.run(guarded())

    def test_registered_tools_real_compiler_runtime(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        self.assertIn(
            "register_generated_lifecycle_tools(mcp, _analysis_write_policy)",
            (ROOT / "scripts/mcp_server.py").read_text(),
        )
        for row in DOCUMENT["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        command = 'import sys;sys.path.insert(0,"scripts");from mcp.server.fastmcp import FastMCP;from generated_lifecycle_tools import register_generated_lifecycle_tools;mcp=FastMCP("lifecycle");register_generated_lifecycle_tools(mcp);mcp.run(transport="stdio")'
        manager = SessionManager()
        async with manager.open(
            "lifecycle",
            StdioConfig(command=sys.executable, args=["-c", command], cwd=str(ROOT)),
            {},
        ) as remote:
            try:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                async def run(document, context):
                    assets = [asset(DESCRIPTOR, json.dumps(document))] + [
                        asset(row["path"], (ROOT / row["path"]).read_text())
                        for row in {
                            r["path"]: r for r in document["provenance"]["sources"]
                        }.values()
                    ]
                    compiled = compile_workflow(
                        "mcp:lifecycle",
                        workflow_documents([DESCRIPTOR], assets)[0],
                        tools,
                    )
                    self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                    self.assertTrue(compiled["runtime_source"])
                    self.assertEqual(
                        set(compiled["bindings"]), set(document["operations"])
                    )

                    async def authorize():
                        pass

                    return await execute(
                        compiled,
                        assets,
                        {"context": context, "record_bound": 10000},
                        remote,
                        authorize,
                    )

                for mode in [
                    "empty",
                    "valid",
                    "findings",
                    "invalid_state",
                    "malformed",
                ]:
                    with tempfile.TemporaryDirectory() as directory:
                        root = Path(directory).resolve()
                        fixture(root, mode)
                        context = {"repo_root": str(root)}
                        output = (
                            root
                            / "artifacts/meta_skills/generated_skill_lifecycle_validation.json"
                        )
                        result = await run(DOCUMENT, context)
                        if mode == "malformed":
                            self.assertEqual(result["status"], "failed", result)
                            self.assertIsNone(result["outputs"])
                            self.assertFalse(output.exists())
                            self.assertEqual(
                                [c["operation"] for c in result["calls"]],
                                [
                                    "prepare",
                                    "validate_record",
                                    "accumulate",
                                    "validate_record",
                                ],
                            )
                            with self.assertRaises(json.JSONDecodeError):
                                native_run(root)
                            with self.assertRaises(json.JSONDecodeError):
                                original_run(root)
                            continue
                        self.assertEqual(result["status"], "accepted", result)
                        report = result["outputs"]["result"]
                        written = output.read_bytes()
                        self.assertEqual(json.loads(written), report)
                        self.assertEqual(report, native_run(root))
                        self.assertEqual(report, original_run(root))
                        self.assertEqual(output.read_bytes(), written)
                        self.assertEqual(report["ok"], mode == "valid")
                        self.assertEqual(
                            report["record_count"], 0 if mode == "empty" else 3
                        )
                        self.assertEqual(
                            len(result["calls"]), 4 if mode == "empty" else 8
                        )
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["replay_artifacts"])
                        if mode == "valid":
                            for limit, expected in [(2, "failed"), (3, "accepted")]:
                                altered = deepcopy(DOCUMENT)
                                altered["flow"]["steps"][1]["max_iterations"] = limit
                                output.unlink(missing_ok=True)
                                bounded = await run(altered, context)
                                self.assertEqual(bounded["status"], expected, bounded)
                                self.assertEqual(
                                    output.exists(), expected == "accepted"
                                )
                                self.assertEqual(
                                    len(bounded["calls"]), 5 if limit == 2 else 8
                                )
                            budget = deepcopy(DOCUMENT)
                            budget["policy"]["limits"]["max_operation_calls"] = 7
                            output.unlink(missing_ok=True)
                            failed = await run(budget, context)
                            self.assertEqual(failed["status"], "failed")
                            self.assertFalse(output.exists())
            except Exception:
                import traceback

                traceback.print_exc()
                raise
        self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
