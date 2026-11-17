#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native equivalence, real registered MCP calls and PRISM compiler/runtime fixtures."""

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
import skill_projection_tools as adapter

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_meta_skills_skill_projections_workflow/workflow.yaml"
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


def put(root, path, value):
    p = root / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value))


def fixture(root, mode):
    rows = []
    for task, targets in [("a", ["z", "a"]), ("b", ["a", "b"])]:
        rows.append(
            dict(
                task_id=task,
                workflow_id="wf_" + task,
                reasoning_types=["z", "a", "z"],
                backend_families=["lean"],
                formal_system_targets=targets,
                object_domains=["numbers"],
                risk_classes=["low"],
            )
        )
    # Last duplicate coordinate wins.
    put(
        root,
        "meta_skills/taxonomy/workflow_taxonomy.json",
        {"workflow_coordinates": [dict(rows[0], workflow_id="overwritten"), *rows]},
    )
    if mode != "empty":
        for name, skills in [
            (
                "a",
                (
                    ["z_missing", "known", "a_missing"]
                    if mode == "missing"
                    else ["known", "known"]
                ),
            ),
            ("b", ["known"]),
        ]:
            put(
                root,
                f"meta_skills/registry/tasks/{name}/task_registry.json",
                {"task_id": name, "composed_skills": [{"skill_id": s} for s in skills]},
            )
        put(
            root,
            "meta_skills/registry/tasks/0/task_registry.json",
            {"task_id": "_template", "composed_skills": [{}]},
        )
        put(
            root,
            "meta_skills/registry/tasks/c/task_registry.json",
            {"task_id": "no_coord", "composed_skills": [{}]},
        )
    if mode == "bad_json":
        (root / "meta_skills/registry/tasks/a/task_registry.json").write_text("{")
    if mode == "bad_key":
        put(root, "meta_skills/registry/tasks/a/task_registry.json", {})
    path = root / "skills/theme/known/SKILL.md"
    path.parent.mkdir(parents=True)
    path.write_text("fixture")
    if mode == "card_write_failure":
        (root / "cards.json").mkdir()
    if mode == "bad_taxonomy":
        put(root, "meta_skills/taxonomy/workflow_taxonomy.json", {})
    if mode == "write_failure":
        (root / "report.json").mkdir()
    ids = [] if mode == "empty" else ["known"]
    if mode == "missing":
        ids = ["z_missing", "known", "a_missing"]
    return {
        "source": {
            "registry_paths": [
                p.relative_to(root).as_posix()
                for p in sorted(
                    (root / "meta_skills/registry/tasks").glob("*/task_registry.json")
                )
            ],
            "projected_skill_ids": ids,
        },
        "destinations": {"output_path": "cards.json", "report_path": "report.json"},
        "repository_root": str(root),
    }


def oracle(root):
    scope = {
        "__file__": str(ROOT / "meta_skills/scripts/build_skill_projections.py"),
        "__name__": "original",
    }
    exec(
        (ROOT / "tests/mcp/fixtures/skill_projections_original.py.txt").read_text(),
        scope,
    )
    scope.update(
        REPO_ROOT=root,
        TAXONOMY_PATH=root / "meta_skills/taxonomy/workflow_taxonomy.json",
        TASK_ROOT=root / "meta_skills/registry/tasks",
    )
    return scope["build"](root / "cards.json", root / "report.json")


class ProjectionTests(unittest.TestCase):
    def test_native_state_and_domain(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            fixture(root, "missing")
            state = adapter.native.initialize_build(
                root / "cards.json", root / "report.json", root
            )
            original_count = len(state["registries"])
            for i in range(original_count):
                result = adapter.native.registry_iteration(state)
                self.assertEqual(len(state["registries"]), original_count - i - 1)
                self.assertEqual(result["done"], i == original_count - 1)
            self.assertEqual(state["card_order"], ["z_missing", "known", "a_missing"])
            self.assertEqual(
                state["cards"]["known"]["formal_system_targets"], ["z", "a", "b"]
            )
            adapter.native.prepare_card_pass(state)
            for i in range(3):
                self.assertEqual(adapter.native.card_iteration(state)["done"], i == 2)
            self.assertEqual(state["cards"]["known"]["task_ids"], ["a", "b"])
            self.assertEqual(
                [f.get("skill_id") for f in state["findings"][1:]],
                ["z_missing", "a_missing"],
            )
            previous = deepcopy(state)
            self.assertTrue(adapter.native.card_iteration(state)["done"])
            self.assertEqual(previous, state)
            self.assertTrue(adapter.native.registry_iteration(state)["done"])

    def test_refactored_entrypoint_and_limit(self):
        from unittest.mock import patch
        import contextlib
        import io

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            fixture(root, "missing")
            expected = oracle(root)
            cards = (root / "cards.json").read_bytes()
            with patch.multiple(
                adapter.native,
                REPO_ROOT=root,
                TAXONOMY_PATH=root / "meta_skills/taxonomy/workflow_taxonomy.json",
                TASK_ROOT=root / "meta_skills/registry/tasks",
            ):
                self.assertEqual(
                    adapter.native.build(root / "cards.json", root / "report.json"),
                    expected,
                )
                self.assertEqual((root / "cards.json").read_bytes(), cards)
                output = io.StringIO()
                with (
                    patch.object(
                        sys,
                        "argv",
                        [
                            "build",
                            "--json",
                            "--output",
                            str(root / "cards.json"),
                            "--report",
                            str(root / "report.json"),
                        ],
                    ),
                    contextlib.redirect_stdout(output),
                ):
                    self.assertEqual(adapter.native.main(), 1)
                self.assertEqual(json.loads(output.getvalue()), expected)
            # The declared final iteration is a normal stop, with no extra source work.
            row = {
                "task_id": "a",
                "composed_skills": [{"skill_id": "s" + str(i)} for i in range(10000)],
            }
            put(root, "meta_skills/registry/tasks/a/task_registry.json", row)
            state = adapter.native.initialize_build(
                root / "cards.json", root / "report.json", root
            )
            while state["registries"]:
                adapter.native.registry_iteration(state)
            adapter.native.prepare_card_pass(state)
            self.assertEqual(
                len(state["pending_cards"]), 10001
            )  # known from b plus 10000 from a
            # Native build has no numeric cap; adapters restrict the published domain.
            state["pending_cards"].remove("known")
            for i in range(10000):
                self.assertEqual(
                    adapter.native.card_iteration(state)["done"], i == 9999
                )

    def test_real_lunar(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        import ast

        tree = ast.parse((ROOT / "scripts/mcp_server.py").read_text())
        self.assertTrue(
            any(
                isinstance(n, ast.Call)
                and isinstance(n.func, ast.Name)
                and n.func.id == "register_skill_projection_tools"
                for n in ast.walk(tree)
            )
        )
        document = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(document["id"], "hub_meta_skills_skill_projections_workflow")
        authored = (
            ROOT
            / "skills/control/workflow-contract-validator/references/skill-projections.workflow.json"
        )
        self.assertEqual(json.loads(authored.read_text()), document)
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        async with manager.open(
            "projections",
            StdioConfig(
                command=sys.executable,
                args=[str(ROOT / "tests/mcp/fixtures/skill_projections_server.py")],
                cwd=str(ROOT),
            ),
            {},
        ) as remote:
            try:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                async def run(doc, inputs):
                    assets = snapshot(doc)
                    compiled = compile_workflow(
                        "mcp:projections",
                        workflow_documents([DESCRIPTOR], assets)[0],
                        tools,
                    )
                    self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                    self.assertTrue(compiled["runtime_source"])
                    self.assertEqual(set(compiled["bindings"]), set(doc["operations"]))

                    async def allow():
                        pass

                    return await execute(compiled, assets, inputs, remote, allow)

                for mode in [
                    "ready",
                    "missing",
                    "empty",
                    "bad_json",
                    "bad_key",
                    "bad_taxonomy",
                    "card_write_failure",
                    "write_failure",
                ]:
                    with tempfile.TemporaryDirectory() as directory:
                        root = Path(directory).resolve()
                        inputs = fixture(root, mode)
                        expected_error = None
                        try:
                            expected = oracle(root)
                        except Exception as error:
                            expected_error = error
                        cards = (
                            (root / "cards.json").read_bytes()
                            if (root / "cards.json").is_file()
                            else None
                        )
                        report = (
                            (root / "report.json").read_bytes()
                            if (root / "report.json").is_file()
                            else None
                        )
                        for path in [root / "cards.json", root / "report.json"]:
                            if path.is_file():
                                path.unlink()
                        result = await run(document, inputs)
                        if expected_error:
                            self.assertEqual(result["status"], "failed", result)
                            self.assertIsNone(result["outputs"])
                            self.assertEqual(result["calls"][-1]["status"], "rejected")
                            if mode == "write_failure":
                                self.assertEqual(
                                    (root / "cards.json").read_bytes(), cards
                                )
                                self.assertEqual(
                                    result["calls"][-1]["operation"], "write_report"
                                )
                            elif mode == "card_write_failure":
                                self.assertTrue((root / "cards.json").is_dir())
                                self.assertFalse((root / "report.json").exists())
                                self.assertEqual(
                                    result["calls"][-1]["operation"], "write_cards"
                                )
                            elif mode == "bad_taxonomy":
                                self.assertEqual(len(result["calls"]), 1)
                                self.assertFalse((root / "cards.json").exists())
                            else:
                                self.assertFalse((root / "cards.json").exists())
                                self.assertEqual(
                                    len(result["calls"]), 3
                                )  # initialize, template, malformed a
                            continue
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertEqual(result["outputs"], {"report": expected})
                        self.assertEqual((root / "cards.json").read_bytes(), cards)
                        self.assertEqual((root / "report.json").read_bytes(), report)
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["replay_artifacts"])
                        self.assertEqual(expected["ok"], mode != "missing")
                        self.assertEqual(
                            len(result["calls"]),
                            (
                                6
                                if mode == "empty"
                                else 4 + 4 + (3 if mode == "missing" else 1)
                            ),
                        )
                        if mode == "ready":
                            payload = json.loads(cards)
                            self.assertEqual(
                                payload["cards"][0]["formal_system_targets"],
                                ["z", "a", "b"],
                            )
                            self.assertEqual(
                                payload["cards"][0]["workflow_ids"], ["wf_a", "wf_b"]
                            )
                            for index, bound in [(1, 3), (3, 1)]:
                                short = deepcopy(document)
                                short["flow"]["steps"][index]["max_iterations"] = bound
                                # Card pass with one item succeeds exactly at its bound.
                                r = await run(short, inputs)
                                self.assertEqual(
                                    r["status"],
                                    "accepted" if index == 3 else "failed",
                                    r,
                                )
                                if index == 1:
                                    self.assertEqual(r["failure_disposition"], "fail")
                            exact = deepcopy(document)
                            exact["flow"]["steps"][1]["max_iterations"] = 4
                            self.assertEqual(
                                (await run(exact, inputs))["status"], "accepted"
                            )
                            budget = deepcopy(document)
                            budget["policy"]["limits"]["max_operation_calls"] = 8
                            self.assertEqual(
                                (await run(budget, inputs))["status"], "failed"
                            )
                            invalid = deepcopy(inputs)
                            invalid["source"]["registry_paths"] = []
                            r = await run(document, invalid)
                            self.assertEqual(r["status"], "failed")
                            self.assertEqual(len(r["calls"]), 1)
                            invalid = deepcopy(inputs)
                            invalid["source"]["projected_skill_ids"] = []
                            r = await run(document, invalid)
                            self.assertEqual(r["status"], "failed")
                            self.assertEqual(
                                r["calls"][-1]["operation"], "prepare_card_pass"
                            )
                        if mode == "missing":
                            short = deepcopy(document)
                            short["flow"]["steps"][3]["max_iterations"] = 2
                            r = await run(short, inputs)
                            self.assertEqual(r["status"], "failed")
                            self.assertEqual(r["failure_disposition"], "fail")
                with tempfile.TemporaryDirectory() as directory:
                    inputs = fixture(Path(directory).resolve(), "empty")
                    inputs["source"]["projected_skill_ids"] = [
                        "s" + str(i) for i in range(10001)
                    ]
                    # Direct callable enforces the same domain even outside the typed runtime.
                    from mcp_connections.client import MCPConnectionError

                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_skill_projections_initialize", inputs
                        )
            except Exception:
                import traceback

                traceback.print_exc()
                raise
        self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
