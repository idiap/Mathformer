#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Real deterministic reflection fixtures, MCP tools, Lunar compilation and PRISM.

There is no provider/model or external theorem compiler in this workflow. The
reflector Python subprocesses run against fixed synthetic text and temporary
ledgers only. No provider configuration, production inputs or artifacts are used.
Test graphs also feed native capture ports to exercise all validation branches;
no production implementation or PRISM compiler/runtime is substituted.
"""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.path[:0] = [str(LUNAR / "app/backend"), str(ROOT / "scripts"), str(ROOT)]

import asyncio
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import unittest
import yaml
from formal_answer_policy_tools import source
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_physics_sympy_formal_answer_reflection_policy_workflow/workflow.yaml"
AUTHORED = "skills/control/workflow-contract-validator/references/formal-answer-policy.workflow.json"
PREFIX = "mathformer_formal_answer_policy_"


def load(path, name):
    spec = importlib.util.spec_from_loader(name, SourceFileLoader(name, str(path)))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assets(doc):
    texts = {DESCRIPTOR: json.dumps(doc)}
    texts.update(
        {
            s["path"]: (ROOT / s["path"]).read_text()
            for s in doc["provenance"]["sources"]
        }
    )
    return [
        dict(
            path=p,
            content=t,
            encoding="text",
            sha256=hashlib.sha256(t.encode()).hexdigest(),
        )
        for p, t in texts.items()
    ]


class Observed:
    def __init__(self, remote, damage=None):
        self.remote, self.damage, self.events, self.directories = remote, damage, [], []

    async def tools(self):
        return await self.remote.tools()

    async def call(self, name, arguments):
        result = await self.remote.call(name, arguments)
        self.events.append((name, deepcopy(arguments), deepcopy(result)))
        if name == PREFIX + "prepare":
            ledger = result["ledger"]
            self.directories.append(Path(ledger["directory"]))
            if self.damage == "json":
                Path(ledger["path"]).write_text("{broken")
        if name == PREFIX + "negative":
            assert not Path(arguments["ledger"]["directory"]).exists()
        return result


class PolicyTests(unittest.TestCase):
    def test_original_and_generator(self):
        original = load(
            ROOT / "tests/mcp/fixtures/formal_answer_policy_original.py.txt",
            "_policy_original",
        )
        self.assertEqual(
            hashlib.sha256(
                (
                    ROOT / "tests/mcp/fixtures/formal_answer_policy_original.py.txt"
                ).read_bytes()
            ).hexdigest(),
            "b9b21835cad7840e0c36e1552c756f4a31f27bb82789ebfa600e6ace57b3a08a",
        )
        original.REPO_ROOT, original.REFLECTOR = source().REPO_ROOT, source().REFLECTOR
        self.assertEqual(original.run_policy_check(), source().run_policy_check())
        streams = []
        for module in (original, source()):
            stream = io.StringIO()
            with redirect_stdout(stream):
                code = module.main(["--json"])
            streams.append((code, stream.getvalue()))
        self.assertEqual(streams[0], streams[1])
        generator = load(
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
            "_policy_generator",
        )
        authored = json.loads((ROOT / AUTHORED).read_text())
        self.assertEqual(
            [d for d in generator.inventory() if d["id"] == authored["id"]], [authored]
        )

    def test_mcp_and_real_prism(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(
                os.environ.get("WORKFLOW_CONTRACT_PATH", ROOT / DESCRIPTOR)
            ).read_text()
        )
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["id"], "hub_physics_sympy_formal_answer_reflection_policy_workflow"
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");import mcp_server; mcp_server._READONLY=True;mcp_server.mcp.run(transport="stdio")'
        failure = None
        async with manager.open(
            "policy",
            StdioConfig(
                command=str(ROOT / ".venv/bin/python"),
                args=["-c", server],
                cwd=str(ROOT),
            ),
            {},
        ) as remote:
            try:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile(doc, inventory=None):
                    received = assets(doc)
                    compiled = compile_workflow(
                        "mcp:policy",
                        workflow_documents([DESCRIPTOR], received)[0],
                        tools if inventory is None else inventory,
                    )
                    return compiled, received

                compiled, received = compile(document)
                self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                self.assertTrue(compiled["runtime_source"])
                self.assertEqual(set(compiled["bindings"]), set(document["operations"]))
                self.assertFalse(compile(document, [])[0]["runnable"])

                async def authorize():
                    pass

                async def run(doc, inputs=None, damage=None):
                    graph, received = compile(doc)
                    self.assertTrue(graph["runnable"], graph["diagnostics"])
                    observed = Observed(remote, damage)
                    result = await execute(
                        graph, received, inputs or {}, observed, authorize
                    )
                    self.assertTrue(all(not p.exists() for p in observed.directories))
                    return result, observed

                result, observed = await run(document)
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(
                    result["outputs"]["report"], source().run_policy_check()
                )
                self.assertEqual(
                    [e[0] for e in observed.events],
                    [
                        PREFIX + n
                        for n in (
                            "prepare",
                            "positive",
                            "negative",
                            "initialize",
                            "inspect_candidate",
                            "inspect_candidate",
                            "finish",
                        )
                    ],
                )
                captures = [
                    e[2]["capture"] for e in observed.events if "capture" in e[2]
                ]
                self.assertEqual(
                    [c["report"]["status"] for c in captures], ["complete", "blocked"]
                )
                self.assertEqual(
                    len(captures[0]["report"]["improvement_candidates"]), 2
                )
                states = [
                    e[2]["state"]
                    for e in observed.events
                    if e[0] == PREFIX + "inspect_candidate"
                ]
                self.assertEqual([s["index"] for s in states], [1, 2])
                self.assertEqual([s["pending"] for s in states], [True, False])
                self.assertEqual([s["findings"] for s in states], [[], []])
                self.assertTrue(result["runtime"]["effect_records"])
                self.assertTrue(result["replay_artifacts"])
                # A malformed temporary fixture ledger causes the actual child to
                # exit nonzero with unparsable stdout. Both calls still precede checks.
                result, observed = await run(document, damage="json")
                self.assertEqual(result["status"], "accepted", result)
                self.assertFalse(result["outputs"]["report"]["ok"])
                self.assertEqual(observed.events[1][2]["capture"]["report"], {})
                self.assertNotEqual(observed.events[1][2]["capture"]["returncode"], 0)
                self.assertEqual(
                    [f["code"] for f in result["outputs"]["report"]["findings"]],
                    [
                        "positive_reflector_command_failed",
                        "valid_ledger_not_accepted",
                        "ledger_status_not_valid",
                        "formal_answer_ground_truth_policy_missing",
                        "monotonic_bypass_rejection_missing",
                    ],
                )
                # Deterministic validation subgraphs consume actual capture ports.
                validation = deepcopy(document)
                validation["inputs"] = {
                    "positive": {"type": "Capture"},
                    "negative": {"type": "Capture"},
                }
                validation["flow"]["steps"] = validation["flow"]["steps"][3:]
                init = validation["flow"]["steps"][0]
                init["arguments"] = {
                    "ledger": {
                        "literal": {
                            "directory": "closed-fixture",
                            "path": "closed-fixture/pre_reflection_ledger.json",
                        }
                    },
                    "findings": {"literal": []},
                    "positive": {"ref": "inputs.positive"},
                }

                def replace(value):
                    if isinstance(value, dict):
                        for k, v in value.items():
                            if k == "ref" and v in (
                                "steps.positive.outputs.capture",
                                "steps.negative.outputs.capture",
                            ):
                                value[k] = "inputs." + v.split(".")[1]
                            else:
                                replace(v)
                    elif isinstance(value, list):
                        for v in value:
                            replace(v)

                replace(validation["flow"])
                reflector = load(source().REFLECTOR, "_policy_reflector_fixture")
                ledger = {
                    "candidate_report_exists": True,
                    "created_before_formal_answer_inspection": True,
                }
                for count, text in [
                    (0, "candidate"),
                    (1, "positive"),
                    (2, "positive scalar"),
                ]:
                    positive = {
                        "returncode": 0,
                        "stderr": "",
                        "report": reflector.build_reflection(
                            "candidate", text, "fixture", ledger
                        ),
                    }
                    negative = {
                        "returncode": 0,
                        "stderr": "",
                        "report": reflector.build_reflection(
                            "candidate", "formal", "fixture"
                        ),
                    }
                    self.assertEqual(
                        len(positive["report"]["improvement_candidates"]), count
                    )
                    inputs = {"positive": positive, "negative": negative}
                    expected_state = source().initialize_candidates(
                        [], deepcopy(positive)
                    )
                    while expected_state["pending"]:
                        expected_state = source().inspect_candidate(expected_state)
                    expected = source().finish_policy(
                        expected_state, positive, negative
                    )
                    result, observed = await run(validation, inputs)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(result["outputs"]["report"], expected)
                    self.assertEqual(len(observed.events), 2 + max(1, count))
                    if count == 2:
                        bounded = deepcopy(validation)
                        bounded["flow"]["steps"][1]["max_iterations"] = 1
                        failed, _ = await run(bounded, inputs)
                        self.assertEqual(failed["status"], "failed", failed)
                        self.assertIsNone(failed["outputs"])
                        self.assertIn("exhaust", str(failed).lower())
                bad_positive = {
                    "returncode": 9,
                    "report": {
                        "status": "blocked",
                        "policy": {},
                        "improvement_candidates": [{}, {}],
                    },
                    "stderr": "positive diagnostic",
                }
                bad_negative = {
                    "returncode": 8,
                    "report": {"status": "complete", "findings": [{"code": "other"}]},
                    "stderr": "negative diagnostic",
                }
                result, _ = await run(
                    validation, {"positive": bad_positive, "negative": bad_negative}
                )
                report = result["outputs"]["report"]
                self.assertFalse(report["ok"])
                self.assertEqual(len(report["findings"]), 12)
                self.assertEqual(
                    [f["severity"] for f in report["findings"]],
                    ["high"] * 9 + ["medium", "high", "high"],
                )
                self.assertEqual(report["findings"][5]["item"], {})
                self.assertEqual(report["findings"][9]["stderr"], "negative diagnostic")
                good = deepcopy(captures[0])
                medium = deepcopy(captures[1])
                medium.update(returncode=4, stderr="medium only")
                result, _ = await run(
                    validation, {"positive": good, "negative": medium}
                )
                self.assertTrue(result["outputs"]["report"]["ok"])
                self.assertEqual(
                    result["outputs"]["report"]["findings"],
                    [
                        {
                            "severity": "medium",
                            "code": "negative_reflector_command_returned_nonzero",
                            "stderr": "medium only",
                        }
                    ],
                )
                malformed = deepcopy(good)
                malformed["report"] = []
                failed, observed = await run(
                    validation, {"positive": malformed, "negative": medium}
                )
                self.assertEqual(failed["status"], "failed", failed)
                self.assertEqual(
                    len(observed.events), 0
                )  # rejected transport is recorded in runtime calls
                self.assertEqual(len(failed["calls"]), 1)
                self.assertEqual(failed["calls"][0]["status"], "rejected")
                bounded = deepcopy(validation)
                bounded["policy"]["limits"]["max_operation_calls"] = 2
                failed, _ = await run(bounded, {"positive": good, "negative": medium})
                self.assertEqual(failed["status"], "failed", failed)
                self.assertIn("budget", str(failed).lower())
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in failed["calls"]
                    ),
                    2,
                )
                malformed_negative = deepcopy(medium)
                malformed_negative["report"]["findings"] = [None]
                failed, _ = await run(
                    validation, {"positive": good, "negative": malformed_negative}
                )
                self.assertEqual(failed["status"], "failed", failed)
                self.assertEqual(len(failed["calls"]), 4)
                self.assertEqual(failed["calls"][-1]["status"], "rejected")
                timed = deepcopy(validation)
                timed["policy"]["limits"]["wall_time_seconds"] = 1
                graph, received = compile(timed)

                async def pending_authorization():
                    await asyncio.Event().wait()

                with self.assertRaises(TimeoutError):
                    await execute(
                        graph,
                        received,
                        {"positive": good, "negative": medium},
                        remote,
                        pending_authorization,
                    )
                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        PREFIX + "negative",
                        {"ledger": {"directory": "unknown", "path": "unknown"}},
                    )
                abandoned = await remote.call(PREFIX + "prepare", {})
                abandoned_directory = Path(abandoned["ledger"]["directory"])
                self.assertTrue(abandoned_directory.exists())
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure:
            raise failure
        self.assertFalse(abandoned_directory.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
