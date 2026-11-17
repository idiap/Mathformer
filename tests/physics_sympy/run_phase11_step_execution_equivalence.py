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
#   Contains executable tests, fixtures, and manifests used for local and CI validation.
#
# Maintenance Notes:
#   Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.

"""Check Phase 11 step execution, equivalence, and ODE validation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backends.sympy.MathformerPhysicsSympy.pipeline import (
    build_physics_step_execution_packet,
)  # noqa: E402

CASES = [
    "constant_acceleration_position",
    "work_energy_constant_force",
    "ideal_gas_density",
    "rc_discharge",
    "projectile_range_level_ground",
    "formalphysics_0000",
    "formalphysics_0172",
]


def require_all_ok(findings: List[str], report: Dict[str, Any], field: str) -> None:
    """Append findings for failed checks in one Phase 11 check group."""
    for check in report.get(field, []):
        if not check.get("ok"):
            findings.append(
                f"{field} failed for {report['case_id']}: {check['id']} -> {check}"
            )


def run_check() -> Dict[str, Any]:
    """Validate Phase 11 report coverage over representative derivation families."""
    findings: List[str] = []
    reports = [build_physics_step_execution_packet(case_id) for case_id in CASES]
    observed_substitution_checks = 0
    observed_calculus_checks = 0
    observed_ode_solution_checks = 0
    observed_approximation_checks = 0
    observed_projection_checks = 0
    for report in reports:
        if not report["ok"]:
            findings.append(
                f"step execution packet is not ok for {report['case_id']}: {report['critical_blockers']}"
            )
        if report["completion_blocked"]:
            findings.append(
                f"step execution should not block valid case {report['case_id']}"
            )
        if not report["legacy_step_verification"]["passed"]:
            findings.append(f"legacy step verification failed for {report['case_id']}")
        if not report["algebraic_equivalence_checks"]:
            findings.append(
                f"missing algebraic equivalence checks for {report['case_id']}"
            )
        require_all_ok(findings, report, "algebraic_equivalence_checks")
        require_all_ok(findings, report, "substitution_checks")
        require_all_ok(findings, report, "calculus_checks")
        require_all_ok(findings, report, "ode_solution_checks")
        require_all_ok(findings, report, "approximation_checks")
        require_all_ok(findings, report, "projection_reduction_checks")
        observed_substitution_checks += len(report["substitution_checks"])
        observed_calculus_checks += len(report["calculus_checks"])
        observed_ode_solution_checks += len(report["ode_solution_checks"])
        observed_approximation_checks += len(report["approximation_checks"])
        observed_projection_checks += len(report["projection_reduction_checks"])

    rc_report = next(
        report for report in reports if report["case_id"] == "rc_discharge"
    )
    rc_ode_checks = rc_report["ode_solution_checks"]
    if len(rc_ode_checks) != 1:
        findings.append("rc_discharge should emit exactly one ODE solution check")
    else:
        rc_check = rc_ode_checks[0]
        if rc_check["ode_residual"] != "0":
            findings.append(
                f"rc_discharge ODE residual should be zero: {rc_check['ode_residual']}"
            )
        if rc_check["initial_condition_residual"] != "0":
            findings.append(
                f"rc_discharge initial condition residual should be zero: {rc_check['initial_condition_residual']}"
            )
        if not rc_check["sample_check_passed"]:
            findings.append("rc_discharge admissible numeric sample did not pass")

    projectile_report = next(
        report
        for report in reports
        if report["case_id"] == "projectile_range_level_ground"
    )
    if not projectile_report["approximation_checks"]:
        findings.append(
            "projectile case should record its nonzero-flight branch/regime check"
        )
    for check in projectile_report["approximation_checks"]:
        if not check["regime_present"]:
            findings.append(
                f"projectile regime was not present for branch check: {check}"
            )

    formal_report = next(
        report for report in reports if report["case_id"] == "formalphysics_0000"
    )
    if not formal_report["projection_reduction_checks"]:
        findings.append(
            "formalphysics_0000 should emit vector-to-scalar projection checks"
        )
    for check in formal_report["projection_reduction_checks"]:
        if not check["projection_axis_declared"]:
            findings.append(f"projection axis not declared: {check}")
        if not check["sign_convention_declared"]:
            findings.append(f"sign convention not declared: {check}")
        if not check["component_equation_dimensionally_consistent"]:
            findings.append(
                f"component equation is not dimensionally consistent: {check}"
            )

    if observed_substitution_checks < 2:
        findings.append("too few substitution checks observed")
    if observed_calculus_checks < 3:
        findings.append("too few calculus checks observed")
    if observed_ode_solution_checks < 1:
        findings.append("no ODE solution check observed")
    if observed_approximation_checks < 1:
        findings.append("no approximation or branch-condition check observed")
    if observed_projection_checks < 1:
        findings.append("no projection reduction check observed")

    persisted = build_physics_step_execution_packet(
        "rc_discharge", write_default_report=True
    )
    persisted_path = REPO_ROOT / persisted.get("report_path", "")
    if not persisted.get("report_path") or not persisted_path.exists():
        findings.append("step execution report was not persisted by default writer")

    return {
        "ok": not findings,
        "backend": "sympy",
        "style": "sympy_physics_derivation_trace",
        "phase": "phase11_step_execution_equivalence_ode_validation",
        "findings": findings,
        "case_count": len(CASES),
        "substitution_check_count": observed_substitution_checks,
        "calculus_check_count": observed_calculus_checks,
        "ode_solution_check_count": observed_ode_solution_checks,
        "approximation_check_count": observed_approximation_checks,
        "projection_reduction_check_count": observed_projection_checks,
        "step_execution_report_path": persisted.get("report_path"),
    }


def main() -> int:
    """Serve as the command-line entry point for the Phase 11 validation check."""
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
