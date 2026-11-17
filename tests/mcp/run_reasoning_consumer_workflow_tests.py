#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Fixture-only native consumer checks through registered MCP and real PRISM.

This workflow has no provider or external compiler boundary to substitute.
The actual JSONL writers, validators, summarizer and PRISM compiler/runtime run.
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
import unittest
import tempfile
import yaml
from reasoning_consumer_tools import native
from render_reasoning_log import event_skill_application
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_control_reasoning_log_consumer_contract_workflow/workflow.yaml"
PREFIX = "mathformer_reasoning_consumer_"


def snapshot(doc):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(doc))] + [
        asset(s["path"], (ROOT / s["path"]).read_text())
        for s in doc["provenance"]["sources"]
    ]


class ConsumerTests(unittest.TestCase):
    def test_registered_workflow(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        doc = yaml.safe_load(Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text())
        self.assertEqual(
            doc["id"], "hub_control_reasoning_log_consumer_contract_workflow"
        )
        self.assertEqual(doc["lifecycle"], "active")
        for row in doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        loader = SourceFileLoader(
            "_consumer_oracle",
            str(ROOT / "tests/mcp/fixtures/reasoning_consumer_original.py.txt"),
        )
        spec = importlib.util.spec_from_loader(loader.name, loader)
        oracle = importlib.util.module_from_spec(spec)
        loader.exec_module(oracle)
        oracle.REPO_ROOT = ROOT
        expected = oracle.run_suite()
        self.assertEqual(native.run_suite(), expected)
        # Native CLI emission and exit status remain source-owned.
        for module in (oracle, native):
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = module.main(["--json"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(stdout.getvalue()), expected)
        manager = SessionManager()
        unfinished = []
        preexisting = set(Path(tempfile.gettempdir()).glob("reasoning-consumer-*"))
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        failure = None
        async with manager.open(
            "consumer",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {},
        ) as remote:
            try:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile(document, inventory=tools):
                    assets = snapshot(document)
                    result = compile_workflow(
                        "mcp:consumer",
                        workflow_documents([DESCRIPTOR], assets)[0],
                        inventory,
                    )
                    return result, assets

                compiled, assets = compile(doc)
                self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                self.assertTrue(compiled["runtime_source"])
                self.assertEqual(set(compiled["bindings"]), set(doc["operations"]))
                self.assertFalse(compile(doc, [])[0]["runnable"])

                async def authorize():
                    pass

                async def run(document=doc):
                    c, a = compile(document)
                    return await execute(c, a, {}, remote, authorize)

                result = await run()
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(result["outputs"], {"report": expected})
                self.assertEqual(
                    [c["tool"] for c in result["calls"]],
                    [PREFIX + "initialize"]
                    + [
                        PREFIX + s
                        for _ in range(4)
                        for s in ("evaluate_fixture", "append_and_advance")
                    ]
                    + [PREFIX + "cleanup_and_aggregate"],
                )
                self.assertEqual(len(result["calls"]), 10)
                self.assertTrue(result["runtime"]["effect_records"])
                self.assertTrue(result["replay_artifacts"])

                async def call(name, **arguments):
                    return await remote.call(PREFIX + name, arguments)

                # Inspect actual temporary logs, branches, accumulator and cleanup.
                state = (await call("initialize"))["state"]
                root = Path(state["root"])
                self.assertEqual(state["checks"], [])
                self.assertEqual(state["cursor"], 0)
                for index, (case_id, mode) in enumerate(native.CASES.items()):
                    old = deepcopy(state)
                    check = (await call("evaluate_fixture", state=state))["check"]
                    self.assertEqual(state, old)
                    log = root / (case_id + ".jsonl")
                    events = [json.loads(line) for line in log.read_text().splitlines()]
                    summary = native.summarize(
                        log, hooks_file=ROOT / "skills/SKILL_HOOKS.yaml"
                    )
                    self.assertEqual(native.check_summary(summary), [])
                    self.assertEqual(len(events), 3 if mode == "multi_skill" else 2)
                    apps = [event_skill_application(event) for event in events]
                    self.assertEqual(
                        [t["status"] for t in summary["timeline"]],
                        [app["status"] for app in apps],
                    )
                    self.assertEqual(summary["run_ids"], ["consumer-fixture-" + mode])
                    self.assertEqual(summary["artifacts"]["log_file"], str(log))
                    self.assertEqual(len(summary["skills"]), 1)
                    # Consumer acceptance deliberately ignores audit ok/status values.
                    unchecked = deepcopy(summary)
                    unchecked["ok"] = False
                    unchecked["timeline"][0]["status"] = "unrecognized_fixture_status"
                    self.assertEqual(native.check_summary(unchecked), [])
                    self.assertEqual(
                        summary["artifacts"].get("report"),
                        (
                            "artifacts/example/report.json"
                            if mode == "multi_skill"
                            else None
                        ),
                    )
                    self.assertEqual(check, expected["checks"][index])
                    if mode == "blocked":
                        self.assertTrue(summary["risks"])
                        self.assertTrue(summary["next_actions"])
                        self.assertNotEqual(
                            check["status_values"],
                            expected["checks"][0]["status_values"],
                        )
                    advanced = await call(
                        "append_and_advance", state=state, check=check
                    )
                    state = advanced["state"]
                    self.assertEqual(state["cursor"], index + 1)
                    self.assertEqual(state["checks"], expected["checks"][: index + 1])
                    self.assertEqual(advanced["done"], index == 3)
                self.assertEqual(
                    (await call("cleanup_and_aggregate", state=state))["report"],
                    expected,
                )
                self.assertFalse(root.exists())
                # A failing consumer check remains data and does not stop later cases.
                state = (await call("initialize"))["state"]
                root = Path(state["root"])
                check = (await call("evaluate_fixture", state=state))["check"]
                check.update(ok=False, errors=native.check_summary({}))
                state = (await call("append_and_advance", state=state, check=check))[
                    "state"
                ]
                for _ in range(3):
                    check = (await call("evaluate_fixture", state=state))["check"]
                    advanced = await call(
                        "append_and_advance", state=state, check=check
                    )
                    state = advanced["state"]
                self.assertTrue(advanced["done"])
                failed = (await call("cleanup_and_aggregate", state=state))["report"]
                self.assertFalse(failed["ok"])
                self.assertEqual(len(failed["checks"]), 4)
                self.assertTrue(all(c["ok"] for c in failed["checks"][1:]))
                self.assertFalse(root.exists())
                # Real filesystem error propagates through the native step/MCP boundary.
                state = (await call("initialize"))["state"]
                root = Path(state["root"])
                (root / "single_skill_success.jsonl").mkdir()
                with self.assertRaises(Exception):
                    await call("evaluate_fixture", state=state)
                self.assertFalse(root.exists())
                # Exercise the same filesystem fault through the compiled graph.
                state = (await call("initialize"))["state"]
                root = Path(state["root"])
                (root / "single_skill_success.jsonl").mkdir()
                fault = deepcopy(doc)
                fault["flow"]["steps"][1]["body"]["steps"][0]["arguments"]["state"] = {
                    "literal": state
                }
                rejected = await run(fault)
                self.assertEqual(rejected["status"], "failed", rejected)
                self.assertIsNone(rejected["outputs"])
                self.assertEqual(
                    [c["tool"] for c in rejected["calls"]],
                    [PREFIX + "initialize", PREFIX + "evaluate_fixture"],
                )
                self.assertEqual(rejected["calls"][-1]["status"], "rejected")
                self.assertTrue(rejected["calls"][-1]["transport_call_performed"])
                self.assertFalse(root.exists())
                # Lowering the descriptor bound never accepts a partial report.
                small = deepcopy(doc)
                small["flow"]["steps"][1]["max_iterations"] = 3
                exhausted = await run(small)
                self.assertEqual(exhausted["status"], "failed", exhausted)
                self.assertIsNone(exhausted["outputs"])
                self.assertEqual(len(exhausted["calls"]), 7)
                self.assertNotIn(
                    PREFIX + "cleanup_and_aggregate",
                    [c["tool"] for c in exhausted["calls"]],
                )
                # Policy call budget fails before invoking the next source operation.
                budget = deepcopy(doc)
                budget["policy"]["limits"]["max_operation_calls"] = 2
                limited = await run(budget)
                self.assertEqual(limited["status"], "failed")
                self.assertIsNone(limited["outputs"])
                self.assertEqual(len(limited["calls"]), 3)
                self.assertEqual(limited["calls"][-1]["status"], "rejected")
                self.assertFalse(
                    limited["calls"][-1].get("transport_call_performed", False)
                )
                self.assertIn("budget", limited["calls"][-1]["error"])
                # Explicit unfinished scope proves server shutdown cleanup as well.
                state = (await call("initialize"))["state"]
                unfinished.append(Path(state["root"]))
                self.assertTrue(unfinished[-1].exists())
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        for path in unfinished:
            self.assertFalse(path.exists())
        self.assertEqual(
            set(Path(tempfile.gettempdir()).glob("reasoning-consumer-*")), preexisting
        )
        if failure is not None:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
