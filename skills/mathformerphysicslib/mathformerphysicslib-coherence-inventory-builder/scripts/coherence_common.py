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
#   Keep MathformerPhysicsLib coherence checks deterministic and shared across
#   the library-level critic skills.
#
# Intent:
#   Provide reusable inventory, canonicalization, Mathlib-grounding, critic,
#   repair-planning, and gate helpers for the MathformerPhysicsLib coherence
#   workflow.
#
# Function:
#   Scans repository-local MathformerPhysicsLib artifacts and emits structured
#   JSON packets consumed by the planned skills and test runner.
#
# Maintenance Notes:
#   Keep concept rules conservative. Findings should point to evidence and
#   blockers rather than pretending to prove semantic equivalence.

"""Shared MathformerPhysicsLib coherence workflow helpers."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
LIB_ROOT = REPO_ROOT / "MathformerPhysicsLib"
LEAN_ROOT = LIB_ROOT / "Lean"
FOUNDATIONS_ROOT = LEAN_ROOT / "Foundations"
FOUNDATIONS_INDEX = LEAN_ROOT / "Foundations.lean"

DECL_RE = re.compile(
    r"^\s*(?:noncomputable\s+)?(def|theorem|lemma|structure|abbrev|axiom)\s+([A-Za-z0-9_'.]+)"
)
IMPORT_RE = re.compile(r"^\s*import\s+(.+?)\s*$")

from libraries.MathformerPhysicsLib.release_status import (
    build_release_status,
)

CONCEPT_RULES: dict[str, dict[str, Any]] = {
    "vector_field.real.euclidean3": {
        "object_class": "vector_field",
        "patterns": ["EuclideanSpace", "Fin 3", "vector", "component", "projection"],
        "mathlib_targets": ["EuclideanSpace Real (Fin n)", "Fin n -> Real", "Pi"],
        "api_terms": ["EuclideanSpace", "Fin", "component", "proj"],
        "owner_hint": "Foundations/Fields.lean",
    },
    "linear_operator.field": {
        "object_class": "quantum_operator",
        "patterns": ["LinearMap", "operator", "matrix", "Hamiltonian", "linear"],
        "mathlib_targets": ["LinearMap", "Matrix", "ContinuousLinearMap"],
        "api_terms": ["LinearMap", "Matrix", "map"],
        "owner_hint": "Foundations/Operators.lean",
    },
    "commutator.algebra": {
        "object_class": "commutator",
        "patterns": ["commutator", "Commute", "noncommut", "bracket"],
        "mathlib_targets": ["Commute", "mul_commutator", "Algebra"],
        "api_terms": ["commutator", "Commute", "mul"],
        "owner_hint": "Foundations/Operators.lean",
    },
    "dirac.vacuum_rabi_born_rule": {
        "object_class": "dirac_vacuum_rabi_born_rule",
        "patterns": [
            "TwoLevelRabiStateExpansion",
            "VacuumRabiAmplitude",
            "transitionAmplitude_from_twoLevelRabiStateExpansion",
            "probabilityFromVacuumRabiAmplitude",
            "vacuumRabiProbabilityFromStateExpansion",
            "Rabi",
            "Born",
            "probabilityFromAmplitude",
        ],
        "mathlib_targets": [
            "InnerProductSpace",
            "inner",
            "Complex.normSq",
            "norm",
            "CompleteSpace",
        ],
        "api_terms": [
            "transitionAmplitude",
            "probabilityFromAmplitude",
            "TwoLevelRabiStateExpansion",
            "VacuumRabiAmplitude",
            "complex_normSq_neg_I_mul_real",
        ],
        "owner_hint": "Foundations/HilbertSpace.lean",
    },
    "dirac.vacuum_rabi_dynamics_measurement": {
        "object_class": "dirac_vacuum_rabi_dynamics_measurement",
        "patterns": [
            "TwoLevelRabiFrame",
            "twoLevelRabiStateFromFrame",
            "transitionAmplitude_from_twoLevelRabiFrameState",
            "projectionBornProbability",
            "TwoLevelRabiGroundMeasurementFrontier",
            "TwoLevelRabiDynamicsFrontier",
            "projectionBornProbability_from_twoLevelRabiDynamics",
            "TwoLevelRabiParameterCalibrationFrontier",
            "TwoLevelRabiOpenSystemFrontier",
            "VacuumRabiRecursiveFrontier",
            "vacuumRabiRecursiveFrontier_probability_curve",
            "unitary evolution",
            "ground-state channel",
        ],
        "mathlib_targets": [
            "InnerProductSpace",
            "ContinuousLinearMap",
            "inner",
            "norm",
            "Set",
            "HasDerivAt",
        ],
        "api_terms": [
            "TwoLevelRabiFrame",
            "twoLevelRabiStateFromFrame",
            "projectionBornProbability",
            "TwoLevelRabiGroundMeasurementFrontier",
            "TwoLevelRabiDynamicsFrontier",
            "TwoLevelRabiParameterCalibrationFrontier",
            "TwoLevelRabiOpenSystemFrontier",
            "VacuumRabiRecursiveFrontier",
        ],
        "owner_hint": "Foundations/HilbertSpace.lean",
    },
    "dirac.hellmann_feynman_expectation": {
        "object_class": "dirac_hellmann_feynman_expectation",
        "patterns": [
            "parameterizedHilbertExpectation",
            "ParameterizedEigenstateEquation",
            "EigenstateExpectationIdentityNear",
            "energy_eq_parameterizedExpectation_near_of_eigenstate",
            "DifferentiatedEigenstateEquation",
            "hellmannFeynmanDerivativeFromDifferentiatedEigenEquation",
            "energyDerivativeEqExpectationDerivative",
            "Hellmann",
            "Feynman",
            "Hamiltonian",
            "eigenstate",
        ],
        "mathlib_targets": [
            "HasDerivAt",
            "InnerProductSpace",
            "ContinuousLinearMap",
            "Filter.EventuallyEq",
            "nhds",
        ],
        "api_terms": [
            "parameterizedHilbertExpectation",
            "ParameterizedEigenstateEquation",
            "EigenstateExpectationIdentityNear",
            "DifferentiatedEigenstateEquation",
            "hellmannFeynmanDerivativeFromDifferentiatedEigenEquation",
        ],
        "owner_hint": "Foundations/HilbertSpace.lean",
    },
    "dirac.parameterized_hamiltonian_recursive": {
        "object_class": "dirac_parameterized_hamiltonian_recursive_frontier",
        "patterns": [
            "ParameterizedHamiltonianDerivativeFrontier",
            "parameterizedHamiltonianDerivativeFrontier_expectation",
            "parameterizedHamiltonianExpectationCurve",
            "parameterizedHamiltonianActionCurve",
            "parameterizedEigenvalueStateCurve",
            "parameterizedActionCurve_eq_eigenvalueStateCurve_near_of_eigenstate",
            "differentiatedEigenstateEquation_of_actionCurve_derivatives",
            "ParameterizedHamiltonianGeneratedDerivativeFrontier",
            "parameterizedHamiltonianGeneratedDerivativeFrontier_differentiated_eigen_eq",
            "parameterizedHamiltonianGeneratedDerivativeFrontier_expectation",
            "ParameterizedHamiltonianRecursiveExpansionFrontier",
            "parameterizedHamiltonianRecursiveExpansionFrontier_expectation",
            "ParameterizedHamiltonianGaugeFrontier",
            "ParameterizedHamiltonianSpectralProjectionBranch",
            "ParameterizedHamiltonianUnboundedDomainFrontier",
            "ParameterizedStateNormalizationDerivativeConstraint",
            "ParameterizedEigenstatePhaseGaugeCondition",
            "operator_curve_derivative_grounding",
            "state_curve_derivative_grounding",
            "energy_curve_derivative_grounding",
            "action_curve_derivative_grounding",
            "eigenvalue_state_curve_derivative_grounding",
            "expectation_derivative_closed",
            "normalization_derivative_constraint",
            "phase_gauge_selected",
            "spectral_projection_tracks_state",
            "projection_witness_near",
            "simple_eigenvalue_gap_radius",
            "bounded_core_matches_hamiltonian_near",
            "bounded_core_matches_derivative",
            "parameterizedHamiltonianDerivativeFrontier_expectation_has_deriv",
            "ParameterizedHamiltonianDifferentiabilityFrontier",
            "differentiated_eigen_eq_from_derivatives",
            "ParameterizedHamiltonianSpectralBranchFrontier",
            "projection_tracks_state",
            "ParameterizedHamiltonianFullyGroundedRecursiveFrontier",
            "common_domain_stability",
            "operator_derivative_domain_stability",
            "ParameterizedHamiltonianRecursiveFrontier",
            "smooth_operator_curve",
            "spectral_projection_tracking",
            "domain_stability_for_unbounded_extension",
        ],
        "mathlib_targets": [
            "HasDerivAt",
            "InnerProductSpace",
            "ContinuousLinearMap",
            "Filter.EventuallyEq",
            "Filter.Eventually",
            "nhds",
            "SelfAdjoint",
        ],
        "api_terms": [
            "ParameterizedHamiltonianDerivativeFrontier",
            "parameterizedHamiltonianExpectationCurve",
            "parameterizedHamiltonianActionCurve",
            "parameterizedEigenvalueStateCurve",
            "ParameterizedHamiltonianGeneratedDerivativeFrontier",
            "parameterizedHamiltonianGeneratedDerivativeFrontier_differentiated_eigen_eq",
            "parameterizedHamiltonianGeneratedDerivativeFrontier_expectation",
            "ParameterizedHamiltonianRecursiveExpansionFrontier",
            "parameterizedHamiltonianRecursiveExpansionFrontier_expectation",
            "ParameterizedHamiltonianGaugeFrontier",
            "ParameterizedHamiltonianSpectralProjectionBranch",
            "ParameterizedHamiltonianUnboundedDomainFrontier",
            "ParameterizedHamiltonianDifferentiabilityFrontier",
            "ParameterizedHamiltonianSpectralBranchFrontier",
            "ParameterizedHamiltonianFullyGroundedRecursiveFrontier",
            "ParameterizedHamiltonianRecursiveFrontier",
            "hellmannFeynmanDerivativeFromDifferentiatedEigenEquation",
        ],
        "owner_hint": "Foundations/HilbertSpace.lean",
    },
    "dirac.position_expectation_integral": {
        "object_class": "dirac_position_expectation_integral",
        "patterns": [
            "PositionWavefunction",
            "positionExpectationIntegrand",
            "positionExpectationIntegrand_apply",
            "PositionResolutionIdentityMeasureKernel",
            "positionExpectationIntegral",
            "positionExpectationIntegral_apply",
            "Born-rule position",
            "position expectation",
        ],
        "mathlib_targets": [
            "MeasureTheory.Measure",
            "MeasurableSpace",
            "integral",
            "norm",
        ],
        "api_terms": [
            "PositionWavefunction",
            "positionExpectationIntegrand",
            "PositionResolutionIdentityMeasureKernel",
            "positionExpectationIntegral",
        ],
        "owner_hint": "Foundations/HilbertSpace.lean",
    },
    "dirac.position_measurement_space": {
        "object_class": "dirac_position_measurement_space_frontier",
        "patterns": [
            "positionBornDensity",
            "positionExpectationIntegrand_eq_value_mul_density",
            "PositionMeasurementSpaceFrontier",
            "positionExpectationFromMeasurementSpace",
            "positionExpectationFromMeasurementSpace_apply",
            "PositionExpectationRecursiveFrontier",
            "PositionSpectralMeasureGrounding",
            "PositionL2WavefunctionGrounding",
            "PositionExpectationIntegrabilityGrounding",
            "PositionBornDensityIntegrable",
            "PositionBornProbabilityNormalization",
            "PositionExpectationIntegrable",
            "spectral_measure_grounding",
            "l2_wavefunction_grounding",
            "integrability_grounding",
        ],
        "mathlib_targets": [
            "MeasureTheory.Measure",
            "MeasurableSpace",
            "integral",
            "norm",
            "Lp",
        ],
        "api_terms": [
            "positionBornDensity",
            "PositionMeasurementSpaceFrontier",
            "positionExpectationFromMeasurementSpace",
            "PositionExpectationRecursiveFrontier",
            "PositionSpectralMeasureGrounding",
            "PositionL2WavefunctionGrounding",
            "PositionExpectationIntegrabilityGrounding",
            "PositionBornProbabilityNormalization",
            "PositionExpectationIntegrable",
        ],
        "owner_hint": "Foundations/HilbertSpace.lean",
    },
    "dirac.complex_imaginary_projection": {
        "object_class": "dirac_complex_imaginary_projection",
        "patterns": [
            "diracImaginaryQuotient",
            "diracImaginaryQuotient_star_eq_im",
            "diracImaginaryQuotient_eq_im_of_conjugate",
            "diracImaginaryQuotient_sq_eq_im_sq_of_conjugate",
            "Complex.im",
            "imaginary part",
        ],
        "mathlib_targets": ["Complex.im", "star", "Complex.I", "field_simp"],
        "api_terms": [
            "diracImaginaryQuotient",
            "diracImaginaryQuotient_eq_im_of_conjugate",
            "diracImaginaryQuotient_sq_eq_im_sq_of_conjugate",
        ],
        "owner_hint": "Foundations/HilbertSpace.lean",
    },
    "dirac.braket_imaginary_projection": {
        "object_class": "dirac_braket_imaginary_projection_frontier",
        "patterns": [
            "DiracBraketPair",
            "diracBraketPair_conjugate_symmetry",
            "diracBraketPairImaginaryQuotient",
            "diracBraketPairImaginaryQuotient_eq_im",
            "diracBraketPairImaginaryQuotient_sq_eq_im_sq",
            "DiracImaginaryProjectionRecursiveFrontier",
            "DiracSkewAdjointGeneratorGrounding",
            "DiracCommutatorExpectationGrounding",
            "quotient_matches_imaginary_part",
            "skew_adjoint_generator_grounding",
            "commutator_expectation_grounding",
        ],
        "mathlib_targets": [
            "InnerProductSpace",
            "inner",
            "star",
            "Complex.im",
            "Complex.I",
        ],
        "api_terms": [
            "DiracBraketPair",
            "diracBraketPairImaginaryQuotient",
            "DiracImaginaryProjectionRecursiveFrontier",
            "DiracSkewAdjointGeneratorGrounding",
            "DiracCommutatorExpectationGrounding",
            "transitionAmplitude_conjugate_symmetry",
        ],
        "owner_hint": "Foundations/HilbertSpace.lean",
    },
    "unbounded_operator.position_momentum_core": {
        "object_class": "unbounded_position_momentum",
        "patterns": [
            "UnboundedHilbertOperator",
            "PositionMomentumPair",
            "CommonInvariantCore",
            "HasDenseDomain",
            "commutatorValueOnCore",
            "canonical commutator",
            "unbounded",
        ],
        "mathlib_targets": [
            "Submodule",
            "LinearMap",
            "Dense",
            "IsClosed",
            "InnerProductSpace",
        ],
        "api_terms": [
            "UnboundedHilbertOperator",
            "CommonInvariantCore",
            "PositionMomentumPair",
            "commutatorValueOnCore",
        ],
        "owner_hint": "Foundations/UnboundedOperators.lean",
    },
    "position_momentum.schwartz_l2_model": {
        "object_class": "schwartz_l2_position_momentum_model",
        "patterns": [
            "SchwartzMap",
            "RealSchwartzWavefunction",
            "realSchwartzDerivative",
            "SchwartzL2PositionMomentumModel",
            "Schwartz/L2",
            "derivCLM",
        ],
        "mathlib_targets": [
            "SchwartzMap",
            "SchwartzMap.derivCLM",
            "InnerProductSpace",
            "CompleteSpace",
        ],
        "api_terms": [
            "RealSchwartzWavefunction",
            "realSchwartzDerivative",
            "SchwartzL2PositionMomentumModel",
            "toPositionMomentumPair",
        ],
        "owner_hint": "Foundations/PositionMomentumModels.lean",
    },
    "position_momentum.real_line_l2_instantiation": {
        "object_class": "real_line_l2_position_momentum_instantiation",
        "patterns": [
            "RealLineL2Wavefunction",
            "MeasureTheory.Lp",
            "realSchwartzToL2",
            "realSchwartzToL2_apply_ae",
            "realSchwartzL2RangeSubmodule",
            "RealLineL2SchwartzRangeSubmoduleDense",
            "RealLineMomentumActionIsDerivative",
            "RealLineSchwartzCanonicalCommutator",
            "RealLineSchwartzCanonicalCommutatorAsSchwartzMap",
            "RealLineL2PositionMomentumModel",
            "RealLinePositionRestrictedToSchwartzCore",
            "RealLineMomentumRestrictedToSchwartzCore",
            "RealLinePositionSchwartzGraphCoreTarget",
            "RealLineMomentumSchwartzGraphCoreTarget",
            "RealLinePositionEssentialSelfAdjointOnSchwartzCoreTarget",
            "RealLineMomentumEssentialSelfAdjointOnSchwartzCoreTarget",
            "RealLinePositionSpectralCalculusAvailable",
            "RealLineMomentumSpectralCalculusAvailable",
            "RealLineL2ClosureFrontier",
            "RealLineSchwartzCommutatorTransport",
            "RealLineSchwartzCanonicalCommutatorTransported",
            "RealLinePositionEssentialSelfAdjointTarget",
            "RealLineMomentumEssentialSelfAdjointTarget",
            "RealLinePositionSpectralCalculusTarget",
            "RealLineMomentumSpectralCalculusTarget",
            "RealLineL2SpectralClosureTargets",
            "L²",
            "L2",
        ],
        "mathlib_targets": [
            "MeasureTheory.Lp",
            "SchwartzMap.toLpCLM",
            "volume",
            "DenseRange",
        ],
        "api_terms": [
            "RealLineL2Wavefunction",
            "realSchwartzToL2",
            "realSchwartzToL2_apply_ae",
            "realSchwartzL2RangeSubmodule",
            "RealLineL2SchwartzRangeSubmoduleDense",
            "RealLineSchwartzCanonicalCommutator",
            "RealLineSchwartzCanonicalCommutatorAsSchwartzMap",
            "RealLineL2PositionMomentumModel",
            "RealLinePositionRestrictedToSchwartzCore",
            "RealLineMomentumRestrictedToSchwartzCore",
            "RealLinePositionSchwartzGraphCoreTarget",
            "RealLineMomentumSchwartzGraphCoreTarget",
            "RealLineSchwartzCommutatorTransport",
            "RealLineSchwartzCanonicalCommutatorTransported",
            "RealLinePositionEssentialSelfAdjointTarget",
            "RealLineMomentumEssentialSelfAdjointTarget",
            "RealLineL2SpectralClosureTargets",
        ],
        "owner_hint": "Foundations/PositionMomentumModels.lean",
    },
    "position_momentum.minimum_uncertainty_coherent_states": {
        "object_class": "minimum_uncertainty_coherent_state_frontier",
        "patterns": [
            "realLineUncertaintyProduct",
            "RealLineMinimumUncertaintySaturationFrontier",
            "realLineHeisenbergProduct_eq_on_saturation",
            "realLineMinimumUncertaintyResidual",
            "RealLineMinimumUncertaintyEquationFrontier",
            "realLineSaturation_of_minimumUncertaintyResidual",
            "RealLineGaussianMinimumUncertaintyFrontier",
            "RealLineCoherentStateOrbitFrontier",
            "minimum uncertainty",
            "coherent state",
            "Gaussian",
            "saturation",
        ],
        "mathlib_targets": [
            "Set",
            "norm",
            "InnerProductSpace",
            "SchwartzMap",
            "MeasureTheory.Lp",
            "LinearIsometryEquiv",
        ],
        "api_terms": [
            "realLineUncertaintyProduct",
            "RealLineMinimumUncertaintySaturationFrontier",
            "realLineMinimumUncertaintyResidual",
            "RealLineMinimumUncertaintyEquationFrontier",
            "RealLineGaussianMinimumUncertaintyFrontier",
            "RealLineCoherentStateOrbitFrontier",
        ],
        "owner_hint": "Foundations/PositionMomentumModels.lean",
    },
    "calculus.derivative_surface": {
        "object_class": "gradient_divergence_curl",
        "patterns": [
            "HasDerivAt",
            "HasFDerivAt",
            "Differentiable",
            "ContDiff",
            "derivative",
            "curl",
            "divergence",
            "gradient",
        ],
        "mathlib_targets": ["HasDerivAt", "HasFDerivAt", "Differentiable", "ContDiff"],
        "api_terms": ["HasDerivAt", "HasFDerivAt", "Differentiable", "deriv"],
        "owner_hint": "Foundations/VectorCalculus.lean",
    },
    "unit_dimension.compatible": {
        "object_class": "unit_bridge",
        "patterns": ["dimension", "unit", "homogeneous", "Quantity", "PhysDim"],
        "mathlib_targets": ["Real", "Module", "Monoid"],
        "api_terms": ["dimension", "unit", "compatible", "homogeneous"],
        "owner_hint": "Foundations/Units.lean",
    },
    "physical_law.witness": {
        "object_class": "physical_law",
        "patterns": ["law", "Law", "Maxwell", "Lorentz", "Schrodinger", "source"],
        "mathlib_targets": ["Prop"],
        "api_terms": ["Law", "law", "witness", "source"],
        "owner_hint": "Foundations/Laws.lean",
    },
    "context.assumption_label": {
        "object_class": "boundary_or_regime_assumption",
        "patterns": ["assumption", "boundary", "regime", "frame", "gauge", "context"],
        "mathlib_targets": ["Prop", "Set", "Filter", "Basis"],
        "api_terms": ["Context", "Assumption", "label", "source"],
        "owner_hint": "Foundations/Contexts.lean",
    },
}


def rel(path: Path, repository_root: Path | None = None) -> str:
    """Return a repository-relative path."""
    try:
        return (
            path.resolve()
            .relative_to(
                REPO_ROOT if repository_root is None else repository_root.resolve()
            )
            .as_posix()
        )
    except ValueError:
        return path.as_posix()


def load_json(path: Path | None) -> dict[str, Any]:
    """Load optional JSON."""
    if path is None:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(payload: Mapping[str, Any], path: Path | None) -> None:
    """Write optional JSON output."""
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if path is None:
        print(text, end="")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def lean_files(lean_root: Path | None = None) -> list[Path]:
    """Return MathformerPhysicsLib Lean files."""
    lean_root = LEAN_ROOT if lean_root is None else lean_root
    if not lean_root.exists():
        return []
    return sorted(path for path in lean_root.rglob("*.lean") if path.is_file())


def matching_concepts(text: str) -> list[str]:
    """Return conservative concept matches for a text block."""
    lower = text.lower()
    matches: list[str] = []
    for concept_id, rule in CONCEPT_RULES.items():
        if any(str(pattern).lower() in lower for pattern in rule["patterns"]):
            matches.append(concept_id)
    return sorted(set(matches))


def extract_declarations(
    path: Path, text: str, repository_root: Path | None = None
) -> list[dict[str, Any]]:
    """Extract declaration-like Lean lines."""
    declarations: list[dict[str, Any]] = []
    lines = text.splitlines()
    for line_no, line in enumerate(lines, 1):
        match = DECL_RE.match(line)
        if not match:
            continue
        context = "\n".join(lines[max(0, line_no - 4) : min(len(lines), line_no + 3)])
        concepts = matching_concepts(context + "\n" + line)
        declarations.append(
            {
                "kind": match.group(1),
                "name": match.group(2),
                "line": line_no,
                "concept_ids": concepts,
                "evidence": line.strip(),
                "path": rel(path, repository_root),
            }
        )
    return declarations


def extract_imports(text: str) -> list[str]:
    """Extract Lean imports."""
    imports: list[str] = []
    for line in text.splitlines():
        match = IMPORT_RE.match(line)
        if match:
            imports.extend(
                part.strip() for part in match.group(1).split() if part.strip()
            )
    return imports


def build_inventory(repository_root: Path | None = None) -> dict[str, Any]:
    """Build a library inventory packet."""
    lib_root = (
        LIB_ROOT
        if repository_root is None
        else repository_root / "MathformerPhysicsLib"
    )
    lean_root = LEAN_ROOT if repository_root is None else lib_root / "Lean"
    foundations_index = (
        FOUNDATIONS_INDEX if repository_root is None else lean_root / "Foundations.lean"
    )
    modules: list[dict[str, Any]] = []
    concept_occurrences: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for path in lean_files(lean_root):
        text = path.read_text(encoding="utf-8")
        imports = extract_imports(text)
        declarations = extract_declarations(path, text, repository_root)
        file_concepts = sorted(
            set(matching_concepts(text))
            | {cid for decl in declarations for cid in decl["concept_ids"]}
        )
        module = {
            "path": rel(path, repository_root),
            "is_foundation": "libraries/MathformerPhysicsLib/Lean/Foundations"
            in rel(path, repository_root)
            or rel(path, repository_root).endswith(
                "libraries/MathformerPhysicsLib/Lean/Foundations.lean"
            ),
            "imports": imports,
            "declaration_count": len(declarations),
            "declarations": declarations,
            "concept_ids": file_concepts,
            "has_broad_mathlib_import": "Mathlib" in imports,
            "has_placeholder": bool(
                re.search(r"\b(sorry|admit|Prop\s*:=\s*True|support_required)\b", text)
            ),
        }
        modules.append(module)
        for concept_id in file_concepts:
            concept_declarations = [
                {
                    "kind": decl["kind"],
                    "name": decl["name"],
                    "line": decl["line"],
                    "evidence": decl["evidence"],
                }
                for decl in declarations
                if concept_id in decl["concept_ids"]
            ]
            ownership_declarations = [
                decl
                for decl in concept_declarations
                if decl["kind"] in {"def", "structure", "abbrev", "axiom"}
            ]
            theorem_declarations = [
                decl
                for decl in concept_declarations
                if decl["kind"] in {"theorem", "lemma"}
            ]
            imports_foundation = any(
                name == "MathformerPhysicsLib.Lean.Foundations"
                or name.startswith("MathformerPhysicsLib.Lean.Foundations.")
                for name in imports
            )
            if ownership_declarations:
                occurrence_kind = "declaration"
            elif theorem_declarations:
                occurrence_kind = "theorem_use"
            else:
                occurrence_kind = "hypothesis_or_term_use"
            concept_occurrences[concept_id].append(
                {
                    "path": module["path"],
                    "declaration_names": [
                        decl["name"] for decl in concept_declarations
                    ],
                    "declarations": concept_declarations,
                    "ownership_declarations": ownership_declarations,
                    "theorem_declarations": theorem_declarations,
                    "occurrence_kind": occurrence_kind,
                    "imports_foundation": imports_foundation,
                    "is_foundation": module["is_foundation"],
                }
            )
    manifest = (
        load_json(lib_root / "MANIFEST.json")
        if (lib_root / "MANIFEST.json").exists()
        else {}
    )
    return {
        "style": "mathformerphysicslib_inventory",
        "schema_version": 1,
        "module_count": len(modules),
        "declaration_count": sum(module["declaration_count"] for module in modules),
        "modules": modules,
        "concept_occurrence_index": dict(sorted(concept_occurrences.items())),
        "manifest_has_foundations": "foundations"
        in manifest.get("backends", {}).get("Lean", {}),
        "foundations_index_exists": foundations_index.exists(),
    }


def canonical_owner(
    concept_id: str, occurrences: Sequence[Mapping[str, Any]]
) -> str | None:
    """Choose a canonical owner when possible."""
    rule = CONCEPT_RULES.get(concept_id, {})
    owner_hint = str(rule.get("owner_hint", ""))
    for occurrence in occurrences:
        path = str(occurrence.get("path", ""))
        if owner_hint and owner_hint in path:
            return path
    for occurrence in occurrences:
        if occurrence.get("is_foundation"):
            return str(occurrence.get("path"))
    if len(occurrences) == 1:
        return str(occurrences[0].get("path"))
    return None


def canonicalize(inventory: Mapping[str, Any]) -> dict[str, Any]:
    """Build a canonical concept graph."""
    concepts: list[dict[str, Any]] = []
    for concept_id, occurrences in sorted(
        inventory.get("concept_occurrence_index", {}).items()
    ):
        rule = CONCEPT_RULES.get(concept_id, {})
        owner = canonical_owner(concept_id, occurrences)
        concepts.append(
            {
                "concept_id": concept_id,
                "object_class": rule.get("object_class", "unknown"),
                "owner_module": owner,
                "owner_status": "owned" if owner else "ambiguous",
                "occurrence_count": len(occurrences),
                "occurrences": list(occurrences),
                "mathlib_targets": rule.get("mathlib_targets", []),
                "api_terms": rule.get("api_terms", []),
                "blockers": [] if owner else ["missing_canonical_owner"],
            }
        )
    return {
        "style": "mathformerphysicslib_concept_graph",
        "schema_version": 1,
        "concept_count": len(concepts),
        "ambiguous_count": sum(
            1 for concept in concepts if concept["owner_status"] == "ambiguous"
        ),
        "concepts": concepts,
    }


def audit_grounding(concept_graph: Mapping[str, Any]) -> dict[str, Any]:
    """Audit Mathlib grounding for concepts."""
    concepts: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    failed_candidate_count = 0
    for concept in concept_graph.get("concepts", []):
        concept_id = str(concept.get("concept_id"))
        targets = list(concept.get("mathlib_targets", []))
        owner = str(concept.get("owner_module") or "")
        if targets and owner and "Foundations" not in owner:
            level = "direct_mathlib"
        elif targets and owner:
            level = "mathlib_bridge"
        elif targets:
            level = "local_blocker"
        else:
            level = "unverified_local"
        counts[level] += 1
        failed_candidates = []
        if level not in {"direct_mathlib", "mathlib_bridge"}:
            for target in targets:
                failed_candidates.append(
                    {
                        "mathlib_target": target,
                        "reason": (
                            "missing_canonical_owner"
                            if not owner
                            else f"grounding_{level}"
                        ),
                        "rerun_gate": "mathformerphysicslib:mathlib-grounding-audit",
                    }
                )
        failed_candidate_count += len(failed_candidates)
        concepts.append(
            {
                "concept_id": concept_id,
                "grounding_level": level,
                "mathlib_targets": targets,
                "owner_module": concept.get("owner_module"),
                "complete_allowed": level in {"direct_mathlib", "mathlib_bridge"},
                "blockers": (
                    []
                    if level in {"direct_mathlib", "mathlib_bridge"}
                    else [f"grounding_{level}"]
                ),
                "failed_mathlib_candidates": failed_candidates,
            }
        )
    return {
        "style": "mathformerphysicslib_mathlib_grounding_report",
        "schema_version": 1,
        "summary": dict(sorted(counts.items())),
        "failed_candidate_count": failed_candidate_count,
        "concepts": concepts,
    }


def initialize_redefinition_traversal(
    concept_graph: Mapping[str, Any], grounding: Mapping[str, Any]
) -> dict[str, Any]:
    """Index grounding and pack the native traversal state."""
    grounding_by_id = {
        item["concept_id"]: item for item in grounding.get("concepts", [])
    }
    findings: list[dict[str, Any]] = []
    reuse_metrics = {
        "healthy_downstream_uses": 0,
        "downstream_local_declarations": 0,
        "confirmed_duplicate_owners": 0,
    }
    concepts = concept_graph.get("concepts", [])
    state = dict(
        concepts=concepts,
        grounding_by_id=grounding_by_id,
        cursor=0,
        findings=findings,
        reuse_metrics=reuse_metrics,
    )
    return {"state": state, "has_concepts": bool(concepts)}


def inspect_redefinition_concept(concept, grounding_by_id, findings, reuse_metrics):
    """Apply native ownership and grounding checks to exactly one concept."""
    concept_id = str(concept.get("concept_id"))
    occurrences = [
        item for item in concept.get("occurrences", []) if isinstance(item, Mapping)
    ]
    distinct_modules = sorted({str(item.get("path")) for item in occurrences})
    foundation_occurrences = [item for item in occurrences if item.get("is_foundation")]
    downstream_occurrences = [
        item for item in occurrences if not item.get("is_foundation")
    ]
    foundation_modules = sorted(
        {str(item.get("path")) for item in foundation_occurrences}
    )
    foundation_names = {
        str(decl.get("name"))
        for item in foundation_occurrences
        for decl in item.get("ownership_declarations", [])
        if isinstance(decl, Mapping) and decl.get("name")
    }
    downstream_owners = [
        item for item in downstream_occurrences if item.get("ownership_declarations")
    ]
    healthy_uses = [
        item
        for item in downstream_occurrences
        if not item.get("ownership_declarations") and item.get("imports_foundation")
    ]
    reuse_metrics["healthy_downstream_uses"] += len(healthy_uses)
    reuse_metrics["downstream_local_declarations"] += len(downstream_owners)

    if len(downstream_owners) > 1 and not foundation_modules:
        findings.append(
            {
                "severity": "high",
                "kind": "concept_spread_without_foundation_owner",
                "concept_id": concept_id,
                "evidence": [
                    {
                        "path": item.get("path"),
                        "declarations": item.get("ownership_declarations", []),
                    }
                    for item in downstream_owners[:8]
                ],
                "message": "Competing local declarations appear in multiple modules without a foundation owner.",
            }
        )
    elif foundation_modules:
        for item in downstream_owners:
            local_names = {
                str(decl.get("name"))
                for decl in item.get("ownership_declarations", [])
                if isinstance(decl, Mapping) and decl.get("name")
            }
            exact_duplicates = sorted(local_names & foundation_names)
            bypasses_foundation = not item.get("imports_foundation")
            if exact_duplicates or bypasses_foundation:
                reuse_metrics["confirmed_duplicate_owners"] += 1
                findings.append(
                    {
                        "severity": "high",
                        "kind": "confirmed_competing_concept_owner",
                        "concept_id": concept_id,
                        "owner_module": foundation_modules[0],
                        "evidence": {
                            "downstream_path": item.get("path"),
                            "downstream_declarations": item.get(
                                "ownership_declarations", []
                            ),
                            "foundation_declaration_names": sorted(foundation_names),
                            "exact_duplicate_names": exact_duplicates,
                            "imports_foundation": item.get("imports_foundation"),
                        },
                        "message": "A downstream module declares competing ownership instead of ordinary foundation reuse.",
                    }
                )
    if grounding_by_id.get(concept_id, {}).get("grounding_level") == "local_blocker":
        findings.append(
            {
                "severity": "medium",
                "kind": "unresolved_grounding_blocker",
                "concept_id": concept_id,
                "evidence": distinct_modules[:8],
                "message": "Concept has Mathlib targets but no accepted owner.",
            }
        )


def visit_redefinition_concept(state: Mapping[str, Any]) -> dict[str, Any]:
    """Carry counters and ordered findings forward without mutating input state."""
    cursor = state["cursor"]
    findings = list(state["findings"])
    reuse_metrics = dict(state["reuse_metrics"])
    inspect_redefinition_concept(
        state["concepts"][cursor], state["grounding_by_id"], findings, reuse_metrics
    )
    updated = dict(
        state, cursor=cursor + 1, findings=findings, reuse_metrics=reuse_metrics
    )
    return {"state": updated, "done": cursor + 1 == len(state["concepts"])}


def finish_redefinition_report(state: Mapping[str, Any]) -> dict[str, Any]:
    """Return native findings; a high finding is data rather than an exception."""
    findings = state["findings"]
    reuse_metrics = state["reuse_metrics"]
    return {
        "style": "mathformerphysicslib_redefinition_report",
        "schema_version": 1,
        "ok": not any(item["severity"] == "high" for item in findings),
        "finding_count": len(findings),
        "reuse_metrics": reuse_metrics,
        "findings": findings,
    }


def critic_redefinitions(
    concept_graph: Mapping[str, Any], grounding: Mapping[str, Any]
) -> dict[str, Any]:
    """Find competing declaration ownership without treating normal use as duplication."""
    state = initialize_redefinition_traversal(concept_graph, grounding)["state"]
    for concept in state["concepts"]:
        inspect_redefinition_concept(
            concept, state["grounding_by_id"], state["findings"], state["reuse_metrics"]
        )
    return finish_redefinition_report(state)


def integration_context(
    inventory: Mapping[str, Any], repository_root: Path | None = None
):
    """Initialize native integration findings and resolve the actual index path."""
    foundations_index = (
        FOUNDATIONS_INDEX
        if repository_root is None
        else repository_root / "MathformerPhysicsLib/Lean/Foundations.lean"
    )
    findings: list[dict[str, Any]] = []
    if not inventory.get("foundations_index_exists"):
        findings.append(
            {
                "severity": "high",
                "kind": "missing_foundations_index",
                "message": "Missing libraries/MathformerPhysicsLib/Lean/Foundations.lean.",
            }
        )
    if not inventory.get("manifest_has_foundations"):
        findings.append(
            {
                "severity": "medium",
                "kind": "manifest_missing_foundations",
                "message": "MANIFEST.json does not expose Lean foundations metadata.",
            }
        )
    return foundations_index, findings


def inspect_integration_concept(
    concept: Mapping[str, Any], findings: list[dict[str, Any]], foundations_index: Path
) -> None:
    """Apply the native short-circuit check to one concept."""
    owner = str(concept.get("owner_module") or "")
    if (
        concept.get("owner_status") == "owned"
        and "Foundations" in owner
        and not foundations_index.exists()
    ):
        findings.append(
            {
                "severity": "high",
                "kind": "foundation_owner_not_indexed",
                "concept_id": concept.get("concept_id"),
                "message": "Foundation owner exists but no accepted index can expose it.",
            }
        )


def finish_integration_report(state: Mapping[str, Any]) -> dict[str, Any]:
    """Assemble findings as data; high severity does not raise."""
    findings = state["findings"]
    return {
        "style": "mathformerphysicslib_integration_report",
        "schema_version": 1,
        "ok": not any(item["severity"] == "high" for item in findings),
        "finding_count": len(findings),
        "findings": findings,
    }


def initialize_integration_traversal(
    inventory: Mapping[str, Any],
    concept_graph: Mapping[str, Any],
    repository_root: Path | None = None,
) -> dict[str, Any]:
    """Expose the source iterator as a JSON cursor for bounded workflow execution."""
    index_path, findings = integration_context(inventory, repository_root)
    concepts = concept_graph.get("concepts", [])
    return {
        "state": {
            "concepts": concepts,
            "index": 0,
            "findings": findings,
            "foundations_index": str(index_path),
        },
        "empty": not concepts,
    }


def visit_integration_concept(state: Mapping[str, Any]) -> dict[str, Any]:
    """Inspect one element without mutating the caller's accumulated state."""
    # A workflow loop runs once even for empty input; expose exhaustion without inspection.
    if not state["concepts"] and state["index"] == 0:
        return {"state": dict(state), "done": True}
    findings = list(state["findings"])
    inspect_integration_concept(
        state["concepts"][state["index"]], findings, Path(state["foundations_index"])
    )
    updated = {**state, "index": state["index"] + 1, "findings": findings}
    return {"state": updated, "done": updated["index"] == len(updated["concepts"])}


def critic_integration(
    inventory: Mapping[str, Any],
    concept_graph: Mapping[str, Any],
    repository_root: Path | None = None,
) -> dict[str, Any]:
    """Check manifest, index, and discoverability integration."""
    foundations_index, findings = integration_context(inventory, repository_root)
    for concept in concept_graph.get("concepts", []):
        inspect_integration_concept(concept, findings, foundations_index)
    return finish_integration_report({"findings": findings})


def initialize_api_traversal(concept_graph: Mapping[str, Any]) -> dict[str, Any]:
    """Pack the native iterator and its accumulated findings for step execution."""
    concepts = concept_graph.get("concepts", [])
    return {
        "state": {"concepts": concepts, "index": 0, "findings": []},
        "empty": not concepts,
    }


def inspect_api_concept(
    concept: Mapping[str, Any], findings: list[dict[str, Any]], repository_root: Path
) -> None:
    """Inspect one owner, preserving native matching and finding order."""
    owner = concept.get("owner_module")
    if not owner or "Foundations" not in str(owner):
        return
    path = repository_root / str(owner)
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    required_terms = list(concept.get("api_terms", []))
    present = [term for term in required_terms if term.lower() in text.lower()]
    if required_terms and not present:
        findings.append(
            {
                "severity": "high",
                "kind": "foundation_without_operable_api",
                "concept_id": concept.get("concept_id"),
                "owner_module": owner,
                "message": "Foundation owner lacks expected API terms for downstream theorem use.",
            }
        )
    elif required_terms and len(present) < min(2, len(required_terms)):
        findings.append(
            {
                "severity": "low",
                "kind": "thin_foundation_api",
                "concept_id": concept.get("concept_id"),
                "owner_module": owner,
                "present_terms": present,
                "message": "Foundation owner has a thin API surface; downstream usage examples should be added.",
            }
        )


def visit_api_concept(
    state: Mapping[str, Any], repository_root: Path | None = None
) -> dict[str, Any]:
    """Advance exactly one concept; owner text and term matches are local."""
    findings = list(state["findings"])
    inspect_api_concept(
        state["concepts"][state["index"]],
        findings,
        REPO_ROOT if repository_root is None else repository_root,
    )
    updated = {
        "concepts": state["concepts"],
        "index": state["index"] + 1,
        "findings": findings,
    }
    return {"state": updated, "done": updated["index"] == len(updated["concepts"])}


def finish_api_report(state: Mapping[str, Any]) -> dict[str, Any]:
    """Report high severity as data, without turning it into an exception."""
    findings = state["findings"]
    return {
        "style": "mathformerphysicslib_api_operability_report",
        "schema_version": 1,
        "ok": not any(item["severity"] == "high" for item in findings),
        "finding_count": len(findings),
        "findings": findings,
    }


def critic_api(
    concept_graph: Mapping[str, Any], repository_root: Path | None = None
) -> dict[str, Any]:
    """Check that foundation-owned concepts expose expected API terms."""
    findings: list[dict[str, Any]] = []
    for concept in concept_graph.get("concepts", []):
        inspect_api_concept(
            concept, findings, REPO_ROOT if repository_root is None else repository_root
        )
    return finish_api_report({"findings": findings})


def compact_findings(
    reports: Sequence[Mapping[str, Any]], limit: int = 12
) -> list[dict[str, Any]]:
    """Extract deterministic finding context for generative probes."""
    findings: list[dict[str, Any]] = []
    for report in reports:
        style = str(report.get("style", "unknown_report"))
        for finding in report.get("findings", []):
            if not isinstance(finding, Mapping):
                continue
            findings.append(
                {
                    "source_report": style,
                    "severity": finding.get("severity", "unknown"),
                    "kind": finding.get("kind", "unknown"),
                    "concept_id": finding.get("concept_id"),
                    "owner_module": finding.get("owner_module"),
                    "evidence": finding.get("evidence")
                    or finding.get("present_terms")
                    or [],
                    "message": finding.get("message", ""),
                }
            )
    return findings[:limit]


def report_digest(reports: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Summarize deterministic reports before generative interpretation."""
    severity_counts: Counter[str] = Counter()
    style_counts: Counter[str] = Counter()
    for report in reports:
        style_counts[str(report.get("style", "unknown_report"))] += 1
        for finding in report.get("findings", []):
            if isinstance(finding, Mapping):
                severity_counts[str(finding.get("severity", "unknown"))] += 1
    return {
        "report_styles": dict(sorted(style_counts.items())),
        "severity_counts": dict(sorted(severity_counts.items())),
        "finding_count": sum(severity_counts.values()),
    }


def generative_probe(
    *,
    probe_id: str,
    role: str,
    objective: str,
    failure_modes: Sequence[str],
    deterministic_gates: Sequence[str],
    required_evidence: Sequence[str],
    context_json: str,
) -> dict[str, Any]:
    """Build one structured generative critic probe."""
    prompt = (
        "You are a MathformerPhysicsLib coherence critic. Interpret the "
        "deterministic evidence below and return exactly one compact JSON "
        "object following the expected schema. Do not invent findings without "
        "binding them to evidence. Do not propose direct target-theorem edits "
        "until library ownership, Mathlib grounding, integration, and API "
        "operability are resolved.\n\n"
        f"Role: {role}\n"
        f"Objective: {objective}\n"
        f"Failure modes to search for: {', '.join(failure_modes)}\n"
        f"Required deterministic gates: {', '.join(deterministic_gates)}\n"
        f"Required evidence bindings: {', '.join(required_evidence)}\n\n"
        f"Deterministic context JSON:\n{context_json}\n"
    )
    return {
        "id": probe_id,
        "role": role,
        "objective": objective,
        "failure_modes": list(failure_modes),
        "required_evidence": list(required_evidence),
        "deterministic_gates": list(deterministic_gates),
        "prompt": prompt,
        "expected_report_schema": {
            "style": "mathformerphysicslib_generative_probe_report",
            "required_keys": [
                "probe_id",
                "verdict",
                "evidence_bindings",
                "findings",
                "repair_hypotheses",
                "deterministic_gates_to_rerun",
                "overreach_risks",
            ],
            "allowed_verdicts": [
                "pass",
                "advisory_findings",
                "deterministic_blocker_supported",
                "insufficient_evidence",
            ],
        },
        "acceptance_criteria": [
            "Every blocking finding cites a deterministic report style plus evidence.",
            "Repair hypotheses are library-first and monotonic.",
            "The probe names the deterministic gate that can confirm or reject it.",
            "The probe separates generative interpretation from accepted facts.",
        ],
    }


def generative_plan(reports: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Build advisory generative critic probes with deterministic evidence bindings."""
    digest = report_digest(reports)
    findings = compact_findings(reports)
    deterministic_context = {
        "digest": digest,
        "findings": findings,
    }
    context_json = json.dumps(
        deterministic_context, ensure_ascii=False, indent=2, sort_keys=True
    )
    common_gates = [
        "mathformerphysicslib:coherence-inventory",
        "mathformerphysicslib:concept-canonicalize",
        "mathformerphysicslib:mathlib-grounding-audit",
        "mathformerphysicslib:redefinition-critic",
        "mathformerphysicslib:integration-critic",
        "mathformerphysicslib:api-operability-critic",
        "mathformerphysicslib:coherence-gate",
    ]
    probes = [
        generative_probe(
            probe_id="mathlib_maximality_critic",
            role="Mathlib maximality critic",
            objective="Find local physics support that should be expressed through existing Mathlib carriers, operators, relations, or calculus APIs before adding local wrappers.",
            failure_modes=[
                "avoidable local carrier",
                "opaque wrapper around Mathlib API",
                "broad import masking missing grounding",
            ],
            deterministic_gates=[
                "mathformerphysicslib:mathlib-grounding-audit",
                "mathlib.grounding_maximize",
                "mathlib.import.plan",
            ],
            required_evidence=[
                "concept_id",
                "mathlib_targets",
                "owner_module",
                "grounding_level",
            ],
            context_json=context_json,
        ),
        generative_probe(
            probe_id="redefinition_spread_critic",
            role="Redefinition and spread critic",
            objective="Identify recurring concepts that are owned in more than one place, named differently across case modules, or missing a single foundation owner.",
            failure_modes=[
                "concept spread",
                "duplicate local definition",
                "downstream case bypasses foundation owner",
            ],
            deterministic_gates=[
                "mathformerphysicslib:concept-canonicalize",
                "mathformerphysicslib:redefinition-critic",
            ],
            required_evidence=[
                "concept_id",
                "occurrence paths",
                "owner_module",
                "source_report",
            ],
            context_json=context_json,
        ),
        generative_probe(
            probe_id="integration_discoverability_critic",
            role="Integration and discoverability critic",
            objective="Check whether accepted or candidate support is reachable through index imports, manifest metadata, docs, hub actions, tests, and object workbench handoffs.",
            failure_modes=[
                "missing index export",
                "manifest drift",
                "unreachable support",
                "hub route missing",
            ],
            deterministic_gates=[
                "mathformerphysicslib:integration-critic",
                "control:workflow-router-coverage",
                "control:all",
            ],
            required_evidence=[
                "path",
                "manifest flag",
                "route id",
                "action id",
                "source_report",
            ],
            context_json=context_json,
        ),
        generative_probe(
            probe_id="physics_semantic_erasure_critic",
            role="Physics semantic-erasure critic",
            objective="Stress-test whether foundations preserve vectors, units, frames, regimes, law witnesses, and assumptions instead of collapsing them to raw scalar algebra.",
            failure_modes=[
                "scalar erasure",
                "unit erasure",
                "frame erasure",
                "hidden law",
                "over-broad assumption",
            ],
            deterministic_gates=[
                "physics-lean:drift-pathology-monitor",
                "physics-lean:audit-grounding",
                "mathformerphysicslib:api-operability-critic",
            ],
            required_evidence=[
                "object_class",
                "owner_module",
                "api_terms",
                "source-backed assumption label",
            ],
            context_json=context_json,
        ),
        generative_probe(
            probe_id="api_usefulness_critic",
            role="Downstream API usefulness critic",
            objective="Ask whether a downstream Lean theorem can use each foundation through public projections, bridge lemmas, imports, and examples without private unfolding or target-shaped assumptions.",
            failure_modes=[
                "private unfolding required",
                "no projection lemma",
                "thin API",
                "target theorem still carries generated support",
            ],
            deterministic_gates=[
                "mathformerphysicslib:api-operability-critic",
                "physics-lean:foundation-verify",
                "mathformerlib:promotion-gate",
            ],
            required_evidence=[
                "owner_module",
                "present_terms",
                "missing API term",
                "downstream import path",
            ],
            context_json=context_json,
        ),
        generative_probe(
            probe_id="negative_control_incoherent_repair",
            role="Negative-control critic",
            objective="Construct a plausible compiling but incoherent repair and state exactly which deterministic gate must reject it.",
            failure_modes=[
                "target-shaped hypothesis",
                "axiom or sorry",
                "weakened theorem",
                "local fake support",
                "hidden strengthening",
            ],
            deterministic_gates=common_gates
            + [
                "autoformalization-result-realness-verifier",
                "mathformerlib:promotion-gate",
            ],
            required_evidence=[
                "forbidden shortcut",
                "expected rejecting gate",
                "minimal failing example",
            ],
            context_json=context_json,
        ),
        generative_probe(
            probe_id="meta_critic_disagreement_overreach",
            role="Meta-critic",
            objective="Detect disagreement between deterministic critics, missing evidence, and generative overreach before any finding blocks completion.",
            failure_modes=[
                "unsupported blocker",
                "critic disagreement",
                "missing evidence",
                "overreach beyond deterministic reports",
            ],
            deterministic_gates=common_gates,
            required_evidence=[
                "conflicting report styles",
                "unsupported claim",
                "rerun gate",
            ],
            context_json=context_json,
        ),
    ]
    return {
        "style": "mathformerphysicslib_generative_critic_plan",
        "schema_version": 1,
        "finding_count_seen": digest["finding_count"],
        "deterministic_context": deterministic_context,
        "probe_count": len(probes),
        "probes": probes,
        "codex_exec_policy": {
            "enabled": True,
            "execution_is_optional": True,
            "raw_outputs_must_be_archived": True,
            "recommended_runner": "skills/control/skill-test-program-orchestrator/scripts/run_content_skill_codex_exec_tests.py",
        },
        "blocking_policy": {
            "generative_findings_are_advisory": True,
            "may_block_only_with_deterministic_evidence": True,
            "required_before_blocking": [
                "source report citation",
                "deterministic evidence binding",
                "named rerun gate",
                "repair planner action or explicit blocker",
            ],
        },
    }


def repair_plan(reports: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Build monotonic repair actions from reports."""
    actions: list[dict[str, Any]] = []
    for report in reports:
        for finding in report.get("findings", []):
            kind = finding.get("kind")
            if kind in {
                "concept_spread_without_foundation_owner",
                "confirmed_competing_concept_owner",
            }:
                action = "consolidate_concept_owner"
            elif kind in {
                "manifest_missing_foundations",
                "missing_foundations_index",
                "foundation_owner_not_indexed",
            }:
                action = "repair_integration_surface"
            elif kind in {"foundation_without_operable_api", "thin_foundation_api"}:
                action = "add_operable_bridge_api"
            else:
                action = "record_or_block_gap"
            actions.append(
                {
                    "action": action,
                    "severity": finding.get("severity"),
                    "concept_id": finding.get("concept_id"),
                    "source_kind": kind,
                    "monotonicity_gate": "must reduce duplicate, missing integration, ungrounded, or unresolved blocker counts without reducing Mathlib grounding",
                }
            )
    return {
        "style": "mathformerphysicslib_coherence_repair_plan",
        "schema_version": 1,
        "action_count": len(actions),
        "actions": actions,
        "status": "repair_required" if actions else "no_repairs_required",
    }


def coherence_gate(reports: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Aggregate reports into a coherence gate result."""
    high = 0
    medium = 0
    for report in reports:
        for finding in report.get("findings", []):
            if finding.get("severity") == "high":
                high += 1
            elif finding.get("severity") == "medium":
                medium += 1
    status = "accepted"
    if high:
        status = "blocked"
    elif medium:
        status = "warn"
    release = build_release_status(
        workflow_executed=True,
        checks_passed=True,
        artifact_status="promoted" if not high else "blocked",
        library_status=status,
        blockers=[f"high_coherence_findings:{high}"] if high else (),
        terminal_states=["repair_required"] if high else (),
    )
    return {
        "style": "mathformerphysicslib_coherence_gate",
        "schema_version": 2,
        "ok": True,
        "status": status,
        "high_findings": high,
        "medium_findings": medium,
        **release,
        "property_gate": {
            "canonical_ownership": high == 0,
            "maximal_mathlib_grounding": high == 0,
            "no_silent_redefinition": high == 0,
            "integration": high == 0,
            "api_operability": high == 0,
            "physics_semantics": True,
            "evidence_complete": True,
        },
    }


def markdown_report(gate: Mapping[str, Any], repair: Mapping[str, Any]) -> str:
    """Render a compact Markdown report."""
    lines = [
        "# MathformerPhysicsLib Coherence Report",
        "",
        f"Status: `{gate.get('status')}`",
        f"High findings: `{gate.get('high_findings')}`",
        f"Medium findings: `{gate.get('medium_findings')}`",
        f"Repair actions: `{repair.get('action_count')}`",
        "",
        "## Next Actions",
    ]
    for action in repair.get("actions", [])[:20]:
        lines.append(
            f"- `{action.get('action')}` for `{action.get('concept_id') or 'library'}` from `{action.get('source_kind')}`."
        )
    if not repair.get("actions"):
        lines.append("- No deterministic repairs required.")
    return "\n".join(lines) + "\n"


def self_test_inventory() -> dict[str, Any]:
    """Construct the native two-concept fixture, without filesystem enumeration."""
    return {
        "style": "mathformerphysicslib_inventory",
        "schema_version": 1,
        "foundations_index_exists": True,
        "manifest_has_foundations": True,
        "concept_occurrence_index": {
            "vector_field.real.euclidean3": [
                {
                    "path": "libraries/MathformerPhysicsLib/Lean/Foundations/Fields.lean",
                    "is_foundation": True,
                    "ownership_declarations": [
                        {"kind": "abbrev", "name": "RealVector3", "line": 1}
                    ],
                },
                {
                    "path": "libraries/MathformerPhysicsLib/Lean/formalphysics_0000/MathformerPhysics.lean",
                    "is_foundation": False,
                    "imports_foundation": True,
                    "ownership_declarations": [],
                    "occurrence_kind": "theorem_use",
                },
            ],
            "physical_law.witness": [
                {
                    "path": "libraries/MathformerPhysicsLib/Lean/formalphysics_0000/MathformerPhysics.lean",
                    "is_foundation": False,
                    "imports_foundation": False,
                    "ownership_declarations": [
                        {"kind": "structure", "name": "LocalLaw", "line": 10}
                    ],
                },
                {
                    "path": "libraries/MathformerPhysicsLib/Lean/formalphysics_0020/MathformerPhysics.lean",
                    "is_foundation": False,
                    "imports_foundation": False,
                    "ownership_declarations": [
                        {"kind": "structure", "name": "OtherLocalLaw", "line": 20}
                    ],
                },
            ],
        },
    }


def self_test_critics(
    inventory: Mapping[str, Any],
    graph: Mapping[str, Any],
    grounding: Mapping[str, Any],
    repository_root: Path | None = None,
) -> dict[str, Any]:
    """Run the native critics in source order."""
    redef = critic_redefinitions(graph, grounding)
    integ = critic_integration(inventory, graph, repository_root)
    api = critic_api(graph, repository_root)
    return {"reports": [redef, integ, api]}


def finish_self_test(
    graph: Mapping[str, Any], grounding: Mapping[str, Any], critics: Mapping[str, Any]
) -> dict[str, Any]:
    """Build recommendations and probes, then enforce native fixture assertions."""
    redef, integ, api = critics["reports"]
    repair = repair_plan([redef, integ, api])
    gate = coherence_gate([redef, integ, api])
    gen = generative_plan([redef, integ, api])
    assert graph["concept_count"] == 2
    assert grounding["concepts"]
    assert grounding["failed_candidate_count"] >= 1
    assert any(
        item["failed_mathlib_candidates"]
        for item in grounding["concepts"]
        if not item["complete_allowed"]
    )
    assert any(
        item["kind"] == "concept_spread_without_foundation_owner"
        for item in redef["findings"]
    )
    assert redef["reuse_metrics"]["healthy_downstream_uses"] == 1
    assert gen["probe_count"] == 7
    assert all("expected_report_schema" in probe for probe in gen["probes"])
    assert all(
        "Deterministic context JSON:" in probe["prompt"] for probe in gen["probes"]
    )
    assert gen["blocking_policy"]["may_block_only_with_deterministic_evidence"] is True
    return {
        "ok": True,
        "graph": graph,
        "grounding": grounding,
        "repair": repair,
        "gate": gate,
        "generative": gen,
    }


def self_test_payload(repository_root: Path | None = None) -> dict[str, Any]:
    """Run an in-memory self-test of the shared workflow."""
    inventory = self_test_inventory()
    graph = canonicalize(inventory)
    grounding = audit_grounding(graph)
    critics = self_test_critics(inventory, graph, grounding, repository_root)
    return finish_self_test(graph, grounding, critics)
