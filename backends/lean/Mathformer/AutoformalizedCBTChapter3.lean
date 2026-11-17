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

import Mathlib.Data.Real.Basic
import Mathlib.Data.Set.Lattice
import Mathlib.Logic.Function.Basic
import Mathlib.SetTheory.Cardinal.SchroederBernstein

/-!
Original source (NL): Chapter 3 of the CBT textbook archive, "CBT in Cantor's
1878 Beitrag", argues that Cantor's use of equivalence classes, the order
relation between powers, the direct two-set allusion, Lemma G for `(0,1]` and
`[0,1]`, the comb/frame proof gestalt, and the discussion of different powers
all presuppose or point toward Cantor-Bernstein reasoning.

Original source (LaTeX): key chapter statements include `M \sim N`, partitions
of linear sets into equal-power classes, `C \subseteq B \subseteq A`, the
comparability assertion for powers, the two-set CBT allusion, Lemma G
`(0,1] \sim [0,1]`, the pushdown/simple-chain construction, frame matchings,
and diagonal evidence for powers above the continuum.

Source anchors: src_L0001-src_L0451

Generated note (NL): This module formalizes the chapter's reusable core in
mathlib-compatible terms.  Equipollence, power comparison by embeddings,
Schroeder-Bernstein antisymmetry, sandwich/single-set CBT, frame-indexed
tagged-union equivalence, and diagonal non-surjectivity are proved.  The
historical continuum comb construction and Cantor's Lemma G are represented as
explicit structures, because the extracted source gives a mathematical
construction narrative rather than a ready-made Lean homeomorphism or interval
equivalence proof.
-/

namespace Mathformer
namespace AutoformalizedCBTChapter3

open Function Set

universe u v w

/--
Original source (NL): Cantor says that two well-defined sets fully and
unequivocally correlate element by element exactly when they have equal power,
or are equivalent.
Original source (LaTeX): `M \sim N`.
Source anchors: src_L0015-src_L0022; src_L0043-src_L0047
Generated note (NL): In mathlib-compatible form, `SamePower A B` is
`Nonempty (A ≃ B)`, an equivalence between set subtypes.
-/
def SamePower {α : Type u} {β : Type v} (A : Set α) (B : Set β) : Prop :=
  Nonempty (A ≃ B)

namespace SamePower

/--
Original source (NL): Cantor did not prove that `\sim` is reflexive, symmetric,
and transitive; this later became the customary rhythm for equivalence
relations.
Original source (LaTeX): `A \sim A`.
Source anchors: src_L0048-src_L0052
Generated note (NL): The Lean signature is exactly `SamePower A A`.
-/
theorem refl {α : Type u} (A : Set α) : SamePower A A := by
  exact ⟨Equiv.refl A⟩

/--
Original source (NL): Cantor's relation of equivalence between sets is
symmetric in modern equivalence-relation form.
Original source (LaTeX): `A \sim B \Rightarrow B \sim A`.
Source anchors: src_L0048-src_L0052
Generated note (NL): The Lean signature turns `SamePower A B` into
`SamePower B A`.
-/
theorem symm {α : Type u} {β : Type v} {A : Set α} {B : Set β}
    (h : SamePower A B) : SamePower B A := by
  rcases h with ⟨e⟩
  exact ⟨e.symm⟩

/--
Original source (NL): Cantor's equivalence of sets is transitive in modern
equivalence-relation form.
Original source (LaTeX): `A \sim B \wedge B \sim C \Rightarrow A \sim C`.
Source anchors: src_L0048-src_L0052
Generated note (NL): The Lean signature composes `SamePower A B` and
`SamePower B C` into `SamePower A C`.
-/
theorem trans {α : Type u} {β : Type v} {γ : Type w}
    {A : Set α} {B : Set β} {C : Set γ}
    (hAB : SamePower A B) (hBC : SamePower B C) : SamePower A C := by
  rcases hAB with ⟨eAB⟩
  rcases hBC with ⟨eBC⟩
  exact ⟨eAB.trans eBC⟩

end SamePower

/--
Original source (NL): Cantor's later definition of a well-defined set requires
that membership and equality of objects in the same conceptual sphere be
determined.
Original source (LaTeX): membership and equality are determined by the logical
principle of excluded third.
Source anchors: src_L0023-src_L0033
Generated note (NL): This record keeps the source's conceptual-sphere
condition explicit.
-/
structure CantorWellDefinedSet (ConceptualSphere : Type u) where
  carrier : Set ConceptualSphere
  membership_decidable : ∀ x : ConceptualSphere, Decidable (x ∈ carrier)
  equality_decidable : ∀ x y : ConceptualSphere, Decidable (x = y)

/--
Original source (NL): The partitions in Cantor's continuum-hypothesis
formulation are equivalence classes for the relation of equal power.
Original source (LaTeX): sets of equal power are put in the same partition.
Source anchors: src_L0034-src_L0042
-/
def PowerClass {α : Type u} (A : Set α) : Set (Set α) :=
  {B | SamePower B A}

/--
Original source (NL): A set belongs to the equal-power class of `A` exactly
when it is equivalent to `A`.
Original source (LaTeX): `B \in [A]_\sim \leftrightarrow B \sim A`.
Source anchors: src_L0034-src_L0042
-/
theorem mem_powerClass_iff {α : Type u} {A B : Set α} :
    B ∈ PowerClass A ↔ SamePower B A := by
  rfl

/--
Generated note (NL): An inclusion of sets induces an embedding of subtypes.
Generated equivalent (LaTeX): `A\subseteq B \Rightarrow A \hookrightarrow B`.
Source anchors: src_L0053-src_L0056
-/
def inclusionEmbedding {α : Type u} {A B : Set α} (hAB : A ⊆ B) : A ↪ B where
  toFun x := ⟨x.1, hAB x.2⟩
  inj' := by
    intro x y hxy
    cases x with
    | mk xv hx =>
      cases y with
      | mk yv hy =>
        simp at hxy
        simp [hxy]

/--
Generated note (NL): Embeddings compose.  This small helper keeps the
Schroeder-Bernstein applications below independent of method names.
Generated equivalent (LaTeX): `(A\hookrightarrow B) \wedge (B\hookrightarrow C)
\Rightarrow A\hookrightarrow C`.
Source anchors: src_L0073-src_L0096
-/
def embeddingTrans {α : Type u} {β : Type v} {γ : Type w}
    (f : α ↪ β) (g : β ↪ γ) : α ↪ γ where
  toFun x := g (f x)
  inj' := by
    intro x y hxy
    exact f.injective (g.injective hxy)

/--
Original source (NL): If `C \subseteq B \subseteq A` and `A` and `C` are in
one equivalence class, CBT excludes `B` from being in a different class.
Original source (LaTeX): `C \subseteq B \subseteq A` and `A \sim C`
imply `A \sim B`.
Source anchors: src_L0053-src_L0059
Generated note (NL): This is the single-set sandwich form of
Schroeder-Bernstein: from subsets `C ⊆ B ⊆ A` and `SamePower A C`, Lean proves
`SamePower A B`.
-/
theorem samePower_of_subset_sandwich {α : Type u} {A B C : Set α}
    (hCB : C ⊆ B) (hBA : B ⊆ A) (hAC : SamePower A C) :
    SamePower A B := by
  rcases hAC with ⟨eAC⟩
  exact Function.Embedding.antisymm
    (embeddingTrans eAC.toEmbedding (inclusionEmbedding hCB))
    (inclusionEmbedding hBA)

/--
Original source (NL): The order between powers is introduced by saying that
`M` has smaller power than `N` when `M` has equal power with a subset of `N`.
Original source (LaTeX): `M \preceq N` iff there is an injection from `M` into
`N`, equivalently `M` is equipollent with a subset of `N`.
Source anchors: src_L0073-src_L0075
-/
def PowerLE {α : Type u} {β : Type v} (A : Set α) (B : Set β) : Prop :=
  Nonempty (A ↪ B)

/--
Original source (NL): Having equal power with a subset of `B` gives the
smaller-or-equal relation between powers.
Original source (LaTeX): `A \sim C \subseteq B \Rightarrow A \preceq B`.
Source anchors: src_L0073-src_L0078
Generated note (NL): The Lean signature turns a subset map `C ⊆ B` and
`SamePower A C` into `PowerLE A B`.
-/
theorem powerLE_of_samePower_subset {α : Type u} {β : Type v}
    {A : Set α} {B C : Set β} (hCB : C ⊆ B) (hAC : SamePower A C) :
    PowerLE A B := by
  rcases hAC with ⟨eAC⟩
  exact ⟨embeddingTrans eAC.toEmbedding (inclusionEmbedding hCB)⟩

/--
Original source (NL): Every set has power less than or equal to itself.
Original source (LaTeX): `A \preceq A`.
Source anchors: src_L0073-src_L0086
-/
theorem powerLE_refl {α : Type u} (A : Set α) : PowerLE A A := by
  exact ⟨(Equiv.refl A).toEmbedding⟩

/--
Original source (NL): Transitivity is essential for Cantor's order relation
between powers.
Original source (LaTeX): `A \preceq B \wedge B \preceq C \Rightarrow
A \preceq C`.
Source anchors: src_L0082-src_L0096
Generated note (NL): The Lean signature composes `PowerLE A B` and `PowerLE B C`
into `PowerLE A C`.
-/
theorem powerLE_trans {α : Type u} {β : Type v} {γ : Type w}
    {A : Set α} {B : Set β} {C : Set γ}
    (hAB : PowerLE A B) (hBC : PowerLE B C) : PowerLE A C := by
  rcases hAB with ⟨eAB⟩
  rcases hBC with ⟨eBC⟩
  exact ⟨embeddingTrans eAB eBC⟩

/--
Original source (NL): The mutual exclusivity or antisymmetry of the two cases
of power inequality is exactly the two-set form of CBT.
Original source (LaTeX): `(A \preceq B \wedge B \preceq A) \Rightarrow
A \sim B`.
Source anchors: src_L0087-src_L0096; src_L0168-src_L0172
Generated note (NL): The Lean signature is the Schroeder-Bernstein step from
`PowerLE A B` and `PowerLE B A` to `SamePower A B`.
-/
theorem powerLE_antisymm_samePower {α : Type u} {β : Type v}
    {A : Set α} {B : Set β} (hAB : PowerLE A B) (hBA : PowerLE B A) :
    SamePower A B := by
  rcases hAB with ⟨eAB⟩
  rcases hBA with ⟨eBA⟩
  exact Function.Embedding.antisymm eAB eBA

/--
Original source (NL): Smaller power means embeddability into the other set
without equal power.
Original source (LaTeX): `A \prec B := A \preceq B \wedge \neg A\sim B`.
Source anchors: src_L0073-src_L0096
-/
def PowerLT {α : Type u} {β : Type v} (A : Set α) (B : Set β) : Prop :=
  PowerLE A B ∧ ¬ SamePower A B

/--
Original source (NL): The two cases of strict power inequality must be mutually
exclusive.
Original source (LaTeX): not both `A \prec B` and `B \prec A`.
Source anchors: src_L0087-src_L0093
Generated note (NL): The Lean signature proves `¬ PowerLT B A` from
`PowerLT A B`.
-/
theorem powerLT_asymm {α : Type u} {β : Type v} {A : Set α} {B : Set β}
    (hAB : PowerLT A B) : ¬ PowerLT B A := by
  intro hBA
  exact hAB.2 (powerLE_antisymm_samePower hAB.1 hBA.1)

/--
Original source (NL): Cantor's comparability assertion says that two
non-equivalent sets must be comparable by power.
Original source (LaTeX): if `\neg M\sim N`, then `M \preceq N` or
`N \preceq M`.
Source anchors: src_L0073-src_L0086
-/
structure CantorComparability (α : Type u) where
  comparable : ∀ A B : Set α, ¬ SamePower A B → PowerLE A B ∨ PowerLE B A

/--
Original source (NL): Comparability plus mutual exclusivity entails the
two-set CBT principle.
Original source (LaTeX): antisymmetry of `\preceq` gives
`A \preceq B \wedge B \preceq A \Rightarrow A \sim B`.
Source anchors: src_L0087-src_L0096
Generated note (NL): The Lean signature derives `SamePower A B` from the two
embedding-order hypotheses `PowerLE A B` and `PowerLE B A`.
-/
theorem twoSetCBT_from_power_antisymmetry {α : Type u} {A B : Set α}
    (hAB : PowerLE A B) (hBA : PowerLE B A) : SamePower A B := by
  exact powerLE_antisymm_samePower hAB hBA

/--
Original source (NL): A set is reflexive if it is equivalent to one of its
proper subsets.
Original source (LaTeX): `\exists B \subsetneq A,\ A \sim B`.
Source anchors: src_L0097-src_L0106
-/
def ProperSubset {α : Type u} (B A : Set α) : Prop :=
  B ⊆ A ∧ ∃ a ∈ A, a ∉ B

/--
Original source (NL): Infinite sets are characterized in the passage by the
possibility of being equivalent to a proper subset.
Original source (LaTeX): `A` is reflexive iff it has an equivalent proper
subset.
Source anchors: src_L0099-src_L0106
-/
def CantorReflexive {α : Type u} (A : Set α) : Prop :=
  ∃ B : Set α, ProperSubset B A ∧ SamePower A B

/--
Original source (NL): The direct allusion warns that mere inclusion or a
one-one correspondence into another set is not enough to infer strict inequality
of powers without knowing non-equivalence.
Original source (LaTeX): `A \preceq B` alone does not imply `A \prec B`.
Source anchors: src_L0102-src_L0113
-/
theorem not_powerLT_of_samePower {α : Type u} {β : Type v}
    {A : Set α} {B : Set β} (h : SamePower A B) : ¬ PowerLT A B := by
  intro hlt
  exact hlt.2 h

/--
Original source (NL): Lemma G says that the open-closed interval `(0,1]` has
the same power as the closed interval `[0,1]`.
Original source (LaTeX): `(0,1] \sim [0,1]`.
Source anchors: src_L0114-src_L0121
-/
def ClosedUnit : Set ℝ :=
  Set.Icc (0 : ℝ) 1

/--
Original source (NL): In current notation, `y` ranges over `(0,1]`.
Original source (LaTeX): `(0,1]`.
Source anchors: src_L0118-src_L0121
-/
def OpenClosedUnit : Set ℝ :=
  Set.Ioc (0 : ℝ) 1

/--
Original source (NL): Cantor's Lemma G is represented as the equivalence data
between `(0,1]` and `[0,1]`.
Original source (LaTeX): `(0,1] \sim [0,1]`.
Source anchors: src_L0116-src_L0135
Generated note (NL): The source describes Cantor's geometric/analytic
construction.  This record preserves the theorem as explicit data so downstream
formalization can later replace it with a fully analytic interval equivalence.
-/
structure CantorLemmaG where
  equivalence : SamePower OpenClosedUnit ClosedUnit

/--
Original source (NL): Lemma G supplies the same-power relation between the
open-closed and closed unit intervals.
Original source (LaTeX): `(0,1] \sim [0,1]`.
Source anchors: src_L0116-src_L0135
Generated note (NL): The Lean signature extracts `SamePower OpenClosedUnit
ClosedUnit` from the `CantorLemmaG` evidence record.
-/
theorem cantorLemmaG_samePower (G : CantorLemmaG) :
    SamePower OpenClosedUnit ClosedUnit := by
  exact G.equivalence

/--
Original source (NL): The discrete set of points of `[0,1]` is mapped to the
corresponding discrete set in `(0,1]` by pushing `0` down the chain.
Original source (LaTeX): `0, 1/2, \ldots` maps to `1/2, \ldots`.
Source anchors: src_L0131-src_L0140
Generated note (NL): The abstract chain core is the equivalence between natural
numbers and positive natural numbers by successor.
-/
def positiveNat : Set ℕ :=
  {n | 0 < n}

/--
Original source (NL): Pushing the first point down the simple chain gives a
bijection from the whole discrete chain to the chain with the first point
omitted.
Original source (LaTeX): `n \mapsto n+1`.
Source anchors: src_L0131-src_L0140
-/
def natPositiveEquiv : ℕ ≃ positiveNat where
  toFun n := ⟨n + 1, Nat.succ_pos n⟩
  invFun n := n.1 - 1
  left_inv := by
    intro n
    simp
  right_inv := by
    intro n
    cases n with
    | mk k hk =>
      apply Subtype.ext
      exact Nat.succ_pred_eq_of_pos hk

/--
Original source (NL): Let the conditions of the single-set formulation of CBT
hold with `M` of the power of the continuum; then the comb/pushdown mapping
gives an equivalence from `M` onto `M'`.
Original source (LaTeX): `M'' \subseteq M' \subseteq M` and `M \sim M''`
imply `M \sim M'`.
Source anchors: src_L0147-src_L0163
Generated note (NL): The Lean signature proves `SamePower M Mp` from
`Mpp ⊆ Mp`, `Mp ⊆ M`, and `SamePower M Mpp`.
-/
theorem singleSetCBT_of_sandwich {α : Type u} {M Mp Mpp : Set α}
    (hMppMp : Mpp ⊆ Mp) (hMpM : Mp ⊆ M) (hMMpp : SamePower M Mpp) :
    SamePower M Mp := by
  exact samePower_of_subset_sandwich hMppMp hMpM hMMpp

/--
Original source (NL): The continuum comb proof uses disjoint open-closed
segments `S_b` standing over each `b` and pushes members down their chains.
Original source (LaTeX): `S_b` and the map `{b}\cup S_b \to S_b`.
Source anchors: src_L0141-src_L0159
Generated note (NL): This structure records the local chain data used by the
comb proof without committing to a particular analytic construction of each
segment inside `[0,1]`.
-/
structure ContinuumComb (Base Point : Type u) where
  segment : Base → Set Point
  markedPoint : Base → Point
  marked_mem_extended : ∀ b : Base, markedPoint b ∈ ({markedPoint b} ∪ segment b)
  pushdown :
    ∀ b : Base, SamePower ({markedPoint b} ∪ segment b : Set Point) (segment b)

/--
Original source (NL): Each tooth of the comb carries the local pushdown
equivalence from the marked point plus its segment onto the open-closed segment.
Original source (LaTeX): `{b}\cup S_b \sim S_b`.
Source anchors: src_L0153-src_L0163
-/
theorem continuumComb_tooth_samePower {Base Point : Type u}
    (C : ContinuumComb Base Point) (b : Base) :
    SamePower ({C.markedPoint b} ∪ C.segment b : Set Point) (C.segment b) := by
  exact C.pushdown b

/--
Original source (NL): The generalized drawing proof matches sub-segments,
later called frames, by crisscross equivalences.
Original source (LaTeX): frames `aa'`, `b'b''`, `bb'`, `a'a''`, ...
Source anchors: src_L0199-src_L0213
-/
structure FrameMatching (ι : Type u) (α : Type v) (β : Type w) where
  leftFrame : ι → Set α
  rightFrame : ι → Set β
  frameEquiv : ∀ i : ι, leftFrame i ≃ rightFrame i

/--
Original source (NL): Because corresponding frames are equivalent, their
disjoint framed unions are equivalent.
Original source (LaTeX): if each frame pair is equivalent, the frame-indexed
unions are equivalent.
Source anchors: src_L0199-src_L0206
Generated note (NL): Tagged sigma types are the mathlib-safe version of
disjoint unions of frames, and `sigmaFrameEquiv` builds an `Equiv` between the
two sigma frame spaces.
-/
def sigmaFrameEquiv {ι : Type u} {α : Type v} {β : Type w}
    (A : ι → Set α) (B : ι → Set β) (e : ∀ i : ι, A i ≃ B i) :
    (Sigma fun i : ι => A i) ≃ (Sigma fun i : ι => B i) where
  toFun x := ⟨x.1, e x.1 x.2⟩
  invFun y := ⟨y.1, (e y.1).symm y.2⟩
  left_inv := by
    intro x
    cases x with
    | mk i a =>
      simp
  right_inv := by
    intro y
    cases y with
    | mk i b =>
      simp

/--
Original source (NL): The frame proof can be generalized to any sets by taking
the given mappings instead of the parallel lines used in the drawing.
Original source (LaTeX): replace parallels by arbitrary one-one maps between
corresponding frames.
Source anchors: src_L0207-src_L0219
Generated note (NL): The Lean signature proves `SamePower` between universal
sets over the tagged sigma frame spaces.
-/
theorem frameMatching_taggedUnion_samePower {ι : Type u}
    {α : Type v} {β : Type w} (F : FrameMatching ι α β) :
    SamePower (Set.univ : Set (Sigma fun i : ι => F.leftFrame i))
      (Set.univ : Set (Sigma fun i : ι => F.rightFrame i)) := by
  refine ⟨?_⟩
  exact Equiv.Set.univ _ |>.trans (sigmaFrameEquiv F.leftFrame F.rightFrame F.frameEquiv |>.trans (Equiv.Set.univ _).symm)

/--
Original source (NL): Cantor's drawing also yields the single-set formulation:
one maps each triangular frame to the next and leaves all other points fixed.
Original source (LaTeX): frame shift plus identity outside the framed part.
Source anchors: src_L0214-src_L0222
Generated note (NL): This structure records the abstract ingredients of such a
single-set frame shift.
-/
structure SingleSetFrameShift (α : Type u) (ι : Type v) where
  bigSet : Set α
  middleSet : Set α
  smallSet : Set α
  small_subset_middle : smallSet ⊆ middleSet
  middle_subset_big : middleSet ⊆ bigSet
  frameIndex : ι → Set α
  shift_equiv : SamePower bigSet smallSet

/--
Original source (NL): A single-set frame shift with `smallSet \subseteq
middleSet \subseteq bigSet` yields the single-set CBT conclusion.
Original source (LaTeX): `small \subseteq middle \subseteq big` and
`big \sim small` imply `big \sim middle`.
Source anchors: src_L0214-src_L0219
-/
theorem singleSetFrameShift_samePower {α : Type u} {ι : Type v}
    (S : SingleSetFrameShift α ι) : SamePower S.bigSet S.middleSet := by
  exact singleSetCBT_of_sandwich S.small_subset_middle S.middle_subset_big S.shift_equiv

/--
Original source (NL): Cantor knew that the positive integers and the continuum
have different powers.
Original source (LaTeX): `\mathbb N \not\sim \mathbb R`.
Source anchors: src_L0246-src_L0258
Generated note (NL): We expose the standard diagonal obstruction: no type
surjects onto its powerset, formalized as `¬ Surjective f`.
-/
theorem no_surjective_to_powerset {α : Type u} (f : α → Set α) :
    ¬ Surjective f := by
  exact Function.cantor_surjective f

/--
Original source (NL): A direct proof that the set of all real functions has
power greater than the power of `R` is obtained by diagonalizing.
Original source (LaTeX): define `g` by changing the diagonal value of `f_x`.
Source anchors: src_L0279-src_L0286
Generated note (NL): The Boolean-valued version is the clean set-theoretic
diagonal core of the real-function argument, formalized as `¬ Surjective F`.
-/
theorem no_surjective_to_bool_functions {α : Type u} (F : α → α → Bool) :
    ¬ Surjective F := by
  intro hsurj
  let g : α → Bool := fun x => !F x x
  rcases hsurj g with ⟨x, hx⟩
  have hdiag : F x x = !F x x := by
    simpa [g] using congrFun hx x
  cases hFx : F x x <;> simp [hFx] at hdiag

/--
Original source (NL): Cantor's comparison program compares natural
mathematical sets by their powers and motivates the comparability assertion.
Original source (LaTeX): compare powers of `\mathbb N`, `\mathbb R`, `(II)`,
and function spaces.
Source anchors: src_L0246-src_L0312
Generated note (NL): The record stores a finite observed comparison program
with a diagonal higher-power witness.
-/
structure CantorComparisonProgram where
  NaturalPower : Type u
  ContinuumPower : Type v
  HigherPower : Type w
  natural_embeds_continuum : Nonempty (NaturalPower ↪ ContinuumPower)
  continuum_embeds_higher : Nonempty (ContinuumPower ↪ HigherPower)
  higher_not_below_continuum : ¬ Nonempty (HigherPower ↪ ContinuumPower)

/--
Original source (NL): If a higher power does not embed into the continuum,
then it is not equipollent with the continuum.
Original source (LaTeX): `Higher \not\preceq Continuum \Rightarrow
Higher \not\sim Continuum`.
Source anchors: src_L0279-src_L0286
Generated note (NL): The Lean signature proves `¬ Nonempty (HigherPower ≃
ContinuumPower)` from a missing embedding witness into the continuum.
-/
theorem higher_not_samePower_continuum (P : CantorComparisonProgram) :
    ¬ Nonempty (P.HigherPower ≃ P.ContinuumPower) := by
  intro h
  rcases h with ⟨e⟩
  exact P.higher_not_below_continuum ⟨e.toEmbedding⟩

/--
Original source (NL): Cantor's denumerable union theorem and denumerable CBT
could be used with the Sequent Lemma to prove non-denumerability of `(II)`.
Original source (LaTeX): the denumerability proofs plus sequent lemma separate
`(II)` from the first number-class.
Source anchors: src_L0288-src_L0335
Generated note (NL): The source-level argument is recorded as a reusable
evidence packet rather than as a construction of Cantor's historical second
number-class.
-/
structure SecondNumberClassEvidence (FirstClass SecondClass : Type u) where
  first_embeds_second : Nonempty (FirstClass ↪ SecondClass)
  second_not_denumerable : ¬ Nonempty (SecondClass ↪ ℕ)
  sequent_generation_principle_available : Prop
  denumerable_union_available : Prop
  denumerable_CBT_available : Prop

/--
Original source (NL): If the second number-class does not embed into `N`, then
it cannot have the same power as `N`.
Original source (LaTeX): `(II) \not\preceq \mathbb N \Rightarrow
(II) \not\sim \mathbb N`.
Source anchors: src_L0288-src_L0335
Generated note (NL): The Lean signature proves `¬ Nonempty (SecondClass ≃ ℕ)`
from `second_not_denumerable`.
-/
theorem secondClass_not_samePower_nat {FirstClass SecondClass : Type u}
    (E : SecondNumberClassEvidence FirstClass SecondClass) :
    ¬ Nonempty (SecondClass ≃ ℕ) := by
  intro h
  rcases h with ⟨e⟩
  exact E.second_not_denumerable ⟨e.toEmbedding⟩

end AutoformalizedCBTChapter3
end Mathformer
