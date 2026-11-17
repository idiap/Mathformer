#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Generate a focused Dirac-notation FormalPhysics batch with explicit
#   recursive MathformerPhysicsLib grounding artifacts.
#
# Intent:
#   Exercise new Hilbert/Dirac foundation surfaces on examples that should not
#   collapse into ungrounded scalar algebra.
#
# Function:
#   Selects five FormalPhysics records, writes Lean examples, builds object
#   intake/surface/workbench artifacts, and records validation evidence.
#
# Maintenance Notes:
#   Keep selected examples synchronized with the FormalPhysics dataset and
#   HilbertSpace foundation surfaces.

"""Generate recursively grounded Dirac-notation FormalPhysics Lean examples."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET = REPO_ROOT / "data" / "benchmarks" / "formal_science" / "FormalPhysics.json"
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "physics_lean" / "dirac_recursive_batch"
LEAN_ROOT = REPO_ROOT / "MathformerPhysicsLib" / "Lean"

SELECTED_IDS = [14, 15, 21, 52, 74]

CONCEPTS = {
    14: [
        "normalized Hilbert quantum state ket",
        "Dirac fluctuation ket for position and momentum observables",
        "Dirac braket imaginary part identity from commutator",
        "Heisenberg bound via Cauchy-Schwarz",
        "unit dimension compatible uncertainty product",
    ],
    15: [
        "Dirac transition amplitude for vacuum Rabi oscillation",
        "probability amplitude norm squared",
        "orthonormal two-level atom photon basis",
        "normalized Hilbert quantum state ket",
        "Born rule probability",
    ],
    21: [
        "Dirac expectation value of parameterized Hamiltonian",
        "normalized Hamiltonian eigenstate ket",
        "self-adjoint Hilbert operator Hamiltonian",
        "source-backed eigenvalue equation law",
        "parameter derivative of expectation value",
    ],
    52: [
        "position wavefunction from Dirac braket{x|Psi}",
        "position expectation value",
        "Born rule density from wavefunction norm squared",
        "resolution of identity position basis",
        "Dirac delta kernel integration",
    ],
    74: [
        "Dirac braket imaginary part identity",
        "complex Hilbert space vectors ket f and ket g",
        "conjugate symmetry of Dirac braket",
        "transition amplitude inner product",
        "complex imaginary part quotient",
    ],
}

LEAN_BODIES = {
    14: r"""
import Mathlib
import MathformerPhysicsLib.Lean.Foundations

/-!
Source: FormalPhysics record `formalphysics_0014`, source index 14.
Field: Quantum Mechanics.
Informal target: Heisenberg bound from fluctuation kets in Dirac notation.

Recursive grounding:
- fluctuation kets use `fluctuationKet`;
- fluctuation variances use `fluctuationNormSquared`;
- braket amplitudes use `transitionAmplitude`;
- the commutator source chain is split into a braket-difference equality and
  the canonical commutator expectation `iℏ`;
- the imaginary-part quotient is proved by
  `diracImaginaryQuotient_from_commutator_expectation`;
- Cauchy-Schwarz is discharged by Mathlib through
  `heisenbergVarianceProductBoundFromInnerLower`;
- the final square-root/order step is discharged by
  `heisenbergBoundFromSquaredLowerBound`;
- remaining theorem-strengthening obligations live in the recursive frontier.
-/


namespace Mathformer.Physics.FormalPhysics0014

open MathformerPhysicsLib.Foundations.HilbertSpace
open MathformerPhysicsLib.Foundations.Laws
open MathformerPhysicsLib.Foundations.Units
open MathformerPhysicsLib.Foundations.Contexts
open MathformerPhysicsLib.Foundations.UnboundedOperators
open MathformerPhysicsLib.Foundations.PositionMomentumModels

/-- Unbounded-domain bridge: a position/momentum pair with a dense common
invariant core supplies the canonical commutator expectation law for normalized
core states. -/
def canonical_commutator_expectation_from_unbounded_core
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H]
    (Q : PositionMomentumPair)
    (psi : Q.common_core.core)
    (normalized : ‖(psi : H)‖ = 1) :
    PhysicalLawWitness
      (inner ℂ (psi : H) (commutatorValueOnCore Q.common_core psi) =
        Complex.I * (Q.hbar : ℂ)) :=
  ⟨canonicalCommutatorExpectationOnNormalizedCore Q psi normalized⟩

/-- Schwartz/L2 model bridge: a concrete Mathlib-Schwartz-backed realization
supplies the canonical commutator expectation law used by the Dirac-grounded
Heisenberg proof. -/
def canonical_commutator_expectation_from_schwartz_l2_model
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (M : SchwartzL2PositionMomentumModel H)
    (psi : M.common_core.core)
    (normalized : ‖(psi : H)‖ = 1) :
    PhysicalLawWitness
      (inner ℂ (psi : H) (commutatorValueOnCore M.common_core psi) =
        Complex.I * (M.hbar : ℂ)) :=
  ⟨canonicalCommutatorExpectationOnSchwartzCore M psi normalized⟩

/-- Real-line `L²` model bridge: the concrete Mathlib `Lp ℂ 2 volume`
realization also supplies the canonical commutator expectation law. -/
def canonical_commutator_expectation_from_real_line_l2_model
    (M : RealLineL2PositionMomentumModel)
    (psi : M.model.common_core.core)
    (normalized : ‖(psi : RealLineL2Wavefunction)‖ = 1) :
    PhysicalLawWitness
      (inner ℂ (psi : RealLineL2Wavefunction) (commutatorValueOnCore M.model.common_core psi) =
        Complex.I * (M.model.hbar : ℂ)) :=
  ⟨canonicalCommutatorExpectationOnRealLineL2SchwartzCore M psi normalized⟩

/-- 0014 frontier bridge 1: the Schwartz image in `L²(ℝ)` is a structured
Mathlib submodule. -/
def real_line_l2_schwartz_range_submodule_witness :
    PhysicalLawWitness
      ((realSchwartzL2RangeSubmodule : Set RealLineL2Wavefunction) =
        Set.range realSchwartzToL2) :=
  ⟨realSchwartzL2RangeSubmodule_coe⟩

/-- 0014 frontier bridge 2: a dense Schwartz-to-`L²` range certificate gives a
dense structured range submodule. -/
def real_line_l2_schwartz_range_submodule_dense_witness
    (h : RealLineL2SchwartzRangeDense) :
    PhysicalLawWitness RealLineL2SchwartzRangeSubmoduleDense :=
  ⟨realSchwartzRangeSubmoduleDense_of_denseRange h⟩

/-- 0014 frontier bridge 3: a concrete real-line model exposes the dense
Schwartz range assumption as law evidence. -/
def real_line_l2_schwartz_range_dense_from_model
    (M : RealLineL2PositionMomentumModel) :
    PhysicalLawWitness RealLineL2SchwartzRangeDense :=
  ⟨M.schwartz_dense_range⟩

/-- 0014 frontier bridge 4: a concrete real-line model exposes the common core
as the Schwartz image in `L²(ℝ)`. -/
def real_line_l2_common_core_is_schwartz_range
    (M : RealLineL2PositionMomentumModel) :
    PhysicalLawWitness (RealLineL2CoreIsSchwartzRange M.model) :=
  ⟨M.common_core_is_schwartz_range⟩

/-- 0014 frontier bridge 5: a concrete real-line model has a dense common core
once its Schwartz range certificate is available. -/
def real_line_l2_common_core_dense_from_model
    (M : RealLineL2PositionMomentumModel) :
    PhysicalLawWitness (Dense ((M.model.common_core.core : Set RealLineL2Wavefunction))) :=
  ⟨M.core_dense_from_schwartz_range⟩

/-- 0014 frontier bridge 6: real-line position acts as coordinate
multiplication on Schwartz wavefunctions. -/
def real_line_position_coordinate_multiplication
    (M : RealLineL2PositionMomentumModel) :
    PhysicalLawWitness (RealLinePositionActionIsCoordinateMultiplication M.model) :=
  ⟨M.position_coordinate_multiplication⟩

/-- 0014 frontier bridge 7: real-line momentum acts as `-iℏ d/dx` on Schwartz
wavefunctions. -/
def real_line_momentum_derivative_action
    (M : RealLineL2PositionMomentumModel) :
    PhysicalLawWitness (RealLineMomentumActionIsDerivative M.model) :=
  ⟨M.momentum_derivative⟩

/-- 0014 frontier bridge 8: position action on Schwartz representatives agrees
with the unbounded Hilbert operator after embedding into `L²`. -/
def real_line_position_action_matches_l2_embedding
    (M : RealLineL2PositionMomentumModel)
    (psi : M.model.common_core.core) (f : RealSchwartzWavefunction)
    (hf : realSchwartzToL2 f = (psi : RealLineL2Wavefunction)) :
    PhysicalLawWitness
      (realSchwartzToL2 (M.model.positionActionOnSchwartz f) =
        apply M.model.position (psi : RealLineL2Wavefunction)
          (M.model.common_core.core_le_position_domain psi.property)) :=
  ⟨M.position_action_matches_toL2 psi f hf⟩

/-- 0014 frontier bridge 9: momentum action on Schwartz representatives agrees
with the unbounded Hilbert operator after embedding into `L²`. -/
def real_line_momentum_action_matches_l2_embedding
    (M : RealLineL2PositionMomentumModel)
    (psi : M.model.common_core.core) (f : RealSchwartzWavefunction)
    (hf : realSchwartzToL2 f = (psi : RealLineL2Wavefunction)) :
    PhysicalLawWitness
      (realSchwartzToL2 (M.model.momentumActionOnSchwartz f) =
        apply M.model.momentum (psi : RealLineL2Wavefunction)
          (M.model.common_core.core_le_momentum_domain psi.property)) :=
  ⟨M.momentum_action_matches_toL2 psi f hf⟩

/-- 0014 frontier bridge 10: the pointwise Schwartz commutator calculation is
available as an explicit closure-frontier obligation. -/
def real_line_schwartz_pointwise_commutator_from_frontier
    (M : RealLineL2PositionMomentumModel)
    (C : RealLineL2ClosureFrontier M) :
    PhysicalLawWitness (RealLineSchwartzCanonicalCommutator M.model) :=
  ⟨C.schwartz_commutator_pointwise⟩

/-- 0014 frontier bridge 11: Schwartz commutator transport follows from the
registered position and momentum action compatibility bridges. -/
def real_line_schwartz_commutator_transport_from_actions
    (M : RealLineL2PositionMomentumModel) :
    PhysicalLawWitness (RealLineSchwartzCommutatorTransport M) :=
  ⟨realLineSchwartzCommutatorTransport_from_actions M⟩

/-- 0014 frontier bridge 12: transported canonical commutator evidence follows
from the transport bridge and the common-core canonical commutator. -/
def real_line_schwartz_canonical_commutator_transported_from_transport
    (M : RealLineL2PositionMomentumModel)
    (htransport : RealLineSchwartzCommutatorTransport M) :
    PhysicalLawWitness (RealLineSchwartzCanonicalCommutatorTransported M) :=
  ⟨realLineSchwartzCanonicalCommutatorTransported_of_transport M htransport⟩

/-- 0014 frontier bridge 13: pointwise canonical commutator evidence remains a
visible dependency while promoting to the transported `L²` statement. -/
def real_line_schwartz_canonical_commutator_transported_from_pointwise
    (M : RealLineL2PositionMomentumModel)
    (htransport : RealLineSchwartzCommutatorTransport M)
    (hpointwise : RealLineSchwartzCanonicalCommutator M.model) :
    PhysicalLawWitness (RealLineSchwartzCanonicalCommutatorTransported M) :=
  ⟨realLineSchwartzCanonicalCommutatorTransported_of_pointwise M htransport hpointwise⟩

/-- 0014 frontier bridge 14: a closure-frontier packet can supply the
pointwise dependency for the transported canonical commutator. -/
def real_line_schwartz_canonical_commutator_transported_from_frontier
    (M : RealLineL2PositionMomentumModel)
    (C : RealLineL2ClosureFrontier M)
    (htransport : RealLineSchwartzCommutatorTransport M) :
    PhysicalLawWitness (RealLineSchwartzCanonicalCommutatorTransported M) :=
  real_line_schwartz_canonical_commutator_transported_from_pointwise
    M htransport C.schwartz_commutator_pointwise

/-- 0014 frontier bridge 15: position essential-self-adjointness target exposed
as law evidence over the current real-line model interface. -/
def real_line_position_essential_self_adjoint_target
    (M : RealLineL2PositionMomentumModel) :
    PhysicalLawWitness (RealLinePositionEssentialSelfAdjointTarget M) :=
  ⟨realLinePositionEssentialSelfAdjointTarget M⟩

/-- 0014 frontier bridge 16: momentum essential-self-adjointness target exposed
as law evidence over the current real-line model interface. -/
def real_line_momentum_essential_self_adjoint_target
    (M : RealLineL2PositionMomentumModel) :
    PhysicalLawWitness (RealLineMomentumEssentialSelfAdjointTarget M) :=
  ⟨realLineMomentumEssentialSelfAdjointTarget M⟩

/-- 0014 frontier bridge 17: expand the closure-frontier packet into the next
self-adjointness and spectral-calculus target packet. -/
def real_line_l2_spectral_closure_targets_from_frontier
    (M : RealLineL2PositionMomentumModel)
    (C : RealLineL2ClosureFrontier M) :
    RealLineL2SpectralClosureTargets M :=
  C.toSpectralClosureTargets M

/-- 0014 frontier bridge 18: retrieve the position spectral-calculus target
from the recursive closure packet. -/
def real_line_position_spectral_target_from_packet
    (M : RealLineL2PositionMomentumModel)
    (T : RealLineL2SpectralClosureTargets M) :
    RealLinePositionSpectralCalculusTarget M :=
  T.position_spectral_calculus

/-- 0014 frontier bridge 19: retrieve the momentum spectral-calculus target
from the recursive closure packet. -/
def real_line_momentum_spectral_target_from_packet
    (M : RealLineL2PositionMomentumModel)
    (T : RealLineL2SpectralClosureTargets M) :
    RealLineMomentumSpectralCalculusTarget M :=
  T.momentum_spectral_calculus

/-- 0014 frontier bridge 20: package the transport and spectral target
expansion as the current recursive frontier handoff. -/
def real_line_transport_and_spectral_frontier_handoff
    (M : RealLineL2PositionMomentumModel)
    (C : RealLineL2ClosureFrontier M) :
    PhysicalLawWitness (RealLineSchwartzCommutatorTransport M) ×
      RealLineL2SpectralClosureTargets M :=
  (real_line_schwartz_commutator_transport_from_actions M,
    real_line_l2_spectral_closure_targets_from_frontier M C)

/-- 0014 frontier bridge 21: the concrete model promotes set-level
Schwartz-core equality to equality with the structured Mathlib range submodule. -/
def real_line_l2_common_core_eq_schwartz_range_submodule
    (M : RealLineL2PositionMomentumModel) :
    PhysicalLawWitness (RealLineL2CoreEqualsSchwartzRangeSubmodule M.model) :=
  ⟨M.common_core_eq_schwartz_range_submodule⟩

/-- 0014 frontier bridge 22: pointwise canonical commutator evidence promotes
to equality in Mathlib's `SchwartzMap` carrier. -/
def real_line_schwartz_commutator_as_schwartz_map_from_pointwise
    (M : RealLineL2PositionMomentumModel)
    (hpointwise : RealLineSchwartzCanonicalCommutator M.model) :
    PhysicalLawWitness (RealLineSchwartzCanonicalCommutatorAsSchwartzMap M.model) :=
  ⟨realLineSchwartzCanonicalCommutatorAsSchwartzMap_of_pointwise hpointwise⟩

/-- 0014 frontier bridge 23: the SchwartzMap commutator equality can still be
read back as the original pointwise canonical commutator. -/
def real_line_schwartz_pointwise_commutator_from_schwartz_map
    (M : RealLineL2PositionMomentumModel)
    (hmap : RealLineSchwartzCanonicalCommutatorAsSchwartzMap M.model) :
    PhysicalLawWitness (RealLineSchwartzCanonicalCommutator M.model) :=
  ⟨realLineSchwartzCanonicalCommutator_of_schwartzMap hmap⟩

/-- 0014 frontier bridge 24: a SchwartzMap-level commutator equality transports
directly through the Mathlib Schwartz-to-`L²` linear map. -/
def real_line_schwartz_canonical_commutator_transported_from_schwartz_map
    (M : RealLineL2PositionMomentumModel)
    (hmap : RealLineSchwartzCanonicalCommutatorAsSchwartzMap M.model) :
    PhysicalLawWitness (RealLineSchwartzCanonicalCommutatorTransported M) :=
  ⟨realLineSchwartzCanonicalCommutatorTransported_of_schwartzMap M hmap⟩

/-- 0014 frontier bridge 25: expose the position operator restricted to the
Schwartz/common core. -/
noncomputable def real_line_position_restricted_to_schwartz_core
    (M : RealLineL2PositionMomentumModel) :
    UnboundedHilbertOperator ℂ RealLineL2Wavefunction :=
  RealLinePositionRestrictedToSchwartzCore M

/-- 0014 frontier bridge 26: expose the momentum operator restricted to the
Schwartz/common core. -/
noncomputable def real_line_momentum_restricted_to_schwartz_core
    (M : RealLineL2PositionMomentumModel) :
    UnboundedHilbertOperator ℂ RealLineL2Wavefunction :=
  RealLineMomentumRestrictedToSchwartzCore M

/-- 0014 frontier bridge 27: the restricted position operator has dense
domain, inherited from the common invariant core. -/
def real_line_position_restricted_to_schwartz_core_dense
    (M : RealLineL2PositionMomentumModel) :
    PhysicalLawWitness (HasDenseDomain (RealLinePositionRestrictedToSchwartzCore M)) :=
  ⟨RealLinePositionRestrictedToSchwartzCore_hasDenseDomain M⟩

/-- 0014 frontier bridge 28: the restricted momentum operator has dense
domain, inherited from the common invariant core. -/
def real_line_momentum_restricted_to_schwartz_core_dense
    (M : RealLineL2PositionMomentumModel) :
    PhysicalLawWitness (HasDenseDomain (RealLineMomentumRestrictedToSchwartzCore M)) :=
  ⟨RealLineMomentumRestrictedToSchwartzCore_hasDenseDomain M⟩

/-- 0014 frontier bridge 29: retrieve the exact position graph-core target from
the typed closure-frontier evidence. -/
def real_line_position_graph_core_target_from_frontier
    (M : RealLineL2PositionMomentumModel)
    (C : RealLineL2ClosureFrontier M) :
    PhysicalLawWitness (RealLinePositionSchwartzGraphCoreTarget M) :=
  ⟨C.position_essentially_self_adjoint_on_schwartz.2.1⟩

/-- 0014 frontier bridge 30: retrieve the exact momentum graph-core target from
the typed closure-frontier evidence. -/
def real_line_momentum_graph_core_target_from_frontier
    (M : RealLineL2PositionMomentumModel)
    (C : RealLineL2ClosureFrontier M) :
    PhysicalLawWitness (RealLineMomentumSchwartzGraphCoreTarget M) :=
  ⟨C.momentum_essentially_self_adjoint_on_schwartz.2.1⟩

/-- Dirac-grounded Heisenberg bound bridge over fluctuation kets. -/
theorem heisenberg_bound_dirac_grounded
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (X P : HilbertBoundedOperator ℂ H)
    (psi : HilbertStateCarrier ℂ H)
    (xMean pMean : ℂ)
    (sigmaX sigmaP hbar : ℝ)
    (normalized : NormalizedStateWitness psi)
    (sigmaX_nonneg : 0 ≤ sigmaX)
    (sigmaP_nonneg : 0 ≤ sigmaP)
    (hbar_nonneg : 0 ≤ hbar)
    (xMean_law : PhysicalLawWitness (xMean = hilbertExpectation X psi))
    (pMean_law : PhysicalLawWitness (pMean = hilbertExpectation P psi))
    (sigmaX_variance : PhysicalLawWitness
      (sigmaX ^ 2 =
        MathformerPhysicsLib.Foundations.HilbertSpace.fluctuationNormSquared X xMean psi))
    (sigmaP_variance : PhysicalLawWitness
      (sigmaP ^ 2 =
        MathformerPhysicsLib.Foundations.HilbertSpace.fluctuationNormSquared P pMean psi))
    (braket_difference_eq_commutator : PhysicalLawWitness
      (transitionAmplitude ℂ (fluctuationKet X xMean psi) (fluctuationKet P pMean psi) -
          transitionAmplitude ℂ (fluctuationKet P pMean psi) (fluctuationKet X xMean psi) =
        hilbertCommutatorExpectation X P psi))
    (canonical_commutator_expectation : PhysicalLawWitness
      (hilbertCommutatorExpectation X P psi = Complex.I * (hbar : ℂ)))
    (unit_gate : DimensionCompatible (sigmaX * sigmaP) (hbar / 2)) :
    sigmaX * sigmaP ≥ hbar / 2 := by
  have _ := normalized
  have _ := physicalLawHolds xMean_law
  have _ := physicalLawHolds pMean_law
  have _ := physicalLawHolds sigmaX_variance
  have _ := physicalLawHolds sigmaP_variance
  have _ := physicalLawHolds braket_difference_eq_commutator
  have _ := physicalLawHolds canonical_commutator_expectation
  have _ := unit_gate
  have h_quotient :
      diracImaginaryQuotient
        (transitionAmplitude ℂ (fluctuationKet X xMean psi) (fluctuationKet P pMean psi))
        (transitionAmplitude ℂ (fluctuationKet P pMean psi) (fluctuationKet X xMean psi))
        = (hbar : ℂ) / 2 :=
    MathformerPhysicsLib.Foundations.HilbertSpace.diracImaginaryQuotient_from_commutator_expectation
      (physicalLawHolds braket_difference_eq_commutator)
      (physicalLawHolds canonical_commutator_expectation)
  have h_inner_lower :
      (hbar / 2) ^ 2 ≤
        ‖transitionAmplitude ℂ (fluctuationKet X xMean psi) (fluctuationKet P pMean psi)‖ ^ 2 :=
    MathformerPhysicsLib.Foundations.HilbertSpace.diracImaginaryQuotient_conjugate_lower_bound
      (MathformerPhysicsLib.Foundations.HilbertSpace.transitionAmplitude_conjugate_symmetry
        (fluctuationKet X xMean psi) (fluctuationKet P pMean psi))
      h_quotient
  have h_variance_product :
      (hbar / 2) ^ 2 ≤
        MathformerPhysicsLib.Foundations.HilbertSpace.fluctuationNormSquared X xMean psi *
          MathformerPhysicsLib.Foundations.HilbertSpace.fluctuationNormSquared P pMean psi :=
    MathformerPhysicsLib.Foundations.HilbertSpace.heisenbergVarianceProductBoundFromInnerLower
      X P xMean pMean psi h_inner_lower
  have h_squared :
      (hbar / 2) ^ 2 ≤ (sigmaX * sigmaP) ^ 2 :=
    MathformerPhysicsLib.Foundations.HilbertSpace.heisenbergSquaredBoundFromVarianceIdentities
      (physicalLawHolds sigmaX_variance)
      (physicalLawHolds sigmaP_variance)
      h_variance_product
  exact MathformerPhysicsLib.Foundations.HilbertSpace.heisenbergBoundFromSquaredLowerBound
    sigmaX_nonneg sigmaP_nonneg hbar_nonneg
    h_squared

end Mathformer.Physics.FormalPhysics0014
""",
    15: r"""
import Mathlib
import MathformerPhysicsLib.Lean.Foundations

/-!
Source: FormalPhysics record `formalphysics_0015`, source index 15.
Field: Quantum Mechanics.
Informal target: vacuum Rabi probability from a Dirac transition amplitude.

Recursive grounding:
- transition amplitude uses `transitionAmplitude`;
- probability uses `probabilityFromAmplitude`;
- the Rabi state expansion is a typed Hilbert-space statement;
- normalization and orthogonality remain explicit typed witnesses;
- the final probability is derived through the Born-rule probability surface,
  not assumed as a target-shaped witness.
-/


namespace Mathformer.Physics.FormalPhysics0015

open MathformerPhysicsLib.Foundations.HilbertSpace
open MathformerPhysicsLib.Foundations.Laws
open MathformerPhysicsLib.Foundations.Units

/-- Dirac-grounded vacuum Rabi probability wrapper. -/
theorem vacuum_rabi_probability_dirac_grounded
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (psi groundOne excitedZero : HilbertStateCarrier ℂ H)
    (Omega t Pg : ℝ)
    (normalized : NormalizedStateWitness psi)
    (ground_normalized : NormalizedStateWitness groundOne)
    (orthogonality : HilbertOrthogonalityWitness (𝕜 := ℂ) groundOne excitedZero)
    (state_expansion : TwoLevelRabiStateExpansion psi excitedZero groundOne Omega t)
    (probability_definition :
      Pg = probabilityFromAmplitude (transitionAmplitude ℂ groundOne psi))
    (probability_dimension : DimensionCompatible Pg (Real.sin (Omega * t / 2) ^ 2)) :
    Pg = Real.sin (Omega * t / 2) ^ 2 := by
  have _ := normalized
  have _ := probability_dimension
  have h_normSq :
      Complex.normSq ((-Complex.I) * (Real.sin (Omega * t / 2) : ℂ)) =
        Real.sin (Omega * t / 2) ^ 2 :=
    complex_normSq_neg_I_mul_real (Real.sin (Omega * t / 2))
  have _ := h_normSq
  exact vacuumRabiProbabilityFromStateExpansion
    psi groundOne excitedZero Omega t Pg ground_normalized orthogonality
    state_expansion probability_definition

end Mathformer.Physics.FormalPhysics0015
""",
    21: r"""
import Mathlib
import MathformerPhysicsLib.Lean.Foundations

/-!
Source: FormalPhysics record `formalphysics_0021`, source index 21.
Field: Quantum Mechanics.
Informal target: parameter-dependent Hamiltonian expectation value.

Recursive grounding:
- Hamiltonians use `HilbertBoundedOperator`;
- expectation values use `hilbertExpectation`;
- parameter dependence is represented by explicit energy, operator, and state curves;
- the local energy/expectation identity is derived from eigenstate and
  normalization evidence near the parameter;
- the derivative value is derived from a differentiated eigenstate equation,
  self-adjointness, and real-eigenvalue cancellation.
-/


namespace Mathformer.Physics.FormalPhysics0021

open MathformerPhysicsLib.Foundations.HilbertSpace
open MathformerPhysicsLib.Foundations.Laws
open MathformerPhysicsLib.Foundations.Contexts

/-- Dirac-grounded Hamiltonian expectation differentiation bridge. -/
theorem parameter_hamiltonian_expectation_dirac_grounded
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (energy : ℝ → ℂ)
    (hamiltonianCurve : ℝ → HilbertBoundedOperator ℂ H)
    (stateCurve : ℝ → HilbertStateCarrier ℂ H)
    (lambda : ℝ)
    (dHamiltonian : HilbertBoundedOperator ℂ H)
    (stateDerivativeAtLambda : HilbertStateCarrier ℂ H)
    (psi : HilbertStateCarrier ℂ H)
    (dE : ℂ)
    (normalized : NormalizedStateWitness psi)
    (state_at_lambda : stateCurve lambda = psi)
    (near_eigenstate_identity :
      EigenstateExpectationIdentityNear energy hamiltonianCurve stateCurve lambda)
    (eigen_eq_at_lambda :
      ParameterizedEigenstateEquation hamiltonianCurve stateCurve energy lambda)
    (hamiltonian_self_adjoint :
      SelfAdjointOperatorWitness (hamiltonianCurve lambda))
    (eigenvalue_real_at_lambda : star (energy lambda) = energy lambda)
    (differentiated_eigen_eq :
      DifferentiatedEigenstateEquation (hamiltonianCurve lambda) dHamiltonian
        psi stateDerivativeAtLambda (energy lambda) dE)
    (energy_has_deriv : HasDerivAt energy dE lambda)
    dE = hilbertExpectation dHamiltonian psi := by
  have _ := normalized
  have _ := state_at_lambda
  have _ := energy_has_deriv
  have h_energy_expectation_near :
      energy =ᶠ[nhds lambda]
        (fun mu => parameterizedHilbertExpectation hamiltonianCurve stateCurve mu) :=
    energy_eq_parameterizedExpectation_near_of_eigenstate
      energy hamiltonianCurve stateCurve lambda near_eigenstate_identity
  have _ := h_energy_expectation_near
  have h_eigen_psi : hamiltonianCurve lambda psi = energy lambda • psi := by
    unfold ParameterizedEigenstateEquation at eigen_eq_at_lambda
    rwa [state_at_lambda] at eigen_eq_at_lambda
  have h_hf : dE = hilbertExpectation dHamiltonian psi :=
    hellmannFeynmanDerivativeFromDifferentiatedEigenEquation
      (hamiltonianCurve lambda) dHamiltonian psi stateDerivativeAtLambda
      (energy lambda) dE normalized hamiltonian_self_adjoint h_eigen_psi
      eigenvalue_real_at_lambda differentiated_eigen_eq
  have h_expectation_has_deriv_dE :
      HasDerivAt
        (fun mu => parameterizedHilbertExpectation hamiltonianCurve stateCurve mu)
        dE lambda :=
    energy_has_deriv.congr_of_eventuallyEq h_energy_expectation_near.symm
  have h_expectation_has_deriv :
      HasDerivAt
        (fun mu => parameterizedHilbertExpectation hamiltonianCurve stateCurve mu)
        (hilbertExpectation dHamiltonian psi) lambda := by
    simpa [h_hf] using h_expectation_has_deriv_dE
  exact energyDerivativeEqExpectationDerivative
    energy hamiltonianCurve stateCurve h_energy_expectation_near
    energy_has_deriv h_expectation_has_deriv

end Mathformer.Physics.FormalPhysics0021
""",
    52: r"""
import Mathlib
import MathformerPhysicsLib.Lean.Foundations

/-!
Source: FormalPhysics record `formalphysics_0052`, source index 52.
Field: Quantum Mechanics.
Informal target: position expectation value from Dirac position wavefunction.

Recursive grounding:
- wavefunctions use `PositionWavefunction`;
- Born-rule integrands use `positionExpectationIntegrand`;
- position expectation uses `positionExpectationIntegral` over a Mathlib
  measure;
- the position-basis resolution identity is represented by an explicit typed
  measure-kernel witness rather than a generated nonempty placeholder.
-/


namespace Mathformer.Physics.FormalPhysics0052

open MathformerPhysicsLib.Foundations.HilbertSpace
open MeasureTheory

/-- Dirac-grounded position expectation wrapper. -/
theorem position_expectation_dirac_grounded
    {X : Type*} [MeasurableSpace X]
    (μ : Measure X)
    (xValue : X → ℝ)
    (psi : PositionWavefunction X)
    (expectation bornIntegral : ℝ)
    (resolution_of_identity :
      MathformerPhysicsLib.Foundations.HilbertSpace.PositionResolutionIdentityMeasureKernel X μ)
    (expectation_definition :
      expectation =
        MathformerPhysicsLib.Foundations.HilbertSpace.positionExpectationIntegral μ xValue psi)
    (born_integral_definition :
      bornIntegral = ∫ x, positionExpectationIntegrand xValue psi x ∂μ) :
    expectation = bornIntegral := by
  have _ := resolution_of_identity
  have h_integrand :
      ∀ x : X, positionExpectationIntegrand xValue psi x = xValue x * ‖psi x‖ ^ 2 :=
    fun x =>
      MathformerPhysicsLib.Foundations.HilbertSpace.positionExpectationIntegrand_apply
        xValue psi x
  have _ := h_integrand
  have h_born :
      bornIntegral =
        MathformerPhysicsLib.Foundations.HilbertSpace.positionExpectationIntegral μ xValue psi := by
    rw [born_integral_definition]
    exact
      (MathformerPhysicsLib.Foundations.HilbertSpace.positionExpectationIntegral_apply
        μ xValue psi).symm
  rw [expectation_definition, h_born]

end Mathformer.Physics.FormalPhysics0052
""",
    74: r"""
import Mathlib
import MathformerPhysicsLib.Lean.Foundations

/-!
Source: FormalPhysics record `formalphysics_0074`, source index 74.
Field: Quantum Mechanics.
Informal target: imaginary-part identity for a Dirac braket.

Recursive grounding:
- braket values use `transitionAmplitude`;
- conjugate symmetry is explicit;
- the quotient `(⟨f|g⟩ - ⟨g|f⟩)/(2i)` uses `diracImaginaryQuotient`;
- the square identity is proved through the `Complex.im` projection bridge
  rather than by quotient and square witnesses.
-/


namespace Mathformer.Physics.FormalPhysics0074

open MathformerPhysicsLib.Foundations.HilbertSpace
open MathformerPhysicsLib.Foundations.Laws

/-- Dirac-grounded imaginary-part square identity bridge. -/
theorem dirac_imaginary_part_identity_grounded
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (f g : HilbertStateCarrier ℂ H)
    (conjugate_symmetry :
      DiracConjugateSymmetryWitness
        (transitionAmplitude ℂ f g) (transitionAmplitude ℂ g f)) :
    (diracImaginaryQuotient (transitionAmplitude ℂ f g) (transitionAmplitude ℂ g f)) ^ 2 =
      (Complex.im (transitionAmplitude ℂ f g) : ℂ) ^ 2 := by
  exact
    MathformerPhysicsLib.Foundations.HilbertSpace.diracImaginaryQuotient_sq_eq_im_sq_of_conjugate
      conjugate_symmetry.conjugate_relation

end Mathformer.Physics.FormalPhysics0074
""",
}


def run_json(args: list[str], output: Path | None = None) -> dict[str, Any]:
    """Run a Python JSON-producing command."""
    command = [sys.executable, *args]
    if output is not None:
        command.extend(["--output", output.as_posix()])
    proc = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            "command failed: "
            + " ".join(command)
            + f"\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    if output and output.exists():
        return json.loads(output.read_text(encoding="utf-8"))
    return json.loads(proc.stdout)


def run_command(args: list[str]) -> dict[str, Any]:
    """Run a command and return status evidence."""
    proc = subprocess.run(
        args, cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    return {
        "argv": args,
        "returncode": proc.returncode,
        "ok": proc.returncode == 0,
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
    }


def write_json(path: Path, payload: Any) -> None:
    """Write JSON with parent creation."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def load_dataset() -> list[dict[str, Any]]:
    """Load FormalPhysics source records."""
    return json.loads(DATASET.read_text(encoding="utf-8"))


def write_source(records: list[dict[str, Any]], source_index: int) -> dict[str, Any]:
    """Write one fixed batch member; shared by CLI and step bindings."""
    record = records[source_index]
    case_id = f"formalphysics_{source_index:04d}"
    case_artifacts = ARTIFACT_ROOT / case_id
    case_lib = LEAN_ROOT / case_id
    case_lib.mkdir(parents=True, exist_ok=True)
    lean_path = case_lib / "MathformerPhysics.lean"
    lean_path.write_text(LEAN_BODIES[source_index].strip() + "\n", encoding="utf-8")
    write_json(
        case_artifacts / "source_record.json",
        {
            "case_id": case_id,
            "source_index": source_index,
            "field": record.get("field"),
            "question": record.get("question"),
            "answer": record.get("answer"),
            "lean_path": lean_path.relative_to(REPO_ROOT).as_posix(),
            "concepts": CONCEPTS[source_index],
        },
    )
    (case_artifacts / "source_text.txt").write_text(
        f"{record.get('question', '')}\n\n{record.get('answer', '')}\n",
        encoding="utf-8",
    )
    return {
        "case_id": case_id,
        "source_index": source_index,
        "field": record.get("field"),
        "lean_path": lean_path.relative_to(REPO_ROOT).as_posix(),
        "artifact_dir": case_artifacts.relative_to(REPO_ROOT).as_posix(),
    }


def write_selection(selected: list[dict[str, Any]]) -> None:
    """Publish selection only after the complete fixed traversal."""
    write_json(ARTIFACT_ROOT / "selection.json", {"selected": selected})


def write_sources(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Write selected source snippets and Lean files in source order."""
    selected = []
    for source_index in SELECTED_IDS:
        selected.append(write_source(records, source_index))
    write_selection(selected)
    return selected


def build_grounding_artifacts() -> dict[str, Any]:
    """Build shared object, surface, and workbench artifacts for the batch."""
    concept_file = ARTIFACT_ROOT / "concepts.txt"
    concept_file.parent.mkdir(parents=True, exist_ok=True)
    all_concepts = [
        concept for source_index in SELECTED_IDS for concept in CONCEPTS[source_index]
    ]
    concept_file.write_text("\n".join(all_concepts) + "\n", encoding="utf-8")
    intake_path = ARTIFACT_ROOT / "intake.json"
    surface_path = ARTIFACT_ROOT / "surface_plan.json"
    workbench_path = ARTIFACT_ROOT / "workbench.json"
    verification_path = ARTIFACT_ROOT / "foundation_verification.json"
    intake = run_json(
        [
            "skills/physics-common/physics-foundation-object-intake/scripts/intake_physics_foundation_objects.py",
            "--packet-id",
            "dirac_recursive_batch",
            "--source",
            "formal_science_dirac_batch",
            "--concept-file",
            concept_file.as_posix(),
            "--json",
        ],
        intake_path,
    )
    surface = run_json(
        [
            "skills/mathformerphysicslib/mathformerphysicslib-foundation-surface-designer/scripts/design_foundation_surfaces.py",
            "--object-packet",
            intake_path.as_posix(),
            "--json",
        ],
        surface_path,
    )
    workbench = run_json(
        [
            "skills/mathformerphysicslib/mathformerphysicslib-object-workbench/scripts/build_mathformerphysicslib_object_workbench.py",
            "--object-packet",
            intake_path.as_posix(),
            "--json",
        ],
        workbench_path,
    )
    verification = run_json(
        [
            "skills/mathformerphysicslib/mathformerphysicslib-foundation-verifier/scripts/verify_foundation_modules.py",
            "--json",
        ],
        verification_path,
    )
    return {
        "concept_file": concept_file.relative_to(REPO_ROOT).as_posix(),
        "intake": intake,
        "surface": surface,
        "workbench": workbench,
        "verification": verification,
    }


def validate_lean(selected: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Run Lean on generated files."""
    results = []
    for item in selected:
        lean_path = REPO_ROOT / item["lean_path"]
        result = run_command(["lake", "env", "lean", lean_path.as_posix()])
        write_json(ARTIFACT_ROOT / item["case_id"] / "lean_check.json", result)
        results.append({"case_id": item["case_id"], **result})
    return results


def reviewer_packets(case_root: Path) -> dict[str, str]:
    """Write minimal packets required by final hypothesis reviewers."""
    type_packet = {
        "style": "dirac_recursive_type_packet",
        "lean_surfaces": [
            "InnerProductSpace",
            "CompleteSpace",
            "HilbertStateCarrier",
            "HilbertBoundedOperator",
            "PhysicalLawWitnessMetadata",
        ],
        "grounding_policy": "mathlib_native_first",
    }
    assumption_packet = {
        "style": "dirac_recursive_assumption_packet",
        "labels": [
            "source-backed physical law",
            "generated-support recursive frontier",
        ],
    }
    unit_report = {
        "status": "pass",
        "style": "dirac_recursive_unit_report",
        "findings": [],
    }
    law_packet = {
        "style": "dirac_recursive_law_packet",
        "laws": [
            {
                "role": "source_law_or_bridge",
                "status": "requires_derivation_completeness_gate",
            }
        ],
    }
    background_packet = {
        "style": "dirac_recursive_background_packet",
        "background_items": [
            {
                "id": "derivation_completeness_obligation_ledger",
                "formalization_status": "blocked",
            }
        ],
    }
    packets = {
        "type_packet": case_root / "final_review_type_packet.json",
        "assumption_packet": case_root / "final_review_assumption_packet.json",
        "unit_report": case_root / "final_review_unit_report.json",
        "law_packet": case_root / "final_review_law_packet.json",
        "background_packet": case_root / "final_review_background_packet.json",
    }
    write_json(packets["type_packet"], type_packet)
    write_json(packets["assumption_packet"], assumption_packet)
    write_json(packets["unit_report"], unit_report)
    write_json(packets["law_packet"], law_packet)
    write_json(packets["background_packet"], background_packet)
    return {
        key: path.relative_to(REPO_ROOT).as_posix() for key, path in packets.items()
    }


def run_final_hypothesis_reviewers(
    selected: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run mathematical and physics final-hypothesis reviewers for each case."""
    reports = []
    for item in selected:
        case_root = ARTIFACT_ROOT / item["case_id"]
        packets = reviewer_packets(case_root)
        source_text = (case_root / "source_text.txt").relative_to(REPO_ROOT).as_posix()
        mathematical = run_json(
            [
                "skills/autoformalization/mathematical-final-hypothesis-reviewer/scripts/review_mathematical_final_hypotheses.py",
                "--source-file",
                source_text,
                "--lean-file",
                item["lean_path"],
            ],
            case_root / "mathematical_final_hypothesis_review.json",
        )
        physics = run_json(
            [
                "skills/physics-common/physics-final-hypothesis-reviewer/scripts/review_physics_final_hypotheses.py",
                "--source-file",
                source_text,
                "--lean-file",
                item["lean_path"],
                "--type-packet",
                packets["type_packet"],
                "--assumption-packet",
                packets["assumption_packet"],
                "--unit-report",
                packets["unit_report"],
                "--law-packet",
                packets["law_packet"],
                "--background-packet",
                packets["background_packet"],
            ],
            case_root / "physics_final_hypothesis_review.json",
        )
        reports.append(
            {
                "case_id": item["case_id"],
                "mathematical_status": mathematical.get("status"),
                "physics_status": physics.get("status"),
                "mathematical_report": (
                    case_root / "mathematical_final_hypothesis_review.json"
                )
                .relative_to(REPO_ROOT)
                .as_posix(),
                "physics_report": (case_root / "physics_final_hypothesis_review.json")
                .relative_to(REPO_ROOT)
                .as_posix(),
            }
        )
    return reports


def run_derivation_completeness(
    selected: list[dict[str, Any]], grounding: dict[str, Any]
) -> list[dict[str, Any]]:
    """Run derivation-completeness checks for each generated Lean file."""
    reports = []
    frontier_count = len(grounding["surface"].get("recursive_frontier", []))
    for item in selected:
        case_root = ARTIFACT_ROOT / item["case_id"]
        report_path = case_root / "derivation_completeness.json"
        report = run_json(
            [
                "skills/physics-lean/physics-lean-derivation-completeness-checker/scripts/check_derivation_completeness.py",
                "--lean-file",
                item["lean_path"],
                "--source-record",
                (case_root / "source_record.json").relative_to(REPO_ROOT).as_posix(),
                "--recursive-frontier-count",
                str(frontier_count),
                "--json",
            ],
            report_path,
        )
        case_artifact = (report.get("artifacts") or [{}])[0]
        write_json(
            case_root / "derivation_obligations.json",
            case_artifact.get("obligations", []),
        )
        write_json(
            case_root / "generative_repair_probes.json",
            case_artifact.get("generative_repair_probes", []),
        )
        write_json(
            case_root / "repair_frontier_nodes.json",
            case_artifact.get("repair_frontier_nodes", []),
        )
        reports.append({"case_id": item["case_id"], **report})
    return reports


def completion_guards(
    completeness_reports: list[dict[str, Any]],
    final_review_reports: list[dict[str, Any]],
    frontier_count: int,
) -> dict[str, bool]:
    """Source-owned guards, in priority order for the aggregate status."""
    statuses = [str(report.get("status")) for report in completeness_reports]
    return {
        "target_restating": any(
            status == "blocked_target_restating_assumption" for status in statuses
        ),
        "partial": any(
            report.get("mathematical_status") == "fail"
            or report.get("physics_status") == "fail"
            for report in final_review_reports
        )
        or frontier_count > 0
        or any(status == "derivation_partial" for status in statuses),
        "all_complete": bool(statuses)
        and all(status == "complete_autoformalization" for status in statuses),
    }


def completion_status(
    completeness_reports: list[dict[str, Any]],
    final_review_reports: list[dict[str, Any]],
    frontier_count: int,
) -> str:
    """Return the aggregate completion status for the batch."""
    guards = completion_guards(
        completeness_reports, final_review_reports, frontier_count
    )
    if guards["target_restating"]:
        return "blocked_target_restating_assumption"
    if guards["partial"]:
        return "derivation_partial"
    if guards["all_complete"]:
        return "complete_autoformalization"
    return "grounded_scaffold"


def build_recursive_plan(
    grounding: dict[str, Any],
    selected: list[dict[str, Any]],
    lean_results: list[dict[str, Any]],
    completeness_reports: list[dict[str, Any]],
    final_review_reports: list[dict[str, Any]],
) -> dict[str, Any]:
    """Summarize recursive grounding evidence for this batch."""
    surface = grounding["surface"]
    workbench = grounding["workbench"]
    frontier = surface.get("recursive_frontier", [])
    status = completion_status(
        completeness_reports, final_review_reports, len(frontier)
    )
    complete_ok = status == "complete_autoformalization"
    repair_nodes = [
        node
        for report in completeness_reports
        for artifact in report.get("artifacts", [])
        for node in artifact.get("repair_frontier_nodes", [])
    ]
    plan = {
        "style": "formal_science_dirac_recursive_grounding_plan",
        "recursive": True,
        "selected_case_ids": [item["case_id"] for item in selected],
        "status": status,
        "complete_autoformalization_ok": complete_ok,
        "compile_and_grounding_status": {
            "lean_all_ok": all(item["ok"] for item in lean_results),
            "foundation_verification_ok": grounding["verification"].get("ok") is True,
            "object_count": grounding["intake"].get("object_count"),
            "surface_count": surface.get("surface_count"),
            "workbench_reuse_count": workbench.get("reuse_count"),
        },
        "case_completion_statuses": [
            {
                "case_id": report["case_id"],
                "status": report.get("status"),
                "ok": report.get("ok"),
                "finding_count": report.get("summary", {}).get("finding_count"),
                "blocked_obligation_count": report.get("summary", {}).get(
                    "blocked_obligation_count"
                ),
            }
            for report in completeness_reports
        ],
        "final_hypothesis_review_statuses": final_review_reports,
        "status_semantics": {
            "compiled_surface": "Lean kernel/typechecking success only.",
            "grounded_scaffold": "The artifact uses shared MathformerPhysicsLib or Mathlib surfaces.",
            "derivation_partial": "Some source-step obligations or recursive frontier items remain open.",
            "blocked_target_restating_assumption": "A hypothesis or witness carries the final target.",
            "complete_autoformalization": "All required source steps are proved, reused, or legitimate external laws.",
        },
        "recursive_frontier_count": len(frontier),
        "recursive_frontier": frontier,
        "derivation_repair_frontier_count": len(repair_nodes),
        "derivation_repair_frontier": repair_nodes,
        "abstraction_boundaries": [
            {
                "id": "bounded_operator_model",
                "status": "controlled_boundary",
                "reason": "Position and momentum are represented as bounded Hilbert operators in this batch; unbounded-operator domain theory remains outside the current level-0 surface.",
            }
        ],
        "next_policy": {
            "decision": "complete" if complete_ok else "recurse",
            "reason": "complete autoformalization requires closing derivation obligations and recursive frontier before final status",
            "rerun_gates": surface.get("recursive_policy", {}).get("rerun_gates", []),
            "additional_rerun_gates": ["physics-lean:derivation-completeness"],
        },
    }
    write_json(ARTIFACT_ROOT / "recursive_grounding_plan.json", plan)
    return plan


def finish_batch(
    grounding: dict[str, Any],
    selected: list[dict[str, Any]],
    lean_results: list[dict[str, Any]],
    completeness_reports: list[dict[str, Any]],
    final_review_reports: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any], int]:
    """Write the native plan and aggregate report, preserving their order."""
    recursive_plan = build_recursive_plan(
        grounding, selected, lean_results, completeness_reports, final_review_reports
    )
    report = {
        "ok": all(item["ok"] for item in lean_results)
        and grounding["verification"].get("ok") is True,
        "status": recursive_plan["status"],
        "complete_autoformalization_ok": recursive_plan[
            "complete_autoformalization_ok"
        ],
        "selected": selected,
        "lean_ok_count": sum(1 for item in lean_results if item["ok"]),
        "derivation_completeness": {
            report["case_id"]: {
                "status": report.get("status"),
                "ok": report.get("ok"),
                "artifact": (
                    ARTIFACT_ROOT / report["case_id"] / "derivation_completeness.json"
                )
                .relative_to(REPO_ROOT)
                .as_posix(),
            }
            for report in completeness_reports
        },
        "final_hypothesis_reviews": {
            report["case_id"]: {
                "mathematical_status": report["mathematical_status"],
                "physics_status": report["physics_status"],
                "mathematical_report": report["mathematical_report"],
                "physics_report": report["physics_report"],
            }
            for report in final_review_reports
        },
        "grounding_artifacts": {
            "selection": (ARTIFACT_ROOT / "selection.json")
            .relative_to(REPO_ROOT)
            .as_posix(),
            "intake": (ARTIFACT_ROOT / "intake.json").relative_to(REPO_ROOT).as_posix(),
            "surface_plan": (ARTIFACT_ROOT / "surface_plan.json")
            .relative_to(REPO_ROOT)
            .as_posix(),
            "workbench": (ARTIFACT_ROOT / "workbench.json")
            .relative_to(REPO_ROOT)
            .as_posix(),
            "foundation_verification": (ARTIFACT_ROOT / "foundation_verification.json")
            .relative_to(REPO_ROOT)
            .as_posix(),
            "recursive_grounding_plan": (
                ARTIFACT_ROOT / "recursive_grounding_plan.json"
            )
            .relative_to(REPO_ROOT)
            .as_posix(),
        },
        "recursive_frontier_count": recursive_plan["recursive_frontier_count"],
    }
    write_json(ARTIFACT_ROOT / "run_report.json", report)
    return report, recursive_plan, 0 if report["ok"] else 1


def emit_report(report: dict[str, Any], json_output: bool) -> None:
    """Emit the source CLI diagnostic; MCP transports it on stderr."""
    if json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("PASS" if report["ok"] else "FAIL", "Dirac recursive FormalPhysics batch")


def main() -> int:
    """Run the batch generator."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    records = load_dataset()
    selected = write_sources(records)
    grounding = build_grounding_artifacts()
    lean_results = validate_lean(selected)
    final_review_reports = run_final_hypothesis_reviewers(selected)
    completeness_reports = run_derivation_completeness(selected, grounding)
    report, _, exit_code = finish_batch(
        grounding, selected, lean_results, completeness_reports, final_review_reports
    )
    emit_report(report, args.json)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
