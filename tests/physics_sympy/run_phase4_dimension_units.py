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

"""Check Phase 4 dimension modeling and unit-system grounding."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict, List

import sympy as sp

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backends.sympy.MathformerPhysicsSympy.pipeline import (  # noqa: E402
    COMMON_DIMS,
    PHYSICS_BASE_DIMENSIONS,
    PHYSICS_COMMON_UNITS,
    PHYSICS_DIMENSION_INFERENCE_RULES,
    build_physics_dimension_packet,
    build_physics_unit_packet,
    dim_equal,
    dimension_of_expr,
)

CASES = [
    "constant_acceleration_position",
    "simple_harmonic_oscillator_period",
    "work_energy_constant_force",
    "rc_discharge",
    "ideal_gas_density",
    "projectile_range_level_ground",
]


def check_dimension_rules(findings: List[str]) -> Dict[str, Any]:
    """Exercise the dimensional inference rules on valid and invalid expressions."""
    x, v0, t, theta = sp.symbols("x v0 t theta")
    dims = {
        "x": COMMON_DIMS["length"],
        "v0": COMMON_DIMS["velocity"],
        "t": COMMON_DIMS["time"],
        "theta": COMMON_DIMS["dimensionless"],
    }
    bad_sum_findings: List[Dict[str, Any]] = []
    dimension_of_expr(x + v0, dims, bad_sum_findings)
    bad_exp_findings: List[Dict[str, Any]] = []
    dimension_of_expr(sp.exp(t), dims, bad_exp_findings)
    bad_trig_findings: List[Dict[str, Any]] = []
    dimension_of_expr(sp.sin(x), dims, bad_trig_findings)
    good_trig_findings: List[Dict[str, Any]] = []
    dimension_of_expr(sp.sin(theta), dims, good_trig_findings)
    derivative_findings: List[Dict[str, Any]] = []
    derivative_dim = dimension_of_expr(sp.Derivative(x, t), dims, derivative_findings)
    integral_findings: List[Dict[str, Any]] = []
    integral_dim = dimension_of_expr(
        sp.Integral(v0, (t, 0, t)), dims, integral_findings
    )

    if not any(
        item["code"] == "additive_dimension_mismatch" for item in bad_sum_findings
    ):
        findings.append("sum mismatch rule did not flag x + v0")
    if not any(
        item["code"] == "dimensioned_function_argument" for item in bad_exp_findings
    ):
        findings.append("exp/log dimensionless rule did not flag exp(t)")
    if not any(
        item["code"] == "dimensioned_function_argument" for item in bad_trig_findings
    ):
        findings.append("trig dimensionless rule did not flag sin(x)")
    if good_trig_findings:
        findings.append("trig dimensionless rule incorrectly flagged sin(theta)")
    if derivative_findings or not dim_equal(derivative_dim, COMMON_DIMS["velocity"]):
        findings.append("derivative rule did not infer length/time")
    if integral_findings or not dim_equal(integral_dim, COMMON_DIMS["length"]):
        findings.append("integral rule did not infer velocity*time")

    return {
        "bad_sum_findings": bad_sum_findings,
        "bad_exp_findings": bad_exp_findings,
        "bad_trig_findings": bad_trig_findings,
        "derivative_dimension": derivative_dim,
        "integral_dimension": integral_dim,
    }


def run_check() -> Dict[str, Any]:
    """Validate Phase 4 base dimensions, unit grounding, and emitted packets."""
    findings: List[str] = []
    base_names = {entry["name"] for entry in PHYSICS_BASE_DIMENSIONS}
    expected_base_names = {
        "length",
        "mass",
        "time",
        "electric current",
        "temperature",
        "amount of substance",
        "luminous intensity",
        "dimensionless angle or pure number",
    }
    if base_names != expected_base_names:
        findings.append(f"base dimension catalog mismatch: {sorted(base_names)}")

    unit_names = {entry["name"] for entry in PHYSICS_COMMON_UNITS}
    expected_units = {
        "meter",
        "kilogram",
        "second",
        "ampere",
        "kelvin",
        "mole",
        "newton",
        "joule",
        "watt",
        "pascal",
        "coulomb",
        "volt",
        "ohm",
        "radian",
    }
    missing_units = sorted(expected_units.difference(unit_names))
    if missing_units:
        findings.append(f"common unit catalog missing {missing_units}")

    rule_ids = {entry["id"] for entry in PHYSICS_DIMENSION_INFERENCE_RULES}
    expected_rules = {
        "sum_equal_dimensions",
        "product_adds_exponents",
        "power_multiplies_exponents",
        "derivative_divides_by_variable",
        "integral_multiplies_by_variable",
        "transcendentals_dimensionless",
        "exp_log_dimensionless",
        "trig_angle_dimensionless",
    }
    if rule_ids != expected_rules:
        findings.append(
            f"dimension inference rule catalog mismatch: {sorted(rule_ids)}"
        )

    dimension_reports = [build_physics_dimension_packet(case_id) for case_id in CASES]
    unit_reports = [build_physics_unit_packet(case_id) for case_id in CASES]
    for report in dimension_reports:
        if not report["ok"]:
            findings.append(f"dimension packet is not ok for {report['case_id']}")
        if not report["quantity_to_dimension_map"]:
            findings.append(
                f"missing quantity-to-dimension map for {report['case_id']}"
            )
        if not report["quantity_to_unit_map"]:
            findings.append(f"missing quantity-to-unit map for {report['case_id']}")
        if not report["inferred_dimensions"]["steps"]:
            findings.append(f"missing inferred step dimensions for {report['case_id']}")
        if not report["source_anchor_map"]:
            findings.append(f"missing dimension source anchors for {report['case_id']}")
        if report["unresolved_dimensions"] or report["conflicting_dimensions"]:
            findings.append(
                f"unexpected unresolved/conflicting dimensions for {report['case_id']}"
            )
    for report in unit_reports:
        object_names = {
            entry["qualified_name"] for entry in report["unit_grounding"]["objects"]
        }
        for expected in {
            "sympy.physics.units.Quantity",
            "sympy.physics.units.Dimension",
            "sympy.physics.units.dimensions.DimensionSystem",
            "sympy.physics.units.unitsystem.UnitSystem",
            "sympy.physics.units.systems.si.SI",
        }:
            if expected not in object_names:
                findings.append(f"missing SymPy unit object grounding {expected}")
        if not report["quantity_to_unit_map"]:
            findings.append(f"missing unit map for {report['case_id']}")

    persisted = build_physics_dimension_packet(
        "constant_acceleration_position", write_default_report=True
    )
    persisted_path = REPO_ROOT / persisted.get("report_path", "")
    if not persisted.get("report_path") or not persisted_path.exists():
        findings.append("dimension_packet.json was not persisted by default writer")

    rule_probe = check_dimension_rules(findings)

    return {
        "ok": not findings,
        "backend": "sympy",
        "style": "sympy_physics_derivation_trace",
        "phase": "phase4_dimension_unit_modeling",
        "findings": findings,
        "case_count": len(CASES),
        "base_dimensions": sorted(base_names),
        "common_units": sorted(unit_names),
        "rule_ids": sorted(rule_ids),
        "dimension_packet_path": persisted.get("report_path"),
        "rule_probe": rule_probe,
        "unit_grounding_objects": (
            unit_reports[0]["unit_grounding"]["objects"] if unit_reports else []
        ),
    }


def main() -> int:
    """Serve as the command-line entry point for the Phase 4 dimension/unit check."""
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
