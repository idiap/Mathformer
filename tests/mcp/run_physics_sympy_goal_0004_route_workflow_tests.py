#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Explicit-contract offline native/MCP/Lunar/PRISM route integration tests."""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT / "tests/mcp/fixtures"),
    str(ROOT / "tests/mcp"),
    str(ROOT),
]
SITES = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
sys.path.extend(SITES)
os.environ["PYTHONPATH"] = os.pathsep.join(SITES)

import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import yaml
from mcp.server.fastmcp import FastMCP
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute
import mathformer as hub
from physics_sympy_goal_0004_route_tools import (
    ACTIONS,
    TIMEOUTS,
    ROUTE,
    WRITES,
    selected_match,
    checked_registry,
    ARTIFACT,
    check_state,
    register_physics_sympy_goal_0004_route_tools,
)
from physics_sympy_goal_0004_route_tree import populate
from physics_sympy_goal_0004_compiler import install as compiler_fixture
from run_sympy_source_only_workflow_tests import load, stable, Observed, ORDER as STAGES

ID = "route_formalize_physics_sympy_goal_sample_0004_workflow"
BASE = "skills/control/workflow-contract-validator/references/"
DESCRIPTOR = BASE + "normalized-workflows/route/" + ID + "/workflow.yaml"
SCHEMA = BASE + "normalized-workflows/hub-interface.schema.json"
AUTHORED = ROOT / BASE / "physics-sympy-goal-0004-route.workflow.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
MATCH = {
    "score": 19,
    "matched_terms": ["physics", "sympy", "0004"],
    "route": {"route_id": ROUTE, "action_ids": list(ACTIONS)},
}
REGISTRY = {key: hub.action_to_dict(hub.build_registry()[key]) for key in ACTIONS}
PREFIX = "mathformer_sympy_goal_0004_route_"
ORDER = ["initialize", "select", "run", "advance", "finish"]


def original():
    scope = dict(vars(hub))
    exec(
        (
            ROOT / "tests/mcp/fixtures/physics_sympy_goal_0004_route_original.py.txt"
        ).read_text(),
        scope,
    )
    return SimpleNamespace(**scope)


def snapshot(document):
    texts = {
        row["path"]: (ROOT / row["path"]).read_text()
        for row in document["provenance"]["sources"]
    }
    texts.update(
        {SCHEMA: (ROOT / SCHEMA).read_text(), DESCRIPTOR: json.dumps(document)}
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


def normalized(value):
    # Process output is a source-owned JSON string. Compare its contents while
    # ignoring only clocks and per-call log identities, never statuses/data.
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if key == "generated_at":
                continue
            if key == "stdout":
                try:
                    item = json.loads(item)
                except (TypeError, json.JSONDecodeError):
                    pass
            result[key] = normalized(item)
        return stable(result)
    if isinstance(value, list):
        return [normalized(v) for v in value]
    return stable(value)


def delta(left, right, path="result"):
    """Report small field differences without dumping captured source reports."""
    if isinstance(left, dict) and isinstance(right, dict):
        if set(left) != set(right):
            return [f"{path}: keys differ {set(left) ^ set(right)}"]
        return [
            difference
            for key in left
            for difference in delta(left[key], right[key], path + "." + key)
        ]
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return [f"{path}: length {len(left)} != {len(right)}"]
        return [
            difference
            for i, (a, b) in enumerate(zip(left, right))
            for difference in delta(a, b, f"{path}[{i}]")
        ]
    return (
        []
        if left == right
        else [f"{path}: {str(left)[:150]!r} != {str(right)[:150]!r}"]
    )


class SympyGoalRouteTests(unittest.TestCase):
    maxDiff = None

    def test_contract_generator_and_native_identity(self):
        document = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(document, json.loads(AUTHORED.read_text()))
        normalizer = load(
            ROOT / BASE / "../scripts/normalize_workflows.py", "sympy_goal_normalizer"
        )
        self.assertEqual(
            normalizer.physics_sympy_goal_0004_route_descriptor(), document
        )
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(document["aliases"], [ROUTE])
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 29},
        )
        self.assertEqual(
            document["policy"]["failure"]["retry"],
            {"max_attempts": 1, "retryable_codes": []},
        )
        self.assertEqual(document["policy"]["resume"]["mode"], "none")
        self.assertEqual(document["flow"]["steps"][1]["max_iterations"], 9)
        self.assertEqual(document["flow"]["steps"][1]["on_exhausted"], "fail")
        self.assertTrue(
            any(
                r["path"] == "scripts/mathformer.py"
                and r["selector"] == "run_intent_match"
                for r in document["provenance"]["sources"]
            )
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        self.assertEqual(
            tuple(checked_registry(REGISTRY)[k].timeout_seconds for k in ACTIONS),
            TIMEOUTS,
        )
        self.assertEqual(tuple(selected_match(MATCH).route.action_ids), ACTIONS)

    def test_native_history_stopping_and_source_equivalence(self):
        oracle, match = original(), selected_match(MATCH)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for keep in (False, True):
                context = hub.RunContext(keep_going=keep)
                result = hub.run_intent_match(
                    match, checked_registry(REGISTRY), context, repository_root=root
                )
                self.assertEqual(
                    result,
                    oracle.run_intent_match(
                        match, checked_registry(REGISTRY), context, repository_root=root
                    ),
                )
                self.assertFalse(result["ok"])
                self.assertEqual(len(result["children"]), 9 if keep else 1)
        for failure_at in (None, 0, 4, 8):
            for keep in (False, True):
                context = vars(hub.RunContext(keep_going=keep))
                initial = hub.initialize_intent_state()
                state = initial
                for index in range(9):
                    self.assertEqual(
                        hub.select_intent_action(state, match), ACTIONS[index]
                    )
                    previous = deepcopy(state)
                    child = {"ok": index != failure_at, "action_id": ACTIONS[index]}
                    state, done = hub.advance_intent_state(
                        state, child, hub.RunContext(**context), 9
                    )
                    self.assertEqual(previous["children"] + [child], state["children"])
                    self.assertEqual(initial, {"ok": True, "children": []})
                    self.assertEqual(
                        state["ok"], failure_at is None or index < failure_at
                    )
                    check_state(state, context)
                    if done:
                        self.assertEqual(
                            index,
                            failure_at if failure_at is not None and not keep else 8,
                        )
                        break
                check_state(state, context, finishing=True)
                with self.assertRaisesRegex(ValueError, "bounds|stopped"):
                    check_state(state, context, selecting=True)
        with self.assertRaisesRegex(ValueError, "unconsumed"):
            check_state(initial, context, finishing=True)
        forged = {"ok": True, "children": [{"ok": False, "action_id": ACTIONS[0]}]}
        with self.assertRaisesRegex(ValueError, "accumulator"):
            check_state(forged, context)
        with self.assertRaisesRegex(ValueError, "projection"):
            checked_registry(
                {ACTIONS[0]: {**REGISTRY[ACTIONS[0]], "command": ["injected"]}}
            )

    def test_actual_regeneration_nested_stages_and_status_guards(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = populate(Path(tmp) / "scratch", ROOT)
            command = hub.build_registry()[ACTIONS[0]].command
            self.assertIn("--regenerate-initial-artifact", command)
            native = load(root / command[1], "scratch_runner")
            prepared = native.prepare_run(
                "formalphysics_0004",
                root
                / "artifacts/physics_sympy/source_only/formalphysics_0004/source_record.json",
                root / "out",
                regenerate_initial_artifact=True,
            )
            self.assertTrue(prepared["initial_draft"]["regenerate_requested"])
            self.assertTrue(prepared["initial_draft"]["generated"])
            self.assertEqual(prepared["stage_order"], STAGES)
            commands = prepared["stage_specs"]
            self.assertIn("--run-gates", commands["goal_plan"])
            self.assertIn(
                str(root / "out/formalphysics_0004/design_guard_review.json"),
                commands["repair_expansion_map"],
            )
            self.assertIn(
                str(root / "out/formalphysics_0004/repair_expansion.json"),
                commands["recursive_repair_control"],
            )
            state = native.pack_run_state(prepared)
            self.assertFalse(state["blockers"])
            for index in range(5):
                self.assertEqual(native.execute_run_stage(state), index == 4)
                self.assertEqual(state["next_stage"], index + 1)
                self.assertEqual(list(state["command_metadata"]), STAGES[: index + 1])
            before = deepcopy(state)
            with self.assertRaisesRegex(ValueError, "exhausted"):
                native.execute_run_stage(state)
            self.assertEqual(state, before)
            assessment = native.assess_run(state)
            status = (
                "complete_sympy_physics_derivation"
                if assessment["complete"]
                else "blocked" if assessment["blocked"] else "derivation_partial"
            )
            self.assertEqual(status, "complete_sympy_physics_derivation")
            self.assertFalse(state["blockers"])
            report = native.emit_run(assessment, status)
            self.assertEqual(list(report["command_metadata"]), STAGES)
            self.assertTrue((root / "out/formalphysics_0004/reasoning.jsonl").exists())
            self.assertNotIn("Sentinel input", (root / ARTIFACT).read_text())
            # Explicit source assessment states cover the final guards
            # independently of which scientific findings the writer emits.
            for thoroughness, blockers, expected in [
                ("complete_sympy_physics_derivation", [], (True, False)),
                ("derivation_partial", [], (False, False)),
                (
                    "complete_sympy_physics_derivation",
                    [{"code": "recorded"}],
                    (False, True),
                ),
            ]:
                observed = deepcopy(state)
                observed["workflow_stage_reports"]["grounded_sample_thoroughness"][
                    "status"
                ] = thoroughness
                observed["blockers"] = blockers
                assessed = native.assess_run(observed)
                self.assertEqual((assessed["complete"], assessed["blocked"]), expected)

    def test_external_compiler_capture_timeout_and_error(self):
        # This schedule has no provider/compiler calls. Exercise the shared
        # native executor's actual compiler boundary separately, never simulate
        # a production route action or replace PRISM parsing/compilation.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            boundary = SimpleNamespace()
            calls = compiler_fixture(boundary, root)
            for mode in ("accept", "reject", "timeout", "launch_error", "write"):
                item = replace(
                    hub.build_registry()[ACTIONS[1]],
                    command=("fixture-physics-compiler", mode),
                    timeout_seconds=300,
                    required_paths=(),
                )
                with patch.object(hub, "subprocess", boundary.subprocess):
                    if mode == "launch_error":
                        with self.assertRaisesRegex(OSError, "launch failed"):
                            hub.run_leaf_action(
                                item, hub.RunContext(), (), repository_root=root
                            )
                        continue
                    result = hub.run_leaf_action(
                        item, hub.RunContext(), (), repository_root=root
                    )
                self.assertEqual(result["ok"], mode == "accept")
                self.assertEqual(
                    result["status"],
                    (
                        "timeout"
                        if mode == "timeout"
                        else "undeclared_writes" if mode == "write" else "completed"
                    ),
                )
                if mode == "timeout":
                    self.assertIsNone(result["returncode"])
                    self.assertEqual(result["stdout"], "partial")
                    self.assertEqual(result["timeout_seconds"], 300)
                if mode == "reject":
                    self.assertEqual(result["returncode"], 7)
                    self.assertEqual(
                        json.loads(result["stdout"])["diagnostics"][0]["code"],
                        "fixture_type_error",
                    )
                if mode == "write":
                    self.assertEqual(result["returncode"], 0)
                    self.assertFalse(result["write_audit"]["ok"])
            self.assertEqual([row["timeout"] for row in calls], [300] * 5)
            self.assertTrue(all(row["source"]["kind"] == "equality" for row in calls))

    def test_service_policy_and_ports(self):
        async def checks():
            enabled = {"write": False, "paths": True}

            def authorize():
                if not enabled["write"]:
                    raise PermissionError("read-only service")

            server = FastMCP("sympy-route-authority")
            register_physics_sympy_goal_0004_route_tools(
                server, authorize, lambda p: enabled["paths"]
            )
            with tempfile.TemporaryDirectory() as tmp:
                args = dict(
                    action_id=ACTIONS[0],
                    context=vars(hub.RunContext()),
                    registry=REGISTRY,
                    repository_root=tmp,
                )
                for write, paths, error in [
                    (False, True, "read-only"),
                    (True, False, "service roots"),
                ]:
                    enabled.update(write=write, paths=paths)
                    with self.assertRaisesRegex(Exception, error):
                        await server.call_tool(PREFIX + "run", args)
                invalid = deepcopy(MATCH)
                invalid["route"]["action_ids"].reverse()
                with self.assertRaisesRegex(Exception, "native declaration"):
                    await server.call_tool(
                        PREFIX + "select",
                        dict(
                            state=hub.initialize_intent_state(),
                            match=invalid,
                            context=args["context"],
                        ),
                    )
                args["context"]["dry_run"] = True
                await server.call_tool(PREFIX + "run", args)
                args["registry"] = {}
                self.assertEqual(
                    (await server.call_tool(PREFIX + "run", args))[1]["child"][
                        "status"
                    ],
                    "unknown_action",
                )
                with self.assertRaisesRegex(Exception, "9"):
                    await server.call_tool(
                        PREFIX + "advance",
                        dict(
                            state=hub.initialize_intent_state(),
                            child={"action_id": ACTIONS[0], "ok": True},
                            context=args["context"],
                            action_count=6,
                        ),
                    )

        asyncio.run(checks())

    def test_registered_tools_lunar_compiler_and_prism_runtime(self):
        asyncio.run(self.connected())

    async def connected(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve()
            server = (
                "import sys;sys.dont_write_bytecode=True;sys.path[:0]="
                + repr(
                    [
                        str(ROOT / "scripts"),
                        str(ROOT / "tests/mcp/fixtures"),
                        str(ROOT),
                        *SITES,
                    ]
                )
                + ";from physics_sympy_goal_0004_route_tree import serve;serve("
                + repr(str(base))
                + ")"
            )
            manager, failure = SessionManager(), None
            async with manager.open(
                "sympy-goal-route",
                StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
                {"PYTHONPATH": os.pathsep.join(SITES), "PYTHONDONTWRITEBYTECODE": "1"},
            ) as remote:
                try:
                    await self.connected_checks(base, Observed(remote))
                except Exception as error:
                    failure = error
            self.assertFalse(manager.active)
            if failure:
                raise failure

    async def connected_checks(self, base, remote):
        doc = yaml.safe_load(CONTRACT.read_text())
        tools = [
            t.model_dump(by_alias=True, exclude_none=True) for t in await remote.tools()
        ]

        def compile(document, inventory=None):
            assets = snapshot(document)
            workflow = workflow_documents([DESCRIPTOR], assets)[0]
            self.assertTrue(workflow["validation"]["valid"], workflow)
            graph = compile_workflow(
                "mcp:sympy-goal-route",
                workflow,
                tools if inventory is None else inventory,
            )
            return graph, assets

        compiled, assets = compile(doc)
        self.assertTrue(compiled["runnable"], compiled["diagnostics"])
        self.assertEqual(compiled["runtime_status"], "ready")
        self.assertEqual(set(compiled["bindings"]), set(ORDER))
        self.assertTrue(compiled["prism_source"])
        self.assertTrue(compiled["runtime_source"])
        self.assertFalse(
            compile(doc, [t for t in tools if t["name"] != PREFIX + "advance"])[0][
                "runnable"
            ]
        )
        self.assertTrue(
            all(
                op["execution"]["binding"]["target"] in {t["name"] for t in tools}
                for op in doc["operations"].values()
            )
        )

        async def authorize():
            pass

        async def run(root, *, dry=False, keep=False, document=None, registry=None):
            graph, received = (
                compile(document) if document is not None else (compiled, assets)
            )
            self.assertTrue(graph["runnable"], graph["diagnostics"])
            inputs = dict(
                context=vars(hub.RunContext(dry_run=dry, keep_going=keep)),
                match=MATCH,
                registry=REGISTRY if registry is None else registry,
                repository_root=str(root),
            )
            remote.events.clear()
            result = await execute(graph, received, inputs, remote, authorize)
            return result, inputs

        # Admission failures are native data. Dry-run traverses the same 9 items.
        missing = base / "missing"
        missing.mkdir()
        for keep in (False, True):
            result, inputs = await run(missing, keep=keep)
            self.assertEqual(result["status"], "accepted", result)
            self.assertEqual(
                result["outputs"]["result"],
                original().run_intent_match(
                    selected_match(MATCH),
                    checked_registry(REGISTRY),
                    hub.RunContext(**inputs["context"]),
                    repository_root=missing,
                ),
            )
            self.assertEqual(
                len(result["outputs"]["result"]["children"]), 9 if keep else 1
            )
        root = populate(base / "dry", ROOT)
        result, inputs = await run(root, dry=True)
        self.assertEqual(result["status"], "accepted", result)
        self.assertTrue(result["outputs"]["result"]["ok"])
        self.assertEqual(len(result["calls"]), 29)
        self.assertEqual(
            [c["operation"] for c in result["calls"]],
            ["initialize"] + ["select", "run", "advance"] * 9 + ["finish"],
        )
        self.assertEqual(
            result["outputs"]["result"],
            original().run_intent_match(
                selected_match(MATCH),
                checked_registry(REGISTRY),
                hub.RunContext(**inputs["context"]),
                repository_root=root,
            ),
        )
        self.assertFalse((root / WRITES).exists())
        for missing_writer, keep in [
            (False, False),
            (False, True),
            (True, False),
            (True, True),
        ]:
            with self.subTest(missing_writer=missing_writer, keep=keep):
                root = populate(
                    base / f"writer-{missing_writer}-{keep}",
                    ROOT,
                    missing_writer=missing_writer,
                )
                result, inputs = await run(root, keep=keep)
                self.assertEqual(result["status"], "accepted", result)
                output = result["outputs"]["result"]
                self.assertEqual(output["route"]["score"], MATCH["score"])
                self.assertEqual(
                    output["route"]["matched_terms"], MATCH["matched_terms"]
                )
                children = output["children"]
                self.assertEqual(
                    [c.get("action", {}).get("id") for c in children],
                    list(ACTIONS[: len(children)]),
                )
                self.assertEqual(output["ok"], all(c["ok"] for c in children))
                self.assertEqual(
                    output["status"],
                    "intent_run_completed" if output["ok"] else "intent_run_failed",
                )
                self.assertEqual(len(result["calls"]), 2 + 3 * len(children))
                self.assertEqual(
                    len(children),
                    (
                        9
                        if keep
                        else next(
                            (i + 1 for i, c in enumerate(children) if not c["ok"]), 9
                        )
                    ),
                )
                runner = json.loads(
                    (root / WRITES / "recursive_goal_run.json").read_text()
                )
                initial = json.loads((root / WRITES / "initial_draft.json").read_text())
                self.assertTrue(initial["regenerate_requested"])
                self.assertEqual(initial["generated"], not missing_writer)
                self.assertEqual(list(runner["command_metadata"]), STAGES)
                self.assertEqual(
                    children[0]["returncode"], 3 if runner["status"] == "blocked" else 0
                )
                if missing_writer:
                    self.assertEqual(runner["status"], "blocked")
                    self.assertEqual(
                        runner["blockers"][0]["code"],
                        "initial_draft_generation_blocked",
                    )
                    self.assertFalse(output["ok"])
                    self.assertEqual(len(children), 9 if keep else 1)
                else:
                    self.assertTrue(output["ok"])
                    self.assertEqual(len(children), 9)
                    self.assertEqual(
                        runner["status"], "complete_sympy_physics_derivation"
                    )
                    self.assertNotIn("Sentinel input", (root / ARTIFACT).read_text())
                if keep:
                    packet = json.loads(children[6]["stdout"])
                    self.assertEqual(
                        packet["style"], "physics_sympy_cross_backend_semantic_packet"
                    )
                    if not missing_writer:
                        self.assertTrue(packet["semantic_parity"]["semantic_parity"])
                    self.assertEqual(
                        len(json.loads(children[7]["stdout"])["results"]), 8
                    )
                    self.assertEqual(
                        json.loads(children[8]["stdout"])["ok"], not missing_writer
                    )
                advances = [
                    event for event in remote.events if event[0] == PREFIX + "advance"
                ]
                for index, (_, arguments, returned) in enumerate(advances):
                    self.assertEqual(arguments["state"]["children"], children[:index])
                    self.assertEqual(
                        returned["state"]["children"], children[: index + 1]
                    )
                    self.assertEqual(returned["done"], index == len(children) - 1)
                self.assertTrue(result["runtime"]["effect_records"])
                self.assertTrue(result["runtime"]["provenance"])
                self.assertTrue(result["replay_artifacts"])
                # Recreate the same input filesystem before the oracle so
                # native write-audit observations compare like for like.
                shutil.rmtree(root / WRITES)
                (root / ARTIFACT).write_text(
                    "# Sentinel input: native regeneration must replace this.\n"
                )
                expected = original().run_intent_match(
                    selected_match(MATCH),
                    checked_registry(REGISTRY),
                    hub.RunContext(**inputs["context"]),
                    repository_root=root,
                )
                differences = delta(normalized(output), normalized(expected))
                self.assertFalse(differences, differences[:12])
        # A late preflight failure stops after seven actions or remains sticky
        # through all nine, using actual source admission (no action substitution).
        root = populate(base / "late-failure", ROOT)
        (
            root
            / "libraries/MathformerPhysicsLib/Lean/formalphysics_0004/MathformerPhysics.lean"
        ).unlink()
        for keep in (False, True):
            result, _ = await run(root, dry=True, keep=keep)
            self.assertEqual(result["status"], "accepted", result)
            output = result["outputs"]["result"]
            self.assertFalse(output["ok"])
            self.assertEqual(len(output["children"]), 9 if keep else 7)
            self.assertFalse(output["children"][6]["ok"])
        ledger = [
            json.loads(line)
            for line in (base / "commands.jsonl").read_text().splitlines()
        ]
        self.assertTrue(all(r["timeout"] in TIMEOUTS for r in ledger))
        self.assertTrue(
            any(
                r["timeout"] == 900 and "--regenerate-initial-artifact" in r["command"]
                for r in ledger
            )
        )
        # Exhaustion fails before finish; the genuine ninth done exits normally.
        for bound in (1, 8):
            changed = deepcopy(doc)
            changed["flow"]["steps"][1]["max_iterations"] = bound
            result, _ = await run(base / "dry", dry=True, document=changed)
            self.assertEqual(result["status"], "failed", result)
            self.assertIsNone(result["outputs"])
            self.assertEqual(result["failure_disposition"], "fail")
            self.assertEqual(
                sum(c["operation"] == "advance" for c in result["calls"]), bound
            )
            self.assertFalse(any(c["operation"] == "finish" for c in result["calls"]))
        changed = deepcopy(doc)
        changed["policy"]["limits"]["max_operation_calls"] = 4
        result, _ = await run(base / "dry", dry=True, document=changed)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(
            sum(bool(c.get("transport_call_performed")) for c in result["calls"]), 4
        )
        changed = deepcopy(doc)
        changed["flow"]["steps"][1]["body"]["steps"][0]["arguments"]["state"] = {
            "literal": {"ok": True, "children": [{"ok": True, "action_id": ACTIONS[1]}]}
        }
        result, _ = await run(base / "dry", dry=True, document=changed)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["calls"][-1]["operation"], "select")
        forged = deepcopy(REGISTRY)
        forged[ACTIONS[0]]["command"] = ["injected"]
        result, _ = await run(base / "dry", dry=True, registry=forged)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["calls"][-1]["operation"], "run")
        result, _ = await run(base / "dry", dry=True, registry={})
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["calls"][-1]["operation"], "finish")
        # A genuine launch error is propagated as graph failure, with no retry.
        root = populate(base / "launch-error", ROOT)
        (root / ".venv/bin/python").unlink()
        result, _ = await run(root)
        self.assertEqual(result["status"], "failed", result)
        self.assertIsNone(result["outputs"])
        self.assertEqual(
            [c["operation"] for c in result["calls"]], ["initialize", "select", "run"]
        )
        with self.assertRaises(OSError):
            original().run_intent_match(
                selected_match(MATCH),
                checked_registry(REGISTRY),
                hub.RunContext(),
                repository_root=root,
            )


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(SympyGoalRouteTests)
    )
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
