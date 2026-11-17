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

# `Mathformer.AutoformalizedChoquetTheory`

[Back to index](../../INDEX.md)

## Metadata

- Source: [backends/lean/Mathformer/AutoformalizedChoquetTheory.lean](../../../../../backends/lean/Mathformer/AutoformalizedChoquetTheory.lean)
- Status: `candidate`
- SHA-256: `16dd7d7d0d5d1d56f90894630ce46c833de3bd35a90fc1946aab4ee19c687ae6`
- Declarations: `20`

## Imports

```lean
import Mathlib.Analysis.Convex.KreinMilman
import Mathlib.MeasureTheory.Measure.ProbabilityMeasure
```

## Module Source Notes

**Original Source**

Choquet theory studies representations of points of compact convex sets by probability measures supported on extreme points. The Wikipedia-level Choquet theorem says that each point of a compact convex metrizable set in a locally convex topological vector space has such a representing measure.

**Original LaTeX**

```latex
for a compact convex metrizable set `K` and `x \in K`,
there is a probability measure `\mu` supported on `\operatorname{Ext}(K)` such
that, equivalently through continuous affine tests,
`f(x)=\int_{\operatorname{Ext}(K)} f(y)\,d\mu(y)`.

Mathlib grounding: local mathlib provides extreme points, continuous affine maps,
probability measures, and Krein--Milman, but not a named Choquet representation
result. This module formalizes the mathlib-native interface, the Krein--Milman
overlap, and consequences of an explicit Choquet representation hypothesis.
```

$$
K
$$

$$
x \in K
$$

$$
\mu
$$

## Declarations

- [`Mathformer.AutoformalizedChoquetTheory.ChoquetSet`](#mathformer-autoformalizedchoquettheory-choquetset) (structure, line 50)
- [`Mathformer.AutoformalizedChoquetTheory.ChoquetSet.instMetrizableSpaceCarrier`](#mathformer-autoformalizedchoquettheory-choquetset-instmetrizablespacecarrier) (instance, line 64)
- [`Mathformer.AutoformalizedChoquetTheory.ChoquetSet.extremePoints`](#mathformer-autoformalizedchoquettheory-choquetset-extremepoints) (def, line 72)
- [`Mathformer.AutoformalizedChoquetTheory.ChoquetSet.extremePoints_subset`](#mathformer-autoformalizedchoquettheory-choquetset-extremepoints-subset) (theorem, line 79)
- [`Mathformer.AutoformalizedChoquetTheory.ChoquetSet.kreinMilman_closure_convexHull_extremePoints`](#mathformer-autoformalizedchoquettheory-choquetset-kreinmilman-closure-convexhull-extremepoints) (theorem, line 88)
- [`Mathformer.AutoformalizedChoquetTheory.ChoquetSet.mem_closure_convexHull_extremePoints`](#mathformer-autoformalizedchoquettheory-choquetset-mem-closure-convexhull-extremepoints) (theorem, line 99)
- [`Mathformer.AutoformalizedChoquetTheory.ChoquetSet.extremePoints_nonempty_of_nonempty`](#mathformer-autoformalizedchoquettheory-choquetset-extremepoints-nonempty-of-nonempty) (theorem, line 110)
- [`Mathformer.AutoformalizedChoquetTheory.ChoquetSet.surjOn_extremePoints_image`](#mathformer-autoformalizedchoquettheory-choquetset-surjon-extremepoints-image) (theorem, line 127)
- [`Mathformer.AutoformalizedChoquetTheory.SupportedOn`](#mathformer-autoformalizedchoquettheory-supportedon) (def, line 142)
- [`Mathformer.AutoformalizedChoquetTheory.supportedOn_mono`](#mathformer-autoformalizedchoquettheory-supportedon-mono) (theorem, line 151)
- [`Mathformer.AutoformalizedChoquetTheory.ChoquetRepresentation`](#mathformer-autoformalizedchoquettheory-choquetrepresentation) (structure, line 163)
- [`Mathformer.AutoformalizedChoquetTheory.ChoquetRepresentation.supportedOnCarrier`](#mathformer-autoformalizedchoquettheory-choquetrepresentation-supportedoncarrier) (theorem, line 178)
- [`Mathformer.AutoformalizedChoquetTheory.ChoquetRepresentation.point_mem_carrier`](#mathformer-autoformalizedchoquettheory-choquetrepresentation-point-mem-carrier) (theorem, line 187)
- [`Mathformer.AutoformalizedChoquetTheory.ChoquetRepresentation.barycenter_formula`](#mathformer-autoformalizedchoquettheory-choquetrepresentation-barycenter-formula) (theorem, line 196)
- [`Mathformer.AutoformalizedChoquetTheory.ChoquetTheoremHypothesis`](#mathformer-autoformalizedchoquettheory-choquettheoremhypothesis) (structure, line 209)
- [`Mathformer.AutoformalizedChoquetTheory.choquet_theorem`](#mathformer-autoformalizedchoquettheory-choquet-theorem) (theorem, line 218)
- [`Mathformer.AutoformalizedChoquetTheory.choquet_exists_representing_measure`](#mathformer-autoformalizedchoquettheory-choquet-exists-representing-measure) (theorem, line 232)
- [`Mathformer.AutoformalizedChoquetTheory.IsChoquetSimplex`](#mathformer-autoformalizedchoquettheory-ischoquetsimplex) (def, line 248)
- [`Mathformer.AutoformalizedChoquetTheory.eq_measure_of_isChoquetSimplex`](#mathformer-autoformalizedchoquettheory-eq-measure-of-ischoquetsimplex) (theorem, line 257)
- [`Mathformer.AutoformalizedChoquetTheory.existsUnique_representingMeasure_of_isChoquetSimplex`](#mathformer-autoformalizedchoquettheory-existsunique-representingmeasure-of-ischoquetsimplex) (theorem, line 270)

<a id="mathformer-autoformalizedchoquettheory-choquetset"></a>

## `Mathformer.AutoformalizedChoquetTheory.ChoquetSet`

- Kind: `structure`
- Source line: [backends/lean/Mathformer/AutoformalizedChoquetTheory.lean:50](../../../../../backends/lean/Mathformer/AutoformalizedChoquetTheory.lean#L50)

**Original Source**

The theorem works over compact convex metrizable subsets of a locally convex topological vector space.

**Original LaTeX**

```latex
`K \subseteq E` is compact, convex, and metrizable.
```

$$
K \subseteq E
$$

**Lean**

```lean
structure ChoquetSet where
  carrier : Set E
  convex : Convex ℝ carrier
  compact : IsCompact carrier
  metrizable : TopologicalSpace.MetrizableSpace carrier

namespace ChoquetSet
```

<a id="mathformer-autoformalizedchoquettheory-choquetset-instmetrizablespacecarrier"></a>

## `Mathformer.AutoformalizedChoquetTheory.ChoquetSet.instMetrizableSpaceCarrier`

- Kind: `instance`
- Source line: [backends/lean/Mathformer/AutoformalizedChoquetTheory.lean:64](../../../../../backends/lean/Mathformer/AutoformalizedChoquetTheory.lean#L64)

**Generated Notes**

This exposes the metrizability field as an instance for the bundled carrier subtype.

**Generated LaTeX**

```latex
from the hypothesis that `K` is metrizable, the
space `K` carries a metrizable topology.
```

$$
K
$$

$$
K
$$

**Lean**

```lean
instance instMetrizableSpaceCarrier (C : ChoquetSet (E := E)) : TopologicalSpace.MetrizableSpace C.carrier :=
  C.metrizable
```

<a id="mathformer-autoformalizedchoquettheory-choquetset-extremepoints"></a>

## `Mathformer.AutoformalizedChoquetTheory.ChoquetSet.extremePoints`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedChoquetTheory.lean:72](../../../../../backends/lean/Mathformer/AutoformalizedChoquetTheory.lean#L72)

**Original Source**

Choquet representations are supported on the extreme points of the compact convex set.

**Original LaTeX**

```latex
`\operatorname{Ext}(K)`.
```

$$
\operatorname{Ext}(K)
$$

**Lean**

```lean
def extremePoints (C : ChoquetSet (E := E)) : Set E :=
  C.carrier.extremePoints ℝ
```

<a id="mathformer-autoformalizedchoquettheory-choquetset-extremepoints-subset"></a>

## `Mathformer.AutoformalizedChoquetTheory.ChoquetSet.extremePoints_subset`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedChoquetTheory.lean:79](../../../../../backends/lean/Mathformer/AutoformalizedChoquetTheory.lean#L79)

**Generated Notes**

Extreme points of the carrier are elements of the carrier.

**Generated LaTeX**

```latex
`\operatorname{Ext}(K) \subseteq K`.
```

$$
\operatorname{Ext}(K) \subseteq K
$$

**Lean**

```lean
theorem extremePoints_subset (C : ChoquetSet (E := E)) :
    C.extremePoints ⊆ C.carrier := by
  exact _root_.extremePoints_subset
```

<a id="mathformer-autoformalizedchoquettheory-choquetset-kreinmilman-closure-convexhull-extremepoints"></a>

## `Mathformer.AutoformalizedChoquetTheory.ChoquetSet.kreinMilman_closure_convexHull_extremePoints`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedChoquetTheory.lean:88](../../../../../backends/lean/Mathformer/AutoformalizedChoquetTheory.lean#L88)

**Generated LaTeX**

```latex
`\overline{\operatorname{conv}(\operatorname{Ext}(K))}=K`.
```

$$
\overline{\operatorname{conv}(\operatorname{Ext}(K))}=K
$$

**Comment**

Mathlib grounding (NL): Krein--Milman identifies the compact convex set with the closure of the convex hull of its extreme points.

**Lean**

```lean
theorem kreinMilman_closure_convexHull_extremePoints (C : ChoquetSet (E := E)) :
    closure (convexHull ℝ C.extremePoints) = C.carrier := by
  simpa [ChoquetSet.extremePoints] using
    (closure_convexHull_extremePoints (s := C.carrier) C.compact C.convex)
```

<a id="mathformer-autoformalizedchoquettheory-choquetset-mem-closure-convexhull-extremepoints"></a>

## `Mathformer.AutoformalizedChoquetTheory.ChoquetSet.mem_closure_convexHull_extremePoints`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedChoquetTheory.lean:99](../../../../../backends/lean/Mathformer/AutoformalizedChoquetTheory.lean#L99)

**Generated Notes**

Every point of the Choquet set lies in the closed convex hull of its extreme points by Krein--Milman.

**Generated LaTeX**

```latex
if `x \in K`, then
`x \in \overline{\operatorname{conv}(\operatorname{Ext}(K))}`.
```

$$
x \in K
$$

$$
x \in \overline{\operatorname{conv}(\operatorname{Ext}(K))}
$$

**Lean**

```lean
theorem mem_closure_convexHull_extremePoints (C : ChoquetSet (E := E)) {x : E}
    (hx : x ∈ C.carrier) :
    x ∈ closure (convexHull ℝ C.extremePoints) := by
  rw [C.kreinMilman_closure_convexHull_extremePoints]
  exact hx
```

<a id="mathformer-autoformalizedchoquettheory-choquetset-extremepoints-nonempty-of-nonempty"></a>

## `Mathformer.AutoformalizedChoquetTheory.ChoquetSet.extremePoints_nonempty_of_nonempty`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedChoquetTheory.lean:110](../../../../../backends/lean/Mathformer/AutoformalizedChoquetTheory.lean#L110)

**Generated Notes**

A nonempty compact convex Choquet set has at least one extreme point.

**Generated LaTeX**

```latex
`K \ne \varnothing \Rightarrow \operatorname{Ext}(K) \ne \varnothing`.
```

$$
K \ne \varnothing \Rightarrow \operatorname{Ext}(K) \ne \varnothing
$$

**Lean**

```lean
theorem extremePoints_nonempty_of_nonempty (C : ChoquetSet (E := E))
    (hC : C.carrier.Nonempty) :
    C.extremePoints.Nonempty := by
  exact by
    simpa [ChoquetSet.extremePoints] using
      C.compact.extremePoints_nonempty hC

section AffineImage
variable {F : Type uF}
variable [AddCommGroup F] [Module ℝ F] [TopologicalSpace F] [T1Space F]
```

<a id="mathformer-autoformalizedchoquettheory-choquetset-surjon-extremepoints-image"></a>

## `Mathformer.AutoformalizedChoquetTheory.ChoquetSet.surjOn_extremePoints_image`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedChoquetTheory.lean:127](../../../../../backends/lean/Mathformer/AutoformalizedChoquetTheory.lean#L127)

**Generated LaTeX**

```latex
`f(\operatorname{Ext}(K))` maps onto
`\operatorname{Ext}(f(K))`.
```

$$
f(\operatorname{Ext}(K))
$$

$$
\operatorname{Ext}(f(K))
$$

**Comment**

Mathlib grounding (NL): Continuous affine images send enough extreme points of the domain to cover the extreme points of the image.

**Lean**

```lean
theorem surjOn_extremePoints_image (C : ChoquetSet (E := E)) (f : E →ᴬ[ℝ] F) :
    SurjOn f C.extremePoints ((f '' C.carrier).extremePoints ℝ) := by
  simpa [ChoquetSet.extremePoints] using
    (_root_.surjOn_extremePoints_image (f := f) (s := C.carrier) C.compact)

end AffineImage

end ChoquetSet
```

<a id="mathformer-autoformalizedchoquettheory-supportedon"></a>

## `Mathformer.AutoformalizedChoquetTheory.SupportedOn`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedChoquetTheory.lean:142](../../../../../backends/lean/Mathformer/AutoformalizedChoquetTheory.lean#L142)

**Generated Notes**

Support-on is represented by requiring the complement to have measure zero.

**Generated LaTeX**

```latex
`\operatorname{supp}(\mu) \subseteq s`, encoded as
`\mu(s^c)=0`.
```

$$
\operatorname{supp}(\mu) \subseteq s
$$

$$
\mu(s^c)=0
$$

**Lean**

```lean
def SupportedOn (μ : ProbabilityMeasure E) (s : Set E) : Prop :=
  (μ : Measure E) sᶜ = 0
```

<a id="mathformer-autoformalizedchoquettheory-supportedon-mono"></a>

## `Mathformer.AutoformalizedChoquetTheory.supportedOn_mono`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedChoquetTheory.lean:151](../../../../../backends/lean/Mathformer/AutoformalizedChoquetTheory.lean#L151)

**Generated Notes**

If a probability measure is supported on a smaller set, it is also supported on any larger set.

**Generated LaTeX**

```latex
`s \subseteq t` and `\mu(s^c)=0` imply
`\mu(t^c)=0`.
```

$$
s \subseteq t
$$

$$
\mu(s^c)=0
$$

$$
\mu(t^c)=0
$$

**Lean**

```lean
theorem supportedOn_mono {μ : ProbabilityMeasure E} {s t : Set E}
    (hst : s ⊆ t)
    (hμ : SupportedOn μ s) :
    SupportedOn μ t := by
  exact measure_mono_null (compl_subset_compl.mpr hst) hμ
```

<a id="mathformer-autoformalizedchoquettheory-choquetrepresentation"></a>

## `Mathformer.AutoformalizedChoquetTheory.ChoquetRepresentation`

- Kind: `structure`
- Source line: [backends/lean/Mathformer/AutoformalizedChoquetTheory.lean:163](../../../../../backends/lean/Mathformer/AutoformalizedChoquetTheory.lean#L163)

**Original Source**

A Choquet representation of `x` is a probability measure supported on extreme points whose barycenter is `x`.

**Original LaTeX**

```latex
`\mu(\operatorname{Ext}(K)^c)=0` and
`f(x)=\int f(y)\,d\mu(y)` for continuous affine real-valued tests `f`.
```

$$
\mu(\operatorname{Ext}(K)^c)=0
$$

$$
f(x)=\int f(y)\,d\mu(y)
$$

$$
f
$$

**Lean**

```lean
structure ChoquetRepresentation (C : ChoquetSet (E := E)) (x : E) where
  mem_carrier : x ∈ C.carrier
  measure : ProbabilityMeasure E
  supportedOnExtremePoints : SupportedOn measure C.extremePoints
  barycenter_eq : ∀ f : E →ᴬ[ℝ] ℝ, f x = ∫ y, f y ∂((measure : Measure E))

namespace ChoquetRepresentation
variable {C : ChoquetSet (E := E)} {x : E}
```

<a id="mathformer-autoformalizedchoquettheory-choquetrepresentation-supportedoncarrier"></a>

## `Mathformer.AutoformalizedChoquetTheory.ChoquetRepresentation.supportedOnCarrier`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedChoquetTheory.lean:178](../../../../../backends/lean/Mathformer/AutoformalizedChoquetTheory.lean#L178)

**Generated Notes**

Support on extreme points implies support on the whole carrier because extreme points lie in the carrier.

**Generated LaTeX**

```latex
`\operatorname{Ext}(K) \subseteq K` gives
`\mu(K^c)=0`.
```

$$
\operatorname{Ext}(K) \subseteq K
$$

$$
\mu(K^c)=0
$$

**Lean**

```lean
theorem supportedOnCarrier (R : ChoquetRepresentation C x) :
    SupportedOn R.measure C.carrier := by
  exact supportedOn_mono C.extremePoints_subset R.supportedOnExtremePoints
```

<a id="mathformer-autoformalizedchoquettheory-choquetrepresentation-point-mem-carrier"></a>

## `Mathformer.AutoformalizedChoquetTheory.ChoquetRepresentation.point_mem_carrier`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedChoquetTheory.lean:187](../../../../../backends/lean/Mathformer/AutoformalizedChoquetTheory.lean#L187)

**Generated Notes**

A representation package includes the proof that the point being represented belongs to the Choquet set.

**Generated LaTeX**

```latex
from `R` we recover `x \in K`.
```

$$
R
$$

$$
x \in K
$$

**Lean**

```lean
theorem point_mem_carrier (R : ChoquetRepresentation C x) :
    x ∈ C.carrier := by
  exact R.mem_carrier
```

<a id="mathformer-autoformalizedchoquettheory-choquetrepresentation-barycenter-formula"></a>

## `Mathformer.AutoformalizedChoquetTheory.ChoquetRepresentation.barycenter_formula`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedChoquetTheory.lean:196](../../../../../backends/lean/Mathformer/AutoformalizedChoquetTheory.lean#L196)

**Original Source**

The barycenter condition says affine test functions agree at `x` with their integral against the representing measure.

**Original LaTeX**

```latex
`f(x)=\int f(y)\,d\mu(y)`.
```

$$
f(x)=\int f(y)\,d\mu(y)
$$

**Lean**

```lean
theorem barycenter_formula (R : ChoquetRepresentation C x) (f : E →ᴬ[ℝ] ℝ) :
    f x = ∫ y, f y ∂((R.measure : Measure E)) := by
  exact R.barycenter_eq f

end ChoquetRepresentation
```

<a id="mathformer-autoformalizedchoquettheory-choquettheoremhypothesis"></a>

## `Mathformer.AutoformalizedChoquetTheory.ChoquetTheoremHypothesis`

- Kind: `structure`
- Source line: [backends/lean/Mathformer/AutoformalizedChoquetTheory.lean:209](../../../../../backends/lean/Mathformer/AutoformalizedChoquetTheory.lean#L209)

**Generated Notes**

Since this mathlib environment lacks the full Choquet representation theorem, the theorem content is isolated as an explicit hypothesis package.

**Generated LaTeX**

```latex
`\forall x \in K, \exists \mu` representing `x`
and supported on `\operatorname{Ext}(K)`.
```

$$
\forall x \in K, \exists \mu
$$

$$
x
$$

$$
\operatorname{Ext}(K)
$$

**Lean**

```lean
structure ChoquetTheoremHypothesis (C : ChoquetSet (E := E)) : Prop where
  exists_representation : ∀ x : E, x ∈ C.carrier → ∃ R : ChoquetRepresentation C x, True
```

<a id="mathformer-autoformalizedchoquettheory-choquet-theorem"></a>

## `Mathformer.AutoformalizedChoquetTheory.choquet_theorem`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedChoquetTheory.lean:218](../../../../../backends/lean/Mathformer/AutoformalizedChoquetTheory.lean#L218)

**Original Source**

Every point of the compact convex metrizable set has a Choquet representing measure.

**Original LaTeX**

```latex
`\forall x \in K, \exists \mu,\ \mu` is supported on
`\operatorname{Ext}(K)` and represents `x`.
```

$$
\forall x \in K, \exists \mu,\ \mu
$$

$$
\operatorname{Ext}(K)
$$

$$
x
$$

**Lean**

```lean
theorem choquet_theorem {C : ChoquetSet (E := E)}
    (hC : ChoquetTheoremHypothesis C)
    {x : E}
    (hx : x ∈ C.carrier) :
    ∃ R : ChoquetRepresentation C x, True := by
  have representationExists := hC.exists_representation
  exact representationExists x hx
```

<a id="mathformer-autoformalizedchoquettheory-choquet-exists-representing-measure"></a>

## `Mathformer.AutoformalizedChoquetTheory.choquet_exists_representing_measure`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedChoquetTheory.lean:232](../../../../../backends/lean/Mathformer/AutoformalizedChoquetTheory.lean#L232)

**Original Source**

The representation can be unpacked as a supported probability measure together with the barycenter identity.

**Original LaTeX**

```latex
`\exists \mu,\ \mu(\operatorname{Ext}(K)^c)=0 \land
\forall f,\ f(x)=\int f(y)\,d\mu(y)`.
```

$$
\exists \mu,\ \mu(\operatorname{Ext}(K)^c)=0 \land \forall f,\ f(x)=\int f(y)\,d\mu(y)
$$

**Lean**

```lean
theorem choquet_exists_representing_measure {C : ChoquetSet (E := E)}
    (hC : ChoquetTheoremHypothesis C)
    {x : E}
    (hx : x ∈ C.carrier) :
    ∃ μ : ProbabilityMeasure E,
      SupportedOn μ C.extremePoints ∧
        ∀ f : E →ᴬ[ℝ] ℝ, f x = ∫ y, f y ∂((μ : Measure E)) := by
  rcases hC.exists_representation x hx with ⟨R, _⟩
  exact ⟨R.measure, R.supportedOnExtremePoints, R.barycenter_eq⟩
```

<a id="mathformer-autoformalizedchoquettheory-ischoquetsimplex"></a>

## `Mathformer.AutoformalizedChoquetTheory.IsChoquetSimplex`

- Kind: `def`
- Source line: [backends/lean/Mathformer/AutoformalizedChoquetTheory.lean:248](../../../../../backends/lean/Mathformer/AutoformalizedChoquetTheory.lean#L248)

**Original Source**

In a Choquet simplex, the representing probability measure is unique.

**Original LaTeX**

```latex
if `R` and `S` represent the same `x`, then
`\mu_R=\mu_S`.
```

$$
R
$$

$$
S
$$

$$
x
$$

**Lean**

```lean
def IsChoquetSimplex (C : ChoquetSet (E := E)) : Prop :=
  ∀ {x : E} (R S : ChoquetRepresentation C x), R.measure = S.measure
```

<a id="mathformer-autoformalizedchoquettheory-eq-measure-of-ischoquetsimplex"></a>

## `Mathformer.AutoformalizedChoquetTheory.eq_measure_of_isChoquetSimplex`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedChoquetTheory.lean:257](../../../../../backends/lean/Mathformer/AutoformalizedChoquetTheory.lean#L257)

**Generated Notes**

This simply applies the uniqueness predicate defining a Choquet simplex.

**Generated LaTeX**

```latex
`R,S` represent the same `x` implies
`\mu_R=\mu_S`.
```

$$
R,S
$$

$$
x
$$

$$
\mu_R=\mu_S
$$

**Lean**

```lean
theorem eq_measure_of_isChoquetSimplex {C : ChoquetSet (E := E)}
    (hSimplex : IsChoquetSimplex C)
    {x : E}
    (R S : ChoquetRepresentation C x) :
    R.measure = S.measure := by
  exact hSimplex R S
```

<a id="mathformer-autoformalizedchoquettheory-existsunique-representingmeasure-of-ischoquetsimplex"></a>

## `Mathformer.AutoformalizedChoquetTheory.existsUnique_representingMeasure_of_isChoquetSimplex`

- Kind: `theorem`
- Source line: [backends/lean/Mathformer/AutoformalizedChoquetTheory.lean:270](../../../../../backends/lean/Mathformer/AutoformalizedChoquetTheory.lean#L270)

**Original Source**

In the simplex case, each point has a unique representing probability measure supported on extreme points.

**Original LaTeX**

```latex
`\exists! \mu,\ \mu(\operatorname{Ext}(K)^c)=0 \land
\forall f,\ f(x)=\int f(y)\,d\mu(y)`.
```

$$
\exists! \mu,\ \mu(\operatorname{Ext}(K)^c)=0 \land \forall f,\ f(x)=\int f(y)\,d\mu(y)
$$

**Lean**

```lean
theorem existsUnique_representingMeasure_of_isChoquetSimplex {C : ChoquetSet (E := E)}
    (hC : ChoquetTheoremHypothesis C)
    (hSimplex : IsChoquetSimplex C)
    {x : E}
    (hx : x ∈ C.carrier) :
    ∃! μ : ProbabilityMeasure E,
      SupportedOn μ C.extremePoints ∧
        ∀ f : E →ᴬ[ℝ] ℝ, f x = ∫ y, f y ∂((μ : Measure E)) := by
  rcases hC.exists_representation x hx with ⟨R, _⟩
  refine ⟨R.measure, ⟨R.supportedOnExtremePoints, R.barycenter_eq⟩, ?_⟩
  intro μ hμ
  let S : ChoquetRepresentation C x :=
    { mem_carrier := hx, measure := μ, supportedOnExtremePoints := hμ.1, barycenter_eq := hμ.2 }
  exact hSimplex S R

end AutoformalizedChoquetTheory

end Mathformer
```
