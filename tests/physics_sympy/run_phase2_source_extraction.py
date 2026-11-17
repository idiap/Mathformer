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

"""Check Phase 2 physics source intake and derivation-unit extraction."""

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
    PHYSICS_SOURCE_FIXTURES,
    PHYSICS_SOURCE_UNIT_ROLES,
    extract_physics_source_units,
)

REQUIRED_UNIT_FIELDS = {
    "source_anchors",
    "literal_nl",
    "literal_latex",
    "inferred_symbols",
    "candidate_dimensions",
    "candidate_units",
    "unresolved_ambiguity_notes",
}


FIXTURE_CASES = {
    "constant_acceleration_kinematics": "constant_acceleration_position",
    "simple_harmonic_oscillator_period": "simple_harmonic_oscillator_period",
    "work_energy_theorem": "work_energy_constant_force",
    "rc_circuit_discharge": "rc_discharge",
    "ideal_gas_law_manipulation": "ideal_gas_density",
    "projectile_range_level_ground": "projectile_range_level_ground",
}


def run_check() -> Dict[str, Any]:
    """Validate source-unit extraction across the controlled Phase 2 fixtures."""
    findings: List[str] = []
    reports = []
    role_union = set()
    fixture_paths = set(PHYSICS_SOURCE_FIXTURES)
    if set(FIXTURE_CASES) != fixture_paths:
        findings.append("fixture map does not match required Phase 2 fixture set")
    for fixture_id, case_id in FIXTURE_CASES.items():
        path = REPO_ROOT / PHYSICS_SOURCE_FIXTURES[fixture_id]
        if not path.exists():
            findings.append(f"fixture missing: {fixture_id}")
            continue
        source = path.read_text(encoding="utf-8")
        report = extract_physics_source_units(
            case_id, source, str(path.relative_to(REPO_ROOT))
        )
        reports.append(report)
        if not report["ok"]:
            findings.append(
                f"extractor returned not-ok for {case_id}: {report['malformed_units']}"
            )
        for unit in report["units"]:
            role_union.add(unit["role"])
            if unit["role"] not in PHYSICS_SOURCE_UNIT_ROLES:
                findings.append(f"unknown role {unit['role']} in {unit['id']}")
            missing = REQUIRED_UNIT_FIELDS.difference(unit)
            if missing:
                findings.append(f"unit {unit['id']} missing fields: {sorted(missing)}")
            if not unit["source_anchors"]:
                findings.append(f"unit {unit['id']} has no source anchors")
            if unit["literal_nl"] is None:
                findings.append(f"unit {unit['id']} has null literal_nl")
    missing_roles = sorted(set(PHYSICS_SOURCE_UNIT_ROLES).difference(role_union))
    if missing_roles:
        findings.append(f"required roles not observed across fixtures: {missing_roles}")
    return {
        "ok": not findings,
        "backend": "sympy",
        "style": "sympy_physics_derivation_trace",
        "phase": "phase2_source_intake_derivation_unit_extraction",
        "findings": findings,
        "fixture_count": len(reports),
        "observed_roles": sorted(role_union),
        "missing_roles": missing_roles,
        "unit_counts": {report["case_id"]: len(report["units"]) for report in reports},
        "role_counts": {report["case_id"]: report["role_counts"] for report in reports},
    }


def main() -> int:
    """Serve as the command-line entry point for the Phase 2 source check."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = run_check()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"ok: {report['ok']}")
        print(f"fixture_count: {report['fixture_count']}")
        print(f"findings: {len(report['findings'])}")
    return 0 if report["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
