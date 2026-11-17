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

# `Mathformer.AutoformalizedGrowthFunction`

[Back to index](../../INDEX.md)

## Metadata

- Source: [backends/lean/Mathformer/AutoformalizedGrowthFunction.lean](../../../../../backends/lean/Mathformer/AutoformalizedGrowthFunction.lean)
- Status: `candidate`
- SHA-256: `78f685994471622b15c0b474389c4e783766f429d97f844eb0582bbfc3c3091b`
- Declarations: `15`

## Imports

```lean
import Mathformer.AutoformalizedVCDimension
```

## Module Source Notes

**Original Source**

In statistical learning theory, the growth function of a set family or binary hypothesis class counts the largest number of distinct dichotomies the class can induce on an `m`-point sample.

**Original LaTeX**

```latex
for a concept class `\mathcal C`,
`\Pi_{\mathcal C}(m)=\max_{X: |X|=m} |\mathcal C \cap X|`, where
`\mathcal C \cap X=\{C \cap X : C \in \mathcal C\}` is the trace on `X`.

Mathlib grounding: this module reuses the `Trace` and `Shatters` definitions
from `AutoformalizedVCDimension`. The maximum is represented by the predicate
`GrowthFunctionValue`, meaning that the value is both attained by an `m`-point
sample and upper-bounds every `m`-point sample.
```

$$
\mathcal C
$$

$$
\Pi_{\mathcal C}(m)=\max_{X: |X|=m} |\mathcal C \cap X|
$$

$$
\mathcal C \cap X=\{C \cap X : C \in \mathcal C\}
$$

## Declarations

- [`Mathformer.AutoformalizedGrowthFunction.PositiveRegion`](#mathformer-autoformalizedgrowthfunction-positiveregion) (def, line 43)
- [`Mathformer.AutoformalizedGrowthFunction.ConceptClassOfBinary`](#mathformer-autoformalizedgrowthfunction-conceptclassofbinary) (def, line 52)
- [`Mathformer.AutoformalizedGrowthFunction.mem_conceptClassOfBinary_iff`](#mathformer-autoformalizedgrowthfunction-mem-conceptclassofbinary-iff) (theorem, line 61)
- [`Mathformer.AutoformalizedGrowthFunction.GrowthFunctionAtLeast`](#mathformer-autoformalizedgrowthfunction-growthfunctionatleast) (def, line 75)
- [`Mathformer.AutoformalizedGrowthFunction.GrowthFunctionAtMost`](#mathformer-autoformalizedgrowthfunction-growthfunctionatmost) (def, line 84)
- [`Mathformer.AutoformalizedGrowthFunction.GrowthFunctionValue`](#mathformer-autoformalizedgrowthfunction-growthfunctionvalue) (def, line 94)
- [`Mathformer.AutoformalizedGrowthFunction.finite_trace_of_finite`](#mathformer-autoformalizedgrowthfunction-finite-trace-of-finite) (theorem, line 104)
- [`Mathformer.AutoformalizedGrowthFunction.trace_ncard_le_two_pow`](#mathformer-autoformalizedgrowthfunction-trace-ncard-le-two-pow) (theorem, line 117)
- [`Mathformer.AutoformalizedGrowthFunction.growthFunctionAtMost_two_pow`](#mathformer-autoformalizedgrowthfunction-growthfunctionatmost-two-pow) (theorem, line 130)
- [`Mathformer.AutoformalizedGrowthFunction.GrowthFunctionValue.atLeast`](#mathformer-autoformalizedgrowthfunction-growthfunctionvalue-atleast) (theorem, line 141)
- [`Mathformer.AutoformalizedGrowthFunction.GrowthFunctionValue.atMost`](#mathformer-autoformalizedgrowthfunction-growthfunctionvalue-atmost) (theorem, line 153)
- [`Mathformer.AutoformalizedGrowthFunction.trace_ncard_eq_two_pow_of_shatters`](#mathformer-autoformalizedgrowthfunction-trace-ncard-eq-two-pow-of-shatters) (theorem, line 165)
- [`Mathformer.AutoformalizedGrowthFunction.growthFunctionAtLeast_two_pow_of_shatters`](#mathformer-autoformalizedgrowthfunction-growthfunctionatleast-two-pow-of-shatters) (theorem, line 178)
- [`Mathformer.AutoformalizedGrowthFunction.growthFunctionValue_two_pow_of_shatters`](#mathformer-autoformalizedgrowthfunction-growthfunctionvalue-two-pow-of-shatters) (theorem, line 192)
- [`Mathformer.AutoformalizedGrowthFunction.BinaryGrowthFunctionValue`](#mathformer-autoformalizedgrowthfunction-binarygrowthfunctionvalue) (def, line 208)

<a id="mathformer-autoformalizedgrowthfunction-positiveregion"></a>

## `Mathformer.AutoformalizedGrowthFunction.PositiveRegion`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedGrowthFunction.lean:43](../../../../../backends/lean/Mathformer/AutoformalizedGrowthFunction.lean#L43)

**Original Source**

A binary classifier determines the set of points it labels positive.

**Original LaTeX**

```latex
for `h : X \to \{0,1\}`,
`h^{-1}(\{1\}) = \{x : h(x)=1\}`.
```

$$
h : X \to \{0,1\}
$$

$$
h^{-1}(\{1\}) = \{x : h(x)=1\}
$$

**Lean**

```lean
def PositiveRegion (h : α → Bool) : Set α :=
  {x | h x = true}
```

<a id="mathformer-autoformalizedgrowthfunction-conceptclassofbinary"></a>

## `Mathformer.AutoformalizedGrowthFunction.ConceptClassOfBinary`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedGrowthFunction.lean:52](../../../../../backends/lean/Mathformer/AutoformalizedGrowthFunction.lean#L52)

**Original Source**

A binary hypothesis class can be viewed as a concept class by taking all positive regions of its classifiers.

**Original LaTeX**

```latex
`\mathcal C_{\mathcal H} =
\{\{x : h(x)=1\} : h \in \mathcal H\}`.
```

$$
\mathcal C_{\mathcal H} = \{\{x : h(x)=1\} : h \in \mathcal H\}
$$

**Lean**

```lean
def ConceptClassOfBinary (ℋ : Set (α → Bool)) : Set (Set α) :=
  {C | ∃ h ∈ ℋ, C = PositiveRegion h}
```

<a id="mathformer-autoformalizedgrowthfunction-mem-conceptclassofbinary-iff"></a>

## `Mathformer.AutoformalizedGrowthFunction.mem_conceptClassOfBinary_iff`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedGrowthFunction.lean:61](../../../../../backends/lean/Mathformer/AutoformalizedGrowthFunction.lean#L61)

**Generated Notes**

Membership in the concept class of a binary hypothesis hypothesis family is exactly being the positive region of one of its hypotheses.

**Generated LaTeX**

```latex
`C \in \mathcal C_{\mathcal H}` iff
`\exists h \in \mathcal H,\ C=\{x:h(x)=1\}`.
```

$$
C \in \mathcal C_{\mathcal H}
$$

$$
\exists h \in \mathcal H,\ C=\{x:h(x)=1\}
$$

**Lean**

```lean
theorem mem_conceptClassOfBinary_iff {ℋ : Set (α → Bool)} {C : Set α} :
    C ∈ ConceptClassOfBinary ℋ ↔ ∃ h ∈ ℋ, C = PositiveRegion h := by
  constructor
  · intro h
    assumption
  · intro h
    assumption
```

<a id="mathformer-autoformalizedgrowthfunction-growthfunctionatleast"></a>

## `Mathformer.AutoformalizedGrowthFunction.GrowthFunctionAtLeast`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedGrowthFunction.lean:75](../../../../../backends/lean/Mathformer/AutoformalizedGrowthFunction.lean#L75)

**Original Source**

The growth function is at least `n` at sample size `m` when some `m`-point sample has at least `n` distinct traces.

**Original LaTeX**

```latex
`\Pi_{\mathcal C}(m) \ge n` iff
`\exists X,\ |X|=m` and `n \le |\mathcal C \cap X|`.
```

$$
\Pi_{\mathcal C}(m) \ge n
$$

$$
\exists X,\ |X|=m
$$

$$
n \le |\mathcal C \cap X|
$$

**Lean**

```lean
def GrowthFunctionAtLeast (𝒞 : Set (Set α)) (m n : ℕ) : Prop :=
  ∃ X : Set α, X.Finite ∧ X.ncard = m ∧ n ≤ (Trace 𝒞 X).ncard
```

<a id="mathformer-autoformalizedgrowthfunction-growthfunctionatmost"></a>

## `Mathformer.AutoformalizedGrowthFunction.GrowthFunctionAtMost`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedGrowthFunction.lean:84](../../../../../backends/lean/Mathformer/AutoformalizedGrowthFunction.lean#L84)

**Original Source**

The growth function is at most `n` at sample size `m` when every `m`-point sample has at most `n` distinct traces.

**Original LaTeX**

```latex
`\Pi_{\mathcal C}(m) \le n` iff for every `X` with
`|X|=m`, `|\mathcal C \cap X| \le n`.
```

$$
\Pi_{\mathcal C}(m) \le n
$$

$$
X
$$

$$
|X|=m
$$

**Lean**

```lean
def GrowthFunctionAtMost (𝒞 : Set (Set α)) (m n : ℕ) : Prop :=
  ∀ X : Set α, X.Finite → X.ncard = m → (Trace 𝒞 X).ncard ≤ n
```

<a id="mathformer-autoformalizedgrowthfunction-growthfunctionvalue"></a>

## `Mathformer.AutoformalizedGrowthFunction.GrowthFunctionValue`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedGrowthFunction.lean:94](../../../../../backends/lean/Mathformer/AutoformalizedGrowthFunction.lean#L94)

**Original Source**

The growth function has value `n` at sample size `m` when the upper bound `n` is attained by some `m`-point sample.

**Original LaTeX**

```latex
`\Pi_{\mathcal C}(m)=n` iff
`\exists X,\ |X|=m \land |\mathcal C \cap X|=n`, and every `m`-point `Y`
satisfies `|\mathcal C \cap Y| \le n`.
```

$$
\Pi_{\mathcal C}(m)=n
$$

$$
\exists X,\ |X|=m \land |\mathcal C \cap X|=n
$$

$$
m
$$

**Lean**

```lean
def GrowthFunctionValue (𝒞 : Set (Set α)) (m n : ℕ) : Prop :=
  (∃ X : Set α, X.Finite ∧ X.ncard = m ∧ (Trace 𝒞 X).ncard = n) ∧
    GrowthFunctionAtMost 𝒞 m n
```

<a id="mathformer-autoformalizedgrowthfunction-finite-trace-of-finite"></a>

## `Mathformer.AutoformalizedGrowthFunction.finite_trace_of_finite`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedGrowthFunction.lean:104](../../../../../backends/lean/Mathformer/AutoformalizedGrowthFunction.lean#L104)

**Generated Notes**

A trace over a finite sample is finite because it is a subfamily of the finite powerset of the sample.

**Generated LaTeX**

```latex
if `X` is finite, then
`\mathcal C \cap X \subseteq \mathcal P(X)` is finite.
```

$$
X
$$

$$
\mathcal C \cap X \subseteq \mathcal P(X)
$$

**Lean**

```lean
theorem finite_trace_of_finite {𝒞 : Set (Set α)} {X : Set α}
    (hX : X.Finite) :
    (Trace 𝒞 X).Finite := by
  refine hX.powerset.subset ?_
  intro Y hY
  exact trace_subset_powerset hY
```

<a id="mathformer-autoformalizedgrowthfunction-trace-ncard-le-two-pow"></a>

## `Mathformer.AutoformalizedGrowthFunction.trace_ncard_le_two_pow`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedGrowthFunction.lean:117](../../../../../backends/lean/Mathformer/AutoformalizedGrowthFunction.lean#L117)

**Original Source**

The growth function is bounded above by the number of all subsets of an `m`-point sample.

**Original LaTeX**

```latex
for `|X|=m`,
`|\mathcal C \cap X| \le |\mathcal P(X)| = 2^m`.
```

$$
|X|=m
$$

$$
|\mathcal C \cap X| \le |\mathcal P(X)| = 2^m
$$

**Lean**

```lean
theorem trace_ncard_le_two_pow {𝒞 : Set (Set α)} {X : Set α}
    (hX : X.Finite) :
    (Trace 𝒞 X).ncard ≤ 2 ^ X.ncard := by
  calc
    (Trace 𝒞 X).ncard ≤ (𝒫 X).ncard := by
      exact ncard_le_ncard (fun Y hY => trace_subset_powerset hY) hX.powerset
    _ = 2 ^ X.ncard := by
      exact ncard_powerset X hX
```

<a id="mathformer-autoformalizedgrowthfunction-growthfunctionatmost-two-pow"></a>

## `Mathformer.AutoformalizedGrowthFunction.growthFunctionAtMost_two_pow`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedGrowthFunction.lean:130](../../../../../backends/lean/Mathformer/AutoformalizedGrowthFunction.lean#L130)

**Generated Notes**

Therefore the growth function is always at most `2^m`.

**Generated LaTeX**

```latex
`\Pi_{\mathcal C}(m) \le 2^m`.
```

$$
\Pi_{\mathcal C}(m) \le 2^m
$$

**Lean**

```lean
theorem growthFunctionAtMost_two_pow (𝒞 : Set (Set α)) (m : ℕ) :
    GrowthFunctionAtMost 𝒞 m (2 ^ m) := by
  intro X hX hcard
  simpa [hcard] using trace_ncard_le_two_pow (𝒞 := 𝒞) hX
```

<a id="mathformer-autoformalizedgrowthfunction-growthfunctionvalue-atleast"></a>

## `Mathformer.AutoformalizedGrowthFunction.GrowthFunctionValue.atLeast`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedGrowthFunction.lean:141](../../../../../backends/lean/Mathformer/AutoformalizedGrowthFunction.lean#L141)

**Generated Notes**

If a maximum growth value is attained, then it gives the corresponding lower-bound statement.

**Generated LaTeX**

```latex
`\Pi_{\mathcal C}(m)=n` implies
`\Pi_{\mathcal C}(m)\ge n`.
```

$$
\Pi_{\mathcal C}(m)=n
$$

$$
\Pi_{\mathcal C}(m)\ge n
$$

**Lean**

```lean
theorem GrowthFunctionValue.atLeast {𝒞 : Set (Set α)} {m n : ℕ}
    (h : GrowthFunctionValue 𝒞 m n) :
    GrowthFunctionAtLeast 𝒞 m n := by
  rcases h.1 with ⟨X, hXfin, hXm, htrace⟩
  exact ⟨X, hXfin, hXm, le_of_eq htrace.symm⟩
```

<a id="mathformer-autoformalizedgrowthfunction-growthfunctionvalue-atmost"></a>

## `Mathformer.AutoformalizedGrowthFunction.GrowthFunctionValue.atMost`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedGrowthFunction.lean:153](../../../../../backends/lean/Mathformer/AutoformalizedGrowthFunction.lean#L153)

**Generated Notes**

If a maximum growth value is attained, then it gives the corresponding upper-bound statement.

**Generated LaTeX**

```latex
`\Pi_{\mathcal C}(m)=n` implies
`\Pi_{\mathcal C}(m)\le n`.
```

$$
\Pi_{\mathcal C}(m)=n
$$

$$
\Pi_{\mathcal C}(m)\le n
$$

**Lean**

```lean
theorem GrowthFunctionValue.atMost {𝒞 : Set (Set α)} {m n : ℕ}
    (h : GrowthFunctionValue 𝒞 m n) :
    GrowthFunctionAtMost 𝒞 m n := by
  rcases h with ⟨_, atMostProof⟩
  exact atMostProof
```

<a id="mathformer-autoformalizedgrowthfunction-trace-ncard-eq-two-pow-of-shatters"></a>

## `Mathformer.AutoformalizedGrowthFunction.trace_ncard_eq_two_pow_of_shatters`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedGrowthFunction.lean:165](../../../../../backends/lean/Mathformer/AutoformalizedGrowthFunction.lean#L165)

**Original Source**

If an `m`-point sample is shattered, the growth function at `m` reaches the full `2^m` possible dichotomies.

**Original LaTeX**

```latex
if `X` is shattered and `|X|=m`, then
`|\mathcal C \cap X| = 2^m`.
```

$$
X
$$

$$
|X|=m
$$

$$
|\mathcal C \cap X| = 2^m
$$

**Lean**

```lean
theorem trace_ncard_eq_two_pow_of_shatters {𝒞 : Set (Set α)} {X : Set α}
    (hXfin : X.Finite)
    (hshatter : Shatters 𝒞 X) :
    (Trace 𝒞 X).ncard = 2 ^ X.ncard := by
  rw [(shatters_iff_trace_eq_powerset).mp hshatter]
  exact ncard_powerset X hXfin
```

<a id="mathformer-autoformalizedgrowthfunction-growthfunctionatleast-two-pow-of-shatters"></a>

## `Mathformer.AutoformalizedGrowthFunction.growthFunctionAtLeast_two_pow_of_shatters`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedGrowthFunction.lean:178](../../../../../backends/lean/Mathformer/AutoformalizedGrowthFunction.lean#L178)

**Original Source**

A shattered `m`-point sample makes the growth function at least `2^m`.

**Original LaTeX**

```latex
if `\mathcal C` shatters `X` and `|X|=m`, then
`\Pi_{\mathcal C}(m) \ge 2^m`.
```

$$
\mathcal C
$$

$$
X
$$

$$
|X|=m
$$

**Lean**

```lean
theorem growthFunctionAtLeast_two_pow_of_shatters {𝒞 : Set (Set α)} {X : Set α} {m : ℕ}
    (hXfin : X.Finite)
    (hXm : X.ncard = m)
    (hshatter : Shatters 𝒞 X) :
    GrowthFunctionAtLeast 𝒞 m (2 ^ m) := by
  refine ⟨X, hXfin, hXm, ?_⟩
  rw [trace_ncard_eq_two_pow_of_shatters hXfin hshatter, hXm]
```

<a id="mathformer-autoformalizedgrowthfunction-growthfunctionvalue-two-pow-of-shatters"></a>

## `Mathformer.AutoformalizedGrowthFunction.growthFunctionValue_two_pow_of_shatters`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedGrowthFunction.lean:192](../../../../../backends/lean/Mathformer/AutoformalizedGrowthFunction.lean#L192)

**Generated Notes**

If the growth function attains the universal upper bound `2^m`, then its value at `m` is exactly `2^m`.

**Generated LaTeX**

```latex
an attained sample with `2^m` traces plus the
universal bound proves `\Pi_{\mathcal C}(m)=2^m`.
```

$$
2^m
$$

$$
\Pi_{\mathcal C}(m)=2^m
$$

**Lean**

```lean
theorem growthFunctionValue_two_pow_of_shatters {𝒞 : Set (Set α)} {X : Set α} {m : ℕ}
    (hXfin : X.Finite)
    (hXm : X.ncard = m)
    (hshatter : Shatters 𝒞 X) :
    GrowthFunctionValue 𝒞 m (2 ^ m) := by
  constructor
  · refine ⟨X, hXfin, hXm, ?_⟩
    rw [trace_ncard_eq_two_pow_of_shatters hXfin hshatter, hXm]
  · exact growthFunctionAtMost_two_pow 𝒞 m
```

<a id="mathformer-autoformalizedgrowthfunction-binarygrowthfunctionvalue"></a>

## `Mathformer.AutoformalizedGrowthFunction.BinaryGrowthFunctionValue`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedGrowthFunction.lean:208](../../../../../backends/lean/Mathformer/AutoformalizedGrowthFunction.lean#L208)

**Original Source**

The growth function of a binary hypothesis class is the growth function of its associated concept class of positive regions.

**Original LaTeX**

```latex
`\Pi_{\mathcal H}(m)` is represented as
`\Pi_{\mathcal C_{\mathcal H}}(m)`.
```

$$
\Pi_{\mathcal H}(m)
$$

$$
\Pi_{\mathcal C_{\mathcal H}}(m)
$$

**Lean**

```lean
def BinaryGrowthFunctionValue (ℋ : Set (α → Bool)) (m n : ℕ) : Prop :=
  GrowthFunctionValue (ConceptClassOfBinary ℋ) m n

end AutoformalizedGrowthFunction
end Mathformer
```
