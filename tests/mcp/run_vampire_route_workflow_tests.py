#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Offline native route/leaf, registered MCP, Lunar and real PRISM integration.

Only external Vampire calls receive deterministic SZS/TSTP fixtures. Scientific
steps and native child Python processes execute unchanged in temporary mounts.
"""

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
    str(ROOT),
    str(ROOT / "scripts"),
    str(ROOT / "tests/mcp"),
    str(ROOT / "tests/mcp/fixtures"),
]
SITES = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
sys.path.extend(SITES)

import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import yaml

import mathformer as hub
from vampire_route_tools import (
    ACTION,
    ROUTE,
    selected_match,
    checked_registry,
    check_state,
)
from vampire_route_boundary import compiler
from backends.atp.MathformerATP import vampire as v
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_prove_vampire_atp_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
MATCH = {
    "route": {"route_id": ROUTE, "action_ids": [ACTION]},
    "score": 23,
    "matched_terms": ["vampire", "ATP"],
}
REGISTRY = {ACTION: hub.action_to_dict(hub.build_registry()[ACTION])}
ORDER = ["initialize", "select_action", "run_action", "advance", "finish"]
PREFIX = "mathformer_vampire_route_"
LEAF = "scripts/run_vampire_atp.py"
OUTPUT = "artifacts/vampire_atp/atp_function_demo"


def original():
    scope = dict(vars(hub))
    exec((ROOT / "tests/mcp/fixtures/vampire_route_original.py.txt").read_text(), scope)
    return SimpleNamespace(**scope)


def clean(value):
    if isinstance(value, dict):
        return {
            key: clean(item)
            for key, item in value.items()
            if key not in ("generated_at", "elapsed_seconds")
        }
    if isinstance(value, list):
        return [clean(item) for item in value]
    if isinstance(value, str):
        return re.sub(r"\d{4}-\d\d-\d\dT[0-9:.]+\+00:00", "<time>", value)
    return value


def ready(root):
    for path in [LEAF, "examples/vampire_group_inverse_product_input.md"]:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, target)


def snapshot(document):
    values = {
        row["path"]: (ROOT / row["path"]).read_text()
        for row in document["provenance"]["sources"]
    }
    values[SCHEMA] = (ROOT / SCHEMA).read_text()
    values[DESCRIPTOR] = json.dumps(document)
    return [
        dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )
        for path, text in values.items()
    ]


class VampireRouteTests(unittest.TestCase):
    maxDiff = None

    def test_contract_source_and_controller_states(self):
        document = yaml.safe_load(CONTRACT.read_text())
        spec = importlib.util.spec_from_file_location(
            "vampire_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)
        self.assertEqual(document, generator.vampire_route_descriptor())
        self.assertEqual(document["id"], "route_prove_vampire_atp_workflow")
        self.assertEqual(document["aliases"], [ROUTE])
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 5},
        )
        self.assertEqual(
            document["policy"]["failure"]["retry"],
            {"max_attempts": 1, "retryable_codes": []},
        )
        self.assertEqual(document["flow"]["steps"][1]["max_iterations"], 1)
        self.assertTrue(
            any(
                row["path"] == "scripts/mathformer.py"
                and row["selector"] == "run_intent_match"
                for row in document["provenance"]["sources"]
            )
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        native, match = checked_registry(REGISTRY), selected_match(MATCH)
        self.assertEqual(native[ACTION].timeout_seconds, 120)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for populated in [False, True]:
                if populated:
                    ready(root)
                for dry in [False, True]:
                    if populated and not dry:
                        continue  # complete leaf runs under compiler fixture below
                    for keep in [False, True]:
                        context = hub.RunContext(dry_run=dry, keep_going=keep)
                        self.assertEqual(
                            original().run_intent_match(
                                match, native, context, repository_root=root
                            ),
                            hub.run_intent_match(
                                match, native, context, repository_root=root
                            ),
                        )
        for keep in [False, True]:
            for child in [{"ok": True}, {"ok": False}, {}]:
                state = hub.initialize_intent_state()
                updated, done = hub.advance_intent_state(
                    state, child, hub.RunContext(keep_going=keep), 1
                )
                self.assertEqual(state, {"ok": True, "children": []})
                self.assertEqual(
                    updated, {"ok": bool(child.get("ok", False)), "children": [child]}
                )
                self.assertTrue(done)
                check_state(updated)
                with self.assertRaises(ValueError):
                    check_state(updated, selecting=True)
            # Shared helpers retain native sticky-failure behavior beyond this singleton specialization.
            state, done = hub.advance_intent_state(
                {"ok": False, "children": [{"ok": False}]},
                {"ok": True},
                hub.RunContext(keep_going=keep),
                3,
            )
            self.assertFalse(state["ok"])
            self.assertFalse(done)
        for state in [
            {"ok": False, "children": []},
            {"ok": True, "children": [{"ok": False}]},
        ]:
            with self.assertRaises(ValueError):
                check_state(state)
        changed = deepcopy(REGISTRY)
        changed[ACTION]["command"] = ["caller-command"]
        with self.assertRaises(ValueError):
            checked_registry(changed)
        changed = deepcopy(MATCH)
        changed["route"]["action_ids"].append(ACTION)
        with self.assertRaises(ValueError):
            selected_match(changed)

    def test_scientific_steps_candidates_and_empty_lists(self):
        # Built-in template generation has no external model boundary.
        for mode in ["success", "late", "unproved"]:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                output = root / OUTPUT
                (root / "fixture-mode").write_text(mode)
                with patch.object(
                    v, "subprocess", SimpleNamespace(run=compiler, PIPE=subprocess.PIPE)
                ):
                    steps = v.discover_proof_steps(
                        "Subset is transitive; subset of T",
                        artifact_root=output,
                        runner=v.VampireRunner(binary="fixture-vampire"),
                        premise_loop=True,
                        premise_budget="medium",
                        time_limit=3,
                    )
                    events = []
                    while True:
                        try:
                            events.append(next(steps))
                        except StopIteration as completed:
                            report = completed.value
                            break
                self.assertGreater(report["candidate_count"], 1)
                self.assertEqual(
                    report["attempt_count"],
                    (
                        1
                        if mode == "success"
                        else 2 if mode == "late" else report["candidate_count"]
                    ),
                )
                self.assertEqual(report["ok"], mode != "unproved")
                self.assertEqual(report["winner"] is not None, mode != "unproved")
                carried = [e for name, e in events if name == "carry_candidate"]
                self.assertEqual(
                    [e["attempt_count"] for e in carried],
                    list(range(1, len(carried) + 1)),
                )
                self.assertTrue(carried[-1]["done"])
                self.assertFalse(any(e["done"] for e in carried[:-1]))
                self.assertEqual(
                    json.loads((output / "discovery_report.json").read_text()), report
                )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            steps = v._minimize_premises_steps(
                problem=v.group_inverse_product_problem(),
                premises=[],
                artifact_root=output,
                runner=v.VampireRunner(binary="fixture-vampire"),
                time_limit=3,
                enabled=True,
            )
            self.assertEqual(next(steps), ("augment_pack", {"initial_ids": []}))
            self.assertEqual(next(steps), ("deletion_step", {"done": True}))
            with self.assertRaises(StopIteration) as finished:
                next(steps)
            self.assertEqual(finished.exception.value[:2], ([], []))
            self.assertEqual(list((output / "premise_minimization").iterdir()), [])
            empty = json.loads(
                (output / "premise_minimization_report.json").read_text()
            )
            self.assertEqual(
                (
                    empty["initial_premise_ids"],
                    empty["final_premise_ids"],
                    empty["attempts"],
                ),
                ([], [], []),
            )

    def test_outer_timeout_and_launch_error_at_external_compiler_boundary(self):
        # Direct compiler action to exercise the hub's native timeout conversion,
        # without replacing the registered route leaf or launching any executable.
        item = replace(
            hub.build_registry()[ACTION],
            command=("fixture-vampire", "problem.p"),
            required_paths=(),
        )
        for error in [
            subprocess.TimeoutExpired(
                item.command, 120, output="partial", stderr="deadline"
            ),
            OSError("launch failed"),
        ]:

            def boundary(command, **kwargs):
                self.assertEqual(command, list(item.command))
                self.assertEqual(kwargs["timeout"], 120)
                raise error

            with (
                tempfile.TemporaryDirectory() as directory,
                patch.object(
                    hub,
                    "subprocess",
                    SimpleNamespace(
                        run=boundary,
                        PIPE=subprocess.PIPE,
                        TimeoutExpired=subprocess.TimeoutExpired,
                    ),
                ),
            ):
                if isinstance(error, OSError):
                    with self.assertRaises(OSError):
                        hub.run_leaf_action(
                            item, hub.RunContext(), (), repository_root=Path(directory)
                        )
                else:
                    child = hub.run_leaf_action(
                        item, hub.RunContext(), (), repository_root=Path(directory)
                    )
                    self.assertFalse(child["ok"])
                    self.assertEqual(
                        (child["status"], child["stdout"], child["stderr"]),
                        ("timeout", "partial", "deadline"),
                    )
                    self.assertTrue(child["write_audit"]["ok"])

    def test_registered_tools_lunar_compile_and_prism_runtime(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(CONTRACT.read_text())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ready(root)
            manager = SessionManager()
            async with manager.open(
                "vampire-route",
                StdioConfig(
                    command=sys.executable,
                    args=[
                        str(ROOT / "tests/mcp/fixtures/vampire_route_boundary.py"),
                        str(root),
                    ],
                    cwd=str(ROOT),
                ),
                {"PYTHONPATH": os.pathsep.join(SITES), "PYTHONDONTWRITEBYTECODE": "1"},
            ) as remote:
                tools = [
                    tool.model_dump(by_alias=True, exclude_none=True)
                    for tool in await remote.tools()
                ]

                def compile_doc(doc, inventory=tools):
                    assets = snapshot(doc)
                    workflow = workflow_documents([DESCRIPTOR], assets)[0]
                    self.assertTrue(workflow["validation"]["valid"], workflow)
                    return (
                        compile_workflow("mcp:vampire-route", workflow, inventory),
                        assets,
                    )

                compiled, assets = compile_doc(document)
                self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                self.assertEqual(compiled["runtime_status"], "ready")
                self.assertTrue(compiled["prism_source"])
                self.assertTrue(compiled["runtime_source"])
                self.assertEqual(set(compiled["bindings"]), set(ORDER))
                missing = [
                    tool for tool in tools if tool["name"] != PREFIX + "run_action"
                ]
                self.assertFalse(compile_doc(document, missing)[0]["runnable"])

                async def authorize():
                    pass

                async def run(inputs, changed=None):
                    program, received = (
                        compile_doc(changed) if changed else (compiled, assets)
                    )
                    self.assertTrue(program["runnable"], program["diagnostics"])
                    return await execute(program, received, inputs, remote, authorize)

                base = {
                    "context": vars(hub.RunContext()),
                    "match": MATCH,
                    "registry": REGISTRY,
                    "repository_root": str(root),
                }
                scenarios = [
                    ("success", False, False),
                    ("success", False, True),
                    ("unproved", False, True),
                    ("write", False, False),
                    ("error", False, False),
                    ("launch_error", False, False),
                    ("timeout", False, False),
                    ("success", True, False),
                    ("preflight", False, False),
                ]
                for mode, dry, keep in scenarios:
                    with self.subTest(mode=mode, dry=dry, keep=keep):
                        output = root / OUTPUT
                        shutil.rmtree(output, ignore_errors=True)
                        (root / "undeclared.txt").unlink(missing_ok=True)
                        ready(root)
                        (root / "fixture-mode").write_text(mode)
                        if mode == "preflight":
                            (root / LEAF).unlink()
                        inputs = deepcopy(base)
                        inputs["context"].update(dry_run=dry, keep_going=keep)
                        result = await run(inputs)
                        self.assertEqual(result["status"], "accepted", result)
                        actual = result["outputs"]["result"]
                        self.assertEqual(actual["ok"], mode == "success")
                        self.assertEqual(len(actual["children"]), 1)
                        self.assertEqual(actual["route"]["score"], MATCH["score"])
                        self.assertEqual(
                            actual["route"]["matched_terms"], MATCH["matched_terms"]
                        )
                        self.assertEqual(
                            [call["operation"] for call in result["calls"]], ORDER
                        )
                        self.assertEqual(
                            [call["tool"] for call in result["calls"]],
                            [PREFIX + op for op in ORDER],
                        )
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["replay_artifacts"])
                        child = actual["children"][0]
                        self.assertEqual(
                            child["argv"],
                            hub.resolve_command(hub.build_registry()[ACTION].command),
                        )
                        if dry or mode == "preflight":
                            self.assertFalse(output.exists())
                        else:
                            self.assertEqual(
                                child["status"],
                                "undeclared_writes" if mode == "write" else "completed",
                            )
                            self.assertEqual(
                                child["write_audit"]["unexpected_paths"],
                                ["undeclared.txt"] if mode == "write" else [],
                            )
                            self.assertEqual(
                                child["returncode"],
                                (
                                    3
                                    if mode == "unproved"
                                    else (
                                        1
                                        if mode in ["error", "launch_error", "timeout"]
                                        else 0
                                    )
                                ),
                            )
                        if mode in ["success", "unproved"] and not dry:
                            report = json.loads(
                                (output / "discovery_report.json").read_text()
                            )
                            calls = [
                                json.loads(line)
                                for line in (output / "compiler.calls.jsonl")
                                .read_text()
                                .splitlines()
                            ]
                            attempt = report["attempts"][0]
                            generation = attempt["premise_generation_report"]
                            self.assertEqual(generation["generated_count"], 4)
                            self.assertEqual(generation["attempted_count"], 3)
                            self.assertEqual(generation["proved_count"], 2)
                            lemmas = generation["generated_lemmas"]
                            self.assertEqual(
                                sum(not lemma["attempt_proof"] for lemma in lemmas), 1
                            )
                            self.assertEqual(
                                [lemma["id"] for lemma in lemmas if lemma["promoted"]],
                                generation["promoted_ids"],
                            )
                            for lemma in lemmas:
                                if lemma["promoted"]:
                                    self.assertEqual(
                                        lemma["candidate"]["premise_type"],
                                        "proved_generated_lemma",
                                    )
                                    self.assertEqual(lemma["proof_status"], "Theorem")
                                    self.assertTrue(Path(lemma["proof_path"]).exists())
                                elif lemma["attempt_proof"]:
                                    self.assertEqual(
                                        lemma["candidate"]["premise_type"],
                                        "rejected_generated_lemma",
                                    )
                                    self.assertNotIn(
                                        lemma["candidate"]["id"],
                                        attempt["final_premise_ids"],
                                    )
                            minimized = json.loads(
                                Path(
                                    attempt["premise_minimization_report_path"]
                                ).read_text()
                            )
                            self.assertEqual(len(minimized["initial_premise_ids"]), 7)
                            self.assertEqual(
                                minimized["final_premise_ids"], ["left_identity"]
                            )
                            self.assertEqual(
                                attempt["final_premise_ids"],
                                minimized["final_premise_ids"],
                            )
                            self.assertEqual(report["ok"], mode == "success")
                            self.assertEqual(report["attempt_count"], 1)
                            self.assertEqual(
                                len(
                                    [
                                        c
                                        for c in calls
                                        if "/premise_generation/" in c["path"]
                                    ]
                                ),
                                3,
                            )
                            trials = attempt["premise_minimization_attempts"]
                            self.assertEqual(
                                len(trials),
                                len(
                                    [
                                        c
                                        for c in calls
                                        if "/premise_minimization/" in c["path"]
                                    ]
                                ),
                            )
                            self.assertTrue(
                                any(t["ok_without_premise"] for t in trials)
                            )
                            self.assertTrue(any(t["kept"] for t in trials))
                            for call in calls:
                                self.assertEqual(
                                    call["command"][
                                        call["command"].index("--time_limit") + 1
                                    ],
                                    (
                                        "1"
                                        if "/premise_minimization/" in call["path"]
                                        else "3"
                                    ),
                                )
                            # Original selected controller launches the same actual leaf, compiler fixture only.
                            shutil.rmtree(output)
                            environment = {
                                "PYTHONPATH": os.pathsep.join(
                                    [
                                        str(root / "compiler-bootstrap"),
                                        str(ROOT / "tests/mcp/fixtures"),
                                        str(ROOT / "scripts"),
                                        str(ROOT),
                                        *SITES,
                                    ]
                                ),
                                "PYTHONDONTWRITEBYTECODE": "1",
                            }
                            with patch.dict(os.environ, environment):
                                expected = original().run_intent_match(
                                    selected_match(MATCH),
                                    checked_registry(REGISTRY),
                                    hub.RunContext(**inputs["context"]),
                                    repository_root=root,
                                )
                            self.assertEqual(clean(actual), clean(expected))
                            self.assertEqual(
                                clean(report),
                                clean(
                                    json.loads(
                                        (output / "discovery_report.json").read_text()
                                    )
                                ),
                            )
                            expected_calls = [
                                json.loads(line)
                                for line in (output / "compiler.calls.jsonl")
                                .read_text()
                                .splitlines()
                            ]
                            self.assertEqual(clean(calls), clean(expected_calls))
                ready(root)
                (root / "fixture-mode").write_text("success")
                inputs = deepcopy(base)
                inputs["context"]["dry_run"] = True
                for keep in [False, True]:
                    carried = await remote.call(
                        PREFIX + "advance",
                        {
                            "state": {"ok": True, "children": []},
                            "child": {"ok": False, "stderr": "native failure"},
                            "context": vars(hub.RunContext(keep_going=keep)),
                        },
                    )
                    self.assertEqual(
                        carried,
                        {
                            "state": {
                                "ok": False,
                                "children": [{"ok": False, "stderr": "native failure"}],
                            },
                            "done": True,
                        },
                    )
                for budget in [1, 3, 4]:
                    changed = deepcopy(document)
                    changed["policy"]["limits"]["max_operation_calls"] = budget
                    result = await run(inputs, changed)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(
                        sum(
                            bool(c.get("transport_call_performed"))
                            for c in result["calls"]
                        ),
                        budget,
                    )
                changed = deepcopy(document)
                changed["flow"]["steps"][1]["until"] = {"literal": False}
                result = await run(inputs, changed)
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual([c["operation"] for c in result["calls"]], ORDER[:-1])
                self.assertIsNone(result["outputs"])
                bad = deepcopy(inputs)
                bad["registry"][ACTION]["command"] = ["caller-injected-command"]
                result = await run(bad)
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual([c["operation"] for c in result["calls"]], ORDER[:3])
                self.assertIsNone(result["outputs"])
                # No native execution for the default project mount: dry-run only.
                for omitted in [False, True]:
                    defaults = deepcopy(inputs)
                    if omitted:
                        defaults.pop("repository_root")
                    else:
                        defaults["repository_root"] = None
                    result = await run(defaults)
                    self.assertEqual(
                        result["outputs"],
                        {
                            "result": hub.run_intent_match(
                                selected_match(MATCH),
                                checked_registry(REGISTRY),
                                hub.RunContext(dry_run=True),
                            )
                        },
                    )
            self.assertFalse(manager.active)


if __name__ == "__main__":
    program = unittest.main(verbosity=2, exit=False)
    result = program.result
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
