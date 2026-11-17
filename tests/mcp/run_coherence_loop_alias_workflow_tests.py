#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Fixture-only native coherence steps through registered MCP and real PRISM.

This source has no model/provider or external compiler calls: it scans Lean text
and plans advisory probes. Filesystem fixtures need no substituted boundaries.
Lunar's parser, checker, compiler, bindings and runtime all execute unchanged.
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
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import json
import tempfile
import unittest
import yaml

from coherence_loop_tools import source
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_physics_lib_coherence_loop_report_workflow/workflow.yaml"
AUTHORED = (
    ROOT
    / "skills/control/workflow-contract-validator/references/coherence-loop-alias.workflow.json"
)


def assets(document):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(s["path"], (ROOT / s["path"]).read_text())
        for s in document["provenance"]["sources"]
    ]


def original():
    source()  # Resolve shared imports from the production module's real location.
    loader = SourceFileLoader(
        "coherence_loop_selected_original",
        str(ROOT / "tests/mcp/fixtures/coherence_loop_selected_original.py.txt"),
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def fixture(root, status="blocked"):
    lean = root / "MathformerPhysicsLib/Lean"
    lean.mkdir(parents=True)
    if status == "blocked":
        (lean / "formalphysics_vector.lean").write_text(
            "import Mathlib\ndef vector : Nat := 1\n"
        )
        (lean / "Other.lean").write_text("import Mathlib\ndef vector : Nat := 2\n")
    else:
        (lean / "formalphysics_fixture.lean").write_text(
            "import Mathlib\ndef datum : Nat := 1\n"
        )
        (lean / "Foundations.lean").write_text("-- fixture integration index\n")
        if status == "accepted":
            (lean.parent / "MANIFEST.json").write_text(
                json.dumps({"backends": {"Lean": {"foundations": {}}}})
            )
    return lean


def reset_previous(output, text):
    output.mkdir(exist_ok=True)
    path = output / "mathlib_grounding.json"
    if text is None:
        path.unlink(missing_ok=True)
    else:
        path.write_text(text)


def contents(output):
    return {p.name: p.read_bytes() for p in output.iterdir() if p.is_file()}


class CoherenceLoopAliasTests(unittest.TestCase):
    def test_native_generator_preserves_authored_alias(self):
        path = (
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py"
        )
        spec = importlib.util.spec_from_file_location(
            "coherence_alias_normalizer", path
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        descriptors = module.inventory()  # Registry inspection only; no execution.
        selected = [
            d
            for d in descriptors
            if d["id"] == "hub_physics_lib_coherence_loop_report_workflow"
        ]
        self.assertEqual(selected, [json.loads(AUTHORED.read_text())])

    def test_shared_native_entrypoint_equivalence(self):
        native, before = source(), original()
        # The oracle is the selected execution source backup, before this pass.
        for status in ("blocked", "warn", "accepted"):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                lean = fixture(root, status)
                output = root / "out"
                for prior in (None, "{", "[]", "{}", '{"concepts":[null,{}]}'):
                    reset_previous(output, prior)
                    expected = before.run_loop(output, root)
                    expected_files = contents(output)
                    reset_previous(output, prior)
                    actual = native.run_loop(output, root)
                    self.assertEqual(actual, expected)
                    self.assertEqual(contents(output), expected_files)
                    self.assertTrue(actual["ok"])
                    self.assertEqual(actual["gate_status"], status)
                    self.assertEqual(actual["generative_probe_count"], 7)
                    self.assertEqual(len(actual["checks"]), 6)
                    self.assertEqual(len(expected_files), 10)
                for path in lean.iterdir():
                    path.unlink()
                result = native.run_loop(output, root)
                self.assertFalse(result["ok"])
                self.assertEqual(
                    [c["id"] for c in result["checks"] if not c["ok"]],
                    ["inventory.scans_lean_modules", "top10_cases_included"],
                )
                self.assertEqual(len(contents(output)), 10)

    def test_registered_tools_and_lunar_runtime(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(
            document["id"], "hub_physics_lib_coherence_loop_report_workflow"
        )
        self.assertEqual(document["aliases"], ["physics-lib:coherence-loop-report"])
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(document, json.loads(AUTHORED.read_text()))
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 9},
        )
        self.assertIn(
            "tests/physics_lean/run_mathformerphysicslib_coherence_loop.py",
            [s["path"] for s in document["provenance"]["sources"]],
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )

        manager = SessionManager()
        # Import the actual production server registrations; do not launch the
        # credential/configuration service or invoke unrelated registered tools.
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            lean = fixture(root)
            output = root / "out"
            async with manager.open(
                "coherence-loop-alias",
                StdioConfig(
                    command=str(ROOT / ".venv/bin/python"),
                    args=["-c", server],
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

                    def compile(doc, advertised=None):
                        received = assets(doc)
                        bound = compile_workflow(
                            "mcp:coherence-loop-alias",
                            workflow_documents([DESCRIPTOR], received)[0],
                            tools if advertised is None else advertised,
                        )
                        return bound, received

                    workflow, received = compile(document)
                    self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                    self.assertTrue(workflow["runtime_source"])
                    self.assertEqual(
                        set(workflow["bindings"]), set(document["operations"])
                    )
                    self.assertFalse(compile(document, [])[0]["runnable"])
                    missing = deepcopy(document)
                    missing["operations"]["inventory"]["execution"]["binding"][
                        "target"
                    ] = "missing_inventory"
                    missing["operations"]["inventory"]["execution"]["binding"][
                        "operation"
                    ] = "missing_inventory"
                    self.assertFalse(compile(missing)[0]["runnable"])

                    async def allow():
                        pass

                    async def run(doc=None, destination=output, repository=root):
                        bound, snapshot = compile(doc) if doc else (workflow, received)
                        self.assertTrue(bound["runnable"], bound["diagnostics"])
                        return await execute(
                            bound,
                            snapshot,
                            {
                                "output_dir": str(destination),
                                "repository_root": str(repository),
                            },
                            remote,
                            allow,
                        )

                    # Every operation is a real callable; prior state is read
                    # before replacement, even when it records a regression.
                    prior_regressed = json.dumps(
                        {
                            "concepts": [
                                {
                                    "concept_id": "vector_field.real.euclidean3",
                                    "grounding_level": "direct_mathlib",
                                }
                            ]
                        }
                    )
                    for prior in (
                        None,
                        "{",
                        "[]",
                        "{}",
                        '{"concepts":[null,{}]}',
                        prior_regressed,
                    ):
                        reset_previous(output, prior)
                        result = await run()
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertEqual(
                            [c["tool"] for c in result["calls"]],
                            [
                                document["operations"][s["operation"]]["execution"][
                                    "binding"
                                ]["target"]
                                for s in document["flow"]["steps"]
                            ],
                        )
                        self.assertEqual(len(result["calls"]), 9)
                        self.assertTrue(result["outputs"]["result"]["ok"])
                        self.assertEqual(
                            result["outputs"]["result"]["gate_status"], "blocked"
                        )
                        self.assertEqual(
                            result["outputs"]["artifacts"],
                            result["outputs"]["result"]["artifacts"],
                        )
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["replay_artifacts"])
                        written = contents(output)
                        grounding = json.loads(written["mathlib_grounding.json"])
                        self.assertEqual(
                            grounding["monotonic_comparison"]["status"],
                            (
                                "regressed"
                                if prior == prior_regressed
                                else "no_previous_report"
                            ),
                        )
                        self.assertEqual(len(written), 10)
                        reset_previous(output, prior)
                        expected = original().run_loop(output, root)
                        self.assertEqual(
                            result["outputs"],
                            {"result": expected, "artifacts": expected["artifacts"]},
                        )
                        self.assertEqual(contents(output), written)
                    result = await run()
                    self.assertEqual(
                        json.loads((output / "mathlib_grounding.json").read_text())[
                            "monotonic_comparison"
                        ]["status"],
                        "monotonic",
                    )
                    self.assertEqual(
                        sorted(p.name for p in lean.iterdir()),
                        ["Other.lean", "formalphysics_vector.lean"],
                    )

                    # The real plans/critics expose all findings and actions;
                    # low and unknown severities do not prevent acceptance.
                    for findings, status in (
                        ([], "accepted"),
                        (
                            [{"severity": "medium", "kind": "thin_foundation_api"}],
                            "warn",
                        ),
                        (
                            [
                                {
                                    "severity": "high",
                                    "kind": "confirmed_competing_concept_owner",
                                }
                            ],
                            "blocked",
                        ),
                    ):
                        reports = [{"findings": findings}, {}, {}, {}]
                        plans = (
                            await remote.call(
                                "mathformer_coherence_loop_plan_and_gate",
                                {"reports": reports},
                            )
                        )["plans"]
                        self.assertEqual(plans, source().plan_and_gate(reports))
                        self.assertEqual(plans["gate"]["status"], status)
                        self.assertEqual(plans["generative"]["probe_count"], 7)
                        self.assertEqual(
                            plans["repairs"]["action_count"], len(findings)
                        )
                    kinds = [
                        "concept_spread_without_foundation_owner",
                        "confirmed_competing_concept_owner",
                        "manifest_missing_foundations",
                        "missing_foundations_index",
                        "foundation_owner_not_indexed",
                        "foundation_without_operable_api",
                        "thin_foundation_api",
                        "unknown",
                    ]
                    reports = [
                        {"findings": [{"kind": k, "severity": "low"} for k in kinds]}
                    ] * 4
                    plans = (
                        await remote.call(
                            "mathformer_coherence_loop_plan_and_gate",
                            {"reports": reports},
                        )
                    )["plans"]
                    actions = (
                        ["consolidate_concept_owner"] * 2
                        + ["repair_integration_surface"] * 3
                        + ["add_operable_bridge_api"] * 2
                        + ["record_or_block_gap"]
                    )
                    self.assertEqual(
                        [a["action"] for a in plans["repairs"]["actions"]], actions * 4
                    )
                    self.assertEqual(plans["gate"]["status"], "accepted")
                    self.assertEqual(plans["gate"]["repair_action_count"], 32)

                    levels = [
                        "unverified_local",
                        "local_blocker",
                        "mathlib_bridge",
                        "direct_mathlib",
                        "unknown",
                    ]
                    prior = {
                        "concepts": [
                            {"concept_id": str(i), "grounding_level": level}
                            for i, level in enumerate(levels)
                        ]
                        + [
                            {
                                "concept_id": "removed",
                                "grounding_level": "direct_mathlib",
                            }
                        ]
                    }
                    current = {
                        "concepts": [
                            {"concept_id": str(i), "grounding_level": level}
                            for i, level in enumerate(reversed(levels))
                        ]
                        + [{"concept_id": "added", "grounding_level": "unknown"}]
                    }
                    reset_previous(output, json.dumps(prior))
                    compared = (
                        await remote.call(
                            "mathformer_coherence_loop_compare_previous",
                            {"directory": str(output), "grounding": current},
                        )
                    )["grounding"]
                    self.assertEqual(
                        compared["monotonic_comparison"],
                        source().compare_grounding(prior, current),
                    )
                    self.assertEqual(
                        compared["monotonic_comparison"]["regression_count"], 2
                    )
                    self.assertEqual(
                        compared["monotonic_comparison"]["improvement_count"], 2
                    )
                    self.assertEqual(
                        json.loads((output / "mathlib_grounding.json").read_text()),
                        prior,
                    )

                    # Null is a real port value. Exercise safe default-context
                    # critics and writing without scanning production inventory.
                    reports = (
                        await remote.call(
                            "mathformer_coherence_loop_critics",
                            {
                                "inventory": {},
                                "graph": {},
                                "grounding": {},
                                "repository_root": None,
                            },
                        )
                    )["reports"]
                    self.assertEqual(reports, source().run_critics({}, {}, {}, None))
                    plans = source().plan_and_gate(reports)
                    with tempfile.TemporaryDirectory(
                        dir=ROOT, prefix=".coherence-fixture-"
                    ) as default_directory:
                        packet = await remote.call(
                            "mathformer_coherence_loop_write_reports",
                            {
                                "directory": default_directory,
                                "inventory": {},
                                "graph": {},
                                "reports": reports,
                                "plans": plans,
                                "repository_root": None,
                            },
                        )
                        self.assertEqual(packet["root"], str(source().REPO_ROOT))
                        self.assertEqual(len(packet["artifacts"]), 10)
                        self.assertTrue(
                            all(
                                (ROOT / p).is_file()
                                for p in packet["artifacts"].values()
                            )
                        )

                    # Full runtime outcomes cover all gate branches and false
                    # report checks. False checks remain successful call data.
                    for status in ("warn", "accepted"):
                        other = root / status
                        fixture(other, status)
                        result = await run(destination=other / "out", repository=other)
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertEqual(
                            result["outputs"]["result"]["gate_status"], status
                        )
                        self.assertTrue(result["outputs"]["result"]["ok"])
                        self.assertEqual(len(result["calls"]), 9)
                    for p in lean.iterdir():
                        p.unlink()
                    result = await run()
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertFalse(result["outputs"]["result"]["ok"])
                    self.assertEqual(result["outputs"]["result"]["module_count"], 0)
                    self.assertEqual(len(result["calls"]), 9)

                    # There is no native retry or repair loop. A smaller host
                    # call ceiling stops before writing or summarizing.
                    for budget in (7, 8):
                        bounded = deepcopy(document)
                        bounded["policy"]["limits"]["max_operation_calls"] = budget
                        destination = root / f"bounded-{budget}"
                        failed = await run(bounded, destination)
                        self.assertEqual(failed["status"], "failed", failed)
                        self.assertIsNone(failed["outputs"])
                        self.assertEqual(
                            sum(
                                bool(c.get("transport_call_performed"))
                                for c in failed["calls"]
                            ),
                            budget,
                        )
                        self.assertIn("budget", str(failed).lower())
                        self.assertEqual(
                            len(contents(destination)), 0 if budget == 7 else 10
                        )
                    timed = deepcopy(document)
                    timed["policy"]["limits"]["wall_time_seconds"] = 1
                    bound, snapshot = compile(timed)

                    async def pending():
                        await asyncio.Event().wait()

                    with self.assertRaises(TimeoutError):
                        await execute(
                            bound,
                            snapshot,
                            {
                                "output_dir": str(root / "timed"),
                                "repository_root": str(root),
                            },
                            remote,
                            pending,
                        )
                    self.assertFalse((root / "timed").exists())

                    # Native I/O errors propagate once and stop following tools.
                    manifest = root / "MathformerPhysicsLib/MANIFEST.json"
                    manifest.write_text("{")
                    failed = await run()
                    self.assertEqual(failed["status"], "failed", failed)
                    self.assertEqual(len(failed["calls"]), 2)
                    self.assertIsNone(failed["outputs"])
                    self.assertEqual(failed["calls"][-1]["status"], "rejected")
                    manifest.unlink()
                    blocker = root / "blocker"
                    blocker.write_text("file")
                    failed = await run(destination=blocker / "out")
                    self.assertEqual(failed["status"], "failed")
                    self.assertEqual(len(failed["calls"]), 1)
                    # Earlier native writes survive a later JSON write failure.
                    partial = root / "partial"
                    partial.mkdir()
                    (partial / "concept_graph.json").mkdir()
                    failed = await run(destination=partial)
                    self.assertEqual(failed["status"], "failed", failed)
                    self.assertEqual(len(failed["calls"]), 8)
                    self.assertIsNone(failed["outputs"])
                    self.assertTrue((partial / "coherence_report.md").is_file())
                    self.assertTrue((partial / "inventory.json").is_file())
                    self.assertFalse((partial / "mathlib_grounding.json").exists())
                    with self.assertRaises(IsADirectoryError):
                        original().run_loop(partial, root)
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_coherence_loop_compare_previous",
                            {
                                "directory": str(partial),
                                "grounding": {"concepts": None},
                            },
                        )
                except BaseException as error:
                    failure = error
            if failure is not None:
                raise failure
        self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
