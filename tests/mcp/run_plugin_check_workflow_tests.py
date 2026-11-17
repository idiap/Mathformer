#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Temporary repository fixtures through original code, MCP and real PRISM.

No model/provider or external compiler is called by this deterministic workflow.
The actual Lunar parser/checker/compiler and runtime are exercised without stubs.
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
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
import hashlib
import io
import json
import tempfile
import unittest
from unittest.mock import patch
import yaml
import sync_agent_plugins as native
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_skills_plugin_check_workflow/workflow.yaml"
AUTHORED = (
    ROOT
    / "skills/control/workflow-contract-validator/references/plugin-check.workflow.json"
)


def digest(data):
    return "sha256:" + hashlib.sha256(data).hexdigest()


def put(root, path, content):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)


def fixture(root, mode):
    root.mkdir(parents=True, exist_ok=True)
    for path, text in [
        ("pyproject.toml", '[project]\nversion = "1.2.3"\n'),
        ("LICENSE", "MIT fixture\n"),
        ("LICENSES/MIT.txt", "MIT fixture\n"),
        (
            "skills/theme/ordinary/SKILL.md",
            "---\nname: ordinary\ndescription: Fixture\n---\n\nSPDX-FileContributor: Example <example@example.com>\n",
        ),
    ]:
        put(root, path, text)
    if mode.startswith("catalog"):
        base = native.WORKFLOWS
        descriptor = "schema_version: workflow-skill/v1\n"
        row = dict(
            id="fixture_workflow",
            category="hub",
            aliases=["fixture:check"],
            description="Fixture workflow",
            owner_skill="skills/theme/ordinary/SKILL.md",
            path="hub/fixture/workflow.yaml",
            descriptor_digest=digest(descriptor.encode()),
        )
        put(root, base / row["path"], descriptor)
        if mode == "catalog_digest":
            row["descriptor_digest"] = "sha256:" + "0" * 64
        if mode == "catalog_escape":
            row["path"] = "../outside.yaml"
        put(
            root,
            base / "catalog.json",
            json.dumps(
                dict(
                    schema_version="mathformer.normalized-workflow-catalog/v1",
                    counts={"hub": 1},
                    workflows=[row],
                )
            ),
        )
        put(root, base / "hub-interface.schema.json", "{}\n")
        put(root, base.parent / "workflow.schema.json", "{}\n")
    if mode == "missing_catalog":
        put(root, native.WORKFLOWS.parent / "workflow.schema.json", "{}")
    if mode == "malformed":
        put(root, "skills/theme/ordinary/SKILL.md", "no frontmatter")
    if mode == "duplicate":
        put(
            root,
            "skills/other/ordinary/SKILL.md",
            "---\nname: ordinary\ndescription: Duplicate\n---\n",
        )
    if mode == "mismatch":
        put(
            root,
            "skills/theme/ordinary/SKILL.md",
            "---\nname: wrong\ndescription: Wrong\n---\n",
        )
    if mode == "no_skills":
        (root / "skills/theme/ordinary/SKILL.md").unlink()
    if mode == "io_error":
        (root / "LICENSE").unlink()
        (root / "LICENSE").mkdir()
    if mode in (
        "parity",
        "changed",
        "stale",
        "catalog",
        "comparison_failure",
        "destination_directory",
    ):
        # Materialize test data only; never invoke the mutating production branch.
        for path, text in native.expected_files(root).items():
            put(root, path, text)
        if mode == "changed":
            (root / native.PLUGIN / ".codex-plugin/plugin.json").write_text("different")
            (root / native.PLUGIN / "LICENSE").unlink()
        if mode == "comparison_failure":
            (root / native.PLUGIN / "LICENSE").write_bytes(b"\xff")
        if mode == "destination_directory":
            (root / native.PLUGIN / "LICENSE").unlink()
            (root / native.PLUGIN / "LICENSE").mkdir()
        if mode == "stale":
            for name in ["z-stale", "a-stale"]:
                put(root, native.PLUGIN / "skills" / name / "SKILL.md", "unmanaged")
    return root


def oracle():
    scope = {
        "__file__": str(ROOT / "scripts/sync_agent_plugins.py"),
        "__name__": "original_plugin_check",
    }
    exec((ROOT / "tests/mcp/fixtures/plugin_check_original.py.txt").read_text(), scope)
    return scope


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


def tree(root):
    return {
        str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()
    }


class PluginCheckTests(unittest.TestCase):
    def test_original_entrypoint_equivalence(self):
        old = oracle()
        for mode in [
            "parity",
            "missing",
            "changed",
            "stale",
            "catalog",
            "malformed",
            "duplicate",
            "mismatch",
            "no_skills",
            "missing_catalog",
            "catalog_escape",
            "catalog_digest",
            "io_error",
            "comparison_failure",
            "destination_directory",
        ]:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = fixture(Path(directory), mode)
                before = tree(root)
                error = None
                try:
                    expected = old["synchronize"](root, check=True)
                except (OSError, ValueError) as e:
                    error = e
                if error:
                    with self.assertRaises(type(error)):
                        native.synchronize(root, check=True)
                else:
                    self.assertEqual(native.synchronize(root, check=True), expected)
                    projection = native.expected_files(root)
                    self.assertEqual(
                        list(projection), list(old["expected_files"](root))
                    )
                    self.assertEqual(projection, old["expected_files"](root))
                    self.assertEqual(
                        native.compare_projection(
                            root, projection, native.find_stale(root, projection)
                        ),
                        expected,
                    )
                # Exercise real main and source-owned stdout/stderr and exit behavior.
                for main, context in [
                    (old["main"], patch.dict(old, REPO_ROOT=root)),
                    (native.main, patch.object(native, "REPO_ROOT", root)),
                ]:
                    out, err = io.StringIO(), io.StringIO()
                    with (
                        context,
                        patch.object(sys, "argv", ["sync", "--check"]),
                        redirect_stdout(out),
                        redirect_stderr(err),
                    ):
                        if error:
                            with self.assertRaises(SystemExit) as raised:
                                main()
                            self.assertEqual(raised.exception.code, 1)
                            self.assertEqual(out.getvalue(), "")
                            self.assertTrue(err.getvalue())
                        else:
                            self.assertEqual(main(), int(bool(expected)))
                            self.assertEqual(
                                json.loads(out.getvalue()),
                                dict(ok=not expected, mode="check", changed=expected),
                            )
                self.assertEqual(tree(root), before)

    def test_registered_tools_real_lunar(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document, json.loads(AUTHORED.read_text()))
        self.assertEqual(document["id"], "hub_skills_plugin_check_workflow")
        self.assertEqual(document["lifecycle"], "active")
        for row in document["provenance"]["sources"]:
            self.assertEqual(row["digest"], digest((ROOT / row["path"]).read_bytes()))
        self.assertIn(
            "register_plugin_check_tools(mcp)",
            (ROOT / "scripts/mcp_server.py").read_text(),
        )
        manager = SessionManager()
        async with manager.open(
            "plugins",
            StdioConfig(
                command=sys.executable,
                args=[str(ROOT / "scripts/plugin_check_tools.py")],
                cwd=str(ROOT),
            ),
            {},
        ) as remote:
            tools = [
                t.model_dump(by_alias=True, exclude_none=True)
                for t in await remote.tools()
            ]

            def compile(doc, inventory=tools):
                assets = snapshot(doc)
                selected = workflow_documents([DESCRIPTOR], assets)[0]
                return compile_workflow("mcp:plugins", selected, inventory), assets

            workflow, assets = compile(document)
            self.assertTrue(workflow["runnable"], workflow["diagnostics"])
            self.assertTrue(workflow["runtime_source"])
            self.assertEqual(set(workflow["bindings"]), set(document["operations"]))
            self.assertFalse(compile(document, [])[0]["runnable"])

            async def allow():
                pass

            async def run(root, doc=document):
                compiled, received = compile(doc)
                self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                return await execute(
                    compiled, received, {"root": str(root)}, remote, allow
                )

            for mode in [
                "parity",
                "missing",
                "changed",
                "stale",
                "catalog",
                "malformed",
                "duplicate",
                "mismatch",
                "no_skills",
                "missing_catalog",
                "catalog_escape",
                "catalog_digest",
                "io_error",
                "comparison_failure",
                "destination_directory",
            ]:
                with (
                    self.subTest(mode=mode),
                    tempfile.TemporaryDirectory() as directory,
                ):
                    root = fixture(Path(directory), mode)
                    before = tree(root)
                    try:
                        expected = oracle()["synchronize"](root, check=True)
                    except (OSError, ValueError):
                        expected = None
                    result = await run(root)
                    self.assertEqual(tree(root), before)
                    if expected is None:
                        self.assertEqual(result["status"], "failed", result)
                        self.assertIsNone(result["outputs"])
                        self.assertEqual(
                            len(result["calls"]),
                            3 if mode == "comparison_failure" else 1,
                        )
                        self.assertEqual(result["calls"][-1]["status"], "rejected")
                        continue
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(
                        result["outputs"],
                        {
                            "differences": expected,
                            "result": dict(
                                ok=not expected,
                                mode="check",
                                changed=expected,
                                exit_code=int(bool(expected)),
                            ),
                        },
                    )
                    self.assertEqual(
                        [c["tool"] for c in result["calls"]],
                        [
                            "mathformer_plugin_check_" + n
                            for n in ["project", "find_stale", "compare", "report"]
                        ],
                    )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["replay_artifacts"])
                    projection = await remote.call(
                        "mathformer_plugin_check_project", {"root": str(root)}
                    )
                    self.assertEqual(
                        projection["expected_order"],
                        [str(p) for p in native.expected_files(root)],
                    )
                    self.assertEqual(
                        projection["expected"],
                        {str(p): v for p, v in native.expected_files(root).items()},
                    )
                    if mode == "stale":
                        self.assertEqual(
                            expected,
                            [
                                "plugins/mathformer/skills/a-stale/SKILL.md",
                                "plugins/mathformer/skills/z-stale/SKILL.md",
                            ],
                        )
                    if mode == "parity":
                        bounded = deepcopy(document)
                        bounded["policy"]["limits"]["max_operation_calls"] = 3
                        failed = await run(root, bounded)
                        self.assertEqual(failed["status"], "failed", failed)
                        self.assertIsNone(failed["outputs"])
                        self.assertEqual(len(failed["calls"]), 4)
                        self.assertEqual(failed["calls"][-1]["status"], "rejected")
                        self.assertIn("budget", failed["calls"][-1]["error"].lower())
                        self.assertEqual(
                            sum(
                                bool(c.get("transport_call_performed"))
                                for c in failed["calls"]
                            ),
                            3,
                        )
        self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
