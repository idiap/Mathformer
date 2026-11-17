-- SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
-- SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
-- SPDX-License-Identifier: MIT
-- Neuro-symbolic AI Group
import MathformerPhysicsLib.Lean.Foundations.UnboundedOperators

namespace MathformerPhysicsLib
namespace Foundations
namespace PositionMomentumModels

open MathformerPhysicsLib.Foundations.UnboundedOperators
open MeasureTheory

/-- Mathlib grounding: a Schwartz wavefunction on the real line is Mathlib's
`SchwartzMap ℝ ℂ`, not a locally redefined smooth-decay predicate. -/
abbrev RealSchwartzWavefunction := SchwartzMap ℝ ℂ

/-- Mathlib grounding: differentiation on real Schwartz wavefunctions reuses
Mathlib's continuous derivative operator on Schwartz space. -/
noncomputable def realSchwartzDerivative :
    RealSchwartzWavefunction →L[ℂ] RealSchwartzWavefunction :=
  SchwartzMap.derivCLM ℂ

/-- Physics role: a controlled Schwartz/L2-style realization of the
position-momentum commutator.  The Hilbert carrier, dense common core, operator
domains, self-adjointness witnesses, and canonical commutator are inherited from
the unbounded-operator layer.  The new information is the Mathlib-grounded
Schwartz representation and its compatibility with the Hilbert-space operators.

This deliberately keeps the hard analytic obligations as fields:
embedding the Schwartz functions into the target Hilbert space, proving the
core is represented by Schwartz functions, connecting the model actions to the
unbounded Hilbert operators, and validating the canonical commutator. -/
structure SchwartzL2PositionMomentumModel (H : Type*) [NormedAddCommGroup H]
    [InnerProductSpace ℂ H] [CompleteSpace H] where
  position : UnboundedHilbertOperator ℂ H
  momentum : UnboundedHilbertOperator ℂ H
  hbar : ℝ
  hbar_nonneg : 0 ≤ hbar
  common_core : CommonInvariantCore position momentum
  position_self_adjoint : SelfAdjointUnboundedOperatorWitness position
  momentum_self_adjoint : SelfAdjointUnboundedOperatorWitness momentum
  schwartzToHilbert : RealSchwartzWavefunction → H
  core_represented_by_schwartz :
    ∀ psi : common_core.core, ∃ f : RealSchwartzWavefunction, schwartzToHilbert f = (psi : H)
  positionActionOnSchwartz : RealSchwartzWavefunction → RealSchwartzWavefunction
  momentumActionOnSchwartz : RealSchwartzWavefunction → RealSchwartzWavefunction
  momentum_is_minus_i_hbar_derivative :
    ∀ f : RealSchwartzWavefunction,
      momentumActionOnSchwartz f =
        (-Complex.I * (hbar : ℂ)) • realSchwartzDerivative f
  position_action_matches_hilbert_operator :
    ∀ psi : common_core.core, ∀ f : RealSchwartzWavefunction,
      schwartzToHilbert f = (psi : H) →
        schwartzToHilbert (positionActionOnSchwartz f) =
          apply position (psi : H) (common_core.core_le_position_domain psi.property)
  momentum_action_matches_hilbert_operator :
    ∀ psi : common_core.core, ∀ f : RealSchwartzWavefunction,
      schwartzToHilbert f = (psi : H) →
        schwartzToHilbert (momentumActionOnSchwartz f) =
          apply momentum (psi : H) (common_core.core_le_momentum_domain psi.property)
  canonical_commutator_on_core :
    ∀ psi : common_core.core,
      commutatorValueOnCore common_core psi = (Complex.I * (hbar : ℂ)) • (psi : H)

/-- A Schwartz/L2 realization promotes to the abstract unbounded
position-momentum pair consumed by downstream Dirac/Heisenberg formalizations. -/
def SchwartzL2PositionMomentumModel.toPositionMomentumPair {H : Type*} [NormedAddCommGroup H]
    [InnerProductSpace ℂ H] [CompleteSpace H] (M : SchwartzL2PositionMomentumModel H) :
    PositionMomentumPair (H := H) :=
  { position := M.position
    momentum := M.momentum
    hbar := M.hbar
    hbar_nonneg := M.hbar_nonneg
    position_self_adjoint := M.position_self_adjoint
    momentum_self_adjoint := M.momentum_self_adjoint
    common_core := M.common_core
    canonical_commutator_on_core := M.canonical_commutator_on_core }

/-- Physics role: the concrete Schwartz/L2 realization supplies the same
canonical expectation theorem as the abstract unbounded pair, but preserves the
provenance that the core states are Schwartz-represented wavefunctions. -/
theorem canonicalCommutatorExpectationOnSchwartzCore {H : Type*} [NormedAddCommGroup H]
    [InnerProductSpace ℂ H] [CompleteSpace H] (M : SchwartzL2PositionMomentumModel H)
    (psi : M.common_core.core) (normalized : ‖(psi : H)‖ = 1) :
    inner ℂ (psi : H) (commutatorValueOnCore M.common_core psi) =
      Complex.I * (M.hbar : ℂ) := by
  exact canonicalCommutatorExpectationOnNormalizedCore M.toPositionMomentumPair psi normalized

/-- Mathlib grounding: the concrete Hilbert carrier for a particle on the real
line is Mathlib's complex `L²(ℝ)` space over Lebesgue volume. -/
abbrev RealLineL2Wavefunction := MeasureTheory.Lp ℂ 2 (volume : Measure ℝ)

/-- Mathlib grounding: the canonical injection from real-line Schwartz
wavefunctions into `L²(ℝ)` is Mathlib's continuous `toLpCLM` map. -/
noncomputable def realSchwartzToL2 :
    RealSchwartzWavefunction →L[ℂ] RealLineL2Wavefunction :=
  SchwartzMap.toLpCLM ℂ ℂ 2 (volume : Measure ℝ)

/-- Mathlib grounding: the `L²` class produced by `realSchwartzToL2` agrees
almost everywhere with the original Schwartz function. -/
theorem realSchwartzToL2_apply_ae (f : RealSchwartzWavefunction) :
    realSchwartzToL2 f =ᵐ[(volume : Measure ℝ)] f := by
  simpa [realSchwartzToL2] using
    (SchwartzMap.coeFn_toLp f 2 (volume : Measure ℝ))

/-- Recursive frontier: density of the Schwartz image in real-line `L²`.  This
is the exact Mathlib-facing proposition a future proof or blocker must target. -/
noncomputable def RealLineL2SchwartzRangeDense : Prop :=
  DenseRange realSchwartzToL2

/-- Frontier 0014-1: the Schwartz image in `L²(ℝ)` as a Mathlib submodule,
not merely as an unstructured set. -/
noncomputable def realSchwartzL2RangeSubmodule : Submodule ℂ RealLineL2Wavefunction :=
  LinearMap.range realSchwartzToL2

/-- Frontier 0014-2: every embedded Schwartz wavefunction belongs to the
Mathlib range submodule. -/
theorem realSchwartzToL2_mem_rangeSubmodule (f : RealSchwartzWavefunction) :
    realSchwartzToL2 f ∈ realSchwartzL2RangeSubmodule :=
  ⟨f, rfl⟩

/-- Frontier 0014-3: the submodule range and the ordinary set-theoretic range
name the same subset of `L²(ℝ)`. -/
theorem realSchwartzL2RangeSubmodule_coe :
    (realSchwartzL2RangeSubmodule : Set RealLineL2Wavefunction) =
      Set.range realSchwartzToL2 := by
  ext psi
  rfl

/-- Frontier 0014-4: density can be stated equivalently for the structured
range submodule. -/
noncomputable def RealLineL2SchwartzRangeSubmoduleDense : Prop :=
  Dense ((realSchwartzL2RangeSubmodule : Set RealLineL2Wavefunction))

/-- Frontier 0014-5: dense range of the embedding supplies density of the
structured range submodule. -/
theorem realSchwartzRangeSubmoduleDense_of_denseRange
    (h : RealLineL2SchwartzRangeDense) :
    RealLineL2SchwartzRangeSubmoduleDense := by
  simpa [RealLineL2SchwartzRangeSubmoduleDense, RealLineL2SchwartzRangeDense,
    realSchwartzL2RangeSubmodule_coe] using h

/-- Recursive frontier: the model's common invariant core is exactly the
Schwartz image in `L²(ℝ)`. -/
noncomputable def RealLineL2CoreIsSchwartzRange
    (M : SchwartzL2PositionMomentumModel RealLineL2Wavefunction) : Prop :=
  (M.common_core.core : Set RealLineL2Wavefunction) = Set.range realSchwartzToL2

/-- Frontier 0014-6: a stronger core statement says the common invariant core
is exactly the Schwartz range submodule. -/
noncomputable def RealLineL2CoreEqualsSchwartzRangeSubmodule
    (M : SchwartzL2PositionMomentumModel RealLineL2Wavefunction) : Prop :=
  M.common_core.core = realSchwartzL2RangeSubmodule

/-- Frontier 0014-7: equality with the structured Schwartz range submodule
implies the older set-level core/range statement. -/
theorem realLineL2CoreIsSchwartzRange_of_submodule_eq
    {M : SchwartzL2PositionMomentumModel RealLineL2Wavefunction}
    (h : RealLineL2CoreEqualsSchwartzRangeSubmodule M) :
    RealLineL2CoreIsSchwartzRange M := by
  unfold RealLineL2CoreIsSchwartzRange
  rw [h, realSchwartzL2RangeSubmodule_coe]

/-- Frontier 0014-8: once the core is the Schwartz range and the embedding has
dense range, the model's common core is dense by Mathlib topology. -/
theorem realLineL2CoreDense_of_rangeSubmodule
    {M : SchwartzL2PositionMomentumModel RealLineL2Wavefunction}
    (hcore : RealLineL2CoreEqualsSchwartzRangeSubmodule M)
    (hdense : RealLineL2SchwartzRangeDense) :
    Dense ((M.common_core.core : Set RealLineL2Wavefunction)) := by
  rw [hcore]
  exact realSchwartzRangeSubmoduleDense_of_denseRange hdense

/-- Frontier support: a concrete model's set-level common-core equality
promotes to equality with the structured Schwartz range submodule. -/
theorem RealLineL2CoreEqualsSchwartzRangeSubmodule.of_set_range
    {M : SchwartzL2PositionMomentumModel RealLineL2Wavefunction}
    (h : RealLineL2CoreIsSchwartzRange M) :
    RealLineL2CoreEqualsSchwartzRangeSubmodule M := by
  ext psi
  unfold RealLineL2CoreIsSchwartzRange at h
  have hset :
      (M.common_core.core : Set RealLineL2Wavefunction) =
        (realSchwartzL2RangeSubmodule : Set RealLineL2Wavefunction) := by
    rw [h, realSchwartzL2RangeSubmodule_coe]
  exact Set.ext_iff.mp hset psi

/-- Physics role: the real-line position action is multiplication by the
coordinate on Schwartz wavefunctions. -/
def RealLinePositionActionIsCoordinateMultiplication
    (M : SchwartzL2PositionMomentumModel RealLineL2Wavefunction) : Prop :=
  ∀ f : RealSchwartzWavefunction, ∀ x : ℝ,
    M.positionActionOnSchwartz f x = (x : ℂ) * f x

/-- Frontier 0014-9: the real-line momentum action is the standard
`-iℏ d/dx` action already grounded in Mathlib's Schwartz derivative. -/
def RealLineMomentumActionIsDerivative
    (M : SchwartzL2PositionMomentumModel RealLineL2Wavefunction) : Prop :=
  ∀ f : RealSchwartzWavefunction,
    M.momentumActionOnSchwartz f =
      (-Complex.I * (M.hbar : ℂ)) • realSchwartzDerivative f

/-- Frontier 0014-10: the pointwise Schwartz commutator before quotienting into
`L²`, used as the concrete calculation target for the canonical commutator. -/
noncomputable def RealLineSchwartzCommutatorAction
    (M : SchwartzL2PositionMomentumModel RealLineL2Wavefunction)
    (f : RealSchwartzWavefunction) : RealSchwartzWavefunction :=
  M.positionActionOnSchwartz (M.momentumActionOnSchwartz f) -
    M.momentumActionOnSchwartz (M.positionActionOnSchwartz f)

/-- Frontier 0014-10 companion: the pointwise canonical commutator on
Schwartz wavefunctions. -/
def RealLineSchwartzCanonicalCommutator
    (M : SchwartzL2PositionMomentumModel RealLineL2Wavefunction) : Prop :=
  ∀ f : RealSchwartzWavefunction, ∀ x : ℝ,
    RealLineSchwartzCommutatorAction M f x = (Complex.I * (M.hbar : ℂ)) * f x

/-- Frontier 0014 companion: the canonical Schwartz commutator as equality of
Mathlib Schwartz functions, not only pointwise scalar notation. -/
def RealLineSchwartzCanonicalCommutatorAsSchwartzMap
    (M : SchwartzL2PositionMomentumModel RealLineL2Wavefunction) : Prop :=
  ∀ f : RealSchwartzWavefunction,
    RealLineSchwartzCommutatorAction M f = (Complex.I * (M.hbar : ℂ)) • f

/-- Frontier support: pointwise canonical commutator evidence promotes to an
equality in Mathlib's `SchwartzMap` carrier. -/
theorem realLineSchwartzCanonicalCommutatorAsSchwartzMap_of_pointwise
    {M : SchwartzL2PositionMomentumModel RealLineL2Wavefunction}
    (h : RealLineSchwartzCanonicalCommutator M) :
    RealLineSchwartzCanonicalCommutatorAsSchwartzMap M := by
  intro f
  ext x
  simpa using h f x

/-- Frontier support: the SchwartzMap equality can be read back as the
pointwise canonical commutator. -/
theorem realLineSchwartzCanonicalCommutator_of_schwartzMap
    {M : SchwartzL2PositionMomentumModel RealLineL2Wavefunction}
    (h : RealLineSchwartzCanonicalCommutatorAsSchwartzMap M) :
    RealLineSchwartzCanonicalCommutator M := by
  intro f x
  have hx := congrArg (fun g : RealSchwartzWavefunction => g x) (h f)
  simpa using hx

/-- Frontier support: the generic model already supplies the real-line momentum
derivative law. -/
theorem realLineMomentumActionIsDerivative
    (M : SchwartzL2PositionMomentumModel RealLineL2Wavefunction) :
    RealLineMomentumActionIsDerivative M :=
  M.momentum_is_minus_i_hbar_derivative

/-- Concrete `L²(ℝ)` realization package for the position-momentum model.  It
uses the real Mathlib Lp carrier and Schwartz-to-Lp map, while retaining the
analytic density/core/action proofs as explicit obligations. -/
structure RealLineL2PositionMomentumModel where
  model : SchwartzL2PositionMomentumModel RealLineL2Wavefunction
  schwartzToHilbert_eq_toLp : model.schwartzToHilbert = realSchwartzToL2
  schwartz_dense_range : RealLineL2SchwartzRangeDense
  common_core_is_schwartz_range : RealLineL2CoreIsSchwartzRange model
  position_action_is_coordinate_multiplication : RealLinePositionActionIsCoordinateMultiplication model

/-- Frontier support: a concrete model inherits core density from the
Schwartz-to-`L²` dense-range certificate. -/
theorem RealLineL2PositionMomentumModel.core_dense_from_schwartz_range
    (M : RealLineL2PositionMomentumModel) :
    Dense ((M.model.common_core.core : Set RealLineL2Wavefunction)) := by
  have hcore := M.common_core_is_schwartz_range
  unfold RealLineL2CoreIsSchwartzRange at hcore
  rw [hcore]
  exact M.schwartz_dense_range

/-- Frontier support: the concrete model's common core is exactly the Mathlib
Schwartz range submodule, not only the corresponding set range. -/
theorem RealLineL2PositionMomentumModel.common_core_eq_schwartz_range_submodule
    (M : RealLineL2PositionMomentumModel) :
    RealLineL2CoreEqualsSchwartzRangeSubmodule M.model :=
  RealLineL2CoreEqualsSchwartzRangeSubmodule.of_set_range M.common_core_is_schwartz_range

/-- Frontier support: the concrete model exposes the pointwise coordinate
multiplication law for position. -/
theorem RealLineL2PositionMomentumModel.position_coordinate_multiplication
    (M : RealLineL2PositionMomentumModel) :
    RealLinePositionActionIsCoordinateMultiplication M.model :=
  M.position_action_is_coordinate_multiplication

/-- Frontier support: the concrete model exposes the `-iℏ d/dx` momentum law. -/
theorem RealLineL2PositionMomentumModel.momentum_derivative
    (M : RealLineL2PositionMomentumModel) :
    RealLineMomentumActionIsDerivative M.model :=
  realLineMomentumActionIsDerivative M.model

/-- Frontier support: position action compatibility specialized to the
Mathlib Schwartz-to-`L²` embedding. -/
theorem RealLineL2PositionMomentumModel.position_action_matches_toL2
    (M : RealLineL2PositionMomentumModel)
    (psi : M.model.common_core.core) (f : RealSchwartzWavefunction)
    (hf : realSchwartzToL2 f = (psi : RealLineL2Wavefunction)) :
    realSchwartzToL2 (M.model.positionActionOnSchwartz f) =
      apply M.model.position (psi : RealLineL2Wavefunction)
        (M.model.common_core.core_le_position_domain psi.property) := by
  have hf' : M.model.schwartzToHilbert f = (psi : RealLineL2Wavefunction) := by
    simpa [M.schwartzToHilbert_eq_toLp] using hf
  have h := M.model.position_action_matches_hilbert_operator psi f hf'
  simpa [M.schwartzToHilbert_eq_toLp] using h

/-- Frontier support: momentum action compatibility specialized to the Mathlib
Schwartz-to-`L²` embedding. -/
theorem RealLineL2PositionMomentumModel.momentum_action_matches_toL2
    (M : RealLineL2PositionMomentumModel)
    (psi : M.model.common_core.core) (f : RealSchwartzWavefunction)
    (hf : realSchwartzToL2 f = (psi : RealLineL2Wavefunction)) :
    realSchwartzToL2 (M.model.momentumActionOnSchwartz f) =
      apply M.model.momentum (psi : RealLineL2Wavefunction)
        (M.model.common_core.core_le_momentum_domain psi.property) := by
  have hf' : M.model.schwartzToHilbert f = (psi : RealLineL2Wavefunction) := by
    simpa [M.schwartzToHilbert_eq_toLp] using hf
  have h := M.model.momentum_action_matches_hilbert_operator psi f hf'
  simpa [M.schwartzToHilbert_eq_toLp] using h

/-- Frontier 0014-21: the position operator restricted to the model's
Schwartz/common core. -/
noncomputable def RealLinePositionRestrictedToSchwartzCore
    (M : RealLineL2PositionMomentumModel) :
    UnboundedHilbertOperator ℂ RealLineL2Wavefunction :=
  restrictToSubmodule M.model.position M.model.common_core.core
    M.model.common_core.core_le_position_domain

/-- Frontier 0014-22: the momentum operator restricted to the model's
Schwartz/common core. -/
noncomputable def RealLineMomentumRestrictedToSchwartzCore
    (M : RealLineL2PositionMomentumModel) :
    UnboundedHilbertOperator ℂ RealLineL2Wavefunction :=
  restrictToSubmodule M.model.momentum M.model.common_core.core
    M.model.common_core.core_le_momentum_domain

/-- Frontier support: the restricted position operator has dense domain because
the common invariant core is dense. -/
theorem RealLinePositionRestrictedToSchwartzCore_hasDenseDomain
    (M : RealLineL2PositionMomentumModel) :
    HasDenseDomain (RealLinePositionRestrictedToSchwartzCore M) :=
  show Dense ((M.model.common_core.core : Set RealLineL2Wavefunction)) from
  M.model.common_core.core_dense

/-- Frontier support: the restricted momentum operator has dense domain because
the common invariant core is dense. -/
theorem RealLineMomentumRestrictedToSchwartzCore_hasDenseDomain
    (M : RealLineL2PositionMomentumModel) :
    HasDenseDomain (RealLineMomentumRestrictedToSchwartzCore M) :=
  show Dense ((M.model.common_core.core : Set RealLineL2Wavefunction)) from
  M.model.common_core.core_dense

/-- Frontier 0014-23: the exact graph-core target for position.  This is the
Mathlib topology statement needed to upgrade a Schwartz-core operator into the
closed real-line position operator. -/
def RealLinePositionSchwartzGraphCoreTarget
    (M : RealLineL2PositionMomentumModel) : Prop :=
  closure (graph (RealLinePositionRestrictedToSchwartzCore M)) =
    graph M.model.position

/-- Frontier 0014-24: the exact graph-core target for momentum.  This is the
Mathlib topology statement needed to upgrade a Schwartz-core operator into the
closed real-line momentum operator. -/
def RealLineMomentumSchwartzGraphCoreTarget
    (M : RealLineL2PositionMomentumModel) : Prop :=
  closure (graph (RealLineMomentumRestrictedToSchwartzCore M)) =
    graph M.model.momentum

/-- Frontier 0014-25: position essential self-adjointness on the Schwartz core,
spelled as a dense restricted operator, a graph-core closure target, and the
self-adjoint closure witness carried by the ambient model. -/
def RealLinePositionEssentialSelfAdjointOnSchwartzCoreTarget
    (M : RealLineL2PositionMomentumModel) : Prop :=
  HasDenseDomain (RealLinePositionRestrictedToSchwartzCore M) ∧
    RealLinePositionSchwartzGraphCoreTarget M ∧
      SelfAdjointUnboundedOperatorWitness M.model.position

/-- Frontier 0014-26: momentum essential self-adjointness on the Schwartz core,
spelled as a dense restricted operator, a graph-core closure target, and the
self-adjoint closure witness carried by the ambient model. -/
def RealLineMomentumEssentialSelfAdjointOnSchwartzCoreTarget
    (M : RealLineL2PositionMomentumModel) : Prop :=
  HasDenseDomain (RealLineMomentumRestrictedToSchwartzCore M) ∧
    RealLineMomentumSchwartzGraphCoreTarget M ∧
      SelfAdjointUnboundedOperatorWitness M.model.momentum

/-- Frontier 0014-27: a spectral-calculus availability target for position is
now tied to the explicit Schwartz-core essential-self-adjointness target. -/
def RealLinePositionSpectralCalculusAvailable
    (M : RealLineL2PositionMomentumModel) : Prop :=
  RealLinePositionEssentialSelfAdjointOnSchwartzCoreTarget M

/-- Frontier 0014-28: a spectral-calculus availability target for momentum is
now tied to the explicit Schwartz-core essential-self-adjointness target. -/
def RealLineMomentumSpectralCalculusAvailable
    (M : RealLineL2PositionMomentumModel) : Prop :=
  RealLineMomentumEssentialSelfAdjointOnSchwartzCoreTarget M

/-- Frontier 0014-29: the closed self-adjoint position target separates graph
closedness from the existing self-adjoint witness. -/
def RealLinePositionClosedSelfAdjointTarget
    (M : RealLineL2PositionMomentumModel) : Prop :=
  IsClosedUnboundedOperator M.model.position ∧
    SelfAdjointUnboundedOperatorWitness M.model.position

/-- Frontier 0014-30: the closed self-adjoint momentum target separates graph
closedness from the existing self-adjoint witness. -/
def RealLineMomentumClosedSelfAdjointTarget
    (M : RealLineL2PositionMomentumModel) : Prop :=
  IsClosedUnboundedOperator M.model.momentum ∧
    SelfAdjointUnboundedOperatorWitness M.model.momentum

/-- Frontier 0014-31: position spectral-measure availability is a typed target
after the closed self-adjoint position operator has been isolated. -/
def RealLinePositionSpectralMeasureTarget
    (M : RealLineL2PositionMomentumModel) : Prop :=
  RealLinePositionClosedSelfAdjointTarget M ∧
    RealLinePositionSpectralCalculusAvailable M

/-- Frontier 0014-32: momentum spectral-measure availability is a typed target
after the closed self-adjoint momentum operator has been isolated. -/
def RealLineMomentumSpectralMeasureTarget
    (M : RealLineL2PositionMomentumModel) : Prop :=
  RealLineMomentumClosedSelfAdjointTarget M ∧
    RealLineMomentumSpectralCalculusAvailable M

/-- Frontier 0014-33: a Mathlib-native one-parameter unitary-group target over
the real-line `L²` carrier.  We use continuous linear maps, norm preservation,
composition, and strong continuity as explicit obligations. -/
structure RealLineOneParameterUnitaryGroupTarget : Type where
  group : ℝ → RealLineL2Wavefunction →L[ℂ] RealLineL2Wavefunction
  identity_law : group 0 = 1
  composition_law : ∀ s t : ℝ, group (s + t) = (group s).comp (group t)
  norm_preserving : ∀ t : ℝ, ∀ psi : RealLineL2Wavefunction, ‖group t psi‖ = ‖psi‖
  inner_preserving :
    ∀ t : ℝ, ∀ psi phi : RealLineL2Wavefunction,
      inner ℂ (group t psi) (group t phi) = inner ℂ psi phi
  strong_continuity :
    Continuous fun p : ℝ × RealLineL2Wavefunction => group p.1 p.2

/-- Frontier support: the inverse law for a one-parameter unitary group follows
from the group law at `t + (-t)`. -/
theorem RealLineOneParameterUnitaryGroupTarget.right_inverse_law
    (U : RealLineOneParameterUnitaryGroupTarget) (t : ℝ) :
    (U.group t).comp (U.group (-t)) = 1 := by
  have h := U.composition_law t (-t)
  have hzero : t + -t = 0 := by abel
  rw [hzero, U.identity_law] at h
  exact h.symm

/-- Frontier support: the opposite inverse law follows from the group law at
`(-t) + t`. -/
theorem RealLineOneParameterUnitaryGroupTarget.left_inverse_law
    (U : RealLineOneParameterUnitaryGroupTarget) (t : ℝ) :
    (U.group (-t)).comp (U.group t) = 1 := by
  have h := U.composition_law (-t) t
  have hzero : -t + t = 0 := by abel
  rw [hzero, U.identity_law] at h
  exact h.symm

/-- Frontier 0014-34: Stone's theorem target for the position operator,
represented as the availability of a strongly continuous unitary group after
the position spectral-measure target is in scope. -/
def RealLinePositionStoneGroupTarget
    (M : RealLineL2PositionMomentumModel) : Prop :=
  RealLinePositionSpectralMeasureTarget M ∧
    Nonempty RealLineOneParameterUnitaryGroupTarget

/-- Frontier 0014-35: Stone's theorem target for the momentum operator,
represented as the availability of a strongly continuous unitary group after
the momentum spectral-measure target is in scope. -/
def RealLineMomentumStoneGroupTarget
    (M : RealLineL2PositionMomentumModel) : Prop :=
  RealLineMomentumSpectralMeasureTarget M ∧
    Nonempty RealLineOneParameterUnitaryGroupTarget

/-- Frontier 0014-36: a Fourier-transform intertwinement target for the
position/momentum pair.  Domain transport remains explicit because both
operators are unbounded. -/
structure RealLineFourierPositionMomentumIntertwinerTarget
    (M : RealLineL2PositionMomentumModel) : Type where
  fourier : RealLineL2Wavefunction →L[ℂ] RealLineL2Wavefunction
  inverse_fourier : RealLineL2Wavefunction →L[ℂ] RealLineL2Wavefunction
  left_inverse : inverse_fourier.comp fourier = 1
  right_inverse : fourier.comp inverse_fourier = 1
  norm_preserving : ∀ psi : RealLineL2Wavefunction, ‖fourier psi‖ = ‖psi‖
  fourier_maps_core_to_momentum_domain :
    ∀ psi : M.model.common_core.core,
      fourier (psi : RealLineL2Wavefunction) ∈ M.model.momentum.domain
  fourier_intertwines_position_momentum_on_core :
    ∀ psi : M.model.common_core.core,
      apply M.model.momentum
          (fourier (psi : RealLineL2Wavefunction))
          (fourier_maps_core_to_momentum_domain psi) =
        fourier
          (apply M.model.position (psi : RealLineL2Wavefunction)
            (M.model.common_core.core_le_position_domain psi.property))

/-- Frontier 0014-37: the Weyl relation target keeps exponentiated position and
momentum groups, phase convention, and common Hilbert carrier explicit. -/
structure RealLineWeylRelationTarget
    (M : RealLineL2PositionMomentumModel) : Type where
  position_group : RealLineOneParameterUnitaryGroupTarget
  momentum_group : RealLineOneParameterUnitaryGroupTarget
  weyl_relation :
    ∀ s t : ℝ, ∀ psi : RealLineL2Wavefunction,
      position_group.group s (momentum_group.group t psi) =
        Complex.exp (Complex.I * (s : ℂ) * (t : ℂ) * (M.model.hbar : ℂ)) •
          momentum_group.group t (position_group.group s psi)

/-- Frontier 0014-39: Stone-generator target for a one-parameter group.  The
infinitesimal generator is still an unbounded operator, so the core-domain
evidence remains explicit. -/
structure RealLineStoneGeneratorTarget
    (M : RealLineL2PositionMomentumModel)
    (A : UnboundedHilbertOperator ℂ RealLineL2Wavefunction)
    (U : RealLineOneParameterUnitaryGroupTarget) : Type where
  core_le_generator_domain : M.model.common_core.core ≤ A.domain
  derivative_on_core :
    ∀ psi : M.model.common_core.core,
      HasDerivAt (fun t : ℝ => U.group t (psi : RealLineL2Wavefunction))
        (Complex.I • apply A (psi : RealLineL2Wavefunction)
          (core_le_generator_domain psi.property)) 0

/-- Frontier 0014-40: position Stone-generator target on the common Schwartz
core. -/
def RealLinePositionStoneGeneratorTarget
    (M : RealLineL2PositionMomentumModel)
    (U : RealLineOneParameterUnitaryGroupTarget) : Type :=
  RealLineStoneGeneratorTarget M M.model.position U

/-- Frontier 0014-41: momentum Stone-generator target on the common Schwartz
core. -/
def RealLineMomentumStoneGeneratorTarget
    (M : RealLineL2PositionMomentumModel)
    (U : RealLineOneParameterUnitaryGroupTarget) : Type :=
  RealLineStoneGeneratorTarget M M.model.momentum U

/-- Frontier 0014-42: concrete modulation action for the exponentiated
position group on Schwartz representatives. -/
structure RealLinePositionModulationActionTarget
    (U : RealLineOneParameterUnitaryGroupTarget) : Type where
  modulationOnSchwartz : ℝ → RealSchwartzWavefunction → RealSchwartzWavefunction
  toL2_intertwines :
    ∀ t : ℝ, ∀ f : RealSchwartzWavefunction,
      realSchwartzToL2 (modulationOnSchwartz t f) = U.group t (realSchwartzToL2 f)
  pointwise_phase :
    ∀ t : ℝ, ∀ f : RealSchwartzWavefunction, ∀ x : ℝ,
      modulationOnSchwartz t f x =
        Complex.exp (Complex.I * (t : ℂ) * (x : ℂ)) * f x

/-- Frontier 0014-43: concrete translation action for the exponentiated
momentum group on Schwartz representatives. -/
structure RealLineMomentumTranslationActionTarget
    (M : RealLineL2PositionMomentumModel)
    (U : RealLineOneParameterUnitaryGroupTarget) : Type where
  translationOnSchwartz : ℝ → RealSchwartzWavefunction → RealSchwartzWavefunction
  toL2_intertwines :
    ∀ t : ℝ, ∀ f : RealSchwartzWavefunction,
      realSchwartzToL2 (translationOnSchwartz t f) = U.group t (realSchwartzToL2 f)
  pointwise_translation :
    ∀ t : ℝ, ∀ f : RealSchwartzWavefunction, ∀ x : ℝ,
      translationOnSchwartz t f x = f (x - M.model.hbar * t)

/-- Frontier 0014-44: a concrete Schwartz-representative Weyl law induced by
modulation and translation actions. -/
structure RealLineWeylRelationFromConcreteActionsTarget
    (M : RealLineL2PositionMomentumModel)
    (positionGroup : RealLineOneParameterUnitaryGroupTarget)
    (momentumGroup : RealLineOneParameterUnitaryGroupTarget)
    (positionAction : RealLinePositionModulationActionTarget positionGroup)
    (momentumAction : RealLineMomentumTranslationActionTarget M momentumGroup) : Type where
  weyl_on_schwartz :
    ∀ s t : ℝ, ∀ f : RealSchwartzWavefunction,
      positionAction.modulationOnSchwartz s (momentumAction.translationOnSchwartz t f) =
        Complex.exp (Complex.I * (s : ℂ) * (t : ℂ) * (M.model.hbar : ℂ)) •
          momentumAction.translationOnSchwartz t
            (positionAction.modulationOnSchwartz s f)

/-- Frontier 0014-45: recursive packet for phase-space action semantics after
the abstract Weyl and Stone-group targets have been named. -/
structure RealLineL2PhaseSpaceActionFrontier
    (M : RealLineL2PositionMomentumModel) : Type where
  position_group : RealLineOneParameterUnitaryGroupTarget
  momentum_group : RealLineOneParameterUnitaryGroupTarget
  position_generator : RealLinePositionStoneGeneratorTarget M position_group
  momentum_generator : RealLineMomentumStoneGeneratorTarget M momentum_group
  position_modulation_action : RealLinePositionModulationActionTarget position_group
  momentum_translation_action : RealLineMomentumTranslationActionTarget M momentum_group
  weyl_from_concrete_actions :
    RealLineWeylRelationFromConcreteActionsTarget M
      position_group momentum_group position_modulation_action momentum_translation_action

/-- Frontier 0014-46: the scalar phase appearing in the real-line Weyl
relation, named so differentiation obligations target a Mathlib expression. -/
noncomputable def realLineWeylPhaseScalar
    (M : RealLineL2PositionMomentumModel) (s t : ℝ) : ℂ :=
  Complex.exp (Complex.I * (s : ℂ) * (t : ℂ) * (M.model.hbar : ℂ))

/-- Frontier 0014-47: differentiability of the Weyl phase at the axes.  These
are the scalar analytic obligations needed before differentiating the Weyl
relation back to a canonical commutator. -/
structure RealLineWeylPhaseDifferentiationTarget
    (M : RealLineL2PositionMomentumModel) : Type where
  phase_has_s_derivative_at_zero :
    ∀ t : ℝ,
      HasDerivAt (fun s : ℝ => realLineWeylPhaseScalar M s t)
        (Complex.I * (t : ℂ) * (M.model.hbar : ℂ)) 0
  phase_has_t_derivative_at_zero :
    ∀ s : ℝ,
      HasDerivAt (fun t : ℝ => realLineWeylPhaseScalar M s t)
        (Complex.I * (s : ℂ) * (M.model.hbar : ℂ)) 0

/-- Frontier 0014-48: differentiability of the two Weyl orbit sides on the
common core, with domain evidence for unbounded generators kept explicit. -/
structure RealLineWeylOrbitDifferentiationTarget
    (M : RealLineL2PositionMomentumModel)
    (W : RealLineWeylRelationTarget M) : Type where
  momentum_orbit_in_position_domain :
    ∀ t : ℝ, ∀ psi : M.model.common_core.core,
      W.momentum_group.group t (psi : RealLineL2Wavefunction) ∈ M.model.position.domain
  position_orbit_in_momentum_domain :
    ∀ s : ℝ, ∀ psi : M.model.common_core.core,
      W.position_group.group s (psi : RealLineL2Wavefunction) ∈ M.model.momentum.domain
  derivative_position_after_momentum :
    ∀ t : ℝ, ∀ psi : M.model.common_core.core,
      HasDerivAt
        (fun s : ℝ =>
          W.position_group.group s
            (W.momentum_group.group t (psi : RealLineL2Wavefunction)))
        (Complex.I •
          apply M.model.position
            (W.momentum_group.group t (psi : RealLineL2Wavefunction))
            (momentum_orbit_in_position_domain t psi)) 0
  derivative_momentum_after_position :
    ∀ s : ℝ, ∀ psi : M.model.common_core.core,
      HasDerivAt
        (fun t : ℝ =>
          W.momentum_group.group t
            (W.position_group.group s (psi : RealLineL2Wavefunction)))
        (Complex.I •
          apply M.model.momentum
            (W.position_group.group s (psi : RealLineL2Wavefunction))
            (position_orbit_in_momentum_domain s psi)) 0

/-- Frontier 0014-49: differentiated Weyl relation target, collecting the
phase and orbit differentiability obligations that should imply the canonical
commutator on the common core. -/
structure RealLineWeylToCommutatorDifferentiationFrontier
    (M : RealLineL2PositionMomentumModel) : Type where
  weyl_relation : RealLineWeylRelationTarget M
  phase_differentiation : RealLineWeylPhaseDifferentiationTarget M
  orbit_differentiation : RealLineWeylOrbitDifferentiationTarget M weyl_relation
  differentiated_commutator_on_core :
    ∀ psi : M.model.common_core.core,
      commutatorValueOnCore M.model.common_core psi =
        (Complex.I * (M.model.hbar : ℂ)) • (psi : RealLineL2Wavefunction)

/-- Frontier 0014-50: covariance and Robertson/Schrödinger-style uncertainty
obligations over common-core states.  This keeps the stronger uncertainty
target separate from the Heisenberg specialization already used by 0014. -/
structure RealLineRobertsonSchrodingerFrontier
    (M : RealLineL2PositionMomentumModel) : Type where
  centered_position : M.model.common_core.core → RealLineL2Wavefunction
  centered_momentum : M.model.common_core.core → RealLineL2Wavefunction
  covariance : M.model.common_core.core → ℂ
  covariance_real_part : M.model.common_core.core → ℝ
  covariance_imaginary_part : M.model.common_core.core → ℝ
  covariance_decomposition :
    ∀ psi : M.model.common_core.core,
      covariance psi =
        (covariance_real_part psi : ℂ) +
          Complex.I * (covariance_imaginary_part psi : ℂ)
  robertson_schrodinger_bound :
    ∀ psi : M.model.common_core.core, ‖(psi : RealLineL2Wavefunction)‖ = 1 →
      (M.model.hbar / 2) ^ 2 + (covariance_real_part psi) ^ 2 ≤
        ‖centered_position psi‖ ^ 2 * ‖centered_momentum psi‖ ^ 2

/-- Frontier 0014-52: position expectation on the common core, using the
unbounded-operator domain evidence carried by the model. -/
noncomputable def realLinePositionExpectationOnCore
    (M : RealLineL2PositionMomentumModel) (psi : M.model.common_core.core) : ℂ :=
  expectationOnDomain M.model.position
    ⟨(psi : RealLineL2Wavefunction),
      M.model.common_core.core_le_position_domain psi.property⟩

/-- Frontier 0014-53: momentum expectation on the common core, using the
unbounded-operator domain evidence carried by the model. -/
noncomputable def realLineMomentumExpectationOnCore
    (M : RealLineL2PositionMomentumModel) (psi : M.model.common_core.core) : ℂ :=
  expectationOnDomain M.model.momentum
    ⟨(psi : RealLineL2Wavefunction),
      M.model.common_core.core_le_momentum_domain psi.property⟩

/-- Frontier 0014-54: centered position action `(X - ⟨X⟩)ψ` for unbounded
position on common-core states. -/
noncomputable def realLineCenteredPositionAction
    (M : RealLineL2PositionMomentumModel) (psi : M.model.common_core.core) :
    RealLineL2Wavefunction :=
  apply M.model.position (psi : RealLineL2Wavefunction)
      (M.model.common_core.core_le_position_domain psi.property) -
    realLinePositionExpectationOnCore M psi • (psi : RealLineL2Wavefunction)

/-- Frontier 0014-55: centered momentum action `(P - ⟨P⟩)ψ` for unbounded
momentum on common-core states. -/
noncomputable def realLineCenteredMomentumAction
    (M : RealLineL2PositionMomentumModel) (psi : M.model.common_core.core) :
    RealLineL2Wavefunction :=
  apply M.model.momentum (psi : RealLineL2Wavefunction)
      (M.model.common_core.core_le_momentum_domain psi.property) -
    realLineMomentumExpectationOnCore M psi • (psi : RealLineL2Wavefunction)

/-- Frontier 0014-56: variance identities connecting common-core variances to
the squared norms of centered unbounded actions. -/
structure RealLineCoreVarianceIdentityFrontier
    (M : RealLineL2PositionMomentumModel) : Type where
  position_variance : M.model.common_core.core → ℝ
  momentum_variance : M.model.common_core.core → ℝ
  position_variance_eq_centered_norm :
    ∀ psi : M.model.common_core.core,
      position_variance psi = ‖realLineCenteredPositionAction M psi‖ ^ 2
  momentum_variance_eq_centered_norm :
    ∀ psi : M.model.common_core.core,
      momentum_variance psi = ‖realLineCenteredMomentumAction M psi‖ ^ 2

/-- Frontier 0014-57: covariance-free specialization of the
Robertson/Schrödinger frontier to the Heisenberg squared lower bound. -/
structure RealLineRobertsonToHeisenbergSpecializationFrontier
    (M : RealLineL2PositionMomentumModel) : Type where
  robertson_schrodinger : RealLineRobertsonSchrodingerFrontier M
  covariance_real_vanishes :
    ∀ psi : M.model.common_core.core,
      robertson_schrodinger.covariance_real_part psi = 0
  centered_position_matches_unbounded_action :
    ∀ psi : M.model.common_core.core,
      robertson_schrodinger.centered_position psi =
        realLineCenteredPositionAction M psi
  centered_momentum_matches_unbounded_action :
    ∀ psi : M.model.common_core.core,
      robertson_schrodinger.centered_momentum psi =
        realLineCenteredMomentumAction M psi

/-- Frontier support: covariance-free Robertson/Schrödinger evidence implies
the Heisenberg squared lower bound for centered unbounded actions. -/
theorem realLineHeisenbergSquaredBound_of_robertsonSpecialization
    {M : RealLineL2PositionMomentumModel}
    (S : RealLineRobertsonToHeisenbergSpecializationFrontier M)
    (psi : M.model.common_core.core)
    (normalized : ‖(psi : RealLineL2Wavefunction)‖ = 1) :
    (M.model.hbar / 2) ^ 2 ≤
      ‖realLineCenteredPositionAction M psi‖ ^ 2 *
        ‖realLineCenteredMomentumAction M psi‖ ^ 2 := by
  have h := S.robertson_schrodinger.robertson_schrodinger_bound psi normalized
  rw [S.covariance_real_vanishes psi] at h
  rw [S.centered_position_matches_unbounded_action psi,
    S.centered_momentum_matches_unbounded_action psi] at h
  nlinarith

/-- Frontier 0014-58: final standard-deviation target connecting squared
variance identities to the Heisenberg product statement on common-core states. -/
structure RealLineHeisenbergStandardDeviationFrontier
    (M : RealLineL2PositionMomentumModel) : Type where
  variance_identities : RealLineCoreVarianceIdentityFrontier M
  sigma_position : M.model.common_core.core → ℝ
  sigma_momentum : M.model.common_core.core → ℝ
  sigma_position_nonneg :
    ∀ psi : M.model.common_core.core, 0 ≤ sigma_position psi
  sigma_momentum_nonneg :
    ∀ psi : M.model.common_core.core, 0 ≤ sigma_momentum psi
  sigma_position_sq_eq_variance :
    ∀ psi : M.model.common_core.core,
      sigma_position psi ^ 2 = variance_identities.position_variance psi
  sigma_momentum_sq_eq_variance :
    ∀ psi : M.model.common_core.core,
      sigma_momentum psi ^ 2 = variance_identities.momentum_variance psi
  heisenberg_product_bound :
    ∀ psi : M.model.common_core.core, ‖(psi : RealLineL2Wavefunction)‖ = 1 →
      sigma_position psi * sigma_momentum psi ≥ M.model.hbar / 2

/-- Frontier 0014-59: the standard-deviation uncertainty product as a named
Mathlib real expression. -/
noncomputable def realLineUncertaintyProduct
    (M : RealLineL2PositionMomentumModel)
    (Hsd : RealLineHeisenbergStandardDeviationFrontier M)
    (psi : M.model.common_core.core) : ℝ :=
  Hsd.sigma_position psi * Hsd.sigma_momentum psi

/-- Frontier 0014-60: normalized common-core states saturating the Heisenberg
product lower bound. -/
structure RealLineMinimumUncertaintySaturationFrontier
    (M : RealLineL2PositionMomentumModel) : Type where
  heisenberg_standard_deviation : RealLineHeisenbergStandardDeviationFrontier M
  saturation_states : Set M.model.common_core.core
  normalized_on_saturation :
    ∀ psi : M.model.common_core.core,
      psi ∈ saturation_states → ‖(psi : RealLineL2Wavefunction)‖ = 1
  product_saturates :
    ∀ psi : M.model.common_core.core,
      psi ∈ saturation_states →
        realLineUncertaintyProduct M heisenberg_standard_deviation psi =
          M.model.hbar / 2

/-- Frontier support: saturation states carry the exact Heisenberg product
identity, not only the lower-bound inequality. -/
theorem realLineHeisenbergProduct_eq_on_saturation
    {M : RealLineL2PositionMomentumModel}
    (S : RealLineMinimumUncertaintySaturationFrontier M)
    (psi : M.model.common_core.core)
    (hpsi : psi ∈ S.saturation_states) :
    realLineUncertaintyProduct M S.heisenberg_standard_deviation psi =
      M.model.hbar / 2 :=
  S.product_saturates psi hpsi

/-- Frontier 0014-61: residual for the centered linear-dependence equation
characterizing minimum-uncertainty states. -/
noncomputable def realLineMinimumUncertaintyResidual
    (M : RealLineL2PositionMomentumModel)
    (slope : ℂ) (psi : M.model.common_core.core) :
    RealLineL2Wavefunction :=
  realLineCenteredMomentumAction M psi -
    slope • realLineCenteredPositionAction M psi

/-- Frontier 0014-62: equality-case equation for Heisenberg saturation.  The
linear-dependence slope is explicit so later analytic work can refine it into
Gaussian/coherent-state parameters. -/
structure RealLineMinimumUncertaintyEquationFrontier
    (M : RealLineL2PositionMomentumModel) : Type where
  saturation : RealLineMinimumUncertaintySaturationFrontier M
  slope : M.model.common_core.core → ℂ
  slope_imaginary_positive :
    ∀ psi : M.model.common_core.core,
      psi ∈ saturation.saturation_states → 0 ≤ (slope psi).im
  residual_vanishes_on_saturation :
    ∀ psi : M.model.common_core.core,
      psi ∈ saturation.saturation_states →
        realLineMinimumUncertaintyResidual M (slope psi) psi = 0
  residual_vanishing_implies_saturation :
    ∀ psi : M.model.common_core.core,
      ‖(psi : RealLineL2Wavefunction)‖ = 1 →
        realLineMinimumUncertaintyResidual M (slope psi) psi = 0 →
          psi ∈ saturation.saturation_states

/-- Frontier support: the equality-case residual equation promotes a
normalized state to a saturation state. -/
theorem realLineSaturation_of_minimumUncertaintyResidual
    {M : RealLineL2PositionMomentumModel}
    (E : RealLineMinimumUncertaintyEquationFrontier M)
    (psi : M.model.common_core.core)
    (normalized : ‖(psi : RealLineL2Wavefunction)‖ = 1)
    (hresidual : realLineMinimumUncertaintyResidual M (E.slope psi) psi = 0) :
    psi ∈ E.saturation.saturation_states :=
  E.residual_vanishing_implies_saturation psi normalized hresidual

/-- Frontier 0014-63: Schwartz/Gaussian representative target for saturated
minimum-uncertainty states.  The Gaussian predicate is an explicit field so the
analytic characterization can be recursively grounded instead of assumed from
Dirac notation. -/
structure RealLineGaussianMinimumUncertaintyFrontier
    (M : RealLineL2PositionMomentumModel) : Type where
  equation_frontier : RealLineMinimumUncertaintyEquationFrontier M
  gaussian_profile :
    M.model.common_core.core → RealSchwartzWavefunction
  gaussian_profile_represents_state :
    ∀ psi : M.model.common_core.core,
      psi ∈ equation_frontier.saturation.saturation_states →
        realSchwartzToL2 (gaussian_profile psi) =
          (psi : RealLineL2Wavefunction)
  gaussian_profile_satisfies_residual :
    ∀ psi : M.model.common_core.core,
      psi ∈ equation_frontier.saturation.saturation_states →
        realLineMinimumUncertaintyResidual M
          (equation_frontier.slope psi) psi = 0
  gaussian_characterization_complete :
    ∀ psi : M.model.common_core.core,
      (∃ f : RealSchwartzWavefunction,
        realSchwartzToL2 f = (psi : RealLineL2Wavefunction)) →
        realLineMinimumUncertaintyResidual M
          (equation_frontier.slope psi) psi = 0 →
          psi ∈ equation_frontier.saturation.saturation_states

/-- Frontier 0014-64: phase-space coherent-state orbit target generated from
minimum-uncertainty Gaussian states by the real-line Weyl actions. -/
structure RealLineCoherentStateOrbitFrontier
    (M : RealLineL2PositionMomentumModel) : Type where
  phase_space_actions : RealLineL2PhaseSpaceActionFrontier M
  gaussian_minimum_uncertainty : RealLineGaussianMinimumUncertaintyFrontier M
  coherent_states : Set M.model.common_core.core
  coherent_subset_saturation :
    ∀ psi : M.model.common_core.core,
      psi ∈ coherent_states →
        psi ∈ gaussian_minimum_uncertainty.equation_frontier.saturation.saturation_states
  center_position : M.model.common_core.core → ℝ
  center_momentum : M.model.common_core.core → ℝ
  generated_by_phase_space_orbit :
    ∀ psi : M.model.common_core.core,
      psi ∈ coherent_states →
        ∃ phi : M.model.common_core.core,
          phi ∈ gaussian_minimum_uncertainty.equation_frontier.saturation.saturation_states ∧
            ∃ q p : ℝ,
              phase_space_actions.position_group.group q
                  (phase_space_actions.momentum_group.group p
                    (phi : RealLineL2Wavefunction)) =
                (psi : RealLineL2Wavefunction)

/-- Frontier 0014-51: phase-space-to-uncertainty packet.  This is the next
recursive target after concrete Weyl action semantics: differentiate Weyl to
CCR, then connect CCR to a stronger uncertainty statement. -/
structure RealLineL2WeylCCRUncertaintyFrontier
    (M : RealLineL2PositionMomentumModel) : Type where
  phase_space_actions : RealLineL2PhaseSpaceActionFrontier M
  weyl_to_commutator : RealLineWeylToCommutatorDifferentiationFrontier M
  robertson_schrodinger : RealLineRobertsonSchrodingerFrontier M
  variance_identities : RealLineCoreVarianceIdentityFrontier M
  robertson_to_heisenberg : RealLineRobertsonToHeisenbergSpecializationFrontier M
  heisenberg_standard_deviation : RealLineHeisenbergStandardDeviationFrontier M
  minimum_uncertainty_saturation : RealLineMinimumUncertaintySaturationFrontier M
  minimum_uncertainty_equation : RealLineMinimumUncertaintyEquationFrontier M
  gaussian_minimum_uncertainty : RealLineGaussianMinimumUncertaintyFrontier M
  coherent_state_orbit : RealLineCoherentStateOrbitFrontier M

/-- Frontier 0014-38: recursive spectral/Fourier phase-space target packet
collecting the next obligations after graph-core closure. -/
structure RealLineL2SpectralFourierFrontier
    (M : RealLineL2PositionMomentumModel) : Type where
  position_closed_self_adjoint : RealLinePositionClosedSelfAdjointTarget M
  momentum_closed_self_adjoint : RealLineMomentumClosedSelfAdjointTarget M
  position_spectral_measure : RealLinePositionSpectralMeasureTarget M
  momentum_spectral_measure : RealLineMomentumSpectralMeasureTarget M
  position_stone_group : RealLinePositionStoneGroupTarget M
  momentum_stone_group : RealLineMomentumStoneGroupTarget M
  fourier_intertwiner : RealLineFourierPositionMomentumIntertwinerTarget M
  weyl_relation : RealLineWeylRelationTarget M
  phase_space_actions : RealLineL2PhaseSpaceActionFrontier M
  weyl_ccr_uncertainty_frontier : RealLineL2WeylCCRUncertaintyFrontier M

/-- Recursive frontier packet for the remaining analytic closure obligations
after the first ten 0014 real-line `L²` surfaces are in place. -/
structure RealLineL2ClosureFrontier
    (M : RealLineL2PositionMomentumModel) : Type where
  schwartz_commutator_pointwise : RealLineSchwartzCanonicalCommutator M.model
  position_essentially_self_adjoint_on_schwartz :
    RealLinePositionEssentialSelfAdjointOnSchwartzCoreTarget M
  momentum_essentially_self_adjoint_on_schwartz :
    RealLineMomentumEssentialSelfAdjointOnSchwartzCoreTarget M
  spectral_calculus_available_for_position :
    RealLinePositionSpectralCalculusAvailable M
  spectral_calculus_available_for_momentum :
    RealLineMomentumSpectralCalculusAvailable M

/-- Frontier 0014-11: transporting the pointwise Schwartz commutator through
the Mathlib Schwartz-to-`L²` embedding agrees with the unbounded commutator on
the common core. -/
def RealLineSchwartzCommutatorTransport
    (M : RealLineL2PositionMomentumModel) : Prop :=
  ∀ psi : M.model.common_core.core, ∀ f : RealSchwartzWavefunction,
    realSchwartzToL2 f = (psi : RealLineL2Wavefunction) →
      realSchwartzToL2 (RealLineSchwartzCommutatorAction M.model f) =
        commutatorValueOnCore M.model.common_core psi

/-- Frontier 0014-12: the position/momentum action compatibility bridges imply
transport of the Schwartz commutator into the unbounded `L²` commutator. -/
theorem realLineSchwartzCommutatorTransport_from_actions
    (M : RealLineL2PositionMomentumModel) :
    RealLineSchwartzCommutatorTransport M := by
  intro psi f hf
  unfold RealLineSchwartzCommutatorAction commutatorValueOnCore
  rw [map_sub]
  rw [M.position_action_matches_toL2
      ⟨apply M.model.momentum (psi : RealLineL2Wavefunction)
          (M.model.common_core.core_le_momentum_domain psi.property),
        M.model.common_core.momentum_maps_core psi⟩
      (M.model.momentumActionOnSchwartz f)
      (M.momentum_action_matches_toL2 psi f hf)]
  rw [M.momentum_action_matches_toL2
      ⟨apply M.model.position (psi : RealLineL2Wavefunction)
          (M.model.common_core.core_le_position_domain psi.property),
        M.model.common_core.position_maps_core psi⟩
      (M.model.positionActionOnSchwartz f)
      (M.position_action_matches_toL2 psi f hf)]

/-- Frontier 0014-13: after transport into `L²`, the Schwartz commutator has
the canonical `iℏ` action on common-core representatives. -/
def RealLineSchwartzCanonicalCommutatorTransported
    (M : RealLineL2PositionMomentumModel) : Prop :=
  ∀ psi : M.model.common_core.core, ∀ f : RealSchwartzWavefunction,
    realSchwartzToL2 f = (psi : RealLineL2Wavefunction) →
      realSchwartzToL2 (RealLineSchwartzCommutatorAction M.model f) =
        (Complex.I * (M.model.hbar : ℂ)) • (psi : RealLineL2Wavefunction)

/-- Frontier 0014-14: commutator transport plus the model's canonical
common-core commutator gives the transported canonical commutator. -/
theorem realLineSchwartzCanonicalCommutatorTransported_of_transport
    (M : RealLineL2PositionMomentumModel)
    (htransport : RealLineSchwartzCommutatorTransport M) :
    RealLineSchwartzCanonicalCommutatorTransported M := by
  intro psi f hf
  rw [htransport psi f hf]
  exact M.model.canonical_commutator_on_core psi

/-- Frontier 0014-15: pointwise Schwartz canonical commutator evidence is kept
as an explicit dependency while promoting to the transported `L²` statement. -/
theorem realLineSchwartzCanonicalCommutatorTransported_of_pointwise
    (M : RealLineL2PositionMomentumModel)
    (htransport : RealLineSchwartzCommutatorTransport M)
    (_hpointwise : RealLineSchwartzCanonicalCommutator M.model) :
    RealLineSchwartzCanonicalCommutatorTransported M :=
  realLineSchwartzCanonicalCommutatorTransported_of_transport M htransport

/-- Frontier support: a canonical commutator equality in the SchwartzMap
carrier transports directly through the Mathlib Schwartz-to-`L²` linear map. -/
theorem realLineSchwartzCanonicalCommutatorTransported_of_schwartzMap
    (M : RealLineL2PositionMomentumModel)
    (hmap : RealLineSchwartzCanonicalCommutatorAsSchwartzMap M.model) :
    RealLineSchwartzCanonicalCommutatorTransported M := by
  intro psi f hf
  rw [hmap f]
  rw [map_smul]
  rw [hf]

/-- Frontier 0014-16: the position operator has the explicit dense-domain,
self-adjoint-witness, and Schwartz-core-domain obligations needed before
claiming essential self-adjointness on the real-line model. -/
def RealLinePositionEssentialSelfAdjointTarget
    (M : RealLineL2PositionMomentumModel) : Prop :=
  HasDenseDomain M.model.position ∧
    SelfAdjointUnboundedOperatorWitness M.model.position ∧
      M.model.common_core.core ≤ M.model.position.domain

/-- Frontier support for the position essential-self-adjointness target carried
by the current model interface. -/
theorem realLinePositionEssentialSelfAdjointTarget
    (M : RealLineL2PositionMomentumModel) :
    RealLinePositionEssentialSelfAdjointTarget M :=
  ⟨M.model.position_self_adjoint.dense_domain,
    M.model.position_self_adjoint,
    M.model.common_core.core_le_position_domain⟩

/-- Frontier 0014-17: the momentum operator has the explicit dense-domain,
self-adjoint-witness, and Schwartz-core-domain obligations needed before
claiming essential self-adjointness on the real-line model. -/
def RealLineMomentumEssentialSelfAdjointTarget
    (M : RealLineL2PositionMomentumModel) : Prop :=
  HasDenseDomain M.model.momentum ∧
    SelfAdjointUnboundedOperatorWitness M.model.momentum ∧
      M.model.common_core.core ≤ M.model.momentum.domain

/-- Frontier support for the momentum essential-self-adjointness target carried
by the current model interface. -/
theorem realLineMomentumEssentialSelfAdjointTarget
    (M : RealLineL2PositionMomentumModel) :
    RealLineMomentumEssentialSelfAdjointTarget M :=
  ⟨M.model.momentum_self_adjoint.dense_domain,
    M.model.momentum_self_adjoint,
    M.model.common_core.core_le_momentum_domain⟩

/-- Frontier 0014-18: spectral-calculus target packet for position.  The
available-calculus field remains an explicit obligation label until grounded in
a Mathlib spectral API. -/
structure RealLinePositionSpectralCalculusTarget
    (M : RealLineL2PositionMomentumModel) : Type where
  essential_self_adjoint : RealLinePositionEssentialSelfAdjointTarget M
  spectral_calculus_available : RealLinePositionSpectralCalculusAvailable M

/-- Frontier 0014-19: spectral-calculus target packet for momentum.  The
available-calculus field remains an explicit obligation label until grounded in
a Mathlib spectral API. -/
structure RealLineMomentumSpectralCalculusTarget
    (M : RealLineL2PositionMomentumModel) : Type where
  essential_self_adjoint : RealLineMomentumEssentialSelfAdjointTarget M
  spectral_calculus_available : RealLineMomentumSpectralCalculusAvailable M

/-- Frontier 0014-20: recursive packet collecting the next self-adjointness and
spectral-calculus closure targets exposed by the real-line `L²` model. -/
structure RealLineL2SpectralClosureTargets
    (M : RealLineL2PositionMomentumModel) : Type where
  position_essential_self_adjoint : RealLinePositionEssentialSelfAdjointTarget M
  momentum_essential_self_adjoint : RealLineMomentumEssentialSelfAdjointTarget M
  position_spectral_calculus : RealLinePositionSpectralCalculusTarget M
  momentum_spectral_calculus : RealLineMomentumSpectralCalculusTarget M
  spectral_fourier_frontier : RealLineL2SpectralFourierFrontier M

/-- Frontier support: the first closure-frontier packet expands into the next
self-adjointness and spectral-calculus target packet. -/
def RealLineL2ClosureFrontier.toSpectralClosureTargets
    (M : RealLineL2PositionMomentumModel)
    (C : RealLineL2ClosureFrontier M)
    (F : RealLineL2SpectralFourierFrontier M) :
    RealLineL2SpectralClosureTargets M :=
  let hpos := realLinePositionEssentialSelfAdjointTarget M
  let hmom := realLineMomentumEssentialSelfAdjointTarget M
  { position_essential_self_adjoint := hpos
    momentum_essential_self_adjoint := hmom
    position_spectral_calculus :=
      { essential_self_adjoint := hpos
        spectral_calculus_available := C.spectral_calculus_available_for_position }
    momentum_spectral_calculus :=
      { essential_self_adjoint := hmom
        spectral_calculus_available := C.spectral_calculus_available_for_momentum }
    spectral_fourier_frontier := F }

/-- The concrete real-line `L²` realization inherits the canonical commutator
expectation theorem from the generic Schwartz/L2 model. -/
theorem canonicalCommutatorExpectationOnRealLineL2SchwartzCore
    (M : RealLineL2PositionMomentumModel)
    (psi : M.model.common_core.core)
    (normalized : ‖(psi : RealLineL2Wavefunction)‖ = 1) :
    inner ℂ (psi : RealLineL2Wavefunction) (commutatorValueOnCore M.model.common_core psi) =
      Complex.I * (M.model.hbar : ℂ) := by
  exact canonicalCommutatorExpectationOnSchwartzCore M.model psi normalized

end PositionMomentumModels
end Foundations
end MathformerPhysicsLib
