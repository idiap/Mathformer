#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Design Mathlib-first MathformerPhysicsLib foundation surfaces."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

MODULES = {
    "Carriers": "libraries/MathformerPhysicsLib/Lean/Foundations/Carriers.lean",
    "Fields": "libraries/MathformerPhysicsLib/Lean/Foundations/Fields.lean",
    "Operators": "libraries/MathformerPhysicsLib/Lean/Foundations/Operators.lean",
    "HilbertSpace": "libraries/MathformerPhysicsLib/Lean/Foundations/HilbertSpace.lean",
    "UnboundedOperators": "libraries/MathformerPhysicsLib/Lean/Foundations/UnboundedOperators.lean",
    "PositionMomentumModels": "libraries/MathformerPhysicsLib/Lean/Foundations/PositionMomentumModels.lean",
    "VectorCalculus": "libraries/MathformerPhysicsLib/Lean/Foundations/VectorCalculus.lean",
    "Units": "libraries/MathformerPhysicsLib/Lean/Foundations/Units.lean",
    "Laws": "libraries/MathformerPhysicsLib/Lean/Foundations/Laws.lean",
    "Contexts": "libraries/MathformerPhysicsLib/Lean/Foundations/Contexts.lean",
}

DECLARATIONS = {
    "vector_field.real.euclidean3": [
        "RealVector3",
        "RealVectorField3",
        "evalRealVectorField3",
    ],
    "projection.fin3.component": [
        "RealVector3",
        "realVector3Component",
        "realVector3Component_apply",
    ],
    "linear_operator.field": ["LinearFieldOperator", "applyLinearFieldOperator"],
    "curl_like_linear_operator": ["CurlLikeOperator"],
    "time_derivative_linear_operator": ["TimeDerivativeOperator"],
    "physical_law.witness": ["PhysicalLawWitness", "physicalLawHolds"],
    "unit_dimension.compatible": ["DimensionCompatible", "dimensionCompatibleEq"],
    "generated_support.assumption_label": [
        "GeneratedSupportAssumption",
        "generatedSupportHolds",
    ],
    "hilbert_state.inner_product_space": [
        "HilbertStateCarrier",
        "hilbertInner",
        "hilbertInner_apply",
    ],
    "hilbert_state.orthogonality_projection": [
        "HilbertOrthogonalityWitness",
        "HilbertProjectionWitness",
    ],
    "hilbert_state.orthonormal_basis": ["HilbertBasisSurface"],
    "hilbert_operator.adjoint_self_adjoint": [
        "HilbertBoundedOperator",
        "applyHilbertOperator",
        "hilbertExpectation",
        "fluctuationKet",
        "HilbertOperatorAdjointWitness",
        "SelfAdjointOperatorWitness",
        "UnitaryOperatorWitness",
    ],
    "hilbert_operator.hilbert_schmidt": ["HilbertSchmidtWithBasisWitness"],
    "unbounded_operator.position_momentum_core": [
        "UnboundedHilbertOperator",
        "MemDomain",
        "apply",
        "restrictToSubmodule",
        "restrictToSubmodule_apply",
        "graph",
        "HasDenseDomain",
        "IsClosedUnboundedOperator",
        "SymmetricUnboundedOperator",
        "UnboundedAdjointWitness",
        "SelfAdjointUnboundedOperatorWitness",
        "CommonInvariantCore",
        "commutatorValueOnCore",
        "PositionMomentumPair",
        "canonicalCommutatorExpectationOnNormalizedCore",
    ],
    "position_momentum.schwartz_l2_model": [
        "RealSchwartzWavefunction",
        "realSchwartzDerivative",
        "SchwartzL2PositionMomentumModel",
        "SchwartzL2PositionMomentumModel.toPositionMomentumPair",
        "canonicalCommutatorExpectationOnSchwartzCore",
    ],
    "position_momentum.real_line_l2_instantiation": [
        "RealLineL2Wavefunction",
        "realSchwartzToL2",
        "realSchwartzToL2_apply_ae",
        "RealLineL2SchwartzRangeDense",
        "realSchwartzL2RangeSubmodule",
        "realSchwartzToL2_mem_rangeSubmodule",
        "realSchwartzL2RangeSubmodule_coe",
        "RealLineL2SchwartzRangeSubmoduleDense",
        "realSchwartzRangeSubmoduleDense_of_denseRange",
        "RealLineL2CoreIsSchwartzRange",
        "RealLineL2CoreEqualsSchwartzRangeSubmodule",
        "realLineL2CoreIsSchwartzRange_of_submodule_eq",
        "realLineL2CoreDense_of_rangeSubmodule",
        "RealLineL2CoreEqualsSchwartzRangeSubmodule.of_set_range",
        "RealLinePositionActionIsCoordinateMultiplication",
        "RealLineMomentumActionIsDerivative",
        "RealLineSchwartzCommutatorAction",
        "RealLineSchwartzCanonicalCommutator",
        "RealLineSchwartzCanonicalCommutatorAsSchwartzMap",
        "realLineSchwartzCanonicalCommutatorAsSchwartzMap_of_pointwise",
        "realLineSchwartzCanonicalCommutator_of_schwartzMap",
        "realLineMomentumActionIsDerivative",
        "RealLineL2PositionMomentumModel",
        "RealLineL2PositionMomentumModel.core_dense_from_schwartz_range",
        "RealLineL2PositionMomentumModel.common_core_eq_schwartz_range_submodule",
        "RealLineL2PositionMomentumModel.position_coordinate_multiplication",
        "RealLineL2PositionMomentumModel.momentum_derivative",
        "RealLineL2PositionMomentumModel.position_action_matches_toL2",
        "RealLineL2PositionMomentumModel.momentum_action_matches_toL2",
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
        "RealLineL2ClosureFrontier.toSpectralClosureTargets",
        "canonicalCommutatorExpectationOnRealLineL2SchwartzCore",
    ],
    "dirac.transition_amplitude": [
        "transitionAmplitude",
        "transitionAmplitude_apply",
        "probabilityFromAmplitude",
        "probabilityFromAmplitude_apply",
        "probabilityFromAmplitude_congr",
        "NormalizedStateWitness",
        "HilbertOrthogonalityWitness",
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
    ],
    "dirac.expectation_value": [
        "hilbertExpectation",
        "HilbertBoundedOperator",
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
    ],
    "dirac.fluctuation_ket": ["fluctuationKet", "diracImaginaryQuotient"],
    "dirac.position_wavefunction": [
        "PositionWavefunction",
        "positionExpectationIntegrand",
        "positionExpectationIntegrand_apply",
        "PositionResolutionIdentityMeasureKernel",
        "positionExpectationIntegral",
        "positionExpectationIntegral_apply",
    ],
    "dirac.imaginary_part_identity": [
        "DiracConjugateSymmetryWitness",
        "diracImaginaryQuotient",
        "diracImaginaryQuotient_star_eq_im",
        "diracImaginaryQuotient_eq_im_of_conjugate",
        "diracImaginaryQuotient_sq_eq_im_sq_of_conjugate",
    ],
    "commutator.algebra": ["commutator"],
}

PROMOTION_LADDERS = {
    "hilbert_state.inner_product_space": [
        {
            "level": 0,
            "name": "carrier_bridge",
            "status": "candidate_generated",
            "gate": "compile Mathlib-backed carrier, inner product bridge, and completeness parameters",
        },
        {
            "level": 1,
            "name": "norm_metric_axiom_reuse",
            "status": "open_recursive_frontier",
            "gate": "reuse Mathlib norm, distance, Cauchy-Schwarz, parallelogram, and polarization APIs without local reproving",
        },
        {
            "level": 2,
            "name": "physics_state_api",
            "status": "open_recursive_frontier",
            "gate": "bind quantum-state roles to complete complex Hilbert carriers used by downstream TDSE examples",
        },
    ],
    "hilbert_state.orthogonality_projection": [
        {
            "level": 0,
            "name": "orthogonality_projection_witnesses",
            "status": "candidate_generated",
            "gate": "compile explicit orthogonality and projection-like witness records",
        },
        {
            "level": 1,
            "name": "mathlib_projection_theorem_reuse",
            "status": "open_recursive_frontier",
            "gate": "ground closed-subspace projection and best-approximation statements in Mathlib orthogonalProjection APIs",
        },
        {
            "level": 2,
            "name": "closed_subspace_decomposition",
            "status": "open_recursive_frontier",
            "gate": "expose reusable direct-sum/decomposition surfaces for physics modal splits",
        },
    ],
    "hilbert_state.orthonormal_basis": [
        {
            "level": 0,
            "name": "hilbert_basis_reexport",
            "status": "candidate_generated",
            "gate": "compile Mathlib HilbertBasis surface",
        },
        {
            "level": 1,
            "name": "bessel_parseval_reuse",
            "status": "open_recursive_frontier",
            "gate": "reuse Mathlib orthonormal-coordinate, Bessel, and Parseval theorem surfaces",
        },
        {
            "level": 2,
            "name": "physics_basis_examples",
            "status": "open_recursive_frontier",
            "gate": "connect finite-dimensional, l2, L2, and Fourier-basis examples to physics source statements",
        },
    ],
    "hilbert_operator.adjoint_self_adjoint": [
        {
            "level": 0,
            "name": "bounded_operator_witnesses",
            "status": "candidate_generated",
            "gate": "compile bounded operator, adjoint relation, self-adjoint, and unitary witness records",
        },
        {
            "level": 1,
            "name": "mathlib_adjoint_api_reuse",
            "status": "open_recursive_frontier",
            "gate": "ground witnesses in Mathlib ContinuousLinearMap adjoint, self-adjoint, isometry, and unitary APIs where available",
        },
        {
            "level": 2,
            "name": "quantum_observable_evolution_api",
            "status": "open_recursive_frontier",
            "gate": "connect self-adjoint Hamiltonians and unitary evolution to source-backed quantum mechanics examples",
        },
    ],
    "hilbert_operator.hilbert_schmidt": [
        {
            "level": 0,
            "name": "basis_relative_summability_witness",
            "status": "candidate_generated",
            "gate": "compile a basis-relative summability witness without claiming a full Hilbert-Schmidt theory",
        },
        {
            "level": 1,
            "name": "matrix_trace_grounding",
            "status": "open_recursive_frontier",
            "gate": "ground finite-dimensional Hilbert-Schmidt norm and matrix trace inner product in Mathlib matrix APIs",
        },
        {
            "level": 2,
            "name": "operator_ideal_frontier",
            "status": "open_recursive_frontier",
            "gate": "record explicit blockers or promoted APIs for infinite-dimensional Hilbert-Schmidt operators",
        },
    ],
    "unbounded_operator.position_momentum_core": [
        {
            "level": 0,
            "name": "domain_bearing_operator_surface",
            "status": "candidate_generated",
            "gate": "compile Submodule-domain operator, graph, dense-domain, symmetry, and self-adjoint witness surfaces",
        },
        {
            "level": 1,
            "name": "common_invariant_core_commutator",
            "status": "candidate_generated",
            "gate": "compile common invariant domain/core and canonical commutator expectation theorem for position and momentum",
        },
        {
            "level": 2,
            "name": "schwartz_or_l2_position_momentum_model",
            "status": "open_recursive_frontier",
            "gate": "instantiate the abstract core with concrete L2/Schwartz position and momentum operators or record a Mathlib blocker",
        },
        {
            "level": 3,
            "name": "spectral_self_adjoint_api",
            "status": "open_recursive_frontier",
            "gate": "ground full self-adjoint spectral/operator-domain semantics in Mathlib APIs before using spectral consequences",
        },
    ],
    "position_momentum.schwartz_l2_model": [
        {
            "level": 0,
            "name": "mathlib_schwartz_wavefunction_anchor",
            "status": "candidate_generated",
            "gate": "compile RealSchwartzWavefunction and realSchwartzDerivative from Mathlib SchwartzMap APIs",
        },
        {
            "level": 1,
            "name": "schwartz_l2_operator_realization",
            "status": "candidate_generated",
            "gate": "compile a model interface connecting Schwartz actions, Hilbert embedding, unbounded domains, and canonical commutator",
        },
        {
            "level": 2,
            "name": "concrete_l2_instantiation",
            "status": "open_recursive_frontier",
            "gate": "instantiate the Hilbert carrier as an L2 space with a dense Schwartz core or record the precise Mathlib blocker",
        },
        {
            "level": 3,
            "name": "spectral_and_essential_self_adjointness",
            "status": "open_recursive_frontier",
            "gate": "ground self-adjoint closure, spectral calculus, and essential self-adjointness claims before downstream spectral consequences",
        },
    ],
    "position_momentum.real_line_l2_instantiation": [
        {
            "level": 0,
            "name": "real_line_l2_mathlib_carrier",
            "status": "candidate_generated",
            "gate": "compile RealLineL2Wavefunction as MeasureTheory.Lp ℂ 2 volume and realSchwartzToL2 via SchwartzMap.toLpCLM",
        },
        {
            "level": 1,
            "name": "schwartz_to_l2_embedding_evidence",
            "status": "candidate_generated",
            "gate": "compile almost-everywhere agreement for the Mathlib Schwartz-to-L2 embedding",
        },
        {
            "level": 2,
            "name": "formalphysics_0014_real_line_l2_frontier_bridges",
            "status": "candidate_generated",
            "gate": "compile ten 0014 bridge surfaces for range submodule, core density, action laws, embedding compatibility, and pointwise commutator obligation routing",
        },
        {
            "level": 3,
            "name": "formalphysics_0014_commutator_transport_and_closure_targets",
            "status": "candidate_generated",
            "gate": "compile the next ten 0014 bridge surfaces for Schwartz commutator transport, transported canonical commutator, essential-self-adjointness targets, and spectral-closure target routing",
        },
        {
            "level": 4,
            "name": "formalphysics_0014_remaining_target_grounding",
            "status": "candidate_generated",
            "gate": "compile structured common-core equality, SchwartzMap commutator equality, restricted core operators, graph-core targets, and typed spectral-availability obligations",
        },
        {
            "level": 5,
            "name": "dense_schwartz_core_instantiation",
            "status": "open_recursive_frontier",
            "gate": "prove or block DenseRange realSchwartzToL2 and exact common-core equality with the Schwartz image for concrete models",
        },
        {
            "level": 6,
            "name": "real_line_position_momentum_self_adjointness",
            "status": "open_recursive_frontier",
            "gate": "prove or block the typed graph-core closure targets for coordinate multiplication and derivative momentum on the Schwartz core",
        },
    ],
    "dirac.transition_amplitude": [
        {
            "level": 0,
            "name": "amplitude_probability_surface",
            "status": "candidate_generated",
            "gate": "compile transition amplitude and probability-from-amplitude surfaces over Mathlib inner products",
        },
        {
            "level": 1,
            "name": "formalphysics_0015_vacuum_rabi_born_rule",
            "status": "candidate_generated",
            "gate": "compile two-level Rabi state expansion, transition-amplitude extraction, complex norm-square, and Born-rule probability bridge without target-restating witnesses",
        },
        {
            "level": 2,
            "name": "born_rule_projection_reuse",
            "status": "open_recursive_frontier",
            "gate": "ground measurement probabilities in projection or orthonormal-basis APIs instead of scalar placeholders",
        },
    ],
    "dirac.expectation_value": [
        {
            "level": 0,
            "name": "expectation_value_surface",
            "status": "candidate_generated",
            "gate": "compile expectation values as inner products of states and bounded operator actions",
        },
        {
            "level": 1,
            "name": "formalphysics_0021_hellmann_feynman_bridge",
            "status": "candidate_generated",
            "gate": "compile parameterized expectation, eigenstate-to-expectation identity, derivative uniqueness, and differentiated-eigen-equation Hellmann-Feynman bridge",
        },
        {
            "level": 2,
            "name": "observable_expectation_api",
            "status": "open_recursive_frontier",
            "gate": "connect expectation values to self-adjoint observables and source-backed differentiation laws",
        },
    ],
    "dirac.fluctuation_ket": [
        {
            "level": 0,
            "name": "fluctuation_ket_surface",
            "status": "candidate_generated",
            "gate": "compile fluctuation ket and braket quotient surfaces",
        },
        {
            "level": 1,
            "name": "uncertainty_theorem_reuse",
            "status": "open_recursive_frontier",
            "gate": "ground Heisenberg bounds in Cauchy-Schwarz, commutator, and variance APIs",
        },
    ],
    "dirac.position_wavefunction": [
        {
            "level": 0,
            "name": "position_wavefunction_surface",
            "status": "candidate_generated",
            "gate": "compile position wavefunction and Born-rule integrand surfaces",
        },
        {
            "level": 1,
            "name": "formalphysics_0052_measure_integral_bridge",
            "status": "candidate_generated",
            "gate": "compile position resolution measure-kernel witness and Mathlib integral surface for Born-rule expectation values",
        },
        {
            "level": 2,
            "name": "measure_theoretic_resolution_identity",
            "status": "open_recursive_frontier",
            "gate": "promote or block measure-theoretic resolution-of-identity and delta-kernel support",
        },
    ],
    "dirac.imaginary_part_identity": [
        {
            "level": 0,
            "name": "dirac_conjugate_symmetry_surface",
            "status": "candidate_generated",
            "gate": "compile conjugate-symmetry and braket quotient surfaces",
        },
        {
            "level": 1,
            "name": "formalphysics_0074_complex_im_projection_bridge",
            "status": "candidate_generated",
            "gate": "compile conjugate-symmetry bridge from Dirac imaginary quotient to Complex.im and its square identity",
        },
        {
            "level": 2,
            "name": "complex_imaginary_projection_api",
            "status": "open_recursive_frontier",
            "gate": "ground real-valued imaginary-part identities in Complex.im and Mathlib inner-product symmetry",
        },
    ],
}

DEFAULT_PROMOTION_LADDER = [
    {
        "level": 0,
        "name": "mathlib_grounded_surface",
        "status": "candidate_generated",
        "gate": "compile or reuse the Mathlib-grounded surface",
    },
    {
        "level": 1,
        "name": "theorem_usable_api",
        "status": "open_recursive_frontier",
        "gate": "promote public projections, bridge lemmas, or explicit missing-API blockers for downstream theorem use",
    },
]


def load_json(path: Path | None) -> dict[str, Any]:
    """Load optional JSON."""
    if path is None:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def module_for(item: dict[str, Any]) -> str:
    """Choose the target foundation module family."""
    return str(item.get("foundation_module") or "Contexts")


def design_surface(item: dict[str, Any]) -> dict[str, Any]:
    """Design one surface item."""
    object_id = str(item.get("object_id"))
    module = module_for(item)
    declarations = DECLARATIONS.get(object_id, [object_id.replace(".", "_")])
    bridge_required = module in {
        "Units",
        "Laws",
        "Contexts",
        "VectorCalculus",
        "HilbertSpace",
        "UnboundedOperators",
        "PositionMomentumModels",
    }
    state = "candidate_generated" if bridge_required else "mathlib_reused"
    promotion_ladder = PROMOTION_LADDERS.get(object_id, DEFAULT_PROMOTION_LADDER)
    recursive_frontier = [
        {
            "object_id": object_id,
            "level": step["level"],
            "name": step["name"],
            "owner_skill": "mathformerphysicslib-foundation-surface-designer",
            "action": "expand_foundation_surface_then_rerun_verifier_and_workbench",
            "gate": step["gate"],
        }
        for step in promotion_ladder
        if step["status"] == "open_recursive_frontier"
    ]
    return {
        "object_id": object_id,
        "object_class": item.get("object_class"),
        "display_name": item.get("display_name"),
        "foundation_module": module,
        "module_path": MODULES.get(module, MODULES["Contexts"]),
        "mathlib_targets": item.get("mathlib_search_terms", []),
        "state": state,
        "surface_kind": (
            "thin_bridge" if bridge_required else "mathlib_reexport_surface"
        ),
        "declarations": declarations,
        "abstraction_boundary": (
            "level-0 declaration records physics role/provenance while preserving Mathlib carrier; richer APIs require recursive promotion gates"
            if bridge_required
            else "no new carrier abstraction; use verified Mathlib surface directly"
        ),
        "promotion_ladder": promotion_ladder,
        "recursive_frontier": recursive_frontier,
        "acceptance_gates": [
            "foundation module has Mathlib grounding comments",
            "no sorry/admit/axiom or Prop := True final support",
            "object workbench can classify promoted support as mathformer_reused",
            "open recursive frontier items are mapped before claiming exhaustive Hilbert-space support",
            "downstream repair remains blocked until reuse, promotion, or explicit blocker",
        ],
    }


def build_plan(object_packet: dict[str, Any]) -> dict[str, Any]:
    """Build the surface design plan using the shared single-pass steps."""
    surfaces = design_surfaces(object_packet)
    modules = collect_modules(surfaces)
    return assemble_plan(object_packet, surfaces, modules)


def design_surfaces(object_packet: dict[str, Any]) -> list[dict[str, Any]]:
    """Design dictionary entries in input order; preserve native shape errors."""
    return [
        design_surface(item)
        for item in object_packet.get("objects", [])
        if isinstance(item, dict)
    ]


def collect_modules(surfaces: list[dict[str, Any]]) -> list[str]:
    """Collect sorted distinct paths after all surface designs succeed."""
    return sorted({item["module_path"] for item in surfaces})


def assemble_plan(object_packet, surfaces, modules) -> dict[str, Any]:
    """Flatten open frontiers and pack the source-owned planning metadata."""
    recursive_frontier = [
        frontier_item
        for surface in surfaces
        for frontier_item in surface.get("recursive_frontier", [])
        if isinstance(frontier_item, dict)
    ]
    return {
        "style": "physics_foundation_surface_plan",
        "source_packet_id": object_packet.get("packet_id"),
        "surface_count": len(surfaces),
        "surfaces": surfaces,
        "recursive_policy": {
            "recursive": True,
            "exhaustive_expansion_required": True,
            "initial_surfaces_are_level_0_not_terminal_theory": True,
            "rerun_gates": [
                "foundation.physics_object_intake",
                "foundation.mathlib_grounding",
                "foundation.surface_design",
                "foundation.lean_draft",
                "foundation.verify",
                "foundation.recursive_expansion",
                "foundation.promote",
                "foundation.downstream_regression",
            ],
        },
        "recursive_frontier_count": len(recursive_frontier),
        "recursive_frontier": recursive_frontier,
        "accepted_index": "libraries/MathformerPhysicsLib/Lean/Foundations.lean",
        "accepted_index_imports": modules,
        "terminal_state": "surface_plan_complete" if surfaces else "no_surfaces",
    }


def parse_args(
    argv: Sequence[str] | None = None, *, prog: str | None = None
) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__, prog=prog)
    parser.add_argument("--object-packet", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def fixed_packet() -> dict[str, Any]:
    """The exact main --self-test packet; no input files are read."""
    return {
        "packet_id": "self_test",
        "objects": [
            {
                "object_id": "vector_field.real.euclidean3",
                "object_class": "vector_field",
                "display_name": "Real vector field",
                "foundation_module": "Fields",
                "mathlib_search_terms": ["EuclideanSpace", "Fin"],
            }
        ],
    }


def check_self_test(args, plan):
    """Run the source assertions only in the self-test branch."""
    if args.self_test:
        assert plan["surface_count"] == 1
        assert plan["surfaces"][0]["module_path"].endswith("Fields.lean")
        assert plan["recursive_policy"]["recursive"] is True
        assert plan["recursive_frontier_count"] >= 1
    return plan


def emit_plan(args, plan, *, working_directory: Path | None = None, before_write=None):
    """Serialize, optionally write, then print, in the native order.

    Remote adapters supply cwd and a write policy; direct callers retain the
    original process-cwd behavior and exceptions.
    """
    output = json.dumps(plan, ensure_ascii=False, indent=2)
    if args.output:
        path = (
            args.output
            if working_directory is None
            else working_directory / args.output
        )
        if before_write is not None:
            before_write(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output + "\n", encoding="utf-8")
    if args.json or not args.output:
        print(output)
    return output, 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run surface design."""
    args = parse_args(argv)
    packet = fixed_packet() if args.self_test else load_json(args.object_packet)
    plan = check_self_test(args, build_plan(packet))
    return emit_plan(args, plan)[1]


if __name__ == "__main__":
    raise SystemExit(main())
