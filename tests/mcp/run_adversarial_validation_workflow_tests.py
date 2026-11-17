#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Offline provider fixtures through production MCP, real Lunar and PRISM.

There is no scientific compiler/prover boundary in this ERFL profile. PRISM's
parser/checker/compiler/runtime are real and are never replaced by fixtures.
The candidate/installed contract is always explicitly supplied by the host.
"""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT / "tests/mcp/fixtures"),
]

import asyncio
from copy import deepcopy
import hashlib
import importlib.util
import json
import tempfile
import unittest
import yaml

import adversarial_validation_tools as native
from adversarial_provider import FixtureProvider
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/profile/profile_adversarial_validation_workflow/workflow.yaml"
PREFIX = "mathformer_adversarial_"


def document():
    return yaml.safe_load(Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text())


def snapshot(doc):
    def asset(path, content):
        return {
            "path": path,
            "content": content,
            "encoding": "text",
            "sha256": hashlib.sha256(content.encode()).hexdigest(),
        }

    return [asset(DESCRIPTOR, json.dumps(doc))] + [
        asset(row["path"], (ROOT / row["path"]).read_text())
        for row in doc["provenance"]["sources"]
    ]


class AdversarialValidationTests(unittest.TestCase):
    def test_definition_and_native_steps(self):
        doc = document()
        self.assertEqual(doc["id"], "profile_adversarial_validation_workflow")
        self.assertEqual(doc["lifecycle"], "active")
        self.assertEqual(
            doc,
            json.loads(
                (
                    ROOT
                    / "skills/control/workflow-contract-validator/references/adversarial-validation.workflow.json"
                ).read_text()
            ),
        )
        self.assertEqual(doc["policy"]["failure"]["retry"]["max_attempts"], 1)
        self.assertEqual(doc["policy"]["limits"]["max_operation_calls"], 4)
        self.assertIn(
            "examples/reasoning_flows/adversarial_validation.rflow",
            [r["path"] for r in doc["provenance"]["sources"]],
        )
        for row in doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        # Preserve the original dependency and terminal statements; no operational
        # loop/bound exists in the original ERFL and none is invented here.
        source = (
            ROOT / "examples/reasoning_flows/adversarial_validation.rflow"
        ).read_text()
        for text in (
            "p:P[target::Claim,scope::Scope->probe_evidence::Evidence]",
            "on e.refuted => stop",
            "on e.not_refuted_within_scope => accept",
            "on e.blocked => stop",
        ):
            self.assertIn(text, source)
        self.assertEqual(
            [s["id"] for s in doc["flow"]["steps"]], ["p", "r", "e", "terminal"]
        )
        with self.assertRaisesRegex(ValueError, "explicit Mathformer"):
            native.configured_provider(None)
        # Terminal implementations guard the same decisions even when invoked
        # directly, outside the compiled switch.
        for decision in native.DECISIONS:
            allowed = decision == "not_refuted_within_scope"
            self.assertFalse(
                native.terminal(decision, {}, accept=allowed)["establishes_proof"]
            )
            with self.assertRaises(ValueError):
                native.terminal(decision, {}, accept=not allowed)
        with self.assertRaises(ValueError):
            native.terminal("proved", {}, accept=False)
        # Generator adoption reads the authored contract without touching the
        # host-owned installed YAML/catalog or generating scientific artifacts.
        path = (
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py"
        )
        spec = importlib.util.spec_from_file_location("adversarial_normalizer", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        generated = module.adversarial_validation_descriptor()
        self.assertEqual(generated, doc)

    def test_real_mcp_lunar_execution(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        doc = document()
        target = {"claim": "x squared is nonnegative", "assumptions": ["real x"]}
        manager = SessionManager()
        with tempfile.TemporaryDirectory(prefix="adversarial-fixture-") as temporary:
            ledger = Path(temporary) / "provider.jsonl"
            server = (
                'import sys;sys.path[:0]=["scripts","tests/mcp/fixtures"];'
                "from adversarial_provider import serve;serve(sys.argv[1])"
            )
            server_python = ROOT / ".venv/bin/python"
            failure = None
            async with manager.open(
                "adversarial",
                StdioConfig(
                    command=(
                        str(server_python) if server_python.exists() else sys.executable
                    ),
                    args=["-c", server, str(ledger)],
                    cwd=str(ROOT),
                ),
                {},
            ) as remote:
                try:
                    tools = [
                        t.model_dump(by_alias=True, exclude_none=True)
                        for t in await remote.tools()
                    ]

                    def compile(selected=doc, inventory=tools):
                        assets = snapshot(selected)
                        workflow = workflow_documents([DESCRIPTOR], assets)[0]
                        return (
                            compile_workflow("mcp:adversarial", workflow, inventory),
                            assets,
                        )

                    compiled, assets = compile()
                    self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                    self.assertTrue(compiled["runtime_source"])
                    self.assertEqual(set(compiled["bindings"]), set(doc["operations"]))
                    for name, binding in compiled["bindings"].items():
                        self.assertEqual(binding["tool"], PREFIX + name)
                    self.assertFalse(compile(inventory=[])[0]["runnable"])

                    async def authorize():
                        pass

                    async def run(case, selected=doc):
                        ledger.unlink(missing_ok=True)
                        selected_compiled, selected_assets = (
                            (compiled, assets) if selected is doc else compile(selected)
                        )
                        inputs = {
                            "target": target,
                            "scope": {
                                "case": case,
                                "dimensions": ["algebra", "domain"],
                            },
                        }
                        result = await execute(
                            selected_compiled,
                            selected_assets,
                            inputs,
                            remote,
                            authorize,
                        )
                        history = (
                            [
                                json.loads(line)
                                for line in ledger.read_text().splitlines()
                            ]
                            if ledger.exists()
                            else []
                        )
                        return result, history, inputs

                    def calls(result):
                        return [c["tool"].removeprefix(PREFIX) for c in result["calls"]]

                    # All three authored branches, with exact provider arguments,
                    # state handoffs and direct-entrypoint parity.
                    for decision in native.DECISIONS:
                        result, history, inputs = await run(decision)
                        provider = FixtureProvider()
                        expected = native.run_validation(**inputs, provider=provider)
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertEqual(result["outputs"], expected)
                        self.assertEqual(history, provider.calls)
                        self.assertEqual(
                            [h["stage"] for h in history], ["p:P", "r:R", "e:E"]
                        )
                        terminal = (
                            "accept"
                            if decision == "not_refuted_within_scope"
                            else "stop"
                        )
                        self.assertEqual(
                            calls(result), ["probe", "assess", "calibrate", terminal]
                        )
                        self.assertEqual(expected["outcome"]["scope"], inputs["scope"])
                        self.assertFalse(expected["outcome"]["establishes_proof"])
                        self.assertEqual(
                            result["outputs"]["validation_status"], decision
                        )
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["replay_artifacts"])
                    # Each source stage fails once, preserving all preceding
                    # calls, and prevents every downstream stage and terminal.
                    for phase, count in [("p", 1), ("r", 2), ("e", 3)]:
                        for kind in ("error", "invalid", "malformed"):
                            case = kind + "_" + phase
                            result, history, inputs = await run(case)
                            self.assertEqual(result["status"], "failed", result)
                            self.assertIsNone(result["outputs"])
                            self.assertEqual(len(history), count)
                            self.assertEqual(
                                calls(result), ["probe", "assess", "calibrate"][:count]
                            )
                            provider = FixtureProvider()
                            with self.assertRaises((RuntimeError, ValueError)):
                                native.run_validation(**inputs, provider=provider)
                            self.assertEqual(history, provider.calls)
                    result, history, _ = await run("unknown_decision")
                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(len(history), 3)
                    self.assertEqual(calls(result), ["probe", "assess", "calibrate"])
                    self.assertIsNone(result["outputs"])
                    # Runtime budget exhaustion is a host failure, never scoped
                    # acceptance. No source-owned retry/iteration is synthesized.
                    budget = deepcopy(doc)
                    budget["policy"]["limits"]["max_operation_calls"] = 2
                    result, history, _ = await run("not_refuted_within_scope", budget)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(len(history), 2)
                    self.assertEqual(len(result["calls"]), 3)
                    self.assertEqual(result["calls"][-1]["status"], "rejected")
                    self.assertIsNone(result["outputs"])
                    self.assertIn("budget", json.dumps(result).lower())
                    # The terminal itself is also counted and may not fabricate
                    # an acceptance receipt after the three provider stages.
                    budget["policy"]["limits"]["max_operation_calls"] = 3
                    result, history, _ = await run("not_refuted_within_scope", budget)
                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(len(history), 3)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(result["calls"][-1]["status"], "rejected")
                    # Null is a legitimate opaque source Claim/Scope payload.
                    stopped = await remote.call(
                        PREFIX + "stop", {"validation_status": "blocked", "scope": None}
                    )
                    self.assertEqual(stopped["outcome"]["scope"], None)
                    self.assertFalse(stopped["outcome"]["establishes_proof"])
                except Exception as error:
                    failure = error
            self.assertFalse(manager.active)
            if failure is not None:
                raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
