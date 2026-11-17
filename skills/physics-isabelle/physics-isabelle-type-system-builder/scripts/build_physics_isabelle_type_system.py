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

"""Build an Isabelle/HOL-facing physics type-system packet."""

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
                r"\\mathbf|\\vec|\\times|cross|vector|component|projection",
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
        "has_integrals": bool(
            re.search(r"\\int|\\oint|\\iiint|\\oiint|integral", source, re.I)
        ),
        "has_operators": bool(
            re.search(
                r"\\hat|\\ket|\\bra|\\braket|commutator|Hamiltonian|operator|TDSE|Schr[oö]dinger",
                source,
                re.I,
            )
        ),
        "has_coordinate_frames": bool(
            re.search(
                r"Cartesian|cylindrical|spherical|coordinate|component|projection|basis|frame|"
                r"\b[xyz][-_ ]?(?:axis|component|coordinate)\b",
                source,
                re.I,
            )
        ),
        "has_time_derivatives": bool(
            re.search(r"\\partial_t|\\partial t|dt|\\dot|time", source, re.I)
        ),
    }


def recommended_imports(features: dict[str, bool]) -> list[str]:
    """Document the responsibility of ``recommended_imports``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``recommended_imports`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    imports = ["Complex_Main"]
    if (
        features["has_vectors"]
        or features["has_fields"]
        or features["has_integrals"]
        or features["has_time_derivatives"]
        or features["has_operators"]
    ):
        imports.append("HOL-Analysis.Analysis")
    return list(dict.fromkeys(imports))


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

    def add_once(
        *,
        requirement_id: str,
        kind: str,
        target: str,
        preferred_surface: str,
        isabelle_search_terms: list[str],
        dependencies: list[str] | None = None,
    ) -> None:
        """Document the responsibility of ``infer_background_requirements.add_once``.

        Motivation:
            Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

        Intent:
            Provide the local operation named ``infer_background_requirements.add_once`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        if any(item["id"] == requirement_id for item in requirements):
            return
        requirements.append(
            {
                "id": requirement_id,
                "kind": kind,
                "target": target,
                "preferred_surface": preferred_surface,
                "formalization_status": "needs_autoformalization",
                "support_status": "isabelle_hol_backed_or_generated_support",
                "required_before": "target_theorem",
                "dependencies": dependencies or [],
                "isabelle_search_terms": isabelle_search_terms,
            }
        )

    if features["has_vectors"] or features["has_fields"]:
        add_once(
            requirement_id="bg.isabelle_vector_carrier_and_projection",
            kind="definition",
            target="Choose the Isabelle/HOL vector carrier and projection bridge used by the physics theorem.",
            preferred_surface="'a::euclidean_space, real ^ 'n, inner, norm, and coordinate projection functions from HOL-Analysis.",
            isabelle_search_terms=[
                "euclidean_space",
                "inner",
                "norm",
                "real ^",
                "basis",
                "cartesian_basis",
            ],
        )
    if features["has_fields"]:
        add_once(
            requirement_id="bg.isabelle_field_carrier",
            kind="definition",
            target="Represent scalar or vector fields as functions over an Isabelle/HOL topological or Euclidean carrier.",
            preferred_surface="'x::euclidean_space => real or 'x::euclidean_space => 'y::real_normed_vector with continuous_on / has_derivative assumptions.",
            isabelle_search_terms=[
                "continuous_on",
                "has_derivative",
                "euclidean_space",
                "field",
            ],
            dependencies=["bg.isabelle_vector_carrier_and_projection"],
        )
    if (
        features["has_time_derivatives"]
        or features["has_integrals"]
        or re.search(
            r"derivative|differentiat|smooth|\\partial|\\dot|chain rule|product rule",
            source,
            re.I,
        )
    ):
        add_once(
            requirement_id="bg.isabelle_calculus_rules",
            kind="background_result",
            target="Formalize or reuse derivative, chain-rule, product-rule, and integral facts needed by the derivation.",
            preferred_surface="DERIV, has_derivative, has_vector_derivative, continuous_on, integrable_on, and integral from HOL-Analysis.",
            isabelle_search_terms=[
                "DERIV",
                "has_derivative",
                "has_vector_derivative",
                "derivative_eq_intros",
                "integral",
            ],
        )
    if features["has_operators"]:
        add_once(
            requirement_id="bg.isabelle_operator_inner_product_surface",
            kind="definition",
            target="Represent quantum/operator statements with Isabelle/HOL complex scalars, inner products, and bounded/linear operator assumptions when available.",
            preferred_surface="complex, inner, norm, bounded_linear, linear, and matrix/vector spaces from Complex_Main/HOL-Analysis.",
            isabelle_search_terms=[
                "complex",
                "inner",
                "bounded_linear",
                "linear",
                "operator",
                "Hamiltonian",
            ],
        )
    if re.search(
        r"unit|dimension|meter|metre|second|kilogram|newton|joule|charge|mass|force|energy|\\hbar|Hamiltonian",
        source,
        re.I,
    ):
        add_once(
            requirement_id="bg.isabelle_unit_dimension_homogeneity",
            kind="bridge_lemma",
            target="Provide dimension/unit homogeneity obligations for each physics transformation.",
            preferred_surface="typed locale assumptions or generated-support bridge lemmas; local dimension records only as blocked fallback.",
            isabelle_search_terms=["dimension", "unit", "homogeneous", "quantity"],
        )
    if re.search(
        r"law|newton|maxwell|lagrange|lorentz|hamilton|constitutive|TDSE|Schr[oö]dinger",
        source,
        re.I,
    ):
        add_once(
            requirement_id="bg.isabelle_source_law_support",
            kind="background_result",
            target="Encode named physical-law substitutions as source-backed support lemmas or locale assumptions.",
            preferred_surface="named Isabelle lemma/theorem/locale assumption with source_backed or generated_support label.",
            isabelle_search_terms=["law", "Maxwell", "Hamilton", "Lagrange", "Lorentz"],
        )
    if re.search(
        r"solve|rearrange|substitut|cancel|simplif|derive|show that|=", source, re.I
    ):
        add_once(
            requirement_id="bg.isabelle_algebraic_core",
            kind="background_result",
            target="Extract a compact reusable algebraic core theorem and prove the physics-rich theorem by calling it.",
            preferred_surface="Isabelle simp/algebra_simps/ring-compatible real or complex equation lemma.",
            isabelle_search_terms=["algebra_simps", "field_simps", "simp", "ring"],
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
    imports = recommended_imports(features)
    background_requirements = infer_background_requirements(source, features)
    return {
        "case_id": case_id,
        "style": "isabelle_physics_type_system_packet",
        "backend": "isabelle",
        "base_dimensions": BASE_DIMENSIONS,
        "feature_flags": features,
        "recommended_imports": imports,
        "library_grounding_target": {
            "status": "maximal_isabelle_hol_native_first",
            "completion_threshold": "high",
            "preferred_library_sources": [
                "Complex_Main",
                "HOL-Analysis.Analysis",
                "locally installed Isabelle/HOL theories found by isarmathlib-grounding-navigator",
                "optional local IsarMathLib theories only when an existing .thy file is cited",
            ],
            "preferred_surfaces": [
                "real and complex scalars from Complex_Main",
                "'a::euclidean_space or real ^ 'n vector carriers",
                "inner, norm, dist, continuous_on, DERIV, has_derivative, has_vector_derivative",
                "bounded_linear or linear operator assumptions",
                "locales/contexts with typed fixes and Prop assumptions",
                "compact algebraic core lemmas proved with simp/algebra_simps/field_simps before the physics wrapper theorem",
            ],
            "fallback_policy": [
                "local quantity, dimension, law, or context records are draft-only fallback scaffolds",
                "raw real scalar equations are accepted only as explicit projections from a native carrier",
                "missing installed theory support must be recorded as a dependency blocker rather than silently replaced by an empty formalism",
            ],
            "block_complete_if": [
                "no Isabelle/HOL native surface is selected for a physics-bearing source",
                "a local record/type synonym replaces an available HOL-Analysis carrier",
                "context is encoded only as strings or bool flags without typed Prop assumptions",
                "required background definitions or laws remain unformalized",
            ],
        },
        "isabelle_surfaces": {
            "scalar": "real and complex from Complex_Main",
            "finite_vector": "real ^ 'n and 'a::euclidean_space from HOL-Analysis",
            "inner_norm": "inner x y, norm x, dist x y",
            "field": "'x::euclidean_space => real or 'x::euclidean_space => 'y::real_normed_vector",
            "calculus": "DERIV f x :> y, (f has_derivative f') (at x within S), has_vector_derivative, continuous_on",
            "linear_operator": "bounded_linear T, linear T, matrix/vector functions over real or complex carriers",
            "physics_context": "locale/context with typed fixes and assumes clauses; labels record source-backed/generated-support status",
            "source_law": "named lemma/theorem/locale assumption with explicit source anchor or generated-support note",
            "algebraic_core": "separate lemma over real/complex projections, then physics wrapper theorem calls it",
        },
        "fallback_surfaces": {
            "dimension_records": "allowed only as blocked/draft bridge when no native carrier or reusable local library declaration exists",
            "raw_scalars": "allowed only as scalar projection conclusions with a declared projection bridge",
            "bool_flags": "allowed only as commentary labels; complete status requires corresponding typed assumptions where semantically relevant",
        },
        "typing_policy": [
            "Search Isabelle/HOL, HOL-Analysis, and available IsarMathLib theories before introducing local physics wrappers.",
            "Dimensioned quantities should be represented by native carriers plus unit/dimension homogeneity obligations before any local dimension record is considered.",
            "Vector and field claims should use 'a::euclidean_space, real ^ 'n, function spaces, inner/norm, and explicit projection bridges.",
            "Calculus claims should use DERIV/has_derivative/has_vector_derivative/continuous_on whenever possible.",
            "Operator algebra should use complex scalars, inner products, bounded_linear/linear assumptions, and source-backed operator laws.",
            "Raw real scalar reductions must be marked as projections from native physics carriers and backed by a compact algebraic core theorem.",
        ],
        "background_formalization_requirements": {
            "policy": "autoformalize or Isabelle-reuse intermediate definitions and background results before accepting the target theorem",
            "requirements": background_requirements,
            "completion_gate": [
                "every requirement is formalized, Isabelle/HOL reused, MathformerPhysicsLib reused, explicitly blocked, or not_required",
                "no background result is target-shaped",
                "target theorem calls support declarations rather than assuming the final equation",
            ],
        },
        "required_obligations": [
            "quantity_binding_complete",
            "dimension_assignment_complete_or_blocked",
            "unit_policy_declared",
            "frame_projection_policy_declared",
            "source_law_or_generated_support_for_each_physics_step",
            "isabelle_locale_or_context_for_nontrivial_assumptions",
        ],
        "forbidden_patterns": [
            "target_equation_as_assumption",
            "sorry_or_oops_in_complete_status",
            "raw_real_only_physics_without_projection_bridge",
            "unlabeled_generated_operator_law",
            "local_record_substitute_for_available_HOL_Analysis_surface",
            "string_only_or_bool_only_context_for_physics_assumptions",
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
    parser.add_argument("--case-id", default="physics_isabelle_case")
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
        "A vector force field in Cartesian coordinates has units."
        if args.self_test
        else read_source(args.source_file, args.source_text)
    )
    packet = build_packet(source, args.case_id)
    if args.self_test:
        assert packet["backend"] == "isabelle"
        assert packet["feature_flags"]["has_vectors"]
        assert "Complex_Main" in packet["recommended_imports"]
        assert "HOL-Analysis.Analysis" in packet["recommended_imports"]
        assert (
            packet["library_grounding_target"]["status"]
            == "maximal_isabelle_hol_native_first"
        )
        assert any(
            item["id"] == "bg.isabelle_vector_carrier_and_projection"
            for item in packet["background_formalization_requirements"]["requirements"]
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
