#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402 - imports follow explicit direct-script path setup
#
#

# File Documentation
#
# Motivation:
#   Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.
#
# Intent:
#   Encode regression checks that catch parser breakage, semantic drift, and missing workflow evidence.
#
# Function:
#   Runs the Phase 15 controlled physics test suite and then a wiki-level KdV physics case.
#
# Maintenance Notes:
#   Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.

"""Run Phase 15 controlled physics tests plus the wiki-level KdV case."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from libraries.MathformerLib.SympyPhysics.Solvers.AnalyticSoliton import (
    KdVOneSoliton,
)
from libraries.MathformerLib.SympyPhysics.Solvers.PseudoSpectralPDE import (
    KdVOneSolitonSimulation,
)
from backends.sympy.MathformerPhysicsSympy.pipeline import (
    WIKI_LEVEL_PHYSICS_CASES,
    controlled_suite,
    now,
)


def run_wiki_level_cases(output_root: Path, enabled: bool) -> dict:
    """Run the Phase 15 wiki-level physics case after controlled cases pass.

    Motivation:
        The controlled suite checks small derivations with explicit oracles;
        the wiki-level case checks that the same evidence discipline scales to
        a realistic PDE soliton derivation and simulation.

    Intent:
        Keep the wiki-level run separate from the controlled fixtures while
        preserving a single Phase 15 verdict.

    Inputs:
        ``output_root`` is where the wiki report is written. ``enabled`` is
        false when controlled fixtures failed, so the wiki case is skipped
        rather than hiding the earlier blocker.

    Outputs:
        Returns a compact report containing the wiki case verdict and report
        path.
    """
    output_root.mkdir(parents=True, exist_ok=True)
    if not enabled:
        return {
            "ok": False,
            "skipped": True,
            "reason": "controlled suite did not pass",
            "cases": WIKI_LEVEL_PHYSICS_CASES,
        }
    derivation = KdVOneSoliton.run_all()
    simulation = KdVOneSolitonSimulation.run_all()
    report = {
        "ok": bool(derivation["ok"] and simulation["passed"]),
        "skipped": False,
        "cases": WIKI_LEVEL_PHYSICS_CASES,
        "derivation_status": derivation["status"],
        "pde_residual": derivation["pde_residual"],
        "reduced_ode_residual": derivation["reduced_ode_residual"],
        "numeric_samples_pass": derivation["numeric_samples"]["passed"],
        "simulation_pass": simulation["passed"],
        "simulation_max_abs_error": simulation["max_abs_error"],
        "simulation_tolerance": simulation["tolerance"],
        "derivation": derivation,
        "simulation": simulation,
    }
    report_path = output_root / "korteweg_de_vries_one_soliton_report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    return {
        "ok": report["ok"],
        "skipped": False,
        "cases": WIKI_LEVEL_PHYSICS_CASES,
        "report_path": str(report_path.relative_to(REPO_ROOT)),
        "derivation_status": report["derivation_status"],
        "pde_residual": report["pde_residual"],
        "simulation_max_abs_error": report["simulation_max_abs_error"],
        "simulation_tolerance": report["simulation_tolerance"],
    }


def main() -> int:
    """Coordinate the Phase 15 command-line workflow.

    Motivation:
        Phase 15 should be runnable from one deterministic entry point in CI,
        local development, and agent-driven validation.

    Intent:
        Parse options, run controlled fixtures, run the wiki-level follow-up
        only when appropriate, persist a compact suite report, and return a
        failing exit code for any contract break.

    Inputs:
        Command-line options define the output root and JSON display mode.

    Outputs:
        Writes Phase 15 reports under ``artifacts/physics_sympy`` and returns
        process status ``0`` on success or ``3`` on validation failure.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("artifacts/physics_sympy/phase15_controlled_suite"),
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    output_root = (REPO_ROOT / args.output_root).resolve()
    controlled = controlled_suite(output_root / "controlled", include_details=False)
    wiki = run_wiki_level_cases(output_root / "wiki_level", enabled=controlled["ok"])
    report = {
        "ok": bool(controlled["ok"] and wiki["ok"]),
        "backend": "sympy",
        "style": "sympy_physics_derivation_trace",
        "phase": "phase15_controlled_physics_test_suite",
        "generated_at": now(),
        "controlled": controlled,
        "wiki_level": wiki,
    }
    report_path = output_root / "phase15_report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    else:
        print(f"ok: {report['ok']}")
        print(f"controlled_case_count: {controlled['case_count']}")
        print(f"wiki_level_skipped: {wiki['skipped']}")
        print(f"report: {report_path.relative_to(REPO_ROOT)}")
    return 0 if report["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
