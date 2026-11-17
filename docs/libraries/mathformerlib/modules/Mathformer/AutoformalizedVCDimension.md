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

# `Mathformer.AutoformalizedVCDimension`

[Back to index](../../INDEX.md)

## Metadata

- Source: [backends/lean/Mathformer/AutoformalizedVCDimension.lean](../../../../../backends/lean/Mathformer/AutoformalizedVCDimension.lean)
- Status: `candidate`
- SHA-256: `c681ca27c0aa11f458432c9425592607dd9df3473ce85df8b30fe6adc2d34c79`
- Declarations: `12`

## Imports

```lean
import Mathlib.Data.Set.Card
```

## Module Source Notes

**Original Source**

The Vapnik--Chervonenkis dimension measures the capacity of a family of sets, or equivalently a binary hypothesis class. A set `X` is shattered by a family `𝒞` when every subset of `X` is realized as `C ∩ X` for some `C ∈ 𝒞`. The VC dimension is the cardinality of the largest shattered set; if arbitrarily large finite sets are shattered, the VC dimension is infinite.

**Original LaTeX**

```latex
for a set family `\mathcal C`,
`\mathcal C \cap X := \{C \cap X \mid C \in \mathcal C\}`. The set `X` is
shattered iff `\mathcal P(X)=\mathcal C \cap X`. The VC dimension is
`\max\{|X| : X \text{ is shattered by } \mathcal C\}`, or `\infty` if such
finite cardinalities are unbounded.

Mathlib grounding: this module uses mathlib's `Set` and finite-set cardinal API
to formalize the core set-family definition and finite/infinite VC-dimension
predicates. Classification-model formulations can be mapped into this interface
by taking the positive regions of binary classifiers.
```

$$
\mathcal C
$$

$$
\mathcal C \cap X := \{C \cap X \mid C \in \mathcal C\}
$$

$$
X
$$

## Declarations

- [`Mathformer.AutoformalizedVCDimension.Trace`](#mathformer-autoformalizedvcdimension-trace) (def, line 45)
- [`Mathformer.AutoformalizedVCDimension.Shatters`](#mathformer-autoformalizedvcdimension-shatters) (def, line 54)
- [`Mathformer.AutoformalizedVCDimension.mem_trace_iff`](#mathformer-autoformalizedvcdimension-mem-trace-iff) (theorem, line 63)
- [`Mathformer.AutoformalizedVCDimension.trace_subset_powerset`](#mathformer-autoformalizedvcdimension-trace-subset-powerset) (theorem, line 75)
- [`Mathformer.AutoformalizedVCDimension.shatters_iff_trace_eq_powerset`](#mathformer-autoformalizedvcdimension-shatters-iff-trace-eq-powerset) (theorem, line 87)
- [`Mathformer.AutoformalizedVCDimension.Shatters.mono`](#mathformer-autoformalizedvcdimension-shatters-mono) (theorem, line 110)
- [`Mathformer.AutoformalizedVCDimension.VCdimAtLeast`](#mathformer-autoformalizedvcdimension-vcdimatleast) (def, line 135)
- [`Mathformer.AutoformalizedVCDimension.InfiniteVCdim`](#mathformer-autoformalizedvcdimension-infinitevcdim) (def, line 144)
- [`Mathformer.AutoformalizedVCDimension.HasFiniteVCdim`](#mathformer-autoformalizedvcdimension-hasfinitevcdim) (def, line 154)
- [`Mathformer.AutoformalizedVCDimension.HasFiniteVCdim.atLeast`](#mathformer-autoformalizedvcdimension-hasfinitevcdim-atleast) (theorem, line 163)
- [`Mathformer.AutoformalizedVCDimension.HasFiniteVCdim.not_atLeast_succ`](#mathformer-autoformalizedvcdimension-hasfinitevcdim-not-atleast-succ) (theorem, line 175)
- [`Mathformer.AutoformalizedVCDimension.shatters_empty_of_nonempty`](#mathformer-autoformalizedvcdimension-shatters-empty-of-nonempty) (theorem, line 187)

<a id="mathformer-autoformalizedvcdimension-trace"></a>

## `Mathformer.AutoformalizedVCDimension.Trace`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedVCDimension.lean:45](../../../../../backends/lean/Mathformer/AutoformalizedVCDimension.lean#L45)

**Original Source**

The trace, or intersection family, of a set family `𝒞` on `X` consists of all intersections `C ∩ X` with `C ∈ 𝒞`.

**Original LaTeX**

```latex
`\mathcal C \cap X := \{C \cap X \mid C \in \mathcal C\}`.
```

$$
\mathcal C \cap X := \{C \cap X \mid C \in \mathcal C\}
$$

**Lean**

```lean
def Trace (𝒞 : Set (Set α)) (X : Set α) : Set (Set α) :=
  {Y | ∃ C ∈ 𝒞, Y = C ∩ X}
```

<a id="mathformer-autoformalizedvcdimension-shatters"></a>

## `Mathformer.AutoformalizedVCDimension.Shatters`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedVCDimension.lean:54](../../../../../backends/lean/Mathformer/AutoformalizedVCDimension.lean#L54)

**Original Source**

A set `X` is shattered by `𝒞` when every subset of `X` is realized as an intersection with a member of `𝒞`.

**Original LaTeX**

```latex
`X` is shattered iff
`\forall Y \subseteq X,\ \exists C \in \mathcal C,\ C \cap X = Y`.
```

$$
X
$$

$$
\forall Y \subseteq X,\ \exists C \in \mathcal C,\ C \cap X = Y
$$

**Lean**

```lean
def Shatters (𝒞 : Set (Set α)) (X : Set α) : Prop :=
  ∀ Y : Set α, Y ⊆ X → ∃ C ∈ 𝒞, C ∩ X = Y
```

<a id="mathformer-autoformalizedvcdimension-mem-trace-iff"></a>

## `Mathformer.AutoformalizedVCDimension.mem_trace_iff`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedVCDimension.lean:63](../../../../../backends/lean/Mathformer/AutoformalizedVCDimension.lean#L63)

**Generated Notes**

Membership in the trace is exactly being an intersection with some concept in the family.

**Generated LaTeX**

```latex
`Y \in \mathcal C \cap X` iff
`\exists C \in \mathcal C,\ Y = C \cap X`.
```

$$
Y \in \mathcal C \cap X
$$

$$
\exists C \in \mathcal C,\ Y = C \cap X
$$

**Lean**

```lean
theorem mem_trace_iff {𝒞 : Set (Set α)} {X Y : Set α} :
    Y ∈ Trace 𝒞 X ↔ ∃ C ∈ 𝒞, Y = C ∩ X := by
  constructor
  · intro h
    assumption
  · intro h
    assumption
```

<a id="mathformer-autoformalizedvcdimension-trace-subset-powerset"></a>

## `Mathformer.AutoformalizedVCDimension.trace_subset_powerset`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedVCDimension.lean:75](../../../../../backends/lean/Mathformer/AutoformalizedVCDimension.lean#L75)

**Generated Notes**

Every trace member is a subset of the base set being traced.

**Generated LaTeX**

```latex
if `Y=C\cap X`, then `Y \subseteq X`.
```

$$
Y=C\cap X
$$

$$
Y \subseteq X
$$

**Lean**

```lean
theorem trace_subset_powerset {𝒞 : Set (Set α)} {X Y : Set α}
    (hY : Y ∈ Trace 𝒞 X) :
    Y ⊆ X := by
  rcases hY with ⟨C, _hC, rfl⟩
  exact inter_subset_right
```

<a id="mathformer-autoformalizedvcdimension-shatters-iff-trace-eq-powerset"></a>

## `Mathformer.AutoformalizedVCDimension.shatters_iff_trace_eq_powerset`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedVCDimension.lean:87](../../../../../backends/lean/Mathformer/AutoformalizedVCDimension.lean#L87)

**Original Source**

Shattering is equivalent to the trace on `X` containing exactly all subsets of `X`.

**Original LaTeX**

```latex
`X` is shattered iff
`\mathcal C \cap X = \mathcal P(X)`.
```

$$
X
$$

$$
\mathcal C \cap X = \mathcal P(X)
$$

**Lean**

```lean
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
```

<a id="mathformer-autoformalizedvcdimension-shatters-mono"></a>

## `Mathformer.AutoformalizedVCDimension.Shatters.mono`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedVCDimension.lean:110](../../../../../backends/lean/Mathformer/AutoformalizedVCDimension.lean#L110)

**Generated Notes**

Shattering is downward closed: every subset of a shattered set is also shattered.

**Generated LaTeX**

```latex
if `Y \subseteq X` and `X` is shattered, then
`Y` is shattered.
```

$$
Y \subseteq X
$$

$$
X
$$

$$
Y
$$

**Lean**

```lean
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
```

<a id="mathformer-autoformalizedvcdimension-vcdimatleast"></a>

## `Mathformer.AutoformalizedVCDimension.VCdimAtLeast`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedVCDimension.lean:135](../../../../../backends/lean/Mathformer/AutoformalizedVCDimension.lean#L135)

**Original Source**

A set family has VC dimension at least `d` when it shatters some finite set of cardinality `d`.

**Original LaTeX**

```latex
`\operatorname{VCdim}(\mathcal C) \ge d` iff
`\exists X,\ |X|=d` and `X` is shattered by `\mathcal C`.
```

$$
\operatorname{VCdim}(\mathcal C) \ge d
$$

$$
\exists X,\ |X|=d
$$

$$
X
$$

**Lean**

```lean
def VCdimAtLeast (𝒞 : Set (Set α)) (d : ℕ) : Prop :=
  ∃ X : Set α, X.Finite ∧ X.ncard = d ∧ Shatters 𝒞 X
```

<a id="mathformer-autoformalizedvcdimension-infinitevcdim"></a>

## `Mathformer.AutoformalizedVCDimension.InfiniteVCdim`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedVCDimension.lean:144](../../../../../backends/lean/Mathformer/AutoformalizedVCDimension.lean#L144)

**Original Source**

The VC dimension is infinite when arbitrarily large finite sets can be shattered.

**Original LaTeX**

```latex
`\operatorname{VCdim}(\mathcal C)=\infty` iff
`\forall d,\ \exists X,\ |X|=d` and `X` is shattered.
```

$$
\operatorname{VCdim}(\mathcal C)=\infty
$$

$$
\forall d,\ \exists X,\ |X|=d
$$

$$
X
$$

**Lean**

```lean
def InfiniteVCdim (𝒞 : Set (Set α)) : Prop :=
  ∀ d : ℕ, VCdimAtLeast 𝒞 d
```

<a id="mathformer-autoformalizedvcdimension-hasfinitevcdim"></a>

## `Mathformer.AutoformalizedVCDimension.HasFiniteVCdim`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedVCDimension.lean:154](../../../../../backends/lean/Mathformer/AutoformalizedVCDimension.lean#L154)

**Original Source**

A finite VC dimension `d` means some `d`-point set is shattered and no `(d+1)`-point finite set is shattered.

**Original LaTeX**

```latex
`\operatorname{VCdim}(\mathcal C)=d` iff
`\operatorname{VCdim}(\mathcal C)\ge d` and not
`\operatorname{VCdim}(\mathcal C)\ge d+1`.
```

$$
\operatorname{VCdim}(\mathcal C)=d
$$

$$
\operatorname{VCdim}(\mathcal C)\ge d
$$

$$
\operatorname{VCdim}(\mathcal C)\ge d+1
$$

**Lean**

```lean
def HasFiniteVCdim (𝒞 : Set (Set α)) (d : ℕ) : Prop :=
  VCdimAtLeast 𝒞 d ∧ ¬ VCdimAtLeast 𝒞 (d + 1)
```

<a id="mathformer-autoformalizedvcdimension-hasfinitevcdim-atleast"></a>

## `Mathformer.AutoformalizedVCDimension.HasFiniteVCdim.atLeast`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedVCDimension.lean:163](../../../../../backends/lean/Mathformer/AutoformalizedVCDimension.lean#L163)

**Generated Notes**

A family with finite VC dimension `d` has VC dimension at least `d`.

**Generated LaTeX**

```latex
`\operatorname{VCdim}(\mathcal C)=d` implies
`\operatorname{VCdim}(\mathcal C)\ge d`.
```

$$
\operatorname{VCdim}(\mathcal C)=d
$$

$$
\operatorname{VCdim}(\mathcal C)\ge d
$$

**Lean**

```lean
theorem HasFiniteVCdim.atLeast {𝒞 : Set (Set α)} {d : ℕ}
    (h : HasFiniteVCdim 𝒞 d) :
    VCdimAtLeast 𝒞 d := by
  rcases h with ⟨atLeastProof, _⟩
  exact atLeastProof
```

<a id="mathformer-autoformalizedvcdimension-hasfinitevcdim-not-atleast-succ"></a>

## `Mathformer.AutoformalizedVCDimension.HasFiniteVCdim.not_atLeast_succ`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedVCDimension.lean:175](../../../../../backends/lean/Mathformer/AutoformalizedVCDimension.lean#L175)

**Generated Notes**

A family with finite VC dimension `d` does not shatter a set of cardinality `d+1`.

**Generated LaTeX**

```latex
`\operatorname{VCdim}(\mathcal C)=d` implies not
`\operatorname{VCdim}(\mathcal C)\ge d+1`.
```

$$
\operatorname{VCdim}(\mathcal C)=d
$$

$$
\operatorname{VCdim}(\mathcal C)\ge d+1
$$

**Lean**

```lean
theorem HasFiniteVCdim.not_atLeast_succ {𝒞 : Set (Set α)} {d : ℕ}
    (h : HasFiniteVCdim 𝒞 d) :
    ¬ VCdimAtLeast 𝒞 (d + 1) := by
  rcases h with ⟨_, notAtLeastSuccProof⟩
  exact notAtLeastSuccProof
```

<a id="mathformer-autoformalizedvcdimension-shatters-empty-of-nonempty"></a>

## `Mathformer.AutoformalizedVCDimension.shatters_empty_of_nonempty`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedVCDimension.lean:187](../../../../../backends/lean/Mathformer/AutoformalizedVCDimension.lean#L187)

**Generated Notes**

Under the explicit nonemptiness assumption, the empty set is shattered by a set family.

**Generated LaTeX**

```latex
if `\mathcal C \ne \varnothing`, then
`\varnothing` is shattered by `\mathcal C`.
```

$$
\mathcal C \ne \varnothing
$$

$$
\varnothing
$$

$$
\mathcal C
$$

**Lean**

```lean
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
```
