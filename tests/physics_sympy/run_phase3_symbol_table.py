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

"""Check Phase 3 symbol-table, quantity-semantics, and binding discipline."""

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
    PHYSICS_SYMBOL_DIAGNOSTIC_CODES,
    PHYSICS_SYMBOL_KINDS,
    build_physics_symbol_table,
)

CASES = [
    "constant_acceleration_position",
    "simple_harmonic_oscillator_period",
    "work_energy_constant_force",
    "rc_discharge",
    "ideal_gas_density",
    "projectile_range_level_ground",
    "formalphysics_0000",
]


def run_check() -> Dict[str, Any]:
    """Validate typed symbol tables and binding diagnostics."""
    findings: List[str] = []
    reports = [build_physics_symbol_table(case_id) for case_id in CASES]
    kind_union = set()
    diagnostic_union = set()
    for report in reports:
        if not report["ok"]:
            findings.append(f"symbol table has binding errors for {report['case_id']}")
        if set(report["symbol_kinds"]) != set(PHYSICS_SYMBOL_KINDS):
            findings.append(f"symbol kinds mismatch for {report['case_id']}")
        if set(report["diagnostic_checklist"]) != set(PHYSICS_SYMBOL_DIAGNOSTIC_CODES):
            findings.append(f"diagnostic checklist mismatch for {report['case_id']}")
        stable_ids = [entry["stable_id"] for entry in report["symbol_table"]]
        if len(stable_ids) != len(set(stable_ids)):
            findings.append(f"duplicate stable symbol ids for {report['case_id']}")
        for entry in report["symbol_table"]:
            kind_union.add(entry["symbol_kind"])
            if (
                entry["generated_support"]
                and entry["source_backing"] == "source_backed"
            ):
                findings.append(
                    f"generated support entry is source-backed: {entry['stable_id']}"
                )
            if (
                entry["symbol_kind"] == "generated_dummy_variable"
                and not entry["generated_support"]
            ):
                findings.append(
                    f"dummy variable not marked generated support: {entry['stable_id']}"
                )
            if entry["symbol_kind"] == "unit_or_dimension" and not entry["dimension"]:
                findings.append(
                    f"unit/dimension entry missing dimension map: {entry['stable_id']}"
                )
        diagnostic_union.update(item["code"] for item in report["binding_diagnostics"])
    missing_kinds = sorted(set(PHYSICS_SYMBOL_KINDS).difference(kind_union))
    if missing_kinds:
        findings.append(f"symbol kinds not observed across test cases: {missing_kinds}")
    if "ambiguous_constant_notation" not in diagnostic_union:
        findings.append("ambiguous constant diagnostic was not exercised")
    if "overloaded_notation_across_corpus" not in diagnostic_union:
        findings.append("overloaded notation diagnostic was not exercised")
    if "implicit_function_of_time_omitted_in_display" not in diagnostic_union:
        findings.append("implicit function-of-time diagnostic was not exercised")
    return {
        "ok": not findings,
        "backend": "sympy",
        "style": "sympy_physics_derivation_trace",
        "phase": "phase3_symbol_table_quantity_semantics_binding_discipline",
        "findings": findings,
        "case_count": len(reports),
        "observed_symbol_kinds": sorted(kind_union),
        "observed_diagnostic_codes": sorted(diagnostic_union),
        "kind_counts": {report["case_id"]: report["kind_counts"] for report in reports},
        "diagnostic_counts": {
            report["case_id"]: report["diagnostic_counts"] for report in reports
        },
    }


def main() -> int:
    """Serve as the command-line entry point for the Phase 3 symbol-table check."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = run_check()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"ok: {report['ok']}")
        print(f"case_count: {report['case_count']}")
        print(f"findings: {len(report['findings'])}")
    return 0 if report["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
