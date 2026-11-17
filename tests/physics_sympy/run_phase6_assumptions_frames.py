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

"""Check Phase 6 assumption/regime and coordinate-frame modeling."""

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
    PHYSICS_ASSUMPTION_CATEGORIES,
    PHYSICS_CONDITION_KINDS,
    PHYSICS_FRAME_CONTEXT_FIELDS,
    build_physics_frame_context_packet,
    build_physics_regime_assumption_packet,
    classify_assumption_categories,
)

CASES = [
    "constant_acceleration_position",
    "simple_harmonic_oscillator_omega",
    "rc_discharge",
    "ideal_gas_density",
    "projectile_range_level_ground",
    "formalphysics_0000",
    "formalphysics_0020",
    "formalphysics_0026",
    "formalphysics_0176",
]


SYNTHETIC_ASSUMPTIONS = {
    "constant_acceleration": "constant acceleration",
    "frictionless_or_no_damping": "frictionless and no damping",
    "small_angle": "small angle approximation",
    "nonrelativistic_speed": "nonrelativistic speed",
    "massless_spring_string": "massless string",
    "ideal_gas": "ideal gas",
    "lumped_circuit_elements": "lumped circuit elements",
    "steady_or_quasistatic": "quasistatic steady state",
    "positivity_or_nonzero": "R > 0 and nonzero",
}


def run_check() -> Dict[str, Any]:
    """Validate Phase 6 packets and silent-strengthening controls."""
    findings: List[str] = []
    assumption_reports = [
        build_physics_regime_assumption_packet(case_id) for case_id in CASES
    ]
    frame_reports = [build_physics_frame_context_packet(case_id) for case_id in CASES]
    catalog_ids = {item["id"] for item in PHYSICS_ASSUMPTION_CATEGORIES}
    if catalog_ids != set(SYNTHETIC_ASSUMPTIONS):
        findings.append(f"assumption category catalog mismatch: {sorted(catalog_ids)}")
    for expected, text in SYNTHETIC_ASSUMPTIONS.items():
        observed = set(
            classify_assumption_categories(text, {"dimension": "0D circuit"})
        )
        if expected not in observed:
            findings.append(
                f"synthetic assumption did not classify {expected}: {text} -> {sorted(observed)}"
            )

    observed_categories = set()
    observed_condition_kinds = set()
    for report in assumption_reports:
        if not report["ok"]:
            findings.append(
                f"assumption packet is not ok for {report['case_id']}: {report['silent_strengthening_risks']}"
            )
        if (
            set(item["id"] for item in report["assumption_category_catalog"])
            != catalog_ids
        ):
            findings.append(f"assumption catalog mismatch for {report['case_id']}")
        if set(report["condition_kind_catalog"]) != set(PHYSICS_CONDITION_KINDS):
            findings.append(f"condition catalog mismatch for {report['case_id']}")
        if report["silent_strengthening_risks"]:
            findings.append(
                f"unexpected silent-strengthening risks for {report['case_id']}"
            )
        if not report["strengthening_policy_checks"]:
            findings.append(
                f"missing strengthening policy checks for {report['case_id']}"
            )
        observed_categories.update(report["observed_assumption_categories"])
        observed_condition_kinds.update(
            record["condition_kind"] for record in report["condition_records"]
        )

    required_observed_categories = {
        "constant_acceleration",
        "frictionless_or_no_damping",
        "ideal_gas",
        "lumped_circuit_elements",
        "positivity_or_nonzero",
    }
    missing_categories = sorted(
        required_observed_categories.difference(observed_categories)
    )
    if missing_categories:
        findings.append(
            f"expected source-backed categories not observed: {missing_categories}"
        )
    missing_conditions = sorted(
        set(PHYSICS_CONDITION_KINDS).difference(observed_condition_kinds)
    )
    if missing_conditions:
        findings.append(
            f"condition kinds not observed across cases: {missing_conditions}"
        )

    frame_field_catalog = set(PHYSICS_FRAME_CONTEXT_FIELDS)
    for report in frame_reports:
        if not report["ok"]:
            findings.append(
                f"frame packet is not ok for {report['case_id']}: {report['missing_required_frame_fields']}"
            )
        if set(report["frame_context_field_catalog"]) != frame_field_catalog:
            findings.append(f"frame context catalog mismatch for {report['case_id']}")
        context = report["frame_context"]
        if not context["axis_orientation"]:
            findings.append(f"missing axis orientation for {report['case_id']}")
        if not context["positive_direction"]:
            findings.append(f"missing positive direction for {report['case_id']}")
        if (
            report["case_id"].startswith("formalphysics")
            and "component" in str(report["frame"]).lower()
        ):
            if not context["scalar_projection_from_vector_law"]["present"]:
                findings.append(
                    f"formal component frame missing scalar projection for {report['case_id']}"
                )

    one_d = next(
        report
        for report in frame_reports
        if report["case_id"] == "constant_acceleration_position"
    )
    if not one_d["frame_context"]["one_dimensional_reduction"]["present"]:
        findings.append(
            "constant-acceleration frame did not mark one-dimensional reduction"
        )
    vector = next(
        report for report in frame_reports if report["case_id"] == "formalphysics_0000"
    )
    if vector["frame_context"]["basis_vectors"] != ["e_x", "e_y", "e_z"]:
        findings.append("3D formalphysics frame did not infer Cartesian basis vectors")

    regime_persisted = build_physics_regime_assumption_packet(
        "rc_discharge", write_default_report=True
    )
    frame_persisted = build_physics_frame_context_packet(
        "formalphysics_0000", write_default_report=True
    )
    for label, persisted in [("regime", regime_persisted), ("frame", frame_persisted)]:
        path = REPO_ROOT / persisted.get("report_path", "")
        if not persisted.get("report_path") or not path.exists():
            findings.append(f"{label} packet was not persisted by default writer")

    return {
        "ok": not findings,
        "backend": "sympy",
        "style": "sympy_physics_derivation_trace",
        "phase": "phase6_assumptions_regimes_frames_conditions",
        "findings": findings,
        "case_count": len(CASES),
        "observed_assumption_categories": sorted(observed_categories),
        "observed_condition_kinds": sorted(observed_condition_kinds),
        "regime_packet_path": regime_persisted.get("report_path"),
        "frame_packet_path": frame_persisted.get("report_path"),
    }


def main() -> int:
    """Serve as the command-line entry point for the Phase 6 packet check."""
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
