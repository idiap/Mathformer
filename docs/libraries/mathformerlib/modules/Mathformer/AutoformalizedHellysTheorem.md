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

# `Mathformer.AutoformalizedHellysTheorem`

[Back to index](../../INDEX.md)

## Metadata

- Source: [backends/lean/Mathformer/AutoformalizedHellysTheorem.lean](../../../../../backends/lean/Mathformer/AutoformalizedHellysTheorem.lean)
- Status: `candidate`
- SHA-256: `0cf98cb695bfd1d465d9a64d217f3802ccd475f93a768ace8df93d17a35b02aa`
- Declarations: `12`

## Imports

```lean
import Mathlib.Analysis.Convex.Radon
import Mathlib.Analysis.InnerProductSpace.PiL2
```

## Module Source Notes

**Comment**

Interface-level autoformalization for Helly's theorem.

This module is source-aligned to `tests/latex/hellys_theorem.tex`. It exposes both abstract finite-dimensional Helly statements from mathlib and explicit Euclidean-space specializations that match the article's `R^d` presentation.

Scope: - finite families and finite sets of convex sets, - compact-family and compact-set extensions with bounded-subfamily assumptions, - classical exact-cardinality variants, - explicit `EuclideanSpace ℝ (Fin d)` formulations of the article-level statements.

## Declarations

- [`Mathformer.AutoformalizedHellysTheorem.helly_finite_classical`](#mathformer-autoformalizedhellystheorem-helly-finite-classical) (theorem, line 41)
- [`Mathformer.AutoformalizedHellysTheorem.helly_finite_small_subfamilies`](#mathformer-autoformalizedhellystheorem-helly-finite-small-subfamilies) (theorem, line 55)
- [`Mathformer.AutoformalizedHellysTheorem.helly_finite_set_classical`](#mathformer-autoformalizedhellystheorem-helly-finite-set-classical) (theorem, line 67)
- [`Mathformer.AutoformalizedHellysTheorem.helly_finite_set_small_subfamilies`](#mathformer-autoformalizedhellystheorem-helly-finite-set-small-subfamilies) (theorem, line 80)
- [`Mathformer.AutoformalizedHellysTheorem.helly_compact_family_small_subfamilies`](#mathformer-autoformalizedhellystheorem-helly-compact-family-small-subfamilies) (theorem, line 98)
- [`Mathformer.AutoformalizedHellysTheorem.helly_compact_family_classical`](#mathformer-autoformalizedhellystheorem-helly-compact-family-classical) (theorem, line 112)
- [`Mathformer.AutoformalizedHellysTheorem.helly_compact_set_small_subfamilies`](#mathformer-autoformalizedhellystheorem-helly-compact-set-small-subfamilies) (theorem, line 127)
- [`Mathformer.AutoformalizedHellysTheorem.helly_compact_set_classical`](#mathformer-autoformalizedhellystheorem-helly-compact-set-classical) (theorem, line 142)
- [`Mathformer.AutoformalizedHellysTheorem.helly_euclidean_finite_classical`](#mathformer-autoformalizedhellystheorem-helly-euclidean-finite-classical) (theorem, line 165)
- [`Mathformer.AutoformalizedHellysTheorem.helly_euclidean_finite_set_classical`](#mathformer-autoformalizedhellystheorem-helly-euclidean-finite-set-classical) (theorem, line 197)
- [`Mathformer.AutoformalizedHellysTheorem.helly_euclidean_compact_family_small_subfamilies`](#mathformer-autoformalizedhellystheorem-helly-euclidean-compact-family-small-subfamilies) (theorem, line 231)
- [`Mathformer.AutoformalizedHellysTheorem.helly_euclidean_compact_set_small_subfamilies`](#mathformer-autoformalizedhellystheorem-helly-euclidean-compact-set-small-subfamilies) (theorem, line 258)

<a id="mathformer-autoformalizedhellystheorem-helly-finite-classical"></a>

## `Mathformer.AutoformalizedHellysTheorem.helly_finite_classical`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedHellysTheorem.lean:41](../../../../../backends/lean/Mathformer/AutoformalizedHellysTheorem.lean#L41)

**Generated Notes**

Abstract finite-family classical Helly theorem: if every subfamily of size `finrank K E + 1` intersects, then the whole family intersects.

**Lean**

```lean
theorem helly_finite_classical
    {F : idx -> Set E}
    {s : Finset idx}
    (h_card : Module.finrank K E + 1 <= s.card)
    (h_convex : forall i, i ∈ s -> Convex K (F i))
    (h_inter :
      forall I, I ⊆ s -> I.card = Module.finrank K E + 1 -> (⋂ i ∈ I, F i).Nonempty) :
    (⋂ i ∈ s, F i).Nonempty := by
  have result := Convex.helly_theorem h_card h_convex h_inter
  exact result
```

<a id="mathformer-autoformalizedhellystheorem-helly-finite-small-subfamilies"></a>

## `Mathformer.AutoformalizedHellysTheorem.helly_finite_small_subfamilies`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedHellysTheorem.lean:55](../../../../../backends/lean/Mathformer/AutoformalizedHellysTheorem.lean#L55)

**Generated Notes**

Abstract finite-family Helly theorem with bounded subfamilies: if every subfamily of size at most `finrank K E + 1` intersects, then the whole family intersects.

**Lean**

```lean
theorem helly_finite_small_subfamilies
    {F : idx -> Set E}
    {s : Finset idx}
    (h_convex : forall i, i ∈ s -> Convex K (F i))
    (h_inter :
      forall I, I ⊆ s -> I.card <= Module.finrank K E + 1 -> (⋂ i ∈ I, F i).Nonempty) :
    (⋂ i ∈ s, F i).Nonempty := by
  have result := Convex.helly_theorem' h_convex h_inter
  exact result
```

<a id="mathformer-autoformalizedhellystheorem-helly-finite-set-classical"></a>

## `Mathformer.AutoformalizedHellysTheorem.helly_finite_set_classical`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedHellysTheorem.lean:67](../../../../../backends/lean/Mathformer/AutoformalizedHellysTheorem.lean#L67)

**Generated Notes**

Abstract finite-set classical Helly theorem for `Finset (Set E)`.

**Lean**

```lean
theorem helly_finite_set_classical
    {F : Finset (Set E)}
    (h_card : Module.finrank K E + 1 <= F.card)
    (h_convex : forall X, X ∈ F -> Convex K X)
    (h_inter :
      forall G : Finset (Set E),
        G ⊆ F -> G.card = Module.finrank K E + 1 -> (⋂₀ (G : Set (Set E))).Nonempty) :
    (⋂₀ (F : Set (Set E))).Nonempty := by
  have result := Convex.helly_theorem_set h_card h_convex h_inter
  exact result
```

<a id="mathformer-autoformalizedhellystheorem-helly-finite-set-small-subfamilies"></a>

## `Mathformer.AutoformalizedHellysTheorem.helly_finite_set_small_subfamilies`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedHellysTheorem.lean:80](../../../../../backends/lean/Mathformer/AutoformalizedHellysTheorem.lean#L80)

**Generated Notes**

Abstract finite-set Helly theorem with bounded subfamilies for `Finset (Set E)`.

**Lean**

```lean
theorem helly_finite_set_small_subfamilies
    {F : Finset (Set E)}
    (h_convex : forall X, X ∈ F -> Convex K X)
    (h_inter :
      forall G : Finset (Set E),
        G ⊆ F -> G.card <= Module.finrank K E + 1 -> (⋂₀ (G : Set (Set E))).Nonempty) :
    (⋂₀ (F : Set (Set E))).Nonempty := by
  classical
  have result := Convex.helly_theorem_set' h_convex h_inter
  exact result

section Compact

variable [TopologicalSpace E] [T2Space E]
```

<a id="mathformer-autoformalizedhellystheorem-helly-compact-family-small-subfamilies"></a>

## `Mathformer.AutoformalizedHellysTheorem.helly_compact_family_small_subfamilies`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedHellysTheorem.lean:98](../../../../../backends/lean/Mathformer/AutoformalizedHellysTheorem.lean#L98)

**Generated Notes**

Source-faithful compact-family Helly theorem: if every finite subfamily of size at most `finrank K E + 1` intersects, then the whole family intersects.

**Lean**

```lean
theorem helly_compact_family_small_subfamilies
    {F : idx -> Set E}
    (h_convex : forall i, Convex K (F i))
    (h_compact : forall i, IsCompact (F i))
    (h_inter :
      forall I : Finset idx, I.card <= Module.finrank K E + 1 -> (⋂ i ∈ I, F i).Nonempty) :
    (⋂ i, F i).Nonempty := by
  have result := Convex.helly_theorem_compact' h_convex h_compact h_inter
  exact result
```

<a id="mathformer-autoformalizedhellystheorem-helly-compact-family-classical"></a>

## `Mathformer.AutoformalizedHellysTheorem.helly_compact_family_classical`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedHellysTheorem.lean:112](../../../../../backends/lean/Mathformer/AutoformalizedHellysTheorem.lean#L112)

**Generated Notes**

Classical compact-family Helly theorem: if the family has at least `finrank K E + 1` sets and every subfamily of that size intersects, then the whole family intersects.

**Lean**

```lean
theorem helly_compact_family_classical
    {F : idx -> Set E}
    (h_card : (Module.finrank K E : ENat) + 1 <= ENat.card idx)
    (h_convex : forall i, Convex K (F i))
    (h_compact : forall i, IsCompact (F i))
    (h_inter :
      forall I : Finset idx,
        I.card = Module.finrank K E + 1 -> (⋂ i ∈ I, F i).Nonempty) :
    (⋂ i, F i).Nonempty := by
  have result := Convex.helly_theorem_compact h_card h_convex h_compact h_inter
  exact result
```

<a id="mathformer-autoformalizedhellystheorem-helly-compact-set-small-subfamilies"></a>

## `Mathformer.AutoformalizedHellysTheorem.helly_compact_set_small_subfamilies`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedHellysTheorem.lean:127](../../../../../backends/lean/Mathformer/AutoformalizedHellysTheorem.lean#L127)

**Generated Notes**

Source-faithful compact-set Helly theorem for `F : Set (Set E)`: if every finite subfamily of size at most `finrank K E + 1` intersects, then the whole family intersects.

**Lean**

```lean
theorem helly_compact_set_small_subfamilies
    {F : Set (Set E)}
    (h_convex : forall X, X ∈ F -> Convex K X)
    (h_compact : forall X, X ∈ F -> IsCompact X)
    (h_inter :
      forall G : Finset (Set E),
        (G : Set (Set E)) ⊆ F ->
          G.card <= Module.finrank K E + 1 -> (⋂₀ (G : Set (Set E))).Nonempty) :
    (⋂₀ F).Nonempty := by
  classical
  have result := Convex.helly_theorem_set_compact' h_convex h_compact h_inter
  exact result
```

<a id="mathformer-autoformalizedhellystheorem-helly-compact-set-classical"></a>

## `Mathformer.AutoformalizedHellysTheorem.helly_compact_set_classical`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedHellysTheorem.lean:142](../../../../../backends/lean/Mathformer/AutoformalizedHellysTheorem.lean#L142)

**Generated Notes**

Classical compact-set Helly theorem for `F : Set (Set E)`.

**Lean**

```lean
theorem helly_compact_set_classical
    {F : Set (Set E)}
    (h_card : (Module.finrank K E : ENat) + 1 <= F.encard)
    (h_convex : forall X, X ∈ F -> Convex K X)
    (h_compact : forall X, X ∈ F -> IsCompact X)
    (h_inter :
      forall G : Finset (Set E),
        (G : Set (Set E)) ⊆ F ->
          G.card = Module.finrank K E + 1 -> (⋂₀ (G : Set (Set E))).Nonempty) :
    (⋂₀ F).Nonempty := by
  classical
  have result := Convex.helly_theorem_set_compact h_card h_convex h_compact h_inter
  exact result

end Compact
end Abstract

section Euclidean

variable {idx : Type uIdx} {d : Nat}
```

<a id="mathformer-autoformalizedhellystheorem-helly-euclidean-finite-classical"></a>

## `Mathformer.AutoformalizedHellysTheorem.helly_euclidean_finite_classical`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedHellysTheorem.lean:165](../../../../../backends/lean/Mathformer/AutoformalizedHellysTheorem.lean#L165)

**Generated Notes**

Article-level finite Helly theorem for families of convex subsets of `R^d`.

**Lean**

```lean
theorem helly_euclidean_finite_classical
    {F : idx -> Set (EuclideanSpace ℝ (Fin d))}
    {s : Finset idx}
    (h_card : d + 1 <= s.card)
    (h_convex : forall i, i ∈ s -> Convex ℝ (F i))
    (h_inter :
      forall I, I ⊆ s -> I.card = d + 1 -> (⋂ i ∈ I, F i).Nonempty) :
    (⋂ i ∈ s, F i).Nonempty := by
  have h_card' : Module.finrank ℝ (EuclideanSpace ℝ (Fin d)) + 1 <= s.card := by
    simpa [finrank_euclideanSpace_fin] using h_card
  have h_inter' :
      forall I,
        I ⊆ s ->
          I.card = Module.finrank ℝ (EuclideanSpace ℝ (Fin d)) + 1 ->
            (⋂ i ∈ I, F i).Nonempty := by
    intro I h_subset h_size
    have h_size' : I.card = d + 1 := by
      simpa [finrank_euclideanSpace_fin] using h_size
    exact h_inter I h_subset h_size'
  have result :=
    helly_finite_classical
      (K := ℝ)
      (E := EuclideanSpace ℝ (Fin d))
      (F := F)
      (s := s)
      h_card'
      h_convex
      h_inter'
  exact result
```

<a id="mathformer-autoformalizedhellystheorem-helly-euclidean-finite-set-classical"></a>

## `Mathformer.AutoformalizedHellysTheorem.helly_euclidean_finite_set_classical`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedHellysTheorem.lean:197](../../../../../backends/lean/Mathformer/AutoformalizedHellysTheorem.lean#L197)

**Generated Notes**

Article-level finite Helly theorem for finite sets of convex subsets of `R^d`.

**Lean**

```lean
theorem helly_euclidean_finite_set_classical
    {F : Finset (Set (EuclideanSpace ℝ (Fin d)))}
    (h_card : d + 1 <= F.card)
    (h_convex : forall X, X ∈ F -> Convex ℝ X)
    (h_inter :
      forall G : Finset (Set (EuclideanSpace ℝ (Fin d))),
        G ⊆ F -> G.card = d + 1 -> (⋂₀ (G : Set (Set (EuclideanSpace ℝ (Fin d))))).Nonempty) :
    (⋂₀ (F : Set (Set (EuclideanSpace ℝ (Fin d))))).Nonempty := by
  have h_card' :
      Module.finrank ℝ (EuclideanSpace ℝ (Fin d)) + 1 <= F.card := by
    simpa [finrank_euclideanSpace_fin] using h_card
  have h_inter' :
      forall G : Finset (Set (EuclideanSpace ℝ (Fin d))),
        G ⊆ F ->
          G.card = Module.finrank ℝ (EuclideanSpace ℝ (Fin d)) + 1 ->
            (⋂₀ (G : Set (Set (EuclideanSpace ℝ (Fin d))))).Nonempty := by
    intro G h_subset h_size
    have h_size' : G.card = d + 1 := by
      simpa [finrank_euclideanSpace_fin] using h_size
    exact h_inter G h_subset h_size'
  have result :=
    helly_finite_set_classical
      (K := ℝ)
      (E := EuclideanSpace ℝ (Fin d))
      (F := F)
      h_card'
      h_convex
      h_inter'
  exact result

section Compact
```

<a id="mathformer-autoformalizedhellystheorem-helly-euclidean-compact-family-small-subfamilies"></a>

## `Mathformer.AutoformalizedHellysTheorem.helly_euclidean_compact_family_small_subfamilies`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedHellysTheorem.lean:231](../../../../../backends/lean/Mathformer/AutoformalizedHellysTheorem.lean#L231)

**Generated Notes**

Article-level compact Helly theorem for families of compact convex subsets of `R^d`.

**Lean**

```lean
theorem helly_euclidean_compact_family_small_subfamilies
    {F : idx -> Set (EuclideanSpace ℝ (Fin d))}
    (h_convex : forall i, Convex ℝ (F i))
    (h_compact : forall i, IsCompact (F i))
    (h_inter :
      forall I : Finset idx, I.card <= d + 1 -> (⋂ i ∈ I, F i).Nonempty) :
    (⋂ i, F i).Nonempty := by
  have h_inter' :
      forall I : Finset idx,
        I.card <= Module.finrank ℝ (EuclideanSpace ℝ (Fin d)) + 1 ->
          (⋂ i ∈ I, F i).Nonempty := by
    intro I h_size
    have h_size' : I.card <= d + 1 := by
      simpa [finrank_euclideanSpace_fin] using h_size
    exact h_inter I h_size'
  have result :=
    helly_compact_family_small_subfamilies
      (K := ℝ)
      (E := EuclideanSpace ℝ (Fin d))
      (F := F)
      h_convex
      h_compact
      h_inter'
  exact result
```

<a id="mathformer-autoformalizedhellystheorem-helly-euclidean-compact-set-small-subfamilies"></a>

## `Mathformer.AutoformalizedHellysTheorem.helly_euclidean_compact_set_small_subfamilies`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedHellysTheorem.lean:258](../../../../../backends/lean/Mathformer/AutoformalizedHellysTheorem.lean#L258)

**Generated Notes**

Article-level compact Helly theorem for sets of compact convex subsets of `R^d`.

**Lean**

```lean
theorem helly_euclidean_compact_set_small_subfamilies
    {F : Set (Set (EuclideanSpace ℝ (Fin d)))}
    (h_convex : forall X, X ∈ F -> Convex ℝ X)
    (h_compact : forall X, X ∈ F -> IsCompact X)
    (h_inter :
      forall G : Finset (Set (EuclideanSpace ℝ (Fin d))),
        (G : Set (Set (EuclideanSpace ℝ (Fin d)))) ⊆ F ->
          G.card <= d + 1 ->
            (⋂₀ (G : Set (Set (EuclideanSpace ℝ (Fin d))))).Nonempty) :
    (⋂₀ F).Nonempty := by
  have h_inter' :
      forall G : Finset (Set (EuclideanSpace ℝ (Fin d))),
        (G : Set (Set (EuclideanSpace ℝ (Fin d)))) ⊆ F ->
          G.card <= Module.finrank ℝ (EuclideanSpace ℝ (Fin d)) + 1 ->
            (⋂₀ (G : Set (Set (EuclideanSpace ℝ (Fin d))))).Nonempty := by
    intro G h_subset h_size
    have h_size' : G.card <= d + 1 := by
      simpa [finrank_euclideanSpace_fin] using h_size
    exact h_inter G h_subset h_size'
  have result :=
    helly_compact_set_small_subfamilies
      (K := ℝ)
      (E := EuclideanSpace ℝ (Fin d))
      (F := F)
      h_convex
      h_compact
      h_inter'
  exact result

end Compact
end Euclidean

end AutoformalizedHellysTheorem
end Mathformer
```
