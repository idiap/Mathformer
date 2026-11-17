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

"""Check Phase 7 implicit-gap detection and generated closure expansion."""

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
    PHYSICS_GAP_TYPES,
    PHYSICS_GENERATED_SUBSTEP_KINDS,
    build_physics_gap_detection_packet,
    build_physics_gap_expansion_packet,
)

CASES = [
    "constant_acceleration_position",
    "constant_acceleration_velocity_position",
    "simple_harmonic_oscillator_omega",
    "work_energy_constant_force",
    "rc_discharge",
    "ideal_gas_density",
    "projectile_range_level_ground",
    "formalphysics_0000",
    "formalphysics_0020",
    "formalphysics_0066",
    "formalphysics_0172",
    "formalphysics_0026",
]


REQUIRED_EXPANSION_FIELDS = {
    "source_predecessor_anchor",
    "source_successor_anchor",
    "rule_api_or_law_used",
    "input_expression",
    "output_expression",
    "side_conditions",
    "dimension_check",
}


def run_check() -> Dict[str, Any]:
    """Validate implicit-gap detection and generated support expansion."""
    findings: List[str] = []
    detection_reports = [
        build_physics_gap_detection_packet(case_id) for case_id in CASES
    ]
    expansion_reports = [
        build_physics_gap_expansion_packet(case_id) for case_id in CASES
    ]
    observed_gap_types = set()
    observed_generated_kinds = set()

    for report in detection_reports:
        if not report["ok"]:
            findings.append(f"gap detection packet is not ok for {report['case_id']}")
        if set(report["gap_type_catalog"]) != set(PHYSICS_GAP_TYPES):
            findings.append(f"gap type catalog mismatch for {report['case_id']}")
        if set(report["generated_substep_kind_catalog"]) != set(
            PHYSICS_GENERATED_SUBSTEP_KINDS
        ):
            findings.append(
                f"generated substep catalog mismatch for {report['case_id']}"
            )
        if not report["implicit_gaps"]:
            findings.append(f"no implicit gaps detected for {report['case_id']}")
        for gap in report["implicit_gaps"]:
            observed_gap_types.add(gap["gap_type"])
            if gap["status"] != "needs_expansion":
                findings.append(
                    f"detected gap status should be needs_expansion: {gap['id']}"
                )
            for field in [
                "source_predecessor_anchor",
                "source_successor_anchor",
                "candidate_rule_api_or_law",
                "side_conditions",
            ]:
                if not gap.get(field):
                    findings.append(f"detected gap missing {field}: {gap['id']}")

    for report in expansion_reports:
        if not report["ok"]:
            findings.append(
                f"gap expansion packet is not ok for {report['case_id']}: {report['unresolved_gaps']}"
            )
        if report["unresolved_gaps"]:
            findings.append(
                f"unresolved gaps remain for {report['case_id']}: {report['unresolved_gaps']}"
            )
        if report["completion_blocked"]:
            findings.append(
                f"completion should not be blocked after expansion for {report['case_id']}"
            )
        if not report["expanded_steps"]:
            findings.append(f"no expanded steps for {report['case_id']}")
        for step in report["expanded_steps"]:
            observed_generated_kinds.add(step["generated_substep_kind"])
            missing_fields = sorted(
                field for field in REQUIRED_EXPANSION_FIELDS if not step.get(field)
            )
            if missing_fields:
                findings.append(
                    f"expanded step missing fields {missing_fields}: {step['id']}"
                )
            if step["source_backing"] != "generated_support":
                findings.append(
                    f"expanded step is not marked generated_support: {step['id']}"
                )
            if step["dimension_check"]["status"] not in {"pass", "recorded", "unknown"}:
                findings.append(
                    f"unexpected dimension-check status for {step['id']}: {step['dimension_check']}"
                )

    missing_gap_types = sorted(set(PHYSICS_GAP_TYPES).difference(observed_gap_types))
    if missing_gap_types:
        findings.append(f"gap types not observed across cases: {missing_gap_types}")
    missing_generated_kinds = sorted(
        set(PHYSICS_GENERATED_SUBSTEP_KINDS).difference(observed_generated_kinds)
    )
    if missing_generated_kinds:
        findings.append(
            f"generated substep kinds not observed across cases: {missing_generated_kinds}"
        )

    rc_detection = next(
        report for report in detection_reports if report["case_id"] == "rc_discharge"
    )
    for expected in {
        "missing_ode_solution",
        "missing_initial_condition_application",
        "missing_unit_conversion",
    }:
        if rc_detection["gap_counts"][expected] < 1:
            findings.append(f"RC discharge did not detect {expected}")
    formal_detection = next(
        report
        for report in detection_reports
        if report["case_id"] == "formalphysics_0000"
    )
    if formal_detection["gap_counts"]["missing_coordinate_projection"] < 1:
        findings.append("formalphysics_0000 did not detect a coordinate projection gap")

    persisted_detection = build_physics_gap_detection_packet(
        "rc_discharge", write_default_report=True
    )
    persisted_expansion = build_physics_gap_expansion_packet(
        "rc_discharge", write_default_report=True
    )
    for label, persisted in [
        ("detection", persisted_detection),
        ("expansion", persisted_expansion),
    ]:
        path = REPO_ROOT / persisted.get("report_path", "")
        if not persisted.get("report_path") or not path.exists():
            findings.append(f"{label} packet was not persisted by default writer")

    return {
        "ok": not findings,
        "backend": "sympy",
        "style": "sympy_physics_derivation_trace",
        "phase": "phase7_implicit_gap_detection_and_closure",
        "findings": findings,
        "case_count": len(CASES),
        "observed_gap_types": sorted(observed_gap_types),
        "observed_generated_substep_kinds": sorted(observed_generated_kinds),
        "gap_packet_path": persisted_detection.get("report_path"),
        "gap_expansion_packet_path": persisted_expansion.get("report_path"),
    }


def main() -> int:
    """Serve as the command-line entry point for the Phase 7 gap check."""
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
