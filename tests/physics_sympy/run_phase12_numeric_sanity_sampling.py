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

"""Check Phase 12 numeric sanity, counterexamples, and regime sampling."""

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
    build_physics_numeric_sanity_packet,
    evaluate_numeric_trial,
    numeric_samples,
)

CASES = [
    "constant_acceleration_position",
    "simple_harmonic_oscillator_omega",
    "simple_harmonic_oscillator_period",
    "rc_discharge",
    "ideal_gas_density",
    "projectile_range_level_ground",
    "formalphysics_0000",
    "formalphysics_0172",
]


def run_check() -> Dict[str, Any]:
    """Validate Phase 12 sampling coverage and counterexample formatting."""
    findings: List[str] = []
    reports = [build_physics_numeric_sanity_packet(case_id) for case_id in CASES]
    observed_constraints: Dict[str, int] = {}
    for report in reports:
        if not report["ok"]:
            findings.append(
                f"numeric sanity packet is not ok for {report['case_id']}: {report['critical_blockers']}"
            )
        if report["completion_blocked"]:
            findings.append(
                f"numeric sanity should not block valid case {report['case_id']}"
            )
        if report["sample_count"] < 5:
            findings.append(
                f"too few samples for {report['case_id']}: {report['sample_count']}"
            )
        if report["counterexamples"]:
            findings.append(
                f"unexpected counterexamples for valid case {report['case_id']}"
            )
        if report["supporting_evidence_policy"].find("supporting evidence only") < 0:
            findings.append(
                f"missing supporting-evidence policy for {report['case_id']}"
            )
        if (
            not report["symbolic_step_validation"]["required"]
            or not report["symbolic_step_validation"]["ok"]
        ):
            findings.append(
                f"symbolic step validation not required/ok for {report['case_id']}"
            )
        for domain_check in report["domain_checks"]:
            if not domain_check["ok"]:
                findings.append(
                    f"domain check failed for {report['case_id']}: {domain_check}"
                )
        for constraint in report["domain_constraints"]:
            observed_constraints[constraint["kind"]] = (
                observed_constraints.get(constraint["kind"], 0) + 1
            )
        for result in report["sample_results"]:
            if not result["passed"]:
                findings.append(
                    f"sample result failed for {report['case_id']}: {result}"
                )
            if not result["domain_ok"]:
                findings.append(
                    f"sample domain was not admissible for {report['case_id']}: {result}"
                )

    expected_constraint_kinds = {
        "positive",
        "nonnegative",
        "nonzero_denominator",
        "open_interval",
    }
    missing_constraint_kinds = expected_constraint_kinds - set(observed_constraints)
    if missing_constraint_kinds:
        findings.append(
            f"missing expected domain constraint kinds: {sorted(missing_constraint_kinds)}"
        )

    legacy = numeric_samples("rc_discharge")
    false_expected = sp.Integer(0)
    failed_trial = evaluate_numeric_trial(
        "rc_discharge",
        legacy["sample"],
        expected_expression=false_expected,
        failed_step_id="phase12_schema_probe",
    )
    counterexample = failed_trial.get("counterexample", {})
    required_counterexample_fields = {
        "sampled_values",
        "units_dimensions",
        "failed_equation",
        "failed_step_id",
        "source_anchors",
    }
    if failed_trial["passed"]:
        findings.append(
            "false expected-expression probe should produce a counterexample"
        )
    missing_counterexample_fields = required_counterexample_fields - set(counterexample)
    if missing_counterexample_fields:
        findings.append(
            f"counterexample schema missing fields: {sorted(missing_counterexample_fields)}"
        )
    if counterexample.get("failed_step_id") != "phase12_schema_probe":
        findings.append("counterexample did not preserve failed step id")
    if not counterexample.get("source_anchors"):
        findings.append("counterexample did not preserve source anchors")
    if "R" not in counterexample.get("units_dimensions", {}):
        findings.append(
            "counterexample units/dimensions did not include sampled resistance"
        )

    persisted = build_physics_numeric_sanity_packet(
        "rc_discharge", write_default_report=True
    )
    persisted_path = REPO_ROOT / persisted.get("report_path", "")
    if not persisted.get("report_path") or not persisted_path.exists():
        findings.append("numeric sanity report was not persisted by default writer")

    return {
        "ok": not findings,
        "backend": "sympy",
        "style": "sympy_physics_derivation_trace",
        "phase": "phase12_numeric_sanity_counterexamples_regime_sampling",
        "findings": findings,
        "case_count": len(CASES),
        "observed_constraint_kinds": observed_constraints,
        "counterexample_schema_probe_passed": bool(counterexample)
        and not missing_counterexample_fields,
        "numeric_sanity_report_path": persisted.get("report_path"),
    }


def main() -> int:
    """Serve as the command-line entry point for the Phase 12 validation check."""
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
