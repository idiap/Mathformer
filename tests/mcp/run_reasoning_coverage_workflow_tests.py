#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Fixture-only native/MCP/PRISM integration; no providers or external compilers."""

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
import yaml
from reasoning_coverage_tools import source
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_control_reasoning_log_coverage_workflow/workflow.yaml"


def oracle(root):
    path = ROOT / "tests/mcp/fixtures/reasoning_coverage_original.py.txt"
    spec = importlib.util.spec_from_loader(
        "coverage_oracle", SourceFileLoader("coverage_oracle", str(path))
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.REPO_ROOT = root
    return module


def fixture(root, wrapper=True, populated=True):
    skills = root / "skills"
    skills.mkdir(parents=True)
    (skills / "SKILL_HOOKS.yaml").write_text(
        "runtime_contract:\n  shared_runtime_scripts:\n    - skills/theme/a/scripts/a.py\n    - skills/theme/a/scripts/a.py\nhooks:\n  - id: owned\n    owner_skill: c\n"
    )
    if wrapper:
        p = (
            root
            / "skills/control/reasoning-log-schema-guardian/scripts/run_with_reasoning_log.py"
        )
        p.parent.mkdir(parents=True)
        p.write_text("# wrapper fixture")
    if populated:
        for name in ["d", "c", "b", "a"]:
            p = skills / "theme" / name / "SKILL.md"
            p.parent.mkdir(parents=True)
            p.write_text(f"---\nname: {name}\ndescription: first\n  continued\n---\n")
        p = skills / "theme/a/scripts"
        p.mkdir()
        (p / "a.py").write_text("# append_skill_start\n")
        (p / "b.py").write_bytes(b"# no marker\xff")
        p = skills / "theme/b/agents"
        p.mkdir()
        (p / "manifest").write_text("agent")
    return skills


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


class CoverageTests(unittest.TestCase):
    def test_native_oracle_cli_and_complete_exhaustion(self):
        for wrapper in (True, False):
            for populated in (True, False):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    skills = fixture(root, wrapper, populated)
                    original = oracle(root)
                    expected = original.audit(skills)
                    self.assertEqual(source().audit(skills, root), expected)
                    self.assertEqual(
                        source().render_text(expected), original.render_text(expected)
                    )
                    self.assertEqual(expected["skill_count"], 4 if populated else 0)
                    self.assertEqual(
                        expected["missing_skill_count"], int(populated and not wrapper)
                    )
                    if populated:
                        self.assertEqual(
                            [r["name"] for r in expected["skills"]], list("abcd")
                        )
                        self.assertEqual(
                            [r["logging_class"] for r in expected["skills"]],
                            [
                                "script-logged" if wrapper else "missing",
                                "agent-logged",
                                "workflow-only",
                                "agent-logged",
                            ],
                        )
                        self.assertEqual(expected["native_logged_script_count"], 1)
                        self.assertTrue(expected["scripts"][0]["registered_runtime"])
                        self.assertEqual(
                            expected["scripts_without_native_logging_count"],
                            int(wrapper),
                        )
                    # Compare the unchanged main() formatting and strict exit policy.
                    for strict in (False, True):
                        for native in (False, True):
                            stream = io.StringIO()
                            argv = (
                                ["--skills-dir", str(skills), "--json"]
                                + (["--strict"] if strict else [])
                                + (
                                    ["--require-native-script-logging"]
                                    if native
                                    else []
                                )
                            )
                            with redirect_stdout(stream):
                                code = original.main(argv)
                            report = json.loads(stream.getvalue())
                            wanted = deepcopy(expected)
                            if native:
                                wanted["ok"] = (
                                    wanted["ok"]
                                    and wanted["scripts_without_native_logging_count"]
                                    == 0
                                )
                            self.assertEqual(report, wanted)
                            self.assertEqual(
                                code, 3 if strict and not wanted["ok"] else 0
                            )

    def test_original_and_current_main_on_fixture_only(self):
        # Only fixture skills are scanned; default repository context is retained.
        with tempfile.TemporaryDirectory(prefix="coverage-fixture-", dir=ROOT) as tmp:
            skills = fixture(Path(tmp))
            original = oracle(ROOT)
            for flags in (
                [],
                ["--strict"],
                ["--strict", "--require-native-script-logging"],
            ):
                captured = []
                for module in (original, source()):
                    stream = io.StringIO()
                    with redirect_stdout(stream):
                        code = module.main(
                            ["--skills-dir", str(skills), "--json", *flags]
                        )
                    captured.append((code, stream.getvalue()))
                self.assertEqual(*captured)
                self.assertEqual(len(json.loads(captured[0][1])["skills"]), 4)

    def test_real_mcp_lunar(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["lifecycle"], "active")
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        failure = None
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        async with manager.open(
            "coverage",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {},
        ) as remote:
            try:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile(doc, inventory=None):
                    assets = snapshot(doc)
                    selected = workflow_documents([DESCRIPTOR], assets)[0]
                    compiled = compile_workflow(
                        "mcp:coverage",
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
                    return await execute(
                        selected,
                        received,
                        {"skills_dir": "skills", "repo_root": str(root)},
                        remote,
                        authorize,
                    )

                for wrapper, populated in ((True, True), (False, True), (False, False)):
                    with tempfile.TemporaryDirectory() as tmp:
                        root = Path(tmp)
                        skills = fixture(root, wrapper, populated)
                        expected = oracle(root).audit(skills)
                        result = await run(root)
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertEqual(result["outputs"], {"report": expected})
                        self.assertEqual(len(result["calls"]), 15 if populated else 5)
                        self.assertEqual(
                            result["calls"][0]["tool"], "mathformer_coverage_prepare"
                        )
                        self.assertEqual(
                            result["calls"][-1]["tool"], "mathformer_coverage_aggregate"
                        )
                        self.assertTrue(result["runtime"]["effect_records"])
                        if populated:
                            # Exactly at script/skill caps must complete, not exhaust.
                            capped = deepcopy(document)
                            flow = capped["flow"]
                            flow["steps"][1]["max_iterations"] = 4
                            flow["steps"][1]["body"]["steps"][1]["max_iterations"] = 2
                            accepted = await run(root, capped)
                            self.assertEqual(
                                accepted["outputs"], {"report": expected}, accepted
                            )
                            # One fewer iteration fails without aggregating a partial report.
                            flow["steps"][1]["body"]["steps"][1]["max_iterations"] = 1
                            script_failed = await run(root, capped)
                            self.assertEqual(
                                script_failed["status"], "failed", script_failed
                            )
                            self.assertIsNone(script_failed["outputs"])
                            self.assertEqual(
                                script_failed["calls"][-1]["tool"],
                                "mathformer_coverage_inspect_script",
                            )
                            flow["steps"][1]["body"]["steps"][1]["max_iterations"] = 2
                            flow["steps"][1]["max_iterations"] = 3
                            failed = await run(root, capped)
                            self.assertEqual(failed["status"], "failed", failed)
                            self.assertIsNone(failed["outputs"])
                            self.assertNotEqual(
                                failed["calls"][-1]["tool"],
                                "mathformer_coverage_aggregate",
                            )
                            budget = deepcopy(document)
                            budget["policy"]["limits"]["max_operation_calls"] = 2
                            failed = await run(root, budget)
                            self.assertEqual(failed["status"], "failed", failed)
                            self.assertEqual(
                                sum(
                                    bool(c.get("transport_call_performed"))
                                    for c in failed["calls"]
                                ),
                                2,
                            )
                            # Real decoding error propagates once; later skills unvisited.
                            (skills / "theme/a/SKILL.md").write_bytes(b"\xff")
                            with self.assertRaises(UnicodeDecodeError):
                                oracle(root).audit(skills)
                            failed = await run(root)
                            self.assertEqual(failed["status"], "failed", failed)
                            self.assertEqual(len(failed["calls"]), 2)
                            self.assertIsNone(failed["outputs"])
                with tempfile.TemporaryDirectory() as tmp:
                    failed = await run(Path(tmp))
                    self.assertEqual(failed["status"], "failed", failed)
                    self.assertEqual(len(failed["calls"]), 1)
            except Exception as error:
                import traceback

                traceback.print_exc()
                failure = error
        self.assertFalse(manager.active)
        if failure:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
