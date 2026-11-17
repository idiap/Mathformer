#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native premise route, real MCP, Lunar compiler, PRISM checker and runtime.

No external provider/compiler exists in this route. No production execution or
promotion is performed. Real KB population/query steps use temporary data; the
full leaf is launched only in an incomplete mount where init must fail. Generic
compiler-boundary fixtures separately verify native process capture and audits.
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
    str(ROOT / "scripts"),
    str(ROOT / "tests/mcp/fixtures"),
]
SITES = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
sys.path.extend(SITES)

import asyncio
from contextlib import redirect_stdout
from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib.util
import io
import json
import shutil
import tempfile
from types import SimpleNamespace
import unittest
import yaml

import mathformer as hub
from premise_selection_route_tools import (
    ACTION,
    ROUTE,
    selected_match,
    checked_registry,
    check_state,
)
from reasoning_route_compiler import install
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_kb_premise_selection_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
MATCH = {
    "route": {"route_id": ROUTE, "action_ids": [ACTION]},
    "score": 19,
    "matched_terms": ["premise", "selection"],
}
REGISTRY = {ACTION: hub.action_to_dict(hub.build_registry()[ACTION])}
ORDER = ["initialize", "select", "execute", "advance", "finish"]
LEAF = "tests/kb/run_premise_kb_e2e.py"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def original():
    scope = dict(vars(hub))
    exec(
        (
            ROOT / "tests/mcp/fixtures/premise_selection_route_original.py.txt"
        ).read_text(),
        scope,
    )
    return SimpleNamespace(**scope)


def ready(root):
    path = root / LEAF
    path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / LEAF, path)
    (root / "backends/premise_kb/MathformerKB").mkdir(parents=True, exist_ok=True)


def snapshot(document):
    values = {
        row["path"]: (ROOT / row["path"]).read_text()
        for row in document["provenance"]["sources"]
    }
    values[SCHEMA] = (ROOT / SCHEMA).read_text()
    values[DESCRIPTOR] = json.dumps(document)
    return [
        {
            "path": path,
            "content": content,
            "encoding": "text",
            "sha256": hashlib.sha256(content.encode()).hexdigest(),
        }
        for path, content in values.items()
    ]


class PremiseSelectionTests(unittest.TestCase):
    maxDiff = None

    def test_contract_generator_and_source_semantics(self):
        document = yaml.safe_load(CONTRACT.read_text())
        generator = load(
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
            "premise_normalizer",
        )
        self.assertEqual(generator.premise_selection_route_descriptor(), document)
        self.assertEqual(document["id"], "route_kb_premise_selection_workflow")
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
        native, match = checked_registry(REGISTRY), selected_match(MATCH)
        self.assertIsNone(native[ACTION].timeout_seconds)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for populated in [False, True]:
                if populated:
                    ready(root)
                for dry in [False, True]:
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
            # Native shared helper retains sticky failure across longer routes.
            state, done = hub.advance_intent_state(
                {"ok": False, "children": [{"ok": False}]},
                {"ok": True},
                hub.RunContext(keep_going=keep),
                3,
            )
            self.assertFalse(done)
            self.assertFalse(state["ok"])
            self.assertEqual(len(state["children"]), 2)
        with self.assertRaises(ValueError):
            check_state({"ok": False, "children": []})
        changed = deepcopy(REGISTRY)
        changed[ACTION]["command"] = ["unregistered-executable"]
        with self.assertRaises(ValueError):
            checked_registry(changed)
        changed = deepcopy(MATCH)
        changed["route"]["action_ids"].append(ACTION)
        with self.assertRaises(ValueError):
            selected_match(changed)

    def test_actual_leaf_population_and_query_without_promotion(self):
        native = load(ROOT / LEAF, "premise_leaf_fixture")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            kb = root / "kb"
            kb.mkdir()
            (kb / "stale").write_text("old")
            reports = root / "reports"
            # More than 12 source records verifies the real ingestion limit.
            for index in range(15):
                path = reports / str(index) / "discovery_report.json"
                path.parent.mkdir(parents=True)
                path.write_text(
                    json.dumps(
                        {
                            "informal_statement": f"Isolated candidate {index}",
                            "winner": {
                                "formulas": [
                                    {"role": "conjecture", "formula": f"p{index}(a)"}
                                ]
                            },
                        }
                    )
                )
            state = native.prepare(
                {"kb_root": str(kb), "artifact_root": str(reports), "json": True}
            )
            self.assertFalse(kb.exists())
            populated = native.populate(state)
            self.assertEqual(state["responses"], {})
            self.assertEqual(
                list(populated["responses"]),
                ["init", "seeds", "vampire", "bloom", "embeddings"],
            )
            self.assertTrue(populated["responses"]["init"]["ok"])
            self.assertGreaterEqual(populated["responses"]["seeds"]["entry_count"], 8)
            self.assertEqual(populated["responses"]["vampire"]["candidate_count"], 12)
            index = Path(populated["responses"]["embeddings"]["embedding_index"])
            self.assertEqual(json.loads(index.read_text())["dimension"], 256)
            queried = native.query(populated)
            self.assertEqual(len(populated["responses"]), 5)
            self.assertEqual(
                list(queried["responses"])[5:],
                ["membership", "absent", "search", "distance"],
            )
            responses = queried["responses"]
            self.assertTrue(responses["membership"]["membership"]["probably_present"])
            self.assertFalse(responses["absent"]["membership"]["probably_present"])
            self.assertLessEqual(len(responses["search"]["hits"]), 5)
            self.assertTrue(responses["search"]["hits"])
            self.assertTrue(
                all("cosine_distance" in hit for hit in responses["search"]["hits"])
            )
            self.assertTrue(
                0 <= responses["distance"]["distance"]["cosine_distance"] <= 1
            )
            # Malformed data must stop populate at ingestion, before indexes.
            bad = reports / "0/discovery_report.json"
            bad.write_text("{invalid JSON")
            failed = native.prepare(
                {"kb_root": str(root / "failed"), "artifact_root": str(reports)}
            )
            with self.assertRaises(RuntimeError):
                native.populate(failed)
            self.assertEqual(failed["responses"], {})
            self.assertFalse((root / "failed/embeddings/index.json").exists())
            for ok in [False, True]:
                for json_output in [False, True]:
                    payload = {"ok": ok, "kb_root": str(kb), "top_hit_ids": ["fixture"]}
                    stream = io.StringIO()
                    with redirect_stdout(stream):
                        emitted = native.emit(payload, {"json": json_output})
                    self.assertEqual(emitted["exit_code"], 0 if ok else 3)
                    self.assertEqual(emitted["stdout"], stream.getvalue())
                    if json_output:
                        self.assertEqual(json.loads(stream.getvalue()), payload)
            # Read storage directly: population/query never curates an entry.
            events = [
                json.loads(line)
                for line in (kb / "curation_log.jsonl").read_text().splitlines()
            ]
            self.assertTrue(events)
            self.assertEqual({event["action"] for event in events}, {"add_entry"})
            self.assertEqual((kb / "rejected.jsonl").read_text(), "")

    def test_generic_external_compiler_fixture(self):
        # A separate compiler action, never a simulated implementation of kb:e2e.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            saved = hub.subprocess
            try:
                for mode in ["success", "reject", "write", "launch_error", "timeout"]:
                    item = replace(
                        hub.build_registry()[ACTION],
                        command=("fixture-reasoning-compiler", mode),
                        required_paths=(),
                        timeout_seconds=3 if mode == "timeout" else None,
                    )
                    calls = install(hub, root)
                    if mode == "launch_error":
                        with self.assertRaises(OSError):
                            hub.run_leaf_action(
                                item, hub.RunContext(), (), repository_root=root
                            )
                    else:
                        child = hub.run_leaf_action(
                            item, hub.RunContext(), (), repository_root=root
                        )
                        self.assertEqual(child["ok"], mode == "success")
                        if mode == "write":
                            self.assertEqual(
                                child["write_audit"]["unexpected_paths"],
                                ["undeclared.txt"],
                            )
                            self.assertEqual(child["status"], "undeclared_writes")
                        elif mode == "reject":
                            self.assertEqual(child["returncode"], 7)
                        elif mode == "timeout":
                            self.assertEqual(
                                (child["status"], child["stdout"], child["stderr"]),
                                ("timeout", "partial", "deadline"),
                            )
                        else:
                            self.assertEqual(
                                json.loads(child["stdout"])["artifact"]["nodes"],
                                ["input", "check"],
                            )
                            self.assertFalse(json.loads(child["stdout"])["ok"])
                    self.assertEqual(
                        calls,
                        [{"argv": list(item.command), "timeout": item.timeout_seconds}],
                    )
                    (root / "undeclared.txt").unlink(missing_ok=True)
            finally:
                hub.subprocess = saved

    def test_registered_mcp_lunar_prism_execution(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        async with manager.open(
            "premise-route",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {"PYTHONPATH": os.pathsep.join(SITES), "PYTHONDONTWRITEBYTECODE": "1"},
        ) as remote:
            document = yaml.safe_load(CONTRACT.read_text())
            tools = [
                t.model_dump(by_alias=True, exclude_none=True)
                for t in await remote.tools()
            ]

            def compile_doc(doc, inventory=tools):
                assets = snapshot(doc)
                selected = workflow_documents([DESCRIPTOR], assets)[0]
                self.assertTrue(selected["validation"]["valid"], selected)
                return (
                    compile_workflow("mcp:premise-route", selected, inventory),
                    assets,
                )

            compiled, assets = compile_doc(document)
            self.assertTrue(compiled["runnable"], compiled["diagnostics"])
            self.assertEqual(compiled["runtime_status"], "ready")
            self.assertTrue(compiled["prism_source"])
            self.assertTrue(compiled["runtime_source"])
            self.assertEqual(set(compiled["bindings"]), set(ORDER))
            missing = [
                t
                for t in tools
                if t["name"] != "mathformer_premise_selection_route_execute"
            ]
            self.assertFalse(compile_doc(document, missing)[0]["runnable"])

            async def authorize():
                pass

            async def run(inputs, changed=None):
                selected, received = (
                    compile_doc(changed) if changed else (compiled, assets)
                )
                self.assertTrue(selected["runnable"], selected["diagnostics"])
                return await execute(selected, received, inputs, remote, authorize)

            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                base = {
                    "context": vars(hub.RunContext()),
                    "match": MATCH,
                    "registry": REGISTRY,
                    "repository_root": str(root),
                }
                for populated in [False, True]:
                    if populated:
                        ready(root)
                    for dry in [False, True]:
                        for keep in [False, True]:
                            inputs = deepcopy(base)
                            inputs["context"].update(dry_run=dry, keep_going=keep)
                            before = hub.snapshot_repository(root)
                            result = await run(inputs)
                            self.assertEqual(result["status"], "accepted", result)
                            actual = result["outputs"]["result"]
                            expected = original().run_intent_match(
                                selected_match(MATCH),
                                checked_registry(REGISTRY),
                                hub.RunContext(**inputs["context"]),
                                repository_root=root,
                            )
                            self.assertEqual(actual, expected)
                            self.assertEqual(actual["ok"], populated and dry)
                            self.assertEqual(len(actual["children"]), 1)
                            self.assertEqual(actual["route"]["score"], MATCH["score"])
                            self.assertEqual(
                                actual["route"]["matched_terms"], MATCH["matched_terms"]
                            )
                            self.assertEqual(
                                [c["operation"] for c in result["calls"]], ORDER
                            )
                            self.assertEqual(
                                [c["tool"] for c in result["calls"]],
                                [
                                    "mathformer_premise_selection_route_" + op
                                    for op in ORDER
                                ],
                            )
                            self.assertEqual(hub.snapshot_repository(root), before)
                            if populated and not dry:
                                child = actual["children"][0]
                                self.assertEqual(
                                    child["argv"], [sys.executable, LEAF, "--json"]
                                )
                                self.assertEqual(child["returncode"], 1)
                                self.assertIn("command failed:", child["stderr"])
                                self.assertTrue(child["write_audit"]["ok"])
                                self.assertEqual(
                                    child["write_audit"]["unexpected_paths"], []
                                )
                            self.assertTrue(result["runtime"]["effect_records"])
                            self.assertTrue(result["runtime"]["provenance"])
                            self.assertTrue(result["replay_artifacts"])
                # Failure data remains data and is finalized on both keep-going paths.
                for keep in [False, True]:
                    advanced = await remote.call(
                        "mathformer_premise_selection_route_advance",
                        {
                            "state": {"ok": True, "children": []},
                            "child": {"ok": False, "stdout": "diagnostic"},
                            "context": vars(hub.RunContext(keep_going=keep)),
                        },
                    )
                    self.assertEqual(
                        advanced,
                        {
                            "state": {
                                "ok": False,
                                "children": [{"ok": False, "stdout": "diagnostic"}],
                            },
                            "done": True,
                        },
                    )
                inputs = deepcopy(base)
                inputs["context"]["dry_run"] = True
                for limit in [1, 3, 4]:
                    changed = deepcopy(document)
                    changed["policy"]["limits"]["max_operation_calls"] = limit
                    result = await run(inputs, changed)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(
                        sum(
                            bool(c.get("transport_call_performed"))
                            for c in result["calls"]
                        ),
                        limit,
                    )
                changed = deepcopy(document)
                changed["flow"]["steps"][1]["until"] = {"literal": False}
                result = await run(inputs, changed)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual([c["operation"] for c in result["calls"]], ORDER[:-1])
                # Adapter exceptions propagate; no route completion or retry occurs.
                changed_inputs = deepcopy(inputs)
                changed_inputs["registry"][ACTION]["command"] = [
                    "unregistered-executable"
                ]
                result = await run(changed_inputs)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual([c["operation"] for c in result["calls"]], ORDER[:3])
                # Optional mount uses native defaults; only dry-run against project.
                for omitted in [False, True]:
                    inputs["repository_root"] = None
                    if omitted:
                        inputs.pop("repository_root")
                    result = await run(inputs)
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
                timed = deepcopy(document)
                timed["policy"]["limits"]["wall_time_seconds"] = 1
                selected, received = compile_doc(timed)

                async def pending():
                    await asyncio.Event().wait()

                with self.assertRaises(TimeoutError):
                    await execute(selected, received, inputs, remote, pending)
        self.assertFalse(manager.active)


if __name__ == "__main__":
    program = unittest.main(verbosity=2, exit=False)
    result = program.result
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
