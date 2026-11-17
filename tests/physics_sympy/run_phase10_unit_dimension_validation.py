#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.
#
# Intent:
#   Encode regression checks that catch parser breakage, semantic drift, and missing workflow evidence.
#
# Function:
#   Contains executable tests, fixtures, and manifests used for local and CI validation.
#
# Maintenance Notes:
#   Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.

"""Check Phase 10 unit and dimensional analysis validation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backends.sympy.MathformerPhysicsSympy.pipeline import (  # noqa: E402
    adversarial_suite,
    build_physics_unit_analysis_packet,
)

CASES = [
    "constant_acceleration_position",
    "simple_harmonic_oscillator_omega",
    "work_energy_constant_force",
    "rc_discharge",
    "ideal_gas_density",
    "projectile_range_level_ground",
    "formalphysics_0000",
    "formalphysics_0020",
    "formalphysics_0172",
    "formalphysics_0026",
]


def run_check() -> Dict[str, Any]:
    """Validate Phase 10 report coverage and blocker behavior."""
    findings: List[str] = []
    reports = [build_physics_unit_analysis_packet(case_id) for case_id in CASES]
    observed_unit_conversion_checks = 0
    observed_equation_checks = 0
    observed_step_checks = 0
    for report in reports:
        if not report["ok"]:
            findings.append(
                f"unit analysis packet is not ok for {report['case_id']}: {report['critical_blockers']}"
            )
        if report["completion_blocked"]:
            findings.append(
                f"unit analysis should not block valid case {report['case_id']}"
            )
        if not report["dimensionally_consistent"]:
            findings.append(
                f"dimensionally_consistent is false for valid case {report['case_id']}"
            )
        if not report["per_equation_dimension_checks"]:
            findings.append(f"missing per-equation checks for {report['case_id']}")
        if not report["per_step_dimension_preservation_checks"]:
            findings.append(f"missing per-step checks for {report['case_id']}")
        if report["conflicting_unit_diagnostics"]:
            findings.append(
                f"unexpected conflicting unit diagnostics for {report['case_id']}"
            )
        if report["missing_unit_diagnostics"]:
            findings.append(
                f"unexpected missing unit diagnostics for {report['case_id']}"
            )
        if report["dimensionless_argument_diagnostics"]:
            findings.append(
                f"unexpected dimensionless argument diagnostics for {report['case_id']}"
            )
        if report["completion_blocker_code"] not in {
            None,
            "inconsistent_units_or_dimensions",
        }:
            findings.append(
                f"unexpected blocker code for {report['case_id']}: {report['completion_blocker_code']}"
            )
        observed_equation_checks += len(report["per_equation_dimension_checks"])
        observed_step_checks += len(report["per_step_dimension_preservation_checks"])
        observed_unit_conversion_checks += len(
            report["generated_unit_conversion_checks"]
        )
        for check in report["generated_unit_conversion_checks"]:
            if not check["ok"]:
                findings.append(
                    f"generated unit conversion did not validate: {check['id']}"
                )
        substitution_checks = [
            check
            for check in report["per_step_dimension_preservation_checks"]
            if check["substitution_preserves_dimensions"] is not None
        ]
        if any(
            check["substitution_preserves_dimensions"] is False
            for check in substitution_checks
        ):
            findings.append(
                f"substitution dimension preservation failed for {report['case_id']}"
            )
        solve_checks = [
            check
            for check in report["per_step_dimension_preservation_checks"]
            if check["solved_expression_matches_expected_target_dimension"] is not None
        ]
        if any(
            check["solved_expression_matches_expected_target_dimension"] is False
            for check in solve_checks
        ):
            findings.append(
                f"solved target dimension check failed for {report['case_id']}"
            )

    if observed_equation_checks <= len(CASES):
        findings.append("too few per-equation checks observed across cases")
    if observed_step_checks <= len(CASES):
        findings.append("too few per-step checks observed across cases")
    if observed_unit_conversion_checks < 1:
        findings.append("no generated unit conversion check observed")

    adversarial = adversarial_suite()
    if not adversarial["ok"]:
        findings.append("adversarial unit suite did not pass")
    for result in adversarial["results"]:
        if not result["blocked_complete_status"]:
            findings.append(
                f"adversarial case did not block complete status: {result['id']}"
            )
    expected_adversarial_codes = {
        "additive_dimension_mismatch",
        "dimensioned_function_argument",
    }
    observed_adversarial_codes = {
        finding["code"]
        for result in adversarial["results"]
        for finding in result["findings"]
    }
    if not expected_adversarial_codes.issubset(observed_adversarial_codes):
        findings.append(
            f"adversarial diagnostics missing expected codes: {sorted(observed_adversarial_codes)}"
        )

    persisted = build_physics_unit_analysis_packet(
        "rc_discharge", write_default_report=True
    )
    persisted_path = REPO_ROOT / persisted.get("report_path", "")
    if not persisted.get("report_path") or not persisted_path.exists():
        findings.append("unit analysis report was not persisted by default writer")

    return {
        "ok": not findings,
        "backend": "sympy",
        "style": "sympy_physics_derivation_trace",
        "phase": "phase10_unit_and_dimensional_analysis_validation",
        "findings": findings,
        "case_count": len(CASES),
        "per_equation_check_count": observed_equation_checks,
        "per_step_check_count": observed_step_checks,
        "generated_unit_conversion_check_count": observed_unit_conversion_checks,
        "adversarial_case_count": len(adversarial["results"]),
        "unit_analysis_report_path": persisted.get("report_path"),
    }


def main() -> int:
    """Serve as the command-line entry point for the Phase 10 validation check."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = run_check()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    else:
        print(f"ok: {report['ok']}")
        print(f"case_count: {report['case_count']}")
        print(f"findings: {len(report['findings'])}")
    return 0 if report["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
