#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Real native stages, production MCP registration, Lunar and PRISM execution.

Require WORKFLOW_CONTRACT_PATH explicitly, including before host installation.
Only disposable filesystem context changes; this planner has no external model
or theorem compiler boundary. No tests are skipped when a dependency is absent.
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
APPLICATION_SITES = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT / "tests/mcp/fixtures"),
    str(ROOT),
]
sys.path.extend(APPLICATION_SITES)

import asyncio
from copy import deepcopy
import hashlib
import importlib.util
import json
import tempfile
import unittest
import yaml
from coherence_grounding_filesystem import fixture
from coherence_loop_tools import source
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute
import run_coherence_loop_workflow_tests as native_oracle_tests

DESCRIPTOR = (
    "skills/control/workflow-contract-validator/references/normalized-workflows/"
    "loop/loop_mathformerphysicslib_coherence_grounding_loop_workflow/workflow.yaml"
)
AUTHORED = (
    ROOT
    / "skills/control/workflow-contract-validator/references/coherence-grounding-loop.workflow.json"
)


def digest(data):
    return "sha256:" + hashlib.sha256(data).hexdigest()


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


class CoherenceGroundingTests(unittest.TestCase):
    # Compare all ten byte-level artifacts and CLI status to the preserved
    # pre-extraction entrypoint, including malformed/missing baselines and empty input.
    test_native_oracle_and_report_branches = (
        native_oracle_tests.CoherenceLoopTests.test_original_equivalence_and_source_branches
    )

    def test_registered_lunar_prism(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(
            document["id"],
            "loop_mathformerphysicslib_coherence_grounding_loop_workflow",
        )
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(document, json.loads(AUTHORED.read_text()))
        self.assertEqual(
            document["policy"]["limits"],
            dict(wall_time_seconds=3600, max_operation_calls=9),
        )
        self.assertEqual(document["policy"]["failure"]["retry"]["max_attempts"], 1)
        self.assertEqual(document["flow"]["kind"], "sequence")
        selected = "tests/physics_lean/run_mathformerphysicslib_coherence_loop.py"
        self.assertIn(selected, [r["path"] for r in document["provenance"]["sources"]])
        for row in document["provenance"]["sources"]:
            self.assertEqual(row["digest"], digest((ROOT / row["path"]).read_bytes()))
        spec = importlib.util.spec_from_file_location(
            "coherence_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        normalizer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(normalizer)
        self.assertEqual(
            next(d for d in normalizer.inventory() if d["id"] == document["id"]),
            document,
        )
        expected = [
            "prepare_directory",
            "build_inventory",
            "canonicalize",
            "audit_grounding",
            "compare_previous",
            "run_critics",
            "plan_and_gate",
            "write_reports",
            "check_and_summarize",
        ]
        self.assertEqual([s["operation"] for s in document["flow"]["steps"]], expected)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            lean = fixture(root)
            output = root / "out"
            paths = [
                str(ROOT / "scripts"),
                str(ROOT / "tests/mcp/fixtures"),
                str(ROOT),
                *APPLICATION_SITES,
            ]
            server = (
                "import sys;sys.dont_write_bytecode=True;sys.path[:0]="
                + repr(paths)
                + ";from coherence_grounding_filesystem import serve;serve("
                + repr(str(root))
                + ")"
            )
            manager = SessionManager()
            async with manager.open(
                "coherence-grounding",
                StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
                {},
            ) as remote:
                failure = None
                try:
                    tools = [
                        t.model_dump(by_alias=True, exclude_none=True)
                        for t in await remote.tools()
                    ]

                    def compile_doc(d, inventory=None):
                        received = assets(d)
                        workflow = workflow_documents([DESCRIPTOR], received)[0]
                        return (
                            compile_workflow(
                                "mcp:coherence-grounding",
                                workflow,
                                tools if inventory is None else inventory,
                            ),
                            received,
                        )

                    compiled, received = compile_doc(document)
                    self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                    self.assertEqual(compiled["runtime_status"], "ready")
                    self.assertTrue(compiled["prism_source_hash"])
                    self.assertTrue(compiled["runtime_source"])
                    self.assertFalse(compile_doc(document, [])[0]["runnable"])
                    advertised = {t["name"]: t for t in tools}
                    for op in document["operations"].values():
                        interface = advertised[op["execution"]["binding"]["target"]]
                        self.assertLessEqual(
                            set(interface["inputSchema"].get("required", [])),
                            set(op["inputs"]),
                        )
                        self.assertLessEqual(
                            set(op["outputs"]),
                            set(interface["outputSchema"]["properties"]),
                        )

                    async def allow():
                        pass

                    async def run(d=None, destination=output, omit_root=False):
                        c, a = compile_doc(d or document)
                        self.assertTrue(c["runnable"], c["diagnostics"])
                        inputs = {"output_dir": str(destination)}
                        if not omit_root:
                            inputs["repository_root"] = str(root)
                        return await execute(c, a, inputs, remote, allow)

                    def reset(prior, target=output):
                        target.mkdir(exist_ok=True)
                        path = target / "mathlib_grounding.json"
                        if prior is None:
                            path.unlink(missing_ok=True)
                        else:
                            path.write_text(prior)

                    baseline = json.dumps(
                        {
                            "concepts": [
                                {
                                    "concept_id": "vector_field.real.euclidean3",
                                    "grounding_level": "direct_mathlib",
                                },
                                {
                                    "concept_id": "removed",
                                    "grounding_level": "direct_mathlib",
                                },
                            ]
                        }
                    )
                    for prior in [None, "{", "[]", "{}", baseline]:
                        reset(prior)
                        result = await run()
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertEqual(
                            [c["operation"] for c in result["calls"]], expected
                        )
                        self.assertTrue(
                            all(c["transport_call_performed"] for c in result["calls"])
                        )
                        report = result["outputs"]["report"]
                        self.assertTrue(report["ok"])
                        self.assertEqual(report["gate_status"], "blocked")
                        self.assertEqual(len(report["checks"]), 6)
                        self.assertEqual(
                            result["outputs"]["artifacts"], report["artifacts"]
                        )
                        self.assertEqual(len(report["artifacts"]), 10)
                        plans = result["outputs"]["plans"]
                        self.assertEqual(plans["generative"]["probe_count"], 7)
                        self.assertTrue(plans["repairs"]["actions"])
                        self.assertEqual(
                            plans["gate"]["repair_action_count"],
                            plans["repairs"]["action_count"],
                        )
                        written = {p.name: p.read_bytes() for p in output.iterdir()}
                        comparison = json.loads(
                            (output / "mathlib_grounding.json").read_text()
                        )["monotonic_comparison"]
                        self.assertEqual(
                            comparison["status"],
                            "regressed" if prior == baseline else "no_previous_report",
                        )
                        if prior == baseline:
                            self.assertEqual(comparison["regression_count"], 1)
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["replay_artifacts"])
                        reset(prior)
                        self.assertEqual(source().run_loop(output, root), report)
                        self.assertEqual(
                            written, {p.name: p.read_bytes() for p in output.iterdir()}
                        )
                    result = await run(omit_root=True)
                    self.assertEqual(result["status"], "accepted", result)
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
                    # All three gate states run every critic and write every report.
                    (lean / "Other.lean").unlink()
                    for mode in ["warn", "accepted"]:
                        fixture(root, mode)
                        reset(None)
                        result = await run()
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertEqual(
                            result["outputs"]["report"]["gate_status"], mode
                        )
                        self.assertEqual(
                            [c["operation"] for c in result["calls"]], expected
                        )
                        if mode == "accepted":
                            self.assertEqual(
                                result["outputs"]["plans"]["repairs"]["status"],
                                "no_repairs_required",
                            )
                    # Ownership priorities and every grounding classification use
                    # actual registered stages with deterministic payload fixtures.
                    cid = "vector_field.real.euclidean3"
                    for occurrences, owner in [
                        (
                            [
                                {"path": "Other.lean", "is_foundation": True},
                                {"path": "Foundations/Fields.lean"},
                            ],
                            "Foundations/Fields.lean",
                        ),
                        (
                            [
                                {"path": "first.lean"},
                                {"path": "foundation.lean", "is_foundation": True},
                            ],
                            "foundation.lean",
                        ),
                        ([{"path": "sole.lean"}], "sole.lean"),
                        ([{"path": "first.lean"}, {"path": "second.lean"}], None),
                    ]:
                        data = {
                            "modules": [],
                            "module_count": 0,
                            "concept_occurrence_index": {cid: occurrences},
                        }
                        graph = (
                            await remote.call(
                                "mathformer_coherence_loop_canonicalize",
                                {"inventory": data},
                            )
                        )["graph"]
                        self.assertEqual(graph["concepts"][0]["owner_module"], owner)
                    graph = {
                        "concept_count": 4,
                        "concepts": [
                            {
                                "concept_id": "direct",
                                "owner_module": "case.lean",
                                "mathlib_targets": ["Real"],
                            },
                            {
                                "concept_id": "bridge",
                                "owner_module": "Foundations/X.lean",
                                "mathlib_targets": ["Real"],
                            },
                            {
                                "concept_id": "blocked",
                                "owner_module": None,
                                "mathlib_targets": ["Real"],
                            },
                            {
                                "concept_id": "local",
                                "owner_module": "case.lean",
                                "mathlib_targets": [],
                            },
                        ],
                    }
                    grounding = (
                        await remote.call(
                            "mathformer_coherence_loop_audit_grounding",
                            {"graph": graph},
                        )
                    )["grounding"]
                    self.assertEqual(
                        [c["grounding_level"] for c in grounding["concepts"]],
                        [
                            "direct_mathlib",
                            "mathlib_bridge",
                            "local_blocker",
                            "unverified_local",
                        ],
                    )
                    self.assertEqual(grounding["failed_candidate_count"], 1)
                    graph = {
                        "concept_count": 1,
                        "concepts": [
                            dict(
                                concept_id="missing_api",
                                owner_module="Foundations/Absent.lean",
                                owner_status="owned",
                                occurrences=[],
                                api_terms=["requiredAPI"],
                            )
                        ],
                    }
                    reports = (
                        await remote.call(
                            "mathformer_coherence_loop_critics",
                            dict(
                                inventory={
                                    "foundations_index_exists": True,
                                    "manifest_has_foundations": True,
                                },
                                graph=graph,
                                grounding=grounding,
                                repository_root=str(root),
                            ),
                        )
                    )["reports"]
                    self.assertEqual(len(reports), 4)
                    self.assertEqual(
                        reports[-1]["findings"][0]["kind"],
                        "foundation_without_operable_api",
                    )
                    # A false native reporting check is data, independent of transport success.
                    for path in lean.iterdir():
                        path.unlink()
                    result = await run()
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertFalse(result["outputs"]["report"]["ok"])
                    self.assertEqual(result["outputs"]["report"]["module_count"], 0)
                    self.assertEqual(len(result["calls"]), 9)
                    self.assertEqual(
                        json.loads((output / "concept_graph.json").read_text())[
                            "concepts"
                        ],
                        [],
                    )
                    # No native iteration bound exists. The host call ceiling stops
                    # before writing, without accepting or rerunning the pass.
                    bounded = deepcopy(document)
                    bounded["policy"]["limits"]["max_operation_calls"] = 7
                    target = root / "bounded"
                    result = await run(bounded, target)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(
                        sum(
                            bool(c.get("transport_call_performed"))
                            for c in result["calls"]
                        ),
                        7,
                    )
                    self.assertIn("budget", result["calls"][-1]["error"])
                    self.assertEqual(list(target.iterdir()), [])
                    # Real filesystem failures propagate at their original stage.
                    manifest = lean.parent / "MANIFEST.json"
                    manifest.write_text("{")
                    result = await run()
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]], expected[:2]
                    )
                    with self.assertRaises(json.JSONDecodeError):
                        source().run_loop(output, root)
                    manifest.unlink()
                    blocker = root / "blocker"
                    blocker.write_text("file")
                    result = await run(destination=blocker / "out")
                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(len(result["calls"]), 1)
                    # Native Markdown precedes JSON; no rollback of partial output.
                    target = root / "partial"
                    target.mkdir()
                    (target / "inventory.json").mkdir()
                    result = await run(destination=target)
                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]], expected[:8]
                    )
                    self.assertTrue((target / "coherence_report.md").is_file())
                    self.assertFalse((target / "mathlib_grounding.json").exists())
                    with self.assertRaises(IsADirectoryError):
                        source().run_loop(target, root)
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_coherence_loop_prepare_directory",
                            {"output_dir": str(root.parent / "denied")},
                        )
                except BaseException as error:
                    failure = error
            self.assertFalse(manager.active)
            if failure is not None:
                raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
