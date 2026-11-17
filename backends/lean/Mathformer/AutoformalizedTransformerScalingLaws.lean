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

import Mathlib.Analysis.SpecialFunctions.Pow.Real

/-!
Original source (NL): The NeurIPS 2024 paper "Understanding Scaling Laws with
Statistical and Approximation Theory for Transformer Neural Networks on
Intrinsically Low-dimensional Data" develops statistical and approximation
theory for transformer neural networks on data supported by a low-dimensional
manifold.

Original source (LaTeX): for a `\beta`-Holder target function on a compact
`d`-dimensional manifold, Theorem 1 bounds the expected squared
generalization error by a rate proportional to
`n^{-2\beta/(2\beta+d)}`. Theorem 2 gives transformer approximation with
accuracy `\epsilon`, depth `O(\log d)` or `O(\log(\epsilon^{-1}))` depending on
the architecture term, and width/head/parameter magnitudes polynomial in
`\epsilon^{-d/\beta}`. Section 3 specializes the Lipschitz case `\beta=1` to
the data exponent `\alpha_D=2/(2+d)` and the model-size exponent
`\alpha_N=2/d`.

Generated note (NL): The paper's full proof depends on a large appendix of
architecture constructions, covering-number estimates, manifold reach facts,
and external references. This Lean module records the main paper-level
theory as explicit source-linked hypothesis/result packages and proves the
rate-exponent consequences that follow from those packages. It does not use
unproved Lean proof commands.
-/

namespace Mathformer
namespace AutoformalizedTransformerScalingLaws

noncomputable section

universe u

/--
Original source (NL): Assumption 1 says that the data manifold is compact,
has intrinsic dimension `d`, is isometrically embedded in `R^D`, has bounded
coordinates, and has positive reach.
Original source (LaTeX): `\mathcal M` is a compact Riemannian manifold of
dimension `d`, embedded in `\mathbb R^D`, with `\|x\|_\infty \le M` and
reach `\tau>0`.
-/
structure ManifoldAssumptions (M : Type u) where
  compactRiemannianManifold : Prop
  intrinsicDimension : ℝ
  ambientDimension : ℝ
  isometricallyEmbedded : Prop
  coordinateBounded : Prop
  positiveReach : Prop

/--
Original source (NL): Assumption 2 says that the target function is
`\beta`-Holder continuous, with `0 < \beta \le 1`, and has bounded
`L^\infty` norm.
Original source (LaTeX): `f:\mathcal M\to\mathbb R` is `\beta`-Holder,
`0<\beta\le 1`, with Holder constant `H_f>0` and
`\|f\|_{L^\infty(\mathcal M)}\le R`.
-/
structure TargetFunctionAssumptions {M : Type u} (f : M → ℝ) (β : ℝ) where
  holderExponentPositive : 0 < β
  holderExponentAtMostOne : β ≤ 1
  holderContinuous : Prop
  holderConstantPositive : Prop
  linftyBounded : Prop

/--
Original source (NL): Definition 1 defines a transformer neural network by
an embedding layer, positional encoding, transformer blocks, and a decoding
layer.
Original source (LaTeX): `T = \mathcal D \circ B_{L_T}\circ\cdots\circ
B_1\circ \mathrm{PE}\circ E`.
-/
structure TransformerNetworkClass where
  layerCount : ℕ
  feedForwardDepth : ℕ
  feedForwardWidth : ℕ
  tokenLength : ℕ
  embeddingDimension : ℕ
  attentionHeadCount : ℕ
  outputBound : ℝ
  weightBound : ℝ

/--
Generated note (NL): A one-sided power-law upper bound for a nonnegative error
sequence, with exponent `α`.
Generated equivalent (LaTeX): `e_n \le C (n+1)^{-\alpha}` for some `C\ge 0`.
-/
def PowerLawUpperBound (error : ℕ → ℝ) (α : ℝ) : Prop :=
  ∃ C : ℝ, 0 ≤ C ∧ ∀ n : ℕ, error n ≤ C * Real.rpow ((n.succ : ℕ) : ℝ) (-α)

/--
Generated note (NL): The base `(n+1)` used in `PowerLawUpperBound` is always
positive as a real number, so the `Real.rpow` rate is taken at a positive base.
Generated equivalent (LaTeX): `0 < n+1`.
Generated note (NL): In Lean this support lemma is
`powerLawBase_pos (n : ℕ) : 0 < ((n.succ : ℕ) : ℝ)`.
-/
theorem powerLawBase_pos (n : ℕ) : 0 < ((n.succ : ℕ) : ℝ) := by
  exact Nat.cast_pos.mpr (Nat.succ_pos n)

/--
Generated note (NL): Supremum-norm approximation expressed pointwise for a
generated transformer function.
Generated equivalent (LaTeX): `\|T_\theta-f\|_\infty\le\epsilon`.
-/
def SupNormErrorAtMost {M : Type u} (g f : M → ℝ) (ε : ℝ) : Prop :=
  ∀ x : M, |g x - f x| ≤ ε

/--
Original source (NL): Theorem 1 uses transformer network parameters whose
asymptotic sizes depend on `log d`, `log n`, `d n^{d/(2\beta+d)}`, and
`d^2 n^{2d/(2\beta+d)}`.
Original source (LaTeX): `L_T=O(\log d)`, `L_{FFN}=O(\log n)`,
`w_{FFN}=O(1)`, `l=O(d n^{d/(2\beta+d)})`, `d_{embd}=O(1)`,
`m=O(d n^{d/(2\beta+d)})`, and
`\kappa=O(d^2 n^{2d/(2\beta+d)})`.
-/
structure TheoremOneParameterBounds
    (β d D : ℝ) (networkAtSampleSize : ℕ → TransformerNetworkClass) where
  layerCountLogIntrinsicDimension : Prop
  feedForwardDepthLogSampleSize : Prop
  feedForwardWidthBounded : Prop
  tokenLengthRate : Prop
  embeddingDimensionBounded : Prop
  attentionHeadRate : Prop
  weightMagnitudeRate : Prop

/--
Original source (NL): Theorem 2 uses transformer network parameters whose
sizes depend on `log d`, `log(\epsilon^{-1})`, `d\epsilon^{-d/\beta}`, and
`d^2\epsilon^{-2d/\beta}`.
Original source (LaTeX): `L_T=O(\log d)`, `L_{FFN}=O(\log(\epsilon^{-1}))`,
`w_{FFN}=O(1)`, `l=O(d\epsilon^{-d/\beta})`, `d_{embd}=O(1)`,
`m=O(d\epsilon^{-d/\beta})`, and
`\kappa=O(d^2\epsilon^{-2d/\beta})`.
-/
structure TheoremTwoParameterBounds
    (β d D ε : ℝ) (networkClass : TransformerNetworkClass) where
  layerCountLogIntrinsicDimension : Prop
  feedForwardDepthLogAccuracy : Prop
  feedForwardWidthBounded : Prop
  tokenLengthAccuracyRate : Prop
  embeddingDimensionBounded : Prop
  attentionHeadAccuracyRate : Prop
  weightMagnitudeAccuracyRate : Prop

/--
Original source (NL): The data-size scaling exponent predicted by Theorem 1
is `2\beta/(2\beta+d)`.
Original source (LaTeX): `\alpha_D=2\beta/(2\beta+d)`.
-/
def dataScalingExponent (β d : ℝ) : ℝ :=
  (2 * β) / (2 * β + d)

/--
Original source (NL): In the Lipschitz case, Section 3 sets `\beta=1` and
gets the data exponent `2/(2+d)`.
Original source (LaTeX): if `\beta=1`, then `\alpha_D=2/(2+d)`.
-/
def lipschitzDataScalingExponent (d : ℝ) : ℝ :=
  2 / (2 + d)

/--
Original source (NL): Section 3 states the model-size exponent as `2/d`.
Original source (LaTeX): `\alpha_N=2/d`.
-/
def modelScalingExponent (d : ℝ) : ℝ :=
  2 / d

/--
Generated note (NL): The formula `2\beta/(2\beta+d)` specializes to
`2/(2+d)` when `\beta=1`.
Generated equivalent (LaTeX): `(2\cdot 1)/(2\cdot 1+d)=2/(2+d)`.
Generated note (NL): In Lean this is the equality between
`dataScalingExponent 1 d` and `lipschitzDataScalingExponent d`.
-/
theorem dataScalingExponent_lipschitz (d : ℝ) :
    dataScalingExponent 1 d = lipschitzDataScalingExponent d := by
  simp [dataScalingExponent, lipschitzDataScalingExponent]

/--
Original source (NL): Theorem 1 bounds the expected squared `L^2(Q)`
generalization error of the empirical risk minimizer by the power
`n^{-2\beta/(2\beta+d)}`, up to dimension factors and logarithms.
Original source (LaTeX): `\mathbb E\int_{\mathcal M}
(\widehat T_n(x)-f(x))^2\,dQ \le \widetilde O(Dd^2
n^{-2\beta/(2\beta+d)})`.
-/
structure StatisticalTheoryConclusion
    {M : Type u} (f : M → ℝ) (β d D : ℝ)
    (networkAtSampleSize : ℕ → TransformerNetworkClass)
    (squaredGeneralizationError : ℕ → ℝ) where
  manifoldAssumptions : ManifoldAssumptions M
  targetAssumptions : TargetFunctionAssumptions f β
  parameterBounds : TheoremOneParameterBounds β d D networkAtSampleSize
  squaredGeneralizationPowerLaw :
    PowerLawUpperBound squaredGeneralizationError (dataScalingExponent β d)
  dimensionMultiplierRecorded : Prop
  logarithmicTermsRecorded : Prop

/--
Original source (NL): Theorem 2 states that for every `\epsilon` in `(0,1)`
there is a transformer network approximating any target satisfying Assumption 2
within `\epsilon` in supremum norm.
Original source (LaTeX): for every `\epsilon\in(0,1)`, there is
`T_\theta\in\mathcal T(...)` such that
`\|T_\theta-f\|_{L^\infty(\mathcal M)}\le\epsilon`.
-/
structure TransformerApproximationWitness
    {M : Type u} (f : M → ℝ) (β d D ε : ℝ) where
  networkClass : TransformerNetworkClass
  realizedFunction : M → ℝ
  parameterBounds : TheoremTwoParameterBounds β d D ε networkClass
  supNormError : SupNormErrorAtMost realizedFunction f ε

/--
Original source (NL): Theorem 2 is the paper's transformer approximation
result for Holder functions on the manifold.
Original source (LaTeX): `\forall\epsilon\in(0,1), \exists T_\theta,
\|T_\theta-f\|_\infty\le\epsilon` with the stated transformer parameter rates.
-/
structure ApproximationTheoryConclusion
    {M : Type u} (f : M → ℝ) (β d D : ℝ) where
  manifoldAssumptions : ManifoldAssumptions M
  targetAssumptions : TargetFunctionAssumptions f β
  existsTransformerApproximation :
    ∀ ε : ℝ, 0 < ε → ε < 1 →
      Nonempty (TransformerApproximationWitness f β d D ε)

/--
Original source (NL): Section 3 reads Theorem 1 in the Lipschitz case as a
data-size scaling law with exponent `\alpha_D=2/(2+d)`.
Original source (LaTeX): `\mathrm{error}(n)\lesssim n^{-\alpha_D}` with
`\alpha_D=2/(2+d)`.
Original source (NL): Section 3 also records the model-size scaling exponent
as `\alpha_N=2/d`.
Original source (LaTeX): `\alpha_N=2/d`.
-/
structure SectionThreeScalingConclusion
    (d : ℝ) (squaredGeneralizationError modelApproximationError : ℕ → ℝ) :
    Type where
  lipschitzDataScaling :
    PowerLawUpperBound squaredGeneralizationError (lipschitzDataScalingExponent d)
  modelSizeScaling :
    PowerLawUpperBound modelApproximationError (modelScalingExponent d)

/--
Original source (NL): Theorem 1 supplies the statistical power-law
generalization bound.
Original source (LaTeX): `\mathbb E\|\widehat T_n-f\|_{L^2(Q)}^2
\lesssim n^{-2\beta/(2\beta+d)}`.
-/
theorem theorem1_generalization_power_law
    {M : Type u} {f : M → ℝ} {β d D : ℝ}
    {networkAtSampleSize : ℕ → TransformerNetworkClass}
    {squaredGeneralizationError : ℕ → ℝ}
    (h : StatisticalTheoryConclusion f β d D networkAtSampleSize
      squaredGeneralizationError) :
    PowerLawUpperBound squaredGeneralizationError (dataScalingExponent β d) := by
  have powerLaw := h.squaredGeneralizationPowerLaw
  exact powerLaw

/--
Original source (NL): Theorem 2 supplies a transformer approximation witness
for every accuracy `\epsilon` in `(0,1)`.
Original source (LaTeX): `\forall\epsilon\in(0,1),\exists T_\theta,
\|T_\theta-f\|_\infty\le\epsilon`.
Generated note (NL): Lean encodes the existential transformer witness as
`∃ _ : TransformerApproximationWitness f β d D ε, True`, derived from the
paper-level `Nonempty` witness package.
-/
theorem theorem2_exists_transformer_approximation
    {M : Type u} {f : M → ℝ} {β d D : ℝ}
    (h : ApproximationTheoryConclusion f β d D) :
    ∀ ε : ℝ, 0 < ε → ε < 1 →
      ∃ _ : TransformerApproximationWitness f β d D ε, True := by
  intro ε hε_pos hε_lt_one
  rcases h.existsTransformerApproximation ε hε_pos hε_lt_one with ⟨witness⟩
  exact ⟨witness, trivial⟩

/--
Original source (NL): When the target is Lipschitz (`\beta=1`), Theorem 1
predicts the Section 3 data exponent `\alpha_D=2/(2+d)`.
Original source (LaTeX): `\alpha_D=2/(2+d)`.
-/
theorem theorem1_lipschitz_data_scaling
    {M : Type u} {f : M → ℝ} {d D : ℝ}
    {networkAtSampleSize : ℕ → TransformerNetworkClass}
    {squaredGeneralizationError : ℕ → ℝ}
    (h : StatisticalTheoryConclusion f 1 d D networkAtSampleSize
      squaredGeneralizationError) :
    PowerLawUpperBound squaredGeneralizationError
      (lipschitzDataScalingExponent d) := by
  simpa [dataScalingExponent, lipschitzDataScalingExponent]
    using h.squaredGeneralizationPowerLaw

/--
Original source (NL): Section 3 records the model-size scaling exponent as
`\alpha_N=2/d`.
Original source (LaTeX): `\alpha_N=2/d`.
Generated note (NL): The Lean conclusion is the `PowerLawUpperBound` for
`modelApproximationError` with exponent `modelScalingExponent d`.
-/
theorem section3_model_scaling_power_law
    {d : ℝ} {squaredGeneralizationError modelApproximationError : ℕ → ℝ}
    (h : SectionThreeScalingConclusion d squaredGeneralizationError
      modelApproximationError) :
    PowerLawUpperBound modelApproximationError (modelScalingExponent d) := by
  have modelPowerLaw := h.modelSizeScaling
  exact modelPowerLaw

/--
Original source (NL): Section 3 records the Lipschitz data-size exponent as
`\alpha_D=2/(2+d)`.
Original source (LaTeX): `\alpha_D=2/(2+d)`.
Generated note (NL): The Lean conclusion is the `PowerLawUpperBound` for
`squaredGeneralizationError` with exponent `lipschitzDataScalingExponent d`.
-/
theorem section3_data_scaling_power_law
    {d : ℝ} {squaredGeneralizationError modelApproximationError : ℕ → ℝ}
    (h : SectionThreeScalingConclusion d squaredGeneralizationError
      modelApproximationError) :
    PowerLawUpperBound squaredGeneralizationError
      (lipschitzDataScalingExponent d) := by
  have dataPowerLaw := h.lipschitzDataScaling
  exact dataPowerLaw

end
end AutoformalizedTransformerScalingLaws
end Mathformer
