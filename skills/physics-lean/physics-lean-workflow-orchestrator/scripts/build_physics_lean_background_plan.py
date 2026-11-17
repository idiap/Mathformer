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

"""Build background-definition and support-result obligations for Lean physics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any, Sequence


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
        content = path.read_text(encoding="utf-8")
        if path.suffix == ".lean":
            header = re.search(r"/-!.*?-/", content, re.S)
            if header:
                return header.group(0)
        return content
    return ""


def load_json(path: Path | None) -> dict[str, Any]:
    """Document the responsibility of ``load_json``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if path is None:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_raw(path: Path | None, text: str | None) -> str:
    """Document the responsibility of ``read_raw``.

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


def has(pattern: str, source: str) -> bool:
    """Document the responsibility of ``has``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``has`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return bool(re.search(pattern, source, re.I | re.S))


def add_item(
    items: list[dict[str, Any]],
    *,
    item_id: str,
    kind: str,
    statement: str,
    support_status: str,
    mathlib_search_terms: list[str],
    required_before: str = "target_theorem",
    dependencies: list[str] | None = None,
) -> None:
    """Document the responsibility of ``add_item``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``add_item`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    items.append(
        {
            "id": item_id,
            "kind": kind,
            "statement": statement,
            "support_status": support_status,
            "formalization_status": "needs_autoformalization",
            "target_backend": "Lean",
            "required_before": required_before,
            "dependencies": dependencies or [],
            "mathlib_search_terms": mathlib_search_terms,
            "acceptance_gates": [
                "source anchor or generated-support note present",
                "Mathlib reuse attempted before local definition",
                "Lean declaration compiles before target theorem depends on it",
                "semantic reviewer confirms the declaration is not target-shaped",
            ],
        }
    )


def add_items_from_roles(items: list[dict[str, Any]], roles: set[str]) -> None:
    """Document the responsibility of ``add_items_from_roles``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``add_items_from_roles`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    existing = {item["id"] for item in items}

    def add_once(
        *,
        item_id: str,
        kind: str,
        statement: str,
        support_status: str,
        mathlib_search_terms: list[str],
        dependencies: list[str] | None = None,
    ) -> None:
        """Document the responsibility of ``add_items_from_roles.add_once``.

        Motivation:
            Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

        Intent:
            Provide the local operation named ``add_items_from_roles.add_once`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        if item_id in existing:
            return
        add_item(
            items,
            item_id=item_id,
            kind=kind,
            statement=statement,
            support_status=support_status,
            mathlib_search_terms=mathlib_search_terms,
            dependencies=dependencies,
        )
        existing.add(item_id)

    if "mathlib_vector_surface" in roles:
        add_once(
            item_id="bg.vector_carrier_and_projection",
            kind="definition",
            statement="Choose the Mathlib-native vector carrier and component projection API used by the physics theorem.",
            support_status="mathlib_backed",
            mathlib_search_terms=[
                "EuclideanSpace Real (Fin n)",
                "PiLp",
                "Fin component projection",
            ],
        )
    if "field_definition" in roles:
        add_once(
            item_id="bg.field_carrier",
            kind="definition",
            statement="Represent scalar or vector fields as functions into Mathlib scalar/vector carriers with explicit smoothness assumptions.",
            support_status="generated_support",
            mathlib_search_terms=[
                "HasFDerivAt",
                "Differentiable",
                "ContDiff",
                "EuclideanSpace",
            ],
        )
    if "calculus_support" in roles:
        add_once(
            item_id="bg.calculus_rules",
            kind="background_result",
            statement="Formalize or reuse the derivative/product/chain-rule facts needed by the displayed derivation steps.",
            support_status="mathlib_backed",
            mathlib_search_terms=[
                "deriv_add",
                "deriv_mul",
                "HasDerivAt",
                "HasFDerivAt",
                "ContDiff",
            ],
        )
    if "source_law_support" in roles:
        add_once(
            item_id="bg.source_law_support",
            kind="background_result",
            statement="Encode named physical law substitutions as source-backed support declarations.",
            support_status="source_backed",
            mathlib_search_terms=[
                "physical law support lemma",
                "constitutive equation",
                "source law",
            ],
            dependencies=["bg.calculus_rules"] if "calculus_support" in roles else [],
        )
    if "unit_dimension_bridge" in roles:
        add_once(
            item_id="bg.unit_dimension_homogeneity",
            kind="bridge_lemma",
            statement="Provide dimension/unit homogeneity obligations for every transformation used by the target derivation.",
            support_status="generated_support",
            mathlib_search_terms=[
                "dimension analysis",
                "units",
                "homogeneous equation",
            ],
        )
    if "algebraic_core" in roles:
        add_once(
            item_id="bg.algebraic_core",
            kind="background_result",
            statement="Extract the reusable algebraic rearrangement core theorem and prove the physics theorem by calling it.",
            support_status="source_backed_or_generated_support",
            mathlib_search_terms=["ring", "linarith", "nlinarith", "field_simp"],
        )
    if "operator_surface" in roles:
        add_once(
            item_id="bg.operator_and_inner_product_surface",
            kind="definition",
            statement="Represent Hilbert/module state vectors, operators, adjoints, and inner products on Mathlib-native linear algebra surfaces.",
            support_status="mathlib_backed",
            mathlib_search_terms=[
                "InnerProductSpace",
                "LinearMap",
                "Matrix.Hermitian",
                "IsSelfAdjoint",
            ],
        )


def grounding_roles_from_expansion(expansion_packet: dict[str, Any]) -> set[str]:
    """Document the responsibility of ``grounding_roles_from_expansion``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``grounding_roles_from_expansion`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    roles: set[str] = set()
    summary_roles = expansion_packet.get("expected_grounding_summary", {}).get(
        "roles", []
    )
    if isinstance(summary_roles, list):
        roles.update(str(role) for role in summary_roles)
    for step in expansion_packet.get("steps", []):
        if isinstance(step, dict) and isinstance(
            step.get("expected_grounding_roles"), list
        ):
            roles.update(str(role) for role in step["expected_grounding_roles"])
    roles.discard("source_alignment")
    return roles


def infer_background_items(
    source: str, type_packet: dict[str, Any]
) -> list[dict[str, Any]]:
    """Document the responsibility of ``infer_background_items``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``infer_background_items`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    items: list[dict[str, Any]] = []
    features = type_packet.get("feature_flags", {}) if type_packet else {}
    source_has_vector = bool(features.get("has_vectors")) or has(
        r"\\vec|\\mathbf|vector|component|projection|cross|\\times", source
    )
    source_has_field = bool(features.get("has_fields")) or has(
        r"(?<!\{)\bfield\b|potential|gradient|curl|divergence|\\nabla|electric field|magnetic field",
        source,
    )
    source_has_operator = bool(features.get("has_operators")) or has(
        r"hamiltonian|operator|\\hat|\\ket|\\bra|tdse|schr[oö]dinger|inner product",
        source,
    )
    source_has_lagrangian = has(
        r"lagrangian|euler.?lagrange|least action|action functional", source
    )
    source_has_lorentz = has(
        r"lorentz|electric field|magnetic field|electromagnetic|A_x|A_y|A_z|\\phi",
        source,
    )
    source_has_derivative = bool(features.get("has_time_derivatives")) or has(
        r"derivative|differentiat|smooth|\\partial|\\dot|d/dt|chain rule|product rule",
        source,
    )
    source_has_units = has(
        r"unit|dimension|meter|metre|second|kilogram|newton|joule|charge|mass|force|energy|\\hbar|hamiltonian",
        source,
    )

    if source_has_vector:
        add_item(
            items,
            item_id="bg.vector_carrier_and_projection",
            kind="definition",
            statement="Choose the Mathlib-native vector carrier and component projection API used by the physics theorem.",
            support_status="mathlib_backed",
            mathlib_search_terms=[
                "EuclideanSpace Real (Fin n)",
                "PiLp",
                "Fin component projection",
            ],
        )
    if source_has_field:
        add_item(
            items,
            item_id="bg.field_carrier",
            kind="definition",
            statement="Represent scalar or vector fields as functions into Mathlib scalar/vector carriers with explicit smoothness assumptions.",
            support_status="generated_support",
            mathlib_search_terms=[
                "HasFDerivAt",
                "Differentiable",
                "ContDiff",
                "EuclideanSpace",
            ],
        )
    if source_has_derivative:
        add_item(
            items,
            item_id="bg.calculus_rules",
            kind="background_result",
            statement="Formalize or reuse the derivative/product/chain-rule facts needed by the displayed derivation steps.",
            support_status="mathlib_backed",
            mathlib_search_terms=[
                "deriv_add",
                "deriv_mul",
                "HasDerivAt",
                "HasFDerivAt",
                "ContDiff",
            ],
        )
    if source_has_lorentz:
        add_item(
            items,
            item_id="bg.em_field_definitions",
            kind="definition",
            statement="Define the electric and magnetic field component identities from electromagnetic potentials before using Lorentz-force algebra.",
            support_status="source_backed",
            mathlib_search_terms=[
                "curl",
                "EuclideanSpace Real (Fin 3)",
                "deriv",
                "fderiv",
            ],
            dependencies=[
                "bg.vector_carrier_and_projection",
                "bg.field_carrier",
                "bg.calculus_rules",
            ],
        )
    if source_has_lagrangian:
        add_item(
            items,
            item_id="bg.euler_lagrange_law",
            kind="background_result",
            statement="Encode the Euler-Lagrange equation, the relevant partial derivative identities, and the force projection used by the derivation.",
            support_status="source_backed",
            mathlib_search_terms=[
                "Euler Lagrange",
                "deriv",
                "HasDerivAt",
                "Lagrangian",
            ],
            dependencies=["bg.calculus_rules"],
        )
    if source_has_operator:
        add_item(
            items,
            item_id="bg.operator_and_inner_product_surface",
            kind="definition",
            statement="Represent Hilbert/module state vectors, operators, adjoints, and inner products on Mathlib-native linear algebra surfaces.",
            support_status="mathlib_backed",
            mathlib_search_terms=[
                "InnerProductSpace",
                "LinearMap",
                "Matrix.Hermitian",
                "IsSelfAdjoint",
            ],
        )
        add_item(
            items,
            item_id="bg.quantum_evolution_identities",
            kind="background_result",
            statement="Formalize or source-label the TDSE/operator substitution identities used before the final algebraic rearrangement.",
            support_status="source_backed",
            mathlib_search_terms=["LinearMap", "inner product", "deriv", "Complex"],
            dependencies=["bg.operator_and_inner_product_surface", "bg.calculus_rules"],
        )
    if source_has_units:
        add_item(
            items,
            item_id="bg.unit_dimension_homogeneity",
            kind="bridge_lemma",
            statement="Provide dimension/unit homogeneity obligations for every transformation used by the target derivation.",
            support_status="generated_support",
            mathlib_search_terms=[
                "dimension analysis",
                "units",
                "homogeneous equation",
            ],
        )
    if has(r"solve|rearrange|substitut|cancel|simplif|derive|show that|=", source):
        add_item(
            items,
            item_id="bg.algebraic_core",
            kind="background_result",
            statement="Extract the reusable algebraic rearrangement core theorem and prove the physics theorem by calling it.",
            support_status="source_backed_or_generated_support",
            mathlib_search_terms=["ring", "linarith", "nlinarith", "field_simp"],
        )
    return items


def lean_evidence_for_item(item_id: str, lean_text: str) -> tuple[str, list[str]]:
    """Document the responsibility of ``lean_evidence_for_item``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``lean_evidence_for_item`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if not lean_text:
        return "needs_autoformalization", []
    checks: dict[str, tuple[str, list[str], list[str]]] = {
        "bg.vector_carrier_and_projection": (
            "mathlib_reused",
            ["EuclideanSpace", "Fin", "Module Real V", "→ₗ[Real]"],
            ["Mathlib-native finite vector carrier and component projection present"],
        ),
        "bg.field_carrier": (
            "formalized",
            ["→", "Differentiable"],
            ["field/function carrier and typed smoothness support present"],
        ),
        "bg.field_carrier_and_smoothness": (
            "formalized",
            ["→", "Differentiable"],
            ["field/function carrier and typed smoothness support present"],
        ),
        "bg.calculus_rules": (
            "mathlib_reused",
            ["LinearMap.map_add", "Differentiable"],
            ["Mathlib linear/calculus support is visible in Lean"],
        ),
        "bg.em_field_definitions": (
            "formalized",
            ["electromagnetic_field_definition_support", "hEx", "hBy", "hBz"],
            [
                "electric and magnetic component definitions are exposed as source support"
            ],
        ),
        "bg.euler_lagrange_law": (
            "formalized",
            ["euler_lagrange_source_law_support", "hEL"],
            ["Euler-Lagrange source-law support is exposed"],
        ),
        "bg.source_law_support": (
            "formalized",
            ["source_law_support", "hAmp"],
            ["source-law support declarations or named source hypotheses are exposed"],
        ),
        "bg.unit_dimension_homogeneity": (
            "formalized",
            ["UnitDimensionCompatible", "unit_dimension_bridge"],
            ["unit/dimension bridge declaration is present"],
        ),
        "bg.unit_dimension_bridge": (
            "formalized",
            ["UnitDimensionCompatible", "unit_dimension_bridge"],
            ["unit/dimension bridge declaration is present"],
        ),
        "bg.algebraic_core": (
            "formalized",
            ["algebra_core", "ring", "linarith"],
            ["reusable algebraic core theorem is present"],
        ),
    }
    status, needles, evidence = checks.get(item_id, ("needs_autoformalization", [], []))
    if needles and any(needle in lean_text for needle in needles):
        return status, evidence
    return "needs_autoformalization", []


def close_items_from_lean(
    items: list[dict[str, Any]], lean_text: str
) -> list[dict[str, Any]]:
    """Document the responsibility of ``close_items_from_lean``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``close_items_from_lean`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    closed = []
    for item in items:
        updated = dict(item)
        status, evidence = lean_evidence_for_item(str(item.get("id", "")), lean_text)
        if status != "needs_autoformalization":
            updated["formalization_status"] = status
            updated["formalization_evidence"] = evidence
        closed.append(updated)
    return closed


def build_plan(
    source: str,
    case_id: str,
    type_packet: dict[str, Any],
    expansion_packet: dict[str, Any] | None = None,
    lean_text: str = "",
) -> dict[str, Any]:
    """Document the responsibility of ``build_plan``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    items = infer_background_items(source, type_packet)
    expansion_roles = grounding_roles_from_expansion(expansion_packet or {})
    add_items_from_roles(items, expansion_roles)
    priority = {
        "bg.vector_carrier_and_projection": 10,
        "bg.field_carrier": 20,
        "bg.operator_and_inner_product_surface": 25,
        "bg.calculus_rules": 30,
        "bg.em_field_definitions": 40,
        "bg.euler_lagrange_law": 50,
        "bg.quantum_evolution_identities": 55,
        "bg.source_law_support": 60,
        "bg.unit_dimension_homogeneity": 70,
        "bg.algebraic_core": 80,
    }
    items = sorted(items, key=lambda item: (priority.get(item["id"], 999), item["id"]))
    items = close_items_from_lean(items, lean_text)
    open_items = [
        item
        for item in items
        if str(item.get("formalization_status", "needs_autoformalization"))
        not in {
            "formalized",
            "mathlib_reused",
            "mathformer_reused",
            "blocked",
            "not_required",
            "complete",
        }
    ]
    return {
        "style": "physics_lean_background_dependency_plan",
        "case_id": case_id,
        "status": (
            "needs_autoformalization"
            if open_items
            else "complete" if items else "not_required"
        ),
        "background_items": items,
        "dependency_order": [item["id"] for item in items],
        "steering_sources": {
            "source_text_heuristics": bool(source),
            "type_packet_features": bool(type_packet),
            "informal_expansion_grounding_roles": sorted(expansion_roles),
        },
        "integration_policy": {
            "declaration_order": [
                "imports",
                "module informal/commentary header",
                "namespace",
                "Mathlib-native definitions or reused imports",
                "generated-support definitions with source notes",
                "background lemmas and bridge lemmas",
                "compact algebraic core theorem",
                "physics-rich target theorem",
            ],
            "reuse_policy": "Search Mathlib and existing MathformerPhysicsLib declarations before creating local definitions.",
            "blocking_rule": "The target theorem cannot be complete while any required background item is needs_autoformalization, unresolved, or target-shaped.",
            "monotonicity": [
                "formalize prerequisites before editing the target theorem",
                "preserve source anchors and generated-support labels on support declarations",
                "never replace a proved support lemma with a stronger target-shaped assumption",
            ],
        },
    }


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
    parser.add_argument("--type-packet", type=Path)
    parser.add_argument("--expansion-packet", type=Path)
    parser.add_argument("--lean-file", type=Path)
    parser.add_argument("--lean-text")
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
        "Use the Euler-Lagrange equation for a charged particle in electromagnetic "
        "potentials to derive the Lorentz force component with units."
        if args.self_test
        else read_source(args.source_file, args.source_text)
    )
    type_packet = (
        {
            "feature_flags": {
                "has_vectors": True,
                "has_fields": True,
                "has_time_derivatives": True,
            }
        }
        if args.self_test
        else load_json(args.type_packet)
    )
    expansion_packet = (
        {
            "expected_grounding_summary": {
                "roles": [
                    "mathlib_vector_surface",
                    "field_definition",
                    "calculus_support",
                    "algebraic_core",
                ]
            }
        }
        if args.self_test
        else load_json(args.expansion_packet)
    )
    lean_text = (
        "EuclideanSpace Differentiable algebra_core"
        if args.self_test
        else read_raw(args.lean_file, args.lean_text)
    )
    plan = build_plan(source, args.case_id, type_packet, expansion_packet, lean_text)
    if args.self_test:
        ids = set(plan["dependency_order"])
        assert plan["status"] in {"complete", "needs_autoformalization"}
        assert "bg.vector_carrier_and_projection" in ids
        assert "bg.em_field_definitions" in ids
        assert "bg.algebraic_core" in ids
        assert (
            "mathlib_vector_surface"
            in plan["steering_sources"]["informal_expansion_grounding_roles"]
        )
        quantum_plan = build_plan(
            r"Let $\\hat{H}$ satisfy the TDSE for $|\\Psi\\rangle$.",
            "quantum_self_test",
            {"feature_flags": {"has_operators": True}},
            {
                "expected_grounding_summary": {
                    "roles": [
                        "operator_surface",
                        "calculus_support",
                        "source_law_support",
                        "unit_dimension_bridge",
                        "algebraic_core",
                    ]
                }
            },
        )
        quantum_ids = set(quantum_plan["dependency_order"])
        assert "bg.operator_and_inner_product_surface" in quantum_ids
        assert "bg.vector_carrier_and_projection" not in quantum_ids
    text = json.dumps(plan, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
