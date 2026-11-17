#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native Agent C, registered MCP and Lunar PRISM parity without live services."""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.dont_write_bytecode = True
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT / "tests/mcp/fixtures"),
]
sys.path.extend(str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages"))
import asyncio
from copy import deepcopy
from dataclasses import asdict
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import json
import tempfile
import unittest
import yaml
from agentc_workflow_tools import agentc_module
from agentc_refinement_workflow_tools import RefinementSteps, register_refinement_tools
from agentc_refinement_boundary import install
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/loop/loop_draft_execute_refine_loop_workflow/workflow.yaml"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"]).resolve()
DOCUMENT = yaml.safe_load(CONTRACT.read_text())
REQUEST = dict(
    informal_statement="A true proposition",
    aspect_description="Preserve the complete source meaning",
    max_iterations=4,
    file_prefix="fixture",
    dependency_context="dependency facts",
    alignment_hints="alignment facts",
    core_statement_annotations="core annotations",
    informal_formal_pairs=[["example statement", "example code"]],
)


def oracle():
    loader = SourceFileLoader(
        "agentc_refinement_original",
        str(ROOT / "tests/mcp/fixtures/agentc_refinement_original.py.txt"),
    )
    module = importlib.util.module_from_spec(
        importlib.util.spec_from_loader(loader.name, loader)
    )
    sys.modules[loader.name] = module
    loader.exec_module(module)
    return module


def stable(value):
    if isinstance(value, dict):
        return {
            k: stable(v)
            for k, v in value.items()
            if k
            not in {
                "step_timings_ms",
                "duration_ms",
                "error_log_path",
                "error_log_text",
            }
        }
    if isinstance(value, list):
        return [stable(v) for v in value]
    return value


def assets(document):
    values = {
        s["path"]: (ROOT / s["path"]).read_text()
        for s in document["provenance"]["sources"]
    }
    values[DESCRIPTOR] = json.dumps(document)
    return [
        dict(
            path=p,
            content=s,
            encoding="text",
            sha256=hashlib.sha256(s.encode()).hexdigest(),
        )
        for p, s in values.items()
    ]


def ledger(directory, name):
    path = Path(directory) / name
    if name == "events.jsonl" and not path.exists():
        files = sorted(
            Path(directory).glob("agentc_steps/step-*/native-events.jsonl"),
            key=lambda p: p.stat().st_mtime_ns,
        )
        return [json.loads(line) for p in files for line in p.read_text().splitlines()]
    return (
        [json.loads(line) for line in path.read_text().splitlines()]
        if path.exists()
        else []
    )


class RefinementTests(unittest.TestCase):
    def test_authored_contract_and_provenance(self):
        self.assertEqual(
            DOCUMENT,
            json.loads(
                (
                    ROOT
                    / "skills/control/workflow-contract-validator/references/agentc-refinement.workflow.json"
                ).read_text()
            ),
        )
        self.assertEqual(DOCUMENT["lifecycle"], "active")
        selected = "skills/autoformalization/autoformalization-agentc/scripts/agentc.py"
        self.assertIn(selected, [s["path"] for s in DOCUMENT["provenance"]["sources"]])
        for source in DOCUMENT["provenance"]["sources"]:
            self.assertEqual(
                source["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / source["path"]).read_bytes()).hexdigest(),
            )

    def test_native_resume_and_interfaces(self):
        from mcp.server.fastmcp import FastMCP

        with tempfile.TemporaryDirectory() as tmp:
            factory, calls, events = install(agentc_module(), tmp, "semantic_unknown")
            steps = RefinementSteps(DOCUMENT, factory)
            request = {
                **REQUEST,
                "initial_formalization": "",
                "initial_formalization_raw": "seed raw",
            }
            state = steps.call("prepare_state", {"request": request})["state"]
            self.assertEqual(state["code"], "")
            self.assertFalse(any(c["kind"] == "draft" for c in calls))
            self.assertEqual(
                steps.call("compute_guard", {"state": state}),
                {"route": "semantic_repair"},
            )
            state["prior_hard_feedback"] = "stale hard"
            state["prior_soft_feedback"] = "stale soft"
            changed = steps.call(
                "semantic_repair_round", dict(request=request, state=state)
            )
            self.assertEqual(
                changed["state"]["prior_hard_feedback"],
                state["correctness"] + "\n" + state["error_details"],
            )
            self.assertEqual(
                changed["state"]["prior_soft_feedback"], state["semantic_judgement"]
            )
            self.assertFalse(changed["stop"])
            self.assertEqual(calls[-3]["kind"], "compile")
            self.assertIn(
                REQUEST["aspect_description"],
                next(
                    c["payload"][-1]["content"]
                    for c in calls
                    if c["kind"] == "semantic"
                ),
            )
            before = len(calls)
            with self.assertRaisesRegex(ValueError, "guard"):
                steps.call(
                    "formal_repair_round", dict(request=request, state=changed["state"])
                )
            self.assertEqual(len(calls), before)
            with self.assertRaisesRegex(ValueError, "schema"):
                steps.call(
                    "prepare_state", {"request": {**request, "max_iterations": 5}}
                )
            with self.assertRaisesRegex(ValueError, "artifact name"):
                steps.call(
                    "prepare_state", {"request": {**request, "file_prefix": "../bad"}}
                )
            # Guard comparison is exact; a noncanonical compiler string takes priority.
            for correctness, judgement, route in [
                ("true", "Judgement: True", "formal_repair"),
                ("True", "Judgement: False", "semantic_repair"),
                ("True", "unknown", "semantic_repair"),
                ("True", "Judgement: True", "early_stop"),
            ]:
                self.assertEqual(
                    steps.call(
                        "compute_guard",
                        {
                            "state": {
                                **state,
                                "correctness": correctness,
                                "semantic_judgement": judgement,
                            }
                        },
                    )["route"],
                    route,
                )

            async def policy():
                registry = FastMCP("readonly")

                def denied():
                    raise PermissionError("read-only policy")

                register_refinement_tools(
                    registry, denied, agent_factory=factory, document=DOCUMENT
                )
                with self.assertRaisesRegex(Exception, "read-only policy"):
                    await registry.call_tool(
                        "mathformer_agentc_workflow_prepare_state", {"request": request}
                    )

            asyncio.run(policy())

    def test_lunar_compiler_runtime_registered_tools_and_original_parity(self):
        asyncio.run(self.execute_cases())

    async def execute_cases(self):
        for mode in [
            "early",
            "formal",
            "semantic_false",
            "semantic_unknown",
            "mixed",
            "cap",
            "last",
            "draft_failure",
            "soft_failure",
            "formal_failure",
            "semantic_failure",
            "compiler_failure",
            "taxonomy_failure",
        ]:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                directory = Path(tmp) / "remote"
                request = deepcopy(REQUEST)
                if mode == "early":
                    request.update(
                        initial_formalization="", initial_formalization_raw="seed raw"
                    )
                original = oracle()
                original_factory, native_calls, native_events = install(
                    original, Path(tmp) / "oracle", mode
                )
                expected_error = None
                try:
                    with original_factory(request) as agent:
                        native_args = {
                            k: v
                            for k, v in request.items()
                            if k not in {"aspect_description", "max_iterations"}
                        }
                        history = [
                            asdict(h)
                            for h in agent.run(
                                **native_args, trace_event=agent.workflow_trace_event
                            )
                        ]
                except (TimeoutError, OSError) as error:
                    expected_error = error
                manager = SessionManager()
                code = "from agentc_refinement_boundary import serve; import sys; serve(sys.argv[1],sys.argv[2],sys.argv[3])"
                paths = [
                    str(ROOT / "tests/mcp/fixtures"),
                    str(ROOT / "scripts"),
                    *[
                        str(p)
                        for p in (ROOT / ".venv/lib").glob("python*/site-packages")
                    ],
                ]
                env = {"PYTHONPATH": os.pathsep.join(paths)}
                failure = None
                async with manager.open(
                    "agentc-fixture",
                    StdioConfig(
                        command=sys.executable,
                        args=["-c", code, str(directory), mode, str(CONTRACT)],
                        cwd=str(ROOT),
                    ),
                    env,
                ) as remote:
                    try:
                        tools = [
                            t.model_dump(by_alias=True, exclude_none=True)
                            for t in await remote.tools()
                        ]

                        def compile_document(document):
                            snapshot = assets(document)
                            workflow = workflow_documents([DESCRIPTOR], snapshot)[0]
                            compiled = compile_workflow(
                                "mcp:agentc-fixture", workflow, tools
                            )
                            self.assertTrue(
                                compiled["runnable"], compiled["diagnostics"]
                            )
                            self.assertEqual(
                                set(compiled["bindings"]), set(document["operations"])
                            )
                            return compiled, snapshot

                        compiled, snapshot = compile_document(DOCUMENT)

                        async def authorize():
                            pass

                        result = await execute(
                            compiled, snapshot, {"request": request}, remote, authorize
                        )
                        if expected_error:
                            self.assertEqual(
                                result["status"],
                                "failed",
                                {
                                    k: result.get(k)
                                    for k in ["status", "calls", "failure_disposition"]
                                },
                            )
                            self.assertIsNone(result["outputs"])
                            self.assertEqual(result["calls"][-1]["status"], "rejected")
                            self.assertEqual(
                                len(
                                    [
                                        c
                                        for c in ledger(directory, "calls.jsonl")
                                        if c["kind"].endswith("failure")
                                    ]
                                ),
                                0,
                            )
                            self.assertEqual(
                                [c["kind"] for c in ledger(directory, "calls.jsonl")],
                                [c["kind"] for c in native_calls],
                            )
                            self.assertFalse(
                                any(
                                    e["event"] == "iterative_run_complete"
                                    for e in ledger(directory, "events.jsonl")
                                )
                            )
                            continue
                        self.assertEqual(
                            result["status"],
                            "accepted",
                            {
                                k: result.get(k)
                                for k in ["status", "calls", "failure_disposition"]
                            },
                        )
                        state = result["outputs"]["final_state"]
                        self.assertEqual(stable(state["history"]), stable(history))
                        self.assertEqual(result["outputs"]["history"], state["history"])
                        self.assertEqual(
                            result["outputs"]["final_code"], history[-1]["code"]
                        )
                        self.assertEqual(ledger(directory, "calls.jsonl"), native_calls)
                        events = ledger(directory, "events.jsonl")
                        self.assertEqual(
                            [e["event"] for e in events],
                            [e["event"] for e in native_events],
                        )
                        self.assertEqual(
                            sum(e["event"] == "iterative_run_complete" for e in events),
                            1,
                        )
                        self.assertTrue(
                            all(
                                h["step_timings_ms"] and h["refinement_analysis"]
                                for h in state["history"]
                            )
                        )
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["replay_artifacts"])
                        if mode in {"cap", "last"}:
                            self.assertEqual(state["round_index"], 4)
                            self.assertEqual(len(state["history"]), 5)
                            self.assertNotIn(
                                "EarlyStop", [h["agent_name"] for h in state["history"]]
                            )
                            self.assertEqual(
                                state["correctness"],
                                "False" if mode == "cap" else "True",
                            )
                            before = len(ledger(directory, "calls.jsonl"))
                            resumed = await execute(
                                compiled,
                                snapshot,
                                {"request": request, "resume_state": state},
                                remote,
                                authorize,
                            )
                            self.assertEqual(resumed["status"], "accepted", resumed)
                            self.assertEqual(resumed["outputs"]["final_state"], state)
                            self.assertEqual(
                                [c["operation"] for c in resumed["calls"]],
                                ["prepare_state", "compute_guard", "return_current"],
                            )
                            self.assertEqual(
                                len(ledger(directory, "calls.jsonl")), before
                            )
                        else:
                            self.assertEqual(
                                state["history"][-1]["agent_name"], "EarlyStop"
                            )
                            self.assertEqual(
                                state["history"][-1]["code"],
                                state["history"][-2]["code"],
                            )
                        if mode == "early":
                            self.assertEqual(state["code"], "")
                        if mode == "cap":
                            # Actual schema exhaustion failure remains a sentinel; the
                            # native cap completes normally through its explicit stop.
                            bounded = deepcopy(DOCUMENT)
                            bounded["flow"]["steps"][1]["max_iterations"] = 1
                            cut, snap = compile_document(bounded)
                            failed = await execute(
                                cut, snap, {"request": request}, remote, authorize
                            )
                            self.assertEqual(
                                failed["status"],
                                "failed",
                                {
                                    k: failed.get(k)
                                    for k in ["status", "calls", "failure_disposition"]
                                },
                            )
                            self.assertIsNone(failed["outputs"])
                            self.assertEqual(
                                [c["operation"] for c in failed["calls"]],
                                [
                                    "prepare_state",
                                    "compute_guard",
                                    "formal_repair_round",
                                ],
                            )
                        # Mid-loop resume recomputes feedback and begins at the next
                        # native round without initial drafting/critique.
                        if mode == "mixed":
                            first = await remote.call(
                                "mathformer_agentc_workflow_prepare_state",
                                {"request": request},
                            )
                            saved = first["state"]
                            saved["prior_hard_feedback"] = "ignored"
                            saved["prior_soft_feedback"] = "ignored"
                            resumed = await execute(
                                compiled,
                                snapshot,
                                {"request": request, "resume_state": saved},
                                remote,
                                authorize,
                            )
                            self.assertEqual(resumed["status"], "accepted", resumed)
                            self.assertEqual(
                                stable(resumed["outputs"]["history"]), stable(history)
                            )
                    except Exception as error:
                        failure = error
                self.assertFalse(manager.active)
                if failure:
                    raise failure


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False).result
    sys.exit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
