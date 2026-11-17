#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native fixture repositories through registered MCP ports and real PRISM.

The source has no provider/model or external compiler boundary to substitute.
All inputs are local deterministic fixtures; PRISM parsing/checking/compilation
and runtime are real. No production registries are validated or reports changed.
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
from copy import deepcopy
from contextlib import redirect_stdout
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import tempfile
import unittest
from unittest.mock import patch
import yaml
from task_registry_tools import source, register_task_registry_tools
from mcp.server.fastmcp import FastMCP
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute, ExecutionRejected

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_meta_skills_registry_validate_workflow/workflow.yaml"


def original():
    path = ROOT / "tests/mcp/fixtures/task_registries_original.py.txt"
    spec = importlib.util.spec_from_loader(
        "registry_oracle", SourceFileLoader("registry_oracle", str(path))
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def valid(task):
    schema = json.loads(
        (ROOT / "meta_skills/schemas/task_registry.schema.json").read_text()
    )
    data = {
        key: [{field: "fixture" for field in fields}]
        for key, fields in schema["nested_required"].items()
    }
    data.update(
        schema_version="mathformer.meta_skills.task_registry.v0.1",
        task_id=task,
        title="Fixture",
    )
    action = sorted(source().mathformer.build_registry())[0]
    data["controlled_actions"] = [{"action_id": action, "role": "validation"}]
    data["visible_workflows"][0]["entry_actions"] = [action]
    data["composed_skills"] = [{"skill_id": "present", "role": "validation"}]
    data["artifacts"] = [
        {"path": "missing-planned", "state": "planned"},
        {"path": "missing-generated", "state": "generated"},
        {"path": "existing", "state": "source"},
    ]
    data["validators"] = [
        {
            "command": "python never_execute_this.py",
            "expected_artifact": "artifacts/never.json",
        }
    ]
    data["generated_skills"] = [
        {"id": "draft", "state": "draft", "promotion_boundary": "requires review"}
    ]
    return data


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


class RegistryTests(unittest.TestCase):
    def setUp(self):
        base = ROOT / "artifacts/workflow_hub"
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="registry-fixture-", dir=base)
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def context(self, name, rows):
        root = self.directory / name
        (root / "meta_skills/schemas").mkdir(parents=True)
        (root / "meta_skills/registry/tasks").mkdir(parents=True)
        (root / "skills/group/present").mkdir(parents=True)
        (root / "skills/group/present/SKILL.md").write_text("fixture")
        (root / "existing").write_text("fixture")
        (root / "meta_skills/schemas/task_registry.schema.json").write_bytes(
            (ROOT / "meta_skills/schemas/task_registry.schema.json").read_bytes()
        )
        for task, data in rows.items():
            path = root / "meta_skills/registry/tasks" / task / "task_registry.json"
            path.parent.mkdir()
            path.write_text(json.dumps(data))
        return root

    def output(self, root):
        return root / "artifacts/meta_skills/task_registry_validation.json"

    def invoke(self, module, root, cli=False):
        with patch.multiple(
            module,
            REPO_ROOT=root,
            SCHEMA_PATH=root / "meta_skills/schemas/task_registry.schema.json",
            REGISTRY_ROOT=root / "meta_skills/registry/tasks",
            OUTPUT_PATH=self.output(root),
        ):
            if not cli:
                return module.run()
            stream = io.StringIO()
            with (
                patch.object(sys, "argv", ["registry", "--json"]),
                redirect_stdout(stream),
            ):
                code = module.main()
            return code, stream.getvalue()

    def test_native_equivalence_branches_and_cli(self):
        bad = valid("b")
        bad.update(schema_version="wrong", task_id="wrong")
        bad["controlled_actions"][0]["action_id"] = "unknown"
        bad["visible_workflows"][0]["entry_actions"] = ["unknown"]
        bad["composed_skills"][0]["skill_id"] = "missing"
        bad["artifacts"] = [{"path": "missing", "state": "invalid"}]
        bad["validators"] = [{"command": "echo never", "expected_artifact": "outside"}]
        bad["generated_skills"] = [
            {"id": "bad", "state": "invalid", "promotion_boundary": ""}
        ]
        bad["risk_controls"] = [1, {}]
        bad["release_boundaries"] = []
        root = self.context("equivalence", {"z": valid("z"), "a": {}, "b": bad})
        expected = self.invoke(original(), root)
        expected_bytes = self.output(root).read_bytes()
        self.assertEqual(self.invoke(source(), root), expected)
        self.assertEqual(self.output(root).read_bytes(), expected_bytes)
        self.assertEqual(
            [row["path"] for row in expected["results"]],
            [
                "meta_skills/registry/tasks/" + name + "/task_registry.json"
                for name in ["a", "b", "z"]
            ],
        )
        self.assertTrue(expected["results"][-1]["ok"])
        self.assertTrue(
            all(
                f["code"] == "missing_field" for f in expected["results"][0]["findings"]
            )
        )
        codes = {f["code"] for f in expected["results"][1]["findings"]}
        self.assertTrue(
            {
                "non_object_row",
                "missing_nested_field",
                "empty_collection",
                "unknown_action_id",
                "unknown_entry_action",
                "missing_skill",
                "invalid_artifact_state",
                "missing_artifact_path",
                "validator_not_python_command",
                "validator_expected_artifact_outside_artifacts",
                "invalid_generated_skill_state",
                "missing_generated_skill_promotion_boundary",
                "unexpected_schema_version",
                "task_id_directory_mismatch",
            }
            <= codes
        )
        self.assertEqual(
            self.invoke(source(), root, True), self.invoke(original(), root, True)
        )
        self.assertEqual(self.invoke(source(), root, True)[0], 1)
        for label, rows in [("empty", {}), ("good", {"one": valid("one")})]:
            root = self.context(label, rows)
            self.assertEqual(self.invoke(source(), root), self.invoke(original(), root))
            self.assertTrue(self.invoke(source(), root)["ok"])
            self.assertEqual(self.invoke(source(), root, True)[0], 0)

    def test_native_uncaught_errors_abort_without_report(self):
        for label, text, error in [
            ("parse", "{", json.JSONDecodeError),
            ("type", "1", TypeError),
            ("semantic", None, AttributeError),
        ]:
            root = self.context(
                label, {"a": valid("a"), "b": valid("b"), "z": valid("z")}
            )
            if text is None:
                data = valid("b")
                data["controlled_actions"] = [1]
                text = json.dumps(data)
            (root / "meta_skills/registry/tasks/b/task_registry.json").write_text(text)
            for module in (original(), source()):
                with self.assertRaises(error):
                    self.invoke(module, root)
                self.assertFalse(self.output(root).exists())

    def test_registered_write_policy(self):
        from mcp.shared.memory import create_connected_server_and_client_session

        async def scenario():
            root = self.context("readonly", {})

            def denied(path):
                raise ValueError("service is read-only")

            mcp = FastMCP("readonly")
            register_task_registry_tools(mcp, denied)
            async with create_connected_server_and_client_session(
                mcp._mcp_server
            ) as session:
                initialized = await session.call_tool(
                    "mathformer_task_registry_initialize",
                    {
                        "domain": {"discovered_registry_count": 0},
                        "repository_root": str(root),
                    },
                )
                state = initialized.structuredContent["state"]
                result = await session.call_tool(
                    "mathformer_task_registry_write_report", {"state": state}
                )
                self.assertTrue(result.isError)
                self.assertIn("read-only", str(result))
                self.assertFalse(self.output(root).exists())

        asyncio.run(scenario())

    def test_real_mcp_lunar(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_meta_skills_registry_validate_workflow")
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(document["policy"]["limits"]["max_operation_calls"], 10002)
        self.assertEqual(document["flow"]["steps"][1]["max_iterations"], 10000)
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp.server.fastmcp import FastMCP;from task_registry_tools import register_task_registry_tools;mcp=FastMCP("task-registry");register_task_registry_tools(mcp);mcp.run(transport="stdio")'
        failure = None
        async with manager.open(
            "registry",
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
                    workflow = compile_workflow(
                        "mcp:registry",
                        workflow_documents([DESCRIPTOR], assets)[0],
                        tools if inventory is None else inventory,
                    )
                    return workflow, assets

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
                        {
                            "repository_root": str(root),
                            "domain": {"discovered_registry_count": count},
                        },
                        remote,
                        authorize,
                    )

                for label, rows in [
                    ("empty", {}),
                    ("valid", {"z": valid("z"), "a": valid("a")}),
                    ("findings", {"a": {}, "z": valid("z")}),
                ]:
                    root = self.context("runtime-" + label, rows)
                    expected = self.invoke(original(), root)
                    expected_bytes = self.output(root).read_bytes()
                    self.output(root).unlink()
                    result = await run(root, len(rows))
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(result["outputs"], {"result": expected})
                    self.assertEqual(self.output(root).read_bytes(), expected_bytes)
                    names = (
                        ["mathformer_task_registry_initialize"]
                        + (
                            ["mathformer_task_registry_validate_accumulate"] * len(rows)
                            if rows
                            else ["mathformer_task_registry_empty_state"]
                        )
                        + ["mathformer_task_registry_write_report"]
                    )
                    self.assertEqual([c["tool"] for c in result["calls"]], names)
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["replay_artifacts"])
                root = self.context("state", {"z": valid("z"), "a": {}})
                initialized = await remote.call(
                    "mathformer_task_registry_initialize",
                    {
                        "domain": {"discovered_registry_count": 2},
                        "repository_root": str(root),
                    },
                )
                state = initialized["state"]
                self.assertTrue(initialized["has_work"])
                self.assertEqual(state["cursor"], 0)
                self.assertEqual(state["results"], [])
                self.assertEqual(state["all_findings"], [])
                fixed = deepcopy(
                    {k: state[k] for k in ["schema", "actions", "registry_paths"]}
                )
                first = await remote.call(
                    "mathformer_task_registry_validate_accumulate", {"state": state}
                )
                self.assertFalse(first["done"])
                self.assertEqual(first["state"]["cursor"], 1)
                self.assertFalse(first["state"]["results"][0]["ok"])
                second = await remote.call(
                    "mathformer_task_registry_validate_accumulate",
                    {"state": first["state"]},
                )
                self.assertTrue(second["done"])
                self.assertEqual(second["state"]["cursor"], 2)
                self.assertTrue(second["state"]["results"][1]["ok"])
                self.assertEqual(
                    second["state"]["all_findings"], first["state"]["all_findings"]
                )
                self.assertEqual({k: second["state"][k] for k in fixed}, fixed)
                self.assertFalse(self.output(root).exists())
                root = self.context("mismatch", {"a": valid("a")})
                for count in (0, 2):
                    self.assertEqual((await run(root, count))["status"], "failed")
                    self.assertFalse(self.output(root).exists())
                with self.assertRaises(ExecutionRejected):
                    await run(root, 10001)
                for label, text in [
                    ("parse", "{"),
                    ("type", "1"),
                    ("semantic", json.dumps({**valid("b"), "controlled_actions": [1]})),
                ]:
                    root = self.context(
                        "runtime-" + label,
                        {"a": valid("a"), "b": valid("b"), "z": valid("z")},
                    )
                    (
                        root / "meta_skills/registry/tasks/b/task_registry.json"
                    ).write_text(text)
                    result = await run(root, 3)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(len(result["calls"]), 3)
                    self.assertEqual(result["calls"][-1]["status"], "rejected")
                    self.assertFalse(self.output(root).exists())
                root = self.context("write-fail", {"a": valid("a")})
                self.output(root).mkdir(parents=True)
                result = await run(root, 1)
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(len(result["calls"]), 3)
                bounded = deepcopy(document)
                bounded["flow"]["steps"][1]["max_iterations"] = 1
                root = self.context("at-bound", {"a": valid("a")})
                self.assertEqual((await run(root, 1, bounded))["status"], "accepted")
                root = self.context("exhausted", {"a": valid("a"), "b": valid("b")})
                result = await run(root, 2, bounded)
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(len(result["calls"]), 2)
                self.assertIn("exhaust", str(result).lower())
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
