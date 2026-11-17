#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402 - test entrypoint configures import paths before dependencies.
"""Scratch artifact fixtures through native subprocesses, MCP, Lunar and PRISM.

No stage/report implementation is substituted. These stages use supplied Python
artifact callbacks and have no external model/compiler boundary of their own.
The deterministic artifacts stand at that input boundary; PRISM compilation,
source validators, design review, mapping, controller and emissions are real.
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
import io
import json
import re
import shutil
import tempfile
import unittest
import yaml
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.workflow_contract.validator import validate
from mcp_connections.execution import execute
from sympy_source_only_tools import SOURCE, packed

REFERENCES = "skills/control/workflow-contract-validator/references"
AUTHORED = ROOT / REFERENCES / "sympy-source-only.workflow.json"
ID = "hub_physics_sympy_source_only_recursive_0000_workflow"
DESCRIPTOR = f"{REFERENCES}/normalized-workflows/hub/{ID}/workflow.yaml"
ORIGINAL = ROOT / "tests/mcp/fixtures/sympy_source_only_original.py.txt"
PREFIX = "mathformer_sympy_source_only_"
CASE = "formalphysics_0000"
OUTPUT_PORT = "result"
ASSESS_OPERATION = "assess"
ORDER = [
    "goal_plan",
    "design_guard_review",
    "repair_expansion_map",
    "recursive_repair_control",
    "grounded_sample_thoroughness",
]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def artifact(mode="complete"):
    """Small deterministic executable input, with observable callback history."""
    planner = load(
        ROOT
        / SOURCE.replace(
            "run_recursive_goal_case.py", "plan_goal_sample_sympy_autoformalization.py"
        ),
        "fixture_constants",
    )
    fields = {name: [] for name in planner.REQUIRED_SURFACES}
    fields.update(
        CLAIM={
            "statement_nl": "A fixed local identity",
            "statement_latex": "x=x",
            "source_anchors": ["L1"],
            "commentary_header": "\n".join(planner.COMMENTARY_MARKERS),
        },
        EQUATION_SURFACE={
            "EQUATION_GRAPH": {
                "nodes": [{"id": "a"}, {"id": "b"}],
                "frame_context": {"frame": "Cartesian"},
            }
        },
        DERIVATION_STEPS=[
            {"generated": False, "source": "source_backed", "source_anchor": "L1"}
        ]
        * (1 if mode == "partial" else 2),
        ASSUMPTION_CONTEXT={
            "CONTEXT_ASSUMPTIONS": [
                {
                    "text": "fixed coordinate frame",
                    "support": "source_backed",
                    "source_anchor": "L1",
                }
            ]
        },
        PROJECTION_BRIDGES=[{"status": "provided"}],
        SYMPY_LIBRARY_GROUNDING={"grounding_level": "high"},
    )
    text = "\n".join(k + " = " + repr(v) for k, v in fields.items()) + "\n"
    text += """from pathlib import Path
import json
history = []
def record(name):
    history.append(name)
    with Path(__file__).with_suffix('.history.jsonl').open('a') as stream:
        stream.write(json.dumps({'name':name,'history':list(history)})+'\\n')
    return {'passed':True,'domain':'x > 0','history':list(history)}
record('import')
"""
    for name in planner.REQUIRED_FUNCTIONS:
        text += f"def {name}(*args):\n    return record({name!r})\n"
    text += """def review_final_equations():
    record('review_final_equations')
    return {'equation':{'status':'pass','findings':[]}}
def run_all():
    result=record('run_all')
    result['final_equation_reviews']={'equation':{'status':'pass'}}
    return result
"""
    if mode == "blocked":
        text += '\ndef validate_dimensions():\n    result=record("validate_dimensions"); result["passed"]=False; return result\n'
    if mode == "crash":
        text += '\ndef validate_no_hidden_target():\n    record("validate_no_hidden_target"); raise RuntimeError("fixture target exception")\n'
    return text


def mount(root):
    root = root.resolve()
    root.mkdir()
    # Real implementations relocated, including the native logging dependency.
    for folder in (
        "skills/physics-sympy",
        "skills/control/reasoning-log-schema-guardian",
        "tests/physics_sympy",
    ):
        shutil.copytree(
            ROOT / folder,
            root / folder,
            ignore=shutil.ignore_patterns("__pycache__"),
            symlinks=True,
        )
    (root / "skills/SKILL_HOOKS.yaml").write_bytes(
        (ROOT / "skills/SKILL_HOOKS.yaml").read_bytes()
    )
    return root


def input_case(root, mode="complete", case=None):
    case = case or CASE
    path = root / "MathformerPhysicsLib/SymPy" / case / "MathformerPhysics.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(artifact(mode))
    path.with_suffix(".history.jsonl").unlink(missing_ok=True)
    record = root / "source.json"
    record.write_text(
        json.dumps(
            {
                "case_id": case,
                "statement_nl": "Local source",
                "statement_latex": "x=x",
                "source_anchors": ["L1"],
            }
        )
    )
    return dict(
        case_id=case,
        source_record="source.json",
        output_root="out",
        regenerate_initial_artifact=False,
    )


def native(root, original=False):
    if original:
        ns = {"__name__": "frozen_source", "__file__": str(root / SOURCE)}
        exec(ORIGINAL.read_text(), ns)
        return type("Oracle", (), ns)
    return load(root / SOURCE, "source_only_scratch")


def stable(value):
    if isinstance(value, dict):
        return {
            k: (["<worker-python>", *stable(v[1:])] if k == "command" else stable(v))
            for k, v in value.items()
            if k
            not in {
                "stdout_bytes",
                "created_at",
                "timestamp_utc",
                "timestamp_unix_ms",
                "monotonic_ns",
                "elapsed_ms_since_log_start",
                "elapsed_ms_since_prev_event",
                "event_index",
            }
        }
    if isinstance(value, list):
        return [stable(v) for v in value]
    if isinstance(value, str):
        # The MCP worker uses the project environment, the oracle uses Lunar's.
        # Normalize only those executable identities, also in nested tracebacks.
        for executable in (ROOT / ".venv/bin/python", LUNAR / ".venv/bin/python"):
            value = value.replace(str(executable), "<worker-python>")
        value = re.sub(r"skill-[a-z0-9-]+-[0-9a-f]{12}", "<skill-call>", value)
        return value
    return value


def assets(doc):
    texts = {DESCRIPTOR: json.dumps(doc)}
    texts.update(
        {
            row["path"]: (ROOT / row["path"]).read_text()
            for row in doc["provenance"]["sources"]
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
    def __init__(self, remote):
        self.remote, self.events = remote, []

    async def tools(self):
        return await self.remote.tools()

    async def call(self, name, args):
        out = await self.remote.call(name, args)
        self.events.append((name, deepcopy(args), deepcopy(out)))
        return out


class SourceOnlyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = yaml.safe_load(Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text())

    def test_contract_and_generator(self):
        self.assertEqual(self.doc["id"], ID)
        self.assertEqual(self.doc["lifecycle"], "active")
        self.assertEqual(self.doc, json.loads(AUTHORED.read_text()))
        self.assertIn(SOURCE, [r["path"] for r in self.doc["provenance"]["sources"]])
        for row in self.doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        result = validate(
            AUTHORED, repository_root=ROOT, require_declared_bindings=True
        )
        self.assertTrue(result["valid"], result["errors"])
        normalizer = load(
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
            "source_only_normalizer",
        )
        self.assertEqual(
            [d for d in normalizer.inventory() if d["id"] == ID], [self.doc]
        )

    def test_frozen_entrypoint_equivalence(self):
        self.assertEqual(
            hashlib.sha256(ORIGINAL.read_bytes()).hexdigest(),
            "937c30fc3407d827f6cbbb55fe99f02c9cbf8370781587c4874fe1a3499b1411",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = mount(Path(tmp) / "scratch")
            for mode in ("complete", "partial", "blocked", "crash"):
                outputs = []
                for original in (True, False):
                    shutil.rmtree(root / "out", ignore_errors=True)
                    input_case(root, mode)
                    module = native(root, original)
                    stream = io.StringIO()
                    with redirect_stdout(stream):
                        code = module.main(
                            [
                                "--case",
                                CASE,
                                "--source-record",
                                str(root / "source.json"),
                                "--output-root",
                                str(root / "out"),
                            ]
                        )
                    payload = json.loads(stream.getvalue())
                    self.assertEqual(code, 3 if payload["status"] == "blocked" else 0)
                    run = root / "out" / CASE
                    events = [
                        json.loads(line)
                        for line in (run / "reasoning.jsonl").read_text().splitlines()
                    ]
                    self.assertEqual(
                        events[-1]["step"], "physics_sympy_source_only_run_complete"
                    )
                    outputs.append(
                        stable(
                            {
                                "payload": payload,
                                "summary": (run / "summary.md").read_text(),
                                "events": events,
                            }
                        )
                    )
                self.assertEqual(*outputs)

    def test_controller_bound_and_precedence(self):
        controller = load(
            ROOT
            / "skills/physics-sympy/physics-sympy-recursive-repair-loop-controller/scripts/control_physics_sympy_recursive_repair.py",
            "source_only_controller",
        )
        expansion = {
            "status": "needs_expansion",
            "exhaustive": True,
            "iteration_signature": "s",
            "outstanding_nodes": [{"id": "n"}],
            "next_frontier": [{"node_id": "n", "action": "repair"}],
        }

        def run(e=expansion, previous=(), iteration=1, maximum=6):
            return controller.build_control_plan(
                expansion_map=e,
                previous_expansion_maps=previous,
                iteration=iteration,
                max_iterations=maximum,
            )

        self.assertEqual(run()["decision"], "recurse")
        for exp, previous, iteration in [
            (expansion, [], 6),
            (expansion, [], 7),
            (expansion, [{"iteration_signature": "s"}], 2),
            ({**expansion, "exhaustive": False}, [], 1),
            ({**expansion, "status": "blocked"}, [], 1),
        ]:
            plan = run(exp, previous, iteration)
            self.assertEqual(plan["decision"], "blocked")
            self.assertTrue(plan["blockers"])
        for status in ("complete", "not_required"):
            self.assertEqual(
                run(
                    {
                        **expansion,
                        "status": status,
                        "exhaustive": False,
                        "outstanding_nodes": [],
                    },
                    iteration=6,
                )["decision"],
                "complete",
            )
        self.assertEqual(
            run({**expansion, "outstanding_nodes": []})["decision"], "complete"
        )

    def test_native_failures_and_loading_boundaries(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = mount(Path(tmp) / "scratch")
            input_case(root)
            n = native(root)
            for stale in ("reasoning.jsonl", "reasoning_log.jsonl"):
                path = root / "out" / CASE / stale
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("stale")
            prepared = n.prepare_run(CASE, root / "source.json", root / "out")
            self.assertEqual(
                prepared["initial_draft"]["status"], "skipped_existing_artifact"
            )
            self.assertFalse((root / "out" / CASE / "reasoning.jsonl").exists())
            self.assertFalse((root / "out" / CASE / "reasoning_log.jsonl").exists())
            state = n.pack_run_state(prepared)
            state["next_stage"] = 5
            with self.assertRaisesRegex(ValueError, "exhausted"):
                n.execute_run_stage(state)
            with self.assertRaises(FileNotFoundError):
                n.run_json([str(root / "absent-executable")], root / "missing.json")
            with self.assertRaises(json.JSONDecodeError):
                n.run_json(
                    [sys.executable, "-c", 'print("invalid JSON")'],
                    root / "missing.json",
                )
            payload, meta = n.run_json(
                [sys.executable, "-c", 'print("{\\"status\\":\\"stdout\\"}")'],
                root / "missing.json",
            )
            self.assertEqual(payload["status"], "stdout")
            self.assertEqual(meta["returncode"], 0)
            output = root / "existing.json"
            output.write_text('{"status":"file"}')
            self.assertEqual(
                n.run_json([sys.executable, "-c", 'print("invalid JSON")'], output)[0][
                    "status"
                ],
                "file",
            )
            self.assertEqual(
                n.run_json([sys.executable, "-c", "raise SystemExit(9)"], output)[0], {}
            )
            packet = n.load_or_synthesize_source_record(None, CASE)
            self.assertEqual(packet["statement_nl"], "A fixed local identity")
            (root / "source.json").write_text("[1,2]")
            self.assertEqual(
                n.load_or_synthesize_source_record(root / "source.json", CASE),
                {"raw_source_record": [1, 2]},
            )
            prepared = n.prepare_run(
                "formalphysics_9999",
                None,
                root / "out",
                regenerate_initial_artifact=True,
            )
            self.assertEqual(prepared["initial_draft"]["status"], "blocked")
            self.assertEqual(
                n.pack_run_state(prepared)["blockers"][0]["code"],
                "initial_draft_generation_blocked",
            )

    def test_real_lunar_and_mcp(self):
        asyncio.run(self.runtime())

    async def runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = mount(Path(tmp) / "scratch")
            manager = SessionManager()
            async with manager.open(
                "sympy-source-only",
                StdioConfig(
                    command=str(ROOT / ".venv/bin/python"),
                    args=[
                        str(ROOT / "tests/mcp/fixtures/sympy_source_only_server.py"),
                        str(root),
                    ],
                    cwd=str(ROOT),
                ),
                {},
            ) as remote:
                failure = None
                try:
                    tools = [
                        t.model_dump(by_alias=True, exclude_none=True)
                        for t in await remote.tools()
                    ]

                    def compile(doc, inventory=None):
                        snapshot = assets(doc)
                        graph = compile_workflow(
                            "mcp:sympy-source-only",
                            workflow_documents([DESCRIPTOR], snapshot)[0],
                            tools if inventory is None else inventory,
                        )
                        return graph, snapshot

                    graph, snapshot = compile(self.doc)
                    self.assertTrue(graph["runnable"], graph["diagnostics"])
                    self.assertEqual(graph["runtime_status"], "ready")
                    self.assertTrue(graph["prism_source"])
                    self.assertTrue(graph["runtime_source"])
                    self.assertEqual(
                        set(graph["bindings"]), set(self.doc["operations"])
                    )
                    self.assertFalse(compile(self.doc, [])[0]["runnable"])
                    for name in self.doc["operations"]:
                        self.assertFalse(
                            compile(
                                self.doc,
                                [
                                    t
                                    for t in tools
                                    if t["name"]
                                    != self.doc["operations"][name]["execution"][
                                        "binding"
                                    ]["target"]
                                ],
                            )[0]["runnable"]
                        )
                    context = {"working_directory": str(root), "allow_mutating": True}

                    async def allow():
                        pass

                    async def run(request, doc=None, ctx=None):
                        g, a = compile(doc) if doc else (graph, snapshot)
                        self.assertTrue(g["runnable"], g["diagnostics"])
                        observed = Observed(remote)
                        result = await execute(
                            g,
                            a,
                            {"request": request, "context": ctx or context},
                            observed,
                            allow,
                        )
                        return result, observed

                    for mode, expected in [
                        ("complete", "complete_sympy_physics_derivation"),
                        ("partial", "blocked"),
                        ("blocked", "blocked"),
                        ("crash", "blocked"),
                    ]:
                        print("Native five-stage fixture: " + mode, flush=True)
                        shutil.rmtree(root / "out", ignore_errors=True)
                        req = input_case(root, mode)
                        result, observed = await run(req)
                        self.assertEqual(
                            result["status"], "accepted", str(result)[:3000]
                        )
                        payload = result["outputs"][OUTPUT_PORT]
                        self.assertEqual(payload["status"], expected)
                        self.assertEqual(len(result["calls"]), 9)
                        self.assertEqual(
                            [e[0] for e in observed.events],
                            [PREFIX + "prepare", PREFIX + "pack_state"]
                            + [PREFIX + "execute_stage"] * 5
                            + [PREFIX + "assess", PREFIX + "emit"],
                        )
                        stages = [
                            e[2]
                            for e in observed.events
                            if e[0] == PREFIX + "execute_stage"
                        ]
                        self.assertEqual(
                            [e["state"]["next_stage"] for e in stages], [1, 2, 3, 4, 5]
                        )
                        self.assertEqual(
                            [e["done"] for e in stages], [False] * 4 + [True]
                        )
                        self.assertEqual(
                            list(
                                json.loads(stages[-1]["state"]["_native_json"])[
                                    "command_metadata"
                                ]
                            ),
                            ORDER,
                        )
                        if mode == "complete":
                            history = [
                                json.loads(line)
                                for line in (
                                    root
                                    / "MathformerPhysicsLib/SymPy"
                                    / CASE
                                    / "MathformerPhysics.history.jsonl"
                                )
                                .read_text()
                                .splitlines()
                            ]
                            planner = load(
                                root
                                / SOURCE.replace(
                                    "run_recursive_goal_case.py",
                                    "plan_goal_sample_sympy_autoformalization.py",
                                ),
                                "history_constants",
                            )
                            self.assertEqual(
                                [e["name"] for e in history[:13]],
                                ["import", *planner.VALIDATOR_FUNCTIONS],
                            )
                            # Planner twice (direct + map), thoroughness once;
                            # the controller does not execute a repair/retry.
                            self.assertEqual(
                                sum(e["name"] == "run_all" for e in history), 3
                            )
                            for entry in history:
                                self.assertEqual(entry["history"][-1], entry["name"])
                        run_dir = root / "out" / CASE
                        self.assertEqual(
                            json.loads(
                                (run_dir / "recursive_goal_run.json").read_text()
                            ),
                            payload,
                        )
                        for original, alias in [
                            ("current_evidence.json", "goal_plan.json"),
                            ("repair_expansion.json", "repair_expansion_map.json"),
                            (
                                "controller_decision.json",
                                "recursive_repair_control.json",
                            ),
                            ("thoroughness.json", "grounded_sample_thoroughness.json"),
                            ("reasoning.jsonl", "reasoning_log.jsonl"),
                        ]:
                            if (run_dir / original).exists():
                                self.assertEqual(
                                    (run_dir / original).read_bytes(),
                                    (run_dir / alias).read_bytes(),
                                )
                        if mode != "crash":
                            controller = json.loads(
                                (run_dir / "controller_decision.json").read_text()
                            )
                            self.assertEqual(controller["iteration"], 1)
                            self.assertEqual(controller["max_iterations"], 6)
                        else:
                            self.assertNotEqual(
                                payload["command_metadata"]["recursive_repair_control"][
                                    "returncode"
                                ],
                                0,
                            )
                            self.assertEqual(
                                payload["workflow_stage_reports"][
                                    "recursive_repair_control"
                                ]["status"],
                                "command_failed",
                            )
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["replay_artifacts"])
                        if expected == "blocked":
                            self.assertTrue(payload["blockers"])
                        # Compare full result with the independent pre-extraction CLI.
                        stream = io.StringIO()
                        with redirect_stdout(stream):
                            native(root, True).main(
                                [
                                    "--case",
                                    CASE,
                                    "--source-record",
                                    str(root / "source.json"),
                                    "--output-root",
                                    str(root / "out"),
                                ]
                            )
                        left, right = (
                            stable(json.loads(stream.getvalue())),
                            stable(payload),
                        )
                        self.assertEqual(left, right)
                    # This is an input-state fixture for the final aggregator,
                    # not a substituted stage. Controller status alone is not a
                    # final blocker; only thoroughness and accumulated blockers
                    # select the final branch.
                    state = deepcopy(stages[-1]["state"])
                    state = json.loads(state["_native_json"])
                    state["blockers"] = []
                    (root / "out" / CASE / "controller_decision.json").write_text(
                        '{"status":"blocked"}'
                    )
                    for stage_status, final_status in [
                        (
                            "complete_sympy_physics_derivation",
                            "complete_sympy_physics_derivation",
                        ),
                        ("derivation_partial", "derivation_partial"),
                    ]:
                        state["workflow_stage_reports"]["grounded_sample_thoroughness"][
                            "status"
                        ] = stage_status
                        assessed = await remote.call(
                            PREFIX + "assess",
                            {"state": packed(state), "context": context},
                        )
                        self.assertFalse(assessed["assessment"]["blocked"])
                        emitted = await remote.call(
                            PREFIX + "emit",
                            {
                                "assessment": assessed["assessment"],
                                "status": final_status,
                                "context": context,
                            },
                        )
                        self.assertEqual(emitted["result"]["status"], final_status)
                        self.assertEqual(
                            emitted["result"]["status_summary"]["recursive_frontier"],
                            "blocked",
                        )
                        # A compiler input-state fixture reaches both final
                        # branches through PRISM, without substituting any
                        # operation or fabricating a subprocess report. Keep
                        # the actual files emitted by the preceding native run.
                        tail = deepcopy(self.doc)
                        tail["inputs"] = {
                            "state": {
                                "type": tail["operations"][ASSESS_OPERATION]["inputs"][
                                    "state"
                                ]["type"]
                            },
                            "context": tail["inputs"]["context"],
                        }
                        tail["flow"]["steps"] = tail["flow"]["steps"][3:]
                        tail["flow"]["steps"][0]["arguments"]["state"] = {
                            "ref": "inputs.state"
                        }
                        g, a = compile(tail)
                        self.assertTrue(g["runnable"], g["diagnostics"])
                        seen = Observed(remote)
                        selected = await execute(
                            g,
                            a,
                            {"state": packed(state), "context": context},
                            seen,
                            allow,
                        )
                        self.assertEqual(selected["status"], "accepted", selected)
                        self.assertEqual(
                            selected["outputs"][OUTPUT_PORT]["status"], final_status
                        )
                        self.assertEqual(
                            [e[0] for e in seen.events],
                            [PREFIX + "assess", PREFIX + "emit"],
                        )
                    req = input_case(root)
                    # Exhausting the compiler fixture's loop limit must stop before
                    # aggregation; normal source traversal completes on visit five.
                    for bound in (1, 4):
                        shutil.rmtree(root / "out", ignore_errors=True)
                        short = deepcopy(self.doc)
                        short["flow"]["steps"][2]["max_iterations"] = bound
                        result, seen = await run(req, short)
                        self.assertEqual(result["status"], "failed")
                        self.assertIsNone(result["outputs"])
                        self.assertEqual(result["failure_disposition"], "fail")
                        self.assertEqual(len(seen.events), 2 + bound)
                        self.assertFalse(
                            (root / "out" / CASE / "recursive_goal_run.json").exists()
                        )
                    budget = deepcopy(self.doc)
                    budget["policy"]["limits"]["max_operation_calls"] = 3
                    result, _ = await run(req, budget)
                    self.assertEqual(result["status"], "failed")
                    self.assertIn("budget", str(result).lower())
                    self.assertEqual(
                        sum(
                            bool(c.get("transport_call_performed"))
                            for c in result["calls"]
                        ),
                        3,
                    )
                    result, _ = await run(req, ctx={**context, "allow_mutating": False})
                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(len(result["calls"]), 1)
                    outside = {**req, "output_root": str(Path(tmp) / "outside")}
                    result, _ = await run(outside)
                    self.assertEqual(result["status"], "failed")
                    self.assertFalse((Path(tmp) / "outside").exists())
                    # JSON preparation error propagates and prevents all subprocesses.
                    (root / "source.json").write_text("{invalid")
                    result, seen = await run(req)
                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(len(result["calls"]), 1)
                    req = input_case(root)
                    # Actual filesystem failure at native report emission.
                    shutil.rmtree(root / "out", ignore_errors=True)
                    (root / "out" / CASE / "summary.md").mkdir(parents=True)
                    result, _ = await run(req)
                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(result["calls"][-1]["tool"], PREFIX + "emit")
                    self.assertTrue(
                        (root / "out" / CASE / "recursive_goal_run.json").exists()
                    )
                    # Transport integrity and native argv guards prevent forged calls.
                    init = await remote.call(
                        PREFIX + "prepare", {"request": req, "context": context}
                    )
                    prepared = init["prepared"]
                    prepared["case_id"] = "tampered"
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            PREFIX + "pack_state",
                            {"prepared": prepared, "context": context},
                        )
                    init = await remote.call(
                        PREFIX + "prepare", {"request": req, "context": context}
                    )
                    prepared = json.loads(init["prepared"]["_native_json"])
                    prepared["stage_specs"]["goal_plan"] = [
                        sys.executable,
                        "-c",
                        "raise SystemExit(0)",
                    ]
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            PREFIX + "pack_state",
                            {"prepared": packed(prepared), "context": context},
                        )
                except Exception as error:
                    failure = error
            self.assertFalse(manager.active)
            if failure:
                raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
