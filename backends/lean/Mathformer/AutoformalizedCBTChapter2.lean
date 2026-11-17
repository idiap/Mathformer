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

/-!
Original source (NL): Chapter 2 of the CBT textbook archive, "Generalizing
Cantor's CBT Proof", reconstructs Cantor's scale of number-classes beyond the
second number-class and states a helical transfinite induction package: Theorem
1, the Fundamental Theorem, the Limitation Theorem, the Different Alephs
Theorem, the Next-Aleph Theorem, the Cantor-Bernstein Theorem, the Union
Theorem, the Sum Lemma, and the Sequent Lemma.

Original source (LaTeX): core statements include `U_g`, `(g)`, `o_g`,
`(g-1) \not\sim U_k` for `k < g`, subsets of `U_g` are finite or have the
power of some `U_k`, `U_g \times U_g \sim U_g`, and if
`M'' \subseteq M' \subseteq M \sim M''` with `M` of the power of `U_g`, then
`M' \sim M`.

Generated note (NL): The historical construction uses Cantor's number-classes,
sequent operation, Limitation Principle, and an interdependent induction proof
not available as a ready-made mathlib object. This module therefore formalizes
the chapter as a reusable Lean schema: concrete equivalence algebra is proved
with mathlib subtypes, while the source's helical induction step is represented
as explicit data whose consequences are exposed by theorem projections.
-/

namespace Mathformer
namespace AutoformalizedCBTChapter2

open Function Set

universe u v w

/--
Generated note (NL): Two sets have the same power when their subtypes are
equivalent. This is the mathlib-compatible form of Cantor's equipollence
relation for the chapter.
Generated equivalent (LaTeX): `A \sim B := \exists e : A \simeq B`.
-/
def SamePower {α : Type u} {β : Type v} (A : Set α) (B : Set β) : Prop :=
  Nonempty (A ≃ B)

namespace SamePower

/--
Generated note (NL): Equipollence is reflexive for every set because Lean has
the identity equivalence on the corresponding subtype.
Generated equivalent (LaTeX): `A \sim A`.
-/
theorem refl {α : Type u} (A : Set α) : SamePower A A := by
  exact ⟨Equiv.refl A⟩

/--
Generated note (NL): Equipollence is symmetric by reversing the witnessing
equivalence.
Generated equivalent (LaTeX): `A \sim B \Rightarrow B \sim A`.
-/
theorem symm {α : Type u} {β : Type v} {A : Set α} {B : Set β}
    (h : SamePower A B) : SamePower B A := by
  rcases h with ⟨e⟩
  exact ⟨e.symm⟩

/--
Generated note (NL): Equipollence is transitive by composing subtype
equivalences.
Generated equivalent (LaTeX): `A \sim B \wedge B \sim C \Rightarrow A \sim C`.
-/
theorem trans {α : Type u} {β : Type v} {γ : Type w}
    {A : Set α} {B : Set β} {C : Set γ}
    (hAB : SamePower A B) (hBC : SamePower B C) : SamePower A C := by
  rcases hAB with ⟨eAB⟩
  rcases hBC with ⟨eBC⟩
  exact ⟨eAB.trans eBC⟩

/--
Generated note (NL): Any explicit subtype equivalence is a same-power witness.
Generated equivalent (LaTeX): `(A \simeq B) \Rightarrow A \sim B`.
-/
theorem of_equiv {α : Type u} {β : Type v} {A : Set α} {B : Set β}
    (e : A ≃ B) : SamePower A B := by
  exact ⟨e⟩

/--
Generated note (NL): Equipollence can be used in either direction, matching
Cantor's reciprocal-correlation language.
Generated equivalent (LaTeX): `A \sim B \leftrightarrow B \sim A`.
-/
theorem comm_iff {α : Type u} {β : Type v} {A : Set α} {B : Set β} :
    SamePower A B ↔ SamePower B A := by
  constructor
  · intro h
    exact symm h
  · intro h
    exact symm h

/--
Generated note (NL): A chain of two same-power witnesses may be composed
without naming the intermediate equivalence.
Generated equivalent (LaTeX): `(A \sim B \wedge B \sim C) \Rightarrow A\sim C`.
-/
theorem trans_of_and {α : Type u} {β : Type v} {γ : Type w}
    {A : Set α} {B : Set β} {C : Set γ}
    (h : SamePower A B ∧ SamePower B C) : SamePower A C := by
  rcases h with ⟨hAB, hBC⟩
  exact trans hAB hBC

end SamePower

/--
Original source (NL): The Union Theorem works with the set of ordered pairs of
numbers from `U_g`.
Original source (LaTeX): `U_g \times U_g`.
Generated note (NL): This definition keeps the chapter's ordered-pair matrix
visible while using mathlib's set product.
-/
def CantorPairMatrix {α : Type u} {β : Type v}
    (A : Set α) (B : Set β) : Set (α × β) :=
  A ×ˢ B

/--
Generated note (NL): The ordered-pair matrix is invariant up to equipollence
under swapping coordinates. This is a concrete mathlib equivalence, independent
of the historical induction assumptions.
Generated equivalent (LaTeX): `A \times B \sim B \times A`.
-/
theorem cantorPairMatrix_swap_samePower {α : Type u} {β : Type v}
    (A : Set α) (B : Set β) :
    SamePower (CantorPairMatrix A B) (CantorPairMatrix B A) := by
  refine ⟨?_⟩
  refine
    { toFun := fun x => ⟨(x.1.2, x.1.1), ?_⟩
      invFun := fun y => ⟨(y.1.2, y.1.1), ?_⟩
      left_inv := ?_
      right_inv := ?_ }
  · exact ⟨x.2.2, x.2.1⟩
  · exact ⟨y.2.2, y.2.1⟩
  · intro x
    ext <;> rfl
  · intro y
    ext <;> rfl

/--
Generated note (NL): Membership in the source's ordered-pair matrix is
preserved exactly by swapping the two coordinates and the two component sets.
Generated equivalent (LaTeX): `(a,b)\in A\times B \leftrightarrow
(b,a)\in B\times A`.
-/
theorem mem_cantorPairMatrix_swap_iff {α : Type u} {β : Type v}
    {A : Set α} {B : Set β} {p : α × β} :
    p ∈ CantorPairMatrix A B ↔ (p.2, p.1) ∈ CantorPairMatrix B A := by
  constructor
  · intro hp
    exact ⟨hp.2, hp.1⟩
  · intro hp
    exact ⟨hp.2, hp.1⟩

/--
Generated note (NL): The matrix swap gives a visible bidirectional subtype
equivalence, not merely a named same-power proposition.
Generated equivalent (LaTeX): `A \times B \simeq B \times A`.
-/
theorem cantorPairMatrix_swap_equiv_nonempty {α : Type u} {β : Type v}
    (A : Set α) (B : Set β) :
    Nonempty (CantorPairMatrix A B ≃ CantorPairMatrix B A) := by
  rcases cantorPairMatrix_swap_samePower A B with ⟨e⟩
  exact ⟨e⟩

/--
Original source (NL): The scale of number-classes consists of classes `(g)`,
initial numbers `o_g`, cumulative unions `U_g`, segment-sets of numbers, a sum
operation, and a sequent operation.
Original source (LaTeX): `(g)`, `o_g`, `U_g`, segment sets, `a+b`, and a
sequent of a succession.
Generated note (NL): The structure records only the data needed by the chapter's
induction pack, not an independent reconstruction of all Cantorian ordinals.
-/
structure CantorScale (Index : Type u) (Number : Type v)
    [Preorder Index] [Preorder Number] where
  numberClass : Index → Set Number
  initial : Index → Number
  cumulative : Index → Set Number
  segment : Number → Set Number
  sum : Number → Number → Number
  sequent : Set Number → Number
  initial_mem_class : ∀ g : Index, initial g ∈ numberClass g
  initial_segment_samePower_cumulative :
    ∀ g : Index, SamePower (segment (initial g)) (cumulative g)
  class_members_have_initial_power :
    ∀ {g : Index} {a : Number}, a ∈ numberClass g →
      SamePower (segment a) (segment (initial g))

/--
Original source (NL): A set has the power of `U_k` when it is equipollent with
the cumulative union of all earlier number-classes up to `k`.
Original source (LaTeX): `A \sim U_k`.
-/
def HasPowerOf {Index : Type u} {Number : Type v} [Preorder Index]
    [Preorder Number] (S : CantorScale Index Number) (A : Set Number)
    (k : Index) : Prop :=
  SamePower A (S.cumulative k)

/--
Original source (NL): The Fundamental Theorem says a subset of `U_g` is either
finite or has the power of some `U_k` with `k \le g`.
Original source (LaTeX): `A \subseteq U_g \Rightarrow
A\text{ finite } \vee \exists k \le g,\ A \sim U_k`.
-/
structure FundamentalAlternative {Index : Type u} {Number : Type v}
    [Preorder Index] [Preorder Number]
    (S : CantorScale Index Number) (g : Index) (A : Set Number) : Prop where
  finite_or_has_cumulative_power :
    A.Finite ∨ ∃ k : Index, k ≤ g ∧ HasPowerOf S A k

/--
Original source (NL): The Limitation Theorem identifies the power of the
previous number-class with `U_g` and with the segment determined by `o_g`.
Original source (LaTeX): `(g-1) \sim U_g \sim o_g`.
-/
structure LimitationConclusion {Index : Type u} {Number : Type v}
    [Preorder Index] [Preorder Number]
    (S : CantorScale Index Number) (pred g : Index) : Prop where
  class_samePower_cumulative : SamePower (S.numberClass pred) (S.cumulative g)
  initial_segment_samePower_cumulative :
    SamePower (S.segment (S.initial g)) (S.cumulative g)

/--
Original source (NL): The Sum Lemma says that if `a,b` are in `U_g`, then
`a+b` is in `U_g` and has the power of the greater summand.
Original source (LaTeX): `a,b\in U_g \Rightarrow a+b\in U_g`, with the power
of `a+b` equal to the power of one of the summands.
-/
structure SumLemmaConclusion {Index : Type u} {Number : Type v}
    [Preorder Index] [Preorder Number]
    (S : CantorScale Index Number) (g : Index) (a b : Number) : Prop where
  sum_mem_cumulative : S.sum a b ∈ S.cumulative g
  sum_power_left_or_right :
    SamePower (S.segment (S.sum a b)) (S.segment a) ∨
      SamePower (S.segment (S.sum a b)) (S.segment b)

/--
Original source (NL): The Sequent Lemma says that a sequence of members of
`(g)`, indexed below `o_g`, has a sequent still in `(g)`.
Original source (LaTeX): `(a_i)_{i<k\le o_g}\subseteq (g)` has a sequent in
`(g)`.
Generated note (NL): The index-bound side condition is represented by the
caller; this record captures the chapter's generated sequent and membership
conclusion.
-/
structure SequentLemmaConclusion {Index : Type u} {Number : Type v}
    [Preorder Index] [Preorder Number]
    (S : CantorScale Index Number) (g : Index)
    (seq : Index → Number) : Prop where
  sequent_mem_class : S.sequent (Set.range seq) ∈ S.numberClass g
  sequence_mem_class : ∀ i : Index, seq i ∈ S.numberClass g

/--
Original source (NL): Chapter 2's induction step proves the main statements in
tandem because the proofs of Theorem 1, the Fundamental Theorem, Limitation,
Different Alephs, CBT, Union, Sum, and Sequent Lemma depend on each other.
Original source (LaTeX): the induction hypothesis covers every `g_0` with
`3 \le g_0 < g`, and the step establishes the whole theorem pack for `g`.
Generated note (NL): This record is the formal interface for one completed
helical induction stage.
-/
structure HelicalInductionStep {Index : Type u} {Number : Type v}
    [Preorder Index] [Preorder Number]
    (S : CantorScale Index Number) (g pred : Index) where
  lower : Index → Prop
  lower_le_stage : ∀ {k : Index}, lower k → k < g
  lower_or_equal : Index → Prop
  predecessor_is_lower_or_equal : lower_or_equal pred
  theorem1 :
    ∀ k : Index, lower k → ¬ SamePower (S.numberClass pred) (S.cumulative k)
  fundamental :
    ∀ {A : Set Number}, A ⊆ S.cumulative g → FundamentalAlternative S g A
  limitation : LimitationConclusion S pred g
  different_alephs :
    ∀ k : Index, lower k → ¬ SamePower (S.cumulative g) (S.cumulative k)
  next_aleph :
    ∀ k : Index, lower k →
      ¬ ∃ A : Set Number, SamePower A (S.cumulative g) ∧ SamePower A (S.cumulative k)
  cantor_bernstein :
    ∀ {M M' M'' : Set Number}, HasPowerOf S M g →
      M'' ⊆ M' → M' ⊆ M → SamePower M M'' → SamePower M' M
  union_theorem : SamePower (CantorPairMatrix (S.cumulative g) (S.cumulative g))
    (S.cumulative g)
  sum_lemma :
    ∀ {a b : Number}, a ∈ S.cumulative g → b ∈ S.cumulative g →
      SumLemmaConclusion S g a b
  sequent_lemma :
    ∀ (seq : Index → Number),
      (∀ i : Index, seq i ∈ S.numberClass g) →
        SequentLemmaConclusion S g seq

/--
Original source (NL): Theorem 1: for successor `g`, the power of `(g-1)` is
different from the power of every `U_k` with `k < g`.
Original source (LaTeX): `(g-1) \not\sim U_k` for `k < g`.
-/
theorem chapter2_theorem1 {Index : Type u} {Number : Type v}
    [Preorder Index] [Preorder Number]
    {S : CantorScale Index Number} {g pred k : Index}
    (H : HelicalInductionStep S g pred) (hk : H.lower k) :
    ¬ SamePower (S.numberClass pred) (S.cumulative k) := by
  exact H.theorem1 k hk

/--
Original source (NL): The Fundamental Theorem: every subset of `U_g` is finite
or has the power of some `U_k` with `k \le g`.
Original source (LaTeX): `A \subseteq U_g \Rightarrow
A\text{ finite} \vee \exists k\le g,\ A\sim U_k`.
-/
theorem chapter2_fundamental_theorem {Index : Type u} {Number : Type v}
    [Preorder Index] [Preorder Number]
    {S : CantorScale Index Number} {g pred : Index} {A : Set Number}
    (H : HelicalInductionStep S g pred) (hA : A ⊆ S.cumulative g) :
    A.Finite ∨ ∃ k : Index, k ≤ g ∧ HasPowerOf S A k := by
  exact (H.fundamental hA).finite_or_has_cumulative_power

/--
Original source (NL): The Limitation Theorem identifies `(g-1)` with `U_g`
in power.
Original source (LaTeX): `(g-1) \sim U_g`.
-/
theorem chapter2_limitation_theorem {Index : Type u} {Number : Type v}
    [Preorder Index] [Preorder Number]
    {S : CantorScale Index Number} {g pred : Index}
    (H : HelicalInductionStep S g pred) :
    SamePower (S.numberClass pred) (S.cumulative g) := by
  exact H.limitation.class_samePower_cumulative

/--
Original source (NL): The initial number `o_g` has the same power as `U_g`.
Original source (LaTeX): `o_g \sim U_g`.
-/
theorem chapter2_initial_segment_has_stage_power {Index : Type u}
    {Number : Type v} [Preorder Index] [Preorder Number]
    {S : CantorScale Index Number} {g pred : Index}
    (H : HelicalInductionStep S g pred) :
    SamePower (S.segment (S.initial g)) (S.cumulative g) := by
  exact H.limitation.initial_segment_samePower_cumulative

/--
Original source (NL): The Limitation Theorem makes `o_g` fulfill the Limitation
Principle by matching the power of the previous number-class.
Original source (LaTeX): `o_g \sim (g-1)`.
-/
theorem chapter2_initial_fulfills_limitation {Index : Type u} {Number : Type v}
    [Preorder Index] [Preorder Number]
    {S : CantorScale Index Number} {g pred : Index}
    (H : HelicalInductionStep S g pred) :
    SamePower (S.segment (S.initial g)) (S.numberClass pred) := by
  exact SamePower.trans
    H.limitation.initial_segment_samePower_cumulative
    (SamePower.symm H.limitation.class_samePower_cumulative)

/--
Original source (NL): The Different Alephs Theorem: the power of `U_g` is
different from that of every earlier `U_k`.
Original source (LaTeX): `U_g \not\sim U_k` for `k < g`.
-/
theorem chapter2_different_alephs_theorem {Index : Type u} {Number : Type v}
    [Preorder Index] [Preorder Number]
    {S : CantorScale Index Number} {g pred k : Index}
    (H : HelicalInductionStep S g pred) (hk : H.lower k) :
    ¬ SamePower (S.cumulative g) (S.cumulative k) := by
  exact H.different_alephs k hk

/--
Original source (NL): The Next-Aleph Theorem says the next stage is not
represented by any earlier cumulative power.
Original source (LaTeX): `\aleph_{g+1}` is the next aleph after `\aleph_g`.
-/
theorem chapter2_next_aleph_theorem {Index : Type u} {Number : Type v}
    [Preorder Index] [Preorder Number]
    {S : CantorScale Index Number} {g pred k : Index}
    (H : HelicalInductionStep S g pred) (hk : H.lower k) :
    ¬ ∃ A : Set Number, SamePower A (S.cumulative g) ∧ SamePower A (S.cumulative k) := by
  exact H.next_aleph k hk

/--
Original source (NL): The generalized Cantor-Bernstein theorem: if
`M'' \subseteq M' \subseteq M`, `M` has the power of `U_g`, and
`M \sim M''`, then `M' \sim M`.
Original source (LaTeX): `M'' \le M' \le M \sim M'' \Rightarrow M' \sim M`.
-/
theorem chapter2_cantor_bernstein_theorem {Index : Type u} {Number : Type v}
    [Preorder Index] [Preorder Number]
    {S : CantorScale Index Number} {g pred : Index} {M M' M'' : Set Number}
    (H : HelicalInductionStep S g pred) (hM : HasPowerOf S M g)
    (hM''M' : M'' ⊆ M') (hM'M : M' ⊆ M) (hMM'' : SamePower M M'') :
    SamePower M' M := by
  exact H.cantor_bernstein hM hM''M' hM'M hMM''

/--
Original source (NL): The Union Theorem: the ordered-pair matrix of `U_g` is
equivalent to `U_g`.
Original source (LaTeX): `U_g \times U_g \sim U_g`.
-/
theorem chapter2_union_theorem {Index : Type u} {Number : Type v}
    [Preorder Index] [Preorder Number]
    {S : CantorScale Index Number} {g pred : Index}
    (H : HelicalInductionStep S g pred) :
    SamePower (CantorPairMatrix (S.cumulative g) (S.cumulative g)) (S.cumulative g) ∧
      (SamePower (CantorPairMatrix (S.cumulative g) (S.cumulative g)) (S.cumulative g) ↔
        SamePower (S.cumulative g) (CantorPairMatrix (S.cumulative g) (S.cumulative g))) := by
  constructor
  · exact H.union_theorem
  · constructor
    · intro h
      exact SamePower.symm h
    · intro h
      exact SamePower.symm h

/--
Original source (NL): The Sum Lemma membership conclusion: if `a,b` are in
`U_g`, then `a+b` is in `U_g`.
Original source (LaTeX): `a,b\in U_g \Rightarrow a+b\in U_g`.
-/
theorem chapter2_sum_lemma_mem {Index : Type u} {Number : Type v}
    [Preorder Index] [Preorder Number]
    {S : CantorScale Index Number} {g pred : Index} {a b : Number}
    (H : HelicalInductionStep S g pred)
    (ha : a ∈ S.cumulative g) (hb : b ∈ S.cumulative g) :
    S.sum a b ∈ S.cumulative g := by
  exact (H.sum_lemma ha hb).sum_mem_cumulative

/--
Original source (NL): The Sum Lemma power conclusion: the segment of `a+b`
has the power of one of the summand segments.
Original source (LaTeX): `|a+b|=|a|` or `|a+b|=|b|`.
-/
theorem chapter2_sum_lemma_power {Index : Type u} {Number : Type v}
    [Preorder Index] [Preorder Number]
    {S : CantorScale Index Number} {g pred : Index} {a b : Number}
    (H : HelicalInductionStep S g pred)
    (ha : a ∈ S.cumulative g) (hb : b ∈ S.cumulative g) :
    SamePower (S.segment (S.sum a b)) (S.segment a) ∨
      SamePower (S.segment (S.sum a b)) (S.segment b) := by
  exact (H.sum_lemma ha hb).sum_power_left_or_right

/--
Original source (NL): The Sequent Lemma: a sequence in `(g)` has a generated
sequent in `(g)`.
Original source (LaTeX): `(a_i)\subseteq (g) \Rightarrow
\operatorname{seq}(a_i)\in(g)`.
-/
theorem chapter2_sequent_lemma {Index : Type u} {Number : Type v}
    [Preorder Index] [Preorder Number]
    {S : CantorScale Index Number} {g pred : Index}
    (H : HelicalInductionStep S g pred) (seq : Index → Number)
    (hseq : ∀ i : Index, seq i ∈ S.numberClass g) :
    SequentLemmaConclusion S g seq := by
  exact H.sequent_lemma seq hseq

/--
Original source (NL): The Sequent Lemma's membership part gives the exact
membership-in-the-number-class conclusion for the generated sequent.
Original source (LaTeX): `\operatorname{seq}(a_i)\in(g)`.
-/
theorem chapter2_sequent_mem_class {Index : Type u} {Number : Type v}
    [Preorder Index] [Preorder Number]
    {S : CantorScale Index Number} {g pred : Index}
    (H : HelicalInductionStep S g pred) (seq : Index → Number)
    (hseq : ∀ i : Index, seq i ∈ S.numberClass g) :
    S.sequent (Set.range seq) ∈ S.numberClass g := by
  exact (H.sequent_lemma seq hseq).sequent_mem_class

/--
Original source (NL): Every member of a number-class has the power of the
initial number of that class.
Original source (LaTeX): `a\in(g) \Rightarrow a\sim o_g`.
-/
theorem chapter2_class_member_has_initial_power {Index : Type u}
    {Number : Type v} [Preorder Index] [Preorder Number]
    (S : CantorScale Index Number) {g : Index} {a : Number}
    (ha : a ∈ S.numberClass g) :
    SamePower (S.segment a) (S.segment (S.initial g)) := by
  exact S.class_members_have_initial_power ha

/--
Original source (NL): The initial number `o_g` is in the number-class `(g)`.
Original source (LaTeX): `o_g \in (g)`.
-/
theorem chapter2_initial_mem_class {Index : Type u} {Number : Type v}
    [Preorder Index] [Preorder Number]
    (S : CantorScale Index Number) (g : Index) :
    S.initial g ∈ S.numberClass g := by
  exact S.initial_mem_class g

/--
Original source (NL): The scale definition makes the segment of `o_g`
equipollent with `U_g`.
Original source (LaTeX): `o_g \sim U_g`.
-/
theorem chapter2_scale_initial_segment_samePower_cumulative {Index : Type u}
    {Number : Type v} [Preorder Index] [Preorder Number]
    (S : CantorScale Index Number) (g : Index) :
    SamePower (S.segment (S.initial g)) (S.cumulative g) := by
  exact S.initial_segment_samePower_cumulative g

end AutoformalizedCBTChapter2
end Mathformer
