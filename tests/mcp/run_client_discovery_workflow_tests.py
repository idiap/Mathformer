#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Filesystem fixtures through native code, registered MCP and real Lunar/PRISM.

This workflow has no model/provider or external compiler boundary to replace.
Only temporary filesystem inputs are used; no production workflow is run.
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
from client_discovery_tools import source
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_skills_client_discovery_workflow/workflow.yaml"


def oracle(root):
    path = ROOT / "tests/mcp/fixtures/client_discovery_original.py.txt"
    spec = importlib.util.spec_from_loader(
        "discovery_oracle", SourceFileLoader("discovery_oracle", str(path))
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.REPO_ROOT = root
    module.SKILLS_ROOT = root / "skills"
    module.CLIENT_TARGETS = {
        name: root / target.relative_to(source().REPO_ROOT)
        for name, target in source().CLIENT_TARGETS.items()
    }
    return module


def fixture(root):
    for name in sorted(source().REQUIRED_SMOKE_SKILLS | {"ordinary"}):
        directory = root / "skills/theme" / name
        directory.mkdir(parents=True)
        (directory / "SKILL.md").write_text(name)
    # Sorted later duplicate wins, exactly as the native map assignment.
    duplicate = root / "skills/z/ordinary"
    duplicate.mkdir(parents=True)
    (duplicate / "SKILL.md").write_text("last duplicate")
    canonical = source().canonical_skills(root / "skills")
    for relative in (".agents/skills", ".claude/skills", ".opencode/skills"):
        target = root / relative
        target.mkdir(parents=True)
        for name, directory in canonical.items():
            (target / name).symlink_to(directory, target_is_directory=True)
    return root


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


class DiscoveryTests(unittest.TestCase):
    def test_native_equivalence_cli_and_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = fixture(Path(directory))
            native, old = source(), oracle(root)
            self.assertEqual(
                native.canonical_skills(root / "skills"), old.canonical_skills()
            )
            self.assertEqual(
                native.canonical_skills(root / "skills")["ordinary"],
                root / "skills/z/ordinary",
            )
            self.assertEqual(native.build_report(root), old.build_report())
            canonical = {key: str(path) for key, path in old.canonical_skills().items()}
            state = native.initialize_discovery(canonical, root)
            history = []
            for index in range(3):
                previous = deepcopy(state)
                result = native.inspect_discovery_client(state)
                state, done = native.advance_discovery(state, result)
                history.append(result)
                self.assertEqual(state["cursor"], index + 1)
                self.assertEqual(done, index == 2)
                self.assertEqual(state["reports"], history)
                self.assertEqual(previous["cursor"], index)
                self.assertEqual(state["canonical"], canonical)
            self.assertEqual(native.aggregate_discovery(state), old.build_report())
            with self.assertRaises(IndexError):
                native.inspect_discovery_client(state)
            # Real CLI uses its default context. Change only filesystem context,
            # leaving every callable (including build_report) intact.
            for module in (native, old):
                context = {
                    "REPO_ROOT": root,
                    "SKILLS_ROOT": root / "skills",
                    "CLIENT_TARGETS": old.CLIENT_TARGETS,
                }
                # check_client's default root is intentionally explicit in shared traversal.
                with (
                    patch.multiple(module, **context),
                    patch.object(sys, "argv", ["discovery", "--json"]),
                ):
                    stream = io.StringIO()
                    with redirect_stdout(stream):
                        self.assertEqual(module.main(), 0)
                    self.assertEqual(json.loads(stream.getvalue()), old.build_report())
            # Missing roots preserve the JSON failure status and original human
            # branch KeyError instead of silently manufacturing expected_count.
            for target in old.CLIENT_TARGETS.values():
                for entry in target.iterdir():
                    entry.unlink()
                target.rmdir()
            expected = old.build_report()
            self.assertEqual(native.build_report(root), expected)
            for module in (native, old):
                with patch.multiple(
                    module,
                    REPO_ROOT=root,
                    SKILLS_ROOT=root / "skills",
                    CLIENT_TARGETS=old.CLIENT_TARGETS,
                ):
                    with patch.object(sys, "argv", ["discovery", "--json"]):
                        stream = io.StringIO()
                        with redirect_stdout(stream):
                            self.assertEqual(module.main(), 1)
                        self.assertEqual(json.loads(stream.getvalue()), expected)
                    with (
                        patch.object(sys, "argv", ["discovery"]),
                        redirect_stdout(io.StringIO()),
                    ):
                        with self.assertRaises(KeyError):
                            module.main()

    def test_registered_mcp_lunar_execution(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_skills_client_discovery_workflow")
        self.assertEqual(document["lifecycle"], "active")
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        # The focused production stdio entrypoint shares the exact registrar
        # installed in mcp_server, without loading unrelated backend packages.
        self.assertIn(
            "register_client_discovery_tools(mcp)",
            (ROOT / "scripts/mcp_server.py").read_text(),
        )
        manager = SessionManager()
        server = 'import runpy;runpy.run_path("scripts/client_discovery_tools.py", run_name="__main__")'
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            healthy = fixture(base / "healthy")
            missing = base / "missing"
            missing.mkdir()
            defects = fixture(base / "defects")
            # codex: extras skipped, broken canonical skips metadata, missing smoke.
            codex = defects / ".agents/skills"
            (codex / "ordinary").unlink()
            (codex / "ordinary").symlink_to(defects / "absent")
            smoke = sorted(source().REQUIRED_SMOKE_SKILLS)[0]
            (codex / smoke).unlink()
            (codex / "extra").symlink_to(defects / "absent-extra")
            # claude: noncanonical metadata missing blocks, opencode warning only.
            alternate = defects / "alternate"
            alternate.mkdir()
            claude = defects / ".claude/skills/ordinary"
            claude.unlink()
            claude.symlink_to(alternate)
            warning = defects / "warning"
            warning.mkdir()
            (warning / "SKILL.md").write_text("metadata")
            opencode = defects / ".opencode/skills/ordinary"
            opencode.unlink()
            opencode.symlink_to(warning)
            io_failure = base / "io-failure"
            (io_failure / ".agents").mkdir(parents=True)
            (io_failure / ".agents/skills").write_text("not a directory")
            async with manager.open(
                "discovery",
                StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
                {},
            ) as remote:
                tools = [
                    tool.model_dump(by_alias=True, exclude_none=True)
                    for tool in await remote.tools()
                ]

                def compile(doc, inventory=None):
                    assets = snapshot(doc)
                    selected = workflow_documents([DESCRIPTOR], assets)[0]
                    compiled = compile_workflow(
                        "mcp:discovery",
                        selected,
                        tools if inventory is None else inventory,
                    )
                    return compiled, assets

                workflow, assets = compile(document)
                self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                self.assertTrue(workflow["runtime_source"])
                self.assertEqual(set(workflow["bindings"]), set(document["operations"]))
                self.assertFalse(compile(document, [])[0]["runnable"])

                async def authorize():
                    pass

                async def run(root, doc=None):
                    selected, received = compile(doc) if doc else (workflow, assets)
                    self.assertTrue(selected["runnable"], selected["diagnostics"])
                    return await execute(
                        selected, received, {"repo_root": str(root)}, remote, authorize
                    )

                calls = (
                    ["collect", "initialize"] + ["check", "advance"] * 3 + ["aggregate"]
                )
                for root in (healthy, missing, defects):
                    result = await run(root)
                    self.assertEqual(result["status"], "accepted", result)
                    expected = oracle(root).build_report()
                    self.assertEqual(result["outputs"], {"report": expected})
                    self.assertEqual(source().build_report(root), expected)
                    self.assertEqual(
                        [c["tool"] for c in result["calls"]],
                        ["mathformer_client_discovery_" + name for name in calls],
                    )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["replay_artifacts"])
                report = source().build_report(defects)
                self.assertFalse(report["ok"])
                self.assertEqual(report["clients"][0]["broken_links"], ["ordinary"])
                self.assertEqual(report["clients"][0]["missing_skill_md"], [])
                self.assertIn(
                    "missing_required_smoke_skill:" + smoke,
                    report["clients"][0]["blockers"],
                )
                self.assertEqual(report["clients"][1]["missing_skill_md"], ["ordinary"])
                self.assertTrue(report["clients"][2]["ok"])
                self.assertEqual(
                    report["clients"][2]["warnings"], ["noncanonical_symlink_targets"]
                )
                missing_report = source().build_report(missing)
                self.assertEqual(
                    [r["client"] for r in missing_report["clients"]],
                    ["codex", "claude", "opencode"],
                )
                self.assertTrue(
                    all(
                        r["blockers"] == ["target_missing"]
                        for r in missing_report["clients"]
                    )
                )
                self.assertTrue(
                    all("expected_count" not in r for r in missing_report["clients"])
                )
                # Tool-level transport exposes state and genuine completion guard.
                canonical = await remote.call(
                    "mathformer_client_discovery_collect", {"repo_root": str(healthy)}
                )
                state = (
                    await remote.call(
                        "mathformer_client_discovery_initialize",
                        {**canonical, "repo_root": str(healthy)},
                    )
                )["state"]
                for index in range(3):
                    checked = await remote.call(
                        "mathformer_client_discovery_check", {"state": state}
                    )
                    advanced = await remote.call(
                        "mathformer_client_discovery_advance",
                        {"state": state, **checked},
                    )
                    self.assertEqual(advanced["done"], index == 2)
                    state = advanced["state"]
                    self.assertEqual(len(state["reports"]), index + 1)
                with self.assertRaises(OSError):
                    source().build_report(io_failure)
                failed = await run(io_failure)
                self.assertEqual(failed["status"], "failed", failed)
                self.assertIsNone(failed["outputs"])
                self.assertEqual(len(failed["calls"]), 3)
                self.assertEqual(failed["calls"][-1]["status"], "rejected")
                exhausted = deepcopy(document)
                exhausted["flow"]["steps"][2]["max_iterations"] = 2
                failed = await run(healthy, exhausted)
                self.assertEqual(failed["status"], "failed", failed)
                self.assertIsNone(failed["outputs"])
                self.assertEqual(len(failed["calls"]), 6)
                bounded = deepcopy(document)
                bounded["policy"]["limits"]["max_operation_calls"] = 8
                failed = await run(healthy, bounded)
                self.assertEqual(failed["status"], "failed", failed)
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in failed["calls"]
                    ),
                    8,
                )
                self.assertIn("budget", str(failed).lower())
        self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
