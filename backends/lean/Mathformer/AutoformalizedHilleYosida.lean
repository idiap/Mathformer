/-
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
#
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# Neuro-symbolic AI Group
#
# SPDX-License-Identifier: MIT
-/

/-
File Documentation

Motivation:
  Keep Lean-facing autoformalization artifacts buildable under the pinned mathlib environment.

Intent:
  Represent mathematical statements as explicit Lean declarations that can be checked, imported, and documented.

Function:
  Defines Lean modules, examples, and the sample executable entry point for the project.

Maintenance Notes:
  Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.
-/

import Mathlib.Analysis.Normed.Operator.Basic
import Mathlib.Analysis.SpecialFunctions.Exp
import Mathlib.Data.NNReal.Basic
import Mathlib.Order.Filter.Basic
import Mathlib.Topology.Algebra.Module.Basic
import Mathlib.Topology.Algebra.Semigroup

/-!
Interface-level autoformalization for the Hille--Yosida theorem.

This file keeps the still-external analytic boundary explicit:
- semigroup continuity/growth is represented concretely on bounded operators;
- strong continuity is primitive at `t = 0` (`∀ x, ContinuousAt (t ↦ T(t)x) 0`);
- unbounded-operator resolvent/generator details are isolated behind an explicit model interface;
- generator limits are expressed through punctured neighborhoods at `0` in `ℝ≥0`;
- theorem content is encoded as assumption packages over that interface.

Conceptual boundary:
this file formalizes the shape of Hille--Yosida statements, not yet the full
operator-theoretic/analytic substance.
-/

namespace Mathformer
namespace AutoformalizedHilleYosida

open scoped Topology

universe uX

variable {X : Type uX}
variable [NormedAddCommGroup X] [NormedSpace ℝ X]

/--
Generated note (NL): A `C₀` semigroup encoded as maps `ℝ≥0 → X →L[ℝ] X` with semigroup law and
continuity at zero as the primitive continuity assumption.
-/
structure C0Semigroup where
  /--
Generated note (NL): The semigroup action at nonnegative time `t`. -/
  toContinuousLinearMap : NNReal → (X →L[ℝ] X)
  /--
Generated note (NL): Semigroup value at time `0` is identity. -/
  map_zero' : toContinuousLinearMap 0 = 1
  /--
Generated note (NL): Semigroup composition law `T(s+t) = T(s) ∘ T(t)`. -/
  map_add' :
    ∀ s t : NNReal,
      toContinuousLinearMap (s + t) =
        (toContinuousLinearMap s).comp (toContinuousLinearMap t)
  /--
Generated note (NL): Primitive `C₀` continuity assumption: for each `x`, `t ↦ T(t)x` is continuous at `0`. -/
  stronglyContinuousAtZero' :
    ∀ x : X, ContinuousAt (fun t : NNReal => toContinuousLinearMap t x) 0

/--
Generated note (NL): Continuity-at-zero accessor for a `C₀` semigroup. -/
theorem C0Semigroup.stronglyContinuousAtZero
    (T : C0Semigroup (X := X))
    (x : X) :
    ContinuousAt (fun t : NNReal => T.toContinuousLinearMap t x) 0 := by
  exact T.stronglyContinuousAtZero' x

/--
Generated note (NL): Optional semigroup-side assumptions extending primitive `C₀` data.
This keeps non-derived global continuity facts out of the core structure.
-/
structure C0SemigroupAssumptions (T : C0Semigroup (X := X)) : Prop where
  /--
Generated note (NL): Global strong continuity (`t ↦ T(t)x` continuous on `ℝ≥0`). -/
  stronglyContinuous :
    ∀ x : X, Continuous (fun t : NNReal => T.toContinuousLinearMap t x)

/--
Generated note (NL): Accessor for global strong continuity when a semigroup-side assumption package is provided. -/
theorem C0Semigroup.stronglyContinuous
    (T : C0Semigroup (X := X))
    (hT : C0SemigroupAssumptions (X := X) T)
    (x : X) :
    Continuous (fun t : NNReal => T.toContinuousLinearMap t x) := by
  exact hT.stronglyContinuous x

/--
Generated note (NL): Exponential growth bound `‖T(t)‖ ≤ M e^{ω t}` for all `t ≥ 0`. -/
def SemigroupGrowthBound (T : C0Semigroup (X := X)) (M ω : ℝ) : Prop :=
  ∀ t : NNReal, ‖T.toContinuousLinearMap t‖ ≤ M * Real.exp (ω * (t : ℝ))

/--
Generated note (NL): A strongly continuous contraction semigroup (`M = 1`, `ω = 0`). -/
def IsContractionSemigroup (T : C0Semigroup (X := X)) : Prop :=
  SemigroupGrowthBound (X := X) T 1 0

/--
Generated note (NL): Punctured right-neighborhood filter at `0` on `ℝ≥0`, used for difference-quotient limits.
This captures `h ↓ 0` with `h > 0`.
For readers of mathlib filter notation, this corresponds to the right-punctured
neighborhood view `[>] 0` (on `NNReal`, this is equivalent to puncturing at `0`).
-/
def puncturedNhdsZeroNNReal : Filter NNReal :=
  nhdsWithin (0 : NNReal) (Set.Ioi 0)

/--
Generated note (NL): Difference quotient map used to express generator limits.
At `h = 0`, this evaluates to `0` because `(0 : ℝ)⁻¹ = 0`.
-/
noncomputable def GeneratorDifferenceQuotient
    (T : C0Semigroup (X := X))
    (x : X)
    (h : NNReal) : X :=
  ((h : ℝ)⁻¹) • (T.toContinuousLinearMap h x - x)

@[simp] theorem generatorDifferenceQuotient_zero
    (T : C0Semigroup (X := X))
    (x : X) :
    GeneratorDifferenceQuotient (T := T) (x := x) 0 = 0 := by
  simp [GeneratorDifferenceQuotient]

/--
Generated note (NL): Interface for unresolved analytic objects in Hille--Yosida:
unbounded operators, resolvent-set semantics, and generation semantics.
-/
structure HilleYosidaModel where
  /--
Generated note (NL): Abstract type of (possibly unbounded) operators on `X`. -/
  Operator : Type*
  /--
Generated note (NL): Domain of an operator as a linear subspace of `X`. -/
  Domain : Operator → Submodule ℝ X
  /--
Generated note (NL): Linear action of the operator on its domain. -/
  toLinearMap : (A : Operator) → (Domain A →ₗ[ℝ] X)
  /--
Generated note (NL): Closedness predicate on operators. -/
  isClosed : Operator → Prop
  /--
Generated note (NL): Closedness is tied to graph closedness for the domain/action pair:
  this prevents `isClosed` from being a free unrelated predicate.
  -/
  isClosed_iff_graphClosed :
    ∀ (A : Operator),
      isClosed A ↔
        IsClosed
          ({p : X × X |
              ∃ x : Domain A, (x : X) = p.1 ∧ toLinearMap A x = p.2} : Set (X × X))
  /--
Generated note (NL): Resolvent-set membership predicate (`λ ∈ ρ(A)`). -/
  inResolventSet : Operator → ℝ → Prop
  /--
Generated note (NL): Explicit bounded resolvent witness for `λ ∈ ρ(A)`.
  Intended meaning: a bounded operator representing `(λ I - A)⁻¹`.
  -/
  resolventCLM :
    ∀ (A : Operator) (lam : ℝ), inResolventSet A lam → (X →L[ℝ] X)
  /--
Generated note (NL): Proof-irrelevance coherence for the resolvent witness:
  different proofs of `λ ∈ ρ(A)` yield the same bounded operator.
  -/
  resolventCLM_congr :
    ∀ {A : Operator} {lam : ℝ}
      (hres₁ hres₂ : inResolventSet A lam),
      resolventCLM A lam hres₁ = resolventCLM A lam hres₂
  /--
Generated note (NL): Resolvent maps every `y : X` into the domain of `A`. -/
  resolvent_mem_domain :
    ∀ {A : Operator} {lam : ℝ} (hres : inResolventSet A lam) (y : X),
      resolventCLM A lam hres y ∈ Domain A
  /--
Generated note (NL): Left-inverse law on domain:
  `R(λ, A) (λx - Ax) = x` for `x ∈ Domain A`.
  -/
  resolvent_left_inverse :
    ∀ {A : Operator} {lam : ℝ} (hres : inResolventSet A lam) (x : Domain A),
      resolventCLM A lam hres (lam • (x : X) - toLinearMap A x) = (x : X)
  /--
Generated note (NL): Right-inverse law on all `y : X`:
  `λ(R(λ,A)y) - A(R(λ,A)y) = y`.
  -/
  resolvent_right_inverse :
    ∀ {A : Operator} {lam : ℝ} (hres : inResolventSet A lam) (y : X),
      let x : Domain A := ⟨resolventCLM A lam hres y, resolvent_mem_domain hres y⟩
      lam • (x : X) - toLinearMap A x = y
  /--
Generated note (NL): Resolvent identity:
  `R(λ, A) - R(μ, A) = (μ - λ) R(λ, A) ∘ R(μ, A)`.
  -/
  resolvent_identity :
    ∀ {A : Operator} {lam mu : ℝ}
      (hres_lam : inResolventSet A lam)
      (hres_mu : inResolventSet A mu),
      resolventCLM A lam hres_lam - resolventCLM A mu hres_mu =
        (mu - lam) •
          ((resolventCLM A lam hres_lam).comp (resolventCLM A mu hres_mu))
  /--
Generated note (NL): Generation relation: operator `A` generates semigroup `T`. -/
  generates : Operator → C0Semigroup (X := X) → Prop
  /--
Generated note (NL): Generator-limit law:
  if `A` generates `T`, then for `x ∈ Domain A` the difference quotient tends to `Ax`.
  -/
  generates_tendsto_generator :
    ∀ {A : Operator} {T : C0Semigroup (X := X)}
      (_hgen : generates A T) (x : Domain A),
      Filter.Tendsto
        (fun h : NNReal => GeneratorDifferenceQuotient (T := T) (x := (x : X)) h)
        (puncturedNhdsZeroNNReal)
        (nhds (toLinearMap A x))
  /--
Generated note (NL): Converse-style generator characterization:
  if the difference quotient converges to `l`, then `x` is in the domain of `A`
  and the generator value equals this limit.
  -/
  generates_domain_eq_limit_of_tendsto :
    ∀ {A : Operator} {T : C0Semigroup (X := X)}
      (_hgen : generates A T) {x l : X},
      Filter.Tendsto
        (fun h : NNReal => GeneratorDifferenceQuotient (T := T) (x := x) h)
        (puncturedNhdsZeroNNReal)
        (nhds l) →
      ∃ hx : x ∈ Domain A, toLinearMap A ⟨x, hx⟩ = l

variable (Mdl : HilleYosidaModel (X := X))

/--
Generated note (NL): The operator `A` has dense domain in `X`. -/
def HasDenseDomain (A : Mdl.Operator) : Prop :=
  Dense ((Mdl.Domain A : Set X))

/--
Generated note (NL): Concrete resolvent power norm bound associated with an explicit resolvent witness.
This exposes the normed-operator content instead of keeping bounds fully opaque.
-/
def ResolventPowerNormBound
    (A : Mdl.Operator)
    (lam : ℝ)
    (hres : Mdl.inResolventSet A lam)
    (n : ℕ)
    (M ω : ℝ) : Prop :=
  ‖(Mdl.resolventCLM A lam hres) ^ n‖ ≤ M / (lam - ω) ^ n

/--
Generated note (NL): Resolvent power norm bounds do not depend on the specific proof witness
of resolvent-set membership.
-/
theorem resolventPowerNormBound_congr
    {A : Mdl.Operator}
    {lam : ℝ}
    {hres₁ hres₂ : Mdl.inResolventSet A lam}
    {n : ℕ}
    {M ω : ℝ} :
    ResolventPowerNormBound (Mdl := Mdl) A lam hres₁ n M ω ↔
      ResolventPowerNormBound (Mdl := Mdl) A lam hres₂ n M ω := by
  constructor
  · intro bound₁
    simpa [ResolventPowerNormBound, Mdl.resolventCLM_congr hres₁ hres₂] using bound₁
  · intro bound₂
    simpa [ResolventPowerNormBound, Mdl.resolventCLM_congr hres₁ hres₂] using bound₂

/--
Generated note (NL): Resolvent side-conditions in the general Hille--Yosida statement. -/
def ResolventConditions (A : Mdl.Operator) (M ω : ℝ) : Prop :=
  ∀ lam : ℝ, ω < lam →
    ∃ hres : Mdl.inResolventSet A lam,
      ∀ n : ℕ, ResolventPowerNormBound (Mdl := Mdl) A lam hres (n + 1) M ω

/--
Generated note (NL): Bundled witness that `A` generates a semigroup together with the chosen
semigroup-side regularity assumptions.
-/
structure GeneratedSemigroup (A : Mdl.Operator) where
  /--
Generated note (NL): The generated semigroup. -/
  T : C0Semigroup (X := X)
  /--
Generated note (NL): Semigroup-side regularity witness. -/
  hT : C0SemigroupAssumptions (X := X) T
  /--
Generated note (NL): Generation relation witness. -/
  hgen : Mdl.generates A T

/--
Generated note (NL): Operational accessor exposing both bundled witnesses:
semigroup regularity and generation.
-/
theorem GeneratedSemigroup.regularityAndGeneration
    {A : Mdl.Operator}
    (S : GeneratedSemigroup (Mdl := Mdl) A) :
    C0SemigroupAssumptions (X := X) S.T ∧ Mdl.generates A S.T := by
  exact ⟨S.hT, S.hgen⟩

/--
Generated note (NL): Global strong continuity on a bundled generated semigroup. -/
theorem GeneratedSemigroup.stronglyContinuous
    {A : Mdl.Operator}
    (S : GeneratedSemigroup (Mdl := Mdl) A)
    (x : X) :
    Continuous (fun t : NNReal => S.T.toContinuousLinearMap t x) := by
  exact S.hT.stronglyContinuous x

/--
Generated note (NL): Generation plus exponential bound (`M`, `ω`) in the general case. -/
def GeneratesSemigroupWithBound (A : Mdl.Operator) (M ω : ℝ) : Prop :=
  ∃ S : GeneratedSemigroup (Mdl := Mdl) A,
    SemigroupGrowthBound (X := X) S.T M ω

/--
Generated note (NL): Resolvent side-condition for the contraction-semigroup specialization. -/
def ResolventContractionCondition (A : Mdl.Operator) : Prop :=
  ∀ lam : ℝ, 0 < lam →
    ∃ hres : Mdl.inResolventSet A lam,
      ResolventPowerNormBound (Mdl := Mdl) A lam hres 1 1 0

/--
Generated note (NL): General resolvent conditions specialize to the `n = 1` contraction resolvent condition
at parameters `(M, ω) = (1, 0)`.
-/
theorem resolventContractionCondition_of_resolventConditions_one_zero
    (A : Mdl.Operator)
    (hRes : ResolventConditions (Mdl := Mdl) A 1 0) :
    ResolventContractionCondition (Mdl := Mdl) A := by
  intro lam hlam
  rcases hRes lam hlam with ⟨hres, hpow⟩
  refine ⟨hres, ?_⟩
  simpa using hpow 0

/--
Generated note (NL): Generation by a strongly continuous contraction semigroup. -/
def GeneratesContractionSemigroup (A : Mdl.Operator) : Prop :=
  ∃ S : GeneratedSemigroup (Mdl := Mdl) A,
    IsContractionSemigroup (X := X) S.T

/--
Generated note (NL): At parameters `(M, ω) = (1, 0)`, semigroup generation with bound is equivalent
to generation by a contraction semigroup.
-/
theorem generatesSemigroupWithBound_one_zero_iff_generatesContractionSemigroup
    (A : Mdl.Operator) :
    GeneratesSemigroupWithBound (Mdl := Mdl) A 1 0 ↔
      GeneratesContractionSemigroup (Mdl := Mdl) A := by
  constructor
  · intro h
    rcases h with ⟨S, hbound⟩
    exact ⟨S, hbound⟩
  · intro h
    rcases h with ⟨S, hcontraction⟩
    exact ⟨S, hcontraction⟩

/--
Generated note (NL): Operational generator characterization under a fixed generation witness:
for a vector `x`, existence of the punctured limit is equivalent to membership in
the domain together with identification of the limit as `Ax`.
-/
theorem generates_tendsto_iff_domain_and_value
    {A : Mdl.Operator}
    {T : C0Semigroup (X := X)}
    (hgen : Mdl.generates A T)
    {x l : X} :
    Filter.Tendsto
      (fun h : NNReal => GeneratorDifferenceQuotient (T := T) (x := x) h)
      puncturedNhdsZeroNNReal
      (nhds l) ↔
      ∃ hx : x ∈ Mdl.Domain A, Mdl.toLinearMap A ⟨x, hx⟩ = l := by
  constructor
  · intro ht
    exact Mdl.generates_domain_eq_limit_of_tendsto hgen ht
  · intro hxl
    rcases hxl with ⟨hx, hl⟩
    rw [← hl]
    simpa using Mdl.generates_tendsto_generator hgen ⟨x, hx⟩

/--
Generated note (NL): Assumption package exposing both Hille--Yosida forms over the interface `Mdl`.
This keeps theorem-level equivalences explicit while unresolved analytic components stay abstract.
-/
structure HilleYosidaAssumptions [CompleteSpace X] : Prop where
  /--
Generated note (NL): General `M`-`ω` Hille--Yosida equivalence. -/
  general_iff :
    ∀ (A : Mdl.Operator) (M ω : ℝ), 0 < M →
      (GeneratesSemigroupWithBound (Mdl := Mdl) A M ω ↔
        (Mdl.isClosed A ∧
          HasDenseDomain (Mdl := Mdl) A ∧
          ResolventConditions (Mdl := Mdl) A M ω))
  /--
Generated note (NL): Bridge assumption for contraction form:
  in this interface layer, we assume the standard implication that the `n = 1`
  resolvent bound implies the all-powers resolvent conditions at `(M, ω) = (1, 0)`.
  -/
  contraction_resolvent_upgrade :
    ∀ (A : Mdl.Operator),
      ResolventContractionCondition (Mdl := Mdl) A →
        ResolventConditions (Mdl := Mdl) A 1 0

/--
Generated note (NL): Hille--Yosida theorem (general `M`-`ω` form) under explicit assumptions. -/
theorem hilleYosida_general
    [CompleteSpace X]
    (hHY : HilleYosidaAssumptions (Mdl := Mdl))
    (A : Mdl.Operator)
    (M ω : ℝ)
    (hM : 0 < M) :
    GeneratesSemigroupWithBound (Mdl := Mdl) A M ω ↔
      (Mdl.isClosed A ∧
        HasDenseDomain (Mdl := Mdl) A ∧
        ResolventConditions (Mdl := Mdl) A M ω) := by
  exact hHY.general_iff (A := A) (M := M) (ω := ω) hM

/--
Generated note (NL): Hille--Yosida theorem for strongly continuous contraction semigroups. -/
theorem hilleYosida_contraction
    [CompleteSpace X]
    (hHY : HilleYosidaAssumptions (Mdl := Mdl))
    (A : Mdl.Operator) :
    GeneratesContractionSemigroup (Mdl := Mdl) A ↔
      (Mdl.isClosed A ∧
        HasDenseDomain (Mdl := Mdl) A ∧
        ResolventContractionCondition (Mdl := Mdl) A) := by
  constructor
  · intro hGenContraction
    have hGeneral :
        GeneratesSemigroupWithBound (Mdl := Mdl) A 1 0 := by
      exact
        (generatesSemigroupWithBound_one_zero_iff_generatesContractionSemigroup
          (Mdl := Mdl) A).2 hGenContraction
    have h := (hHY.general_iff A 1 0 (by norm_num)).1 hGeneral
    refine ⟨h.1, h.2.1, ?_⟩
    exact
      resolventContractionCondition_of_resolventConditions_one_zero
        (Mdl := Mdl) A h.2.2
  · intro hContraction
    have hResGeneral :
        ResolventConditions (Mdl := Mdl) A 1 0 := by
      exact hHY.contraction_resolvent_upgrade A hContraction.2.2
    have hGeneral :
        GeneratesSemigroupWithBound (Mdl := Mdl) A 1 0 := by
      exact
        (hHY.general_iff A 1 0 (by norm_num)).2
          ⟨hContraction.1, hContraction.2.1, hResGeneral⟩
    exact
      (generatesSemigroupWithBound_one_zero_iff_generatesContractionSemigroup
        (Mdl := Mdl) A).1 hGeneral

end AutoformalizedHilleYosida
end Mathformer
