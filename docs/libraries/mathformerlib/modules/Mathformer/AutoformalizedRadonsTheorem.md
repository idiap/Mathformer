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

# `Mathformer.AutoformalizedRadonsTheorem`

[Back to index](../../INDEX.md)

## Metadata

- Source: [backends/lean/Mathformer/AutoformalizedRadonsTheorem.lean](../../../../../backends/lean/Mathformer/AutoformalizedRadonsTheorem.lean)
- Status: `candidate`
- SHA-256: `225b305dec6fb185abff44e221c3bc995e1e2576b18e36ba1df8f6556f5620f3`
- Declarations: `7`

## Imports

```lean
import Mathlib.Analysis.Convex.Radon
import Mathlib.Analysis.InnerProductSpace.PiL2
```

## Module Source Notes

**Original Source**

Radon's theorem says that any set of `d + 2` points in real `d`-dimensional Euclidean space can be partitioned into two disjoint parts whose convex hulls intersect.

**Original LaTeX**

```latex
for `S \subset \mathbb{R}^d` with
`|S| = d + 2`, there are `S_1,S_2` partitioning `S` such that
`\operatorname{conv}(S_1) \cap \operatorname{conv}(S_2) \ne \varnothing`.

Mathlib grounding: mathlib already proves the stronger affine-dependent-family
version as `Convex.radon_partition`. This module packages that theorem, exposes
an intersection point, and specializes it to `d + 2` indexed points in
`EuclideanSpace ℝ (Fin d)`.
```

$$
S \subset \mathbb{R}^d
$$

$$
|S| = d + 2
$$

$$
S_1,S_2
$$

## Declarations

- [`Mathformer.AutoformalizedRadonsTheorem.radon_partition_affine_dependent`](#mathformer-autoformalizedradonstheorem-radon-partition-affine-dependent) (theorem, line 44)
- [`Mathformer.AutoformalizedRadonsTheorem.radon_partition_affine_dependent_point`](#mathformer-autoformalizedradonstheorem-radon-partition-affine-dependent-point) (theorem, line 60)
- [`Mathformer.AutoformalizedRadonsTheorem.not_affineIndependent_of_finrank_add_one_lt_card`](#mathformer-autoformalizedradonstheorem-not-affineindependent-of-finrank-add-one-lt-card) (theorem, line 76)
- [`Mathformer.AutoformalizedRadonsTheorem.radon_partition_of_finrank_add_one_lt_card`](#mathformer-autoformalizedradonstheorem-radon-partition-of-finrank-add-one-lt-card) (theorem, line 96)
- [`Mathformer.AutoformalizedRadonsTheorem.radon_partition_of_finrank_add_one_lt_card_point`](#mathformer-autoformalizedradonstheorem-radon-partition-of-finrank-add-one-lt-card-point) (theorem, line 112)
- [`Mathformer.AutoformalizedRadonsTheorem.radon_partition_euclidean_fin`](#mathformer-autoformalizedradonstheorem-radon-partition-euclidean-fin) (theorem, line 129)
- [`Mathformer.AutoformalizedRadonsTheorem.radon_partition_euclidean_fin_point`](#mathformer-autoformalizedradonstheorem-radon-partition-euclidean-fin-point) (theorem, line 144)

<a id="mathformer-autoformalizedradonstheorem-radon-partition-affine-dependent"></a>

## `Mathformer.AutoformalizedRadonsTheorem.radon_partition_affine_dependent`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedRadonsTheorem.lean:44](../../../../../backends/lean/Mathformer/AutoformalizedRadonsTheorem.lean#L44)

**Generated LaTeX**

```latex
if `(f_i)_{i \in \iota}` is affinely dependent,
then there is `I \subseteq \iota` such that
`\operatorname{conv}(f(I)) \cap \operatorname{conv}(f(I^c)) \ne \varnothing`.
```

$$
(f_i)_{i \in \iota}
$$

$$
I \subseteq \iota
$$

$$
\operatorname{conv}(f(I)) \cap \operatorname{conv}(f(I^c)) \ne \varnothing
$$

**Comment**

Mathlib grounding (NL): This is Radon's theorem in mathlib's affine-dependent form.

**Lean**

```lean
theorem radon_partition_affine_dependent
    {ι : Type uι} {𝕜 : Type u𝕜} {E : Type uE}
    [Field 𝕜] [LinearOrder 𝕜] [IsStrictOrderedRing 𝕜]
    [AddCommGroup E] [Module 𝕜 E]
    {f : ι → E}
    (h : ¬ AffineIndependent 𝕜 f) :
    ∃ I : Set ι, (convexHull 𝕜 (f '' I) ∩ convexHull 𝕜 (f '' Iᶜ)).Nonempty := by
  exact Convex.radon_partition h
```

<a id="mathformer-autoformalizedradonstheorem-radon-partition-affine-dependent-point"></a>

## `Mathformer.AutoformalizedRadonsTheorem.radon_partition_affine_dependent_point`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedRadonsTheorem.lean:60](../../../../../backends/lean/Mathformer/AutoformalizedRadonsTheorem.lean#L60)

**Generated Notes**

This unpacks the nonempty intersection into an explicit Radon point.

**Generated LaTeX**

```latex
there exist `I \subseteq \iota` and `p \in E`
with `p \in \operatorname{conv}(f(I))` and
`p \in \operatorname{conv}(f(I^c))`.
```

$$
I \subseteq \iota
$$

$$
p \in E
$$

$$
p \in \operatorname{conv}(f(I))
$$

**Lean**

```lean
theorem radon_partition_affine_dependent_point
    {ι : Type uι} {𝕜 : Type u𝕜} {E : Type uE}
    [Field 𝕜] [LinearOrder 𝕜] [IsStrictOrderedRing 𝕜]
    [AddCommGroup E] [Module 𝕜 E]
    {f : ι → E}
    (h : ¬ AffineIndependent 𝕜 f) :
    ∃ I : Set ι, ∃ p : E, p ∈ convexHull 𝕜 (f '' I) ∧ p ∈ convexHull 𝕜 (f '' Iᶜ) := by
  rcases radon_partition_affine_dependent (f := f) h with ⟨I, p, hp⟩
  exact ⟨I, p, hp.1, hp.2⟩
```

<a id="mathformer-autoformalizedradonstheorem-not-affineindependent-of-finrank-add-one-lt-card"></a>

## `Mathformer.AutoformalizedRadonsTheorem.not_affineIndependent_of_finrank_add_one_lt_card`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedRadonsTheorem.lean:76](../../../../../backends/lean/Mathformer/AutoformalizedRadonsTheorem.lean#L76)

**Generated Notes**

A finite family with more indices than `finrank E + 1` cannot be affinely independent.

**Generated LaTeX**

```latex
if `\operatorname{finrank}_{\mathbb{k}} E + 1 < |\iota|`,
then `(f_i)_{i \in \iota}` is not affinely independent.
```

$$
\operatorname{finrank}_{\mathbb{k}} E + 1 < |\iota|
$$

$$
(f_i)_{i \in \iota}
$$

**Lean**

```lean
theorem not_affineIndependent_of_finrank_add_one_lt_card
    {ι : Type uι} {𝕜 : Type u𝕜} {E : Type uE}
    [Field 𝕜] [AddCommGroup E] [Module 𝕜 E] [Module.Finite 𝕜 E] [Fintype ι]
    (f : ι → E)
    (hcard : Module.finrank 𝕜 E + 1 < Fintype.card ι) :
    ¬ AffineIndependent 𝕜 f := by
  intro hf
  have hspan : Module.finrank 𝕜 (vectorSpan 𝕜 (Set.range f)) ≤ Module.finrank 𝕜 E := by
    exact Submodule.finrank_le (vectorSpan 𝕜 (Set.range f))
  have hle : Fintype.card ι ≤ Module.finrank 𝕜 E + 1 := by
    exact hf.card_le_finrank_succ.trans (Nat.add_le_add_right hspan 1)
  exact (not_lt_of_ge hle) hcard
```

<a id="mathformer-autoformalizedradonstheorem-radon-partition-of-finrank-add-one-lt-card"></a>

## `Mathformer.AutoformalizedRadonsTheorem.radon_partition_of_finrank_add_one_lt_card`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedRadonsTheorem.lean:96](../../../../../backends/lean/Mathformer/AutoformalizedRadonsTheorem.lean#L96)

**Generated Notes**

Combining the finite-dimensional affine-dependence bound with mathlib's Radon partition gives the general finite-family form.

**Generated LaTeX**

```latex
if `\operatorname{finrank}_{\mathbb{k}} E + 1 < |\iota|`,
then some `I` satisfies
`\operatorname{conv}(f(I)) \cap \operatorname{conv}(f(I^c)) \ne \varnothing`.
```

$$
\operatorname{finrank}_{\mathbb{k}} E + 1 < |\iota|
$$

$$
I
$$

$$
\operatorname{conv}(f(I)) \cap \operatorname{conv}(f(I^c)) \ne \varnothing
$$

**Lean**

```lean
theorem radon_partition_of_finrank_add_one_lt_card
    {ι : Type uι} {𝕜 : Type u𝕜} {E : Type uE}
    [Field 𝕜] [LinearOrder 𝕜] [IsStrictOrderedRing 𝕜]
    [AddCommGroup E] [Module 𝕜 E] [Module.Finite 𝕜 E] [Fintype ι]
    {f : ι → E}
    (hcard : Module.finrank 𝕜 E + 1 < Fintype.card ι) :
    ∃ I : Set ι, (convexHull 𝕜 (f '' I) ∩ convexHull 𝕜 (f '' Iᶜ)).Nonempty := by
  exact radon_partition_affine_dependent (f := f)
    (not_affineIndependent_of_finrank_add_one_lt_card f hcard)
```

<a id="mathformer-autoformalizedradonstheorem-radon-partition-of-finrank-add-one-lt-card-point"></a>

## `Mathformer.AutoformalizedRadonsTheorem.radon_partition_of_finrank_add_one_lt_card_point`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedRadonsTheorem.lean:112](../../../../../backends/lean/Mathformer/AutoformalizedRadonsTheorem.lean#L112)

**Generated Notes**

This is the finite-family Radon partition with the intersection witness made explicit.

**Generated LaTeX**

```latex
there exist `I \subseteq \iota` and `p \in E`
with `p \in \operatorname{conv}(f(I)) \cap \operatorname{conv}(f(I^c))`.
```

$$
I \subseteq \iota
$$

$$
p \in E
$$

$$
p \in \operatorname{conv}(f(I)) \cap \operatorname{conv}(f(I^c))
$$

**Lean**

```lean
theorem radon_partition_of_finrank_add_one_lt_card_point
    {ι : Type uι} {𝕜 : Type u𝕜} {E : Type uE}
    [Field 𝕜] [LinearOrder 𝕜] [IsStrictOrderedRing 𝕜]
    [AddCommGroup E] [Module 𝕜 E] [Module.Finite 𝕜 E] [Fintype ι]
    {f : ι → E}
    (hcard : Module.finrank 𝕜 E + 1 < Fintype.card ι) :
    ∃ I : Set ι, ∃ p : E, p ∈ convexHull 𝕜 (f '' I) ∧ p ∈ convexHull 𝕜 (f '' Iᶜ) := by
  exact radon_partition_affine_dependent_point (f := f)
    (not_affineIndependent_of_finrank_add_one_lt_card f hcard)
```

<a id="mathformer-autoformalizedradonstheorem-radon-partition-euclidean-fin"></a>

## `Mathformer.AutoformalizedRadonsTheorem.radon_partition_euclidean_fin`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedRadonsTheorem.lean:129](../../../../../backends/lean/Mathformer/AutoformalizedRadonsTheorem.lean#L129)

**Original Source**

Any `d + 2` points in `d`-dimensional Euclidean space can be partitioned so that the convex hulls of the two parts intersect.

**Original LaTeX**

```latex
for `f : \operatorname{Fin}(d+2) \to \mathbb{R}^d`,
there is `I \subseteq \operatorname{Fin}(d+2)` such that
`\operatorname{conv}(f(I)) \cap \operatorname{conv}(f(I^c)) \ne \varnothing`.
```

$$
f : \operatorname{Fin}(d+2) \to \mathbb{R}^d
$$

$$
I \subseteq \operatorname{Fin}(d+2)
$$

$$
\operatorname{conv}(f(I)) \cap \operatorname{conv}(f(I^c)) \ne \varnothing
$$

**Lean**

```lean
theorem radon_partition_euclidean_fin
    {d : ℕ}
    (f : Fin (d + 2) → EuclideanSpace ℝ (Fin d)) :
    ∃ I : Set (Fin (d + 2)),
      (convexHull ℝ (f '' I) ∩ convexHull ℝ (f '' Iᶜ)).Nonempty := by
  apply radon_partition_of_finrank_add_one_lt_card (f := f)
  simp
```

<a id="mathformer-autoformalizedradonstheorem-radon-partition-euclidean-fin-point"></a>

## `Mathformer.AutoformalizedRadonsTheorem.radon_partition_euclidean_fin_point`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedRadonsTheorem.lean:144](../../../../../backends/lean/Mathformer/AutoformalizedRadonsTheorem.lean#L144)

**Original Source**

The Radon partition has a common point in the two convex hulls.

**Original LaTeX**

```latex
there exist `I` and `p \in \mathbb{R}^d` such that
`p \in \operatorname{conv}(f(I))` and
`p \in \operatorname{conv}(f(I^c))`.
```

$$
I
$$

$$
p \in \mathbb{R}^d
$$

$$
p \in \operatorname{conv}(f(I))
$$

**Lean**

```lean
theorem radon_partition_euclidean_fin_point
    {d : ℕ}
    (f : Fin (d + 2) → EuclideanSpace ℝ (Fin d)) :
    ∃ I : Set (Fin (d + 2)), ∃ p : EuclideanSpace ℝ (Fin d),
      p ∈ convexHull ℝ (f '' I) ∧ p ∈ convexHull ℝ (f '' Iᶜ) := by
  rcases radon_partition_euclidean_fin f with ⟨I, p, hp⟩
  exact ⟨I, p, hp.1, hp.2⟩

end AutoformalizedRadonsTheorem

end Mathformer
```
