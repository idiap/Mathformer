#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Actual native suite, registered MCP interfaces and Lunar PRISM execution.

All repositories and Git history are deterministic temporary fixture data.
There is no provider or external compiler boundary in this validation workflow;
PRISM parsing, checking, compilation and execution are never substituted.
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
from copy import deepcopy
from functools import partial
import hashlib
import io
import json
import subprocess
import tempfile
import types
import unittest
import yaml
from plugin_test_tools import Session, load_source, SOURCE
import sync_agent_plugins as plugins
from workflow_catalog import WORKFLOWS, load_catalog
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_skills_plugin_test_workflow/workflow.yaml"
AUTHORED = (
    ROOT
    / "skills/control/workflow-contract-validator/references/plugin-test.workflow.json"
)


def digest(data):
    return "sha256:" + hashlib.sha256(data).hexdigest()


def put(root, path, content):
    path = root / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def fixture(root, mode="current"):
    # Native fixture construction and projection, entirely within this temp tree.
    source = load_source(root)
    source.AgentPluginTests().fixture(root)
    doc = json.loads(AUTHORED.read_text())
    text = json.dumps(doc)
    row = dict(
        id=doc["id"],
        category="hub",
        aliases=doc["aliases"],
        description=doc["description"],
        owner_skill="skills/lean/demo/SKILL.md",
        path="hub/plugin-test/workflow.yaml",
        descriptor_digest=digest(text.encode()),
    )
    put(root, WORKFLOWS / row["path"], text)
    put(
        root,
        WORKFLOWS / "catalog.json",
        json.dumps(
            dict(
                schema_version="mathformer.normalized-workflow-catalog/v1",
                counts={"hub": 1},
                workflows=[row],
            )
        ),
    )
    for path in [
        "skills/control/workflow-contract-validator/references/workflow.schema.json",
        str(WORKFLOWS / "hub-interface.schema.json"),
        "skills/control/workflow-contract-validator/scripts/validate_workflow.py",
        *[item["path"] for item in doc["provenance"]["sources"]],
    ]:
        put(root, path, (ROOT / path).read_text())
    put(
        root,
        "tracked.txt",
        "# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>\nfixture\n",
    )
    git = [
        "git",
        "-c",
        f"core.hooksPath={os.devnull}",
        "-c",
        "user.name=Andre Freitas",
        "-c",
        "user.email=andre.freitas@idiap.ch",
    ]
    for args in [
        ("init", "-q"),
        ("add", "tracked.txt"),
        ("commit", "-q", "-m", "fixture"),
    ]:
        subprocess.run([*git, *args], cwd=root, check=True, capture_output=True)
    # Materialize expected fixture data without invoking a production workflow.
    for path, text in plugins.expected_files(root).items():
        put(root, path, text)
    if mode == "drift":
        put(root, plugins.PLUGIN / "LICENSE", "drift\n")
    if mode == "error":
        (root / "LICENSE").unlink()
        (root / "LICENSE").mkdir()
    return root


def baseline(root):
    # The exact original unittest entrypoint's suite and runner, with repository
    # context supplied explicitly. No test or helper implementation is replaced.
    module = types.ModuleType("mathformer_plugin_tests")
    module.__file__ = str(SOURCE)
    exec(
        compile(
            (ROOT / "tests/mcp/fixtures/plugin_test_original.py.txt").read_text(),
            str(SOURCE),
            "exec",
        ),
        module.__dict__,
    )
    module.ROOT = root
    module.load_catalog = partial(load_catalog, root)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(module.AgentPluginTests)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream).run(suite)
    return result, stream.getvalue()


def snapshot(doc):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(doc))] + [
        asset(row["path"], (ROOT / row["path"]).read_text())
        for row in doc["provenance"]["sources"]
    ]


class PluginTestWorkflowTests(unittest.TestCase):
    def test_shared_native_suite_and_stop(self):
        with tempfile.TemporaryDirectory() as directory:
            root = fixture(Path(directory))
            old, transcript = baseline(root)
            self.assertTrue(old.wasSuccessful(), transcript)
            live = Session(root)
            initial = live.state()
            self.assertEqual(len(initial["tests"]), 11)
            with self.assertRaisesRegex(ValueError, "not stopped"):
                live.finish(initial)
            altered = deepcopy(initial)
            altered["index"] = 1
            with self.assertRaisesRegex(ValueError, "modified"):
                live.advance(altered)
            advanced = live.advance(initial)
            self.assertFalse(advanced["done"])
            self.assertEqual(advanced["state"]["index"], 1)
            with self.assertRaisesRegex(ValueError, "stale"):
                live.advance(initial)
            # Real unittest stop signal: the next test is already at startTest;
            # finish that in-flight test, then TestSuite observes shouldStop.
            live.result.stop()
            stopped = live.advance(live.state())
            self.assertTrue(stopped["done"])
            final = live.finish(stopped["state"])["result"]
            self.assertEqual(final["tests_run"], 2)
            self.assertTrue(final["state"]["should_stop"])
            self.assertIn("Ran 2 tests", final["runner_output"])
            with self.assertRaisesRegex(ValueError, "exhausted"):
                live.advance(stopped["state"])

    def test_registered_tools_real_prism_runtime(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        doc = yaml.safe_load(Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text())
        self.assertEqual(doc, json.loads(AUTHORED.read_text()))
        self.assertEqual(doc["id"], "hub_skills_plugin_test_workflow")
        for row in doc["provenance"]["sources"]:
            self.assertEqual(row["digest"], digest((ROOT / row["path"]).read_bytes()))
        self.assertIn(
            "register_plugin_test_tools(mcp)",
            (ROOT / "scripts/mcp_server.py").read_text(),
        )
        manager = SessionManager()
        async with manager.open(
            "plugins",
            StdioConfig(
                command=sys.executable,
                args=[str(ROOT / "scripts/plugin_test_tools.py")],
                cwd=str(ROOT),
            ),
            {},
        ) as remote:
            inventory = [
                t.model_dump(by_alias=True, exclude_none=True)
                for t in await remote.tools()
            ]

            def compile(document, tools=inventory):
                assets = snapshot(document)
                workflow = workflow_documents([DESCRIPTOR], assets)[0]
                return compile_workflow("mcp:plugins", workflow, tools), assets

            compiled, assets = compile(doc)
            self.assertTrue(compiled["runnable"], compiled["diagnostics"])
            self.assertTrue(compiled["runtime_source"])
            self.assertEqual(set(compiled["bindings"]), set(doc["operations"]))
            self.assertFalse(compile(doc, [])[0]["runnable"])

            async def allow():
                pass

            for mode in ["current", "drift", "error"]:
                with (
                    self.subTest(mode=mode),
                    tempfile.TemporaryDirectory() as directory,
                ):
                    root = fixture(Path(directory), mode)
                    old, transcript = baseline(root)
                    result = await execute(
                        compiled, assets, {"repository_root": str(root)}, remote, allow
                    )
                    self.assertEqual(result["status"], "accepted", result)
                    final = result["outputs"]["result"]
                    self.assertEqual(final["successful"], old.wasSuccessful())
                    self.assertEqual(
                        final["exit_code"], 0 if old.wasSuccessful() else 1
                    )
                    self.assertEqual(final["tests_run"], 11)
                    self.assertEqual(final["state"]["index"], 11)
                    self.assertFalse(final["state"]["should_stop"])
                    outcomes = final["state"]["outcomes"]
                    self.assertEqual(
                        [r["test"] for r in outcomes], final["state"]["tests"]
                    )
                    self.assertEqual(
                        [r["test"] for r in outcomes if r["status"] == "failure"],
                        [t.id() for t, _ in old.failures],
                    )
                    self.assertEqual(
                        [r["test"] for r in outcomes if r["status"] == "error"],
                        [t.id() for t, _ in old.errors],
                    )
                    self.assertEqual(len(outcomes), 11)
                    self.assertIn("Ran 11 tests", final["runner_output"])
                    self.assertEqual(
                        final["runner_output"].splitlines()[0],
                        transcript.splitlines()[0],
                    )
                    self.assertEqual(
                        final["runner_output"].splitlines()[-1],
                        transcript.splitlines()[-1],
                    )
                    self.assertEqual(len(result["calls"]), 13)
                    self.assertEqual(
                        [c["tool"] for c in result["calls"]],
                        ["mathformer_plugin_test_initialize"]
                        + ["mathformer_plugin_test_next"] * 11
                        + ["mathformer_plugin_test_finish"],
                    )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["replay_artifacts"])
                    if mode == "current":
                        self.assertTrue(final["successful"], final["runner_output"])
                    else:
                        self.assertFalse(final["successful"])
                    with self.assertRaisesRegex(Exception, "rejected"):
                        await remote.call(
                            "mathformer_plugin_test_finish", {"state": final["state"]}
                        )
            # Real loop exhaustion and call-budget paths, using the source suite.
            with tempfile.TemporaryDirectory() as directory:
                root = fixture(Path(directory))
                for limit in ["loop", "calls"]:
                    changed = deepcopy(doc)
                    if limit == "loop":
                        changed["flow"]["steps"][1]["max_iterations"] = 10
                    else:
                        changed["policy"]["limits"]["max_operation_calls"] = 11
                    bounded, bound_assets = compile(changed)
                    self.assertTrue(bounded["runnable"], bounded["diagnostics"])

                    class RecordedTransport:
                        last = None

                        async def tools(self):
                            return await remote.tools()

                        async def call(self, name, arguments):
                            response = await remote.call(name, arguments)
                            self.last = response
                            return response

                    recording = RecordedTransport()
                    failed = await execute(
                        bounded,
                        bound_assets,
                        {"repository_root": str(root)},
                        recording,
                        allow,
                    )
                    self.assertEqual(failed["status"], "failed", failed)
                    self.assertIsNone(failed["outputs"])
                    self.assertEqual(
                        len(failed["calls"]), 11 if limit == "loop" else 12
                    )
                    # Drain the still-live native session: no fixture leaks.
                    state = recording.last["state"]
                    self.assertEqual(state["index"], 10)
                    if limit == "calls":
                        self.assertEqual(failed["calls"][-1]["status"], "rejected")
                        self.assertIn("budget", failed["calls"][-1]["error"])
                    last = await remote.call(
                        "mathformer_plugin_test_next", {"state": state}
                    )
                    self.assertTrue(last["done"])
                    await remote.call(
                        "mathformer_plugin_test_finish", {"state": last["state"]}
                    )
            failed = await execute(
                compiled,
                assets,
                {
                    "repository_root": str(
                        Path(gettempdir())
                        / "mathformer-test-fixtures/nonexistent/mathformer-fixture"
                    )
                },
                remote,
                allow,
            )
            self.assertEqual(failed["status"], "failed", failed)
            self.assertEqual(len(failed["calls"]), 1)
            self.assertEqual(failed["calls"][0]["status"], "rejected")
        self.assertFalse(manager.active)


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False).result
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
