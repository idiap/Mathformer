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

# `Mathformer.AutoformalizedCBTChapter1`

[Back to index](../../INDEX.md)

## Metadata

- Source: [backends/lean/Mathformer/AutoformalizedCBTChapter1.lean](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter1.lean)
- Status: `candidate`
- SHA-256: `67d47bfe0b493268d8dbaa8b434df039fe7845bcebd2d6be8705e6b257f1629a`
- Declarations: `23`

## Imports

```lean
import Mathlib.Data.Set.Countable
import Mathlib.Logic.Function.Basic
import Mathlib.SetTheory.Cardinal.SchroederBernstein
```

## Module Source Notes

**Original Source**

Chapter 1 of the CBT textbook archive, "Cantor's CBT Proof for Sets of the Power of (II)", presents Cantor's generation principles, the denumerable union theorem, the denumerable Cantor-Bernstein theorem, Cantor's diagonal/sequent argument separating the first and second number classes, Lemma 2 on least elements of subsets, the Fundamental Theorem for subsets of the second number-class, Cantor-Bernstein for `(II)`, the Limitation Principle, and the Union Theorem for the next number-class.

**Original LaTeX**

```latex
key chapter statements include: "The union of a
denumerable set of denumerable sets is denumerable"; "An infinite subset of a
denumerable set is denumerable"; "The power of `(II)` is different from the
power of `(I)`"; "In every subset of `(II)` there is a smallest number"; and a
Cantor-Bernstein statement from mutual embeddings/equipollence.
```

$$
(II)
$$

$$
(I)
$$

$$
(II)
$$

**Generated Notes**

This file formalizes the chapter's reusable mathematical core in modern mathlib terms. The historical generation and limitation principles are recorded as explicit structures because the source describes Cantor's ordinal-generation framework, not a ready-made Lean construction of the second number-class. The countability, diagonal, least-element, and Schroeder-Bernstein components are proved with complete Lean proof terms and without target axioms.

## Declarations

- [`Mathformer.AutoformalizedCBTChapter1.FirstGenerationPrinciple`](#mathformer-autoformalizedcbtchapter1-firstgenerationprinciple) (structure, line 53)
- [`Mathformer.AutoformalizedCBTChapter1.SecondGenerationPrinciple`](#mathformer-autoformalizedcbtchapter1-secondgenerationprinciple) (structure, line 67)
- [`Mathformer.AutoformalizedCBTChapter1.LimitationPrinciple`](#mathformer-autoformalizedcbtchapter1-limitationprinciple) (structure, line 83)
- [`Mathformer.AutoformalizedCBTChapter1.Denumerable`](#mathformer-autoformalizedcbtchapter1-denumerable) (def, line 96)
- [`Mathformer.AutoformalizedCBTChapter1.Denumerable.exists_nat_surjection`](#mathformer-autoformalizedcbtchapter1-denumerable-exists-nat-surjection) (theorem, line 107)
- [`Mathformer.AutoformalizedCBTChapter1.CantorIndexedUnion`](#mathformer-autoformalizedcbtchapter1-cantorindexedunion) (def, line 119)
- [`Mathformer.AutoformalizedCBTChapter1.CantorPairMatrix`](#mathformer-autoformalizedcbtchapter1-cantorpairmatrix) (def, line 130)
- [`Mathformer.AutoformalizedCBTChapter1.denumerable_union_theorem`](#mathformer-autoformalizedcbtchapter1-denumerable-union-theorem) (theorem, line 142)
- [`Mathformer.AutoformalizedCBTChapter1.countable_union_of_countable_family`](#mathformer-autoformalizedcbtchapter1-countable-union-of-countable-family) (theorem, line 161)
- [`Mathformer.AutoformalizedCBTChapter1.denumerable_cbt`](#mathformer-autoformalizedcbtchapter1-denumerable-cbt) (theorem, line 176)
- [`Mathformer.AutoformalizedCBTChapter1.intermediate_subset_of_denumerable_countable`](#mathformer-autoformalizedcbtchapter1-intermediate-subset-of-denumerable-countable) (theorem, line 189)
- [`Mathformer.AutoformalizedCBTChapter1.theorem1_nat_cannot_enumerate_powerset`](#mathformer-autoformalizedcbtchapter1-theorem1-nat-cannot-enumerate-powerset) (theorem, line 203)
- [`Mathformer.AutoformalizedCBTChapter1.no_equiv_nat_powerset`](#mathformer-autoformalizedcbtchapter1-no-equiv-nat-powerset) (theorem, line 215)
- [`Mathformer.AutoformalizedCBTChapter1.lemma2_nat_least_element`](#mathformer-autoformalizedcbtchapter1-lemma2-nat-least-element) (theorem, line 226)
- [`Mathformer.AutoformalizedCBTChapter1.finite_descending_chain_bound_nat`](#mathformer-autoformalizedcbtchapter1-finite-descending-chain-bound-nat) (theorem, line 243)
- [`Mathformer.AutoformalizedCBTChapter1.no_infinite_descending_sequence_nat`](#mathformer-autoformalizedcbtchapter1-no-infinite-descending-sequence-nat) (theorem, line 261)
- [`Mathformer.AutoformalizedCBTChapter1.fundamental_countability_component`](#mathformer-autoformalizedcbtchapter1-fundamental-countability-component) (theorem, line 277)
- [`Mathformer.AutoformalizedCBTChapter1.fundamental_finite_branch_countable`](#mathformer-autoformalizedcbtchapter1-fundamental-finite-branch-countable) (theorem, line 287)
- [`Mathformer.AutoformalizedCBTChapter1.cantor_bernstein_for_II_modern`](#mathformer-autoformalizedcbtchapter1-cantor-bernstein-for-ii-modern) (theorem, line 300)
- [`Mathformer.AutoformalizedCBTChapter1.cantor_bernstein_between_subsets`](#mathformer-autoformalizedcbtchapter1-cantor-bernstein-between-subsets) (theorem, line 312)
- [`Mathformer.AutoformalizedCBTChapter1.union_theorem_countable_version`](#mathformer-autoformalizedcbtchapter1-union-theorem-countable-version) (theorem, line 334)
- [`Mathformer.AutoformalizedCBTChapter1.countable_product_component`](#mathformer-autoformalizedcbtchapter1-countable-product-component) (theorem, line 344)
- [`Mathformer.AutoformalizedCBTChapter1.nat_pair_set_countable`](#mathformer-autoformalizedcbtchapter1-nat-pair-set-countable) (theorem, line 355)

<a id="mathformer-autoformalizedcbtchapter1-firstgenerationprinciple"></a>

## `Mathformer.AutoformalizedCBTChapter1.FirstGenerationPrinciple`

- Kind: `structure`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter1.lean:53](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter1.lean#L53)

**Original Source**

The first generation principle says that, given a number, a new number is generated: its successor or sequent.

**Original LaTeX**

```latex
`a \mapsto a+1`.
```

$$
a \mapsto a+1
$$

**Generated Notes**

The chapter treats this as a historical principle for Cantor's scale of numbers. We record the data needed for such a successor operation and its freshness property.

**Lean**

```lean
structure FirstGenerationPrinciple (α : Type u) where
  successor : α → α
  successor_ne_self : ∀ a : α, successor a ≠ a
```

<a id="mathformer-autoformalizedcbtchapter1-secondgenerationprinciple"></a>

## `Mathformer.AutoformalizedCBTChapter1.SecondGenerationPrinciple`

- Kind: `structure`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter1.lean:67](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter1.lean#L67)

**Original Source**

The second generation principle says that every definite succession of already-defined numbers with no greatest member generates a new limit or sequent.

**Original LaTeX**

```latex
a succession with no greatest member has a limit
sequent.
```

**Generated Notes**

This structure isolates the source principle as data: for every admissible succession with no greatest member there is a generated limit element.

**Lean**

```lean
structure SecondGenerationPrinciple (α : Type u) [LT α] where
  AdmissibleSuccession : Set α → Prop
  hasNoGreatest : Set α → Prop
  limitSequent : (s : Set α) → AdmissibleSuccession s → hasNoGreatest s → α
  below_limit :
    ∀ (s : Set α) (hs : AdmissibleSuccession s) (hng : hasNoGreatest s),
      ∀ a ∈ s, a < limitSequent s hs hng
```

<a id="mathformer-autoformalizedcbtchapter1-limitationprinciple"></a>

## `Mathformer.AutoformalizedCBTChapter1.LimitationPrinciple`

- Kind: `structure`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter1.lean:83](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter1.lean#L83)

**Original Source**

The Limitation Principle admits a new integer into the scale only if its power is that of an already existing complete number-class.

**Original LaTeX**

```latex
a generated number is admitted only when its power
matches a prior number-class.
```

**Generated Notes**

This is a predicate-level record of the admission rule, separated from any particular construction of Cantor's historical classes.

**Lean**

```lean
structure LimitationPrinciple (α : Type u) where
  alreadyExistingClass : Set α → Prop
  samePowerAsExistingClass : α → Prop
  admissible : α → Prop
  admission_rule : ∀ a : α, samePowerAsExistingClass a → admissible a
```

<a id="mathformer-autoformalizedcbtchapter1-denumerable"></a>

## `Mathformer.AutoformalizedCBTChapter1.Denumerable`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter1.lean:96](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter1.lean#L96)

**Generated Notes**

A set is denumerable in the chapter's modernized sense when it is countable and nonempty. This keeps the countability content separate from the historical convention that Cantor's positive integers start at `1`.

**Generated LaTeX**

```latex
`\mathrm{Denumerable}(s) := s\text{ is countable}
\wedge s\ne\varnothing`.
```

$$
\mathrm{Denumerable}(s) := s\text{ is countable} \wedge s\ne\varnothing
$$

**Lean**

```lean
def Denumerable {α : Type u} (s : Set α) : Prop :=
  s.Countable ∧ s.Nonempty
```

<a id="mathformer-autoformalizedcbtchapter1-denumerable-exists-nat-surjection"></a>

## `Mathformer.AutoformalizedCBTChapter1.Denumerable.exists_nat_surjection`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter1.lean:107](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter1.lean#L107)

**Original Source**

The enumeration-by method enumerates a denumerable set by the first number-class.

**Original LaTeX**

```latex
if `A` is denumerable, then there is an onto map
`\mathbb N \twoheadrightarrow A`.
```

$$
A
$$

$$
\mathbb N \twoheadrightarrow A
$$

**Generated Notes**

Mathlib packages this as `Set.Countable.exists_surjective` for the subtype determined by a nonempty countable set.

**Lean**

```lean
theorem Denumerable.exists_nat_surjection {α : Type u} {A : Set α}
    (hA : Denumerable A) :
    ∃ f : ℕ → A, Surjective f := by
  exact hA.1.exists_surjective hA.2
```

<a id="mathformer-autoformalizedcbtchapter1-cantorindexedunion"></a>

## `Mathformer.AutoformalizedCBTChapter1.CantorIndexedUnion`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter1.lean:119](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter1.lean#L119)

**Original Source**

The Denumerable Union Theorem discusses the union of a set-indexed family of sets.

**Original LaTeX**

```latex
`\bigcup_{i\in I} A_i`.
```

$$
\bigcup_{i\in I} A_i
$$

**Generated Notes**

This definition gives the chapter's indexed-union object a source-specific name while using Lean's ordinary indexed union.

**Lean**

```lean
def CantorIndexedUnion {ι : Type u} {α : Type v}
    (I : Set ι) (A : ι → Set α) : Set α :=
  ⋃ i ∈ I, A i
```

<a id="mathformer-autoformalizedcbtchapter1-cantorpairmatrix"></a>

## `Mathformer.AutoformalizedCBTChapter1.CantorPairMatrix`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter1.lean:130](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter1.lean#L130)

**Original Source**

The Union Theorem proof represents the relevant union as a matrix of ordered pairs.

**Original LaTeX**

```latex
`{(a,b) \mid a\in A \wedge b\in B}`.
```

$$
{(a,b) \mid a\in A \wedge b\in B}
$$

**Generated Notes**

This definition names the source's pair matrix as the mathlib set product.

**Lean**

```lean
def CantorPairMatrix {α : Type u} {β : Type v}
    (A : Set α) (B : Set β) : Set (α × β) :=
  A ×ˢ B
```

<a id="mathformer-autoformalizedcbtchapter1-denumerable-union-theorem"></a>

## `Mathformer.AutoformalizedCBTChapter1.denumerable_union_theorem`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter1.lean:142](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter1.lean#L142)

**Original Source**

The Denumerable Union Theorem: the union of a denumerable set of denumerable sets is denumerable.

**Original LaTeX**

```latex
`\bigcup_{i\in I} A_i` is denumerable when `I` is
denumerable and each `A_i` is denumerable.
```

$$
\bigcup_{i\in I} A_i
$$

$$
I
$$

$$
A_i
$$

**Generated Notes**

Mathlib's `Set.Countable.biUnion` proves the countability part directly; nonemptiness is supplied by one inhabited component.

**Lean**

```lean
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
```

<a id="mathformer-autoformalizedcbtchapter1-countable-union-of-countable-family"></a>

## `Mathformer.AutoformalizedCBTChapter1.countable_union_of_countable_family`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter1.lean:161](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter1.lean#L161)

**Original Source**

The countability content of the Denumerable Union Theorem is the countability of the indexed union.

**Original LaTeX**

```latex
if `I` is countable and each `A_i` is countable, then
`\bigcup_{i\in I} A_i` is countable.
```

$$
I
$$

$$
A_i
$$

$$
\bigcup_{i\in I} A_i
$$

**Lean**

```lean
theorem countable_union_of_countable_family {ι : Type u} {α : Type v}
    {I : Set ι} {A : ι → Set α}
    (hI : I.Countable) (hA : ∀ i ∈ I, (A i).Countable) :
    (CantorIndexedUnion I A).Countable := by
  unfold CantorIndexedUnion
  exact hI.biUnion fun i hi => hA i hi
```

<a id="mathformer-autoformalizedcbtchapter1-denumerable-cbt"></a>

## `Mathformer.AutoformalizedCBTChapter1.denumerable_cbt`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter1.lean:176](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter1.lean#L176)

**Original Source**

The Denumerable CBT: an infinite subset of a denumerable set is denumerable.

**Original LaTeX**

```latex
if `A\subseteq B`, `B` is denumerable, and `A` is
infinite, then `A` is denumerable.
```

$$
A\subseteq B
$$

$$
B
$$

$$
A
$$

**Generated Notes**

In Lean the countability part is simply monotonicity of `Set.Countable`; infinitude supplies nonemptiness.

**Lean**

```lean
theorem denumerable_cbt {α : Type u} {A B : Set α}
    (hAB : A ⊆ B) (hB : B.Countable) (hAinf : A.Infinite) :
    Denumerable A := by
  constructor
  · exact hB.mono hAB
  · exact hAinf.nonempty
```

<a id="mathformer-autoformalizedcbtchapter1-intermediate-subset-of-denumerable-countable"></a>

## `Mathformer.AutoformalizedCBTChapter1.intermediate_subset_of_denumerable_countable`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter1.lean:189](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter1.lean#L189)

**Original Source**

The single-set formulation used in the chapter says that intermediate subsets of a denumerable set are countable.

**Original LaTeX**

```latex
if `M''\subseteq M'\subseteq M` and `M` is
denumerable, then `M'` is countable.
```

$$
M''\subseteq M'\subseteq M
$$

$$
M
$$

$$
M'
$$

**Lean**

```lean
theorem intermediate_subset_of_denumerable_countable {α : Type u}
    {Mp M : Set α} (hMpM : Mp ⊆ M) (hM : M.Countable) :
    Mp.Countable := by
  exact hM.mono hMpM
```

<a id="mathformer-autoformalizedcbtchapter1-theorem1-nat-cannot-enumerate-powerset"></a>

## `Mathformer.AutoformalizedCBTChapter1.theorem1_nat_cannot_enumerate_powerset`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter1.lean:203](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter1.lean#L203)

**Original Source**

Theorem 1 says that the power of `(II)` differs from the power of `(I)`.

**Original LaTeX**

```latex
`|(II)|\ne |(I)|`.
```

$$
|(II)|\ne |(I)|
$$

**Generated Notes**

A modern diagonal counterpart is Cantor's theorem: there is no surjection from a type to its powerset. For `α = ℕ`, this says that the power set of the first number-class cannot be enumerated by the first number-class.

**Lean**

```lean
theorem theorem1_nat_cannot_enumerate_powerset (f : ℕ → Set ℕ) :
    ¬ Surjective f := by
  exact Function.cantor_surjective f
```

<a id="mathformer-autoformalizedcbtchapter1-no-equiv-nat-powerset"></a>

## `Mathformer.AutoformalizedCBTChapter1.no_equiv_nat_powerset`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter1.lean:215](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter1.lean#L215)

**Original Source**

Cantor's sequent argument rules out an enumeration whose sequent is already among the preceding numbers.

**Original LaTeX**

```latex
no function `\mathbb N\to\mathcal P(\mathbb N)` is
onto.
```

$$
\mathbb N\to\mathcal P(\mathbb N)
$$

**Generated Notes**

This is the nonexistence of an equivalence between the natural numbers and their powerset.

**Lean**

```lean
theorem no_equiv_nat_powerset : IsEmpty (ℕ ≃ Set ℕ) := by
  refine ⟨fun e => ?_⟩
  exact Function.cantor_surjective (fun n => e n) e.surjective
```

<a id="mathformer-autoformalizedcbtchapter1-lemma2-nat-least-element"></a>

## `Mathformer.AutoformalizedCBTChapter1.lemma2_nat_least_element`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter1.lean:226](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter1.lean#L226)

**Original Source**

Lemma 2(i): in every subset of `(II)` there is a smallest number.

**Original LaTeX**

```latex
every nonempty subset has a least element.
```

**Generated Notes**

The directly mathlib-compatible analogue is the well-ordering of `ℕ`.

**Lean**

```lean
theorem lemma2_nat_least_element {s : Set ℕ} (hs : s.Nonempty) :
    ∃ n ∈ s, ∀ m ∈ s, n ≤ m := by
  classical
  let p : ℕ → Prop := fun n => n ∈ s
  have hp : ∃ n, p n := hs
  refine ⟨Nat.find hp, Nat.find_spec hp, ?_⟩
  intro m hm
  exact Nat.find_min' hp hm
```

<a id="mathformer-autoformalizedcbtchapter1-finite-descending-chain-bound-nat"></a>

## `Mathformer.AutoformalizedCBTChapter1.finite_descending_chain_bound_nat`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter1.lean:243](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter1.lean#L243)

**Original Source**

Lemma 2(ii): every descending sequence of numbers from `(II)` is finite.

**Original LaTeX**

```latex
there is no infinite strictly descending sequence.
```

**Generated Notes**

We prove the finite obstruction for `ℕ`: a strictly descending chain of length `n` forces `a n + n \le a 0`, so its length is bounded by the first value.

**Lean**

```lean
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
```

<a id="mathformer-autoformalizedcbtchapter1-no-infinite-descending-sequence-nat"></a>

## `Mathformer.AutoformalizedCBTChapter1.no_infinite_descending_sequence_nat`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter1.lean:261](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter1.lean#L261)

**Original Source**

Lemma 2(ii) rules out an infinite descending sequence.

**Original LaTeX**

```latex
no `a_0>a_1>a_2>\cdots`.
```

$$
a_0>a_1>a_2>\cdots
$$

**Lean**

```lean
theorem no_infinite_descending_sequence_nat :
    ¬ ∃ a : ℕ → ℕ, ∀ n : ℕ, a (n + 1) < a n := by
  rintro ⟨a, hdesc⟩
  have hbound := finite_descending_chain_bound_nat a hdesc (a 0 + 1)
  have hle : a 0 + 1 ≤ a (a 0 + 1) + (a 0 + 1) := Nat.le_add_left _ _
  exact Nat.not_succ_le_self (a 0) (hle.trans hbound)
```

<a id="mathformer-autoformalizedcbtchapter1-fundamental-countability-component"></a>

## `Mathformer.AutoformalizedCBTChapter1.fundamental_countability_component`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter1.lean:277](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter1.lean#L277)

**Original Source**

The Fundamental Theorem: a subset of `(II)` is finite, or has the power of `(I)`, or has the power of `(II)`.

**Original LaTeX**

```latex
every subset of `(II)` falls into the finite,
denumerable, or full-second-class case.
```

$$
(II)
$$

**Generated Notes**

The countability component of the theorem says that every subset of a countable ambient class is countable. This is the part used in the chapter's later countability reductions.

**Lean**

```lean
theorem fundamental_countability_component {α : Type u} {S II : Set α}
    (hS : S ⊆ II) (hII : II.Countable) :
    S.Countable := by
  exact hII.mono hS
```

<a id="mathformer-autoformalizedcbtchapter1-fundamental-finite-branch-countable"></a>

## `Mathformer.AutoformalizedCBTChapter1.fundamental_finite_branch_countable`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter1.lean:287](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter1.lean#L287)

**Original Source**

The Fundamental Theorem's finite branch is compatible with countability.

**Original LaTeX**

```latex
finite subsets are countable.
```

**Lean**

```lean
theorem fundamental_finite_branch_countable {α : Type u} {S : Set α}
    (hS : S.Finite) :
    S.Countable := by
  exact hS.countable
```

<a id="mathformer-autoformalizedcbtchapter1-cantor-bernstein-for-ii-modern"></a>

## `Mathformer.AutoformalizedCBTChapter1.cantor_bernstein_for_II_modern`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter1.lean:300](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter1.lean#L300)

**Original Source**

Cantor-Bernstein for `(II)`: if a set of the power of `(II)` embeds into an intermediate set and the intermediate set embeds back, the two have equal power.

**Original LaTeX**

```latex
mutual one-one maps yield equipollence.
```

**Generated Notes**

This is the modern Schroeder-Bernstein theorem from mathlib.

**Lean**

```lean
theorem cantor_bernstein_for_II_modern {α : Type u} {β : Type v}
    (f : α → β) (g : β → α)
    (hf : Injective f) (hg : Injective g) :
    Nonempty (α ≃ β) := by
  exact Function.Embedding.antisymm ⟨f, hf⟩ ⟨g, hg⟩
```

<a id="mathformer-autoformalizedcbtchapter1-cantor-bernstein-between-subsets"></a>

## `Mathformer.AutoformalizedCBTChapter1.cantor_bernstein_between_subsets`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter1.lean:312](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter1.lean#L312)

**Original Source**

The set-theoretic inclusion form of the chapter's Cantor-Bernstein argument uses the inclusion maps as injections.

**Original LaTeX**

```latex
from `M''\subseteq M'\subseteq M` together with a
reverse injection, obtain equal power.
```

$$
M''\subseteq M'\subseteq M
$$

**Lean**

```lean
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
```

<a id="mathformer-autoformalizedcbtchapter1-union-theorem-countable-version"></a>

## `Mathformer.AutoformalizedCBTChapter1.union_theorem_countable_version`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter1.lean:334](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter1.lean#L334)

**Original Source**

The Union Theorem for `V`: a union indexed by a class of power `O`, with each member of power `O`, again has power `O`.

**Original LaTeX**

```latex
a countable analogue is
`\bigcup_{i\in I} A_i` countable when `I` and all `A_i` are countable.
```

$$
\bigcup_{i\in I} A_i
$$

$$
I
$$

$$
A_i
$$

**Generated Notes**

This is the same countability theorem as the denumerable union theorem, stated as a reusable union principle.

**Lean**

```lean
theorem union_theorem_countable_version {ι : Type u} {α : Type v}
    [Countable ι] (A : ι → Set α) (hA : ∀ i, (A i).Countable) :
    (⋃ i, A i).Countable := by
  exact Set.countable_iUnion hA
```

<a id="mathformer-autoformalizedcbtchapter1-countable-product-component"></a>

## `Mathformer.AutoformalizedCBTChapter1.countable_product_component`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter1.lean:344](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter1.lean#L344)

**Original Source**

Cantor's proof of the Union Theorem orders pairs and uses the fact that a product of countable sets is countable.

**Original LaTeX**

```latex
`\aleph_0\cdot\aleph_0=\aleph_0`.
```

$$
\aleph_0\cdot\aleph_0=\aleph_0
$$

**Lean**

```lean
theorem countable_product_component {α : Type u} {β : Type v}
    {A : Set α} {B : Set β} (hA : A.Countable) (hB : B.Countable) :
    (CantorPairMatrix A B).Countable := by
  unfold CantorPairMatrix
  exact hA.prod hB
```

<a id="mathformer-autoformalizedcbtchapter1-nat-pair-set-countable"></a>

## `Mathformer.AutoformalizedCBTChapter1.nat_pair_set_countable`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter1.lean:355](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter1.lean#L355)

**Original Source**

The proof of the Denumerable Union Theorem is captured by enumerating ordered pairs of positive integers.

**Original LaTeX**

```latex
`\mathbb N\times\mathbb N` is denumerable.
```

$$
\mathbb N\times\mathbb N
$$

**Lean**

```lean
theorem nat_pair_set_countable : (Set.univ : Set (ℕ × ℕ)).Countable := by
  exact Set.countable_univ

end AutoformalizedCBTChapter1
end Mathformer
```
