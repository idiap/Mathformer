#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Candidate-explicit native/MCP/Lunar/PRISM fixtures for the SymPy trace loop.

The shared suite uses temporary executable artifact inputs, not provider calls.
All five source CLIs, callback histories, logging and report emission run for
real. There is no model or external compiler in this source schedule. Lunar's
PRISM parser, checker, compiler and runtime are never substituted.
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

import hashlib  # noqa: E402
import json  # noqa: E402
import tempfile  # noqa: E402
import unittest  # noqa: E402
from unittest.mock import patch  # noqa: E402
import run_sympy_source_only_workflow_tests as suite  # noqa: E402

suite.ID = "loop_sympy_physics_derivation_trace_loop_workflow"
suite.DESCRIPTOR = (
    f"{suite.REFERENCES}/normalized-workflows/loop/{suite.ID}/workflow.yaml"
)
suite.AUTHORED = ROOT / suite.REFERENCES / "sympy-physics-derivation-loop.workflow.json"
suite.OUTPUT_PORT = "report"
suite.ASSESS_OPERATION = "assess_run"


class SympyTraceLoopTests(suite.SourceOnlyTests):
    def test_contract_and_generator(self):
        self.assertEqual(self.doc["id"], suite.ID)
        self.assertEqual(self.doc["lifecycle"], "active")
        self.assertEqual(self.doc, json.loads(suite.AUTHORED.read_text()))
        self.assertEqual(self.doc["aliases"], ["sympy_physics_derivation_trace_loop"])
        self.assertEqual(
            self.doc["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 9},
        )
        self.assertEqual(self.doc["policy"]["effects"]["network"], [])
        self.assertEqual(self.doc["policy"]["effects"]["external_write"], [])
        self.assertEqual(self.doc["flow"]["steps"][2]["max_iterations"], 5)
        self.assertEqual(self.doc["flow"]["steps"][2]["on_exhausted"], "fail")
        self.assertIn(
            suite.SOURCE, [r["path"] for r in self.doc["provenance"]["sources"]]
        )
        for row in self.doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        validation = suite.validate(
            suite.AUTHORED, repository_root=ROOT, require_declared_bindings=True
        )
        self.assertTrue(validation["valid"], validation["errors"])
        normalizer = suite.load(
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
            "sympy_trace_loop_normalizer",
        )
        selected = [
            row
            for row in normalizer.parse_loop_contracts(
                (ROOT / normalizer.HOOKS).read_text().splitlines()
            )
            if row["id"] == "sympy_physics_derivation_trace_loop"
        ]
        self.assertEqual(len(selected), 1)
        # Scope metadata inventory to this loop; do not regenerate host-owned
        # YAML/catalog or inspect unrelated work in the shared checkout.
        with (
            patch.object(normalizer.hub, "build_registry", return_value={}),
            patch.object(normalizer.hub, "build_intent_routes", return_value=[]),
            patch.object(normalizer, "parse_loop_contracts", return_value=selected),
        ):
            self.assertEqual(
                [d for d in normalizer.inventory() if d["id"] == suite.ID], [self.doc]
            )

    def test_native_nonzero_findings_and_exhaustion(self):
        # Real source fixtures produce nonzero gates and severity findings;
        # the runner must retain both kinds of blocker and still visit stage 5.
        with tempfile.TemporaryDirectory() as tmp:
            root = suite.mount(Path(tmp) / "scratch")
            suite.input_case(root, "blocked")
            native = suite.native(root)
            prepared = native.prepare_run(
                suite.CASE, root / "source.json", root / "out"
            )
            state = native.pack_run_state(prepared)
            for index in range(5):
                done = native.execute_run_stage(state)
                self.assertEqual(state["next_stage"], index + 1)
                self.assertEqual(done, index == 4)
            self.assertEqual(list(state["command_metadata"]), suite.ORDER)
            self.assertTrue(
                all(m["returncode"] == 0 for m in state["command_metadata"].values())
            )
            self.assertTrue(
                any(
                    b.get("severity") in {"high", "critical", "error"}
                    for b in state["blockers"]
                )
            )
            self.assertTrue(native.assess_run(state)["blocked"])
            before = json.dumps(state)
            with self.assertRaisesRegex(ValueError, "exhausted"):
                native.execute_run_stage(state)
            self.assertEqual(json.dumps(state), before)
            commands = prepared["stage_specs"]
            self.assertIn("--run-gates", commands["goal_plan"])
            self.assertEqual(
                commands["repair_expansion_map"][
                    commands["repair_expansion_map"].index("--review") + 1
                ],
                str(root / "out" / suite.CASE / "design_guard_review.json"),
            )
            control = commands["recursive_repair_control"]
            self.assertEqual(
                control[control.index("--expansion-map") + 1],
                str(root / "out" / suite.CASE / "repair_expansion.json"),
            )
            for flag in ("--previous-expansion-map", "--iteration", "--max-iterations"):
                self.assertNotIn(flag, control)
            # A callback exception causes a real child CLI failure. This is
            # distinct from high findings in a successfully emitted report.
            suite.input_case(root, "crash")
            prepared = native.prepare_run(
                suite.CASE, root / "source.json", root / "out"
            )
            failed = native.pack_run_state(prepared)
            for index in range(5):
                self.assertEqual(native.execute_run_stage(failed), index == 4)
            self.assertEqual(list(failed["command_metadata"]), suite.ORDER)
            self.assertTrue(
                any(b["code"] == "stage_command_failed" for b in failed["blockers"])
            )
            self.assertEqual(failed["next_stage"], 5)


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(SympyTraceLoopTests)
    )
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
