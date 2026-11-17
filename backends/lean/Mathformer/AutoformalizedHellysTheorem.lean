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

import Mathlib.Analysis.Convex.Radon
import Mathlib.Analysis.InnerProductSpace.PiL2

/-!
Interface-level autoformalization for Helly's theorem.

This module is source-aligned to `tests/latex/hellys_theorem.tex`.
It exposes both abstract finite-dimensional Helly statements from mathlib and explicit
Euclidean-space specializations that match the article's `R^d` presentation.

Scope:
- finite families and finite sets of convex sets,
- compact-family and compact-set extensions with bounded-subfamily assumptions,
- classical exact-cardinality variants,
- explicit `EuclideanSpace ℝ (Fin d)` formulations of the article-level statements.
-/

namespace Mathformer
namespace AutoformalizedHellysTheorem

universe uIdx uK uE

section Abstract

variable {idx : Type uIdx} {K : Type uK} {E : Type uE}
variable [Field K] [LinearOrder K] [IsStrictOrderedRing K]
variable [AddCommGroup E] [Module K E] [FiniteDimensional K E]

/--
Generated note (NL): Abstract finite-family classical Helly theorem:
if every subfamily of size `finrank K E + 1` intersects, then the whole family intersects. -/
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

/--
Generated note (NL): Abstract finite-family Helly theorem with bounded subfamilies:
if every subfamily of size at most `finrank K E + 1` intersects, then the whole family intersects. -/
theorem helly_finite_small_subfamilies
    {F : idx -> Set E}
    {s : Finset idx}
    (h_convex : forall i, i ∈ s -> Convex K (F i))
    (h_inter :
      forall I, I ⊆ s -> I.card <= Module.finrank K E + 1 -> (⋂ i ∈ I, F i).Nonempty) :
    (⋂ i ∈ s, F i).Nonempty := by
  have result := Convex.helly_theorem' h_convex h_inter
  exact result

/--
Generated note (NL): Abstract finite-set classical Helly theorem for `Finset (Set E)`. -/
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

/--
Generated note (NL): Abstract finite-set Helly theorem with bounded subfamilies for `Finset (Set E)`. -/
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

/--
Generated note (NL): Source-faithful compact-family Helly theorem:
if every finite subfamily of size at most `finrank K E + 1` intersects, then the whole family intersects. -/
theorem helly_compact_family_small_subfamilies
    {F : idx -> Set E}
    (h_convex : forall i, Convex K (F i))
    (h_compact : forall i, IsCompact (F i))
    (h_inter :
      forall I : Finset idx, I.card <= Module.finrank K E + 1 -> (⋂ i ∈ I, F i).Nonempty) :
    (⋂ i, F i).Nonempty := by
  have result := Convex.helly_theorem_compact' h_convex h_compact h_inter
  exact result

/--
Generated note (NL): Classical compact-family Helly theorem:
if the family has at least `finrank K E + 1` sets and every subfamily of that size intersects,
then the whole family intersects. -/
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

/--
Generated note (NL): Source-faithful compact-set Helly theorem for `F : Set (Set E)`:
if every finite subfamily of size at most `finrank K E + 1` intersects, then the whole family intersects. -/
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

/--
Generated note (NL): Classical compact-set Helly theorem for `F : Set (Set E)`. -/
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

/--
Generated note (NL): Article-level finite Helly theorem for families of convex subsets of `R^d`. -/
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

/--
Generated note (NL): Article-level finite Helly theorem for finite sets of convex subsets of `R^d`. -/
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

/--
Generated note (NL): Article-level compact Helly theorem for families of compact convex subsets of `R^d`. -/
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

/--
Generated note (NL): Article-level compact Helly theorem for sets of compact convex subsets of `R^d`. -/
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
