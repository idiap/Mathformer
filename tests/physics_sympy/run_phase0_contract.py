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

"""Check the Phase 0 contract for physics SymPy derivation traces."""

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
    PHYSICS_SYMPY_COMPLETENESS_CRITERIA,
    classify_physics_sympy_completion,
    physics_sympy_phase0_contract,
)


def criterion_validation(value: bool) -> Dict[str, bool]:
    """Return a validation map keyed by all Phase 0 completion criteria."""
    return {
        str(criterion["validation_key"]): value
        for criterion in PHYSICS_SYMPY_COMPLETENESS_CRITERIA
        if "validation_key" in criterion
    }


def run_check() -> Dict[str, Any]:
    """Validate the style, scope, artifact contract, and completion statuses."""
    contract = physics_sympy_phase0_contract()
    required_domains = {
        "single_particle_kinematics",
        "newtonian_point_mass_dynamics",
        "harmonic_oscillator_derivations",
        "elementary_energy_work_derivations",
        "idealized_circuit_ode_derivations",
        "elementary_thermodynamic_identity_manipulations",
    }
    deferred_domains = {
        "tensor_calculus_general_relativity",
        "continuum_mechanics",
        "gauge_field_derivations",
        "quantum_noncommuting_operator_algebra",
        "stochastic_differential_physics",
    }
    criteria = {
        "source_preservation",
        "source_equation_exposure",
        "implicit_step_expansion",
        "generated_support_marking",
        "context_declaration",
        "unit_dimension_analysis",
        "target_chain_validation",
        "artifact_realness",
    }
    findings: List[str] = []
    if contract["style"] != "sympy_physics_derivation_trace":
        findings.append("backend style is not sympy_physics_derivation_trace")
    if contract["distinct_from"] != "sympy_equational_trace":
        findings.append(
            "physics derivation style is not explicitly distinct from sympy_equational_trace"
        )
    if {item["id"] for item in contract["initial_target_domains"]} != required_domains:
        findings.append("initial target domain set does not match Phase 0 scope")
    if {item["id"] for item in contract["deferred_domains"]} != deferred_domains:
        findings.append("deferred domain set does not match Phase 0 scope")
    if {item["id"] for item in contract["complete_artifact_criteria"]} != criteria:
        findings.append("complete artifact criteria do not match Phase 0 contract")
    status_keys = set(contract["completion_statuses"])
    if status_keys != {"complete", "draft", "blocked"}:
        findings.append("completion status set must be exactly complete/draft/blocked")

    complete = classify_physics_sympy_completion(criterion_validation(True))
    draft_validation = criterion_validation(True)
    draft_validation["numeric_sanity_no_counterexample"] = False
    draft = classify_physics_sympy_completion(draft_validation)
    blocked_validation = criterion_validation(True)
    blocked_validation["all_equations_dimensionally_consistent"] = False
    blocked = classify_physics_sympy_completion(blocked_validation)
    if complete["status"] != "complete":
        findings.append("all-passing validation does not classify as complete")
    if draft["status"] != "draft":
        findings.append("non-hard unresolved validation does not classify as draft")
    if blocked["status"] != "blocked":
        findings.append("dimension inconsistency does not classify as blocked")

    return {
        "ok": not findings,
        "backend": "sympy",
        "style": contract["style"],
        "phase": "phase0_scope_contract_completion_semantics",
        "findings": findings,
        "contract": contract,
        "classification_examples": {
            "complete": complete,
            "draft": draft,
            "blocked": blocked,
        },
    }


def main() -> int:
    """Serve as the command-line entry point for the Phase 0 contract check."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = run_check()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"ok: {report['ok']}")
        print(f"style: {report['style']}")
        print(f"findings: {len(report['findings'])}")
    return 0 if report["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
