-- SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
-- SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
-- SPDX-License-Identifier: MIT
-- Neuro-symbolic AI Group
import Mathlib

namespace MathformerPhysicsLib
namespace Foundations
namespace UnboundedOperators

/-- Mathlib grounding: an unbounded Hilbert operator is represented by a
Mathlib linear submodule domain together with a linear action from the domain
subtype into the ambient Hilbert space.  This is intentionally not a
`ContinuousLinearMap`, so domain obligations cannot disappear. -/
structure UnboundedHilbertOperator (𝕜 : Type*) (H : Type*) [RCLike 𝕜]
    [NormedAddCommGroup H] [InnerProductSpace 𝕜 H] where
  domain : Submodule 𝕜 H
  action : domain →ₗ[𝕜] H

/-- Physics role: domain membership remains an explicit proposition. -/
def MemDomain {𝕜 H : Type*} [RCLike 𝕜] [NormedAddCommGroup H] [InnerProductSpace 𝕜 H]
    (A : UnboundedHilbertOperator 𝕜 H) (x : H) : Prop :=
  x ∈ A.domain

/-- Physics role: applying an unbounded operator requires explicit domain evidence. -/
def apply {𝕜 H : Type*} [RCLike 𝕜] [NormedAddCommGroup H] [InnerProductSpace 𝕜 H]
    (A : UnboundedHilbertOperator 𝕜 H) (x : H) (hx : MemDomain A x) : H :=
  A.action ⟨x, hx⟩

/-- Mathlib grounding: restrict a domain-bearing operator to a submodule of
its original domain.  This exposes core restrictions without pretending the
restricted operator is bounded. -/
def restrictToSubmodule {𝕜 H : Type*} [RCLike 𝕜] [NormedAddCommGroup H]
    [InnerProductSpace 𝕜 H] (A : UnboundedHilbertOperator 𝕜 H)
    (S : Submodule 𝕜 H) (hS : S ≤ A.domain) :
    UnboundedHilbertOperator 𝕜 H where
  domain := S
  action := A.action.comp (Submodule.inclusion hS)

/-- Mathlib grounding: applying a restricted unbounded operator is definitionally
the original operator action with the submodule-domain evidence transported. -/
theorem restrictToSubmodule_apply {𝕜 H : Type*} [RCLike 𝕜] [NormedAddCommGroup H]
    [InnerProductSpace 𝕜 H] (A : UnboundedHilbertOperator 𝕜 H)
    (S : Submodule 𝕜 H) (hS : S ≤ A.domain) (x : S) :
    apply (restrictToSubmodule A S hS) (x : H) x.property =
      apply A (x : H) (hS x.property) := rfl

/-- Mathlib grounding: applying to a domain subtype is definitional. -/
theorem apply_subtype {𝕜 H : Type*} [RCLike 𝕜] [NormedAddCommGroup H]
    [InnerProductSpace 𝕜 H] (A : UnboundedHilbertOperator 𝕜 H) (x : A.domain) :
    apply A (x : H) x.property = A.action x := rfl

/-- Mathlib grounding: unbounded-operator application is additive on its domain. -/
theorem apply_add {𝕜 H : Type*} [RCLike 𝕜] [NormedAddCommGroup H] [InnerProductSpace 𝕜 H]
    (A : UnboundedHilbertOperator 𝕜 H) {x y : H} (hx : MemDomain A x) (hy : MemDomain A y) :
    apply A (x + y) (A.domain.add_mem hx hy) = apply A x hx + apply A y hy := by
  exact A.action.map_add ⟨x, hx⟩ ⟨y, hy⟩

/-- Mathlib grounding: unbounded-operator application respects scalar
multiplication on its domain. -/
theorem apply_smul {𝕜 H : Type*} [RCLike 𝕜] [NormedAddCommGroup H]
    [InnerProductSpace 𝕜 H] (A : UnboundedHilbertOperator 𝕜 H) (c : 𝕜) {x : H}
    (hx : MemDomain A x) :
    apply A (c • x) (A.domain.smul_mem c hx) = c • apply A x hx := by
  exact A.action.map_smul c ⟨x, hx⟩

/-- Mathlib grounding: the graph of a domain-bearing operator is a set in the
product Hilbert space. Closedness can therefore be stated using Mathlib
topology, without pretending the operator is bounded. -/
def graph {𝕜 H : Type*} [RCLike 𝕜] [NormedAddCommGroup H] [InnerProductSpace 𝕜 H]
    (A : UnboundedHilbertOperator 𝕜 H) : Set (H × H) :=
  {p | ∃ hx : MemDomain A p.1, apply A p.1 hx = p.2}

/-- Physics role: a dense-domain obligation is explicit and Mathlib-native. -/
def HasDenseDomain {𝕜 H : Type*} [RCLike 𝕜] [NormedAddCommGroup H] [InnerProductSpace 𝕜 H]
    (A : UnboundedHilbertOperator 𝕜 H) : Prop :=
  Dense ((A.domain : Set H))

/-- Physics role: a closed unbounded operator is one whose graph is closed in
the Mathlib product topology. -/
def IsClosedUnboundedOperator {𝕜 H : Type*} [RCLike 𝕜] [NormedAddCommGroup H]
    [InnerProductSpace 𝕜 H] (A : UnboundedHilbertOperator 𝕜 H) : Prop :=
  IsClosed (graph A)

/-- Physics role: symmetry for an unbounded Hilbert operator is an
inner-product identity on the operator domain. -/
structure SymmetricUnboundedOperator {H : Type*} [NormedAddCommGroup H]
    [InnerProductSpace ℂ H] (A : UnboundedHilbertOperator ℂ H) : Prop where
  inner_symmetric : ∀ x y : A.domain,
    inner ℂ (A.action x) (y : H) = inner ℂ (x : H) (A.action y)

/-- Physics role: an adjoint witness relates two domain-bearing operators by
the Hilbert-space adjoint pairing.  This is a witness surface, not a claim that
Mathlib has promoted a full adjoint-domain API for this operator. -/
structure UnboundedAdjointWitness {H : Type*} [NormedAddCommGroup H]
    [InnerProductSpace ℂ H] (A Astar : UnboundedHilbertOperator ℂ H) : Prop where
  pairing : ∀ x : A.domain, ∀ y : Astar.domain,
    inner ℂ (A.action x) (y : H) = inner ℂ (x : H) (Astar.action y)

/-- Physics role: a self-adjoint unbounded-operator witness records dense
domain, adjoint pairing to itself, and the maximal-domain obligation usually
hidden by informal physics notation. -/
structure SelfAdjointUnboundedOperatorWitness {H : Type*} [NormedAddCommGroup H]
    [InnerProductSpace ℂ H] (A : UnboundedHilbertOperator ℂ H) : Prop where
  dense_domain : HasDenseDomain A
  adjoint_pairing : UnboundedAdjointWitness A A
  adjoint_domain_maximal :
    ∀ B : UnboundedHilbertOperator ℂ H, UnboundedAdjointWitness A B → B.domain ≤ A.domain

/-- Physics role: an expectation value for an unbounded operator is only formed
for a state that already carries domain evidence. -/
def expectationOnDomain {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H]
    (A : UnboundedHilbertOperator ℂ H) (psi : A.domain) : ℂ :=
  inner ℂ (psi : H) (A.action psi)

/-- Physics role: a common invariant core for two unbounded operators.  This is
the surface needed for products such as `XPψ` and `PXψ` in canonical
commutator statements. -/
structure CommonInvariantCore {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H]
    (X P : UnboundedHilbertOperator ℂ H) where
  core : Submodule ℂ H
  core_dense : Dense ((core : Set H))
  core_le_position_domain : core ≤ X.domain
  core_le_momentum_domain : core ≤ P.domain
  position_maps_core : ∀ psi : core, apply X (psi : H) (core_le_position_domain psi.property) ∈ core
  momentum_maps_core : ∀ psi : core, apply P (psi : H) (core_le_momentum_domain psi.property) ∈ core

/-- Physics role: the commutator value `[X,P]ψ = X(Pψ) - P(Xψ)` on a common
invariant core. -/
def commutatorValueOnCore {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H]
    {X P : UnboundedHilbertOperator ℂ H} (C : CommonInvariantCore X P) (psi : C.core) : H :=
  apply X
      (apply P (psi : H) (C.core_le_momentum_domain psi.property))
      (C.core_le_position_domain (C.momentum_maps_core psi)) -
    apply P
      (apply X (psi : H) (C.core_le_position_domain psi.property))
      (C.core_le_momentum_domain (C.position_maps_core psi))

/-- Physics role: a position/momentum pair is an unbounded-operator pair with a
dense common invariant core and a canonical commutator on that core. -/
structure PositionMomentumPair {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] where
  position : UnboundedHilbertOperator ℂ H
  momentum : UnboundedHilbertOperator ℂ H
  hbar : ℝ
  hbar_nonneg : 0 ≤ hbar
  position_self_adjoint : SelfAdjointUnboundedOperatorWitness position
  momentum_self_adjoint : SelfAdjointUnboundedOperatorWitness momentum
  common_core : CommonInvariantCore position momentum
  canonical_commutator_on_core :
    ∀ psi : common_core.core,
      commutatorValueOnCore common_core psi = (Complex.I * (hbar : ℂ)) • (psi : H)

/-- Physics role: the commutator expectation on a normalized vector in the
common core is the canonical scalar `iℏ`. -/
theorem canonicalCommutatorExpectationOnNormalizedCore {H : Type*} [NormedAddCommGroup H]
    [InnerProductSpace ℂ H] (Q : PositionMomentumPair)
    (psi : Q.common_core.core) (normalized : ‖(psi : H)‖ = 1) :
    inner ℂ (psi : H) (commutatorValueOnCore Q.common_core psi) = Complex.I * (Q.hbar : ℂ) := by
  have hinner : inner ℂ (psi : H) (psi : H) = 1 := by
    rw [inner_self_eq_norm_sq_to_K, normalized]
    norm_num
  rw [Q.canonical_commutator_on_core psi]
  rw [inner_smul_right, hinner, mul_one]

end UnboundedOperators
end Foundations
end MathformerPhysicsLib
