#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Real filesystem, MCP, PRISM parser/checker/compiler and runtime fixtures.

The source has no provider/model or external compiler boundary to substitute.
Only temporary repositories are inspected or repaired, never production layout.
"""

from tempfile import gettempdir

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
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import tempfile
import unittest
from unittest.mock import patch
import yaml
import organize_repository_layout as native
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_control_thematic_layout_workflow/workflow.yaml"


def snapshot(document):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(r["path"], (ROOT / r["path"]).read_text())
        for r in document["provenance"]["sources"]
    ]


class LayoutTests(unittest.TestCase):
    def setUp(self):
        base = ROOT / "artifacts/workflow_hub"
        base.mkdir(parents=True, exist_ok=True)
        tmp = tempfile.TemporaryDirectory(prefix="layout-fixture-", dir=base)
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        for folder in ["skills", "scripts", "tests", "docs", "backends", "libraries"]:
            (self.root / folder).mkdir()
        for canonical in native.expected_views(self.root).values():
            canonical.touch()
        for theme in native.DOC_THEMES:
            (self.root / "docs" / theme).mkdir()
        for family, components in native.BACKEND_COMPONENTS.items():
            for component in components:
                path = self.root / "backends" / family / component
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
        for component in native.LIBRARY_COMPONENTS:
            (self.root / "libraries" / component).touch()
        skill = self.root / "skills/control/workflow-contract-validator/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.touch()

    def oracle(self):
        path = ROOT / "tests/mcp/fixtures/thematic_layout_original.py.txt"
        spec = importlib.util.spec_from_loader(
            "_layout_oracle", SourceFileLoader("_layout_oracle", str(path))
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for key, folder in [
            ("REPO_ROOT", ""),
            ("SKILLS_ROOT", "skills"),
            ("SCRIPTS_ROOT", "scripts"),
            ("TESTS_ROOT", "tests"),
            ("DOCS_ROOT", "docs"),
            ("BACKENDS_ROOT", "backends"),
            ("LIBRARIES_ROOT", "libraries"),
        ]:
            setattr(module, key, self.root / folder)
        return module

    def cli(self, module, args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with (
            redirect_stdout(stdout),
            redirect_stderr(stderr),
            patch.object(sys, "argv", ["layout", *args]),
        ):
            try:
                code = (
                    module.main(args, self.root) if module is native else module.main()
                )
            except (SystemExit, ValueError) as error:
                code = ("terminated", str(error))
        return code, stdout.getvalue(), stderr.getvalue()

    def test_original_equivalence_and_native_finite_scans(self):
        oracle = self.oracle()
        for args in [[], ["--json"], ["--bad"], ["--help"]]:
            self.assertEqual(self.cli(native, args), self.cli(oracle, args))
        # Repair and repeated repair terminate over the fixed ordered alias table.
        self.assertEqual(
            self.cli(native, ["--apply", "--json"]),
            self.cli(oracle, ["--apply", "--json"]),
        )
        self.assertEqual(self.cli(native, ["--apply"]), self.cli(oracle, ["--apply"]))
        report = native.build_report(self.root)
        self.assertTrue(report["ok"], report)
        self.assertEqual(
            report["view_count"],
            sum(map(len, native.SCRIPT_THEMES.values()))
            + sum(map(len, native.TEST_ALIASES.values())),
        )
        self.assertEqual(report["view_states"], {"ok": report["view_count"]})
        # Exactly two-deep discovery, classification, and all failure collections.
        for rel in [
            "skills/flat/SKILL.md",
            "skills/wrong/lean-example/SKILL.md",
            "skills/deeper/x/y/SKILL.md",
            "scripts/unmanaged",
            "tests/unmanaged",
            "docs/unmanaged",
            "Main.lean",
        ]:
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
        (self.root / "docs/archive").rmdir()
        (self.root / "libraries/MathformerLib").unlink()
        report = native.build_report(self.root)
        self.assertEqual(report, oracle.build_report())
        self.assertFalse(report["ok"])
        self.assertEqual(report["flat_skills"], ["flat"])
        self.assertEqual(report["misclassified_skills"], ["skills/wrong/lean-example"])
        self.assertEqual(report["skill_theme_counts"], {"control": 1, "wrong": 1})
        for field in [
            "unclassified_root_scripts",
            "unclassified_root_tests",
            "unclassified_root_docs",
        ]:
            self.assertEqual(report[field], ["unmanaged"])
        self.assertEqual(report["missing_doc_themes"], ["archive"])
        self.assertEqual(report["missing_library_components"], ["MathformerLib"])
        self.assertEqual(report["legacy_component_roots"], ["Main.lean"])
        self.assertEqual(report["root_lean_files"], ["Main.lean"])

    def test_registered_tools_and_lunar_runtime(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_control_thematic_layout_workflow")
        self.assertEqual(document["lifecycle"], "active")
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        async with manager.open(
            "layout",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {},
        ) as remote:
            tools = [
                t.model_dump(by_alias=True, exclude_none=True)
                for t in await remote.tools()
            ]

            def compile(doc, inventory=tools):
                assets = snapshot(doc)
                compiled = compile_workflow(
                    "mcp:layout", workflow_documents([DESCRIPTOR], assets)[0], inventory
                )
                return compiled, assets

            workflow, assets = compile(document)
            self.assertTrue(workflow["runnable"], workflow["diagnostics"])
            self.assertTrue(workflow["runtime_source"])
            self.assertEqual(set(workflow["bindings"]), set(document["operations"]))
            self.assertFalse(compile(document, [])[0]["runnable"])

            async def authorize():
                pass

            async def run(args, doc=document, context=None):
                c, a = compile(doc)
                self.assertTrue(c["runnable"], c["diagnostics"])
                return await execute(
                    c,
                    a,
                    {
                        "argv": args,
                        "context": context or {"repository_root": str(self.root)},
                    },
                    remote,
                    authorize,
                )

            for args in [
                [],
                ["--json"],
                ["--apply", "--json"],
                ["--apply"],
                ["--json"],
            ]:
                result = await run(args)
                self.assertEqual(result["status"], "accepted", result)
                code, text, _ = self.cli(
                    self.oracle(), [a for a in args if a != "--apply"]
                )
                self.assertEqual(
                    result["outputs"],
                    {
                        "report": native.build_report(self.root),
                        "completion": {"stdout": text, "exit_code": code},
                    },
                )
                self.assertEqual(
                    [c["tool"] for c in result["calls"]],
                    ["mathformer_layout_parse"]
                    + (["mathformer_layout_repair"] if "--apply" in args else [])
                    + ["mathformer_layout_validate", "mathformer_layout_emit"],
                )
                self.assertTrue(result["runtime"]["effect_records"])
                self.assertTrue(result["runtime"]["provenance"])
                self.assertTrue(result["replay_artifacts"])
            # Help succeeds before any repository access, even for absent context.
            result = await run(
                ["--help"],
                context={
                    "repository_root": str(
                        Path(gettempdir()) / "mathformer-test-fixtures/not-a-repository"
                    )
                },
            )
            self.assertEqual(result["status"], "accepted", result)
            self.assertIsNone(result["outputs"]["report"])
            self.assertEqual(result["outputs"]["completion"]["exit_code"], 0)
            self.assertIn("--apply", result["outputs"]["completion"]["stdout"])
            self.assertEqual(
                [c["tool"] for c in result["calls"]],
                ["mathformer_layout_parse", "mathformer_layout_halt"],
            )
            views = list(native.expected_views(self.root).items())
            # Wrong target is repaired with the relative canonical target.
            alias, canonical = views[0]
            alias.unlink()
            alias.symlink_to("../wrong")
            result = await run(["--apply", "--json"])
            self.assertEqual(result["status"], "accepted", result)
            self.assertTrue(result["outputs"]["report"]["ok"])
            self.assertEqual(
                os.readlink(alias), native.relative_target(alias, canonical)
            )
            # Occupied alias anywhere rejects the entire repair before any write.
            first = views[0][0]
            first.unlink()
            occupied = views[-1][0]
            occupied.unlink()
            occupied.write_text("retain")
            result = await run(["--apply"])
            self.assertEqual(result["status"], "failed", result)
            self.assertEqual(len(result["calls"]), 2)
            self.assertFalse(first.exists())
            self.assertEqual(occupied.read_text(), "retain")
            occupied.unlink()
            # Later missing canonical preserves earlier filesystem mutations.
            late_alias, late_canonical = views[-1]
            late_canonical.unlink()
            result = await run(["--apply"])
            self.assertEqual(result["status"], "failed", result)
            self.assertEqual(len(result["calls"]), 2)
            self.assertTrue(first.is_symlink())
            self.assertFalse(late_alias.is_symlink())
            self.assertIsNone(result["outputs"])
            late_canonical.touch()
            for args in [["--unknown"], ["--apply", "extra"]]:
                result = await run(args)
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(len(result["calls"]), 1)
            # Unknown skill raises at native classification; no emit or retry.
            skill = self.root / "skills/control/unknown/SKILL.md"
            skill.parent.mkdir()
            skill.touch()
            result = await run(["--json"])
            self.assertEqual(result["status"], "failed", result)
            self.assertEqual(len(result["calls"]), 2)
            skill.unlink()
            skill.parent.rmdir()
            bounded = deepcopy(document)
            bounded["policy"]["limits"]["max_operation_calls"] = 2
            result = await run(["--json"], bounded)
            self.assertEqual(result["status"], "failed", result)
            self.assertEqual(
                sum(bool(c.get("transport_call_performed")) for c in result["calls"]), 2
            )
            self.assertIn("budget", str(result).lower())
            result = await run(
                ["--json"], context={"repository_root": str(Path(gettempdir()))}
            )
            self.assertEqual(result["status"], "failed", result)
            self.assertEqual(len(result["calls"]), 2)
            # Cancellation by the host wall budget is real, with no live work.
            timed = deepcopy(document)
            timed["policy"]["limits"]["wall_time_seconds"] = 1
            c, a = compile(timed)

            async def pending_authority():
                await asyncio.Event().wait()

            with self.assertRaises(TimeoutError):
                await execute(
                    c,
                    a,
                    {"argv": [], "context": {"repository_root": str(self.root)}},
                    remote,
                    pending_authority,
                )
        self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
