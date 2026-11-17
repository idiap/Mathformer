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

# `Mathformer.AutoformalizedCBTChapter2`

[Back to index](../../INDEX.md)

## Metadata

- Source: [backends/lean/Mathformer/AutoformalizedCBTChapter2.lean](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter2.lean)
- Status: `candidate`
- SHA-256: `dc42668dccc74477a3ac23f8e76a830f49a3a3ad47823994909517be4c3c5601`
- Declarations: `34`

## Imports

```lean
import Mathlib.Data.Set.Countable
import Mathlib.Logic.Function.Basic
```

## Module Source Notes

**Original Source**

Chapter 2 of the CBT textbook archive, "Generalizing Cantor's CBT Proof", reconstructs Cantor's scale of number-classes beyond the second number-class and states a helical transfinite induction package: Theorem 1, the Fundamental Theorem, the Limitation Theorem, the Different Alephs Theorem, the Next-Aleph Theorem, the Cantor-Bernstein Theorem, the Union Theorem, the Sum Lemma, and the Sequent Lemma.

**Original LaTeX**

```latex
core statements include `U_g`, `(g)`, `o_g`,
`(g-1) \not\sim U_k` for `k < g`, subsets of `U_g` are finite or have the
power of some `U_k`, `U_g \times U_g \sim U_g`, and if
`M'' \subseteq M' \subseteq M \sim M''` with `M` of the power of `U_g`, then
`M' \sim M`.
```

$$
U_g
$$

$$
(g)
$$

$$
o_g
$$

**Generated Notes**

The historical construction uses Cantor's number-classes, sequent operation, Limitation Principle, and an interdependent induction proof not available as a ready-made mathlib object. This module therefore formalizes the chapter as a reusable Lean schema: concrete equivalence algebra is proved with mathlib subtypes, while the source's helical induction step is represented as explicit data whose consequences are exposed by theorem projections.

## Declarations

- [`Mathformer.AutoformalizedCBTChapter2.SamePower`](#mathformer-autoformalizedcbtchapter2-samepower) (def, line 48)
- [`Mathformer.AutoformalizedCBTChapter2.SamePower.refl`](#mathformer-autoformalizedcbtchapter2-samepower-refl) (theorem, line 58)
- [`Mathformer.AutoformalizedCBTChapter2.SamePower.symm`](#mathformer-autoformalizedcbtchapter2-samepower-symm) (theorem, line 66)
- [`Mathformer.AutoformalizedCBTChapter2.SamePower.trans`](#mathformer-autoformalizedcbtchapter2-samepower-trans) (theorem, line 76)
- [`Mathformer.AutoformalizedCBTChapter2.SamePower.of_equiv`](#mathformer-autoformalizedcbtchapter2-samepower-of-equiv) (theorem, line 87)
- [`Mathformer.AutoformalizedCBTChapter2.SamePower.comm_iff`](#mathformer-autoformalizedcbtchapter2-samepower-comm-iff) (theorem, line 96)
- [`Mathformer.AutoformalizedCBTChapter2.SamePower.trans_of_and`](#mathformer-autoformalizedcbtchapter2-samepower-trans-of-and) (theorem, line 109)
- [`Mathformer.AutoformalizedCBTChapter2.CantorPairMatrix`](#mathformer-autoformalizedcbtchapter2-cantorpairmatrix) (def, line 124)
- [`Mathformer.AutoformalizedCBTChapter2.cantorPairMatrix_swap_samePower`](#mathformer-autoformalizedcbtchapter2-cantorpairmatrix-swap-samepower) (theorem, line 134)
- [`Mathformer.AutoformalizedCBTChapter2.mem_cantorPairMatrix_swap_iff`](#mathformer-autoformalizedcbtchapter2-mem-cantorpairmatrix-swap-iff) (theorem, line 156)
- [`Mathformer.AutoformalizedCBTChapter2.cantorPairMatrix_swap_equiv_nonempty`](#mathformer-autoformalizedcbtchapter2-cantorpairmatrix-swap-equiv-nonempty) (theorem, line 170)
- [`Mathformer.AutoformalizedCBTChapter2.CantorScale`](#mathformer-autoformalizedcbtchapter2-cantorscale) (structure, line 185)
- [`Mathformer.AutoformalizedCBTChapter2.HasPowerOf`](#mathformer-autoformalizedcbtchapter2-haspowerof) (def, line 205)
- [`Mathformer.AutoformalizedCBTChapter2.FundamentalAlternative`](#mathformer-autoformalizedcbtchapter2-fundamentalalternative) (structure, line 216)
- [`Mathformer.AutoformalizedCBTChapter2.LimitationConclusion`](#mathformer-autoformalizedcbtchapter2-limitationconclusion) (structure, line 227)
- [`Mathformer.AutoformalizedCBTChapter2.SumLemmaConclusion`](#mathformer-autoformalizedcbtchapter2-sumlemmaconclusion) (structure, line 240)
- [`Mathformer.AutoformalizedCBTChapter2.SequentLemmaConclusion`](#mathformer-autoformalizedcbtchapter2-sequentlemmaconclusion) (structure, line 257)
- [`Mathformer.AutoformalizedCBTChapter2.HelicalInductionStep`](#mathformer-autoformalizedcbtchapter2-helicalinductionstep) (structure, line 273)
- [`Mathformer.AutoformalizedCBTChapter2.chapter2_theorem1`](#mathformer-autoformalizedcbtchapter2-chapter2-theorem1) (theorem, line 308)
- [`Mathformer.AutoformalizedCBTChapter2.chapter2_fundamental_theorem`](#mathformer-autoformalizedcbtchapter2-chapter2-fundamental-theorem) (theorem, line 321)
- [`Mathformer.AutoformalizedCBTChapter2.chapter2_limitation_theorem`](#mathformer-autoformalizedcbtchapter2-chapter2-limitation-theorem) (theorem, line 333)
- [`Mathformer.AutoformalizedCBTChapter2.chapter2_initial_segment_has_stage_power`](#mathformer-autoformalizedcbtchapter2-chapter2-initial-segment-has-stage-power) (theorem, line 344)
- [`Mathformer.AutoformalizedCBTChapter2.chapter2_initial_fulfills_limitation`](#mathformer-autoformalizedcbtchapter2-chapter2-initial-fulfills-limitation) (theorem, line 356)
- [`Mathformer.AutoformalizedCBTChapter2.chapter2_different_alephs_theorem`](#mathformer-autoformalizedcbtchapter2-chapter2-different-alephs-theorem) (theorem, line 370)
- [`Mathformer.AutoformalizedCBTChapter2.chapter2_next_aleph_theorem`](#mathformer-autoformalizedcbtchapter2-chapter2-next-aleph-theorem) (theorem, line 382)
- [`Mathformer.AutoformalizedCBTChapter2.chapter2_cantor_bernstein_theorem`](#mathformer-autoformalizedcbtchapter2-chapter2-cantor-bernstein-theorem) (theorem, line 395)
- [`Mathformer.AutoformalizedCBTChapter2.chapter2_union_theorem`](#mathformer-autoformalizedcbtchapter2-chapter2-union-theorem) (theorem, line 408)
- [`Mathformer.AutoformalizedCBTChapter2.chapter2_sum_lemma_mem`](#mathformer-autoformalizedcbtchapter2-chapter2-sum-lemma-mem) (theorem, line 428)
- [`Mathformer.AutoformalizedCBTChapter2.chapter2_sum_lemma_power`](#mathformer-autoformalizedcbtchapter2-chapter2-sum-lemma-power) (theorem, line 441)
- [`Mathformer.AutoformalizedCBTChapter2.chapter2_sequent_lemma`](#mathformer-autoformalizedcbtchapter2-chapter2-sequent-lemma) (theorem, line 456)
- [`Mathformer.AutoformalizedCBTChapter2.chapter2_sequent_mem_class`](#mathformer-autoformalizedcbtchapter2-chapter2-sequent-mem-class) (theorem, line 469)
- [`Mathformer.AutoformalizedCBTChapter2.chapter2_class_member_has_initial_power`](#mathformer-autoformalizedcbtchapter2-chapter2-class-member-has-initial-power) (theorem, line 482)
- [`Mathformer.AutoformalizedCBTChapter2.chapter2_initial_mem_class`](#mathformer-autoformalizedcbtchapter2-chapter2-initial-mem-class) (theorem, line 493)
- [`Mathformer.AutoformalizedCBTChapter2.chapter2_scale_initial_segment_samePower_cumulative`](#mathformer-autoformalizedcbtchapter2-chapter2-scale-initial-segment-samepower-cumulative) (theorem, line 504)

<a id="mathformer-autoformalizedcbtchapter2-samepower"></a>

## `Mathformer.AutoformalizedCBTChapter2.SamePower`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter2.lean:48](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter2.lean#L48)

**Generated Notes**

Two sets have the same power when their subtypes are equivalent. This is the mathlib-compatible form of Cantor's equipollence relation for the chapter.

**Generated LaTeX**

```latex
`A \sim B := \exists e : A \simeq B`.
```

$$
A \sim B := \exists e : A \simeq B
$$

**Lean**

```lean
def SamePower {α : Type u} {β : Type v} (A : Set α) (B : Set β) : Prop :=
  Nonempty (A ≃ B)

namespace SamePower
```

<a id="mathformer-autoformalizedcbtchapter2-samepower-refl"></a>

## `Mathformer.AutoformalizedCBTChapter2.SamePower.refl`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter2.lean:58](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter2.lean#L58)

**Generated Notes**

Equipollence is reflexive for every set because Lean has the identity equivalence on the corresponding subtype.

**Generated LaTeX**

```latex
`A \sim A`.
```

$$
A \sim A
$$

**Lean**

```lean
theorem refl {α : Type u} (A : Set α) : SamePower A A := by
  exact ⟨Equiv.refl A⟩
```

<a id="mathformer-autoformalizedcbtchapter2-samepower-symm"></a>

## `Mathformer.AutoformalizedCBTChapter2.SamePower.symm`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter2.lean:66](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter2.lean#L66)

**Generated Notes**

Equipollence is symmetric by reversing the witnessing equivalence.

**Generated LaTeX**

```latex
`A \sim B \Rightarrow B \sim A`.
```

$$
A \sim B \Rightarrow B \sim A
$$

**Lean**

```lean
theorem symm {α : Type u} {β : Type v} {A : Set α} {B : Set β}
    (h : SamePower A B) : SamePower B A := by
  rcases h with ⟨e⟩
  exact ⟨e.symm⟩
```

<a id="mathformer-autoformalizedcbtchapter2-samepower-trans"></a>

## `Mathformer.AutoformalizedCBTChapter2.SamePower.trans`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter2.lean:76](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter2.lean#L76)

**Generated Notes**

Equipollence is transitive by composing subtype equivalences.

**Generated LaTeX**

```latex
`A \sim B \wedge B \sim C \Rightarrow A \sim C`.
```

$$
A \sim B \wedge B \sim C \Rightarrow A \sim C
$$

**Lean**

```lean
theorem trans {α : Type u} {β : Type v} {γ : Type w}
    {A : Set α} {B : Set β} {C : Set γ}
    (hAB : SamePower A B) (hBC : SamePower B C) : SamePower A C := by
  rcases hAB with ⟨eAB⟩
  rcases hBC with ⟨eBC⟩
  exact ⟨eAB.trans eBC⟩
```

<a id="mathformer-autoformalizedcbtchapter2-samepower-of-equiv"></a>

## `Mathformer.AutoformalizedCBTChapter2.SamePower.of_equiv`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter2.lean:87](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter2.lean#L87)

**Generated Notes**

Any explicit subtype equivalence is a same-power witness.

**Generated LaTeX**

```latex
`(A \simeq B) \Rightarrow A \sim B`.
```

$$
(A \simeq B) \Rightarrow A \sim B
$$

**Lean**

```lean
theorem of_equiv {α : Type u} {β : Type v} {A : Set α} {B : Set β}
    (e : A ≃ B) : SamePower A B := by
  exact ⟨e⟩
```

<a id="mathformer-autoformalizedcbtchapter2-samepower-comm-iff"></a>

## `Mathformer.AutoformalizedCBTChapter2.SamePower.comm_iff`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter2.lean:96](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter2.lean#L96)

**Generated Notes**

Equipollence can be used in either direction, matching Cantor's reciprocal-correlation language.

**Generated LaTeX**

```latex
`A \sim B \leftrightarrow B \sim A`.
```

$$
A \sim B \leftrightarrow B \sim A
$$

**Lean**

```lean
theorem comm_iff {α : Type u} {β : Type v} {A : Set α} {B : Set β} :
    SamePower A B ↔ SamePower B A := by
  constructor
  · intro h
    exact symm h
  · intro h
    exact symm h
```

<a id="mathformer-autoformalizedcbtchapter2-samepower-trans-of-and"></a>

## `Mathformer.AutoformalizedCBTChapter2.SamePower.trans_of_and`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter2.lean:109](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter2.lean#L109)

**Generated Notes**

A chain of two same-power witnesses may be composed without naming the intermediate equivalence.

**Generated LaTeX**

```latex
`(A \sim B \wedge B \sim C) \Rightarrow A\sim C`.
```

$$
(A \sim B \wedge B \sim C) \Rightarrow A\sim C
$$

**Lean**

```lean
theorem trans_of_and {α : Type u} {β : Type v} {γ : Type w}
    {A : Set α} {B : Set β} {C : Set γ}
    (h : SamePower A B ∧ SamePower B C) : SamePower A C := by
  rcases h with ⟨hAB, hBC⟩
  exact trans hAB hBC

end SamePower
```

<a id="mathformer-autoformalizedcbtchapter2-cantorpairmatrix"></a>

## `Mathformer.AutoformalizedCBTChapter2.CantorPairMatrix`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter2.lean:124](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter2.lean#L124)

**Original Source**

The Union Theorem works with the set of ordered pairs of numbers from `U_g`.

**Original LaTeX**

```latex
`U_g \times U_g`.
```

$$
U_g \times U_g
$$

**Generated Notes**

This definition keeps the chapter's ordered-pair matrix visible while using mathlib's set product.

**Lean**

```lean
def CantorPairMatrix {α : Type u} {β : Type v}
    (A : Set α) (B : Set β) : Set (α × β) :=
  A ×ˢ B
```

<a id="mathformer-autoformalizedcbtchapter2-cantorpairmatrix-swap-samepower"></a>

## `Mathformer.AutoformalizedCBTChapter2.cantorPairMatrix_swap_samePower`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter2.lean:134](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter2.lean#L134)

**Generated Notes**

The ordered-pair matrix is invariant up to equipollence under swapping coordinates. This is a concrete mathlib equivalence, independent of the historical induction assumptions.

**Generated LaTeX**

```latex
`A \times B \sim B \times A`.
```

$$
A \times B \sim B \times A
$$

**Lean**

```lean
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
```

<a id="mathformer-autoformalizedcbtchapter2-mem-cantorpairmatrix-swap-iff"></a>

## `Mathformer.AutoformalizedCBTChapter2.mem_cantorPairMatrix_swap_iff`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter2.lean:156](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter2.lean#L156)

**Generated Notes**

Membership in the source's ordered-pair matrix is preserved exactly by swapping the two coordinates and the two component sets.

**Generated LaTeX**

```latex
`(a,b)\in A\times B \leftrightarrow
(b,a)\in B\times A`.
```

$$
(a,b)\in A\times B \leftrightarrow (b,a)\in B\times A
$$

**Lean**

```lean
theorem mem_cantorPairMatrix_swap_iff {α : Type u} {β : Type v}
    {A : Set α} {B : Set β} {p : α × β} :
    p ∈ CantorPairMatrix A B ↔ (p.2, p.1) ∈ CantorPairMatrix B A := by
  constructor
  · intro hp
    exact ⟨hp.2, hp.1⟩
  · intro hp
    exact ⟨hp.2, hp.1⟩
```

<a id="mathformer-autoformalizedcbtchapter2-cantorpairmatrix-swap-equiv-nonempty"></a>

## `Mathformer.AutoformalizedCBTChapter2.cantorPairMatrix_swap_equiv_nonempty`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter2.lean:170](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter2.lean#L170)

**Generated Notes**

The matrix swap gives a visible bidirectional subtype equivalence, not merely a named same-power proposition.

**Generated LaTeX**

```latex
`A \times B \simeq B \times A`.
```

$$
A \times B \simeq B \times A
$$

**Lean**

```lean
theorem cantorPairMatrix_swap_equiv_nonempty {α : Type u} {β : Type v}
    (A : Set α) (B : Set β) :
    Nonempty (CantorPairMatrix A B ≃ CantorPairMatrix B A) := by
  rcases cantorPairMatrix_swap_samePower A B with ⟨e⟩
  exact ⟨e⟩
```

<a id="mathformer-autoformalizedcbtchapter2-cantorscale"></a>

## `Mathformer.AutoformalizedCBTChapter2.CantorScale`

- Kind: `structure`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter2.lean:185](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter2.lean#L185)

**Original Source**

The scale of number-classes consists of classes `(g)`, initial numbers `o_g`, cumulative unions `U_g`, segment-sets of numbers, a sum operation, and a sequent operation.

**Original LaTeX**

```latex
`(g)`, `o_g`, `U_g`, segment sets, `a+b`, and a
sequent of a succession.
```

$$
(g)
$$

$$
o_g
$$

$$
U_g
$$

**Generated Notes**

The structure records only the data needed by the chapter's induction pack, not an independent reconstruction of all Cantorian ordinals.

**Lean**

```lean
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
```

<a id="mathformer-autoformalizedcbtchapter2-haspowerof"></a>

## `Mathformer.AutoformalizedCBTChapter2.HasPowerOf`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter2.lean:205](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter2.lean#L205)

**Original Source**

A set has the power of `U_k` when it is equipollent with the cumulative union of all earlier number-classes up to `k`.

**Original LaTeX**

```latex
`A \sim U_k`.
```

$$
A \sim U_k
$$

**Lean**

```lean
def HasPowerOf {Index : Type u} {Number : Type v} [Preorder Index]
    [Preorder Number] (S : CantorScale Index Number) (A : Set Number)
    (k : Index) : Prop :=
  SamePower A (S.cumulative k)
```

<a id="mathformer-autoformalizedcbtchapter2-fundamentalalternative"></a>

## `Mathformer.AutoformalizedCBTChapter2.FundamentalAlternative`

- Kind: `structure`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter2.lean:216](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter2.lean#L216)

**Original Source**

The Fundamental Theorem says a subset of `U_g` is either finite or has the power of some `U_k` with `k \le g`.

**Original LaTeX**

```latex
`A \subseteq U_g \Rightarrow
A\text{ finite } \vee \exists k \le g,\ A \sim U_k`.
```

$$
A \subseteq U_g \Rightarrow A\text{ finite } \vee \exists k \le g,\ A \sim U_k
$$

**Lean**

```lean
structure FundamentalAlternative {Index : Type u} {Number : Type v}
    [Preorder Index] [Preorder Number]
    (S : CantorScale Index Number) (g : Index) (A : Set Number) : Prop where
  finite_or_has_cumulative_power :
    A.Finite ∨ ∃ k : Index, k ≤ g ∧ HasPowerOf S A k
```

<a id="mathformer-autoformalizedcbtchapter2-limitationconclusion"></a>

## `Mathformer.AutoformalizedCBTChapter2.LimitationConclusion`

- Kind: `structure`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter2.lean:227](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter2.lean#L227)

**Original Source**

The Limitation Theorem identifies the power of the previous number-class with `U_g` and with the segment determined by `o_g`.

**Original LaTeX**

```latex
`(g-1) \sim U_g \sim o_g`.
```

$$
(g-1) \sim U_g \sim o_g
$$

**Lean**

```lean
structure LimitationConclusion {Index : Type u} {Number : Type v}
    [Preorder Index] [Preorder Number]
    (S : CantorScale Index Number) (pred g : Index) : Prop where
  class_samePower_cumulative : SamePower (S.numberClass pred) (S.cumulative g)
  initial_segment_samePower_cumulative :
    SamePower (S.segment (S.initial g)) (S.cumulative g)
```

<a id="mathformer-autoformalizedcbtchapter2-sumlemmaconclusion"></a>

## `Mathformer.AutoformalizedCBTChapter2.SumLemmaConclusion`

- Kind: `structure`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter2.lean:240](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter2.lean#L240)

**Original Source**

The Sum Lemma says that if `a,b` are in `U_g`, then `a+b` is in `U_g` and has the power of the greater summand.

**Original LaTeX**

```latex
`a,b\in U_g \Rightarrow a+b\in U_g`, with the power
of `a+b` equal to the power of one of the summands.
```

$$
a,b\in U_g \Rightarrow a+b\in U_g
$$

$$
a+b
$$

**Lean**

```lean
structure SumLemmaConclusion {Index : Type u} {Number : Type v}
    [Preorder Index] [Preorder Number]
    (S : CantorScale Index Number) (g : Index) (a b : Number) : Prop where
  sum_mem_cumulative : S.sum a b ∈ S.cumulative g
  sum_power_left_or_right :
    SamePower (S.segment (S.sum a b)) (S.segment a) ∨
      SamePower (S.segment (S.sum a b)) (S.segment b)
```

<a id="mathformer-autoformalizedcbtchapter2-sequentlemmaconclusion"></a>

## `Mathformer.AutoformalizedCBTChapter2.SequentLemmaConclusion`

- Kind: `structure`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter2.lean:257](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter2.lean#L257)

**Original Source**

The Sequent Lemma says that a sequence of members of `(g)`, indexed below `o_g`, has a sequent still in `(g)`.

**Original LaTeX**

```latex
`(a_i)_{i<k\le o_g}\subseteq (g)` has a sequent in
`(g)`.
```

$$
(a_i)_{i<k\le o_g}\subseteq (g)
$$

$$
(g)
$$

**Generated Notes**

The index-bound side condition is represented by the caller; this record captures the chapter's generated sequent and membership conclusion.

**Lean**

```lean
structure SequentLemmaConclusion {Index : Type u} {Number : Type v}
    [Preorder Index] [Preorder Number]
    (S : CantorScale Index Number) (g : Index)
    (seq : Index → Number) : Prop where
  sequent_mem_class : S.sequent (Set.range seq) ∈ S.numberClass g
  sequence_mem_class : ∀ i : Index, seq i ∈ S.numberClass g
```

<a id="mathformer-autoformalizedcbtchapter2-helicalinductionstep"></a>

## `Mathformer.AutoformalizedCBTChapter2.HelicalInductionStep`

- Kind: `structure`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter2.lean:273](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter2.lean#L273)

**Original Source**

Chapter 2's induction step proves the main statements in tandem because the proofs of Theorem 1, the Fundamental Theorem, Limitation, Different Alephs, CBT, Union, Sum, and Sequent Lemma depend on each other.

**Original LaTeX**

```latex
the induction hypothesis covers every `g_0` with
`3 \le g_0 < g`, and the step establishes the whole theorem pack for `g`.
```

$$
g_0
$$

$$
3 \le g_0 < g
$$

$$
g
$$

**Generated Notes**

This record is the formal interface for one completed helical induction stage.

**Lean**

```lean
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
```

<a id="mathformer-autoformalizedcbtchapter2-chapter2-theorem1"></a>

## `Mathformer.AutoformalizedCBTChapter2.chapter2_theorem1`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter2.lean:308](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter2.lean#L308)

**Original Source**

Theorem 1: for successor `g`, the power of `(g-1)` is different from the power of every `U_k` with `k < g`.

**Original LaTeX**

```latex
`(g-1) \not\sim U_k` for `k < g`.
```

$$
(g-1) \not\sim U_k
$$

$$
k < g
$$

**Lean**

```lean
theorem chapter2_theorem1 {Index : Type u} {Number : Type v}
    [Preorder Index] [Preorder Number]
    {S : CantorScale Index Number} {g pred k : Index}
    (H : HelicalInductionStep S g pred) (hk : H.lower k) :
    ¬ SamePower (S.numberClass pred) (S.cumulative k) := by
  exact H.theorem1 k hk
```

<a id="mathformer-autoformalizedcbtchapter2-chapter2-fundamental-theorem"></a>

## `Mathformer.AutoformalizedCBTChapter2.chapter2_fundamental_theorem`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter2.lean:321](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter2.lean#L321)

**Original Source**

The Fundamental Theorem: every subset of `U_g` is finite or has the power of some `U_k` with `k \le g`.

**Original LaTeX**

```latex
`A \subseteq U_g \Rightarrow
A\text{ finite} \vee \exists k\le g,\ A\sim U_k`.
```

$$
A \subseteq U_g \Rightarrow A\text{ finite} \vee \exists k\le g,\ A\sim U_k
$$

**Lean**

```lean
theorem chapter2_fundamental_theorem {Index : Type u} {Number : Type v}
    [Preorder Index] [Preorder Number]
    {S : CantorScale Index Number} {g pred : Index} {A : Set Number}
    (H : HelicalInductionStep S g pred) (hA : A ⊆ S.cumulative g) :
    A.Finite ∨ ∃ k : Index, k ≤ g ∧ HasPowerOf S A k := by
  exact (H.fundamental hA).finite_or_has_cumulative_power
```

<a id="mathformer-autoformalizedcbtchapter2-chapter2-limitation-theorem"></a>

## `Mathformer.AutoformalizedCBTChapter2.chapter2_limitation_theorem`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter2.lean:333](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter2.lean#L333)

**Original Source**

The Limitation Theorem identifies `(g-1)` with `U_g` in power.

**Original LaTeX**

```latex
`(g-1) \sim U_g`.
```

$$
(g-1) \sim U_g
$$

**Lean**

```lean
theorem chapter2_limitation_theorem {Index : Type u} {Number : Type v}
    [Preorder Index] [Preorder Number]
    {S : CantorScale Index Number} {g pred : Index}
    (H : HelicalInductionStep S g pred) :
    SamePower (S.numberClass pred) (S.cumulative g) := by
  exact H.limitation.class_samePower_cumulative
```

<a id="mathformer-autoformalizedcbtchapter2-chapter2-initial-segment-has-stage-power"></a>

## `Mathformer.AutoformalizedCBTChapter2.chapter2_initial_segment_has_stage_power`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter2.lean:344](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter2.lean#L344)

**Original Source**

The initial number `o_g` has the same power as `U_g`.

**Original LaTeX**

```latex
`o_g \sim U_g`.
```

$$
o_g \sim U_g
$$

**Lean**

```lean
theorem chapter2_initial_segment_has_stage_power {Index : Type u}
    {Number : Type v} [Preorder Index] [Preorder Number]
    {S : CantorScale Index Number} {g pred : Index}
    (H : HelicalInductionStep S g pred) :
    SamePower (S.segment (S.initial g)) (S.cumulative g) := by
  exact H.limitation.initial_segment_samePower_cumulative
```

<a id="mathformer-autoformalizedcbtchapter2-chapter2-initial-fulfills-limitation"></a>

## `Mathformer.AutoformalizedCBTChapter2.chapter2_initial_fulfills_limitation`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter2.lean:356](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter2.lean#L356)

**Original Source**

The Limitation Theorem makes `o_g` fulfill the Limitation Principle by matching the power of the previous number-class.

**Original LaTeX**

```latex
`o_g \sim (g-1)`.
```

$$
o_g \sim (g-1)
$$

**Lean**

```lean
theorem chapter2_initial_fulfills_limitation {Index : Type u} {Number : Type v}
    [Preorder Index] [Preorder Number]
    {S : CantorScale Index Number} {g pred : Index}
    (H : HelicalInductionStep S g pred) :
    SamePower (S.segment (S.initial g)) (S.numberClass pred) := by
  exact SamePower.trans
    H.limitation.initial_segment_samePower_cumulative
    (SamePower.symm H.limitation.class_samePower_cumulative)
```

<a id="mathformer-autoformalizedcbtchapter2-chapter2-different-alephs-theorem"></a>

## `Mathformer.AutoformalizedCBTChapter2.chapter2_different_alephs_theorem`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter2.lean:370](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter2.lean#L370)

**Original Source**

The Different Alephs Theorem: the power of `U_g` is different from that of every earlier `U_k`.

**Original LaTeX**

```latex
`U_g \not\sim U_k` for `k < g`.
```

$$
U_g \not\sim U_k
$$

$$
k < g
$$

**Lean**

```lean
theorem chapter2_different_alephs_theorem {Index : Type u} {Number : Type v}
    [Preorder Index] [Preorder Number]
    {S : CantorScale Index Number} {g pred k : Index}
    (H : HelicalInductionStep S g pred) (hk : H.lower k) :
    ¬ SamePower (S.cumulative g) (S.cumulative k) := by
  exact H.different_alephs k hk
```

<a id="mathformer-autoformalizedcbtchapter2-chapter2-next-aleph-theorem"></a>

## `Mathformer.AutoformalizedCBTChapter2.chapter2_next_aleph_theorem`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter2.lean:382](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter2.lean#L382)

**Original Source**

The Next-Aleph Theorem says the next stage is not represented by any earlier cumulative power.

**Original LaTeX**

```latex
`\aleph_{g+1}` is the next aleph after `\aleph_g`.
```

$$
\aleph_{g+1}
$$

$$
\aleph_g
$$

**Lean**

```lean
theorem chapter2_next_aleph_theorem {Index : Type u} {Number : Type v}
    [Preorder Index] [Preorder Number]
    {S : CantorScale Index Number} {g pred k : Index}
    (H : HelicalInductionStep S g pred) (hk : H.lower k) :
    ¬ ∃ A : Set Number, SamePower A (S.cumulative g) ∧ SamePower A (S.cumulative k) := by
  exact H.next_aleph k hk
```

<a id="mathformer-autoformalizedcbtchapter2-chapter2-cantor-bernstein-theorem"></a>

## `Mathformer.AutoformalizedCBTChapter2.chapter2_cantor_bernstein_theorem`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter2.lean:395](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter2.lean#L395)

**Original Source**

The generalized Cantor-Bernstein theorem: if `M'' \subseteq M' \subseteq M`, `M` has the power of `U_g`, and `M \sim M''`, then `M' \sim M`.

**Original LaTeX**

```latex
`M'' \le M' \le M \sim M'' \Rightarrow M' \sim M`.
```

$$
M'' \le M' \le M \sim M'' \Rightarrow M' \sim M
$$

**Lean**

```lean
theorem chapter2_cantor_bernstein_theorem {Index : Type u} {Number : Type v}
    [Preorder Index] [Preorder Number]
    {S : CantorScale Index Number} {g pred : Index} {M M' M'' : Set Number}
    (H : HelicalInductionStep S g pred) (hM : HasPowerOf S M g)
    (hM''M' : M'' ⊆ M') (hM'M : M' ⊆ M) (hMM'' : SamePower M M'') :
    SamePower M' M := by
  exact H.cantor_bernstein hM hM''M' hM'M hMM''
```

<a id="mathformer-autoformalizedcbtchapter2-chapter2-union-theorem"></a>

## `Mathformer.AutoformalizedCBTChapter2.chapter2_union_theorem`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter2.lean:408](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter2.lean#L408)

**Original Source**

The Union Theorem: the ordered-pair matrix of `U_g` is equivalent to `U_g`.

**Original LaTeX**

```latex
`U_g \times U_g \sim U_g`.
```

$$
U_g \times U_g \sim U_g
$$

**Lean**

```lean
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
```

<a id="mathformer-autoformalizedcbtchapter2-chapter2-sum-lemma-mem"></a>

## `Mathformer.AutoformalizedCBTChapter2.chapter2_sum_lemma_mem`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter2.lean:428](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter2.lean#L428)

**Original Source**

The Sum Lemma membership conclusion: if `a,b` are in `U_g`, then `a+b` is in `U_g`.

**Original LaTeX**

```latex
`a,b\in U_g \Rightarrow a+b\in U_g`.
```

$$
a,b\in U_g \Rightarrow a+b\in U_g
$$

**Lean**

```lean
theorem chapter2_sum_lemma_mem {Index : Type u} {Number : Type v}
    [Preorder Index] [Preorder Number]
    {S : CantorScale Index Number} {g pred : Index} {a b : Number}
    (H : HelicalInductionStep S g pred)
    (ha : a ∈ S.cumulative g) (hb : b ∈ S.cumulative g) :
    S.sum a b ∈ S.cumulative g := by
  exact (H.sum_lemma ha hb).sum_mem_cumulative
```

<a id="mathformer-autoformalizedcbtchapter2-chapter2-sum-lemma-power"></a>

## `Mathformer.AutoformalizedCBTChapter2.chapter2_sum_lemma_power`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter2.lean:441](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter2.lean#L441)

**Original Source**

The Sum Lemma power conclusion: the segment of `a+b` has the power of one of the summand segments.

**Original LaTeX**

```latex
`|a+b|=|a|` or `|a+b|=|b|`.
```

$$
|a+b|=|a|
$$

$$
|a+b|=|b|
$$

**Lean**

```lean
theorem chapter2_sum_lemma_power {Index : Type u} {Number : Type v}
    [Preorder Index] [Preorder Number]
    {S : CantorScale Index Number} {g pred : Index} {a b : Number}
    (H : HelicalInductionStep S g pred)
    (ha : a ∈ S.cumulative g) (hb : b ∈ S.cumulative g) :
    SamePower (S.segment (S.sum a b)) (S.segment a) ∨
      SamePower (S.segment (S.sum a b)) (S.segment b) := by
  exact (H.sum_lemma ha hb).sum_power_left_or_right
```

<a id="mathformer-autoformalizedcbtchapter2-chapter2-sequent-lemma"></a>

## `Mathformer.AutoformalizedCBTChapter2.chapter2_sequent_lemma`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter2.lean:456](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter2.lean#L456)

**Original Source**

The Sequent Lemma: a sequence in `(g)` has a generated sequent in `(g)`.

**Original LaTeX**

```latex
`(a_i)\subseteq (g) \Rightarrow
\operatorname{seq}(a_i)\in(g)`.
```

$$
(a_i)\subseteq (g) \Rightarrow \operatorname{seq}(a_i)\in(g)
$$

**Lean**

```lean
theorem chapter2_sequent_lemma {Index : Type u} {Number : Type v}
    [Preorder Index] [Preorder Number]
    {S : CantorScale Index Number} {g pred : Index}
    (H : HelicalInductionStep S g pred) (seq : Index → Number)
    (hseq : ∀ i : Index, seq i ∈ S.numberClass g) :
    SequentLemmaConclusion S g seq := by
  exact H.sequent_lemma seq hseq
```

<a id="mathformer-autoformalizedcbtchapter2-chapter2-sequent-mem-class"></a>

## `Mathformer.AutoformalizedCBTChapter2.chapter2_sequent_mem_class`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter2.lean:469](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter2.lean#L469)

**Original Source**

The Sequent Lemma's membership part gives the exact membership-in-the-number-class conclusion for the generated sequent.

**Original LaTeX**

```latex
`\operatorname{seq}(a_i)\in(g)`.
```

$$
\operatorname{seq}(a_i)\in(g)
$$

**Lean**

```lean
theorem chapter2_sequent_mem_class {Index : Type u} {Number : Type v}
    [Preorder Index] [Preorder Number]
    {S : CantorScale Index Number} {g pred : Index}
    (H : HelicalInductionStep S g pred) (seq : Index → Number)
    (hseq : ∀ i : Index, seq i ∈ S.numberClass g) :
    S.sequent (Set.range seq) ∈ S.numberClass g := by
  exact (H.sequent_lemma seq hseq).sequent_mem_class
```

<a id="mathformer-autoformalizedcbtchapter2-chapter2-class-member-has-initial-power"></a>

## `Mathformer.AutoformalizedCBTChapter2.chapter2_class_member_has_initial_power`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter2.lean:482](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter2.lean#L482)

**Original Source**

Every member of a number-class has the power of the initial number of that class.

**Original LaTeX**

```latex
`a\in(g) \Rightarrow a\sim o_g`.
```

$$
a\in(g) \Rightarrow a\sim o_g
$$

**Lean**

```lean
theorem chapter2_class_member_has_initial_power {Index : Type u}
    {Number : Type v} [Preorder Index] [Preorder Number]
    (S : CantorScale Index Number) {g : Index} {a : Number}
    (ha : a ∈ S.numberClass g) :
    SamePower (S.segment a) (S.segment (S.initial g)) := by
  exact S.class_members_have_initial_power ha
```

<a id="mathformer-autoformalizedcbtchapter2-chapter2-initial-mem-class"></a>

## `Mathformer.AutoformalizedCBTChapter2.chapter2_initial_mem_class`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter2.lean:493](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter2.lean#L493)

**Original Source**

The initial number `o_g` is in the number-class `(g)`.

**Original LaTeX**

```latex
`o_g \in (g)`.
```

$$
o_g \in (g)
$$

**Lean**

```lean
theorem chapter2_initial_mem_class {Index : Type u} {Number : Type v}
    [Preorder Index] [Preorder Number]
    (S : CantorScale Index Number) (g : Index) :
    S.initial g ∈ S.numberClass g := by
  exact S.initial_mem_class g
```

<a id="mathformer-autoformalizedcbtchapter2-chapter2-scale-initial-segment-samepower-cumulative"></a>

## `Mathformer.AutoformalizedCBTChapter2.chapter2_scale_initial_segment_samePower_cumulative`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter2.lean:504](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter2.lean#L504)

**Original Source**

The scale definition makes the segment of `o_g` equipollent with `U_g`.

**Original LaTeX**

```latex
`o_g \sim U_g`.
```

$$
o_g \sim U_g
$$

**Lean**

```lean
theorem chapter2_scale_initial_segment_samePower_cumulative {Index : Type u}
    {Number : Type v} [Preorder Index] [Preorder Number]
    (S : CantorScale Index Number) (g : Index) :
    SamePower (S.segment (S.initial g)) (S.cumulative g) := by
  exact S.initial_segment_samePower_cumulative g

end AutoformalizedCBTChapter2
end Mathformer
```
