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

import Mathlib.Data.Set.Card

/-!
Original source (NL): The Vapnik--Chervonenkis dimension measures the capacity
of a family of sets, or equivalently a binary hypothesis class. A set `X` is
shattered by a family `𝒞` when every subset of `X` is realized as `C ∩ X` for
some `C ∈ 𝒞`. The VC dimension is the cardinality of the largest shattered set;
if arbitrarily large finite sets are shattered, the VC dimension is infinite.

Original source (LaTeX): for a set family `\mathcal C`,
`\mathcal C \cap X := \{C \cap X \mid C \in \mathcal C\}`. The set `X` is
shattered iff `\mathcal P(X)=\mathcal C \cap X`. The VC dimension is
`\max\{|X| : X \text{ is shattered by } \mathcal C\}`, or `\infty` if such
finite cardinalities are unbounded.

Mathlib grounding: this module uses mathlib's `Set` and finite-set cardinal API
to formalize the core set-family definition and finite/infinite VC-dimension
predicates. Classification-model formulations can be mapped into this interface
by taking the positive regions of binary classifiers.
-/

namespace Mathformer
namespace AutoformalizedVCDimension

open Set

universe u

variable {α : Type u}

/--
Original source (NL): The trace, or intersection family, of a set family `𝒞` on
`X` consists of all intersections `C ∩ X` with `C ∈ 𝒞`.
Original source (LaTeX): `\mathcal C \cap X := \{C \cap X \mid C \in \mathcal C\}`.
-/
def Trace (𝒞 : Set (Set α)) (X : Set α) : Set (Set α) :=
  {Y | ∃ C ∈ 𝒞, Y = C ∩ X}

/--
Original source (NL): A set `X` is shattered by `𝒞` when every subset of `X` is
realized as an intersection with a member of `𝒞`.
Original source (LaTeX): `X` is shattered iff
`\forall Y \subseteq X,\ \exists C \in \mathcal C,\ C \cap X = Y`.
-/
def Shatters (𝒞 : Set (Set α)) (X : Set α) : Prop :=
  ∀ Y : Set α, Y ⊆ X → ∃ C ∈ 𝒞, C ∩ X = Y

/--
Generated note (NL): Membership in the trace is exactly being an intersection
with some concept in the family.
Generated equivalent (LaTeX): `Y \in \mathcal C \cap X` iff
`\exists C \in \mathcal C,\ Y = C \cap X`.
-/
theorem mem_trace_iff {𝒞 : Set (Set α)} {X Y : Set α} :
    Y ∈ Trace 𝒞 X ↔ ∃ C ∈ 𝒞, Y = C ∩ X := by
  constructor
  · intro h
    assumption
  · intro h
    assumption

/--
Generated note (NL): Every trace member is a subset of the base set being traced.
Generated equivalent (LaTeX): if `Y=C\cap X`, then `Y \subseteq X`.
-/
theorem trace_subset_powerset {𝒞 : Set (Set α)} {X Y : Set α}
    (hY : Y ∈ Trace 𝒞 X) :
    Y ⊆ X := by
  rcases hY with ⟨C, _hC, rfl⟩
  exact inter_subset_right

/--
Original source (NL): Shattering is equivalent to the trace on `X` containing
exactly all subsets of `X`.
Original source (LaTeX): `X` is shattered iff
`\mathcal C \cap X = \mathcal P(X)`.
-/
theorem shatters_iff_trace_eq_powerset {𝒞 : Set (Set α)} {X : Set α} :
    Shatters 𝒞 X ↔ Trace 𝒞 X = {Y : Set α | Y ⊆ X} := by
  constructor
  · intro h
    ext Y
    constructor
    · intro hY
      exact trace_subset_powerset hY
    · intro hY
      rcases h Y hY with ⟨C, hC, hCX⟩
      exact ⟨C, hC, hCX.symm⟩
  · intro h Y hY
    have hmem : Y ∈ Trace 𝒞 X := by
      simpa [h] using hY
    rcases hmem with ⟨C, hC, hCY⟩
    exact ⟨C, hC, hCY.symm⟩

/--
Generated note (NL): Shattering is downward closed: every subset of a shattered
set is also shattered.
Generated equivalent (LaTeX): if `Y \subseteq X` and `X` is shattered, then
`Y` is shattered.
-/
theorem Shatters.mono {𝒞 : Set (Set α)} {X Y : Set α}
    (hX : Shatters 𝒞 X)
    (hYX : Y ⊆ X) :
    Shatters 𝒞 Y := by
  intro Z hZY
  have hZX : Z ⊆ X := hZY.trans hYX
  rcases hX Z hZX with ⟨C, hC, hCX⟩
  refine ⟨C, hC, ?_⟩
  ext a
  constructor
  · intro ha
    have haX : a ∈ X := hYX ha.2
    have : a ∈ C ∩ X := ⟨ha.1, haX⟩
    simpa [hCX] using this
  · intro haZ
    have haCX : a ∈ C ∩ X := by
      simpa [hCX] using haZ
    exact ⟨haCX.1, hZY haZ⟩

/--
Original source (NL): A set family has VC dimension at least `d` when it
shatters some finite set of cardinality `d`.
Original source (LaTeX): `\operatorname{VCdim}(\mathcal C) \ge d` iff
`\exists X,\ |X|=d` and `X` is shattered by `\mathcal C`.
-/
def VCdimAtLeast (𝒞 : Set (Set α)) (d : ℕ) : Prop :=
  ∃ X : Set α, X.Finite ∧ X.ncard = d ∧ Shatters 𝒞 X

/--
Original source (NL): The VC dimension is infinite when arbitrarily large finite
sets can be shattered.
Original source (LaTeX): `\operatorname{VCdim}(\mathcal C)=\infty` iff
`\forall d,\ \exists X,\ |X|=d` and `X` is shattered.
-/
def InfiniteVCdim (𝒞 : Set (Set α)) : Prop :=
  ∀ d : ℕ, VCdimAtLeast 𝒞 d

/--
Original source (NL): A finite VC dimension `d` means some `d`-point set is
shattered and no `(d+1)`-point finite set is shattered.
Original source (LaTeX): `\operatorname{VCdim}(\mathcal C)=d` iff
`\operatorname{VCdim}(\mathcal C)\ge d` and not
`\operatorname{VCdim}(\mathcal C)\ge d+1`.
-/
def HasFiniteVCdim (𝒞 : Set (Set α)) (d : ℕ) : Prop :=
  VCdimAtLeast 𝒞 d ∧ ¬ VCdimAtLeast 𝒞 (d + 1)

/--
Generated note (NL): A family with finite VC dimension `d` has VC dimension at
least `d`.
Generated equivalent (LaTeX): `\operatorname{VCdim}(\mathcal C)=d` implies
`\operatorname{VCdim}(\mathcal C)\ge d`.
-/
theorem HasFiniteVCdim.atLeast {𝒞 : Set (Set α)} {d : ℕ}
    (h : HasFiniteVCdim 𝒞 d) :
    VCdimAtLeast 𝒞 d := by
  rcases h with ⟨atLeastProof, _⟩
  exact atLeastProof

/--
Generated note (NL): A family with finite VC dimension `d` does not shatter a
set of cardinality `d+1`.
Generated equivalent (LaTeX): `\operatorname{VCdim}(\mathcal C)=d` implies not
`\operatorname{VCdim}(\mathcal C)\ge d+1`.
-/
theorem HasFiniteVCdim.not_atLeast_succ {𝒞 : Set (Set α)} {d : ℕ}
    (h : HasFiniteVCdim 𝒞 d) :
    ¬ VCdimAtLeast 𝒞 (d + 1) := by
  rcases h with ⟨_, notAtLeastSuccProof⟩
  exact notAtLeastSuccProof

/--
Generated note (NL): Under the explicit nonemptiness assumption, the empty set is
shattered by a set family.
Generated equivalent (LaTeX): if `\mathcal C \ne \varnothing`, then
`\varnothing` is shattered by `\mathcal C`.
-/
theorem shatters_empty_of_nonempty {𝒞 : Set (Set α)}
    (h𝒞 : 𝒞.Nonempty) :
    Shatters 𝒞 (∅ : Set α) := by
  rcases h𝒞 with ⟨C, hC⟩
  intro Y hY
  refine ⟨C, hC, ?_⟩
  ext a
  constructor
  · intro ha
    cases ha.2
  · intro ha
    cases hY ha

end AutoformalizedVCDimension
end Mathformer
