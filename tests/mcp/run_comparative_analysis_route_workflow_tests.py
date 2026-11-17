#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402 - imports follow explicit interpreter and source-path setup
"""Offline native controller, registered MCP tools and real Lunar/PRISM runtime."""

from tempfile import gettempdir

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
SITES = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
PATHS = [
    str(ROOT / "scripts"),
    str(ROOT / "tests/mcp/fixtures"),
    str(LUNAR / "app/backend"),
    *SITES,
]
sys.path[:0] = PATHS

import asyncio
from copy import deepcopy
import hashlib
import importlib.util
import json
import tempfile
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import yaml

import mathformer as hub
from comparative_analysis_route_tools import (
    ACTIONS,
    ROUTE,
    SOURCE,
    checked_registry,
    selected_match,
)
from comparative_analysis_boundary import CODE, SMOKE, LeanCompiler, populate, put
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_report_formalphysics_comparative_analysis_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
PREFIX = "mathformer_comparative_analysis_"
REGISTRY = {key: hub.action_to_dict(hub.build_registry()[key]) for key in ACTIONS}
MATCH = {
    "route": {"route_id": ROUTE, "action_ids": list(ACTIONS)},
    "score": 19,
    "matched_terms": ["comparative", "report"],
}
OPS = ["initialize"] + ["select_action", "run_child", "advance"] * 2 + ["finish"]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def original():
    scope = dict(vars(hub))
    exec(
        (
            ROOT / "tests/mcp/fixtures/comparative_analysis_route_original.py.txt"
        ).read_text(),
        scope,
    )
    return scope["run_intent_match"]


def snapshot(document):
    values = {
        row["path"]: (ROOT / row["path"]).read_text()
        for row in document["provenance"]["sources"]
    }
    values[DESCRIPTOR] = json.dumps(document)
    values[SCHEMA] = (ROOT / SCHEMA).read_text()
    return [
        {
            "path": p,
            "content": t,
            "encoding": "text",
            "sha256": hashlib.sha256(t.encode()).hexdigest(),
        }
        for p, t in values.items()
    ]


class RouteTests(unittest.TestCase):
    maxDiff = None

    def test_contract_generator_and_capabilities(self):
        normalizer = load(
            "comparative_route_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        d = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(normalizer.comparative_analysis_route_descriptor(), d)
        self.assertEqual(d["lifecycle"], "active")
        self.assertEqual(d["aliases"], [ROUTE])
        self.assertEqual(
            d["policy"]["limits"], {"wall_time_seconds": 3600, "max_operation_calls": 8}
        )
        self.assertEqual(
            d["policy"]["failure"]["retry"], {"max_attempts": 1, "retryable_codes": []}
        )
        self.assertEqual(d["policy"]["resume"]["mode"], "none")
        self.assertEqual(d["flow"]["steps"][1]["max_iterations"], 2)
        self.assertEqual(d["flow"]["steps"][1]["on_exhausted"], "fail")
        self.assertEqual([REGISTRY[a]["timeout_seconds"] for a in ACTIONS], [180, 900])
        self.assertEqual(REGISTRY[ACTIONS[1]]["command"], ["{python}", SOURCE])
        self.assertEqual(
            checked_registry(REGISTRY), {a: hub.build_registry()[a] for a in ACTIONS}
        )
        self.assertTrue(
            any(
                row["path"] == "scripts/mathformer.py"
                and row["selector"] == "run_intent_match"
                for row in d["provenance"]["sources"]
            )
        )
        for row in d["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        bad = deepcopy(REGISTRY)
        bad[ACTIONS[0]]["command"] = ["arbitrary"]
        with self.assertRaisesRegex(ValueError, "registry"):
            checked_registry(bad)
        bad = deepcopy(MATCH)
        bad["route"]["action_ids"].reverse()
        with self.assertRaisesRegex(ValueError, "route"):
            selected_match(bad)

    def test_report_real_steps_compiler_and_imported_provider_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            populate(root, ROOT)
            native = load("comparative_report_fixture", root / SOURCE)
            records = [
                {
                    "FS_index": i,
                    "question": "Force identity for a charged particle.",
                    "answer": "A reference answer, never gold.",
                    "formaldiscovery_output": CODE,
                    "mathformerphysics_output": "obsolete",
                }
                for i in range(3)
            ]
            dataset = put(root, "records.json", json.dumps(records))
            judge = {
                "case_id": "formalphysics_0000",
                "candidate_id": "external_formaldiscovery",
                "judge_id": "lean_tp_judge",
                "fixture_decision": "inspect",
            }
            results = put(root, "judge-results.json", json.dumps({"results": [judge]}))
            args = native.parse_args(
                [
                    "--input-json",
                    str(dataset),
                    "--repo-root",
                    str(root),
                    "--lean-cwd",
                    str(root),
                    "--output-dir",
                    str(root / "out"),
                    "--codex-results-json",
                    str(results),
                ]
            )
            self.assertEqual(args.timeout, 60)
            # Production has no provider call or judge loop; all supplied results
            # are ingested by the actual evaluator. Default compile is skipped.
            with patch.object(
                native,
                "subprocess",
                SimpleNamespace(run=lambda *a, **k: self.fail("unexpected process")),
            ):
                skipped = native.build_report(args)
            self.assertEqual(skipped["summary"]["candidate_count"], 6)
            self.assertTrue(
                all(
                    c["lean_compile"]["status"] == "not_run"
                    for case in skipped["cases"]
                    for c in case["candidates"]
                )
            )
            args.execute_lean = True
            compiler = LeanCompiler(
                ["timeout", "fail", "pass", "pass", "pass", "pass"], root, 60
            )
            with patch.object(
                native,
                "subprocess",
                SimpleNamespace(
                    run=compiler.run, TimeoutExpired=subprocess.TimeoutExpired
                ),
            ):
                state = native.prepare_report(args)
                cursors = []
                while state["has_cases"]:
                    native.open_report_case(state)
                    while state["data"]["phase"] == "candidate":
                        cursors.append(
                            (
                                state["data"]["case_cursor"],
                                state["data"]["candidate_cursor"],
                            )
                        )
                        native.evaluate_report_candidate(state)
                    native.close_report_case(state)
                report = native.assemble_report(state)
            self.assertEqual(cursors, [(i, j) for i in range(3) for j in range(2)])
            self.assertEqual(state["data"]["case_cursor"], 3)
            self.assertEqual(len(compiler.calls), 6)
            self.assertEqual(
                [
                    c["lean_compile"]["status"]
                    for case in report["cases"]
                    for c in case["candidates"]
                ],
                ["timeout", "fail", "pass", "pass", "pass", "pass"],
            )
            self.assertEqual(
                report["cases"][0]["candidates"][0]["lean_compile"]["stdout"], "partial"
            )
            self.assertEqual(
                report["cases"][0]["candidates"][1]["lean_compile"]["error_count"], 1
            )
            self.assertEqual(report["summary"]["case_count"], 3)
            self.assertFalse(report["policy"]["reference_answer_is_gold"])
            self.assertEqual(len(report["codex_exec_judge_prompts"]), 48)
            completed = [
                p
                for p in report["codex_exec_judge_prompts"]
                if p["result_status"] == "completed"
            ]
            self.assertEqual(len(completed), 1)
            self.assertEqual(completed[0]["result"], judge)
            self.assertEqual(
                set(report["qualitative_reviews"]),
                {"theorem_prover_expert", "physics_expert"},
            )
            self.assertTrue(all("best_solution" in case for case in report["cases"]))
            paths = native.write_outputs(report, args.output_dir)
            self.assertEqual(json.loads(Path(paths["json"]).read_text()), report)
            self.assertIn("Lean Side By Side", Path(paths["html"]).read_text())
            self.assertTrue(all(Path(p).exists() for p in paths.values()))
            self.assertNotIn(
                "mathformerphysics_output",
                (args.output_dir / "selected_examples.cleaned.json").read_text(),
            )
            # Same shared source steps through the original build_report entrypoint.
            compiler = LeanCompiler(
                ["timeout", "fail", "pass", "pass", "pass", "pass"], root, 60
            )
            with patch.object(
                native,
                "subprocess",
                SimpleNamespace(
                    run=compiler.run, TimeoutExpired=subprocess.TimeoutExpired
                ),
            ):
                direct = native.build_report(args)
            # Timestamps and temporary Lean filenames are source-owned nondeterminism.
            for value in [direct, report]:
                value.pop("created_at")
                value["manifest"].pop("created_at")
                for case in value["cases"]:
                    for c in case["candidates"]:
                        c["lean_compile"].pop("command", None)
            self.assertEqual(direct, report)
            compiler = LeanCompiler(["crash"], root, 60)
            with patch.object(
                native,
                "subprocess",
                SimpleNamespace(
                    run=compiler.run, TimeoutExpired=subprocess.TimeoutExpired
                ),
            ):
                with self.assertRaisesRegex(OSError, "compiler fixture launch failed"):
                    native.build_report(args)
            self.assertEqual(compiler.calls, ["crash"])
            dataset.write_text("[]")
            with patch.object(
                native,
                "subprocess",
                SimpleNamespace(
                    run=lambda *a, **k: self.fail("empty traversal compiled")
                ),
            ):
                empty = native.build_report(args)
            self.assertEqual(empty["cases"], [])
            self.assertEqual(empty["codex_exec_judge_prompts"], [])
            self.assertEqual(empty["summary"]["candidate_count"], 0)
            dataset.write_text("{}")
            with self.assertRaisesRegex(ValueError, "must contain a list"):
                native.build_report(args)

    def test_registered_mcp_lunar_prism_runtime(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        d = yaml.safe_load(CONTRACT.read_text())
        with tempfile.TemporaryDirectory(prefix="comparative-route-") as directory:
            root = Path(directory).resolve()
            populate(root, ROOT)
            manager = SessionManager()
            # Imports registrations only; main/config/credentials are never used.
            startup = (
                "from comparative_analysis_boundary import serve;serve("
                + repr(str(root))
                + ")"
            )
            failure = None
            async with manager.open(
                "comparative-route",
                StdioConfig(
                    command=sys.executable, args=["-c", startup], cwd=str(ROOT)
                ),
                {"PYTHONPATH": os.pathsep.join(PATHS), "PYTHONDONTWRITEBYTECODE": "1"},
            ) as remote:
                try:
                    tools = [
                        t.model_dump(by_alias=True, exclude_none=True)
                        for t in await remote.tools()
                    ]

                    def compile(document, inventory=tools):
                        assets = snapshot(document)
                        record = workflow_documents([DESCRIPTOR], assets)[0]
                        self.assertTrue(record["validation"]["valid"], record)
                        return (
                            compile_workflow(
                                "mcp:comparative-route", record, inventory
                            ),
                            assets,
                        )

                    compiled, assets = compile(d)
                    self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                    self.assertEqual(compiled["runtime_status"], "ready")
                    self.assertTrue(compiled["runtime_source"])
                    self.assertTrue(compiled["prism_source"])
                    self.assertEqual(set(compiled["bindings"]), set(d["operations"]))
                    self.assertFalse(
                        compile(
                            d, [t for t in tools if t["name"] != PREFIX + "run_child"]
                        )[0]["runnable"]
                    )
                    advertised = {t["name"]: t for t in tools}
                    for op in d["operations"].values():
                        binding = op["execution"]["binding"]
                        self.assertEqual(binding["target"], binding["operation"])
                        interface = advertised[binding["target"]]
                        self.assertEqual(
                            set(interface["inputSchema"]["properties"]),
                            set(op["inputs"]),
                        )
                        self.assertEqual(
                            set(interface["outputSchema"]["properties"]),
                            set(op["outputs"]),
                        )

                    async def authorize():
                        pass

                    async def run(values, changed=None):
                        c, a = (
                            compile(changed)
                            if changed is not None
                            else (compiled, assets)
                        )
                        self.assertTrue(c["runnable"], c["diagnostics"])
                        return await execute(c, a, values, remote, authorize)

                    inputs = dict(
                        match=MATCH,
                        context=vars(hub.RunContext()),
                        registry=REGISTRY,
                        repository_root=str(root),
                    )
                    for mode in [
                        "native",
                        "dry",
                        "missing_smoke",
                        "missing_foundations",
                    ]:
                        smoke = root / SMOKE
                        foundations = (
                            root
                            / "libraries/MathformerPhysicsLib/Lean/Foundations.lean"
                        )
                        removed = (
                            smoke
                            if mode == "missing_smoke"
                            else foundations if mode == "missing_foundations" else None
                        )
                        content = removed.read_text() if removed else None
                        if removed:
                            removed.unlink()
                        try:
                            for keep in [False, True]:
                                values = deepcopy(inputs)
                                values["context"].update(
                                    keep_going=keep, dry_run=mode == "dry"
                                )
                                result = await run(values)
                                self.assertEqual(result["status"], "accepted", result)
                                expected = original()(
                                    selected_match(MATCH),
                                    checked_registry(REGISTRY),
                                    hub.RunContext(**values["context"]),
                                    repository_root=root,
                                )
                                # The smoke summary includes its random TemporaryDirectory.
                                # Compare every field after normalizing that one path.
                                observed = deepcopy(result["outputs"])
                                for value in [observed["result"], expected]:
                                    for child in value["children"]:
                                        if child.get("returncode") == 0 and child.get(
                                            "stdout"
                                        ):
                                            payload = json.loads(child["stdout"])
                                            payload["summary"][
                                                "judge_synthesis_path"
                                            ] = "<temporary synthesis fixture>"
                                            child["stdout"] = json.dumps(
                                                payload, sort_keys=True
                                            )
                                self.assertEqual(observed, {"result": expected})
                                got = result["outputs"]["result"]
                                count = 1 if mode == "missing_smoke" and not keep else 2
                                self.assertEqual(len(got["children"]), count)
                                self.assertEqual(
                                    [c["operation"] for c in result["calls"]],
                                    OPS if count == 2 else OPS[:4] + ["finish"],
                                )
                                self.assertEqual(got["ok"], mode == "dry")
                                if mode == "native":
                                    self.assertTrue(got["children"][0]["ok"])
                                    self.assertTrue(
                                        json.loads(got["children"][0]["stdout"])["ok"]
                                    )
                                    self.assertEqual(
                                        got["children"][1]["returncode"], 1
                                    )
                                    self.assertIn(
                                        "--input-json is required",
                                        got["children"][1]["stderr"],
                                    )
                                    self.assertTrue(
                                        got["children"][1]["write_audit"]["ok"]
                                    )
                                if mode == "missing_smoke":
                                    self.assertTrue(
                                        got["children"][0]["preflight_errors"]
                                    )
                                    self.assertNotIn("returncode", got["children"][0])
                                    if keep:
                                        self.assertEqual(
                                            got["children"][1]["returncode"], 1
                                        )
                                self.assertTrue(result["runtime"]["effect_records"])
                                self.assertTrue(result["runtime"]["provenance"])
                                self.assertTrue(result["replay_artifacts"])
                        finally:
                            if removed:
                                put(root, str(removed.relative_to(root)), content)
                    values = deepcopy(inputs)
                    values["context"]["dry_run"] = True
                    short = deepcopy(d)
                    short["flow"]["steps"][1]["max_iterations"] = 1
                    exhausted = await run(values, short)
                    self.assertEqual(exhausted["status"], "failed", exhausted)
                    self.assertIsNone(exhausted["outputs"])
                    self.assertEqual(
                        [c["operation"] for c in exhausted["calls"]], OPS[:4]
                    )
                    self.assertIn("exhaust", str(exhausted).lower())
                    budget = deepcopy(d)
                    budget["policy"]["limits"]["max_operation_calls"] = 4
                    failed = await run(values, budget)
                    self.assertEqual(failed["status"], "failed")
                    self.assertIsNone(failed["outputs"])
                    self.assertEqual(
                        sum(
                            bool(c.get("transport_call_performed"))
                            for c in failed["calls"]
                        ),
                        4,
                    )
                    values["registry"][ACTIONS[0]]["timeout_seconds"] = 1
                    failed = await run(values)
                    self.assertEqual(failed["status"], "failed")
                    self.assertIsNone(failed["outputs"])
                    self.assertEqual([c["operation"] for c in failed["calls"]], OPS[:3])
                    # Finish retains native KeyError when route metadata is absent.
                    values["registry"] = {}
                    failed = await run(values)
                    self.assertEqual(failed["status"], "failed")
                    self.assertEqual(failed["calls"][-1]["operation"], "finish")
                    with self.assertRaises(KeyError):
                        original()(
                            selected_match(MATCH),
                            {},
                            hub.RunContext(),
                            repository_root=root,
                        )
                    # Caller histories remain immutable and a subsequent success never
                    # clears failure; invalid cursors reject at the real MCP boundary.
                    context = vars(hub.RunContext(dry_run=True, keep_going=True))
                    state = (await remote.call(PREFIX + "initialize", {}))["state"]
                    child = (
                        await remote.call(
                            PREFIX + "run_child",
                            dict(
                                action=ACTIONS[0],
                                context=context,
                                registry={},
                                repository_root=str(root),
                            ),
                        )
                    )["child"]
                    first = await remote.call(
                        PREFIX + "advance",
                        dict(state=state, child=child, context=context, action_count=2),
                    )
                    self.assertFalse(first["done"])
                    good = (
                        await remote.call(
                            PREFIX + "run_child",
                            dict(
                                action=ACTIONS[1],
                                context=context,
                                registry=REGISTRY,
                                repository_root=str(root),
                            ),
                        )
                    )["child"]
                    final = await remote.call(
                        PREFIX + "advance",
                        dict(
                            state=first["state"],
                            child=good,
                            context=context,
                            action_count=2,
                        ),
                    )
                    self.assertTrue(final["done"])
                    self.assertFalse(final["state"]["ok"])
                    self.assertTrue(good["ok"])
                    self.assertEqual(final["state"]["children"], [child, good])
                    self.assertEqual(state, {"ok": True, "children": []})
                    with self.assertRaises(Exception):
                        await remote.call(
                            PREFIX + "select_action",
                            dict(state=final["state"], match=MATCH),
                        )
                except Exception as error:
                    failure = error
            self.assertFalse(manager.active)
            if failure is not None:
                raise failure
        # Service restrictions apply on the production registration too.
        import mcp_server as server

        args = dict(
            action=ACTIONS[0],
            context=vars(hub.RunContext()),
            registry=REGISTRY,
            repository_root=str(Path(gettempdir())),
        )
        with patch.object(server, "_READONLY", True):
            with self.assertRaisesRegex(Exception, "read-only"):
                await server.mcp.call_tool(PREFIX + "run_child", args)
        with patch.object(
            server, "_ALLOWED_WRITE_ROOTS", [Path(str(Path(gettempdir()) / "denied"))]
        ):
            with self.assertRaisesRegex(Exception, "service roots"):
                await server.mcp.call_tool(PREFIX + "run_child", args)


if __name__ == "__main__":
    program = unittest.main(verbosity=2, exit=False)
    result = program.result
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
