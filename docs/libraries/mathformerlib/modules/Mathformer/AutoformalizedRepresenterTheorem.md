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

# `Mathformer.AutoformalizedRepresenterTheorem`

[Back to index](../../INDEX.md)

## Metadata

- Source: [backends/lean/Mathformer/AutoformalizedRepresenterTheorem.lean](../../../../../backends/lean/Mathformer/AutoformalizedRepresenterTheorem.lean)
- Status: `candidate`
- SHA-256: `dbe4955addb3f079049b4be5769b6f4a21ec144e4d003cfaedc986cad85472e4`
- Declarations: `12`

## Imports

```lean
import Mathlib.Algebra.BigOperators.Group.Finset.Basic
import Mathlib.Data.Fintype.Basic
import Mathlib.Data.Real.Basic
import Mathlib.Order.Monotone.Basic
```

## Module Source Notes

**Original Source**

A representer theorem states that a minimizer of a regularized empirical risk functional over a reproducing kernel Hilbert space can be represented as a finite linear combination of kernel products evaluated at the input points in the training set.

**Original LaTeX**

```latex
if `k : \mathcal X \times \mathcal X \to \mathbb R`
is a positive-definite kernel with RKHS `H_k`, then a minimizer
`f^*` of
`E((x_i,y_i,f(x_i))_{i=1}^n) + g(\|f\|)`
has the representation
`f^*(\cdot)=\sum_{i=1}^n \alpha_i k(\cdot,x_i)`.

Generated note: this module formalizes a finite-risk, real-valued version of
the representer theorem. The RKHS projection argument is captured by reduction
hypotheses saying that functions outside the finite kernel span can be replaced
by a finite kernel combination with the same training values and a smaller, or
no larger, regularization size. Under strict monotonicity, any minimizer must
already lie in the finite kernel span.
```

$$
k : \mathcal X \times \mathcal X \to \mathbb R
$$

$$
H_k
$$

$$
f^*
$$

## Declarations

- [`Mathformer.AutoformalizedRepresenterTheorem.KernelSection`](#mathformer-autoformalizedrepresentertheorem-kernelsection) (def, line 50)
- [`Mathformer.AutoformalizedRepresenterTheorem.FiniteKernelCombination`](#mathformer-autoformalizedrepresentertheorem-finitekernelcombination) (def, line 58)
- [`Mathformer.AutoformalizedRepresenterTheorem.finiteKernelCombination_apply`](#mathformer-autoformalizedrepresentertheorem-finitekernelcombination-apply) (theorem, line 68)
- [`Mathformer.AutoformalizedRepresenterTheorem.TrainingData`](#mathformer-autoformalizedrepresentertheorem-trainingdata) (def, line 80)
- [`Mathformer.AutoformalizedRepresenterTheorem.SameTrainingValues`](#mathformer-autoformalizedrepresentertheorem-sametrainingvalues) (def, line 90)
- [`Mathformer.AutoformalizedRepresenterTheorem.RegularizedEmpiricalRisk`](#mathformer-autoformalizedrepresentertheorem-regularizedempiricalrisk) (def, line 102)
- [`Mathformer.AutoformalizedRepresenterTheorem.IsMinimizer`](#mathformer-autoformalizedrepresentertheorem-isminimizer) (def, line 117)
- [`Mathformer.AutoformalizedRepresenterTheorem.WeakRepresenterReduction`](#mathformer-autoformalizedrepresentertheorem-weakrepresenterreduction) (def, line 128)
- [`Mathformer.AutoformalizedRepresenterTheorem.StrictRepresenterReduction`](#mathformer-autoformalizedrepresentertheorem-strictrepresenterreduction) (def, line 146)
- [`Mathformer.AutoformalizedRepresenterTheorem.trainingData_eq_of_sameTrainingValues`](#mathformer-autoformalizedrepresentertheorem-trainingdata-eq-of-sametrainingvalues) (theorem, line 163)
- [`Mathformer.AutoformalizedRepresenterTheorem.exists_representer_minimizer_of_minimizer`](#mathformer-autoformalizedrepresentertheorem-exists-representer-minimizer-of-minimizer) (theorem, line 178)
- [`Mathformer.AutoformalizedRepresenterTheorem.representer_theorem_real_valued`](#mathformer-autoformalizedrepresentertheorem-representer-theorem-real-valued) (theorem, line 218)

<a id="mathformer-autoformalizedrepresentertheorem-kernelsection"></a>

## `Mathformer.AutoformalizedRepresenterTheorem.KernelSection`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedRepresenterTheorem.lean:50](../../../../../backends/lean/Mathformer/AutoformalizedRepresenterTheorem.lean#L50)

**Original Source**

The kernel section at a training input `x_i` is the function `x ↦ k(x,x_i)`.

**Original LaTeX**

```latex
`k(\cdot,x_i)`.
```

$$
k(\cdot,x_i)
$$

**Lean**

```lean
def KernelSection (k : X → X → ℝ) (xᵢ : X) : X → ℝ :=
  fun x => k x xᵢ
```

<a id="mathformer-autoformalizedrepresentertheorem-finitekernelcombination"></a>

## `Mathformer.AutoformalizedRepresenterTheorem.FiniteKernelCombination`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedRepresenterTheorem.lean:58](../../../../../backends/lean/Mathformer/AutoformalizedRepresenterTheorem.lean#L58)

**Original Source**

A representer-form function is a finite linear combination of the kernel sections at the training inputs.

**Original LaTeX**

```latex
`f(\cdot)=\sum_{i=1}^n \alpha_i k(\cdot,x_i)`.
```

$$
f(\cdot)=\sum_{i=1}^n \alpha_i k(\cdot,x_i)
$$

**Lean**

```lean
def FiniteKernelCombination {n : ℕ}
    (k : X → X → ℝ) (sample : Fin n → X) (f : X → ℝ) : Prop :=
  ∃ α : Fin n → ℝ, ∀ x : X, f x = ∑ i : Fin n, α i * k x (sample i)
```

<a id="mathformer-autoformalizedrepresentertheorem-finitekernelcombination-apply"></a>

## `Mathformer.AutoformalizedRepresenterTheorem.finiteKernelCombination_apply`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedRepresenterTheorem.lean:68](../../../../../backends/lean/Mathformer/AutoformalizedRepresenterTheorem.lean#L68)

**Generated Notes**

Unfolding the finite kernel combination property gives the coefficient vector and the pointwise kernel expansion.

**Generated LaTeX**

```latex
from
`f=\sum_i \alpha_i k(\cdot,x_i)` we obtain the same equality at every `x`.
```

$$
f=\sum_i \alpha_i k(\cdot,x_i)
$$

$$
x
$$

**Lean**

```lean
theorem finiteKernelCombination_apply {n : ℕ}
    {k : X → X → ℝ} {sample : Fin n → X} {f : X → ℝ}
    (hf : FiniteKernelCombination k sample f) :
    ∃ α : Fin n → ℝ, ∀ x : X, f x = ∑ i : Fin n, α i * k x (sample i) := by
  exact hf
```

<a id="mathformer-autoformalizedrepresentertheorem-trainingdata"></a>

## `Mathformer.AutoformalizedRepresenterTheorem.TrainingData`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedRepresenterTheorem.lean:80](../../../../../backends/lean/Mathformer/AutoformalizedRepresenterTheorem.lean#L80)

**Original Source**

The empirical loss only sees the values of a candidate function at the training inputs.

**Original LaTeX**

```latex
the loss term has inputs
`(x_i,y_i,f(x_i))_{i=1}^n`.
```

$$
(x_i,y_i,f(x_i))_{i=1}^n
$$

**Lean**

```lean
def TrainingData {n : ℕ}
    (sample : Fin n → X) (labels : Fin n → ℝ) (f : X → ℝ) :
    Fin n → X × ℝ × ℝ :=
  fun i => (sample i, labels i, f (sample i))
```

<a id="mathformer-autoformalizedrepresentertheorem-sametrainingvalues"></a>

## `Mathformer.AutoformalizedRepresenterTheorem.SameTrainingValues`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedRepresenterTheorem.lean:90](../../../../../backends/lean/Mathformer/AutoformalizedRepresenterTheorem.lean#L90)

**Original Source**

Two candidate functions agree on the training sample when they give the same prediction at every training input.

**Original LaTeX**

```latex
`\forall i,\ h(x_i)=f(x_i)`.
```

$$
\forall i,\ h(x_i)=f(x_i)
$$

**Lean**

```lean
def SameTrainingValues {n : ℕ}
    (sample : Fin n → X) (f h : X → ℝ) : Prop :=
  ∀ i : Fin n, h (sample i) = f (sample i)
```

<a id="mathformer-autoformalizedrepresentertheorem-regularizedempiricalrisk"></a>

## `Mathformer.AutoformalizedRepresenterTheorem.RegularizedEmpiricalRisk`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedRepresenterTheorem.lean:102](../../../../../backends/lean/Mathformer/AutoformalizedRepresenterTheorem.lean#L102)

**Original Source**

The regularized empirical risk is the empirical error plus a monotone function of the Hilbert-space norm.

**Original LaTeX**

```latex
`E((x_i,y_i,f(x_i))_{i=1}^n)+g(\|f\|)`.
Generated note: `normLike` is the regularization size supplied by the RKHS
model, usually the Hilbert norm.
```

$$
E((x_i,y_i,f(x_i))_{i=1}^n)+g(\|f\|)
$$

$$
normLike
$$

**Lean**

```lean
def RegularizedEmpiricalRisk {n : ℕ}
    (E : (Fin n → X × ℝ × ℝ) → ℝ)
    (g : ℝ → ℝ)
    (normLike : (X → ℝ) → ℝ)
    (sample : Fin n → X)
    (labels : Fin n → ℝ)
    (f : X → ℝ) : ℝ :=
  E (TrainingData sample labels f) + g (normLike f)
```

<a id="mathformer-autoformalizedrepresentertheorem-isminimizer"></a>

## `Mathformer.AutoformalizedRepresenterTheorem.IsMinimizer`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedRepresenterTheorem.lean:117](../../../../../backends/lean/Mathformer/AutoformalizedRepresenterTheorem.lean#L117)

**Original Source**

A minimizer is a candidate whose objective value is no larger than the objective value of every other candidate.

**Original LaTeX**

```latex
`f^* \in \arg\min_f J(f)` iff
`\forall h,\ J(f^*)\le J(h)`.
```

$$
f^* \in \arg\min_f J(f)
$$

$$
\forall h,\ J(f^*)\le J(h)
$$

**Lean**

```lean
def IsMinimizer (J : (X → ℝ) → ℝ) (f : X → ℝ) : Prop :=
  ∀ h : X → ℝ, J f ≤ J h
```

<a id="mathformer-autoformalizedrepresentertheorem-weakrepresenterreduction"></a>

## `Mathformer.AutoformalizedRepresenterTheorem.WeakRepresenterReduction`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedRepresenterTheorem.lean:128](../../../../../backends/lean/Mathformer/AutoformalizedRepresenterTheorem.lean#L128)

**Original Source**

The projection proof replaces a function by its component in the span of the training kernel sections without changing training values and without increasing the norm.

**Original LaTeX**

```latex
writing `f=s+v`, with
`s=\sum_i \alpha_i k(\cdot,x_i)` and `v \perp k(\cdot,x_i)`, gives
`s(x_j)=f(x_j)` and `\|s\|\le\|f\|`.
```

$$
f=s+v
$$

$$
s=\sum_i \alpha_i k(\cdot,x_i)
$$

$$
v \perp k(\cdot,x_i)
$$

**Lean**

```lean
def WeakRepresenterReduction {n : ℕ}
    (k : X → X → ℝ)
    (sample : Fin n → X)
    (normLike : (X → ℝ) → ℝ) : Prop :=
  ∀ f : X → ℝ,
    ∃ h : X → ℝ,
      FiniteKernelCombination k sample h ∧
        SameTrainingValues sample f h ∧
          normLike h ≤ normLike f
```

<a id="mathformer-autoformalizedrepresentertheorem-strictrepresenterreduction"></a>

## `Mathformer.AutoformalizedRepresenterTheorem.StrictRepresenterReduction`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedRepresenterTheorem.lean:146](../../../../../backends/lean/Mathformer/AutoformalizedRepresenterTheorem.lean#L146)

**Original Source**

If a function has a nonzero orthogonal component outside the finite span, setting that component to zero leaves the loss unchanged and strictly decreases the norm.

**Original LaTeX**

```latex
if `f` is not in the span, then for
`s=\sum_i \alpha_i k(\cdot,x_i)`,
`s(x_j)=f(x_j)` and `\|s\|<\|f\|`.
```

$$
f
$$

$$
s=\sum_i \alpha_i k(\cdot,x_i)
$$

$$
s(x_j)=f(x_j)
$$

**Lean**

```lean
def StrictRepresenterReduction {n : ℕ}
    (k : X → X → ℝ)
    (sample : Fin n → X)
    (normLike : (X → ℝ) → ℝ) : Prop :=
  ∀ f : X → ℝ,
    ¬ FiniteKernelCombination k sample f →
      ∃ h : X → ℝ,
        FiniteKernelCombination k sample h ∧
          SameTrainingValues sample f h ∧
            normLike h < normLike f
```

<a id="mathformer-autoformalizedrepresentertheorem-trainingdata-eq-of-sametrainingvalues"></a>

## `Mathformer.AutoformalizedRepresenterTheorem.trainingData_eq_of_sameTrainingValues`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedRepresenterTheorem.lean:163](../../../../../backends/lean/Mathformer/AutoformalizedRepresenterTheorem.lean#L163)

**Generated Notes**

If two functions agree on all training inputs, then the training data fed to the empirical loss are equal.

**Generated LaTeX**

```latex
`h(x_i)=f(x_i)` for all `i` implies
`(x_i,y_i,h(x_i))_i=(x_i,y_i,f(x_i))_i`.
```

$$
h(x_i)=f(x_i)
$$

$$
i
$$

$$
(x_i,y_i,h(x_i))_i=(x_i,y_i,f(x_i))_i
$$

**Lean**

```lean
theorem trainingData_eq_of_sameTrainingValues {n : ℕ}
    {sample : Fin n → X} {labels : Fin n → ℝ} {f h : X → ℝ}
    (hsame : SameTrainingValues sample f h) :
    TrainingData sample labels h = TrainingData sample labels f := by
  funext i
  exact by
    simp [TrainingData, hsame i]
```

<a id="mathformer-autoformalizedrepresentertheorem-exists-representer-minimizer-of-minimizer"></a>

## `Mathformer.AutoformalizedRepresenterTheorem.exists_representer_minimizer_of_minimizer`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedRepresenterTheorem.lean:178](../../../../../backends/lean/Mathformer/AutoformalizedRepresenterTheorem.lean#L178)

**Generated Notes**

A weak representer reduction turns any minimizer into a representer-form minimizer with the same training predictions.

**Generated LaTeX**

```latex
if `g` is nondecreasing and `f^*` minimizes
`E+g(\|\cdot\|)`, then there is a minimizer
`h=\sum_i \alpha_i k(\cdot,x_i)` with `h(x_j)=f^*(x_j)`.
```

$$
g
$$

$$
f^*
$$

$$
E+g(\|\cdot\|)
$$

**Lean**

```lean
theorem exists_representer_minimizer_of_minimizer {n : ℕ}
    {k : X → X → ℝ}
    {sample : Fin n → X}
    {labels : Fin n → ℝ}
    {E : (Fin n → X × ℝ × ℝ) → ℝ}
    {g : ℝ → ℝ}
    {normLike : (X → ℝ) → ℝ}
    (hg : Monotone g)
    (hreduce : WeakRepresenterReduction k sample normLike)
    {fstar : X → ℝ}
    (hmin : IsMinimizer (RegularizedEmpiricalRisk E g normLike sample labels) fstar) :
    ∃ h : X → ℝ,
      FiniteKernelCombination k sample h ∧
        IsMinimizer (RegularizedEmpiricalRisk E g normLike sample labels) h ∧
          SameTrainingValues sample fstar h ∧
            normLike h ≤ normLike fstar := by
  rcases hreduce fstar with ⟨h, hrepr, hsame, hnorm⟩
  have hE : E (TrainingData sample labels h) =
      E (TrainingData sample labels fstar) := by
    rw [trainingData_eq_of_sameTrainingValues hsame]
  have hobj_le :
      RegularizedEmpiricalRisk E g normLike sample labels h ≤
        RegularizedEmpiricalRisk E g normLike sample labels fstar := by
    unfold RegularizedEmpiricalRisk
    rw [hE]
    exact add_le_add_left (hg hnorm) _
  have hmin_h :
      IsMinimizer (RegularizedEmpiricalRisk E g normLike sample labels) h := by
    intro q
    exact le_trans hobj_le (hmin q)
  exact ⟨h, hrepr, hmin_h, hsame, hnorm⟩
```

<a id="mathformer-autoformalizedrepresentertheorem-representer-theorem-real-valued"></a>

## `Mathformer.AutoformalizedRepresenterTheorem.representer_theorem_real_valued`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedRepresenterTheorem.lean:218](../../../../../backends/lean/Mathformer/AutoformalizedRepresenterTheorem.lean#L218)

**Original Source**

Under a strictly increasing regularizer, any minimizer of the regularized empirical risk must lie in the finite span of the kernel sections at the training inputs.

**Original LaTeX**

```latex
if `g` is strictly increasing, then every minimizer
`f^*` satisfies
`f^*(\cdot)=\sum_{i=1}^n \alpha_i k(\cdot,x_i)`.
```

$$
g
$$

$$
f^*
$$

$$
f^*(\cdot)=\sum_{i=1}^n \alpha_i k(\cdot,x_i)
$$

**Lean**

```lean
theorem representer_theorem_real_valued {n : ℕ}
    {k : X → X → ℝ}
    {sample : Fin n → X}
    {labels : Fin n → ℝ}
    {E : (Fin n → X × ℝ × ℝ) → ℝ}
    {g : ℝ → ℝ}
    {normLike : (X → ℝ) → ℝ}
    (hg : StrictMono g)
    (hreduce : StrictRepresenterReduction k sample normLike)
    {fstar : X → ℝ}
    (hmin : IsMinimizer (RegularizedEmpiricalRisk E g normLike sample labels) fstar) :
    FiniteKernelCombination k sample fstar := by
  by_contra hnot
  rcases hreduce fstar hnot with ⟨h, _hrepr, hsame, hnorm⟩
  have hE : E (TrainingData sample labels h) =
      E (TrainingData sample labels fstar) := by
    rw [trainingData_eq_of_sameTrainingValues hsame]
  have hglt : g (normLike h) < g (normLike fstar) :=
    hg hnorm
  have hobj_lt :
      RegularizedEmpiricalRisk E g normLike sample labels h <
        RegularizedEmpiricalRisk E g normLike sample labels fstar := by
    unfold RegularizedEmpiricalRisk
    rw [hE]
    exact add_lt_add_left hglt _
  exact (not_lt_of_ge (hmin h)) hobj_lt

end AutoformalizedRepresenterTheorem
end Mathformer
```
