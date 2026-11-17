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

"""Check Phase 13 reference-free physics consistency reporting."""

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
    consistency_report,
)  # noqa: E402

CASES = [
    "constant_acceleration_position",
    "rc_discharge",
    "projectile_range_level_ground",
    "formalphysics_0000",
    "formalphysics_0172",
]

REQUIRED_PACKET_KEYS = {
    "source",
    "symbols",
    "dimensions",
    "units",
    "equations",
    "regimes",
    "frames",
    "expanded",
    "laws",
    "plan",
    "generated_artifact",
    "execution",
    "unit_analysis",
    "step_verification",
    "numeric_sanity",
}

REQUIRED_RFDE_METRICS = {
    "source_anchor_coverage",
    "equation_parse_coverage",
    "quantity_binding_completeness",
    "dimension_consistency",
    "unit_grounding_density",
    "law_grounding_density",
    "implicit_gap_closure",
    "step_executability",
    "assumption_regime_fidelity",
    "coordinate_frame_explicitness",
    "target_derivation_success",
    "artifact_realness",
}

REQUIRED_VALIDATION_KEYS = {
    "all_source_targets_represented",
    "all_required_gaps_closed",
    "all_derivation_steps_execute",
    "all_equations_dimensionally_consistent",
    "target_expression_computed_from_steps",
    "no_critical_blockers",
}


def run_check() -> Dict[str, Any]:
    """Validate Phase 13 report coverage over representative cases."""
    findings: List[str] = []
    reports = [consistency_report(case_id) for case_id in CASES]
    for report in reports:
        if not report["ok"]:
            findings.append(
                f"consistency report is not ok for {report['case_id']}: {report['blockers']}"
            )
        if report["phase"] != "phase13_reference_free_physics_consistency_report":
            findings.append(
                f"wrong phase label for {report['case_id']}: {report['phase']}"
            )
        if report["status"] != "complete":
            findings.append(
                f"expected complete status for {report['case_id']}: {report['status']}"
            )
        if report["critical_blockers"]:
            findings.append(
                f"unexpected critical blockers for {report['case_id']}: {report['critical_blockers']}"
            )
        if report["aggregate_reference_free_score"] < 1.0:
            findings.append(
                f"unexpected reference-free score for {report['case_id']}: {report['aggregate_reference_free_score']}"
            )
        missing_packets = REQUIRED_PACKET_KEYS - set(report["packets"])
        if missing_packets:
            findings.append(
                f"missing aggregate packets for {report['case_id']}: {sorted(missing_packets)}"
            )
        false_inventory = [
            key for key, ok in report["packet_inventory"].items() if not ok
        ]
        if false_inventory:
            findings.append(
                f"packet inventory not complete for {report['case_id']}: {false_inventory}"
            )
        missing_metrics = REQUIRED_RFDE_METRICS - set(report["physics_rfde_metrics"])
        if missing_metrics:
            findings.append(
                f"missing RFDE metrics for {report['case_id']}: {sorted(missing_metrics)}"
            )
        nonunit_metrics = {
            key: value
            for key, value in report["physics_rfde_metrics"].items()
            if value != 1.0
        }
        if nonunit_metrics:
            findings.append(
                f"nonpassing RFDE metrics for {report['case_id']}: {nonunit_metrics}"
            )
        missing_metric_evidence = REQUIRED_RFDE_METRICS - set(report["metric_evidence"])
        if missing_metric_evidence:
            findings.append(
                f"missing metric evidence labels for {report['case_id']}: {sorted(missing_metric_evidence)}"
            )
        missing_validation = REQUIRED_VALIDATION_KEYS - set(
            report["validation_criteria"]
        )
        if missing_validation:
            findings.append(
                f"missing validation criteria for {report['case_id']}: {sorted(missing_validation)}"
            )
        failed_validation = [
            key for key, ok in report["validation_criteria"].items() if not ok
        ]
        if failed_validation:
            findings.append(
                f"failed validation criteria for {report['case_id']}: {failed_validation}"
            )
        if not report["artifact_inventory"]["realness_ok"]:
            findings.append(
                f"artifact realness failed for {report['case_id']}: {report['artifact_inventory']}"
            )
        if (
            not report["derivation_graph"]["nodes"]
            or not report["derivation_graph"]["edges"]
        ):
            findings.append(f"derivation graph is empty for {report['case_id']}")

    persisted = consistency_report("rc_discharge", write_default_report=True)
    persisted_path = REPO_ROOT / persisted.get("report_path", "")
    if not persisted.get("report_path") or not persisted_path.exists():
        findings.append(
            "physics consistency report was not persisted by default writer"
        )

    return {
        "ok": not findings,
        "backend": "sympy",
        "style": "sympy_physics_derivation_trace",
        "phase": "phase13_reference_free_physics_consistency_report",
        "findings": findings,
        "case_count": len(CASES),
        "required_packet_count": len(REQUIRED_PACKET_KEYS),
        "required_rfde_metric_count": len(REQUIRED_RFDE_METRICS),
        "required_validation_count": len(REQUIRED_VALIDATION_KEYS),
        "physics_consistency_report_path": persisted.get("report_path"),
    }


def main() -> int:
    """Serve as the command-line entry point for the Phase 13 validation check."""
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
