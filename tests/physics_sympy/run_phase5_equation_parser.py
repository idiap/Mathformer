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

"""Check Phase 5 physics equation parsing and normalization."""

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
    PHYSICS_EQUATION_FORM_KINDS,
    PHYSICS_EQUATION_NORMALIZATION_TARGETS,
    build_physics_equation_packet,
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
    "formalphysics_0026",
]


def run_check() -> Dict[str, Any]:
    """Validate Phase 5 equation parser packets across scalar, vector, and operator cases."""
    findings: List[str] = []
    reports = [build_physics_equation_packet(case_id) for case_id in CASES]
    observed_kinds = set()
    observed_normalization_ids = {
        item["id"] for item in PHYSICS_EQUATION_NORMALIZATION_TARGETS
    }
    expected_normalization_ids = {
        "equality_to_eq",
        "residual_form",
        "derivative_form",
        "integral_form",
        "vector_projection_form",
        "ode_solution_form",
    }
    if observed_normalization_ids != expected_normalization_ids:
        findings.append(
            f"normalization target catalog mismatch: {sorted(observed_normalization_ids)}"
        )

    for report in reports:
        if not report["ok"]:
            findings.append(
                f"equation packet is not ok for {report['case_id']}: {report['blockers']}"
            )
        if not report["parsed"]:
            findings.append(f"parsed flag is false for {report['case_id']}")
        if report["target_parse_status"] != "parsed":
            findings.append(f"target equation did not parse for {report['case_id']}")
        if not report["target_derived_from_trace"]:
            findings.append(
                f"target equation was not derived from trace for {report['case_id']}"
            )
        if not report["equation_packet"]:
            findings.append(f"empty equation packet for {report['case_id']}")
        if not report["raw_source_equations"]:
            findings.append(
                f"missing raw source equation records for {report['case_id']}"
            )
        if report["unparsed_source_targets"]:
            findings.append(f"unparsed target records for {report['case_id']}")
        if not all(
            record["normalized_eq"] for record in report["normalized_equations"]
        ):
            findings.append(
                f"missing normalized Eq representation for {report['case_id']}"
            )
        if not all(
            record["residual"] is not None for record in report["normalized_equations"]
        ):
            findings.append(f"missing residual representation for {report['case_id']}")
        if set(report["equation_form_kinds"]) != set(PHYSICS_EQUATION_FORM_KINDS):
            findings.append(f"equation form catalog mismatch for {report['case_id']}")
        observed_kinds.update(report["coverage"]["kind_coverage"])

    missing_kinds = sorted(set(PHYSICS_EQUATION_FORM_KINDS).difference(observed_kinds))
    if missing_kinds:
        findings.append(
            f"equation kinds not observed across test cases: {missing_kinds}"
        )

    rc_report = next(
        report for report in reports if report["case_id"] == "rc_discharge"
    )
    rc_records = rc_report["equation_packet"]
    if not any(record["contains_derivative"] for record in rc_records):
        findings.append("RC discharge packet did not preserve a derivative form")
    if not any(record["uses_ode_solution"] for record in rc_records):
        findings.append("RC discharge packet did not mark an ODE solution form")

    constant_report = next(
        report
        for report in reports
        if report["case_id"] == "constant_acceleration_position"
    )
    if not any(
        record["contains_integral"] for record in constant_report["equation_packet"]
    ):
        findings.append(
            "constant-acceleration packet did not preserve an Integral form"
        )

    vector_report = next(
        report for report in reports if report["case_id"] == "formalphysics_0000"
    )
    if not any(
        record["equation_kind"] == "vector_equation" and record["parser_uncertainty"]
        for record in vector_report["equation_packet"]
    ):
        findings.append("vector projection record did not preserve parser uncertainty")

    persisted = build_physics_equation_packet("rc_discharge", write_default_report=True)
    persisted_path = REPO_ROOT / persisted.get("report_path", "")
    if not persisted.get("report_path") or not persisted_path.exists():
        findings.append("equation_packet.json was not persisted by default writer")

    return {
        "ok": not findings,
        "backend": "sympy",
        "style": "sympy_physics_derivation_trace",
        "phase": "phase5_physics_equation_parsing_normalization",
        "findings": findings,
        "case_count": len(reports),
        "observed_equation_kinds": sorted(observed_kinds),
        "normalization_targets": sorted(observed_normalization_ids),
        "equation_packet_path": persisted.get("report_path"),
        "kind_counts": {report["case_id"]: report["kind_counts"] for report in reports},
    }


def main() -> int:
    """Serve as the command-line entry point for the Phase 5 equation parser check."""
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
