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

# `Mathformer.AutoformalizedCBTChapter3`

[Back to index](../../INDEX.md)

## Metadata

- Source: [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean)
- Status: `candidate`
- SHA-256: `9e735c1eed59930ce5982af4e3b9be56097d524be80c674fb535840c3d56c8be`
- Declarations: `42`

## Imports

```lean
import Mathlib.Data.Real.Basic
import Mathlib.Data.Set.Lattice
import Mathlib.Logic.Function.Basic
import Mathlib.SetTheory.Cardinal.SchroederBernstein
```

## Module Source Notes

**Original Source**

Chapter 3 of the CBT textbook archive, "CBT in Cantor's 1878 Beitrag", argues that Cantor's use of equivalence classes, the order relation between powers, the direct two-set allusion, Lemma G for `(0,1]` and `[0,1]`, the comb/frame proof gestalt, and the discussion of different powers all presuppose or point toward Cantor-Bernstein reasoning.

**Original LaTeX**

```latex
key chapter statements include `M \sim N`, partitions
of linear sets into equal-power classes, `C \subseteq B \subseteq A`, the
comparability assertion for powers, the two-set CBT allusion, Lemma G
`(0,1] \sim [0,1]`, the pushdown/simple-chain construction, frame matchings,
and diagonal evidence for powers above the continuum.

Source anchors: src_L0001-src_L0451
```

$$
M \sim N
$$

$$
C \subseteq B \subseteq A
$$

$$
(0,1] \sim [0,1]
$$

**Generated Notes**

This module formalizes the chapter's reusable core in mathlib-compatible terms.  Equipollence, power comparison by embeddings, Schroeder-Bernstein antisymmetry, sandwich/single-set CBT, frame-indexed tagged-union equivalence, and diagonal non-surjectivity are proved.  The historical continuum comb construction and Cantor's Lemma G are represented as explicit structures, because the extracted source gives a mathematical construction narrative rather than a ready-made Lean homeomorphism or interval equivalence proof.

## Declarations

- [`Mathformer.AutoformalizedCBTChapter3.SamePower`](#mathformer-autoformalizedcbtchapter3-samepower) (def, line 56)
- [`Mathformer.AutoformalizedCBTChapter3.SamePower.refl`](#mathformer-autoformalizedcbtchapter3-samepower-refl) (theorem, line 69)
- [`Mathformer.AutoformalizedCBTChapter3.SamePower.symm`](#mathformer-autoformalizedcbtchapter3-samepower-symm) (theorem, line 80)
- [`Mathformer.AutoformalizedCBTChapter3.SamePower.trans`](#mathformer-autoformalizedcbtchapter3-samepower-trans) (theorem, line 93)
- [`Mathformer.AutoformalizedCBTChapter3.CantorWellDefinedSet`](#mathformer-autoformalizedcbtchapter3-cantorwelldefinedset) (structure, line 112)
- [`Mathformer.AutoformalizedCBTChapter3.PowerClass`](#mathformer-autoformalizedcbtchapter3-powerclass) (def, line 123)
- [`Mathformer.AutoformalizedCBTChapter3.mem_powerClass_iff`](#mathformer-autoformalizedcbtchapter3-mem-powerclass-iff) (theorem, line 132)
- [`Mathformer.AutoformalizedCBTChapter3.inclusionEmbedding`](#mathformer-autoformalizedcbtchapter3-inclusionembedding) (def, line 141)
- [`Mathformer.AutoformalizedCBTChapter3.embeddingTrans`](#mathformer-autoformalizedcbtchapter3-embeddingtrans) (def, line 159)
- [`Mathformer.AutoformalizedCBTChapter3.samePower_of_subset_sandwich`](#mathformer-autoformalizedcbtchapter3-samepower-of-subset-sandwich) (theorem, line 176)
- [`Mathformer.AutoformalizedCBTChapter3.PowerLE`](#mathformer-autoformalizedcbtchapter3-powerle) (def, line 191)
- [`Mathformer.AutoformalizedCBTChapter3.powerLE_of_samePower_subset`](#mathformer-autoformalizedcbtchapter3-powerle-of-samepower-subset) (theorem, line 202)
- [`Mathformer.AutoformalizedCBTChapter3.powerLE_refl`](#mathformer-autoformalizedcbtchapter3-powerle-refl) (theorem, line 213)
- [`Mathformer.AutoformalizedCBTChapter3.powerLE_trans`](#mathformer-autoformalizedcbtchapter3-powerle-trans) (theorem, line 225)
- [`Mathformer.AutoformalizedCBTChapter3.powerLE_antisymm_samePower`](#mathformer-autoformalizedcbtchapter3-powerle-antisymm-samepower) (theorem, line 241)
- [`Mathformer.AutoformalizedCBTChapter3.PowerLT`](#mathformer-autoformalizedcbtchapter3-powerlt) (def, line 254)
- [`Mathformer.AutoformalizedCBTChapter3.powerLT_asymm`](#mathformer-autoformalizedcbtchapter3-powerlt-asymm) (theorem, line 265)
- [`Mathformer.AutoformalizedCBTChapter3.CantorComparability`](#mathformer-autoformalizedcbtchapter3-cantorcomparability) (structure, line 277)
- [`Mathformer.AutoformalizedCBTChapter3.twoSetCBT_from_power_antisymmetry`](#mathformer-autoformalizedcbtchapter3-twosetcbt-from-power-antisymmetry) (theorem, line 289)
- [`Mathformer.AutoformalizedCBTChapter3.ProperSubset`](#mathformer-autoformalizedcbtchapter3-propersubset) (def, line 299)
- [`Mathformer.AutoformalizedCBTChapter3.CantorReflexive`](#mathformer-autoformalizedcbtchapter3-cantorreflexive) (def, line 309)
- [`Mathformer.AutoformalizedCBTChapter3.not_powerLT_of_samePower`](#mathformer-autoformalizedcbtchapter3-not-powerlt-of-samepower) (theorem, line 319)
- [`Mathformer.AutoformalizedCBTChapter3.ClosedUnit`](#mathformer-autoformalizedcbtchapter3-closedunit) (def, line 330)
- [`Mathformer.AutoformalizedCBTChapter3.OpenClosedUnit`](#mathformer-autoformalizedcbtchapter3-openclosedunit) (def, line 338)
- [`Mathformer.AutoformalizedCBTChapter3.CantorLemmaG`](#mathformer-autoformalizedcbtchapter3-cantorlemmag) (structure, line 350)
- [`Mathformer.AutoformalizedCBTChapter3.cantorLemmaG_samePower`](#mathformer-autoformalizedcbtchapter3-cantorlemmag-samepower) (theorem, line 361)
- [`Mathformer.AutoformalizedCBTChapter3.positiveNat`](#mathformer-autoformalizedcbtchapter3-positivenat) (def, line 373)
- [`Mathformer.AutoformalizedCBTChapter3.natPositiveEquiv`](#mathformer-autoformalizedcbtchapter3-natpositiveequiv) (def, line 383)
- [`Mathformer.AutoformalizedCBTChapter3.singleSetCBT_of_sandwich`](#mathformer-autoformalizedcbtchapter3-singlesetcbt-of-sandwich) (theorem, line 406)
- [`Mathformer.AutoformalizedCBTChapter3.ContinuumComb`](#mathformer-autoformalizedcbtchapter3-continuumcomb) (structure, line 420)
- [`Mathformer.AutoformalizedCBTChapter3.continuumComb_tooth_samePower`](#mathformer-autoformalizedcbtchapter3-continuumcomb-tooth-samepower) (theorem, line 433)
- [`Mathformer.AutoformalizedCBTChapter3.FrameMatching`](#mathformer-autoformalizedcbtchapter3-framematching) (structure, line 444)
- [`Mathformer.AutoformalizedCBTChapter3.sigmaFrameEquiv`](#mathformer-autoformalizedcbtchapter3-sigmaframeequiv) (def, line 459)
- [`Mathformer.AutoformalizedCBTChapter3.frameMatching_taggedUnion_samePower`](#mathformer-autoformalizedcbtchapter3-framematching-taggedunion-samepower) (theorem, line 484)
- [`Mathformer.AutoformalizedCBTChapter3.SingleSetFrameShift`](#mathformer-autoformalizedcbtchapter3-singlesetframeshift) (structure, line 499)
- [`Mathformer.AutoformalizedCBTChapter3.singleSetFrameShift_samePower`](#mathformer-autoformalizedcbtchapter3-singlesetframeshift-samepower) (theorem, line 515)
- [`Mathformer.AutoformalizedCBTChapter3.no_surjective_to_powerset`](#mathformer-autoformalizedcbtchapter3-no-surjective-to-powerset) (theorem, line 527)
- [`Mathformer.AutoformalizedCBTChapter3.no_surjective_to_bool_functions`](#mathformer-autoformalizedcbtchapter3-no-surjective-to-bool-functions) (theorem, line 539)
- [`Mathformer.AutoformalizedCBTChapter3.CantorComparisonProgram`](#mathformer-autoformalizedcbtchapter3-cantorcomparisonprogram) (structure, line 557)
- [`Mathformer.AutoformalizedCBTChapter3.higher_not_samePower_continuum`](#mathformer-autoformalizedcbtchapter3-higher-not-samepower-continuum) (theorem, line 574)
- [`Mathformer.AutoformalizedCBTChapter3.SecondNumberClassEvidence`](#mathformer-autoformalizedcbtchapter3-secondnumberclassevidence) (structure, line 590)
- [`Mathformer.AutoformalizedCBTChapter3.secondClass_not_samePower_nat`](#mathformer-autoformalizedcbtchapter3-secondclass-not-samepower-nat) (theorem, line 606)

<a id="mathformer-autoformalizedcbtchapter3-samepower"></a>

## `Mathformer.AutoformalizedCBTChapter3.SamePower`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean:56](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean#L56)

**Original Source**

Cantor says that two well-defined sets fully and unequivocally correlate element by element exactly when they have equal power, or are equivalent.

**Original LaTeX**

```latex
`M \sim N`.
Source anchors: src_L0015-src_L0022; src_L0043-src_L0047
```

$$
M \sim N
$$

**Generated Notes**

In mathlib-compatible form, `SamePower A B` is `Nonempty (A ≃ B)`, an equivalence between set subtypes.

**Lean**

```lean
def SamePower {α : Type u} {β : Type v} (A : Set α) (B : Set β) : Prop :=
  Nonempty (A ≃ B)

namespace SamePower
```

<a id="mathformer-autoformalizedcbtchapter3-samepower-refl"></a>

## `Mathformer.AutoformalizedCBTChapter3.SamePower.refl`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean:69](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean#L69)

**Original Source**

Cantor did not prove that `\sim` is reflexive, symmetric, and transitive; this later became the customary rhythm for equivalence relations.

**Original LaTeX**

```latex
`A \sim A`.
Source anchors: src_L0048-src_L0052
```

$$
A \sim A
$$

**Generated Notes**

The Lean signature is exactly `SamePower A A`.

**Lean**

```lean
theorem refl {α : Type u} (A : Set α) : SamePower A A := by
  exact ⟨Equiv.refl A⟩
```

<a id="mathformer-autoformalizedcbtchapter3-samepower-symm"></a>

## `Mathformer.AutoformalizedCBTChapter3.SamePower.symm`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean:80](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean#L80)

**Original Source**

Cantor's relation of equivalence between sets is symmetric in modern equivalence-relation form.

**Original LaTeX**

```latex
`A \sim B \Rightarrow B \sim A`.
Source anchors: src_L0048-src_L0052
```

$$
A \sim B \Rightarrow B \sim A
$$

**Generated Notes**

The Lean signature turns `SamePower A B` into `SamePower B A`.

**Lean**

```lean
theorem symm {α : Type u} {β : Type v} {A : Set α} {B : Set β}
    (h : SamePower A B) : SamePower B A := by
  rcases h with ⟨e⟩
  exact ⟨e.symm⟩
```

<a id="mathformer-autoformalizedcbtchapter3-samepower-trans"></a>

## `Mathformer.AutoformalizedCBTChapter3.SamePower.trans`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean:93](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean#L93)

**Original Source**

Cantor's equivalence of sets is transitive in modern equivalence-relation form.

**Original LaTeX**

```latex
`A \sim B \wedge B \sim C \Rightarrow A \sim C`.
Source anchors: src_L0048-src_L0052
```

$$
A \sim B \wedge B \sim C \Rightarrow A \sim C
$$

**Generated Notes**

The Lean signature composes `SamePower A B` and `SamePower B C` into `SamePower A C`.

**Lean**

```lean
theorem trans {α : Type u} {β : Type v} {γ : Type w}
    {A : Set α} {B : Set β} {C : Set γ}
    (hAB : SamePower A B) (hBC : SamePower B C) : SamePower A C := by
  rcases hAB with ⟨eAB⟩
  rcases hBC with ⟨eBC⟩
  exact ⟨eAB.trans eBC⟩

end SamePower
```

<a id="mathformer-autoformalizedcbtchapter3-cantorwelldefinedset"></a>

## `Mathformer.AutoformalizedCBTChapter3.CantorWellDefinedSet`

- Kind: `structure`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean:112](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean#L112)

**Original Source**

Cantor's later definition of a well-defined set requires that membership and equality of objects in the same conceptual sphere be determined.

**Original LaTeX**

```latex
membership and equality are determined by the logical
principle of excluded third.
Source anchors: src_L0023-src_L0033
```

$$
membership and equality are determined by the logical principle of excluded third. Source anchors: src_L0023-src_L0033
$$

**Generated Notes**

This record keeps the source's conceptual-sphere condition explicit.

**Lean**

```lean
structure CantorWellDefinedSet (ConceptualSphere : Type u) where
  carrier : Set ConceptualSphere
  membership_decidable : ∀ x : ConceptualSphere, Decidable (x ∈ carrier)
  equality_decidable : ∀ x y : ConceptualSphere, Decidable (x = y)
```

<a id="mathformer-autoformalizedcbtchapter3-powerclass"></a>

## `Mathformer.AutoformalizedCBTChapter3.PowerClass`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean:123](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean#L123)

**Original Source**

The partitions in Cantor's continuum-hypothesis formulation are equivalence classes for the relation of equal power.

**Original LaTeX**

```latex
sets of equal power are put in the same partition.
Source anchors: src_L0034-src_L0042
```

$$
sets of equal power are put in the same partition. Source anchors: src_L0034-src_L0042
$$

**Lean**

```lean
def PowerClass {α : Type u} (A : Set α) : Set (Set α) :=
  {B | SamePower B A}
```

<a id="mathformer-autoformalizedcbtchapter3-mem-powerclass-iff"></a>

## `Mathformer.AutoformalizedCBTChapter3.mem_powerClass_iff`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean:132](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean#L132)

**Original Source**

A set belongs to the equal-power class of `A` exactly when it is equivalent to `A`.

**Original LaTeX**

```latex
`B \in [A]_\sim \leftrightarrow B \sim A`.
Source anchors: src_L0034-src_L0042
```

$$
B \in [A]_\sim \leftrightarrow B \sim A
$$

**Lean**

```lean
theorem mem_powerClass_iff {α : Type u} {A B : Set α} :
    B ∈ PowerClass A ↔ SamePower B A := by
  rfl
```

<a id="mathformer-autoformalizedcbtchapter3-inclusionembedding"></a>

## `Mathformer.AutoformalizedCBTChapter3.inclusionEmbedding`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean:141](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean#L141)

**Generated Notes**

An inclusion of sets induces an embedding of subtypes.

**Generated LaTeX**

```latex
`A\subseteq B \Rightarrow A \hookrightarrow B`.
Source anchors: src_L0053-src_L0056
```

$$
A\subseteq B \Rightarrow A \hookrightarrow B
$$

**Lean**

```lean
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
```

<a id="mathformer-autoformalizedcbtchapter3-embeddingtrans"></a>

## `Mathformer.AutoformalizedCBTChapter3.embeddingTrans`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean:159](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean#L159)

**Generated Notes**

Embeddings compose.  This small helper keeps the Schroeder-Bernstein applications below independent of method names.

**Generated LaTeX**

```latex
`(A\hookrightarrow B) \wedge (B\hookrightarrow C)
\Rightarrow A\hookrightarrow C`.
Source anchors: src_L0073-src_L0096
```

$$
(A\hookrightarrow B) \wedge (B\hookrightarrow C) \Rightarrow A\hookrightarrow C
$$

**Lean**

```lean
def embeddingTrans {α : Type u} {β : Type v} {γ : Type w}
    (f : α ↪ β) (g : β ↪ γ) : α ↪ γ where
  toFun x := g (f x)
  inj' := by
    intro x y hxy
    exact f.injective (g.injective hxy)
```

<a id="mathformer-autoformalizedcbtchapter3-samepower-of-subset-sandwich"></a>

## `Mathformer.AutoformalizedCBTChapter3.samePower_of_subset_sandwich`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean:176](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean#L176)

**Original Source**

If `C \subseteq B \subseteq A` and `A` and `C` are in one equivalence class, CBT excludes `B` from being in a different class.

**Original LaTeX**

```latex
`C \subseteq B \subseteq A` and `A \sim C`
imply `A \sim B`.
Source anchors: src_L0053-src_L0059
```

$$
C \subseteq B \subseteq A
$$

$$
A \sim C
$$

$$
A \sim B
$$

**Generated Notes**

This is the single-set sandwich form of Schroeder-Bernstein: from subsets `C ⊆ B ⊆ A` and `SamePower A C`, Lean proves `SamePower A B`.

**Lean**

```lean
theorem samePower_of_subset_sandwich {α : Type u} {A B C : Set α}
    (hCB : C ⊆ B) (hBA : B ⊆ A) (hAC : SamePower A C) :
    SamePower A B := by
  rcases hAC with ⟨eAC⟩
  exact Function.Embedding.antisymm
    (embeddingTrans eAC.toEmbedding (inclusionEmbedding hCB))
    (inclusionEmbedding hBA)
```

<a id="mathformer-autoformalizedcbtchapter3-powerle"></a>

## `Mathformer.AutoformalizedCBTChapter3.PowerLE`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean:191](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean#L191)

**Original Source**

The order between powers is introduced by saying that `M` has smaller power than `N` when `M` has equal power with a subset of `N`.

**Original LaTeX**

```latex
`M \preceq N` iff there is an injection from `M` into
`N`, equivalently `M` is equipollent with a subset of `N`.
Source anchors: src_L0073-src_L0075
```

$$
M \preceq N
$$

$$
M
$$

$$
N
$$

**Lean**

```lean
def PowerLE {α : Type u} {β : Type v} (A : Set α) (B : Set β) : Prop :=
  Nonempty (A ↪ B)
```

<a id="mathformer-autoformalizedcbtchapter3-powerle-of-samepower-subset"></a>

## `Mathformer.AutoformalizedCBTChapter3.powerLE_of_samePower_subset`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean:202](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean#L202)

**Original Source**

Having equal power with a subset of `B` gives the smaller-or-equal relation between powers.

**Original LaTeX**

```latex
`A \sim C \subseteq B \Rightarrow A \preceq B`.
Source anchors: src_L0073-src_L0078
```

$$
A \sim C \subseteq B \Rightarrow A \preceq B
$$

**Generated Notes**

The Lean signature turns a subset map `C ⊆ B` and `SamePower A C` into `PowerLE A B`.

**Lean**

```lean
theorem powerLE_of_samePower_subset {α : Type u} {β : Type v}
    {A : Set α} {B C : Set β} (hCB : C ⊆ B) (hAC : SamePower A C) :
    PowerLE A B := by
  rcases hAC with ⟨eAC⟩
  exact ⟨embeddingTrans eAC.toEmbedding (inclusionEmbedding hCB)⟩
```

<a id="mathformer-autoformalizedcbtchapter3-powerle-refl"></a>

## `Mathformer.AutoformalizedCBTChapter3.powerLE_refl`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean:213](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean#L213)

**Original Source**

Every set has power less than or equal to itself.

**Original LaTeX**

```latex
`A \preceq A`.
Source anchors: src_L0073-src_L0086
```

$$
A \preceq A
$$

**Lean**

```lean
theorem powerLE_refl {α : Type u} (A : Set α) : PowerLE A A := by
  exact ⟨(Equiv.refl A).toEmbedding⟩
```

<a id="mathformer-autoformalizedcbtchapter3-powerle-trans"></a>

## `Mathformer.AutoformalizedCBTChapter3.powerLE_trans`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean:225](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean#L225)

**Original Source**

Transitivity is essential for Cantor's order relation between powers.

**Original LaTeX**

```latex
`A \preceq B \wedge B \preceq C \Rightarrow
A \preceq C`.
Source anchors: src_L0082-src_L0096
```

$$
A \preceq B \wedge B \preceq C \Rightarrow A \preceq C
$$

**Generated Notes**

The Lean signature composes `PowerLE A B` and `PowerLE B C` into `PowerLE A C`.

**Lean**

```lean
theorem powerLE_trans {α : Type u} {β : Type v} {γ : Type w}
    {A : Set α} {B : Set β} {C : Set γ}
    (hAB : PowerLE A B) (hBC : PowerLE B C) : PowerLE A C := by
  rcases hAB with ⟨eAB⟩
  rcases hBC with ⟨eBC⟩
  exact ⟨embeddingTrans eAB eBC⟩
```

<a id="mathformer-autoformalizedcbtchapter3-powerle-antisymm-samepower"></a>

## `Mathformer.AutoformalizedCBTChapter3.powerLE_antisymm_samePower`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean:241](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean#L241)

**Original Source**

The mutual exclusivity or antisymmetry of the two cases of power inequality is exactly the two-set form of CBT.

**Original LaTeX**

```latex
`(A \preceq B \wedge B \preceq A) \Rightarrow
A \sim B`.
Source anchors: src_L0087-src_L0096; src_L0168-src_L0172
```

$$
(A \preceq B \wedge B \preceq A) \Rightarrow A \sim B
$$

**Generated Notes**

The Lean signature is the Schroeder-Bernstein step from `PowerLE A B` and `PowerLE B A` to `SamePower A B`.

**Lean**

```lean
theorem powerLE_antisymm_samePower {α : Type u} {β : Type v}
    {A : Set α} {B : Set β} (hAB : PowerLE A B) (hBA : PowerLE B A) :
    SamePower A B := by
  rcases hAB with ⟨eAB⟩
  rcases hBA with ⟨eBA⟩
  exact Function.Embedding.antisymm eAB eBA
```

<a id="mathformer-autoformalizedcbtchapter3-powerlt"></a>

## `Mathformer.AutoformalizedCBTChapter3.PowerLT`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean:254](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean#L254)

**Original Source**

Smaller power means embeddability into the other set without equal power.

**Original LaTeX**

```latex
`A \prec B := A \preceq B \wedge \neg A\sim B`.
Source anchors: src_L0073-src_L0096
```

$$
A \prec B := A \preceq B \wedge \neg A\sim B
$$

**Lean**

```lean
def PowerLT {α : Type u} {β : Type v} (A : Set α) (B : Set β) : Prop :=
  PowerLE A B ∧ ¬ SamePower A B
```

<a id="mathformer-autoformalizedcbtchapter3-powerlt-asymm"></a>

## `Mathformer.AutoformalizedCBTChapter3.powerLT_asymm`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean:265](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean#L265)

**Original Source**

The two cases of strict power inequality must be mutually exclusive.

**Original LaTeX**

```latex
not both `A \prec B` and `B \prec A`.
Source anchors: src_L0087-src_L0093
```

$$
A \prec B
$$

$$
B \prec A
$$

**Generated Notes**

The Lean signature proves `¬ PowerLT B A` from `PowerLT A B`.

**Lean**

```lean
theorem powerLT_asymm {α : Type u} {β : Type v} {A : Set α} {B : Set β}
    (hAB : PowerLT A B) : ¬ PowerLT B A := by
  intro hBA
  exact hAB.2 (powerLE_antisymm_samePower hAB.1 hBA.1)
```

<a id="mathformer-autoformalizedcbtchapter3-cantorcomparability"></a>

## `Mathformer.AutoformalizedCBTChapter3.CantorComparability`

- Kind: `structure`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean:277](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean#L277)

**Original Source**

Cantor's comparability assertion says that two non-equivalent sets must be comparable by power.

**Original LaTeX**

```latex
if `\neg M\sim N`, then `M \preceq N` or
`N \preceq M`.
Source anchors: src_L0073-src_L0086
```

$$
\neg M\sim N
$$

$$
M \preceq N
$$

$$
N \preceq M
$$

**Lean**

```lean
structure CantorComparability (α : Type u) where
  comparable : ∀ A B : Set α, ¬ SamePower A B → PowerLE A B ∨ PowerLE B A
```

<a id="mathformer-autoformalizedcbtchapter3-twosetcbt-from-power-antisymmetry"></a>

## `Mathformer.AutoformalizedCBTChapter3.twoSetCBT_from_power_antisymmetry`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean:289](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean#L289)

**Original Source**

Comparability plus mutual exclusivity entails the two-set CBT principle.

**Original LaTeX**

```latex
antisymmetry of `\preceq` gives
`A \preceq B \wedge B \preceq A \Rightarrow A \sim B`.
Source anchors: src_L0087-src_L0096
```

$$
\preceq
$$

$$
A \preceq B \wedge B \preceq A \Rightarrow A \sim B
$$

**Generated Notes**

The Lean signature derives `SamePower A B` from the two embedding-order hypotheses `PowerLE A B` and `PowerLE B A`.

**Lean**

```lean
theorem twoSetCBT_from_power_antisymmetry {α : Type u} {A B : Set α}
    (hAB : PowerLE A B) (hBA : PowerLE B A) : SamePower A B := by
  exact powerLE_antisymm_samePower hAB hBA
```

<a id="mathformer-autoformalizedcbtchapter3-propersubset"></a>

## `Mathformer.AutoformalizedCBTChapter3.ProperSubset`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean:299](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean#L299)

**Original Source**

A set is reflexive if it is equivalent to one of its proper subsets.

**Original LaTeX**

```latex
`\exists B \subsetneq A,\ A \sim B`.
Source anchors: src_L0097-src_L0106
```

$$
\exists B \subsetneq A,\ A \sim B
$$

**Lean**

```lean
def ProperSubset {α : Type u} (B A : Set α) : Prop :=
  B ⊆ A ∧ ∃ a ∈ A, a ∉ B
```

<a id="mathformer-autoformalizedcbtchapter3-cantorreflexive"></a>

## `Mathformer.AutoformalizedCBTChapter3.CantorReflexive`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean:309](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean#L309)

**Original Source**

Infinite sets are characterized in the passage by the possibility of being equivalent to a proper subset.

**Original LaTeX**

```latex
`A` is reflexive iff it has an equivalent proper
subset.
Source anchors: src_L0099-src_L0106
```

$$
A
$$

**Lean**

```lean
def CantorReflexive {α : Type u} (A : Set α) : Prop :=
  ∃ B : Set α, ProperSubset B A ∧ SamePower A B
```

<a id="mathformer-autoformalizedcbtchapter3-not-powerlt-of-samepower"></a>

## `Mathformer.AutoformalizedCBTChapter3.not_powerLT_of_samePower`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean:319](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean#L319)

**Original Source**

The direct allusion warns that mere inclusion or a one-one correspondence into another set is not enough to infer strict inequality of powers without knowing non-equivalence.

**Original LaTeX**

```latex
`A \preceq B` alone does not imply `A \prec B`.
Source anchors: src_L0102-src_L0113
```

$$
A \preceq B
$$

$$
A \prec B
$$

**Lean**

```lean
theorem not_powerLT_of_samePower {α : Type u} {β : Type v}
    {A : Set α} {B : Set β} (h : SamePower A B) : ¬ PowerLT A B := by
  intro hlt
  exact hlt.2 h
```

<a id="mathformer-autoformalizedcbtchapter3-closedunit"></a>

## `Mathformer.AutoformalizedCBTChapter3.ClosedUnit`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean:330](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean#L330)

**Original Source**

Lemma G says that the open-closed interval `(0,1]` has the same power as the closed interval `[0,1]`.

**Original LaTeX**

```latex
`(0,1] \sim [0,1]`.
Source anchors: src_L0114-src_L0121
```

$$
(0,1] \sim [0,1]
$$

**Lean**

```lean
def ClosedUnit : Set ℝ :=
  Set.Icc (0 : ℝ) 1
```

<a id="mathformer-autoformalizedcbtchapter3-openclosedunit"></a>

## `Mathformer.AutoformalizedCBTChapter3.OpenClosedUnit`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean:338](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean#L338)

**Original Source**

In current notation, `y` ranges over `(0,1]`.

**Original LaTeX**

```latex
`(0,1]`.
Source anchors: src_L0118-src_L0121
```

$$
(0,1]
$$

**Lean**

```lean
def OpenClosedUnit : Set ℝ :=
  Set.Ioc (0 : ℝ) 1
```

<a id="mathformer-autoformalizedcbtchapter3-cantorlemmag"></a>

## `Mathformer.AutoformalizedCBTChapter3.CantorLemmaG`

- Kind: `structure`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean:350](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean#L350)

**Original Source**

Cantor's Lemma G is represented as the equivalence data between `(0,1]` and `[0,1]`.

**Original LaTeX**

```latex
`(0,1] \sim [0,1]`.
Source anchors: src_L0116-src_L0135
```

$$
(0,1] \sim [0,1]
$$

**Generated Notes**

The source describes Cantor's geometric/analytic construction.  This record preserves the theorem as explicit data so downstream formalization can later replace it with a fully analytic interval equivalence.

**Lean**

```lean
structure CantorLemmaG where
  equivalence : SamePower OpenClosedUnit ClosedUnit
```

<a id="mathformer-autoformalizedcbtchapter3-cantorlemmag-samepower"></a>

## `Mathformer.AutoformalizedCBTChapter3.cantorLemmaG_samePower`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean:361](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean#L361)

**Original Source**

Lemma G supplies the same-power relation between the open-closed and closed unit intervals.

**Original LaTeX**

```latex
`(0,1] \sim [0,1]`.
Source anchors: src_L0116-src_L0135
```

$$
(0,1] \sim [0,1]
$$

**Generated Notes**

The Lean signature extracts `SamePower OpenClosedUnit ClosedUnit` from the `CantorLemmaG` evidence record.

**Lean**

```lean
theorem cantorLemmaG_samePower (G : CantorLemmaG) :
    SamePower OpenClosedUnit ClosedUnit := by
  exact G.equivalence
```

<a id="mathformer-autoformalizedcbtchapter3-positivenat"></a>

## `Mathformer.AutoformalizedCBTChapter3.positiveNat`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean:373](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean#L373)

**Original Source**

The discrete set of points of `[0,1]` is mapped to the corresponding discrete set in `(0,1]` by pushing `0` down the chain.

**Original LaTeX**

```latex
`0, 1/2, \ldots` maps to `1/2, \ldots`.
Source anchors: src_L0131-src_L0140
```

$$
0, 1/2, \ldots
$$

$$
1/2, \ldots
$$

**Generated Notes**

The abstract chain core is the equivalence between natural numbers and positive natural numbers by successor.

**Lean**

```lean
def positiveNat : Set ℕ :=
  {n | 0 < n}
```

<a id="mathformer-autoformalizedcbtchapter3-natpositiveequiv"></a>

## `Mathformer.AutoformalizedCBTChapter3.natPositiveEquiv`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean:383](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean#L383)

**Original Source**

Pushing the first point down the simple chain gives a bijection from the whole discrete chain to the chain with the first point omitted.

**Original LaTeX**

```latex
`n \mapsto n+1`.
Source anchors: src_L0131-src_L0140
```

$$
n \mapsto n+1
$$

**Lean**

```lean
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
```

<a id="mathformer-autoformalizedcbtchapter3-singlesetcbt-of-sandwich"></a>

## `Mathformer.AutoformalizedCBTChapter3.singleSetCBT_of_sandwich`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean:406](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean#L406)

**Original Source**

Let the conditions of the single-set formulation of CBT hold with `M` of the power of the continuum; then the comb/pushdown mapping gives an equivalence from `M` onto `M'`.

**Original LaTeX**

```latex
`M'' \subseteq M' \subseteq M` and `M \sim M''`
imply `M \sim M'`.
Source anchors: src_L0147-src_L0163
```

$$
M'' \subseteq M' \subseteq M
$$

$$
M \sim M''
$$

$$
M \sim M'
$$

**Generated Notes**

The Lean signature proves `SamePower M Mp` from `Mpp ⊆ Mp`, `Mp ⊆ M`, and `SamePower M Mpp`.

**Lean**

```lean
theorem singleSetCBT_of_sandwich {α : Type u} {M Mp Mpp : Set α}
    (hMppMp : Mpp ⊆ Mp) (hMpM : Mp ⊆ M) (hMMpp : SamePower M Mpp) :
    SamePower M Mp := by
  exact samePower_of_subset_sandwich hMppMp hMpM hMMpp
```

<a id="mathformer-autoformalizedcbtchapter3-continuumcomb"></a>

## `Mathformer.AutoformalizedCBTChapter3.ContinuumComb`

- Kind: `structure`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean:420](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean#L420)

**Original Source**

The continuum comb proof uses disjoint open-closed segments `S_b` standing over each `b` and pushes members down their chains.

**Original LaTeX**

```latex
`S_b` and the map `{b}\cup S_b \to S_b`.
Source anchors: src_L0141-src_L0159
```

$$
S_b
$$

$$
{b}\cup S_b \to S_b
$$

**Generated Notes**

This structure records the local chain data used by the comb proof without committing to a particular analytic construction of each segment inside `[0,1]`.

**Lean**

```lean
structure ContinuumComb (Base Point : Type u) where
  segment : Base → Set Point
  markedPoint : Base → Point
  marked_mem_extended : ∀ b : Base, markedPoint b ∈ ({markedPoint b} ∪ segment b)
  pushdown :
    ∀ b : Base, SamePower ({markedPoint b} ∪ segment b : Set Point) (segment b)
```

<a id="mathformer-autoformalizedcbtchapter3-continuumcomb-tooth-samepower"></a>

## `Mathformer.AutoformalizedCBTChapter3.continuumComb_tooth_samePower`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean:433](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean#L433)

**Original Source**

Each tooth of the comb carries the local pushdown equivalence from the marked point plus its segment onto the open-closed segment.

**Original LaTeX**

```latex
`{b}\cup S_b \sim S_b`.
Source anchors: src_L0153-src_L0163
```

$$
{b}\cup S_b \sim S_b
$$

**Lean**

```lean
theorem continuumComb_tooth_samePower {Base Point : Type u}
    (C : ContinuumComb Base Point) (b : Base) :
    SamePower ({C.markedPoint b} ∪ C.segment b : Set Point) (C.segment b) := by
  exact C.pushdown b
```

<a id="mathformer-autoformalizedcbtchapter3-framematching"></a>

## `Mathformer.AutoformalizedCBTChapter3.FrameMatching`

- Kind: `structure`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean:444](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean#L444)

**Original Source**

The generalized drawing proof matches sub-segments, later called frames, by crisscross equivalences.

**Original LaTeX**

```latex
frames `aa'`, `b'b''`, `bb'`, `a'a''`, ...
Source anchors: src_L0199-src_L0213
```

$$
aa'
$$

$$
b'b''
$$

$$
bb'
$$

**Lean**

```lean
structure FrameMatching (ι : Type u) (α : Type v) (β : Type w) where
  leftFrame : ι → Set α
  rightFrame : ι → Set β
  frameEquiv : ∀ i : ι, leftFrame i ≃ rightFrame i
```

<a id="mathformer-autoformalizedcbtchapter3-sigmaframeequiv"></a>

## `Mathformer.AutoformalizedCBTChapter3.sigmaFrameEquiv`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean:459](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean#L459)

**Original Source**

Because corresponding frames are equivalent, their disjoint framed unions are equivalent.

**Original LaTeX**

```latex
if each frame pair is equivalent, the frame-indexed
unions are equivalent.
Source anchors: src_L0199-src_L0206
```

$$
if each frame pair is equivalent, the frame-indexed unions are equivalent. Source anchors: src_L0199-src_L0206
$$

**Generated Notes**

Tagged sigma types are the mathlib-safe version of disjoint unions of frames, and `sigmaFrameEquiv` builds an `Equiv` between the two sigma frame spaces.

**Lean**

```lean
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
```

<a id="mathformer-autoformalizedcbtchapter3-framematching-taggedunion-samepower"></a>

## `Mathformer.AutoformalizedCBTChapter3.frameMatching_taggedUnion_samePower`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean:484](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean#L484)

**Original Source**

The frame proof can be generalized to any sets by taking the given mappings instead of the parallel lines used in the drawing.

**Original LaTeX**

```latex
replace parallels by arbitrary one-one maps between
corresponding frames.
Source anchors: src_L0207-src_L0219
```

$$
replace parallels by arbitrary one-one maps between corresponding frames. Source anchors: src_L0207-src_L0219
$$

**Generated Notes**

The Lean signature proves `SamePower` between universal sets over the tagged sigma frame spaces.

**Lean**

```lean
theorem frameMatching_taggedUnion_samePower {ι : Type u}
    {α : Type v} {β : Type w} (F : FrameMatching ι α β) :
    SamePower (Set.univ : Set (Sigma fun i : ι => F.leftFrame i))
      (Set.univ : Set (Sigma fun i : ι => F.rightFrame i)) := by
  refine ⟨?_⟩
  exact Equiv.Set.univ _ |>.trans (sigmaFrameEquiv F.leftFrame F.rightFrame F.frameEquiv |>.trans (Equiv.Set.univ _).symm)
```

<a id="mathformer-autoformalizedcbtchapter3-singlesetframeshift"></a>

## `Mathformer.AutoformalizedCBTChapter3.SingleSetFrameShift`

- Kind: `structure`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean:499](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean#L499)

**Original Source**

Cantor's drawing also yields the single-set formulation: one maps each triangular frame to the next and leaves all other points fixed.

**Original LaTeX**

```latex
frame shift plus identity outside the framed part.
Source anchors: src_L0214-src_L0222
```

$$
frame shift plus identity outside the framed part. Source anchors: src_L0214-src_L0222
$$

**Generated Notes**

This structure records the abstract ingredients of such a single-set frame shift.

**Lean**

```lean
structure SingleSetFrameShift (α : Type u) (ι : Type v) where
  bigSet : Set α
  middleSet : Set α
  smallSet : Set α
  small_subset_middle : smallSet ⊆ middleSet
  middle_subset_big : middleSet ⊆ bigSet
  frameIndex : ι → Set α
  shift_equiv : SamePower bigSet smallSet
```

<a id="mathformer-autoformalizedcbtchapter3-singlesetframeshift-samepower"></a>

## `Mathformer.AutoformalizedCBTChapter3.singleSetFrameShift_samePower`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean:515](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean#L515)

**Original Source**

A single-set frame shift with `smallSet \subseteq middleSet \subseteq bigSet` yields the single-set CBT conclusion.

**Original LaTeX**

```latex
`small \subseteq middle \subseteq big` and
`big \sim small` imply `big \sim middle`.
Source anchors: src_L0214-src_L0219
```

$$
small \subseteq middle \subseteq big
$$

$$
big \sim small
$$

$$
big \sim middle
$$

**Lean**

```lean
theorem singleSetFrameShift_samePower {α : Type u} {ι : Type v}
    (S : SingleSetFrameShift α ι) : SamePower S.bigSet S.middleSet := by
  exact singleSetCBT_of_sandwich S.small_subset_middle S.middle_subset_big S.shift_equiv
```

<a id="mathformer-autoformalizedcbtchapter3-no-surjective-to-powerset"></a>

## `Mathformer.AutoformalizedCBTChapter3.no_surjective_to_powerset`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean:527](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean#L527)

**Original Source**

Cantor knew that the positive integers and the continuum have different powers.

**Original LaTeX**

```latex
`\mathbb N \not\sim \mathbb R`.
Source anchors: src_L0246-src_L0258
```

$$
\mathbb N \not\sim \mathbb R
$$

**Generated Notes**

We expose the standard diagonal obstruction: no type surjects onto its powerset, formalized as `¬ Surjective f`.

**Lean**

```lean
theorem no_surjective_to_powerset {α : Type u} (f : α → Set α) :
    ¬ Surjective f := by
  exact Function.cantor_surjective f
```

<a id="mathformer-autoformalizedcbtchapter3-no-surjective-to-bool-functions"></a>

## `Mathformer.AutoformalizedCBTChapter3.no_surjective_to_bool_functions`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean:539](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean#L539)

**Original Source**

A direct proof that the set of all real functions has power greater than the power of `R` is obtained by diagonalizing.

**Original LaTeX**

```latex
define `g` by changing the diagonal value of `f_x`.
Source anchors: src_L0279-src_L0286
```

$$
g
$$

$$
f_x
$$

**Generated Notes**

The Boolean-valued version is the clean set-theoretic diagonal core of the real-function argument, formalized as `¬ Surjective F`.

**Lean**

```lean
theorem no_surjective_to_bool_functions {α : Type u} (F : α → α → Bool) :
    ¬ Surjective F := by
  intro hsurj
  let g : α → Bool := fun x => !F x x
  rcases hsurj g with ⟨x, hx⟩
  have hdiag : F x x = !F x x := by
    simpa [g] using congrFun hx x
  cases hFx : F x x <;> simp [hFx] at hdiag
```

<a id="mathformer-autoformalizedcbtchapter3-cantorcomparisonprogram"></a>

## `Mathformer.AutoformalizedCBTChapter3.CantorComparisonProgram`

- Kind: `structure`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean:557](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean#L557)

**Original Source**

Cantor's comparison program compares natural mathematical sets by their powers and motivates the comparability assertion.

**Original LaTeX**

```latex
compare powers of `\mathbb N`, `\mathbb R`, `(II)`,
and function spaces.
Source anchors: src_L0246-src_L0312
```

$$
\mathbb N
$$

$$
\mathbb R
$$

$$
(II)
$$

**Generated Notes**

The record stores a finite observed comparison program with a diagonal higher-power witness.

**Lean**

```lean
structure CantorComparisonProgram where
  NaturalPower : Type u
  ContinuumPower : Type v
  HigherPower : Type w
  natural_embeds_continuum : Nonempty (NaturalPower ↪ ContinuumPower)
  continuum_embeds_higher : Nonempty (ContinuumPower ↪ HigherPower)
  higher_not_below_continuum : ¬ Nonempty (HigherPower ↪ ContinuumPower)
```

<a id="mathformer-autoformalizedcbtchapter3-higher-not-samepower-continuum"></a>

## `Mathformer.AutoformalizedCBTChapter3.higher_not_samePower_continuum`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean:574](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean#L574)

**Original Source**

If a higher power does not embed into the continuum, then it is not equipollent with the continuum.

**Original LaTeX**

```latex
`Higher \not\preceq Continuum \Rightarrow
Higher \not\sim Continuum`.
Source anchors: src_L0279-src_L0286
```

$$
Higher \not\preceq Continuum \Rightarrow Higher \not\sim Continuum
$$

**Generated Notes**

The Lean signature proves `¬ Nonempty (HigherPower ≃ ContinuumPower)` from a missing embedding witness into the continuum.

**Lean**

```lean
theorem higher_not_samePower_continuum (P : CantorComparisonProgram) :
    ¬ Nonempty (P.HigherPower ≃ P.ContinuumPower) := by
  intro h
  rcases h with ⟨e⟩
  exact P.higher_not_below_continuum ⟨e.toEmbedding⟩
```

<a id="mathformer-autoformalizedcbtchapter3-secondnumberclassevidence"></a>

## `Mathformer.AutoformalizedCBTChapter3.SecondNumberClassEvidence`

- Kind: `structure`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean:590](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean#L590)

**Original Source**

Cantor's denumerable union theorem and denumerable CBT could be used with the Sequent Lemma to prove non-denumerability of `(II)`.

**Original LaTeX**

```latex
the denumerability proofs plus sequent lemma separate
`(II)` from the first number-class.
Source anchors: src_L0288-src_L0335
```

$$
(II)
$$

**Generated Notes**

The source-level argument is recorded as a reusable evidence packet rather than as a construction of Cantor's historical second number-class.

**Lean**

```lean
structure SecondNumberClassEvidence (FirstClass SecondClass : Type u) where
  first_embeds_second : Nonempty (FirstClass ↪ SecondClass)
  second_not_denumerable : ¬ Nonempty (SecondClass ↪ ℕ)
  sequent_generation_principle_available : Prop
  denumerable_union_available : Prop
  denumerable_CBT_available : Prop
```

<a id="mathformer-autoformalizedcbtchapter3-secondclass-not-samepower-nat"></a>

## `Mathformer.AutoformalizedCBTChapter3.secondClass_not_samePower_nat`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean:606](../../../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean#L606)

**Original Source**

If the second number-class does not embed into `N`, then it cannot have the same power as `N`.

**Original LaTeX**

```latex
`(II) \not\preceq \mathbb N \Rightarrow
(II) \not\sim \mathbb N`.
Source anchors: src_L0288-src_L0335
```

$$
(II) \not\preceq \mathbb N \Rightarrow (II) \not\sim \mathbb N
$$

**Generated Notes**

The Lean signature proves `¬ Nonempty (SecondClass ≃ ℕ)` from `second_not_denumerable`.

**Lean**

```lean
theorem secondClass_not_samePower_nat {FirstClass SecondClass : Type u}
    (E : SecondNumberClassEvidence FirstClass SecondClass) :
    ¬ Nonempty (SecondClass ≃ ℕ) := by
  intro h
  rcases h with ⟨e⟩
  exact E.second_not_denumerable ⟨e.toEmbedding⟩

end AutoformalizedCBTChapter3
end Mathformer
```
