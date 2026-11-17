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

# `Mathformer.AutoformalizedTransformerScalingLaws`

[Back to index](../../INDEX.md)

## Metadata

- Source: [backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean](../../../../../backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean)
- Status: `candidate`
- SHA-256: `d2d9ed1163befab654236ad53301a8ec6de9ed9349766dcc559876a82476ae45`
- Declarations: `21`

## Imports

```lean
import Mathlib.Analysis.SpecialFunctions.Pow.Real
```

## Module Source Notes

**Original Source**

The NeurIPS 2024 paper "Understanding Scaling Laws with Statistical and Approximation Theory for Transformer Neural Networks on Intrinsically Low-dimensional Data" develops statistical and approximation theory for transformer neural networks on data supported by a low-dimensional manifold.

**Original LaTeX**

```latex
for a `\beta`-Holder target function on a compact
`d`-dimensional manifold, Theorem 1 bounds the expected squared
generalization error by a rate proportional to
`n^{-2\beta/(2\beta+d)}`. Theorem 2 gives transformer approximation with
accuracy `\epsilon`, depth `O(\log d)` or `O(\log(\epsilon^{-1}))` depending on
the architecture term, and width/head/parameter magnitudes polynomial in
`\epsilon^{-d/\beta}`. Section 3 specializes the Lipschitz case `\beta=1` to
the data exponent `\alpha_D=2/(2+d)` and the model-size exponent
`\alpha_N=2/d`.
```

$$
\beta
$$

$$
d
$$

$$
n^{-2\beta/(2\beta+d)}
$$

**Generated Notes**

The paper's full proof depends on a large appendix of architecture constructions, covering-number estimates, manifold reach facts, and external references. This Lean module records the main paper-level theory as explicit source-linked hypothesis/result packages and proves the rate-exponent consequences that follow from those packages. It does not use unproved Lean proof commands.

## Declarations

- [`Mathformer.AutoformalizedTransformerScalingLaws.ManifoldAssumptions`](#mathformer-autoformalizedtransformerscalinglaws-manifoldassumptions) (structure, line 52)
- [`Mathformer.AutoformalizedTransformerScalingLaws.TargetFunctionAssumptions`](#mathformer-autoformalizedtransformerscalinglaws-targetfunctionassumptions) (structure, line 68)
- [`Mathformer.AutoformalizedTransformerScalingLaws.TransformerNetworkClass`](#mathformer-autoformalizedtransformerscalinglaws-transformernetworkclass) (structure, line 82)
- [`Mathformer.AutoformalizedTransformerScalingLaws.PowerLawUpperBound`](#mathformer-autoformalizedtransformerscalinglaws-powerlawupperbound) (def, line 97)
- [`Mathformer.AutoformalizedTransformerScalingLaws.powerLawBase_pos`](#mathformer-autoformalizedtransformerscalinglaws-powerlawbase-pos) (theorem, line 107)
- [`Mathformer.AutoformalizedTransformerScalingLaws.SupNormErrorAtMost`](#mathformer-autoformalizedtransformerscalinglaws-supnormerroratmost) (def, line 115)
- [`Mathformer.AutoformalizedTransformerScalingLaws.TheoremOneParameterBounds`](#mathformer-autoformalizedtransformerscalinglaws-theoremoneparameterbounds) (structure, line 127)
- [`Mathformer.AutoformalizedTransformerScalingLaws.TheoremTwoParameterBounds`](#mathformer-autoformalizedtransformerscalinglaws-theoremtwoparameterbounds) (structure, line 146)
- [`Mathformer.AutoformalizedTransformerScalingLaws.dataScalingExponent`](#mathformer-autoformalizedtransformerscalinglaws-datascalingexponent) (def, line 161)
- [`Mathformer.AutoformalizedTransformerScalingLaws.lipschitzDataScalingExponent`](#mathformer-autoformalizedtransformerscalinglaws-lipschitzdatascalingexponent) (def, line 169)
- [`Mathformer.AutoformalizedTransformerScalingLaws.modelScalingExponent`](#mathformer-autoformalizedtransformerscalinglaws-modelscalingexponent) (def, line 176)
- [`Mathformer.AutoformalizedTransformerScalingLaws.dataScalingExponent_lipschitz`](#mathformer-autoformalizedtransformerscalinglaws-datascalingexponent-lipschitz) (theorem, line 186)
- [`Mathformer.AutoformalizedTransformerScalingLaws.StatisticalTheoryConclusion`](#mathformer-autoformalizedtransformerscalinglaws-statisticaltheoryconclusion) (structure, line 198)
- [`Mathformer.AutoformalizedTransformerScalingLaws.TransformerApproximationWitness`](#mathformer-autoformalizedtransformerscalinglaws-transformerapproximationwitness) (structure, line 218)
- [`Mathformer.AutoformalizedTransformerScalingLaws.ApproximationTheoryConclusion`](#mathformer-autoformalizedtransformerscalinglaws-approximationtheoryconclusion) (structure, line 231)
- [`Mathformer.AutoformalizedTransformerScalingLaws.SectionThreeScalingConclusion`](#mathformer-autoformalizedtransformerscalinglaws-sectionthreescalingconclusion) (structure, line 248)
- [`Mathformer.AutoformalizedTransformerScalingLaws.theorem1_generalization_power_law`](#mathformer-autoformalizedtransformerscalinglaws-theorem1-generalization-power-law) (theorem, line 262)
- [`Mathformer.AutoformalizedTransformerScalingLaws.theorem2_exists_transformer_approximation`](#mathformer-autoformalizedtransformerscalinglaws-theorem2-exists-transformer-approximation) (theorem, line 281)
- [`Mathformer.AutoformalizedTransformerScalingLaws.theorem1_lipschitz_data_scaling`](#mathformer-autoformalizedtransformerscalinglaws-theorem1-lipschitz-data-scaling) (theorem, line 295)
- [`Mathformer.AutoformalizedTransformerScalingLaws.section3_model_scaling_power_law`](#mathformer-autoformalizedtransformerscalinglaws-section3-model-scaling-power-law) (theorem, line 313)
- [`Mathformer.AutoformalizedTransformerScalingLaws.section3_data_scaling_power_law`](#mathformer-autoformalizedtransformerscalinglaws-section3-data-scaling-power-law) (theorem, line 328)

<a id="mathformer-autoformalizedtransformerscalinglaws-manifoldassumptions"></a>

## `Mathformer.AutoformalizedTransformerScalingLaws.ManifoldAssumptions`

- Kind: `structure`
- Source line: [backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean:52](../../../../../backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean#L52)

**Original Source**

Assumption 1 says that the data manifold is compact, has intrinsic dimension `d`, is isometrically embedded in `R^D`, has bounded coordinates, and has positive reach.

**Original LaTeX**

```latex
`\mathcal M` is a compact Riemannian manifold of
dimension `d`, embedded in `\mathbb R^D`, with `\|x\|_\infty \le M` and
reach `\tau>0`.
```

$$
\mathcal M
$$

$$
d
$$

$$
\mathbb R^D
$$

**Lean**

```lean
structure ManifoldAssumptions (M : Type u) where
  compactRiemannianManifold : Prop
  intrinsicDimension : ℝ
  ambientDimension : ℝ
  isometricallyEmbedded : Prop
  coordinateBounded : Prop
  positiveReach : Prop
```

<a id="mathformer-autoformalizedtransformerscalinglaws-targetfunctionassumptions"></a>

## `Mathformer.AutoformalizedTransformerScalingLaws.TargetFunctionAssumptions`

- Kind: `structure`
- Source line: [backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean:68](../../../../../backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean#L68)

**Original Source**

Assumption 2 says that the target function is `\beta`-Holder continuous, with `0 < \beta \le 1`, and has bounded `L^\infty` norm.

**Original LaTeX**

```latex
`f:\mathcal M\to\mathbb R` is `\beta`-Holder,
`0<\beta\le 1`, with Holder constant `H_f>0` and
`\|f\|_{L^\infty(\mathcal M)}\le R`.
```

$$
f:\mathcal M\to\mathbb R
$$

$$
\beta
$$

$$
0<\beta\le 1
$$

**Lean**

```lean
structure TargetFunctionAssumptions {M : Type u} (f : M → ℝ) (β : ℝ) where
  holderExponentPositive : 0 < β
  holderExponentAtMostOne : β ≤ 1
  holderContinuous : Prop
  holderConstantPositive : Prop
  linftyBounded : Prop
```

<a id="mathformer-autoformalizedtransformerscalinglaws-transformernetworkclass"></a>

## `Mathformer.AutoformalizedTransformerScalingLaws.TransformerNetworkClass`

- Kind: `structure`
- Source line: [backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean:82](../../../../../backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean#L82)

**Original Source**

Definition 1 defines a transformer neural network by an embedding layer, positional encoding, transformer blocks, and a decoding layer.

**Original LaTeX**

```latex
`T = \mathcal D \circ B_{L_T}\circ\cdots\circ
B_1\circ \mathrm{PE}\circ E`.
```

$$
T = \mathcal D \circ B_{L_T}\circ\cdots\circ B_1\circ \mathrm{PE}\circ E
$$

**Lean**

```lean
structure TransformerNetworkClass where
  layerCount : ℕ
  feedForwardDepth : ℕ
  feedForwardWidth : ℕ
  tokenLength : ℕ
  embeddingDimension : ℕ
  attentionHeadCount : ℕ
  outputBound : ℝ
  weightBound : ℝ
```

<a id="mathformer-autoformalizedtransformerscalinglaws-powerlawupperbound"></a>

## `Mathformer.AutoformalizedTransformerScalingLaws.PowerLawUpperBound`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean:97](../../../../../backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean#L97)

**Generated Notes**

A one-sided power-law upper bound for a nonnegative error sequence, with exponent `α`.

**Generated LaTeX**

```latex
`e_n \le C (n+1)^{-\alpha}` for some `C\ge 0`.
```

$$
e_n \le C (n+1)^{-\alpha}
$$

$$
C\ge 0
$$

**Lean**

```lean
def PowerLawUpperBound (error : ℕ → ℝ) (α : ℝ) : Prop :=
  ∃ C : ℝ, 0 ≤ C ∧ ∀ n : ℕ, error n ≤ C * Real.rpow ((n.succ : ℕ) : ℝ) (-α)
```

<a id="mathformer-autoformalizedtransformerscalinglaws-powerlawbase-pos"></a>

## `Mathformer.AutoformalizedTransformerScalingLaws.powerLawBase_pos`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean:107](../../../../../backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean#L107)

**Generated Notes**

The base `(n+1)` used in `PowerLawUpperBound` is always positive as a real number, so the `Real.rpow` rate is taken at a positive base. In Lean this support lemma is `powerLawBase_pos (n : ℕ) : 0 < ((n.succ : ℕ) : ℝ)`.

**Generated LaTeX**

```latex
`0 < n+1`.
```

$$
0 < n+1
$$

**Lean**

```lean
theorem powerLawBase_pos (n : ℕ) : 0 < ((n.succ : ℕ) : ℝ) := by
  exact Nat.cast_pos.mpr (Nat.succ_pos n)
```

<a id="mathformer-autoformalizedtransformerscalinglaws-supnormerroratmost"></a>

## `Mathformer.AutoformalizedTransformerScalingLaws.SupNormErrorAtMost`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean:115](../../../../../backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean#L115)

**Generated Notes**

Supremum-norm approximation expressed pointwise for a generated transformer function.

**Generated LaTeX**

```latex
`\|T_\theta-f\|_\infty\le\epsilon`.
```

$$
\|T_\theta-f\|_\infty\le\epsilon
$$

**Lean**

```lean
def SupNormErrorAtMost {M : Type u} (g f : M → ℝ) (ε : ℝ) : Prop :=
  ∀ x : M, |g x - f x| ≤ ε
```

<a id="mathformer-autoformalizedtransformerscalinglaws-theoremoneparameterbounds"></a>

## `Mathformer.AutoformalizedTransformerScalingLaws.TheoremOneParameterBounds`

- Kind: `structure`
- Source line: [backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean:127](../../../../../backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean#L127)

**Original Source**

Theorem 1 uses transformer network parameters whose asymptotic sizes depend on `log d`, `log n`, `d n^{d/(2\beta+d)}`, and `d^2 n^{2d/(2\beta+d)}`.

**Original LaTeX**

```latex
`L_T=O(\log d)`, `L_{FFN}=O(\log n)`,
`w_{FFN}=O(1)`, `l=O(d n^{d/(2\beta+d)})`, `d_{embd}=O(1)`,
`m=O(d n^{d/(2\beta+d)})`, and
`\kappa=O(d^2 n^{2d/(2\beta+d)})`.
```

$$
L_T=O(\log d)
$$

$$
L_{FFN}=O(\log n)
$$

$$
w_{FFN}=O(1)
$$

**Lean**

```lean
structure TheoremOneParameterBounds
    (β d D : ℝ) (networkAtSampleSize : ℕ → TransformerNetworkClass) where
  layerCountLogIntrinsicDimension : Prop
  feedForwardDepthLogSampleSize : Prop
  feedForwardWidthBounded : Prop
  tokenLengthRate : Prop
  embeddingDimensionBounded : Prop
  attentionHeadRate : Prop
  weightMagnitudeRate : Prop
```

<a id="mathformer-autoformalizedtransformerscalinglaws-theoremtwoparameterbounds"></a>

## `Mathformer.AutoformalizedTransformerScalingLaws.TheoremTwoParameterBounds`

- Kind: `structure`
- Source line: [backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean:146](../../../../../backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean#L146)

**Original Source**

Theorem 2 uses transformer network parameters whose sizes depend on `log d`, `log(\epsilon^{-1})`, `d\epsilon^{-d/\beta}`, and `d^2\epsilon^{-2d/\beta}`.

**Original LaTeX**

```latex
`L_T=O(\log d)`, `L_{FFN}=O(\log(\epsilon^{-1}))`,
`w_{FFN}=O(1)`, `l=O(d\epsilon^{-d/\beta})`, `d_{embd}=O(1)`,
`m=O(d\epsilon^{-d/\beta})`, and
`\kappa=O(d^2\epsilon^{-2d/\beta})`.
```

$$
L_T=O(\log d)
$$

$$
L_{FFN}=O(\log(\epsilon^{-1}))
$$

$$
w_{FFN}=O(1)
$$

**Lean**

```lean
structure TheoremTwoParameterBounds
    (β d D ε : ℝ) (networkClass : TransformerNetworkClass) where
  layerCountLogIntrinsicDimension : Prop
  feedForwardDepthLogAccuracy : Prop
  feedForwardWidthBounded : Prop
  tokenLengthAccuracyRate : Prop
  embeddingDimensionBounded : Prop
  attentionHeadAccuracyRate : Prop
  weightMagnitudeAccuracyRate : Prop
```

<a id="mathformer-autoformalizedtransformerscalinglaws-datascalingexponent"></a>

## `Mathformer.AutoformalizedTransformerScalingLaws.dataScalingExponent`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean:161](../../../../../backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean#L161)

**Original Source**

The data-size scaling exponent predicted by Theorem 1 is `2\beta/(2\beta+d)`.

**Original LaTeX**

```latex
`\alpha_D=2\beta/(2\beta+d)`.
```

$$
\alpha_D=2\beta/(2\beta+d)
$$

**Lean**

```lean
def dataScalingExponent (β d : ℝ) : ℝ :=
  (2 * β) / (2 * β + d)
```

<a id="mathformer-autoformalizedtransformerscalinglaws-lipschitzdatascalingexponent"></a>

## `Mathformer.AutoformalizedTransformerScalingLaws.lipschitzDataScalingExponent`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean:169](../../../../../backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean#L169)

**Original Source**

In the Lipschitz case, Section 3 sets `\beta=1` and gets the data exponent `2/(2+d)`.

**Original LaTeX**

```latex
if `\beta=1`, then `\alpha_D=2/(2+d)`.
```

$$
\beta=1
$$

$$
\alpha_D=2/(2+d)
$$

**Lean**

```lean
def lipschitzDataScalingExponent (d : ℝ) : ℝ :=
  2 / (2 + d)
```

<a id="mathformer-autoformalizedtransformerscalinglaws-modelscalingexponent"></a>

## `Mathformer.AutoformalizedTransformerScalingLaws.modelScalingExponent`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean:176](../../../../../backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean#L176)

**Original Source**

Section 3 states the model-size exponent as `2/d`.

**Original LaTeX**

```latex
`\alpha_N=2/d`.
```

$$
\alpha_N=2/d
$$

**Lean**

```lean
def modelScalingExponent (d : ℝ) : ℝ :=
  2 / d
```

<a id="mathformer-autoformalizedtransformerscalinglaws-datascalingexponent-lipschitz"></a>

## `Mathformer.AutoformalizedTransformerScalingLaws.dataScalingExponent_lipschitz`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean:186](../../../../../backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean#L186)

**Generated Notes**

The formula `2\beta/(2\beta+d)` specializes to `2/(2+d)` when `\beta=1`. In Lean this is the equality between `dataScalingExponent 1 d` and `lipschitzDataScalingExponent d`.

**Generated LaTeX**

```latex
`(2\cdot 1)/(2\cdot 1+d)=2/(2+d)`.
```

$$
(2\cdot 1)/(2\cdot 1+d)=2/(2+d)
$$

**Lean**

```lean
theorem dataScalingExponent_lipschitz (d : ℝ) :
    dataScalingExponent 1 d = lipschitzDataScalingExponent d := by
  simp [dataScalingExponent, lipschitzDataScalingExponent]
```

<a id="mathformer-autoformalizedtransformerscalinglaws-statisticaltheoryconclusion"></a>

## `Mathformer.AutoformalizedTransformerScalingLaws.StatisticalTheoryConclusion`

- Kind: `structure`
- Source line: [backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean:198](../../../../../backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean#L198)

**Original Source**

Theorem 1 bounds the expected squared `L^2(Q)` generalization error of the empirical risk minimizer by the power `n^{-2\beta/(2\beta+d)}`, up to dimension factors and logarithms.

**Original LaTeX**

```latex
`\mathbb E\int_{\mathcal M}
(\widehat T_n(x)-f(x))^2\,dQ \le \widetilde O(Dd^2
n^{-2\beta/(2\beta+d)})`.
```

$$
\mathbb E\int_{\mathcal M} (\widehat T_n(x)-f(x))^2\,dQ \le \widetilde O(Dd^2 n^{-2\beta/(2\beta+d)})
$$

**Lean**

```lean
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
```

<a id="mathformer-autoformalizedtransformerscalinglaws-transformerapproximationwitness"></a>

## `Mathformer.AutoformalizedTransformerScalingLaws.TransformerApproximationWitness`

- Kind: `structure`
- Source line: [backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean:218](../../../../../backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean#L218)

**Original Source**

Theorem 2 states that for every `\epsilon` in `(0,1)` there is a transformer network approximating any target satisfying Assumption 2 within `\epsilon` in supremum norm.

**Original LaTeX**

```latex
for every `\epsilon\in(0,1)`, there is
`T_\theta\in\mathcal T(...)` such that
`\|T_\theta-f\|_{L^\infty(\mathcal M)}\le\epsilon`.
```

$$
\epsilon\in(0,1)
$$

$$
T_\theta\in\mathcal T(...)
$$

$$
\|T_\theta-f\|_{L^\infty(\mathcal M)}\le\epsilon
$$

**Lean**

```lean
structure TransformerApproximationWitness
    {M : Type u} (f : M → ℝ) (β d D ε : ℝ) where
  networkClass : TransformerNetworkClass
  realizedFunction : M → ℝ
  parameterBounds : TheoremTwoParameterBounds β d D ε networkClass
  supNormError : SupNormErrorAtMost realizedFunction f ε
```

<a id="mathformer-autoformalizedtransformerscalinglaws-approximationtheoryconclusion"></a>

## `Mathformer.AutoformalizedTransformerScalingLaws.ApproximationTheoryConclusion`

- Kind: `structure`
- Source line: [backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean:231](../../../../../backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean#L231)

**Original Source**

Theorem 2 is the paper's transformer approximation result for Holder functions on the manifold.

**Original LaTeX**

```latex
`\forall\epsilon\in(0,1), \exists T_\theta,
\|T_\theta-f\|_\infty\le\epsilon` with the stated transformer parameter rates.
```

$$
\forall\epsilon\in(0,1), \exists T_\theta, \|T_\theta-f\|_\infty\le\epsilon
$$

**Lean**

```lean
structure ApproximationTheoryConclusion
    {M : Type u} (f : M → ℝ) (β d D : ℝ) where
  manifoldAssumptions : ManifoldAssumptions M
  targetAssumptions : TargetFunctionAssumptions f β
  existsTransformerApproximation :
    ∀ ε : ℝ, 0 < ε → ε < 1 →
      Nonempty (TransformerApproximationWitness f β d D ε)
```

<a id="mathformer-autoformalizedtransformerscalinglaws-sectionthreescalingconclusion"></a>

## `Mathformer.AutoformalizedTransformerScalingLaws.SectionThreeScalingConclusion`

- Kind: `structure`
- Source line: [backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean:248](../../../../../backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean#L248)

**Original Source**

Section 3 reads Theorem 1 in the Lipschitz case as a data-size scaling law with exponent `\alpha_D=2/(2+d)`. Section 3 also records the model-size scaling exponent as `\alpha_N=2/d`.

**Original LaTeX**

```latex
`\mathrm{error}(n)\lesssim n^{-\alpha_D}` with
`\alpha_D=2/(2+d)`.
`\alpha_N=2/d`.
```

$$
\mathrm{error}(n)\lesssim n^{-\alpha_D}
$$

$$
\alpha_D=2/(2+d)
$$

$$
\alpha_N=2/d
$$

**Lean**

```lean
structure SectionThreeScalingConclusion
    (d : ℝ) (squaredGeneralizationError modelApproximationError : ℕ → ℝ) :
    Type where
  lipschitzDataScaling :
    PowerLawUpperBound squaredGeneralizationError (lipschitzDataScalingExponent d)
  modelSizeScaling :
    PowerLawUpperBound modelApproximationError (modelScalingExponent d)
```

<a id="mathformer-autoformalizedtransformerscalinglaws-theorem1-generalization-power-law"></a>

## `Mathformer.AutoformalizedTransformerScalingLaws.theorem1_generalization_power_law`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean:262](../../../../../backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean#L262)

**Original Source**

Theorem 1 supplies the statistical power-law generalization bound.

**Original LaTeX**

```latex
`\mathbb E\|\widehat T_n-f\|_{L^2(Q)}^2
\lesssim n^{-2\beta/(2\beta+d)}`.
```

$$
\mathbb E\|\widehat T_n-f\|_{L^2(Q)}^2 \lesssim n^{-2\beta/(2\beta+d)}
$$

**Lean**

```lean
theorem theorem1_generalization_power_law
    {M : Type u} {f : M → ℝ} {β d D : ℝ}
    {networkAtSampleSize : ℕ → TransformerNetworkClass}
    {squaredGeneralizationError : ℕ → ℝ}
    (h : StatisticalTheoryConclusion f β d D networkAtSampleSize
      squaredGeneralizationError) :
    PowerLawUpperBound squaredGeneralizationError (dataScalingExponent β d) := by
  have powerLaw := h.squaredGeneralizationPowerLaw
  exact powerLaw
```

<a id="mathformer-autoformalizedtransformerscalinglaws-theorem2-exists-transformer-approximation"></a>

## `Mathformer.AutoformalizedTransformerScalingLaws.theorem2_exists_transformer_approximation`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean:281](../../../../../backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean#L281)

**Original Source**

Theorem 2 supplies a transformer approximation witness for every accuracy `\epsilon` in `(0,1)`.

**Original LaTeX**

```latex
`\forall\epsilon\in(0,1),\exists T_\theta,
\|T_\theta-f\|_\infty\le\epsilon`.
```

$$
\forall\epsilon\in(0,1),\exists T_\theta, \|T_\theta-f\|_\infty\le\epsilon
$$

**Generated Notes**

Lean encodes the existential transformer witness as `∃ _ : TransformerApproximationWitness f β d D ε, True`, derived from the paper-level `Nonempty` witness package.

**Lean**

```lean
theorem theorem2_exists_transformer_approximation
    {M : Type u} {f : M → ℝ} {β d D : ℝ}
    (h : ApproximationTheoryConclusion f β d D) :
    ∀ ε : ℝ, 0 < ε → ε < 1 →
      ∃ _ : TransformerApproximationWitness f β d D ε, True := by
  intro ε hε_pos hε_lt_one
  rcases h.existsTransformerApproximation ε hε_pos hε_lt_one with ⟨witness⟩
  exact ⟨witness, trivial⟩
```

<a id="mathformer-autoformalizedtransformerscalinglaws-theorem1-lipschitz-data-scaling"></a>

## `Mathformer.AutoformalizedTransformerScalingLaws.theorem1_lipschitz_data_scaling`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean:295](../../../../../backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean#L295)

**Original Source**

When the target is Lipschitz (`\beta=1`), Theorem 1 predicts the Section 3 data exponent `\alpha_D=2/(2+d)`.

**Original LaTeX**

```latex
`\alpha_D=2/(2+d)`.
```

$$
\alpha_D=2/(2+d)
$$

**Lean**

```lean
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
```

<a id="mathformer-autoformalizedtransformerscalinglaws-section3-model-scaling-power-law"></a>

## `Mathformer.AutoformalizedTransformerScalingLaws.section3_model_scaling_power_law`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean:313](../../../../../backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean#L313)

**Original Source**

Section 3 records the model-size scaling exponent as `\alpha_N=2/d`.

**Original LaTeX**

```latex
`\alpha_N=2/d`.
```

$$
\alpha_N=2/d
$$

**Generated Notes**

The Lean conclusion is the `PowerLawUpperBound` for `modelApproximationError` with exponent `modelScalingExponent d`.

**Lean**

```lean
theorem section3_model_scaling_power_law
    {d : ℝ} {squaredGeneralizationError modelApproximationError : ℕ → ℝ}
    (h : SectionThreeScalingConclusion d squaredGeneralizationError
      modelApproximationError) :
    PowerLawUpperBound modelApproximationError (modelScalingExponent d) := by
  have modelPowerLaw := h.modelSizeScaling
  exact modelPowerLaw
```

<a id="mathformer-autoformalizedtransformerscalinglaws-section3-data-scaling-power-law"></a>

## `Mathformer.AutoformalizedTransformerScalingLaws.section3_data_scaling_power_law`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean:328](../../../../../backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean#L328)

**Original Source**

Section 3 records the Lipschitz data-size exponent as `\alpha_D=2/(2+d)`.

**Original LaTeX**

```latex
`\alpha_D=2/(2+d)`.
```

$$
\alpha_D=2/(2+d)
$$

**Generated Notes**

The Lean conclusion is the `PowerLawUpperBound` for `squaredGeneralizationError` with exponent `lipschitzDataScalingExponent d`.

**Lean**

```lean
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
```
