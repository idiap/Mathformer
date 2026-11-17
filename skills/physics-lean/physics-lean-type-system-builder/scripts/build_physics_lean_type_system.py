#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.
#
# Intent:
#   Tell coding agents what context to load, what invariants to preserve, and how to validate their work.
#
# Function:
#   Contains skill instructions, prompts, references, and scripts used by Codex-style workflows.
#
# Maintenance Notes:
#   Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.

"""Build a Lean-facing physics type-system packet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any, Sequence

BASE_DIMENSIONS = ["M", "L", "T", "I", "Theta", "N", "J"]


def infer_features(source: str) -> dict[str, bool]:
    """Document the responsibility of ``infer_features``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``infer_features`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return {
        "has_vectors": bool(
            re.search(
                r"\\mathbf|\\vec|\\times|cross|component|projection|vector",
                source,
                re.I,
            )
        ),
        "has_fields": bool(
            re.search(
                r"\\nabla|(?<!\{)\bfield\b|potential|curl|divergence|gradient|electric field|magnetic field",
                source,
                re.I,
            )
        ),
        "has_integrals": bool(re.search(r"\\int|\\oint|\\iiint|\\oiint", source)),
        "has_operators": bool(
            re.search(
                r"\\hat|\\ket|\\bra|\\braket|commutator|Hamiltonian|operator|self-adjoint|Hermitian|TDSE|Schr[oö]dinger|inner product",
                source,
                re.I,
            )
        ),
        "has_coordinate_frames": bool(
            re.search(
                r"Cartesian|spherical|cylindrical|coordinate|component|projection|basis|frame|"
                r"\b[xyzr][-_ ]?(?:axis|component|coordinate)\b|theta|\\theta|\\varphi",
                source,
                re.I,
            )
        ),
        "has_time_derivatives": bool(
            re.search(r"\\partial t|dt|\\dot|time", source, re.I)
        ),
    }


def infer_background_requirements(
    source: str, features: dict[str, bool]
) -> list[dict[str, Any]]:
    """Document the responsibility of ``infer_background_requirements``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``infer_background_requirements`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    requirements: list[dict[str, Any]] = []

    def add(
        requirement_id: str,
        kind: str,
        description: str,
        status: str,
        depends_on: list[str] | None = None,
    ) -> None:
        """Document the responsibility of ``infer_background_requirements.add``.

        Motivation:
            Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

        Intent:
            Provide the local operation named ``infer_background_requirements.add`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        requirements.append(
            {
                "id": requirement_id,
                "kind": kind,
                "description": description,
                "source_status": status,
                "formalization_status": "needs_autoformalization",
                "depends_on": depends_on or [],
            }
        )

    source_lower = source.lower()
    if features["has_vectors"] or features["has_fields"]:
        add(
            "bg.vector_carrier_and_projection",
            "definition",
            "Mathlib-native vector carrier and component projection used by the theorem surface.",
            "mathlib_backed",
        )
    if features["has_fields"]:
        add(
            "bg.field_carrier_and_smoothness",
            "definition",
            "Field carrier plus smoothness/differentiability assumptions for derivatives appearing in the source.",
            "generated_support",
            ["bg.vector_carrier_and_projection"] if features["has_vectors"] else [],
        )
    if (
        features["has_time_derivatives"]
        or "\\partial" in source
        or "derivative" in source_lower
    ):
        add(
            "bg.calculus_support",
            "background_result",
            "Derivative, product-rule, chain-rule, or partial-derivative facts needed by the informal transitions.",
            "mathlib_backed",
        )
    if re.search(
        r"euler.?lagrange|lagrangian|lorentz|maxwell|tdse|schrodinger|hamilton",
        source,
        re.I,
    ):
        add(
            "bg.source_law_support",
            "background_result",
            "Source-law support lemmas for the physical law substitutions used before the final algebraic step.",
            "source_backed",
            ["bg.calculus_support"] if requirements else [],
        )
    if re.search(
        r"unit|dimension|force|mass|charge|velocity|energy|current|Hamiltonian|\\hbar",
        source,
        re.I,
    ):
        add(
            "bg.unit_dimension_bridge",
            "bridge_lemma",
            "Unit/dimension homogeneity bridge obligations for each physics transformation.",
            "generated_support",
        )
    if re.search(r"derive|show that|solve|rearrange|substitut|cancel|=", source, re.I):
        add(
            "bg.algebraic_core",
            "background_result",
            "Reusable algebraic core theorem that the physics-rich theorem calls.",
            "source_backed_or_generated_support",
        )
    return requirements


def build_packet(source: str, case_id: str) -> dict[str, Any]:
    """Document the responsibility of ``build_packet``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    features = infer_features(source)
    background_requirements = infer_background_requirements(source, features)
    recommended_imports = [
        "Mathlib.Tactic",
        "Mathlib.Analysis.Calculus.Deriv.Basic",
        "Mathlib.Analysis.Calculus.FDeriv.Basic",
        "Mathlib.Data.Real.Basic",
    ]
    if features["has_vectors"] or features["has_fields"]:
        recommended_imports.extend(
            [
                "Mathlib.Analysis.InnerProductSpace.PiL2",
                "Mathlib.Analysis.InnerProductSpace.Projection.Basic",
                "Mathlib.Data.Fin.VecNotation",
            ]
        )
    if features["has_integrals"]:
        recommended_imports.append("Mathlib.MeasureTheory.Integral.Bochner.Basic")
    if features["has_operators"]:
        recommended_imports.extend(
            [
                "Mathlib.Data.Complex.Basic",
                "Mathlib.LinearAlgebra.Matrix.Hermitian",
                "Mathlib.Analysis.InnerProductSpace.LinearMap",
                "Mathlib.Analysis.Complex.Exponential",
            ]
        )

    return {
        "case_id": case_id,
        "style": "lean_physics_type_system_packet",
        "base_dimensions": BASE_DIMENSIONS,
        "feature_flags": features,
        "recommended_imports": sorted(set(recommended_imports)),
        "mathlib_grounding_target": {
            "status": "maximal_mathlib_native_first",
            "minimum_complete_level": "high",
            "local_wrapper_policy": "fallback_only_with_explicit_blocker_or_abstraction_boundary",
            "forbidden_for_complete_without_waiver": [
                "locally declared scalar wrapper as the only quantity surface",
                "locally declared finite-vector wrapper as the only vector surface",
                "opaque dimension markers standing in for physical semantics",
                "String-valued context or source-law labels as theorem evidence",
                "raw Real scalar theorem without Mathlib-typed projection bridge",
            ],
        },
        "background_formalization_requirements": {
            "status": (
                "needs_autoformalization" if background_requirements else "not_required"
            ),
            "policy": "formalize or Mathlib-reuse intermediate definitions and background results before the target theorem is accepted",
            "requirements": background_requirements,
            "required_order": [item["id"] for item in background_requirements],
            "complete_status_requires": [
                "every requirement is formalized, Mathlib-reused, or explicitly blocked",
                "support declarations compile before the target theorem depends on them",
                "no support lemma is target-shaped",
                "source-backed and generated-support labels are preserved",
            ],
        },
        "lean_surfaces": {
            "scalar_core": "Real only inside compact algebraic core lemmas or explicit scalar projections",
            "finite_vector": "EuclideanSpace Real (Fin n)",
            "component_projection": "(v : EuclideanSpace Real (Fin n)) (i : Fin n) ↦ v i",
            "vector_field": "X -> EuclideanSpace Real (Fin 3)",
            "linear_operator": "V ->ₗ[Real] V",
            "time_derivative": "HasDerivAt, HasFDerivAt, Differentiable, or ContDiff assumptions",
            "operator_quantum": "Matrix n n Complex, V ->ₗ[Complex] V, inner-product/module surfaces",
            "source_law": "typed Prop assumptions or structures whose fields are propositions, not String labels",
            "fallback_dimension_boundary": "local dimension tags only when no Mathlib-compatible carrier exists, and only with an explicit blocker/waiver",
        },
        "fallback_surfaces": {
            "dimension": "legacy dimension-tag record with SI exponent fields",
            "scalar_carrier": "legacy scalar wrapper over Real",
            "finite_vector_carrier": "legacy finite-vector wrapper over Fin-indexed Real components",
            "context_carrier": "legacy typed-Prop context carrier",
        },
        "typing_policy": [
            "Start from Mathlib-native spaces, maps, calculus predicates, and linear algebra structures.",
            "Use local scalar or vector wrappers only as a documented fallback, not as the primary complete surface.",
            "Coordinate scalar projections may use Real only with a projection lemma from a Mathlib-native vector/field.",
            "Fields should expose domain, codomain module/vector type, smoothness assumptions, and frame.",
            "Operator algebra may be abstract, but commutator/bilinearity assumptions must use typed maps or matrices when available.",
        ],
        "required_obligations": [
            "background_definitions_and_results_formalized_or_blocked",
            "mathlib_native_surface_complete_or_blocked",
            "quantity_binding_complete",
            "dimension_assignment_complete_or_blocked",
            "unit_policy_declared",
            "frame_and_projection_policy_declared",
            "source_law_or_generated_support_for_each_physics_step",
        ],
        "forbidden_patterns": [
            "target_equation_as_hypothesis",
            "axiom_for_final_claim",
            "unformalized_background_dependency_used_by_target",
            "background_result_identical_to_target",
            "all_quantities_erased_to_raw_reals_without_projection_lemmas",
            "local_quantity_wrappers_count_as_maximal_grounding",
            "opaque_dimensions_or_string_context_as_final_evidence",
            "regime_assumption_without_source_or_generated_support_note",
        ],
    }


def read_source(path: Path | None, text: str | None) -> str:
    """Document the responsibility of ``read_source``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if text is not None:
        return text
    if path is not None:
        return path.read_text(encoding="utf-8")
    return ""


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Document the responsibility of ``parse_args``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Parse caller-provided input into the structured representation expected by downstream code.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-file", type=Path)
    parser.add_argument("--source-text")
    parser.add_argument("--case-id", default="physics_lean_case")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Document the responsibility of ``main``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Serve as the command-line entry point and coordinate argument parsing, execution, and reporting.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    args = parse_args(argv)
    source = (
        "F_x = q E_x + q (v \\times B)_x"
        if args.self_test
        else read_source(args.source_file, args.source_text)
    )
    packet = build_packet(source, args.case_id)
    if args.self_test:
        assert packet["feature_flags"]["has_vectors"]
        assert "target_equation_as_hypothesis" in packet["forbidden_patterns"]
        assert (
            packet["mathlib_grounding_target"]["status"]
            == "maximal_mathlib_native_first"
        )
        assert "EuclideanSpace Real (Fin n)" in packet["lean_surfaces"]["finite_vector"]
        assert (
            packet["background_formalization_requirements"]["status"]
            == "needs_autoformalization"
        )
        assert (
            "bg.algebraic_core"
            in packet["background_formalization_requirements"]["required_order"]
        )
        quantum_packet = build_packet(
            r"Let $\\hat{H}$ satisfy the TDSE for $|\\Psi\\rangle$.",
            "quantum_self_test",
        )
        assert quantum_packet["feature_flags"]["has_operators"]
        assert not quantum_packet["feature_flags"]["has_vectors"]
    text = json.dumps(packet, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
