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

"""Review final physics hypotheses for a Lean physics derivation."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Sequence

PHYSICAL_TERMS = [
    "force",
    "mass",
    "acceleration",
    "velocity",
    "energy",
    "momentum",
    "charge",
    "current",
    "field",
    "unit",
    "dimension",
    "meter",
    "metre",
    "second",
    "kilogram",
    "newton",
    "joule",
]

VECTOR_TERMS = [
    "vector",
    "field",
    "gradient",
    "curl",
    "divergence",
    "cross",
    "\\vec",
    "\\times",
]
FRAME_TERMS = [
    "frame",
    "coordinate",
    "basis",
    "inertial",
    "observer",
    "gauge",
    "sign convention",
]
LAW_TERMS = [
    "newton",
    "maxwell",
    "lagrange",
    "hamilton",
    "conservation",
    "law",
    "constitutive",
]
ASSUMPTION_TERMS = [
    "positive",
    "nonzero",
    "differentiable",
    "smooth",
    "integrable",
    "boundary",
    "initial",
    "approximation",
    "ideal",
    "regime",
]

BACKGROUND_SOURCE_TERMS = [
    "define",
    "definition",
    "where",
    "given by",
    "euler",
    "lagrange",
    "lorentz",
    "maxwell",
    "hamilton",
    "tdse",
    "schrodinger",
    "operator",
    "potential",
    "partial",
    "derivative",
    "product rule",
    "chain rule",
    "projection",
    "component",
]

MATHLIB_NATIVE_SURFACE_TERMS = [
    "EuclideanSpace",
    "LinearMap",
    "ContinuousLinearMap",
    "Matrix",
    "InnerProductSpace",
    "NormedSpace",
    "Module",
    "HasDerivAt",
    "HasFDerivAt",
    "Differentiable",
    "ContDiff",
    "deriv",
    "fderiv",
    "Hermitian",
    "IsSelfAdjoint",
    "IsUnitary",
]

MATHLIB_VECTOR_SURFACE_TERMS = [
    "EuclideanSpace",
    "LinearMap",
    "ContinuousLinearMap",
    "Matrix",
    "InnerProductSpace",
    "NormedSpace",
]

LOCAL_SCAFFOLD_TERMS = [
    "Quantity",
    "VectorQuantity",
    "PhysicsContext",
    "SourceLaw",
    "SmoothPotentialContext",
    "PhysDim",
]

FOUNDATION_BRIDGE_SCAFFOLD_TERMS = [
    "PhysicsContext",
]

MATHFORMER_FOUNDATION_SUPPORT_TERMS = [
    "FourierIntegrationByPartsGrounding",
    "fourierIntegrationByPartsFromGrounding",
    "fourierPositionIntegral",
    "fourierDerivativeIntegral",
    "fourierWindowIntegral",
    "UnitDimensionCompatible",
    "unit_dimension_bridge",
    "FourierIntegrationByPartsEvidence",
    "fourierIntegrationByPartsResult",
    "fluctuationKet",
    "fluctuationNormSquared",
    "transitionAmplitude",
    "probabilityFromAmplitude",
    "probabilityFromAmplitude_apply",
    "probabilityFromAmplitude_congr",
    "TwoLevelRabiStateExpansion",
    "VacuumRabiAmplitude",
    "transitionAmplitude_from_twoLevelRabiStateExpansion",
    "vacuumRabiAmplitude_apply",
    "complex_normSq_neg_I_mul_real",
    "norm_neg_I_mul_real_sq",
    "probabilityFromAmplitude_neg_I_mul_real",
    "probabilityFromVacuumRabiAmplitude",
    "bornProbabilityFromVacuumRabiTransitionAmplitude",
    "vacuumRabiProbabilityFromStateExpansion",
    "hilbertOperatorCommutator",
    "hilbertCommutatorExpectation",
    "UnboundedHilbertOperator",
    "restrictToSubmodule",
    "HasDenseDomain",
    "IsClosedUnboundedOperator",
    "SymmetricUnboundedOperator",
    "SelfAdjointUnboundedOperatorWitness",
    "CommonInvariantCore",
    "PositionMomentumPair",
    "commutatorValueOnCore",
    "canonicalCommutatorExpectationOnNormalizedCore",
    "RealSchwartzWavefunction",
    "realSchwartzDerivative",
    "SchwartzL2PositionMomentumModel",
    "canonicalCommutatorExpectationOnSchwartzCore",
    "RealLineL2Wavefunction",
    "realSchwartzToL2",
    "realSchwartzToL2_apply_ae",
    "realSchwartzL2RangeSubmodule",
    "realSchwartzToL2_mem_rangeSubmodule",
    "realSchwartzL2RangeSubmodule_coe",
    "RealLineL2SchwartzRangeSubmoduleDense",
    "realSchwartzRangeSubmoduleDense_of_denseRange",
    "RealLineL2CoreEqualsSchwartzRangeSubmodule",
    "RealLineL2CoreEqualsSchwartzRangeSubmodule.of_set_range",
    "realLineL2CoreIsSchwartzRange_of_submodule_eq",
    "realLineL2CoreDense_of_rangeSubmodule",
    "RealLineMomentumActionIsDerivative",
    "RealLineSchwartzCommutatorAction",
    "RealLineSchwartzCanonicalCommutator",
    "RealLineSchwartzCanonicalCommutatorAsSchwartzMap",
    "realLineSchwartzCanonicalCommutatorAsSchwartzMap_of_pointwise",
    "realLineSchwartzCanonicalCommutator_of_schwartzMap",
    "realLineMomentumActionIsDerivative",
    "RealLineL2PositionMomentumModel",
    "RealLineL2PositionMomentumModel.common_core_eq_schwartz_range_submodule",
    "RealLinePositionRestrictedToSchwartzCore",
    "RealLineMomentumRestrictedToSchwartzCore",
    "RealLinePositionRestrictedToSchwartzCore_hasDenseDomain",
    "RealLineMomentumRestrictedToSchwartzCore_hasDenseDomain",
    "RealLinePositionSchwartzGraphCoreTarget",
    "RealLineMomentumSchwartzGraphCoreTarget",
    "RealLinePositionEssentialSelfAdjointOnSchwartzCoreTarget",
    "RealLineMomentumEssentialSelfAdjointOnSchwartzCoreTarget",
    "RealLinePositionSpectralCalculusAvailable",
    "RealLineMomentumSpectralCalculusAvailable",
    "RealLineL2ClosureFrontier",
    "RealLineSchwartzCommutatorTransport",
    "realLineSchwartzCommutatorTransport_from_actions",
    "RealLineSchwartzCanonicalCommutatorTransported",
    "realLineSchwartzCanonicalCommutatorTransported_of_transport",
    "realLineSchwartzCanonicalCommutatorTransported_of_pointwise",
    "realLineSchwartzCanonicalCommutatorTransported_of_schwartzMap",
    "RealLinePositionEssentialSelfAdjointTarget",
    "realLinePositionEssentialSelfAdjointTarget",
    "RealLineMomentumEssentialSelfAdjointTarget",
    "realLineMomentumEssentialSelfAdjointTarget",
    "RealLinePositionSpectralCalculusTarget",
    "RealLineMomentumSpectralCalculusTarget",
    "RealLineL2SpectralClosureTargets",
    "canonicalCommutatorExpectationOnRealLineL2SchwartzCore",
    "real_line_l2_schwartz_range_submodule_witness",
    "real_line_l2_schwartz_range_submodule_dense_witness",
    "real_line_l2_schwartz_range_dense_from_model",
    "real_line_l2_common_core_is_schwartz_range",
    "real_line_l2_common_core_dense_from_model",
    "real_line_position_coordinate_multiplication",
    "real_line_momentum_derivative_action",
    "real_line_position_action_matches_l2_embedding",
    "real_line_momentum_action_matches_l2_embedding",
    "real_line_schwartz_pointwise_commutator_witness",
    "real_line_schwartz_commutator_transport_from_actions",
    "real_line_schwartz_canonical_commutator_transported_from_transport",
    "real_line_schwartz_canonical_commutator_transported_from_pointwise",
    "real_line_schwartz_canonical_commutator_transported_witness",
    "real_line_position_essential_self_adjoint_target",
    "real_line_momentum_essential_self_adjoint_target",
    "real_line_l2_spectral_closure_targets",
    "real_line_position_spectral_target_from_packet",
    "real_line_momentum_spectral_target_from_packet",
    "real_line_transport_and_spectral_frontier_handoff",
    "real_line_l2_common_core_eq_schwartz_range_submodule",
    "real_line_schwartz_commutator_as_schwartz_map_from_pointwise",
    "real_line_schwartz_pointwise_commutator_from_schwartz_map",
    "real_line_schwartz_canonical_commutator_transported_from_schwartz_map",
    "real_line_position_restricted_to_schwartz_core",
    "real_line_momentum_restricted_to_schwartz_core",
    "real_line_position_restricted_to_schwartz_core_dense",
    "real_line_momentum_restricted_to_schwartz_core_dense",
    "real_line_position_graph_core_witness",
    "real_line_momentum_graph_core_witness",
    "diracImaginaryQuotient",
    "diracImaginaryQuotient_from_commutator_expectation",
    "diracImaginaryQuotient_conjugate_lower_bound",
    "diracImaginaryQuotient_star_lower_bound",
    "diracImaginaryQuotient_star_eq_im",
    "diracImaginaryQuotient_eq_im_of_conjugate",
    "diracImaginaryQuotient_sq_eq_im_sq_of_conjugate",
    "transitionAmplitude_conjugate_symmetry",
    "innerNormSquared_le_normSquared_mul_normSquared",
    "heisenbergVarianceProductBoundFromInnerLower",
    "heisenbergSquaredBoundFromVarianceIdentities",
    "heisenbergBoundFromSquaredLowerBound",
    "heisenbergBoundFromLowerBound",
    "parameterizedHilbertExpectation",
    "parameterizedHilbertExpectation_apply",
    "derivativeEqOfEventuallyEq",
    "energyDerivativeEqExpectationDerivative",
    "ParameterizedEigenstateEquation",
    "EigenstateExpectationIdentityNear",
    "parameterizedHilbertExpectation_eq_eigenvalue_of_eigenstate",
    "energy_eq_parameterizedExpectation_near_of_eigenstate",
    "DifferentiatedEigenstateEquation",
    "hellmannFeynmanDerivativeFromDifferentiatedEigenEquation",
    "PositionWavefunction",
    "positionExpectationIntegrand",
    "positionExpectationIntegrand_apply",
    "PositionResolutionIdentityMeasureKernel",
    "PositionMeasurementSpaceFrontier",
    "PositionBornDensityIntegrable",
    "PositionBornProbabilityNormalization",
    "PositionExpectationIntegrable",
    "positionBornDensity",
    "positionExpectationFromMeasurementSpace",
    "positionExpectationIntegral",
    "positionExpectationIntegral_apply",
    "PositionVarianceBornEvidence",
    "positionVarianceBornFormula",
    "HeisenbergEquationEvidence",
    "HeisenbergSourceLaw",
    "heisenbergEquationOfMotion",
    "heisenberg_calculus_product_rule_support",
    "heisenberg_source_law_support",
    "heisenberg_unit_dimension_bridge",
    "heisenberg_equation_position_mathlib_grounded",
    "commutator",
]


def read_text(path: Path | None, inline: str | None) -> str:
    """Document the responsibility of ``read_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if inline is not None:
        return inline
    if path is None:
        return ""
    return path.read_text(encoding="utf-8")


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


def has_any(text: str, terms: Sequence[str]) -> bool:
    """Document the responsibility of ``has_any``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``has_any`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    lower = text.lower()
    return any(term.lower() in lower for term in terms)


def add_finding(
    findings: list[dict[str, Any]],
    *,
    severity: str,
    code: str,
    message: str,
    repair_surface: str,
) -> None:
    """Document the responsibility of ``add_finding``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Search available candidates and return the matches needed by the caller.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    findings.append(
        {
            "severity": severity,
            "code": code,
            "message": message,
            "repair_surface": repair_surface,
        }
    )


def packet_text(packet: dict[str, Any]) -> str:
    """Document the responsibility of ``packet_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``packet_text`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return json.dumps(packet, ensure_ascii=False).lower() if packet else ""


def packet_raw_text(packet: dict[str, Any]) -> str:
    """Document the responsibility of ``packet_raw_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``packet_raw_text`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return json.dumps(packet, ensure_ascii=False) if packet else ""


def strip_lean_comments(lean_text: str) -> str:
    """Document the responsibility of ``strip_lean_comments``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``strip_lean_comments`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    without_blocks = re.sub(r"/-!?.*?-/", "", lean_text, flags=re.S)
    return re.sub(r"--.*", "", without_blocks)


def module_header_comment(lean_text: str) -> str:
    """Document the responsibility of ``module_header_comment``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``module_header_comment`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    lines = lean_text.splitlines()
    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped or stripped.startswith("import "):
            index += 1
            continue
        break
    if index >= len(lines) or not lines[index].lstrip().startswith("/-!"):
        return ""
    collected = []
    while index < len(lines):
        collected.append(lines[index])
        if "-/" in lines[index]:
            break
        index += 1
    return "\n".join(collected)


def count_terms(text: str, terms: Sequence[str]) -> int:
    """Document the responsibility of ``count_terms``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``count_terms`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return sum(len(re.findall(rf"\b{re.escape(term)}\b", text)) for term in terms)


def count_local_scaffolds(lean_code: str, type_packet: dict[str, Any]) -> int:
    """Document the responsibility of ``count_local_scaffolds``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``count_local_scaffolds`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return count_terms(lean_code, LOCAL_SCAFFOLD_TERMS) + count_terms(
        packet_raw_text(type_packet), LOCAL_SCAFFOLD_TERMS
    )


def has_mathformer_foundation_bridge_surface(
    lean_code: str, type_packet: dict[str, Any], assumption_packet: dict[str, Any]
) -> bool:
    """Return whether local context wrappers are backed by accepted foundations."""
    combined = (
        lean_code
        + "\n"
        + packet_raw_text(type_packet)
        + "\n"
        + packet_raw_text(assumption_packet)
    )
    return (
        count_mathlib_native_surfaces(combined) > 0
        and has_typed_prop_context(lean_code)
        and count_terms(combined, MATHFORMER_FOUNDATION_SUPPORT_TERMS) > 0
    )


def count_unresolved_local_scaffolds(
    *,
    lean_code: str,
    type_packet: dict[str, Any],
    assumption_packet: dict[str, Any],
) -> int:
    """Count local scaffolds that are not explicit MathformerPhysicsLib bridges."""
    raw_count = count_local_scaffolds(lean_code, type_packet)
    if not has_mathformer_foundation_bridge_surface(
        lean_code, type_packet, assumption_packet
    ):
        return raw_count
    bridge_text = lean_code + "\n" + packet_raw_text(type_packet)
    bridge_count = count_terms(bridge_text, FOUNDATION_BRIDGE_SCAFFOLD_TERMS)
    return max(0, raw_count - bridge_count)


def count_mathlib_native_surfaces(text: str) -> int:
    """Document the responsibility of ``count_mathlib_native_surfaces``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``count_mathlib_native_surfaces`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return count_terms(text, MATHLIB_NATIVE_SURFACE_TERMS)


def count_mathlib_vector_surfaces(text: str) -> int:
    """Document the responsibility of ``count_mathlib_vector_surfaces``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``count_mathlib_vector_surfaces`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return count_terms(text, MATHLIB_VECTOR_SURFACE_TERMS)


def count_opaque_dimension_surfaces(lean_code: str) -> int:
    """Document the responsibility of ``count_opaque_dimension_surfaces``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``count_opaque_dimension_surfaces`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return len(
        re.findall(
            r"^\s*opaque\s+\w*(?:Dim|Dimension|Charge|Force|Velocity|Field|Energy|Mass|Length|Time)\w*\s*:\s*Type\b",
            lean_code,
            re.M,
        )
    )


def count_string_context_surfaces(lean_code: str) -> int:
    """Document the responsibility of ``count_string_context_surfaces``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``count_string_context_surfaces`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return len(re.findall(r":\s*String\b", lean_code)) + len(
        re.findall(r'=\s*"[^"]*(?:source|generated|frame|smooth|law)', lean_code, re.I)
    )


def has_typed_prop_context(lean_code: str) -> bool:
    """Document the responsibility of ``has_typed_prop_context``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``has_typed_prop_context`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    predicate_pattern = (
        r"\b(HasDerivAt|HasFDerivAt|Differentiable|ContDiff|IsSelfAdjoint|Hermitian|IsUnitary|LinearMap|"
        r"ContinuousLinearMap|InnerProductSpace|CompleteSpace|NormedAddCommGroup|PhysicalLawWitness|"
        r"DimensionCompatible|UnitDimensionCompatible|PhysicsContext|NormalizedStateWitness|NeZero|NoZeroSMulDivisors|forall)\b"
    )
    return bool(
        re.search(predicate_pattern, lean_code)
        or re.search(r"(^|[\s(:])0\s*[<≤]", lean_code)
    )


def mathlib_grounding_level(
    *,
    lean_code: str,
    type_packet: dict[str, Any],
    assumption_packet: dict[str, Any],
) -> str:
    """Document the responsibility of ``mathlib_grounding_level``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``mathlib_grounding_level`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    combined = (
        lean_code
        + "\n"
        + packet_raw_text(type_packet)
        + "\n"
        + packet_raw_text(assumption_packet)
    )
    native_count = count_mathlib_native_surfaces(combined)
    local_count = count_unresolved_local_scaffolds(
        lean_code=lean_code,
        type_packet=type_packet,
        assumption_packet=assumption_packet,
    )
    opaque_count = count_opaque_dimension_surfaces(lean_code)
    string_count = count_string_context_surfaces(lean_code)
    typed_context = has_typed_prop_context(lean_code)
    if (
        native_count > 0
        and local_count == 0
        and opaque_count == 0
        and string_count == 0
        and typed_context
    ):
        return "high"
    if native_count > 0:
        return "medium"
    return "low"


def background_items(
    background_packet: dict[str, Any], type_packet: dict[str, Any]
) -> list[dict[str, Any]]:
    """Document the responsibility of ``background_items``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``background_items`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    items = background_packet.get("background_items", []) if background_packet else []
    if isinstance(items, list) and items:
        return [item for item in items if isinstance(item, dict)]
    requirements = type_packet.get("background_formalization_requirements", {}).get(
        "requirements", []
    )
    if isinstance(requirements, list):
        return [item for item in requirements if isinstance(item, dict)]
    return []


def open_background_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Document the responsibility of ``open_background_items``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``open_background_items`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    closed = {
        "formalized",
        "mathlib_reused",
        "mathformer_reused",
        "blocked",
        "not_required",
        "complete",
    }
    open_items = []
    for item in items:
        status = str(item.get("formalization_status", "needs_autoformalization"))
        if status not in closed:
            open_items.append(item)
    return open_items


def background_item_closed_by_lean(item: dict[str, Any], lean_code: str) -> bool:
    """Return whether a background obligation is visibly discharged in Lean."""
    item_id = str(item.get("id", ""))
    if item_id in {"bg.calculus_support", "bg.calculus_rules"}:
        return bool(
            re.search(
                r"\b(HasDerivAt|Differentiable|deriv|heisenberg_calculus_product_rule_support|"
                r"product_rule_derivative|ladder_number_no_calculus_rule_required|"
                r"MeasureTheory|positionExpectationIntegral|positionSecondMomentIntegral|"
                r"position_variance_mean_integral_support|"
                r"position_variance_second_moment_integral_support)\b",
                lean_code,
            )
        )
    if item_id == "bg.source_law_support":
        return bool(
            re.search(
                r"\b(SourceLaw|Law|law|HeisenbergSourceLaw|heisenberg_source_law_support|"
                r"heisenbergEquationOfMotion|maxwell_ampere_source_law|"
                r"lorentz_cross_curl_x_source_law_support|lorentzCrossCurlXComponent|"
                r"lorentzCrossCurlX_of_evidence|LorentzCrossCurlXFrontier|"
                r"euler_lagrange_x_force_balance_source_law_support|"
                r"eulerLagrangeXForceBalance|eulerLagrangeXForceBalance_of_evidence|"
                r"EulerLagrangeXForceBalanceFrontier|"
                r"first_variation_evaluation_source_law_support|"
                r"firstVariationEvaluation|FirstVariationEvaluationFrontier|"
                r"tdse_product_source_law_support|tdseProductDifferentiation|"
                r"TimeDependentSchrodingerProductDifferentiationFrontier|"
                r"maxwell_magnetic_flux_constitutive|maxwell_electric_displacement_constitutive|"
                r"maxwell_magnetization_current|maxwellAmpereMatter)\b",
                lean_code,
                re.I,
            )
        )
    if item_id == "bg.euler_lagrange_law":
        return bool(
            re.search(
                r"\b(EulerLagrangeXForceBalanceFrontier|"
                r"euler_lagrange_x_before_cancellation|"
                r"euler_lagrange_common_term_cancellation_support|"
                r"euler_lagrange_force_definition|"
                r"euler_lagrange_x_force_balance_source_law_support|"
                r"eulerLagrangeXForceBalance|"
                r"eulerLagrangeXForceBalanceAlgebraCore)\b",
                lean_code,
            )
        )
    if item_id in {"bg.unit_dimension_bridge", "bg.unit_dimension_homogeneity"}:
        return bool(
            re.search(
                r"\b(UnitDimensionCompatible|unit_dimension_bridge|DimensionCompatible)\b",
                lean_code,
            )
        )
    if item_id == "bg.algebraic_core":
        return bool(
            re.search(
                r"\b(heisenbergEquationOfMotion|heisenberg_equation_position_mathlib_grounded|"
                r"heisenberg_equation_position_source_grounded|fourier_integration_by_parts_algebraic_core|"
                r"fourier_integration_by_parts_from_source_laws|ladder_number_operator_algebraic_core|"
                r"ladder_number_scalar_algebraic_core|ladder_number_operator_source_law_support|"
                r"physical_ladder_product_algebraic_core|"
                r"physical_ladder_product_source_law_support|PhysicalLadderProductSourceLaw|"
                r"physicalLadderProductExpansion|"
                r"maxwellAmpereMatterAlgebraCore|maxwell_ampere_matter_core_replay|"
                r"maxwell_magnetic_flux_curl_bridge|maxwell_displacement_current_expansion|"
                r"maxwell_ampere_after_displacement_expansion|"
                r"oscillator_position_second_derivative_algebraic_core|"
                r"oscillator_position_second_derivative_source_law_support|"
                r"oscillatorPositionSecondDerivative|"
                r"oscillator_hamilton_momentum_equation_algebraic_core|"
                r"oscillator_hamilton_momentum_source_law_support|"
                r"oscillatorMomentumEquationFromHamiltonian|"
                r"oscillator_momentum_second_derivative_algebraic_core|"
                r"oscillator_momentum_second_derivative_source_law_support|"
                r"oscillatorMomentumSecondDerivative|"
                r"oscillator_position_solution_algebraic_core|"
                r"oscillator_position_solution_source_law_support|"
                r"oscillatorPositionSolutionFromInitialData|"
                r"separable_wave_second_derivative_algebraic_core|"
                r"separable_wave_second_spatial_derivative_source_law_support|"
                r"separableWaveSecondSpatialDerivative|"
                r"position_variance_born_algebraic_core|"
                r"position_variance_born_source_law_support|"
                r"positionVarianceBornFormula|"
                r"position_momentum_canonical_expectation_algebraic_core|"
                r"position_momentum_canonical_expectation_source_law_support|"
                r"positionMomentumCanonicalExpectation|"
                r"rabi_probability_algebraic_core|"
                r"rabi_probability_source_law_support|"
                r"rabiProbabilityFromAmplitude|"
                r"probabilityFromVacuumRabiAmplitude|"
                r"separable_wave_tdse_algebraic_core|"
                r"separable_wave_tdse_source_law_support|"
                r"separableWaveTDSEEigenRelation|"
                r"lorentz_cross_curl_x_core_replay|"
                r"lorentz_cross_curl_x_source_law_support|"
                r"lorentzCrossCurlXAlgebraCore|"
                r"lorentzCrossCurlXComponent|"
                r"euler_lagrange_x_force_balance_core_replay|"
                r"euler_lagrange_x_force_balance_source_law_support|"
                r"eulerLagrangeXForceBalanceAlgebraCore|"
                r"eulerLagrangeXForceBalance|"
                r"first_variation_evaluation_core_replay|"
                r"first_variation_evaluation_source_law_support|"
                r"firstVariationEvaluationAlgebraCore|"
                r"firstVariationEvaluation|"
                r"tdse_product_identity_core_replay|"
                r"tdse_product_source_law_support|"
                r"tdseProductDifferentiationIdentityCore|"
                r"tdseProductDifferentiation|"
                r"heisenberg_cauchy_schwarz_algebraic_core|"
                r"heisenberg_cauchy_schwarz_source_law_support|"
                r"heisenbergCauchySchwarzIntermediate|"
                r"diracImaginaryQuotient)\b",
                lean_code,
            )
        )
    if item_id == "bg.em_field_definitions":
        return bool(
            re.search(
                r"\b(positionBornDensity|PositionWavefunction|PositionMeasurementSpaceFrontier|"
                r"positionExpectationIntegrand|positionExpectationIntegral|"
                r"position_variance_born_density_support|LorentzCrossCurlXFrontier|"
                r"lorentz_cross_x_component|lorentz_curl_y_from_potential|"
                r"lorentz_curl_z_from_potential|lorentz_expanded_force_component|"
                r"cross_x_component|curl_y_from_potential|curl_z_from_potential|"
                r"expanded_force_component|EulerLagrangeXForceBalanceFrontier|"
                r"vectorPotentialTimeX|vectorPotentialXX|vectorPotentialXY|"
                r"vectorPotentialXZ|vectorPotentialYX|vectorPotentialZX|"
                r"scalarPotentialX)\b",
                lean_code,
            )
        )
    if item_id == "bg.vector_carrier_and_projection":
        return bool(
            re.search(
                r"\b(LinearMap|Module|EuclideanSpace|Vector|Field|projection|coordinate)\b",
                lean_code,
                re.I,
            )
        )
    if item_id == "bg.operator_and_inner_product_surface":
        return bool(
            re.search(
                r"\b(InnerProductSpace|LinearMap|Matrix|Module|HeisenbergEquationEvidence|"
                r"RealLineL2PositionMomentumModel|commutatorValueOnCore|"
                r"canonical_operator_identity_on_core_support|"
                r"PositionMomentumCanonicalExpectationEvidence|"
                r"PositionMomentumCanonicalExpectationSourceLaw|commutator)\b",
                lean_code,
            )
        )
    if item_id == "bg.quantum_evolution_identities":
        return bool(
            re.search(
                r"\b(HeisenbergSourceLaw|heisenberg_source_law_support|heisenberg_calculus_product_rule_support|"
                r"heisenbergEquationOfMotion|product_rule_derivative|commutator_identification|result_definition|"
                r"DimensionlessLadderOperatorSourceLaw|ladder_operator_definition_support|"
                r"ladder_number_operator_source_law_support|OscillatorMomentumSourceLaw|"
                r"oscillator_velocity_relation_support|oscillator_momentum_source_law_support|"
                r"oscillatorVelocityEvidenceOfHilbertGrounding|oscillatorMomentumFromVelocity|"
                r"OscillatorPositionSecondDerivativeSourceLaw|"
                r"oscillator_position_second_from_velocity_support|"
                r"oscillator_position_momentum_equation_support|"
                r"oscillator_position_second_derivative_source_law_support|"
                r"oscillatorPositionSecondDerivativeEvidence|"
                r"oscillatorPositionSecondDerivative|"
                r"OscillatorHamiltonMomentumSourceLaw|"
                r"oscillator_hamiltonian_gradient_support|"
                r"oscillator_hamilton_equation_support|"
                r"oscillator_hamilton_momentum_source_law_support|"
                r"oscillatorHamiltonEquationEvidenceOfHilbertGrounding|"
                r"OscillatorHamiltonEquationEvidence|"
                r"oscillatorMomentumEquationFromHamiltonian|"
                r"OscillatorMomentumSecondDerivativeSourceLaw|"
                r"oscillator_momentum_equation_support|"
                r"oscillator_momentum_differentiated_equation_support|"
                r"oscillator_momentum_rhs_derivative_support|"
                r"oscillator_momentum_second_derivative_source_law_support|"
                r"oscillatorMomentumSecondDerivativeEvidenceOfHilbertGrounding|"
                r"OscillatorMomentumSecondDerivativeEvidence|"
                r"oscillatorMomentumSecondDerivative|"
                r"OscillatorPositionSolutionSourceLaw|"
                r"oscillator_position_general_solution_support|"
                r"oscillator_position_initial_position_support|"
                r"oscillator_position_initial_momentum_support|"
                r"oscillator_position_solution_source_law_support|"
                r"oscillatorGeneralSolutionEvidenceOfGrounding|"
                r"OscillatorGeneralSolutionEvidence|"
                r"oscillatorPositionSolutionFromInitialData|"
                r"RabiProbabilitySourceLaw|"
                r"rabi_state_expansion_support|"
                r"rabi_transition_amplitude_from_state_support|"
                r"rabi_vacuum_amplitude_definition_support|"
                r"rabi_vacuum_amplitude_apply_support|"
                r"rabi_probability_definition_support|"
                r"rabi_probability_source_law_support|"
                r"rabiProbabilityEvidenceOfGrounding|"
                r"RabiProbabilityEvidence|"
                r"rabiProbabilityFromAmplitude|"
                r"TwoLevelRabiStateExpansion|"
                r"VacuumRabiAmplitude|"
                r"probabilityFromAmplitude|"
                r"vacuumRabiProbabilityFromStateExpansion|"
                r"SeparableWaveTDSESourceLaw|"
                r"separable_wave_time_derivative_support|"
                r"separable_wave_tdse_lhs_definition_support|"
                r"separable_wave_tdse_rhs_definition_support|"
                r"separable_wave_phase_cancellation_support|"
                r"separable_wave_tdse_source_law_support|"
                r"separableWaveTDSEEvidenceOfGrounding|"
                r"SeparableWaveTDSEEvidence|"
                r"separableWaveTDSEEigenRelation|"
                r"HeisenbergCauchySchwarzIntermediateSourceLaw|"
                r"heisenberg_fg_integral_reduction_support|"
                r"heisenberg_dirac_quotient_definition_support|"
                r"heisenberg_quotient_definition_support|"
                r"heisenberg_cauchy_schwarz_bound_support|"
                r"heisenberg_cauchy_schwarz_source_law_support|"
                r"heisenbergCauchySchwarzIntermediateEvidenceOfGrounding|"
                r"HeisenbergCauchySchwarzIntermediateEvidence|"
                r"heisenbergCauchySchwarzIntermediate|"
                r"diracImaginaryQuotient|"
                r"KineticEnergyEigenSourceLaw|kinetic_energy_operator_definition_support|"
                r"kinetic_energy_second_derivative_support|kinetic_energy_source_law_support|"
                r"kineticEnergyEigenRelation|"
                r"tdse_product_identity_core_replay|"
                r"tdse_product_source_law_support|"
                r"tdse_product_rule_decomposition|"
                r"tdse_energy_derivative_substitution|"
                r"tdse_ket_inner_substitution|"
                r"tdse_adjoint_bra_substitution|"
                r"tdseProductDifferentiationIdentityCore|"
                r"tdseProductDifferentiation|"
                r"TimeDependentSchrodingerProductDifferentiationFrontier)\b",
                lean_code,
            )
        )
    return False


def support_declaration_count(lean_code: str) -> int:
    """Document the responsibility of ``support_declaration_count``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``support_declaration_count`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    support_decl = re.compile(
        r"^\s*(def|abbrev|structure|class|instance|lemma)\s+[A-Za-z0-9_'.]+|"
        r"^\s*theorem\s+[A-Za-z0-9_'.]*(?:core|projection|bridge|support|law|unit|dimension|field|calculus|definition)[A-Za-z0-9_'.]*",
        re.M,
    )
    local_decl_count = len(support_decl.findall(lean_code))
    reused_foundation_count = count_terms(
        lean_code, MATHFORMER_FOUNDATION_SUPPORT_TERMS
    )
    return local_decl_count + reused_foundation_count


def build_report(
    *,
    source_text: str,
    lean_text: str,
    type_packet: dict[str, Any],
    assumption_packet: dict[str, Any],
    unit_report: dict[str, Any],
    law_packet: dict[str, Any],
    background_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Document the responsibility of ``build_report``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    findings: list[dict[str, Any]] = []
    source_physical = has_any(source_text, PHYSICAL_TERMS)
    source_vector = has_any(source_text, VECTOR_TERMS)
    source_frame = has_any(source_text, FRAME_TERMS)
    source_law = has_any(source_text, LAW_TERMS)
    source_assumptions = has_any(source_text, ASSUMPTION_TERMS)
    source_background = has_any(source_text, BACKGROUND_SOURCE_TERMS)
    source_has_informal_derivation = has_any(
        source_text, ["informal derivation", "question", "show that", "derive"]
    )

    lean_code = strip_lean_comments(lean_text)
    combined_type = lean_code + "\n" + packet_raw_text(type_packet)
    combined_assumptions = lean_code + "\n" + packet_raw_text(assumption_packet)
    combined_laws = lean_code + "\n" + packet_raw_text(law_packet)
    header = module_header_comment(lean_text)
    header_lower = header.lower()

    raw_local_scaffold_count = count_local_scaffolds(lean_code, type_packet)
    local_scaffold_count = count_unresolved_local_scaffolds(
        lean_code=lean_code,
        type_packet=type_packet,
        assumption_packet=assumption_packet,
    )
    mathlib_native_count = count_mathlib_native_surfaces(combined_type)
    mathlib_vector_count = count_mathlib_vector_surfaces(combined_type)
    opaque_dimension_count = count_opaque_dimension_surfaces(lean_code)
    string_context_count = count_string_context_surfaces(lean_code)
    typed_prop_context = has_typed_prop_context(lean_code)
    grounding_level = mathlib_grounding_level(
        lean_code=lean_code,
        type_packet=type_packet,
        assumption_packet=assumption_packet,
    )
    support_decl_count = support_declaration_count(lean_code)
    required_background_items = background_items(background_packet or {}, type_packet)
    open_background = [
        item
        for item in open_background_items(required_background_items)
        if not background_item_closed_by_lean(item, lean_code)
    ]
    has_quantity_surface = bool(
        re.search(
            r"\b(Quantity|PhysDim|VectorQuantity|Unit|Dimension)\b", combined_type
        )
        or mathlib_native_count
    )
    has_vector_surface = bool(
        re.search(r"\b(VectorQuantity|Vector|Field)\b", combined_type)
        or mathlib_vector_count
    )
    has_frame_surface = bool(
        re.search(
            r"\b(Frame|frame|Coordinate|coordinate|Gauge|Regime)\b",
            combined_assumptions,
        )
    )
    assumption_label_terms = [
        "source-backed",
        "source_backed",
        "sourcebacked",
        "source_law",
        "sourcelaw",
        "mathlib-backed",
        "mathlib_backed",
        "mathlibbacked",
        "generated-support",
        "generated_support",
        "generatedsupport",
        "blocked",
    ]
    has_assumption_labels = any(
        label in combined_assumptions.lower() for label in assumption_label_terms
    )
    has_law_surface = bool(
        re.search(
            r"\b(SourceLaw|Law|law|HeisenbergSourceLaw|heisenberg_source_law_support|"
            r"heisenbergEquationOfMotion|conservation|newton|maxwell|constitutive)\b",
            combined_laws,
            re.I,
        )
    )
    unit_status = unit_report.get("status", "missing") if unit_report else "missing"
    raw_real_count = len(re.findall(r"\b(Real|Float|Rat)\b", lean_text))
    has_projection = bool(
        re.search(
            r"\b(project|projection|coordinate|coord|toReal|scalar)\b", lean_text, re.I
        )
    )
    target_as_law = (
        bool(re.search(r"^\s*(axiom|constant)\b", lean_text, re.M)) and has_law_surface
    )
    has_commentary_header = bool(header)
    has_full_informal_header = "informal" in header_lower and (
        "derivation" in header_lower or "target" in header_lower
    )
    has_formal_alignment = bool(
        re.search(
            r"\b(formal alignment|lean proof|maps to|corresponding lean|mirrors these steps|proof block)\b",
            header,
            re.I,
        )
    )
    semantic_contract_fields = [
        "Semantic preservation contract",
        "Source target",
        "Lean target",
        "Preservation status",
        "Semantic deltas",
        "Step alignment",
        "Trust boundary",
    ]
    missing_semantic_contract_fields = [
        field for field in semantic_contract_fields if field.lower() not in header_lower
    ]
    has_semantic_preservation_contract = not missing_semantic_contract_fields
    vacuous_physics_context_count = len(
        re.findall(r"\bPhysicsContext\s+True\b", lean_text)
    )
    reflexive_unit_dimension_count = len(
        re.findall(r"\bUnitDimensionCompatible\s+([A-Za-z0-9_.]+)\s+\1\b", lean_text)
    )

    if source_physical and not has_quantity_surface:
        add_finding(
            findings,
            severity="critical",
            code="missing_physics_quantity_hypotheses",
            message="The source is physics-bearing, but final hypotheses do not expose typed quantities, dimensions, or units.",
            repair_surface="quantity_typing",
        )
    if source_physical and unit_status not in {"pass", "ok", "complete"}:
        add_finding(
            findings,
            severity="critical",
            code="unit_dimension_review_not_passing",
            message="Final physics hypotheses lack a passing unit/dimension report.",
            repair_surface="unit_dimension_obligation",
        )
    if source_vector and not has_vector_surface:
        add_finding(
            findings,
            severity="critical",
            code="missing_vector_or_field_hypotheses",
            message="Vector or field source structure is not represented in final hypotheses.",
            repair_surface="projection_bridge",
        )
    if open_background:
        add_finding(
            findings,
            severity="critical",
            code="background_formalization_obligations_open",
            message=(
                "Required intermediate definitions or background results remain unformalized: "
                + ", ".join(
                    str(item.get("id", "unknown")) for item in open_background[:6]
                )
            ),
            repair_surface="support_dependency",
        )
    if (source_background or required_background_items) and not support_decl_count:
        add_finding(
            findings,
            severity="error",
            code="missing_background_support_declarations",
            message=(
                "The source requires intermediate definitions or background results, but the Lean artifact "
                "does not expose support definitions, lemmas, bridge lemmas, or reusable core theorems."
            ),
            repair_surface="support_dependency",
        )
    if source_physical and grounding_level != "high":
        add_finding(
            findings,
            severity="critical",
            code="mathlib_grounding_below_complete_threshold",
            message=(
                "Physics-bearing theorem surfaces do not reach high Mathlib grounding; "
                "local wrappers or scalar cores must be replaced by Mathlib-native carriers, "
                "or an explicit abstraction-boundary blocker must keep the artifact draft/blocked."
            ),
            repair_surface="mathlib_grounding",
        )
    if source_physical and local_scaffold_count:
        add_finding(
            findings,
            severity="error",
            code="local_physics_scaffold_at_final_surface",
            message=(
                "Local Quantity/VectorQuantity/context/law scaffolds remain in the final theorem surface; "
                "they are fallback scaffolds, not maximal Mathlib grounding evidence."
            ),
            repair_surface="mathlib_grounding",
        )
    if (
        source_vector
        and re.search(r"\bVectorQuantity\b", lean_code)
        and not mathlib_vector_count
    ):
        add_finding(
            findings,
            severity="critical",
            code="local_vector_wrapper_without_mathlib_vector_surface",
            message=(
                "The source is vector- or field-bearing, but the final artifact uses a local vector wrapper "
                "without a Mathlib-native vector, module, matrix, or linear-map surface."
            ),
            repair_surface="mathlib_grounding",
        )
    if source_physical and opaque_dimension_count:
        add_finding(
            findings,
            severity="critical",
            code="opaque_dimension_placeholders_at_final_surface",
            message="Opaque dimension placeholder types remain in the final physics surface.",
            repair_surface="mathlib_grounding",
        )
    if source_physical and string_context_count and not typed_prop_context:
        add_finding(
            findings,
            severity="error",
            code="string_context_without_typed_prop_context",
            message=(
                "Context, law, frame, or smoothness evidence is encoded as String labels without "
                "corresponding typed Prop assumptions or Mathlib predicates."
            ),
            repair_surface="mathlib_grounding",
        )
    if source_frame and not has_frame_surface:
        add_finding(
            findings,
            severity="error",
            code="missing_frame_regime_hypotheses",
            message="Frame, coordinate, gauge, sign, or regime context is missing from final hypotheses.",
            repair_surface="frame_regime",
        )
    if (
        source_assumptions
        or re.search(r"\b(0\s*<|!=\s*0|NeZero|Differentiable|ContDiff)\b", lean_text)
    ) and not has_assumption_labels:
        add_finding(
            findings,
            severity="error",
            code="unlabeled_contextual_assumptions",
            message="Contextual assumptions are present or implied but not labeled by source status.",
            repair_surface="contextual_assumption",
        )
    if source_law and not has_law_surface:
        add_finding(
            findings,
            severity="error",
            code="missing_law_grounding_hypotheses",
            message="A physical law or constitutive assumption is used in the source but not visible in final hypotheses.",
            repair_surface="law_grounding",
        )
    if source_physical and not has_commentary_header:
        add_finding(
            findings,
            severity="error",
            code="informal_commentary_header_missing",
            message="The Lean artifact does not preserve the original informal statement and derivation in a module header.",
            repair_surface="source_alignment_commentary",
        )
    if source_has_informal_derivation and not has_full_informal_header:
        add_finding(
            findings,
            severity="error",
            code="full_informal_derivation_not_in_header",
            message="The module header does not visibly contain the full informal derivation or target statement.",
            repair_surface="source_alignment_commentary",
        )
    if source_has_informal_derivation and not has_formal_alignment:
        add_finding(
            findings,
            severity="error",
            code="informal_to_formal_alignment_missing",
            message="The module header does not map informal steps to corresponding Lean hypotheses, lemmas, or proof blocks.",
            repair_surface="source_alignment_commentary",
        )
    if source_has_informal_derivation and missing_semantic_contract_fields:
        add_finding(
            findings,
            severity="warning",
            code="semantic_preservation_contract_incomplete",
            message=(
                "The module header lacks explicit semantic-preservation contract fields: "
                + ", ".join(missing_semantic_contract_fields)
            ),
            repair_surface="source_alignment_commentary",
        )
    if source_physical and vacuous_physics_context_count:
        add_finding(
            findings,
            severity="warning",
            code="vacuous_physics_context_true",
            message=(
                "The Lean artifact still contains PhysicsContext True; new or repaired "
                "artifacts should replace generic context labels with typed source-backed propositions."
            ),
            repair_surface="contextual_assumption",
        )
    if source_physical and reflexive_unit_dimension_count:
        add_finding(
            findings,
            severity="warning",
            code="reflexive_unit_dimension_bridge",
            message=(
                "The Lean artifact contains reflexive UnitDimensionCompatible evidence; "
                "new or repaired artifacts should use non-reflexive dimension evidence or an explicit dimension algebra."
            ),
            repair_surface="unit_dimension_obligation",
        )
    if (
        source_physical
        and raw_real_count >= 3
        and not has_projection
        and not mathlib_native_count
    ):
        add_finding(
            findings,
            severity="critical",
            code="raw_scalar_erasure_at_final_review",
            message="Final hypotheses use several raw scalar variables without a projection bridge for a physics claim.",
            repair_surface="projection_bridge",
        )
    if target_as_law:
        add_finding(
            findings,
            severity="critical",
            code="target_shaped_law_or_axiom",
            message="Final hypotheses may hide the target as an axiom, constant, or all-purpose law.",
            repair_surface="target_nonvacuity",
        )

    severity_rank = {"info": 0, "warning": 1, "error": 2, "critical": 3}
    max_severity = max(
        (severity_rank[item["severity"]] for item in findings), default=0
    )
    status = "fail" if max_severity >= 2 else "warn" if max_severity == 1 else "pass"
    return {
        "style": "physics_final_hypothesis_review",
        "status": status,
        "reviewed_properties": {
            "source_physical": source_physical,
            "source_vector": source_vector,
            "source_frame": source_frame,
            "source_law": source_law,
            "source_background": source_background,
            "quantity_surface": has_quantity_surface,
            "vector_surface": has_vector_surface,
            "frame_surface": has_frame_surface,
            "assumption_labels": has_assumption_labels,
            "unit_status": unit_status,
            "commentary_header": has_commentary_header,
            "full_informal_header": has_full_informal_header,
            "formal_alignment_commentary": has_formal_alignment,
            "semantic_preservation_contract": has_semantic_preservation_contract,
            "missing_semantic_contract_fields": missing_semantic_contract_fields,
            "mathlib_grounding_level": grounding_level,
            "mathlib_native_surface_count": mathlib_native_count,
            "mathlib_vector_surface_count": mathlib_vector_count,
            "local_scaffold_count": local_scaffold_count,
            "raw_local_scaffold_count": raw_local_scaffold_count,
            "foundation_bridge_scaffold_count": raw_local_scaffold_count
            - local_scaffold_count,
            "opaque_dimension_surface_count": opaque_dimension_count,
            "string_context_surface_count": string_context_count,
            "vacuous_physics_context_true_count": vacuous_physics_context_count,
            "reflexive_unit_dimension_count": reflexive_unit_dimension_count,
            "typed_prop_context": typed_prop_context,
            "background_item_count": len(required_background_items),
            "open_background_item_count": len(open_background),
            "support_declaration_count": support_decl_count,
        },
        "findings": findings,
        "refinement_required": status == "fail",
        "refinement_handoff": {
            "router": "physics-lean-review-refinement-router",
            "repair_surfaces": sorted({item["repair_surface"] for item in findings}),
            "rerun_gates": [
                "dependency.resolve",
                "mathlib.grounding_maximize",
                "review.physics_final_hypotheses",
                "review.mathematical_final_hypotheses",
                "review.final_derivation_hypotheses",
            ],
            "monotonicity_constraints": [
                "preserve passing source anchors",
                "preserve theorem names and already-correct hypotheses",
                "do not weaken the target conclusion",
                "do not reduce unit or dimension coverage",
                "do not reduce Mathlib-native surface coverage",
                "do not remove or weaken already-correct background support declarations",
                "do not reclassify local wrappers, opaque dimensions, or String context labels as maximal grounding",
                "rerun affected reviewers and protected gates",
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
    parser.add_argument("--lean-file", type=Path)
    parser.add_argument("--lean-text")
    parser.add_argument("--type-packet", type=Path)
    parser.add_argument("--assumption-packet", type=Path)
    parser.add_argument("--unit-report", type=Path)
    parser.add_argument("--law-packet", type=Path)
    parser.add_argument("--background-packet", type=Path)
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
    if args.self_test:
        report = build_report(
            source_text="A vector force obeys Newton's law in an inertial frame with units.",
            lean_text="theorem bad (F m a : Real) : F = m * a := by sorry",
            type_packet={},
            assumption_packet={},
            unit_report={},
            law_packet={},
            background_packet={},
        )
        assert report["status"] == "fail"
        assert "quantity_typing" in report["refinement_handoff"]["repair_surfaces"]
        assert "mathlib_grounding" in report["refinement_handoff"]["repair_surfaces"]
        background_report = build_report(
            source_text="Define the electric field from a potential and use a projection lemma to derive the force component.",
            lean_text="""
import Mathlib.Analysis.InnerProductSpace.PiL2
/-!
Informal derivation: source background definitions are still open.

Formal alignment:
- The target theorem depends on background definitions.
-/
theorem target (F : EuclideanSpace Real (Fin 3)) : F = F := rfl
""",
            type_packet={},
            assumption_packet={"labels": ["source-backed"]},
            unit_report={"status": "pass"},
            law_packet={},
            background_packet={
                "background_items": [
                    {
                        "id": "bg.em_field_definitions",
                        "formalization_status": "needs_autoformalization",
                    }
                ]
            },
        )
        assert background_report["status"] == "fail"
        assert (
            "support_dependency"
            in background_report["refinement_handoff"]["repair_surfaces"]
        )
        good_report = build_report(
            source_text="A vector force has units.",
            lean_text="""
import Mathlib.Analysis.InnerProductSpace.PiL2
import Mathlib.Analysis.Calculus.FDeriv.Basic

/-!
Informal derivation: the force vector identity is represented directly on a
Mathlib Euclidean vector space.

Formal alignment:
- The informal vector identity maps to theorem `good`.
- The positivity side condition maps to `hpos`.
-/

theorem good
    (F a : EuclideanSpace Real (Fin 3))
    (m : Real)
    (hpos : 0 < m)
    (T : EuclideanSpace Real (Fin 3) -> EuclideanSpace Real (Fin 3))
    (h : F = m • a) :
    F = m • a := h
""",
            type_packet={
                "lean_surfaces": ["EuclideanSpace Real (Fin 3)", "HasDerivAt"]
            },
            assumption_packet={"labels": ["source-backed positivity"]},
            unit_report={"status": "pass"},
            law_packet={},
            background_packet={},
        )
        assert good_report["status"] == "pass", good_report
        assert good_report["reviewed_properties"]["mathlib_grounding_level"] == "high"
    else:
        report = build_report(
            source_text=read_text(args.source_file, args.source_text),
            lean_text=read_text(args.lean_file, args.lean_text),
            type_packet=load_json(args.type_packet),
            assumption_packet=load_json(args.assumption_packet),
            unit_report=load_json(args.unit_report),
            law_packet=load_json(args.law_packet),
            background_packet=load_json(args.background_packet),
        )
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
