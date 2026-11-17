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

# `Mathformer.AutoformalizedSazonov`

[Back to index](../../INDEX.md)

## Metadata

- Source: [backends/lean/Mathformer/AutoformalizedSazonov.lean](../../../../../backends/lean/Mathformer/AutoformalizedSazonov.lean)
- Status: `candidate`
- SHA-256: `94def1e5d6783a145ed417e1a244d275228ef58395fae51e383e464eb974bc35`
- Declarations: `12`

## Imports

```lean
import Mathlib.Analysis.InnerProductSpace.l2Space
import Mathlib.MeasureTheory.Measure.ProbabilityMeasure
import Mathlib.Probability.Distributions.Gaussian.Basic
```

## Module Source Notes

**Original Source**

Sazonov-type theorems characterize when a Gaussian cylindrical measure on a Hilbert space extends to a Radon probability measure after applying an operator. In the Hilbert-space formulation represented here, the key equivalence is between gamma-radonifying behavior and the Hilbert--Schmidt property.

**Original LaTeX**

```latex
for a bounded linear operator `T : G \to H` between real
Hilbert spaces, `T` is `\gamma`-radonifying iff `T` is Hilbert--Schmidt; a
basis-relative Hilbert--Schmidt criterion is
`\sum_i \|T e_i\|^2 < \infty`.
```

$$
T : G \to H
$$

$$
T
$$

$$
\gamma
$$

**Generated Notes**

This file records the cylindrical Gaussian extension component explicitly because that construction is not yet developed locally.

Generated notes: - Cylindrical Gaussian extension is represented as an explicit model component. - The scalar field is restricted to `ℝ`, matching standard Gaussian/radonifying formulations. - `IsHilbertSchmidtWith` records square summability for a chosen Hilbert basis. - Hilbert--Schmidt definitions/lemmas live in a complete-domain section (`[CompleteSpace G]`). - The existential witness in `IsHilbertSchmidt` is fixed to index universe `uG` for stable universe inference. - The Gaussian side reuses `ProbabilityTheory.IsGaussian` from mathlib. - `GammaRadonifyingModel` keeps only the cylindrical-extension component as a model field. - `IsGammaRadonifying` is kept minimal at the definition layer (`[MeasurableSpace H]` only); downstream lemma layers can add `OpensMeasurableSpace`/`BorelSpace` as needed. - `SazonovAssumptions`/Sazonov theorems are stated in the Hilbert-space layer (`CompleteSpace G`, `CompleteSpace H`). - `SazonovAssumptions` is an explicit structure of hypotheses (not a typeclass).

## Declarations

- [`Mathformer.AutoformalizedSazonov.IsHilbertSchmidtWith`](#mathformer-autoformalizedsazonov-ishilbertschmidtwith) (def, line 63)
- [`Mathformer.AutoformalizedSazonov.IsHilbertSchmidt`](#mathformer-autoformalizedsazonov-ishilbertschmidt) (def, line 72)
- [`Mathformer.AutoformalizedSazonov.IsHilbertSchmidtBasisIndependent`](#mathformer-autoformalizedsazonov-ishilbertschmidtbasisindependent) (def, line 81)
- [`Mathformer.AutoformalizedSazonov.isHilbertSchmidtWith_of_isHilbertSchmidt`](#mathformer-autoformalizedsazonov-ishilbertschmidtwith-of-ishilbertschmidt) (theorem, line 97)
- [`Mathformer.AutoformalizedSazonov.isHilbertSchmidt_iff_with`](#mathformer-autoformalizedsazonov-ishilbertschmidt-iff-with) (theorem, line 116)
- [`Mathformer.AutoformalizedSazonov.GammaRadonifyingModel`](#mathformer-autoformalizedsazonov-gammaradonifyingmodel) (structure, line 144)
- [`Mathformer.AutoformalizedSazonov.IsGammaRadonifying`](#mathformer-autoformalizedsazonov-isgammaradonifying) (def, line 162)
- [`Mathformer.AutoformalizedSazonov.SazonovAssumptions`](#mathformer-autoformalizedsazonov-sazonovassumptions) (structure, line 183)
- [`Mathformer.AutoformalizedSazonov.isHilbertSchmidt_iff_with_of_sazonovAssumptions`](#mathformer-autoformalizedsazonov-ishilbertschmidt-iff-with-of-sazonovassumptions) (theorem, line 200)
- [`Mathformer.AutoformalizedSazonov.sazonov_hilbertSchmidt_to_gammaRadonifying`](#mathformer-autoformalizedsazonov-sazonov-hilbertschmidt-to-gammaradonifying) (theorem, line 214)
- [`Mathformer.AutoformalizedSazonov.sazonov_gammaRadonifying_to_hilbertSchmidt`](#mathformer-autoformalizedsazonov-sazonov-gammaradonifying-to-hilbertschmidt) (theorem, line 229)
- [`Mathformer.AutoformalizedSazonov.sazonov_iff`](#mathformer-autoformalizedsazonov-sazonov-iff) (theorem, line 244)

<a id="mathformer-autoformalizedsazonov-ishilbertschmidtwith"></a>

## `Mathformer.AutoformalizedSazonov.IsHilbertSchmidtWith`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedSazonov.lean:63](../../../../../backends/lean/Mathformer/AutoformalizedSazonov.lean#L63)

**Original Source**

A Hilbert--Schmidt operator has square-summable images of an orthonormal Hilbert basis.

**Original LaTeX**

```latex
for a Hilbert basis `(e_i)`, `\sum_i \|T e_i\|^2 < \infty`.
```

$$
(e_i)
$$

$$
\sum_i \|T e_i\|^2 < \infty
$$

**Lean**

```lean
def IsHilbertSchmidtWith {ι : Type*} (b : HilbertBasis ι ℝ G) (T : G →L[ℝ] H) : Prop :=
  Summable (fun i : ι => ‖T (b i)‖ ^ (2 : ℕ))
```

<a id="mathformer-autoformalizedsazonov-ishilbertschmidt"></a>

## `Mathformer.AutoformalizedSazonov.IsHilbertSchmidt`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedSazonov.lean:72](../../../../../backends/lean/Mathformer/AutoformalizedSazonov.lean#L72)

**Original Source**

A bounded linear map is Hilbert--Schmidt when the basis-relative square-summability criterion holds for some Hilbert basis.

**Original LaTeX**

```latex
`T` is Hilbert--Schmidt iff
`\exists (e_i),\ \sum_i \|T e_i\|^2 < \infty`.
```

$$
T
$$

$$
\exists (e_i),\ \sum_i \|T e_i\|^2 < \infty
$$

**Lean**

```lean
def IsHilbertSchmidt [CompleteSpace G] (T : G →L[ℝ] H) : Prop :=
  ∃ (ι : Type uG) (b : HilbertBasis ι ℝ G), IsHilbertSchmidtWith b T
```

<a id="mathformer-autoformalizedsazonov-ishilbertschmidtbasisindependent"></a>

## `Mathformer.AutoformalizedSazonov.IsHilbertSchmidtBasisIndependent`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedSazonov.lean:81](../../../../../backends/lean/Mathformer/AutoformalizedSazonov.lean#L81)

**Generated Notes**

This records basis invariance of the basis-relative Hilbert--Schmidt predicate as an explicit hypothesis.

**Generated LaTeX**

```latex
for Hilbert bases `(e_i)` and `(f_j)`,
`\sum_i \|T e_i\|^2 < \infty \iff \sum_j \|T f_j\|^2 < \infty`.
```

$$
(e_i)
$$

$$
(f_j)
$$

$$
\sum_i \|T e_i\|^2 < \infty \iff \sum_j \|T f_j\|^2 < \infty
$$

**Lean**

```lean
def IsHilbertSchmidtBasisIndependent [CompleteSpace G] : Prop :=
  ∀ {ι κ : Type uG}
    (b : HilbertBasis ι ℝ G)
    (c : HilbertBasis κ ℝ G)
    (T : G →L[ℝ] H),
    IsHilbertSchmidtWith b T ↔ IsHilbertSchmidtWith c T
```

<a id="mathformer-autoformalizedsazonov-ishilbertschmidtwith-of-ishilbertschmidt"></a>

## `Mathformer.AutoformalizedSazonov.isHilbertSchmidtWith_of_isHilbertSchmidt`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedSazonov.lean:97](../../../../../backends/lean/Mathformer/AutoformalizedSazonov.lean#L97)

**Generated Notes**

From existential Hilbert--Schmidt and basis independence, the criterion holds for any chosen Hilbert basis.

**Generated LaTeX**

```latex
if `\exists (f_j),\sum_j\|T f_j\|^2<\infty`,
then for every basis `(e_i)`, `\sum_i\|T e_i\|^2<\infty`.
Operational consequence of basis independence: from existential
Hilbert--Schmidt and one basis-independence hypothesis,
we can recover the basis-relative predicate on any chosen Hilbert basis.
```

$$
\exists (f_j),\sum_j\|T f_j\|^2<\infty
$$

$$
(e_i)
$$

$$
\sum_i\|T e_i\|^2<\infty
$$

**Lean**

```lean
theorem isHilbertSchmidtWith_of_isHilbertSchmidt
    [CompleteSpace G]
    {ι : Type uG}
    (b : HilbertBasis ι ℝ G)
    (hBI : IsHilbertSchmidtBasisIndependent (G := G) (H := H))
    {T : G →L[ℝ] H}
    (hHS : IsHilbertSchmidt T) :
    IsHilbertSchmidtWith b T := by
  rcases hHS with ⟨κ, c, hc⟩
  exact (hBI c b T).1 hc
```

<a id="mathformer-autoformalizedsazonov-ishilbertschmidt-iff-with"></a>

## `Mathformer.AutoformalizedSazonov.isHilbertSchmidt_iff_with`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedSazonov.lean:116](../../../../../backends/lean/Mathformer/AutoformalizedSazonov.lean#L116)

**Generated Notes**

Under basis independence, the existential and fixed-basis Hilbert--Schmidt formulations are equivalent.

**Generated LaTeX**

```latex
`T` is Hilbert--Schmidt iff
`\sum_i \|T e_i\|^2 < \infty` for the chosen basis `(e_i)`.
Under basis independence, existential Hilbert--Schmidt is equivalent to
the basis-relative predicate on any fixed Hilbert basis.
```

$$
T
$$

$$
\sum_i \|T e_i\|^2 < \infty
$$

$$
(e_i)
$$

**Lean**

```lean
theorem isHilbertSchmidt_iff_with
    [CompleteSpace G]
    {ι : Type uG}
    (b : HilbertBasis ι ℝ G)
    (hBI : IsHilbertSchmidtBasisIndependent (G := G) (H := H))
    (T : G →L[ℝ] H) :
    IsHilbertSchmidt T ↔ IsHilbertSchmidtWith b T := by
  constructor
  · intro hHS
    exact isHilbertSchmidtWith_of_isHilbertSchmidt (b := b) hBI hHS
  · intro hb
    exact ⟨ι, b, hb⟩

end HilbertSchmidt

section Gamma

variable [MeasurableSpace H]
```

<a id="mathformer-autoformalizedsazonov-gammaradonifyingmodel"></a>

## `Mathformer.AutoformalizedSazonov.GammaRadonifyingModel`

- Kind: `structure`
- Source line: [backends/lean/Mathformer/AutoformalizedSazonov.lean:144](../../../../../backends/lean/Mathformer/AutoformalizedSazonov.lean#L144)

**Generated Notes**

This structure isolates the cylindrical Gaussian extension component that is not fully developed in the local mathlib environment.

**Generated LaTeX**

```latex
it provides the relation saying the Gaussian
cylindrical pushforward along `T` extends to a probability measure `\nu` on `H`.
Model for the Gaussian/cylindrical side used in Sazonov-style statements.
Only the cylindrical-extension component is represented by a field here. Gaussianity is stated with
`ProbabilityTheory.IsGaussian` directly.
```

$$
T
$$

$$
\nu
$$

$$
H
$$

**Lean**

```lean
structure GammaRadonifyingModel where
  /--
  Explicit model point of this file:
  witness that the pushforward of the canonical Gaussian cylindrical object along `T`
  extends to the probability measure `ν` on `H`.
  -/
  HasCanonicalGaussianCylinderExtension :
    (G →L[ℝ] H) → MeasureTheory.ProbabilityMeasure H → Prop

variable (M : GammaRadonifyingModel (G := G) (H := H))
```

<a id="mathformer-autoformalizedsazonov-isgammaradonifying"></a>

## `Mathformer.AutoformalizedSazonov.IsGammaRadonifying`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedSazonov.lean:162](../../../../../backends/lean/Mathformer/AutoformalizedSazonov.lean#L162)

**Original Source**

A map is gamma-radonifying when the relevant Gaussian cylindrical object extends to a Gaussian probability measure after applying the map.

**Original LaTeX**

```latex
`T` is `\gamma`-radonifying iff there exists a Gaussian
probability measure `\nu` on `H` extending the canonical Gaussian cylindrical
pushforward along `T`.
```

$$
T
$$

$$
\gamma
$$

$$
\nu
$$

**Lean**

```lean
def IsGammaRadonifying (T : G →L[ℝ] H) : Prop :=
  ∃ ν : MeasureTheory.ProbabilityMeasure H,
    ProbabilityTheory.IsGaussian (ν : MeasureTheory.Measure H) ∧
    M.HasCanonicalGaussianCylinderExtension T ν

/-!
`IsGammaRadonifying` uses only `[MeasurableSpace H]` at the definition layer.
When proving nontrivial Gaussian-map or characteristic-function lemmas downstream, it is expected
to strengthen assumptions (typically to `OpensMeasurableSpace` and/or `BorelSpace`).
-/

section Hilbert
```

<a id="mathformer-autoformalizedsazonov-sazonovassumptions"></a>

## `Mathformer.AutoformalizedSazonov.SazonovAssumptions`

- Kind: `structure`
- Source line: [backends/lean/Mathformer/AutoformalizedSazonov.lean:183](../../../../../backends/lean/Mathformer/AutoformalizedSazonov.lean#L183)

**Generated Notes**

This assumption package records the pieces needed to state the Sazonov equivalence without asserting unavailable analytic development as global postulates.

**Generated LaTeX**

```latex
it contains basis independence and both directions
`HilbertSchmidt(T) \Rightarrow \gamma\text{-radonifying}(T)` and
`\gamma\text{-radonifying}(T) \Rightarrow HilbertSchmidt(T)`.
```

$$
HilbertSchmidt(T) \Rightarrow \gamma\text{-radonifying}(T)
$$

$$
\gamma\text{-radonifying}(T) \Rightarrow HilbertSchmidt(T)
$$

**Lean**

```lean
structure SazonovAssumptions [CompleteSpace G] [CompleteSpace H] : Prop where
  /-- Basis-independence interface for Hilbert--Schmidt summability. -/
  hilbertSchmidt_basisIndependent :
    IsHilbertSchmidtBasisIndependent (G := G) (H := H)
  hilbertSchmidt_to_gammaRadonifying :
    ∀ (T : G →L[ℝ] H), IsHilbertSchmidt T → IsGammaRadonifying M T
  gammaRadonifying_to_hilbertSchmidt :
    ∀ (T : G →L[ℝ] H), IsGammaRadonifying M T → IsHilbertSchmidt T
```

<a id="mathformer-autoformalizedsazonov-ishilbertschmidt-iff-with-of-sazonovassumptions"></a>

## `Mathformer.AutoformalizedSazonov.isHilbertSchmidt_iff_with_of_sazonovAssumptions`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedSazonov.lean:200](../../../../../backends/lean/Mathformer/AutoformalizedSazonov.lean#L200)

**Generated Notes**

Sazonov assumptions imply the fixed-basis and existential Hilbert--Schmidt criteria agree.

**Generated LaTeX**

```latex
under the assumptions,
`HilbertSchmidt(T) \iff \sum_i \|T e_i\|^2 < \infty`.
Under Sazonov assumptions, existential Hilbert--Schmidt is equivalent to
the basis-relative criterion on any fixed Hilbert basis.
```

$$
HilbertSchmidt(T) \iff \sum_i \|T e_i\|^2 < \infty
$$

**Lean**

```lean
theorem isHilbertSchmidt_iff_with_of_sazonovAssumptions
    [CompleteSpace G] [CompleteSpace H]
    (hS : SazonovAssumptions (M := M))
    {ι : Type uG}
    (b : HilbertBasis ι ℝ G)
    (T : G →L[ℝ] H) :
    IsHilbertSchmidt T ↔ IsHilbertSchmidtWith b T := by
  exact isHilbertSchmidt_iff_with b hS.hilbertSchmidt_basisIndependent T
```

<a id="mathformer-autoformalizedsazonov-sazonov-hilbertschmidt-to-gammaradonifying"></a>

## `Mathformer.AutoformalizedSazonov.sazonov_hilbertSchmidt_to_gammaRadonifying`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedSazonov.lean:214](../../../../../backends/lean/Mathformer/AutoformalizedSazonov.lean#L214)

**Original Source**

The Hilbert--Schmidt condition implies the gamma-radonifying condition.

**Original LaTeX**

```latex
`T \in HS(G,H) \Rightarrow T` is `\gamma`-radonifying.
```

$$
T \in HS(G,H) \Rightarrow T
$$

$$
\gamma
$$

**Lean**

```lean
theorem sazonov_hilbertSchmidt_to_gammaRadonifying
    [CompleteSpace G] [CompleteSpace H]
    (hS : SazonovAssumptions (M := M))
    (T : G →L[ℝ] H) :
    IsHilbertSchmidt T →
    IsGammaRadonifying M T := by
  intro hHS
  have gammaFromHilbert := hS.hilbertSchmidt_to_gammaRadonifying
  exact gammaFromHilbert T hHS
```

<a id="mathformer-autoformalizedsazonov-sazonov-gammaradonifying-to-hilbertschmidt"></a>

## `Mathformer.AutoformalizedSazonov.sazonov_gammaRadonifying_to_hilbertSchmidt`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedSazonov.lean:229](../../../../../backends/lean/Mathformer/AutoformalizedSazonov.lean#L229)

**Original Source**

The gamma-radonifying condition implies the Hilbert--Schmidt condition.

**Original LaTeX**

```latex
`T` is `\gamma`-radonifying `\Rightarrow T \in HS(G,H)`.
```

$$
T
$$

$$
\gamma
$$

$$
\Rightarrow T \in HS(G,H)
$$

**Lean**

```lean
theorem sazonov_gammaRadonifying_to_hilbertSchmidt
    [CompleteSpace G] [CompleteSpace H]
    (hS : SazonovAssumptions (M := M))
    (T : G →L[ℝ] H) :
    IsGammaRadonifying M T →
    IsHilbertSchmidt T := by
  intro hGamma
  have fromGamma := hS.gammaRadonifying_to_hilbertSchmidt
  exact fromGamma T hGamma
```

<a id="mathformer-autoformalizedsazonov-sazonov-iff"></a>

## `Mathformer.AutoformalizedSazonov.sazonov_iff`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedSazonov.lean:244](../../../../../backends/lean/Mathformer/AutoformalizedSazonov.lean#L244)

**Original Source**

Sazonov's equivalence identifies gamma-radonifying operators with Hilbert--Schmidt operators in this Hilbert-space interface.

**Original LaTeX**

```latex
`T` is `\gamma`-radonifying `\iff T \in HS(G,H)`.
```

$$
T
$$

$$
\gamma
$$

$$
\iff T \in HS(G,H)
$$

**Lean**

```lean
theorem sazonov_iff
    [CompleteSpace G] [CompleteSpace H]
    (hS : SazonovAssumptions (M := M))
    (T : G →L[ℝ] H) :
    IsGammaRadonifying M T ↔
    IsHilbertSchmidt T := by
  constructor
  · exact sazonov_gammaRadonifying_to_hilbertSchmidt (M := M) hS T
  · intro hHS
    exact sazonov_hilbertSchmidt_to_gammaRadonifying (M := M) hS T hHS

end Hilbert

end Gamma

end AutoformalizedSazonov
end Mathformer
```
