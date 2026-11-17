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

import Mathlib.Data.Set.Countable
import Mathlib.Logic.Function.Basic
import Mathlib.SetTheory.Cardinal.SchroederBernstein

/-!
Original source (NL): Chapter 1 of the CBT textbook archive, "Cantor's CBT
Proof for Sets of the Power of (II)", presents Cantor's generation principles,
the denumerable union theorem, the denumerable Cantor-Bernstein theorem,
Cantor's diagonal/sequent argument separating the first and second number
classes, Lemma 2 on least elements of subsets, the Fundamental Theorem for
subsets of the second number-class, Cantor-Bernstein for `(II)`, the Limitation
Principle, and the Union Theorem for the next number-class.

Original source (LaTeX): key chapter statements include: "The union of a
denumerable set of denumerable sets is denumerable"; "An infinite subset of a
denumerable set is denumerable"; "The power of `(II)` is different from the
power of `(I)`"; "In every subset of `(II)` there is a smallest number"; and a
Cantor-Bernstein statement from mutual embeddings/equipollence.

Generated note (NL): This file formalizes the chapter's reusable mathematical
core in modern mathlib terms. The historical generation and limitation
principles are recorded as explicit structures because the source describes
Cantor's ordinal-generation framework, not a ready-made Lean construction of
the second number-class. The countability, diagonal, least-element, and
Schroeder-Bernstein components are proved with complete Lean proof terms and
without target axioms.
-/

namespace Mathformer
namespace AutoformalizedCBTChapter1

open Function Set

universe u v

/--
Original source (NL): The first generation principle says that, given a number,
a new number is generated: its successor or sequent.
Original source (LaTeX): `a \mapsto a+1`.
Generated note (NL): The chapter treats this as a historical principle for
Cantor's scale of numbers. We record the data needed for such a successor
operation and its freshness property.
-/
structure FirstGenerationPrinciple (α : Type u) where
  successor : α → α
  successor_ne_self : ∀ a : α, successor a ≠ a

/--
Original source (NL): The second generation principle says that every definite
succession of already-defined numbers with no greatest member generates a new
limit or sequent.
Original source (LaTeX): a succession with no greatest member has a limit
sequent.
Generated note (NL): This structure isolates the source principle as data:
for every admissible succession with no greatest member there is a generated
limit element.
-/
structure SecondGenerationPrinciple (α : Type u) [LT α] where
  AdmissibleSuccession : Set α → Prop
  hasNoGreatest : Set α → Prop
  limitSequent : (s : Set α) → AdmissibleSuccession s → hasNoGreatest s → α
  below_limit :
    ∀ (s : Set α) (hs : AdmissibleSuccession s) (hng : hasNoGreatest s),
      ∀ a ∈ s, a < limitSequent s hs hng

/--
Original source (NL): The Limitation Principle admits a new integer into the
scale only if its power is that of an already existing complete number-class.
Original source (LaTeX): a generated number is admitted only when its power
matches a prior number-class.
Generated note (NL): This is a predicate-level record of the admission rule,
separated from any particular construction of Cantor's historical classes.
-/
structure LimitationPrinciple (α : Type u) where
  alreadyExistingClass : Set α → Prop
  samePowerAsExistingClass : α → Prop
  admissible : α → Prop
  admission_rule : ∀ a : α, samePowerAsExistingClass a → admissible a

/--
Generated note (NL): A set is denumerable in the chapter's modernized sense
when it is countable and nonempty. This keeps the countability content separate
from the historical convention that Cantor's positive integers start at `1`.
Generated equivalent (LaTeX): `\mathrm{Denumerable}(s) := s\text{ is countable}
\wedge s\ne\varnothing`.
-/
def Denumerable {α : Type u} (s : Set α) : Prop :=
  s.Countable ∧ s.Nonempty

/--
Original source (NL): The enumeration-by method enumerates a denumerable set
by the first number-class.
Original source (LaTeX): if `A` is denumerable, then there is an onto map
`\mathbb N \twoheadrightarrow A`.
Generated note (NL): Mathlib packages this as `Set.Countable.exists_surjective`
for the subtype determined by a nonempty countable set.
-/
theorem Denumerable.exists_nat_surjection {α : Type u} {A : Set α}
    (hA : Denumerable A) :
    ∃ f : ℕ → A, Surjective f := by
  exact hA.1.exists_surjective hA.2

/--
Original source (NL): The Denumerable Union Theorem discusses the union of a
set-indexed family of sets.
Original source (LaTeX): `\bigcup_{i\in I} A_i`.
Generated note (NL): This definition gives the chapter's indexed-union object
a source-specific name while using Lean's ordinary indexed union.
-/
def CantorIndexedUnion {ι : Type u} {α : Type v}
    (I : Set ι) (A : ι → Set α) : Set α :=
  ⋃ i ∈ I, A i

/--
Original source (NL): The Union Theorem proof represents the relevant union as
a matrix of ordered pairs.
Original source (LaTeX): `{(a,b) \mid a\in A \wedge b\in B}`.
Generated note (NL): This definition names the source's pair matrix as the
mathlib set product.
-/
def CantorPairMatrix {α : Type u} {β : Type v}
    (A : Set α) (B : Set β) : Set (α × β) :=
  A ×ˢ B

/--
Original source (NL): The Denumerable Union Theorem: the union of a
denumerable set of denumerable sets is denumerable.
Original source (LaTeX): `\bigcup_{i\in I} A_i` is denumerable when `I` is
denumerable and each `A_i` is denumerable.
Generated note (NL): Mathlib's `Set.Countable.biUnion` proves the countability
part directly; nonemptiness is supplied by one inhabited component.
-/
theorem denumerable_union_theorem {ι : Type u} {α : Type v}
    {I : Set ι} {A : ι → Set α}
    (hI : I.Countable) (hA : ∀ i ∈ I, (A i).Countable)
    (hne : ∃ i ∈ I, (A i).Nonempty) :
    Denumerable (CantorIndexedUnion I A) := by
  unfold CantorIndexedUnion
  constructor
  · exact hI.biUnion fun i hi => hA i hi
  · rcases hne with ⟨i, hi, x, hx⟩
    refine ⟨x, ?_⟩
    simp only [mem_iUnion]
    exact ⟨i, ⟨hi, hx⟩⟩

/--
Original source (NL): The countability content of the Denumerable Union
Theorem is the countability of the indexed union.
Original source (LaTeX): if `I` is countable and each `A_i` is countable, then
`\bigcup_{i\in I} A_i` is countable.
-/
theorem countable_union_of_countable_family {ι : Type u} {α : Type v}
    {I : Set ι} {A : ι → Set α}
    (hI : I.Countable) (hA : ∀ i ∈ I, (A i).Countable) :
    (CantorIndexedUnion I A).Countable := by
  unfold CantorIndexedUnion
  exact hI.biUnion fun i hi => hA i hi

/--
Original source (NL): The Denumerable CBT: an infinite subset of a denumerable
set is denumerable.
Original source (LaTeX): if `A\subseteq B`, `B` is denumerable, and `A` is
infinite, then `A` is denumerable.
Generated note (NL): In Lean the countability part is simply monotonicity of
`Set.Countable`; infinitude supplies nonemptiness.
-/
theorem denumerable_cbt {α : Type u} {A B : Set α}
    (hAB : A ⊆ B) (hB : B.Countable) (hAinf : A.Infinite) :
    Denumerable A := by
  constructor
  · exact hB.mono hAB
  · exact hAinf.nonempty

/--
Original source (NL): The single-set formulation used in the chapter says
that intermediate subsets of a denumerable set are countable.
Original source (LaTeX): if `M''\subseteq M'\subseteq M` and `M` is
denumerable, then `M'` is countable.
-/
theorem intermediate_subset_of_denumerable_countable {α : Type u}
    {Mp M : Set α} (hMpM : Mp ⊆ M) (hM : M.Countable) :
    Mp.Countable := by
  exact hM.mono hMpM

/--
Original source (NL): Theorem 1 says that the power of `(II)` differs from
the power of `(I)`.
Original source (LaTeX): `|(II)|\ne |(I)|`.
Generated note (NL): A modern diagonal counterpart is Cantor's theorem: there
is no surjection from a type to its powerset. For `α = ℕ`, this says that the
power set of the first number-class cannot be enumerated by the first
number-class.
-/
theorem theorem1_nat_cannot_enumerate_powerset (f : ℕ → Set ℕ) :
    ¬ Surjective f := by
  exact Function.cantor_surjective f

/--
Original source (NL): Cantor's sequent argument rules out an enumeration whose
sequent is already among the preceding numbers.
Original source (LaTeX): no function `\mathbb N\to\mathcal P(\mathbb N)` is
onto.
Generated note (NL): This is the nonexistence of an equivalence between the
natural numbers and their powerset.
-/
theorem no_equiv_nat_powerset : IsEmpty (ℕ ≃ Set ℕ) := by
  refine ⟨fun e => ?_⟩
  exact Function.cantor_surjective (fun n => e n) e.surjective

/--
Original source (NL): Lemma 2(i): in every subset of `(II)` there is a
smallest number.
Original source (LaTeX): every nonempty subset has a least element.
Generated note (NL): The directly mathlib-compatible analogue is the
well-ordering of `ℕ`.
-/
theorem lemma2_nat_least_element {s : Set ℕ} (hs : s.Nonempty) :
    ∃ n ∈ s, ∀ m ∈ s, n ≤ m := by
  classical
  let p : ℕ → Prop := fun n => n ∈ s
  have hp : ∃ n, p n := hs
  refine ⟨Nat.find hp, Nat.find_spec hp, ?_⟩
  intro m hm
  exact Nat.find_min' hp hm

/--
Original source (NL): Lemma 2(ii): every descending sequence of numbers from
`(II)` is finite.
Original source (LaTeX): there is no infinite strictly descending sequence.
Generated note (NL): We prove the finite obstruction for `ℕ`: a strictly
descending chain of length `n` forces `a n + n \le a 0`, so its length is bounded
by the first value.
-/
theorem finite_descending_chain_bound_nat (a : ℕ → ℕ)
    (hdesc : ∀ n : ℕ, a (n + 1) < a n) :
    ∀ n : ℕ, a n + n ≤ a 0 := by
  intro n
  induction n with
  | zero =>
      simp
  | succ n ih =>
      have hstep : a (n + 1) + 1 ≤ a n := Nat.succ_le_of_lt (hdesc n)
      calc
        a (n + 1) + (n + 1) = (a (n + 1) + 1) + n := by omega
        _ ≤ a n + n := Nat.add_le_add_right hstep n
        _ ≤ a 0 := ih

/--
Original source (NL): Lemma 2(ii) rules out an infinite descending sequence.
Original source (LaTeX): no `a_0>a_1>a_2>\cdots`.
-/
theorem no_infinite_descending_sequence_nat :
    ¬ ∃ a : ℕ → ℕ, ∀ n : ℕ, a (n + 1) < a n := by
  rintro ⟨a, hdesc⟩
  have hbound := finite_descending_chain_bound_nat a hdesc (a 0 + 1)
  have hle : a 0 + 1 ≤ a (a 0 + 1) + (a 0 + 1) := Nat.le_add_left _ _
  exact Nat.not_succ_le_self (a 0) (hle.trans hbound)

/--
Original source (NL): The Fundamental Theorem: a subset of `(II)` is finite,
or has the power of `(I)`, or has the power of `(II)`.
Original source (LaTeX): every subset of `(II)` falls into the finite,
denumerable, or full-second-class case.
Generated note (NL): The countability component of the theorem says that every
subset of a countable ambient class is countable. This is the part used in the
chapter's later countability reductions.
-/
theorem fundamental_countability_component {α : Type u} {S II : Set α}
    (hS : S ⊆ II) (hII : II.Countable) :
    S.Countable := by
  exact hII.mono hS

/--
Original source (NL): The Fundamental Theorem's finite branch is compatible
with countability.
Original source (LaTeX): finite subsets are countable.
-/
theorem fundamental_finite_branch_countable {α : Type u} {S : Set α}
    (hS : S.Finite) :
    S.Countable := by
  exact hS.countable

/--
Original source (NL): Cantor-Bernstein for `(II)`: if a set of the power of
`(II)` embeds into an intermediate set and the intermediate set embeds back, the
two have equal power.
Original source (LaTeX): mutual one-one maps yield equipollence.
Generated note (NL): This is the modern Schroeder-Bernstein theorem from
mathlib.
-/
theorem cantor_bernstein_for_II_modern {α : Type u} {β : Type v}
    (f : α → β) (g : β → α)
    (hf : Injective f) (hg : Injective g) :
    Nonempty (α ≃ β) := by
  exact Function.Embedding.antisymm ⟨f, hf⟩ ⟨g, hg⟩

/--
Original source (NL): The set-theoretic inclusion form of the chapter's
Cantor-Bernstein argument uses the inclusion maps as injections.
Original source (LaTeX): from `M''\subseteq M'\subseteq M` together with a
reverse injection, obtain equal power.
-/
theorem cantor_bernstein_between_subsets {α : Type u} {Mpp Mp M : Set α}
    (hMpM : Mp ⊆ M) (hMppMp : Mpp ⊆ Mp)
    (reverse : M → Mpp) (hreverse : Injective reverse) :
    Nonempty (Mp ≃ M) := by
  let toM : Mp → M := fun x => ⟨x.1, hMpM x.2⟩
  have htoM : Injective toM := by
    intro x y hxy
    exact Subtype.ext (congr_arg (fun z : M => (z : α)) hxy)
  let toMp : M → Mp := fun x => ⟨(reverse x).1, hMppMp (reverse x).2⟩
  have htoMp : Injective toMp := by
    intro x y hxy
    exact hreverse (Subtype.ext (congr_arg (fun z : Mp => (z : α)) hxy))
  exact Function.Embedding.antisymm ⟨toM, htoM⟩ ⟨toMp, htoMp⟩

/--
Original source (NL): The Union Theorem for `V`: a union indexed by a class of
power `O`, with each member of power `O`, again has power `O`.
Original source (LaTeX): a countable analogue is
`\bigcup_{i\in I} A_i` countable when `I` and all `A_i` are countable.
Generated note (NL): This is the same countability theorem as the denumerable
union theorem, stated as a reusable union principle.
-/
theorem union_theorem_countable_version {ι : Type u} {α : Type v}
    [Countable ι] (A : ι → Set α) (hA : ∀ i, (A i).Countable) :
    (⋃ i, A i).Countable := by
  exact Set.countable_iUnion hA

/--
Original source (NL): Cantor's proof of the Union Theorem orders pairs and
uses the fact that a product of countable sets is countable.
Original source (LaTeX): `\aleph_0\cdot\aleph_0=\aleph_0`.
-/
theorem countable_product_component {α : Type u} {β : Type v}
    {A : Set α} {B : Set β} (hA : A.Countable) (hB : B.Countable) :
    (CantorPairMatrix A B).Countable := by
  unfold CantorPairMatrix
  exact hA.prod hB

/--
Original source (NL): The proof of the Denumerable Union Theorem is captured
by enumerating ordered pairs of positive integers.
Original source (LaTeX): `\mathbb N\times\mathbb N` is denumerable.
-/
theorem nat_pair_set_countable : (Set.univ : Set (ℕ × ℕ)).Countable := by
  exact Set.countable_univ

end AutoformalizedCBTChapter1
end Mathformer
