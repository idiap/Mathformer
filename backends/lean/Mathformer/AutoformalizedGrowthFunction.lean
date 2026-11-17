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

import Mathformer.AutoformalizedVCDimension

/-!
Original source (NL): In statistical learning theory, the growth function of a
set family or binary hypothesis class counts the largest number of distinct
dichotomies the class can induce on an `m`-point sample.

Original source (LaTeX): for a concept class `\mathcal C`,
`\Pi_{\mathcal C}(m)=\max_{X: |X|=m} |\mathcal C \cap X|`, where
`\mathcal C \cap X=\{C \cap X : C \in \mathcal C\}` is the trace on `X`.

Mathlib grounding: this module reuses the `Trace` and `Shatters` definitions
from `AutoformalizedVCDimension`. The maximum is represented by the predicate
`GrowthFunctionValue`, meaning that the value is both attained by an `m`-point
sample and upper-bounds every `m`-point sample.
-/

namespace Mathformer
namespace AutoformalizedGrowthFunction

open Set
open AutoformalizedVCDimension

universe u

variable {α : Type u}

/--
Original source (NL): A binary classifier determines the set of points it labels
positive.
Original source (LaTeX): for `h : X \to \{0,1\}`,
`h^{-1}(\{1\}) = \{x : h(x)=1\}`.
-/
def PositiveRegion (h : α → Bool) : Set α :=
  {x | h x = true}

/--
Original source (NL): A binary hypothesis class can be viewed as a concept class
by taking all positive regions of its classifiers.
Original source (LaTeX): `\mathcal C_{\mathcal H} =
\{\{x : h(x)=1\} : h \in \mathcal H\}`.
-/
def ConceptClassOfBinary (ℋ : Set (α → Bool)) : Set (Set α) :=
  {C | ∃ h ∈ ℋ, C = PositiveRegion h}

/--
Generated note (NL): Membership in the concept class of a binary hypothesis
hypothesis family is exactly being the positive region of one of its hypotheses.
Generated equivalent (LaTeX): `C \in \mathcal C_{\mathcal H}` iff
`\exists h \in \mathcal H,\ C=\{x:h(x)=1\}`.
-/
theorem mem_conceptClassOfBinary_iff {ℋ : Set (α → Bool)} {C : Set α} :
    C ∈ ConceptClassOfBinary ℋ ↔ ∃ h ∈ ℋ, C = PositiveRegion h := by
  constructor
  · intro h
    assumption
  · intro h
    assumption

/--
Original source (NL): The growth function is at least `n` at sample size `m`
when some `m`-point sample has at least `n` distinct traces.
Original source (LaTeX): `\Pi_{\mathcal C}(m) \ge n` iff
`\exists X,\ |X|=m` and `n \le |\mathcal C \cap X|`.
-/
def GrowthFunctionAtLeast (𝒞 : Set (Set α)) (m n : ℕ) : Prop :=
  ∃ X : Set α, X.Finite ∧ X.ncard = m ∧ n ≤ (Trace 𝒞 X).ncard

/--
Original source (NL): The growth function is at most `n` at sample size `m` when
every `m`-point sample has at most `n` distinct traces.
Original source (LaTeX): `\Pi_{\mathcal C}(m) \le n` iff for every `X` with
`|X|=m`, `|\mathcal C \cap X| \le n`.
-/
def GrowthFunctionAtMost (𝒞 : Set (Set α)) (m n : ℕ) : Prop :=
  ∀ X : Set α, X.Finite → X.ncard = m → (Trace 𝒞 X).ncard ≤ n

/--
Original source (NL): The growth function has value `n` at sample size `m` when
the upper bound `n` is attained by some `m`-point sample.
Original source (LaTeX): `\Pi_{\mathcal C}(m)=n` iff
`\exists X,\ |X|=m \land |\mathcal C \cap X|=n`, and every `m`-point `Y`
satisfies `|\mathcal C \cap Y| \le n`.
-/
def GrowthFunctionValue (𝒞 : Set (Set α)) (m n : ℕ) : Prop :=
  (∃ X : Set α, X.Finite ∧ X.ncard = m ∧ (Trace 𝒞 X).ncard = n) ∧
    GrowthFunctionAtMost 𝒞 m n

/--
Generated note (NL): A trace over a finite sample is finite because it is a
subfamily of the finite powerset of the sample.
Generated equivalent (LaTeX): if `X` is finite, then
`\mathcal C \cap X \subseteq \mathcal P(X)` is finite.
-/
theorem finite_trace_of_finite {𝒞 : Set (Set α)} {X : Set α}
    (hX : X.Finite) :
    (Trace 𝒞 X).Finite := by
  refine hX.powerset.subset ?_
  intro Y hY
  exact trace_subset_powerset hY

/--
Original source (NL): The growth function is bounded above by the number of all
subsets of an `m`-point sample.
Original source (LaTeX): for `|X|=m`,
`|\mathcal C \cap X| \le |\mathcal P(X)| = 2^m`.
-/
theorem trace_ncard_le_two_pow {𝒞 : Set (Set α)} {X : Set α}
    (hX : X.Finite) :
    (Trace 𝒞 X).ncard ≤ 2 ^ X.ncard := by
  calc
    (Trace 𝒞 X).ncard ≤ (𝒫 X).ncard := by
      exact ncard_le_ncard (fun Y hY => trace_subset_powerset hY) hX.powerset
    _ = 2 ^ X.ncard := by
      exact ncard_powerset X hX

/--
Generated note (NL): Therefore the growth function is always at most `2^m`.
Generated equivalent (LaTeX): `\Pi_{\mathcal C}(m) \le 2^m`.
-/
theorem growthFunctionAtMost_two_pow (𝒞 : Set (Set α)) (m : ℕ) :
    GrowthFunctionAtMost 𝒞 m (2 ^ m) := by
  intro X hX hcard
  simpa [hcard] using trace_ncard_le_two_pow (𝒞 := 𝒞) hX

/--
Generated note (NL): If a maximum growth value is attained, then it gives the
corresponding lower-bound statement.
Generated equivalent (LaTeX): `\Pi_{\mathcal C}(m)=n` implies
`\Pi_{\mathcal C}(m)\ge n`.
-/
theorem GrowthFunctionValue.atLeast {𝒞 : Set (Set α)} {m n : ℕ}
    (h : GrowthFunctionValue 𝒞 m n) :
    GrowthFunctionAtLeast 𝒞 m n := by
  rcases h.1 with ⟨X, hXfin, hXm, htrace⟩
  exact ⟨X, hXfin, hXm, le_of_eq htrace.symm⟩

/--
Generated note (NL): If a maximum growth value is attained, then it gives the
corresponding upper-bound statement.
Generated equivalent (LaTeX): `\Pi_{\mathcal C}(m)=n` implies
`\Pi_{\mathcal C}(m)\le n`.
-/
theorem GrowthFunctionValue.atMost {𝒞 : Set (Set α)} {m n : ℕ}
    (h : GrowthFunctionValue 𝒞 m n) :
    GrowthFunctionAtMost 𝒞 m n := by
  rcases h with ⟨_, atMostProof⟩
  exact atMostProof

/--
Original source (NL): If an `m`-point sample is shattered, the growth function at
`m` reaches the full `2^m` possible dichotomies.
Original source (LaTeX): if `X` is shattered and `|X|=m`, then
`|\mathcal C \cap X| = 2^m`.
-/
theorem trace_ncard_eq_two_pow_of_shatters {𝒞 : Set (Set α)} {X : Set α}
    (hXfin : X.Finite)
    (hshatter : Shatters 𝒞 X) :
    (Trace 𝒞 X).ncard = 2 ^ X.ncard := by
  rw [(shatters_iff_trace_eq_powerset).mp hshatter]
  exact ncard_powerset X hXfin

/--
Original source (NL): A shattered `m`-point sample makes the growth function at
least `2^m`.
Original source (LaTeX): if `\mathcal C` shatters `X` and `|X|=m`, then
`\Pi_{\mathcal C}(m) \ge 2^m`.
-/
theorem growthFunctionAtLeast_two_pow_of_shatters {𝒞 : Set (Set α)} {X : Set α} {m : ℕ}
    (hXfin : X.Finite)
    (hXm : X.ncard = m)
    (hshatter : Shatters 𝒞 X) :
    GrowthFunctionAtLeast 𝒞 m (2 ^ m) := by
  refine ⟨X, hXfin, hXm, ?_⟩
  rw [trace_ncard_eq_two_pow_of_shatters hXfin hshatter, hXm]

/--
Generated note (NL): If the growth function attains the universal upper bound
`2^m`, then its value at `m` is exactly `2^m`.
Generated equivalent (LaTeX): an attained sample with `2^m` traces plus the
universal bound proves `\Pi_{\mathcal C}(m)=2^m`.
-/
theorem growthFunctionValue_two_pow_of_shatters {𝒞 : Set (Set α)} {X : Set α} {m : ℕ}
    (hXfin : X.Finite)
    (hXm : X.ncard = m)
    (hshatter : Shatters 𝒞 X) :
    GrowthFunctionValue 𝒞 m (2 ^ m) := by
  constructor
  · refine ⟨X, hXfin, hXm, ?_⟩
    rw [trace_ncard_eq_two_pow_of_shatters hXfin hshatter, hXm]
  · exact growthFunctionAtMost_two_pow 𝒞 m

/--
Original source (NL): The growth function of a binary hypothesis class is the
growth function of its associated concept class of positive regions.
Original source (LaTeX): `\Pi_{\mathcal H}(m)` is represented as
`\Pi_{\mathcal C_{\mathcal H}}(m)`.
-/
def BinaryGrowthFunctionValue (ℋ : Set (α → Bool)) (m n : ℕ) : Prop :=
  GrowthFunctionValue (ConceptClassOfBinary ℋ) m n

end AutoformalizedGrowthFunction
end Mathformer
