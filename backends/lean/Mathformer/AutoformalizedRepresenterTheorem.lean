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

import Mathlib.Algebra.BigOperators.Group.Finset.Basic
import Mathlib.Data.Fintype.Basic
import Mathlib.Data.Real.Basic
import Mathlib.Order.Monotone.Basic

/-!
Original source (NL): A representer theorem states that a minimizer of a
regularized empirical risk functional over a reproducing kernel Hilbert space
can be represented as a finite linear combination of kernel products evaluated
at the input points in the training set.

Original source (LaTeX): if `k : \mathcal X \times \mathcal X \to \mathbb R`
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
-/

namespace Mathformer
namespace AutoformalizedRepresenterTheorem

open Finset

universe u

variable {X : Type u}

/--
Original source (NL): The kernel section at a training input `x_i` is the
function `x ↦ k(x,x_i)`.
Original source (LaTeX): `k(\cdot,x_i)`.
-/
def KernelSection (k : X → X → ℝ) (xᵢ : X) : X → ℝ :=
  fun x => k x xᵢ

/--
Original source (NL): A representer-form function is a finite linear
combination of the kernel sections at the training inputs.
Original source (LaTeX): `f(\cdot)=\sum_{i=1}^n \alpha_i k(\cdot,x_i)`.
-/
def FiniteKernelCombination {n : ℕ}
    (k : X → X → ℝ) (sample : Fin n → X) (f : X → ℝ) : Prop :=
  ∃ α : Fin n → ℝ, ∀ x : X, f x = ∑ i : Fin n, α i * k x (sample i)

/--
Generated note (NL): Unfolding the finite kernel combination property gives the
coefficient vector and the pointwise kernel expansion.
Generated equivalent (LaTeX): from
`f=\sum_i \alpha_i k(\cdot,x_i)` we obtain the same equality at every `x`.
-/
theorem finiteKernelCombination_apply {n : ℕ}
    {k : X → X → ℝ} {sample : Fin n → X} {f : X → ℝ}
    (hf : FiniteKernelCombination k sample f) :
    ∃ α : Fin n → ℝ, ∀ x : X, f x = ∑ i : Fin n, α i * k x (sample i) := by
  exact hf

/--
Original source (NL): The empirical loss only sees the values of a candidate
function at the training inputs.
Original source (LaTeX): the loss term has inputs
`(x_i,y_i,f(x_i))_{i=1}^n`.
-/
def TrainingData {n : ℕ}
    (sample : Fin n → X) (labels : Fin n → ℝ) (f : X → ℝ) :
    Fin n → X × ℝ × ℝ :=
  fun i => (sample i, labels i, f (sample i))

/--
Original source (NL): Two candidate functions agree on the training sample when
they give the same prediction at every training input.
Original source (LaTeX): `\forall i,\ h(x_i)=f(x_i)`.
-/
def SameTrainingValues {n : ℕ}
    (sample : Fin n → X) (f h : X → ℝ) : Prop :=
  ∀ i : Fin n, h (sample i) = f (sample i)

/--
Original source (NL): The regularized empirical risk is the empirical error
plus a monotone function of the Hilbert-space norm.
Original source (LaTeX):
`E((x_i,y_i,f(x_i))_{i=1}^n)+g(\|f\|)`.
Generated note: `normLike` is the regularization size supplied by the RKHS
model, usually the Hilbert norm.
-/
def RegularizedEmpiricalRisk {n : ℕ}
    (E : (Fin n → X × ℝ × ℝ) → ℝ)
    (g : ℝ → ℝ)
    (normLike : (X → ℝ) → ℝ)
    (sample : Fin n → X)
    (labels : Fin n → ℝ)
    (f : X → ℝ) : ℝ :=
  E (TrainingData sample labels f) + g (normLike f)

/--
Original source (NL): A minimizer is a candidate whose objective value is no
larger than the objective value of every other candidate.
Original source (LaTeX): `f^* \in \arg\min_f J(f)` iff
`\forall h,\ J(f^*)\le J(h)`.
-/
def IsMinimizer (J : (X → ℝ) → ℝ) (f : X → ℝ) : Prop :=
  ∀ h : X → ℝ, J f ≤ J h

/--
Original source (NL): The projection proof replaces a function by its component
in the span of the training kernel sections without changing training values
and without increasing the norm.
Original source (LaTeX): writing `f=s+v`, with
`s=\sum_i \alpha_i k(\cdot,x_i)` and `v \perp k(\cdot,x_i)`, gives
`s(x_j)=f(x_j)` and `\|s\|\le\|f\|`.
-/
def WeakRepresenterReduction {n : ℕ}
    (k : X → X → ℝ)
    (sample : Fin n → X)
    (normLike : (X → ℝ) → ℝ) : Prop :=
  ∀ f : X → ℝ,
    ∃ h : X → ℝ,
      FiniteKernelCombination k sample h ∧
        SameTrainingValues sample f h ∧
          normLike h ≤ normLike f

/--
Original source (NL): If a function has a nonzero orthogonal component outside
the finite span, setting that component to zero leaves the loss unchanged and
strictly decreases the norm.
Original source (LaTeX): if `f` is not in the span, then for
`s=\sum_i \alpha_i k(\cdot,x_i)`,
`s(x_j)=f(x_j)` and `\|s\|<\|f\|`.
-/
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

/--
Generated note (NL): If two functions agree on all training inputs, then the
training data fed to the empirical loss are equal.
Generated equivalent (LaTeX): `h(x_i)=f(x_i)` for all `i` implies
`(x_i,y_i,h(x_i))_i=(x_i,y_i,f(x_i))_i`.
-/
theorem trainingData_eq_of_sameTrainingValues {n : ℕ}
    {sample : Fin n → X} {labels : Fin n → ℝ} {f h : X → ℝ}
    (hsame : SameTrainingValues sample f h) :
    TrainingData sample labels h = TrainingData sample labels f := by
  funext i
  exact by
    simp [TrainingData, hsame i]

/--
Generated note (NL): A weak representer reduction turns any minimizer into a
representer-form minimizer with the same training predictions.
Generated equivalent (LaTeX): if `g` is nondecreasing and `f^*` minimizes
`E+g(\|\cdot\|)`, then there is a minimizer
`h=\sum_i \alpha_i k(\cdot,x_i)` with `h(x_j)=f^*(x_j)`.
-/
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

/--
Original source (NL): Under a strictly increasing regularizer, any minimizer of
the regularized empirical risk must lie in the finite span of the kernel
sections at the training inputs.
Original source (LaTeX): if `g` is strictly increasing, then every minimizer
`f^*` satisfies
`f^*(\cdot)=\sum_{i=1}^n \alpha_i k(\cdot,x_i)`.
-/
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
