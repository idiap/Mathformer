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

import Mathlib.Analysis.Complex.Trigonometric
import Mathlib.MeasureTheory.Measure.ProbabilityMeasure
import Mathlib.Topology.Algebra.InfiniteSum.Basic

open scoped Topology
open Filter MeasureTheory

/--
Generated note (NL): Small arithmetic smoke theorem produced by the
autoformalization examples.
Generated equivalent (LaTeX): `a+b=b+a`.
-/
theorem autoformalized_add_comm (a b : Nat) : a + b = b + a := by
  simpa using Nat.add_comm a b

/--
Generated note (NL): Euler's complex exponential identity in the example suite.
Generated equivalent (LaTeX): `\exp(i\theta)=\cos(\theta)+i\sin(\theta)`.
-/
theorem autoformalized_euler_formula (θ : ℝ) :
    Complex.exp ((θ : ℂ) * Complex.I) = Real.cos θ + Real.sin θ * Complex.I := by
  simpa using (Complex.exp_mul_I (x := (θ : ℂ)))

/--
Generated note (NL): Linear projection of a vector in `\mathbb{R}^k` along a
coefficient vector.
Generated equivalent (LaTeX): `x \mapsto \sum_i t_i x_i`.
-/
noncomputable def linearProjection {k : ℕ} (t : Fin k → ℝ) : (Fin k → ℝ) → ℝ :=
  fun x => ∑ i, t i * x i

/--
Generated note (NL): The finite-dimensional linear projection map is continuous.
Generated equivalent (LaTeX): `x \mapsto \sum_i t_i x_i` is continuous.
-/
lemma continuous_linearProjection {k : ℕ} (t : Fin k → ℝ) :
    Continuous (linearProjection (k := k) t) := by
  classical
  simpa [linearProjection] using
    (continuous_finset_sum Finset.univ
      (fun i _ => (continuous_const.mul (continuous_apply i))))

/--
Generated note (NL): Continuity gives almost-everywhere measurability for the
linear projection under any measure.
Generated equivalent (LaTeX): continuous `\pi_t` implies `\pi_t` is
`\mu`-a.e. measurable.
-/
lemma aemeasurable_linearProjection {k : ℕ} (μ : Measure (Fin k → ℝ)) (t : Fin k → ℝ) :
    AEMeasurable (linearProjection (k := k) t) μ := by
  exact (continuous_linearProjection (k := k) t).aemeasurable

/--
Generated note (NL): Source-level Cramer--Wold equivalence packaged as an
explicit assumption until the full probability-theoretic proof is developed
locally.
Generated equivalent (LaTeX): `X_n \Rightarrow X \iff
\forall t,\langle t,X_n\rangle \Rightarrow \langle t,X\rangle`.
-/
def CramerWoldProjectionCriterion
    {k : ℕ}
    {Ω : Type*}
    [MeasurableSpace Ω]
    (ℙ : ProbabilityMeasure Ω)
    (Xn : ℕ → Ω → (Fin k → ℝ))
    (X : Ω → (Fin k → ℝ))
    (hXn : ∀ n, AEMeasurable (Xn n) ℙ)
    (hX : AEMeasurable X ℙ) : Prop :=
  Tendsto (fun n => ProbabilityMeasure.map ℙ (hXn n)) atTop
      (𝓝 (ProbabilityMeasure.map ℙ hX)) ↔
    ∀ t : Fin k → ℝ,
      Tendsto
        (fun n =>
          ProbabilityMeasure.map
            (ProbabilityMeasure.map ℙ (hXn n))
            (aemeasurable_linearProjection
              (μ := (ProbabilityMeasure.map ℙ (hXn n) : Measure (Fin k → ℝ))) t))
        atTop
        (𝓝 (
          ProbabilityMeasure.map
            (ProbabilityMeasure.map ℙ hX)
            (aemeasurable_linearProjection
              (μ := (ProbabilityMeasure.map ℙ hX : Measure (Fin k → ℝ))) t)))

/--
Original source (NL): Cramer--Wold states that convergence in distribution of
random vectors in `\mathbb{R}^k` is equivalent to convergence of all
one-dimensional linear projections.
Original source (LaTeX): `X_n \Rightarrow X` iff
`\langle t,X_n\rangle \Rightarrow \langle t,X\rangle` for every
`t \in \mathbb{R}^k`.
-/
theorem autoformalized_cramer_wold
    {k : ℕ}
    {Ω : Type*}
    [MeasurableSpace Ω]
    (ℙ : ProbabilityMeasure Ω)
    (Xn : ℕ → Ω → (Fin k → ℝ))
    (X : Ω → (Fin k → ℝ))
    (hXn : ∀ n, AEMeasurable (Xn n) ℙ)
    (hX : AEMeasurable X ℙ)
    (hCW : CramerWoldProjectionCriterion ℙ Xn X hXn hX) :
    Tendsto (fun n => ProbabilityMeasure.map ℙ (hXn n)) atTop (𝓝 (ProbabilityMeasure.map ℙ hX)) ↔
      ∀ t : Fin k → ℝ,
        Tendsto
          (fun n =>
            ProbabilityMeasure.map
              (ProbabilityMeasure.map ℙ (hXn n))
              (aemeasurable_linearProjection
                (μ := (ProbabilityMeasure.map ℙ (hXn n) : Measure (Fin k → ℝ))) t))
          atTop
          (𝓝 (
            ProbabilityMeasure.map
              (ProbabilityMeasure.map ℙ hX)
              (aemeasurable_linearProjection
                (μ := (ProbabilityMeasure.map ℙ hX : Measure (Fin k → ℝ))) t))) := by
  exact hCW

/--
Generated note (NL): Source-level nonnegative-coefficient Cramer--Wold
criterion packaged as an explicit assumption until the full proof is developed
locally.
Generated equivalent (LaTeX): for nonnegative random vectors, convergence of
all `t\ge 0` linear projections implies distributional convergence.
-/
def CramerWoldNonnegativeProjectionCriterion
    {k : ℕ}
    {Ω : Type*}
    [MeasurableSpace Ω]
    (ℙ : ProbabilityMeasure Ω)
    (Xn : ℕ → Ω → (Fin k → ℝ))
    (X : Ω → (Fin k → ℝ))
    (hXn : ∀ n, AEMeasurable (Xn n) ℙ)
    (hX : AEMeasurable X ℙ)
    (_hXn_nonneg : ∀ n, ∀ᵐ ω ∂(ℙ : Measure Ω), ∀ i, 0 ≤ Xn n ω i)
    (_hX_nonneg : ∀ᵐ ω ∂(ℙ : Measure Ω), ∀ i, 0 ≤ X ω i) : Prop :=
  (∀ t : Fin k → ℝ,
    (∀ i, 0 ≤ t i) →
    Tendsto
      (fun n =>
        ProbabilityMeasure.map
          (ProbabilityMeasure.map ℙ (hXn n))
          (aemeasurable_linearProjection
            (μ := (ProbabilityMeasure.map ℙ (hXn n) : Measure (Fin k → ℝ))) t))
      atTop
      (𝓝 (
        ProbabilityMeasure.map
          (ProbabilityMeasure.map ℙ hX)
          (aemeasurable_linearProjection
            (μ := (ProbabilityMeasure.map ℙ hX : Measure (Fin k → ℝ))) t)))) →
  Tendsto (fun n => ProbabilityMeasure.map ℙ (hXn n)) atTop (𝓝 (ProbabilityMeasure.map ℙ hX))

/--
Original source (NL): For random vectors supported in
`\mathbb{R}_{\ge 0}^k`, it suffices to check nonnegative coefficient vectors
`t`.
Original source (LaTeX): if `X_n,X \in \mathbb{R}_{\ge0}^k`, convergence of
`\langle t,X_n\rangle` for all `t \ge 0` implies `X_n \Rightarrow X`.
-/
theorem autoformalized_cramer_wold_nonneg_coeffs
    {k : ℕ}
    {Ω : Type*}
    [MeasurableSpace Ω]
    (ℙ : ProbabilityMeasure Ω)
    (Xn : ℕ → Ω → (Fin k → ℝ))
    (X : Ω → (Fin k → ℝ))
    (hXn : ∀ n, AEMeasurable (Xn n) ℙ)
    (hX : AEMeasurable X ℙ)
    (hXn_nonneg : ∀ n, ∀ᵐ ω ∂(ℙ : Measure Ω), ∀ i, 0 ≤ Xn n ω i)
    (hX_nonneg : ∀ᵐ ω ∂(ℙ : Measure Ω), ∀ i, 0 ≤ X ω i)
    (hCW_nonneg :
      CramerWoldNonnegativeProjectionCriterion ℙ Xn X hXn hX hXn_nonneg hX_nonneg) :
    (∀ t : Fin k → ℝ,
      (∀ i, 0 ≤ t i) →
      Tendsto
        (fun n =>
          ProbabilityMeasure.map
            (ProbabilityMeasure.map ℙ (hXn n))
            (aemeasurable_linearProjection
              (μ := (ProbabilityMeasure.map ℙ (hXn n) : Measure (Fin k → ℝ))) t))
        atTop
        (𝓝 (
          ProbabilityMeasure.map
            (ProbabilityMeasure.map ℙ hX)
            (aemeasurable_linearProjection
              (μ := (ProbabilityMeasure.map ℙ hX : Measure (Fin k → ℝ))) t)))) →
    Tendsto (fun n => ProbabilityMeasure.map ℙ (hXn n)) atTop (𝓝 (ProbabilityMeasure.map ℙ hX)) := by
  exact hCW_nonneg
