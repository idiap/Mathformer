<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Make the framework understandable without requiring readers to inspect implementation details first.

Intent:
  Explain architecture, installation, principles, tutorials, licensing, and generated library outputs.

Function:
  Provides human-facing documentation that should stay aligned with tested behavior and code paths.

Maintenance Notes:
  Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.
-->

# `Mathformer.AutoformalizedExamples`

[Back to index](../../INDEX.md)

## Metadata

- Source: [backends/lean/Mathformer/AutoformalizedExamples.lean](../../../../../backends/lean/Mathformer/AutoformalizedExamples.lean)
- Status: `candidate`
- SHA-256: `6499147a90efac86adfcc1840b1826d6319f0687dad6ab1deb721dcb7d0d0380`
- Declarations: `9`

## Imports

```lean
import Mathlib.Analysis.Complex.Trigonometric
import Mathlib.MeasureTheory.Measure.ProbabilityMeasure
import Mathlib.Topology.Algebra.InfiniteSum.Basic
```

## Declarations

- [`autoformalized_add_comm`](#autoformalized-add-comm) (theorem, line 13)
- [`autoformalized_euler_formula`](#autoformalized-euler-formula) (theorem, line 20)
- [`linearProjection`](#linearprojection) (def, line 29)
- [`continuous_linearProjection`](#continuous-linearprojection) (lemma, line 36)
- [`aemeasurable_linearProjection`](#aemeasurable-linearprojection) (lemma, line 49)
- [`CramerWoldProjectionCriterion`](#cramerwoldprojectioncriterion) (def, line 60)
- [`autoformalized_cramer_wold`](#autoformalized-cramer-wold) (theorem, line 93)
- [`CramerWoldNonnegativeProjectionCriterion`](#cramerwoldnonnegativeprojectioncriterion) (def, line 126)
- [`autoformalized_cramer_wold_nonneg_coeffs`](#autoformalized-cramer-wold-nonneg-coeffs) (theorem, line 160)

## `autoformalized_add_comm`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedExamples.lean:13](../../../../../backends/lean/Mathformer/AutoformalizedExamples.lean#L13)

**Generated Notes**

Small arithmetic smoke theorem produced by the autoformalization examples.

**Generated LaTeX**

```latex
`a+b=b+a`.
```

$$
a+b=b+a
$$

**Lean**

```lean
theorem autoformalized_add_comm (a b : Nat) : a + b = b + a := by
  simpa using Nat.add_comm a b
```

## `autoformalized_euler_formula`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedExamples.lean:20](../../../../../backends/lean/Mathformer/AutoformalizedExamples.lean#L20)

**Generated Notes**

Euler's complex exponential identity in the example suite.

**Generated LaTeX**

```latex
`\exp(i\theta)=\cos(\theta)+i\sin(\theta)`.
```

$$
\exp(i\theta)=\cos(\theta)+i\sin(\theta)
$$

**Lean**

```lean
theorem autoformalized_euler_formula (θ : ℝ) :
    Complex.exp ((θ : ℂ) * Complex.I) = Real.cos θ + Real.sin θ * Complex.I := by
  simpa using (Complex.exp_mul_I (x := (θ : ℂ)))
```

## `linearProjection`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedExamples.lean:29](../../../../../backends/lean/Mathformer/AutoformalizedExamples.lean#L29)

**Generated Notes**

Linear projection of a vector in `\mathbb{R}^k` along a coefficient vector.

**Generated LaTeX**

```latex
`x \mapsto \sum_i t_i x_i`.
```

$$
x \mapsto \sum_i t_i x_i
$$

**Lean**

```lean
noncomputable def linearProjection {k : ℕ} (t : Fin k → ℝ) : (Fin k → ℝ) → ℝ :=
  fun x => ∑ i, t i * x i
```

## `continuous_linearProjection`

- Kind: `lemma`
- Source line: [backends/lean/Mathformer/AutoformalizedExamples.lean:36](../../../../../backends/lean/Mathformer/AutoformalizedExamples.lean#L36)

**Generated Notes**

The finite-dimensional linear projection map is continuous.

**Generated LaTeX**

```latex
`x \mapsto \sum_i t_i x_i` is continuous.
```

$$
x \mapsto \sum_i t_i x_i
$$

**Lean**

```lean
lemma continuous_linearProjection {k : ℕ} (t : Fin k → ℝ) :
    Continuous (linearProjection (k := k) t) := by
  classical
  simpa [linearProjection] using
    (continuous_finset_sum Finset.univ
      (fun i _ => (continuous_const.mul (continuous_apply i))))
```

## `aemeasurable_linearProjection`

- Kind: `lemma`
- Source line: [backends/lean/Mathformer/AutoformalizedExamples.lean:49](../../../../../backends/lean/Mathformer/AutoformalizedExamples.lean#L49)

**Generated Notes**

Continuity gives almost-everywhere measurability for the linear projection under any measure.

**Generated LaTeX**

```latex
continuous `\pi_t` implies `\pi_t` is
`\mu`-a.e. measurable.
```

$$
\pi_t
$$

$$
\pi_t
$$

$$
\mu
$$

**Lean**

```lean
lemma aemeasurable_linearProjection {k : ℕ} (μ : Measure (Fin k → ℝ)) (t : Fin k → ℝ) :
    AEMeasurable (linearProjection (k := k) t) μ := by
  exact (continuous_linearProjection (k := k) t).aemeasurable
```

## `CramerWoldProjectionCriterion`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedExamples.lean:60](../../../../../backends/lean/Mathformer/AutoformalizedExamples.lean#L60)

**Generated Notes**

Source-level Cramer--Wold equivalence packaged as an explicit assumption until the full probability-theoretic proof is developed locally.

**Generated LaTeX**

```latex
`X_n \Rightarrow X \iff
\forall t,\langle t,X_n\rangle \Rightarrow \langle t,X\rangle`.
```

$$
X_n \Rightarrow X \iff \forall t,\langle t,X_n\rangle \Rightarrow \langle t,X\rangle
$$

**Lean**

```lean
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
```

## `autoformalized_cramer_wold`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedExamples.lean:93](../../../../../backends/lean/Mathformer/AutoformalizedExamples.lean#L93)

**Original Source**

Cramer--Wold states that convergence in distribution of random vectors in `\mathbb{R}^k` is equivalent to convergence of all one-dimensional linear projections.

**Original LaTeX**

```latex
`X_n \Rightarrow X` iff
`\langle t,X_n\rangle \Rightarrow \langle t,X\rangle` for every
`t \in \mathbb{R}^k`.
```

$$
X_n \Rightarrow X
$$

$$
\langle t,X_n\rangle \Rightarrow \langle t,X\rangle
$$

$$
t \in \mathbb{R}^k
$$

**Lean**

```lean
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
```

## `CramerWoldNonnegativeProjectionCriterion`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedExamples.lean:126](../../../../../backends/lean/Mathformer/AutoformalizedExamples.lean#L126)

**Generated Notes**

Source-level nonnegative-coefficient Cramer--Wold criterion packaged as an explicit assumption until the full proof is developed locally.

**Generated LaTeX**

```latex
for nonnegative random vectors, convergence of
all `t\ge 0` linear projections implies distributional convergence.
```

$$
t\ge 0
$$

**Lean**

```lean
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
```

## `autoformalized_cramer_wold_nonneg_coeffs`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedExamples.lean:160](../../../../../backends/lean/Mathformer/AutoformalizedExamples.lean#L160)

**Original Source**

For random vectors supported in `\mathbb{R}_{\ge 0}^k`, it suffices to check nonnegative coefficient vectors `t`.

**Original LaTeX**

```latex
if `X_n,X \in \mathbb{R}_{\ge0}^k`, convergence of
`\langle t,X_n\rangle` for all `t \ge 0` implies `X_n \Rightarrow X`.
```

$$
X_n,X \in \mathbb{R}_{\ge0}^k
$$

$$
\langle t,X_n\rangle
$$

$$
t \ge 0
$$

**Lean**

```lean
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
```
