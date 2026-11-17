#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Isolated filesystem fixtures through real native steps, MCP and Lunar/PRISM.

This workflow has no model/provider or external compiler boundary. Tests use
actual validation, rendering and auditing; PRISM parsing/checking/compilation and
execution are real. No service config, credentials or hub actions are loaded.
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
from functools import partial
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import tempfile
import unittest
import yaml
from reasoning_smoke_tools import (
    source,
    register_reasoning_smoke_tools,
    smoke_lifespan,
    _SCOPES,
)
from mcp.server.fastmcp import FastMCP
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_control_reasoning_log_smoke_workflow/workflow.yaml"
GUARDIAN = "skills/control/reasoning-log-schema-guardian"


def repository(root, count=100, valid=True, wrapper=True):
    skills = root / "skills"
    skills.mkdir(parents=True)
    hooks = (ROOT / "skills/SKILL_HOOKS.yaml").read_text()
    if not valid:
        hooks = hooks.replace(
            "control.reasoning_log_schema", "disabled.reasoning_log_schema"
        )
    (skills / "SKILL_HOOKS.yaml").write_text(hooks)
    for i in range(count):
        folder = skills / "fixture" / f"skill-{i:03}"
        folder.mkdir(parents=True)
        (folder / "SKILL.md").write_text(f"---\nname: skill-{i:03}\n---\nFixture\n")
    if count:
        script = skills / "fixture/skill-000/scripts"
        script.mkdir()
        (script / "native.py").write_text("# append_skill_start\n")
        (script / "plain.py").write_text("pass\n")
        (skills / "fixture/skill-002/SKILL.md").write_text(
            "---\nname: reasoning-flow-language\n---\nFixture\n"
        )
        agents = skills / "fixture/skill-001/agents"
        agents.mkdir()
        (agents / "agent.yaml").write_text("name: fixture\n")
        if wrapper:
            guardian = root / GUARDIAN
            (guardian / "scripts").mkdir(parents=True)
            (guardian / "SKILL.md").write_text(
                "---\nname: reasoning-log-schema-guardian\n---\nFixture\n"
            )
            (guardian / "scripts/run_with_reasoning_log.py").write_text("pass\n")
    return root


def original(root):
    path = ROOT / "tests/mcp/fixtures/reasoning_smoke_original.py.txt"
    spec = importlib.util.spec_from_loader(
        "smoke_oracle", SourceFileLoader("smoke_oracle", str(path))
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Supply the fixture's read context to the unchanged authoritative function.
    module.REPO_ROOT = root
    module.audit_coverage = partial(source().audit_coverage, repo_root=root)
    return module


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


class SmokeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = repository(Path(self.temporary.name) / "repository")

    def test_original_equivalence_and_native_output(self):
        native, oracle = source(), original(self.root)
        actual = native.run_self_test(self.root)
        expected = oracle.run_self_test()
        self.assertGreater(actual["render_summary"].pop("html_bytes"), 0)
        self.assertGreater(expected["render_summary"].pop("html_bytes"), 0)
        self.assertEqual(actual, expected)
        self.assertTrue(actual["ok"], actual)
        self.assertEqual(len(actual["checks"]), 7)
        self.assertEqual(actual["render_summary"]["event_count"], 3)
        self.assertEqual(actual["render_summary"]["skill_invocation_count"], 1)
        self.assertEqual(actual["coverage_summary"]["skill_count"], 101)
        self.assertEqual(actual["coverage_summary"]["script_count"], 3)
        self.assertEqual(
            actual["coverage_summary"]["logging_class_counts"],
            {"script-logged": 2, "agent-logged": 98, "workflow-only": 1},
        )
        self.assertEqual(actual["coverage_summary"]["native_logged_script_count"], 1)
        self.assertEqual(actual["coverage_summary"]["wrapper_logged_script_count"], 2)
        # main's unchanged formatting/exit contract, using the real fixture context.
        # Invoke the frozen original CLI body by setting its native read context.
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = oracle.main(["--json"])
        self.assertEqual(code, 0)
        cli = json.loads(stream.getvalue())
        self.assertGreater(cli["render_summary"].pop("html_bytes"), 0)
        self.assertEqual(cli, expected)

    def test_native_event_state_rendering_and_failed_validation_continues(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = source().create_fixture(Path(directory))
            events = source().load_events(Path(fixture["log_file"]))
            self.assertEqual(len(events), 3)
            self.assertEqual(
                [e["step"] for e in events],
                [
                    "skill_application_start",
                    "skill_application_evidence_recorded",
                    "skill_application_complete",
                ],
            )
            self.assertEqual(
                [e["payload"]["skill_application"]["status"] for e in events],
                ["running", "running", "complete"],
            )
            self.assertEqual(
                {e["payload"]["skill_application"]["skill_call_id"] for e in events},
                {fixture["skill_call_id"]},
            )
            bad = repository(Path(self.temporary.name) / "bad", valid=False)
            validation = source().validate_fixture(fixture, bad)
            self.assertFalse(validation["ok"])
            self.assertTrue(validation["findings"])
            rendered = source().render_fixture(fixture, validation)
            self.assertEqual(
                Path(fixture["rendered_file"]).read_text(), rendered["markdown"]
            )
            self.assertEqual(Path(fixture["html_file"]).read_text(), rendered["html"])
            self.assertEqual(
                rendered["summary"]["html_bytes"], len(rendered["html"].encode("utf-8"))
            )
            coverage = source().audit_fixture_coverage(bad)
            report = source().finish_fixture(validation, rendered, coverage)
            self.assertFalse(report["ok"])
            self.assertFalse(report["checks"]["validation_ok"])
            self.assertTrue(
                all(v for k, v in report["checks"].items() if k != "validation_ok")
            )
        self.assertFalse(Path(fixture["log_file"]).exists())
        empty = repository(Path(self.temporary.name) / "empty", count=0)
        report = source().run_self_test(empty)
        self.assertEqual(report["coverage_summary"]["skill_count"], 0)
        self.assertTrue(report["checks"]["coverage_ok"])
        self.assertFalse(report["checks"]["coverage_has_all_skills"])
        missing = repository(Path(self.temporary.name) / "missing", wrapper=False)
        report = source().run_self_test(missing)
        self.assertFalse(report["checks"]["coverage_ok"])
        self.assertEqual(report["coverage_summary"]["missing_skill_count"], 1)
        stream = io.StringIO()
        with redirect_stdout(stream):
            self.assertEqual(original(missing).main([]), 3)
        self.assertIn("ok: False", stream.getvalue())

    def test_registered_cleanup_on_exception_and_lifespan(self):
        asyncio.run(self.cleanup_scenario())

    async def cleanup_scenario(self):
        server = FastMCP("scope-tests", lifespan=smoke_lifespan)
        register_reasoning_smoke_tools(server)

        async def call(name, args):
            # Actual FastMCP registration and validation, rather than calling helpers.
            result = await server.call_tool("mathformer_reasoning_smoke_" + name, args)
            return result[1] if isinstance(result, tuple) else result

        async with smoke_lifespan(server):
            fixture = (
                await call(
                    "create_fixture", {"context": {"repository_root": str(self.root)}}
                )
            )["fixture"]
            self.assertTrue(Path(fixture["log_file"]).exists())
            with self.assertRaises(Exception):
                await call("render_fixture", {"fixture": fixture, "validation": {}})
            self.assertFalse(Path(fixture["log_file"]).exists())
            fixture = (
                await call(
                    "create_fixture", {"context": {"repository_root": str(self.root)}}
                )
            )["fixture"]
            # Native validation I/O exception must also close the temporary scope.
            Path(fixture["log_file"]).write_bytes(b"\xff")
            with self.assertRaises(Exception):
                await call("validate_fixture", {"fixture": fixture})
            self.assertFalse(Path(fixture["log_file"]).exists())
            fixture = (
                await call(
                    "create_fixture", {"context": {"repository_root": str(self.root)}}
                )
            )["fixture"]
            self.assertTrue(_SCOPES)
        self.assertFalse(_SCOPES)
        self.assertFalse(Path(fixture["log_file"]).exists())

    def test_real_registered_mcp_and_lunar(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_control_reasoning_log_smoke_workflow")
        self.assertEqual(document["lifecycle"], "active")
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        pending_paths = []
        failure = None
        async with manager.open(
            "smoke",
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
                    return (
                        compile_workflow(
                            "mcp:smoke",
                            selected,
                            tools if inventory is None else inventory,
                        ),
                        assets,
                    )

                qualified, assets = compile(document)
                self.assertTrue(qualified["runnable"], qualified["diagnostics"])
                self.assertTrue(qualified["runtime_source"])
                self.assertEqual(
                    set(qualified["bindings"]), set(document["operations"])
                )
                self.assertFalse(compile(document, [])[0]["runnable"])

                async def authorize():
                    pass

                async def run(root, doc=None):
                    workflow, received = compile(doc) if doc else (qualified, assets)
                    return await execute(
                        workflow,
                        received,
                        {"context": {"repository_root": str(root)}},
                        remote,
                        authorize,
                    )

                result = await run(self.root)
                self.assertEqual(result["status"], "accepted", result)
                expected = source().run_self_test(self.root)
                # MCP uses a descriptive temporary prefix, so path-bearing HTML
                # bytes differ; every semantic summary and check must agree.
                actual = deepcopy(result["outputs"]["result"])
                self.assertGreater(actual["render_summary"].pop("html_bytes"), 0)
                expected["render_summary"].pop("html_bytes")
                self.assertEqual(actual, expected)
                self.assertEqual(
                    [c["operation"] for c in result["calls"]],
                    list(document["operations"]),
                )
                self.assertTrue(result["runtime"]["effect_records"])
                self.assertTrue(result["replay_artifacts"])
                bad = repository(Path(self.temporary.name) / "runtime-bad", valid=False)
                failed_checks = await run(bad)
                self.assertEqual(failed_checks["status"], "accepted", failed_checks)
                self.assertEqual(len(failed_checks["calls"]), 5)
                self.assertFalse(failed_checks["outputs"]["result"]["ok"])
                self.assertTrue(
                    failed_checks["outputs"]["result"]["checks"]["coverage_ok"]
                )
                # Actual read failure at coverage, after successful validation/rendering.
                broken = repository(Path(self.temporary.name) / "runtime-broken")
                (broken / "skills/fixture/skill-000/SKILL.md").write_bytes(b"\xff")
                failed = await run(broken)
                self.assertEqual(failed["status"], "failed", failed)
                self.assertIsNone(failed["outputs"])
                self.assertEqual(len(failed["calls"]), 4)
                self.assertEqual(failed["calls"][-1]["status"], "rejected")
                # Observe real scope paths to verify cleanup on finish and abort.
                fixture = (
                    await remote.call(
                        "mathformer_reasoning_smoke_create_fixture",
                        {"context": {"repository_root": str(self.root)}},
                    )
                )["fixture"]
                validation = (
                    await remote.call(
                        "mathformer_reasoning_smoke_validate_fixture",
                        {"fixture": fixture},
                    )
                )["validation"]
                rendered = (
                    await remote.call(
                        "mathformer_reasoning_smoke_render_fixture",
                        {"fixture": fixture, "validation": validation},
                    )
                )["rendered"]
                coverage = (
                    await remote.call(
                        "mathformer_reasoning_smoke_audit_coverage",
                        {"fixture": fixture},
                    )
                )["coverage"]
                completed = await remote.call(
                    "mathformer_reasoning_smoke_finish",
                    {
                        "fixture": fixture,
                        "validation": validation,
                        "rendered": rendered,
                        "coverage": coverage,
                    },
                )
                self.assertTrue(completed["result"]["ok"])
                self.assertFalse(Path(fixture["log_file"]).exists())
                bounded = deepcopy(document)
                bounded["policy"]["limits"]["max_operation_calls"] = 2
                failed = await run(self.root, bounded)
                self.assertEqual(failed["status"], "failed", failed)
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in failed["calls"]
                    ),
                    2,
                )
                self.assertIn("budget", str(failed).lower())
                timed = deepcopy(document)
                timed["policy"]["limits"]["wall_time_seconds"] = 1
                workflow, received = compile(timed)

                async def pending():
                    await asyncio.Event().wait()

                with self.assertRaises(TimeoutError):
                    await execute(
                        workflow,
                        received,
                        {"context": {"repository_root": str(self.root)}},
                        remote,
                        pending,
                    )
                unfinished = (
                    await remote.call(
                        "mathformer_reasoning_smoke_create_fixture",
                        {"context": {"repository_root": str(self.root)}},
                    )
                )["fixture"]
                pending_paths.append(Path(unfinished["log_file"]))
                self.assertTrue(pending_paths[-1].exists())
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        self.assertTrue(all(not p.exists() for p in pending_paths))
        if failure:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
