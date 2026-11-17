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

"""Check Phase 8 physical-law and SymPy API grounding."""

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
    PHYSICS_LAW_GROUNDING_TEMPLATES,
    PHYSICS_SYMPY_OPERATION_GROUNDINGS,
    build_physics_law_api_grounding_packet,
)

CASES = [
    "constant_acceleration_position",
    "simple_harmonic_oscillator_omega",
    "work_energy_constant_force",
    "rc_discharge",
    "ideal_gas_density",
    "projectile_range_level_ground",
    "formalphysics_0000",
    "formalphysics_0172",
    "formalphysics_0026",
]


REQUIRED_LAW_TEMPLATE_IDS = {
    "newton_second_law",
    "hooke_law",
    "work_energy_relation",
    "conservation_mechanical_energy",
    "ohm_law",
    "capacitor_relation",
    "ideal_gas_law",
    "first_law_thermodynamics_sign_convention",
}


REQUIRED_OPERATION_IDS = {
    "solve",
    "solveset",
    "dsolve",
    "integrate",
    "Integral",
    "diff",
    "Derivative",
    "simplify",
    "expand",
    "factor",
    "cancel",
    "subs",
    "vector_dot_cross",
    "unit_conversion_dimension_simplification",
}


def run_check() -> Dict[str, Any]:
    """Validate the Phase 8 law/API grounding packet over representative cases."""
    findings: List[str] = []
    reports = [build_physics_law_api_grounding_packet(case_id) for case_id in CASES]
    catalog_law_ids = {item["id"] for item in PHYSICS_LAW_GROUNDING_TEMPLATES}
    catalog_operation_ids = {item["id"] for item in PHYSICS_SYMPY_OPERATION_GROUNDINGS}
    observed_law_templates = set()
    observed_operation_ids = set()
    observed_backing = set()

    missing_law_catalog = sorted(REQUIRED_LAW_TEMPLATE_IDS.difference(catalog_law_ids))
    if missing_law_catalog:
        findings.append(f"missing required law templates: {missing_law_catalog}")
    missing_operation_catalog = sorted(
        REQUIRED_OPERATION_IDS.difference(catalog_operation_ids)
    )
    if missing_operation_catalog:
        findings.append(
            f"missing required SymPy operation groundings: {missing_operation_catalog}"
        )

    for report in reports:
        if not report["ok"]:
            findings.append(
                f"law/API grounding packet is not ok for {report['case_id']}"
            )
        if not report["grounding_summary"]["law_and_api_surfaces_are_distinct"]:
            findings.append(
                f"law/API surfaces are not distinct for {report['case_id']}"
            )
        if report["completion_blocked"]:
            findings.append(
                f"completion should not be blocked by Phase 8 grounding for {report['case_id']}"
            )
        if report["law_uses_without_provenance"]:
            findings.append(
                f"law use without provenance for {report['case_id']}: {report['law_uses_without_provenance']}"
            )
        if report["missing_operation_groundings"]:
            findings.append(
                f"missing operation grounding for {report['case_id']}: {report['missing_operation_groundings']}"
            )
        for operation in report["operation_api_catalog"]:
            if (
                operation["id"] in REQUIRED_OPERATION_IDS
                and operation["status"] != "grounded"
            ):
                findings.append(
                    f"required operation is not grounded: {operation['id']}"
                )
        for law in report["law_groundings"]:
            observed_backing.add(law["source_backing"])
            if not law.get("justification"):
                findings.append(f"law grounding missing justification: {law['id']}")
            if law.get("template_id") in REQUIRED_LAW_TEMPLATE_IDS:
                observed_law_templates.add(law["template_id"])
        for use in report["operation_uses"]:
            observed_operation_ids.add(use["operation_id"])
            if use["grounding_family"] != "mathematical_operation_api":
                findings.append(f"operation use should stay in API family: {use['id']}")

    for required_observed in [
        "hooke_law",
        "work_energy_relation",
        "ohm_law",
        "capacitor_relation",
        "ideal_gas_law",
    ]:
        if required_observed not in observed_law_templates:
            findings.append(
                f"representative cases did not observe law template {required_observed}"
            )
    for required_observed in [
        "solve",
        "integrate",
        "diff",
        "subs",
        "simplify",
        "vector_dot_cross",
    ]:
        if required_observed not in observed_operation_ids:
            findings.append(
                f"representative cases did not observe operation {required_observed}"
            )
    if "source_backed" not in observed_backing:
        findings.append("no source-backed law grounding observed")
    if "generated_support" not in observed_backing:
        findings.append("no generated-support law grounding observed")

    persisted = build_physics_law_api_grounding_packet(
        "rc_discharge", write_default_report=True
    )
    persisted_path = REPO_ROOT / persisted.get("report_path", "")
    if not persisted.get("report_path") or not persisted_path.exists():
        findings.append("law/API grounding packet was not persisted by default writer")

    return {
        "ok": not findings,
        "backend": "sympy",
        "style": "sympy_physics_derivation_trace",
        "phase": "phase8_physics_law_and_api_grounding",
        "findings": findings,
        "case_count": len(CASES),
        "law_template_catalog_count": len(catalog_law_ids),
        "operation_catalog_count": len(catalog_operation_ids),
        "observed_law_templates": sorted(observed_law_templates),
        "observed_operation_ids": sorted(observed_operation_ids),
        "observed_source_backing": sorted(observed_backing),
        "law_api_grounding_packet_path": persisted.get("report_path"),
    }


def main() -> int:
    """Serve as the command-line entry point for the Phase 8 grounding check."""
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
