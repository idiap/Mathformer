#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic logs through native steps, registered MCP, real Lunar/PRISM.

No model/provider or external compiler is used by this source. The PRISM parser,
checker, compiler and runtime are real and receive the explicitly selected contract.
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
import yaml
from reasoning_summary_tools import source
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_control_reasoning_log_summary_workflow/workflow.yaml"
PREFIX = "mathformer_reasoning_summary_"


def oracle():
    loader = SourceFileLoader(
        "summary_oracle",
        str(ROOT / "tests/mcp/fixtures/reasoning_summary_original.py.txt"),
    )
    module = importlib.util.module_from_spec(
        importlib.util.spec_from_loader(loader.name, loader)
    )
    loader.exec_module(module)
    module.REPO_ROOT = ROOT
    return module


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
        for r in {r["path"]: r for r in document["provenance"]["sources"]}.values()
    ]


def event(index, run="r1", status="failed", **changes):
    app = dict(
        skill="reasoning-log-schema-guardian",
        hook_id="control.reasoning_log_schema",
        run_id=run,
        status=status,
        human_summary="fixture",
        artifacts={"shared": index},
        decision={"status": "pass"},
        risks={"risk": "fixture"},
        next_action="continue",
        schema_version=1,
        skill_call_id="fixture-call",
        intent="Inspect fixture",
        inputs={},
        evidence={},
    )
    app.update(changes)
    return dict(
        event_index=index,
        step="skill_application_complete",
        payload={"skill": "reasoning-log-schema-guardian", "skill_application": app},
        timestamp_utc="2026-01-01T00:00:00+00:00",
        timestamp_unix_ms=index,
        monotonic_ns=index,
        elapsed_ms_since_log_start=index,
        elapsed_ms_since_prev_event=1,
    )


class SummaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.hooks = self.directory / "hooks.yaml"
        self.hooks.write_text(
            "hooks:\n  - id: control.reasoning_log_schema\n    owner_skill: reasoning-log-schema-guardian\n"
        )
        self.native, self.original = source(), oracle()

    def file(self, name, events=None, raw=None):
        path = self.directory / name
        path.write_text(
            raw if raw is not None else "".join(json.dumps(e) + "\n" for e in events)
        )
        return path

    def fixtures(self):
        return [
            self.file("empty", []),
            self.file("mixed", raw="\n7\n[]\n{bad\n" + json.dumps(event(2)) + "\n"),
            self.file("single", [event(1)]),
            self.file("good", [event(1, status="complete", risks={})]),
            self.file(
                "multiple",
                [event(1), event(2, run="r2", status="complete"), event(3, run="r1")],
            ),
            self.file(
                "legacy",
                [
                    dict(
                        event_index=1,
                        step="finding",
                        payload={
                            "skill": "legacy",
                            "run_id": "old",
                            "artifacts": {"x": 1},
                        },
                    )
                ],
            ),
        ]

    def test_original_equivalence_cli_state_and_native_uncapped(self):
        for path in self.fixtures():
            expected = self.original.summarize(path, hooks_file=self.hooks)
            self.assertEqual(
                self.native.summarize(path, hooks_file=self.hooks), expected
            )
            if path.name == "good":
                self.assertTrue(expected["ok"])
            if path.name == "mixed":
                self.assertFalse(expected["ok"])
            if path.name == "single":
                self.assertEqual(expected["run_id"], "r1")
            if path.name == "multiple":
                self.assertIsNone(expected["run_id"])
            for flags in (
                [],
                ["--json"],
                ["--output-file", str(self.directory / "out.json")],
            ):
                captured = []
                for module in (self.native, self.original):
                    stream = io.StringIO()
                    with redirect_stdout(stream):
                        code = module.main(
                            [
                                "--log-file",
                                str(path),
                                "--hooks-file",
                                str(self.hooks),
                                *flags,
                            ]
                        )
                    captured.append((code, stream.getvalue()))
                    self.assertEqual(code, 0 if expected["ok"] else 3)
                self.assertEqual(*captured)
        events = [
            event(1),
            event(2, run="r2"),
            event(
                3,
                run="r1",
                skill="",
                hook_id=None,
                decision={},
                risks=[],
                next_action="",
            ),
        ]
        state = self.native.initialize_summary(events)["state"]
        for index in range(3):
            result = self.native.advance_summary(events, state)
            self.assertEqual(state["cursor"], index + 1)
            self.assertEqual(result["done"], index == 2)
        self.assertEqual(state["skills"], ["reasoning-log-schema-guardian"])
        self.assertEqual(state["run_ids"], ["r1", "r2"])
        self.assertEqual(state["artifacts"], {"shared": 1})
        self.assertEqual(len(state["timeline"]), 3)
        self.assertEqual(state["next_actions"], ["continue"])
        # Native traversal is uncapped, with no break on failed-status events.
        path = self.file("uncapped", [event(i) for i in range(10001)])
        self.assertEqual(
            self.native.summarize(path, hooks_file=self.hooks),
            self.original.summarize(path, hooks_file=self.hooks),
        )
        self.assertEqual(
            self.native.summarize(path, hooks_file=self.hooks)["event_count"], 10001
        )
        for path, error in [
            (self.directory / "missing", FileNotFoundError),
            (self.directory, IsADirectoryError),
            (
                self.file("bad-artifacts", [event(1, artifacts=["invalid"])]),
                AttributeError,
            ),
        ]:
            for module in (self.native, self.original):
                with self.assertRaises(error):
                    module.summarize(path, hooks_file=self.hooks)

    def test_registered_tools_real_lunar_and_failure_paths(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_control_reasoning_log_summary_workflow")
        self.assertEqual(document["lifecycle"], "active")
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        failure = None
        async with manager.open(
            "summary",
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
                    compiled = compile_workflow(
                        "mcp:summary",
                        workflow_documents([DESCRIPTOR], assets)[0],
                        tools if inventory is None else inventory,
                    )
                    return compiled, assets

                workflow, assets = compile(document)
                self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                self.assertTrue(workflow["runtime_source"])
                self.assertEqual(set(workflow["bindings"]), set(document["operations"]))
                self.assertFalse(compile(document, [])[0]["runnable"])

                async def allow():
                    pass

                async def run(path, doc=None, hooks=None):
                    w, a = compile(doc) if doc else (workflow, assets)
                    self.assertTrue(w["runnable"], w["diagnostics"])
                    return await execute(
                        w,
                        a,
                        {"log_file": str(path), "hooks_file": str(hooks or self.hooks)},
                        remote,
                        allow,
                    )

                for path in self.fixtures():
                    expected = self.original.summarize(path, hooks_file=self.hooks)
                    result = await run(path)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(result["outputs"], {"summary": expected})
                    self.assertEqual(
                        [c["tool"] for c in result["calls"]],
                        [
                            PREFIX + n
                            for n in ["load", "validate", "audit", "initialize"]
                            + ["advance"] * max(1, expected["event_count"])
                            + ["finish"]
                        ],
                    )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["runtime"]["provenance"])
                    self.assertTrue(result["replay_artifacts"])
                # Inspect carried data through registered tools, including canonical/legacy paths.
                path = self.file(
                    "states",
                    [event(1), event(2, run="r2"), event(3, skill="", decision=None)],
                )
                loaded = await remote.call(PREFIX + "load", {"log_file": str(path)})
                events = loaded["events"]
                expected = self.native.initialize_summary(events)
                observed = await remote.call(PREFIX + "initialize", loaded)
                self.assertEqual(observed, expected)
                for index in range(3):
                    expected = self.native.advance_summary(events, expected["state"])
                    observed = await remote.call(
                        PREFIX + "advance",
                        {"events": events, "state": observed["state"]},
                    )
                    self.assertEqual(observed, expected)
                    self.assertEqual(observed["done"], index == 2)
                # Full input admission boundary is exercised without 10000 costly runtime receipts.
                bound = self.file("bound", [{}] * 10000)
                admitted = await remote.call(PREFIX + "load", {"log_file": str(bound)})
                self.assertEqual(len(admitted["events"]), 10000)
                over = self.file("over", [{}] * 10001)
                result = await run(over)
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(len(result["calls"]), 1)
                self.assertIsNone(result["outputs"])
                # Compiler fixtures keep the source graph/tools; small bounds make exact stopping observable.
                path = self.file("two", [event(1), event(2)])
                capped = deepcopy(document)
                loop = capped["flow"]["steps"][4]
                loop["max_iterations"] = 2
                result = await run(path, capped)
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(len(result["calls"]), 7)
                self.assertEqual(
                    result["outputs"],
                    {"summary": self.original.summarize(path, hooks_file=self.hooks)},
                )
                loop["max_iterations"] = 1
                result = await run(path, capped)
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(result["failure_disposition"], "fail")
                self.assertEqual(len(result["calls"]), 5)
                self.assertEqual(result["calls"][-1]["tool"], PREFIX + "advance")
                self.assertIsNone(result["outputs"])
                budget = deepcopy(document)
                budget["policy"]["limits"]["max_operation_calls"] = 2
                result = await run(path, budget)
                self.assertEqual(result["status"], "failed")
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in result["calls"]
                    ),
                    2,
                )
                self.assertIn("budget", str(result).lower())
                # Exceptions propagate once and prevent all subsequent operations.
                for path in [
                    self.directory / "absent",
                    self.directory,
                    self.directory / "invalid-utf8",
                ]:
                    if path.name == "invalid-utf8":
                        path.write_bytes(b"\xff")
                    result = await run(path)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(len(result["calls"]), 1)
                    self.assertIsNone(result["outputs"])
                result = await run(
                    path=self.file("validation-error", []), hooks=self.directory
                )
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(len(result["calls"]), 2)
                bad = self.file("advance-error", [event(1, artifacts=["invalid"])])
                result = await run(bad)
                self.assertEqual(result["status"], "failed")
                self.assertEqual(len(result["calls"]), 5)
                self.assertEqual(result["calls"][-1]["tool"], PREFIX + "advance")
                self.assertIsNone(result["outputs"])
                timed = deepcopy(document)
                timed["policy"]["limits"]["wall_time_seconds"] = 1
                w, a = compile(timed)

                async def pending():
                    await asyncio.Event().wait()

                with self.assertRaises(TimeoutError):
                    await execute(
                        w,
                        a,
                        {"log_file": str(path), "hooks_file": str(self.hooks)},
                        remote,
                        pending,
                    )
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
