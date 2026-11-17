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

set_option linter.unusedSectionVars false

/-!
Original source (NL): Radon's theorem says that any set of `d + 2` points in real
`d`-dimensional Euclidean space can be partitioned into two disjoint parts whose
convex hulls intersect.

Original source (LaTeX): for `S \subset \mathbb{R}^d` with
`|S| = d + 2`, there are `S_1,S_2` partitioning `S` such that
`\operatorname{conv}(S_1) \cap \operatorname{conv}(S_2) \ne \varnothing`.

Mathlib grounding: mathlib already proves the stronger affine-dependent-family
version as `Convex.radon_partition`. This module packages that theorem, exposes
an intersection point, and specializes it to `d + 2` indexed points in
`EuclideanSpace ℝ (Fin d)`.
-/

noncomputable section
open Set

namespace Mathformer

namespace AutoformalizedRadonsTheorem

universe uι u𝕜 uE

/--
Mathlib grounding (NL): This is Radon's theorem in mathlib's affine-dependent
form.
Generated equivalent (LaTeX): if `(f_i)_{i \in \iota}` is affinely dependent,
then there is `I \subseteq \iota` such that
`\operatorname{conv}(f(I)) \cap \operatorname{conv}(f(I^c)) \ne \varnothing`.
-/
theorem radon_partition_affine_dependent
    {ι : Type uι} {𝕜 : Type u𝕜} {E : Type uE}
    [Field 𝕜] [LinearOrder 𝕜] [IsStrictOrderedRing 𝕜]
    [AddCommGroup E] [Module 𝕜 E]
    {f : ι → E}
    (h : ¬ AffineIndependent 𝕜 f) :
    ∃ I : Set ι, (convexHull 𝕜 (f '' I) ∩ convexHull 𝕜 (f '' Iᶜ)).Nonempty := by
  exact Convex.radon_partition h

/--
Generated note (NL): This unpacks the nonempty intersection into an explicit
Radon point.
Generated equivalent (LaTeX): there exist `I \subseteq \iota` and `p \in E`
with `p \in \operatorname{conv}(f(I))` and
`p \in \operatorname{conv}(f(I^c))`.
-/
theorem radon_partition_affine_dependent_point
    {ι : Type uι} {𝕜 : Type u𝕜} {E : Type uE}
    [Field 𝕜] [LinearOrder 𝕜] [IsStrictOrderedRing 𝕜]
    [AddCommGroup E] [Module 𝕜 E]
    {f : ι → E}
    (h : ¬ AffineIndependent 𝕜 f) :
    ∃ I : Set ι, ∃ p : E, p ∈ convexHull 𝕜 (f '' I) ∧ p ∈ convexHull 𝕜 (f '' Iᶜ) := by
  rcases radon_partition_affine_dependent (f := f) h with ⟨I, p, hp⟩
  exact ⟨I, p, hp.1, hp.2⟩

/--
Generated note (NL): A finite family with more indices than `finrank E + 1`
cannot be affinely independent.
Generated equivalent (LaTeX): if `\operatorname{finrank}_{\mathbb{k}} E + 1 < |\iota|`,
then `(f_i)_{i \in \iota}` is not affinely independent.
-/
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

/--
Generated note (NL): Combining the finite-dimensional affine-dependence bound
with mathlib's Radon partition gives the general finite-family form.
Generated equivalent (LaTeX): if `\operatorname{finrank}_{\mathbb{k}} E + 1 < |\iota|`,
then some `I` satisfies
`\operatorname{conv}(f(I)) \cap \operatorname{conv}(f(I^c)) \ne \varnothing`.
-/
theorem radon_partition_of_finrank_add_one_lt_card
    {ι : Type uι} {𝕜 : Type u𝕜} {E : Type uE}
    [Field 𝕜] [LinearOrder 𝕜] [IsStrictOrderedRing 𝕜]
    [AddCommGroup E] [Module 𝕜 E] [Module.Finite 𝕜 E] [Fintype ι]
    {f : ι → E}
    (hcard : Module.finrank 𝕜 E + 1 < Fintype.card ι) :
    ∃ I : Set ι, (convexHull 𝕜 (f '' I) ∩ convexHull 𝕜 (f '' Iᶜ)).Nonempty := by
  exact radon_partition_affine_dependent (f := f)
    (not_affineIndependent_of_finrank_add_one_lt_card f hcard)

/--
Generated note (NL): This is the finite-family Radon partition with the
intersection witness made explicit.
Generated equivalent (LaTeX): there exist `I \subseteq \iota` and `p \in E`
with `p \in \operatorname{conv}(f(I)) \cap \operatorname{conv}(f(I^c))`.
-/
theorem radon_partition_of_finrank_add_one_lt_card_point
    {ι : Type uι} {𝕜 : Type u𝕜} {E : Type uE}
    [Field 𝕜] [LinearOrder 𝕜] [IsStrictOrderedRing 𝕜]
    [AddCommGroup E] [Module 𝕜 E] [Module.Finite 𝕜 E] [Fintype ι]
    {f : ι → E}
    (hcard : Module.finrank 𝕜 E + 1 < Fintype.card ι) :
    ∃ I : Set ι, ∃ p : E, p ∈ convexHull 𝕜 (f '' I) ∧ p ∈ convexHull 𝕜 (f '' Iᶜ) := by
  exact radon_partition_affine_dependent_point (f := f)
    (not_affineIndependent_of_finrank_add_one_lt_card f hcard)

/--
Original source (NL): Any `d + 2` points in `d`-dimensional Euclidean space can
be partitioned so that the convex hulls of the two parts intersect.
Original source (LaTeX): for `f : \operatorname{Fin}(d+2) \to \mathbb{R}^d`,
there is `I \subseteq \operatorname{Fin}(d+2)` such that
`\operatorname{conv}(f(I)) \cap \operatorname{conv}(f(I^c)) \ne \varnothing`.
-/
theorem radon_partition_euclidean_fin
    {d : ℕ}
    (f : Fin (d + 2) → EuclideanSpace ℝ (Fin d)) :
    ∃ I : Set (Fin (d + 2)),
      (convexHull ℝ (f '' I) ∩ convexHull ℝ (f '' Iᶜ)).Nonempty := by
  apply radon_partition_of_finrank_add_one_lt_card (f := f)
  simp

/--
Original source (NL): The Radon partition has a common point in the two convex
hulls.
Original source (LaTeX): there exist `I` and `p \in \mathbb{R}^d` such that
`p \in \operatorname{conv}(f(I))` and
`p \in \operatorname{conv}(f(I^c))`.
-/
theorem radon_partition_euclidean_fin_point
    {d : ℕ}
    (f : Fin (d + 2) → EuclideanSpace ℝ (Fin d)) :
    ∃ I : Set (Fin (d + 2)), ∃ p : EuclideanSpace ℝ (Fin d),
      p ∈ convexHull ℝ (f '' I) ∧ p ∈ convexHull ℝ (f '' Iᶜ) := by
  rcases radon_partition_euclidean_fin f with ⟨I, p, hp⟩
  exact ⟨I, p, hp.1, hp.2⟩

end AutoformalizedRadonsTheorem

end Mathformer
