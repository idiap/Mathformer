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

import Mathlib.Analysis.Convex.KreinMilman
import Mathlib.MeasureTheory.Measure.ProbabilityMeasure

set_option linter.unusedSectionVars false
set_option linter.unusedVariables false

/-!
Original source (NL): Choquet theory studies representations of points of compact
convex sets by probability measures supported on extreme points. The
Wikipedia-level Choquet theorem says that each point of a compact convex
metrizable set in a locally convex topological vector space has such a
representing measure.

Original source (LaTeX): for a compact convex metrizable set `K` and `x \in K`,
there is a probability measure `\mu` supported on `\operatorname{Ext}(K)` such
that, equivalently through continuous affine tests,
`f(x)=\int_{\operatorname{Ext}(K)} f(y)\,d\mu(y)`.

Mathlib grounding: local mathlib provides extreme points, continuous affine maps,
probability measures, and Krein--Milman, but not a named Choquet representation
result. This module formalizes the mathlib-native interface, the Krein--Milman
overlap, and consequences of an explicit Choquet representation hypothesis.
-/

noncomputable section
open Set MeasureTheory
open scoped Topology

namespace Mathformer

namespace AutoformalizedChoquetTheory

universe uE uF
variable {E : Type uE}
variable [AddCommGroup E] [Module ℝ E] [TopologicalSpace E] [MeasurableSpace E]
variable [T2Space E] [IsTopologicalAddGroup E] [ContinuousSMul ℝ E] [LocallyConvexSpace ℝ E]

/--
Original source (NL): The theorem works over compact convex metrizable subsets
of a locally convex topological vector space.
Original source (LaTeX): `K \subseteq E` is compact, convex, and metrizable.
-/
structure ChoquetSet where
  carrier : Set E
  convex : Convex ℝ carrier
  compact : IsCompact carrier
  metrizable : TopologicalSpace.MetrizableSpace carrier

namespace ChoquetSet

/--
Generated note (NL): This exposes the metrizability field as an instance for the
bundled carrier subtype.
Generated equivalent (LaTeX): from the hypothesis that `K` is metrizable, the
space `K` carries a metrizable topology.
-/
instance instMetrizableSpaceCarrier (C : ChoquetSet (E := E)) : TopologicalSpace.MetrizableSpace C.carrier :=
  C.metrizable

/--
Original source (NL): Choquet representations are supported on the extreme
points of the compact convex set.
Original source (LaTeX): `\operatorname{Ext}(K)`.
-/
def extremePoints (C : ChoquetSet (E := E)) : Set E :=
  C.carrier.extremePoints ℝ

/--
Generated note (NL): Extreme points of the carrier are elements of the carrier.
Generated equivalent (LaTeX): `\operatorname{Ext}(K) \subseteq K`.
-/
theorem extremePoints_subset (C : ChoquetSet (E := E)) :
    C.extremePoints ⊆ C.carrier := by
  exact _root_.extremePoints_subset

/--
Mathlib grounding (NL): Krein--Milman identifies the compact convex set with the
closure of the convex hull of its extreme points.
Generated equivalent (LaTeX): `\overline{\operatorname{conv}(\operatorname{Ext}(K))}=K`.
-/
theorem kreinMilman_closure_convexHull_extremePoints (C : ChoquetSet (E := E)) :
    closure (convexHull ℝ C.extremePoints) = C.carrier := by
  simpa [ChoquetSet.extremePoints] using
    (closure_convexHull_extremePoints (s := C.carrier) C.compact C.convex)

/--
Generated note (NL): Every point of the Choquet set lies in the closed convex
hull of its extreme points by Krein--Milman.
Generated equivalent (LaTeX): if `x \in K`, then
`x \in \overline{\operatorname{conv}(\operatorname{Ext}(K))}`.
-/
theorem mem_closure_convexHull_extremePoints (C : ChoquetSet (E := E)) {x : E}
    (hx : x ∈ C.carrier) :
    x ∈ closure (convexHull ℝ C.extremePoints) := by
  rw [C.kreinMilman_closure_convexHull_extremePoints]
  exact hx

/--
Generated note (NL): A nonempty compact convex Choquet set has at least one
extreme point.
Generated equivalent (LaTeX): `K \ne \varnothing \Rightarrow \operatorname{Ext}(K) \ne \varnothing`.
-/
theorem extremePoints_nonempty_of_nonempty (C : ChoquetSet (E := E))
    (hC : C.carrier.Nonempty) :
    C.extremePoints.Nonempty := by
  exact by
    simpa [ChoquetSet.extremePoints] using
      C.compact.extremePoints_nonempty hC

section AffineImage
variable {F : Type uF}
variable [AddCommGroup F] [Module ℝ F] [TopologicalSpace F] [T1Space F]

/--
Mathlib grounding (NL): Continuous affine images send enough extreme points of
the domain to cover the extreme points of the image.
Generated equivalent (LaTeX): `f(\operatorname{Ext}(K))` maps onto
`\operatorname{Ext}(f(K))`.
-/
theorem surjOn_extremePoints_image (C : ChoquetSet (E := E)) (f : E →ᴬ[ℝ] F) :
    SurjOn f C.extremePoints ((f '' C.carrier).extremePoints ℝ) := by
  simpa [ChoquetSet.extremePoints] using
    (_root_.surjOn_extremePoints_image (f := f) (s := C.carrier) C.compact)

end AffineImage

end ChoquetSet

/--
Generated note (NL): Support-on is represented by requiring the complement to
have measure zero.
Generated equivalent (LaTeX): `\operatorname{supp}(\mu) \subseteq s`, encoded as
`\mu(s^c)=0`.
-/
def SupportedOn (μ : ProbabilityMeasure E) (s : Set E) : Prop :=
  (μ : Measure E) sᶜ = 0

/--
Generated note (NL): If a probability measure is supported on a smaller set, it
is also supported on any larger set.
Generated equivalent (LaTeX): `s \subseteq t` and `\mu(s^c)=0` imply
`\mu(t^c)=0`.
-/
theorem supportedOn_mono {μ : ProbabilityMeasure E} {s t : Set E}
    (hst : s ⊆ t)
    (hμ : SupportedOn μ s) :
    SupportedOn μ t := by
  exact measure_mono_null (compl_subset_compl.mpr hst) hμ

/--
Original source (NL): A Choquet representation of `x` is a probability measure
supported on extreme points whose barycenter is `x`.
Original source (LaTeX): `\mu(\operatorname{Ext}(K)^c)=0` and
`f(x)=\int f(y)\,d\mu(y)` for continuous affine real-valued tests `f`.
-/
structure ChoquetRepresentation (C : ChoquetSet (E := E)) (x : E) where
  mem_carrier : x ∈ C.carrier
  measure : ProbabilityMeasure E
  supportedOnExtremePoints : SupportedOn measure C.extremePoints
  barycenter_eq : ∀ f : E →ᴬ[ℝ] ℝ, f x = ∫ y, f y ∂((measure : Measure E))

namespace ChoquetRepresentation
variable {C : ChoquetSet (E := E)} {x : E}

/--
Generated note (NL): Support on extreme points implies support on the whole
carrier because extreme points lie in the carrier.
Generated equivalent (LaTeX): `\operatorname{Ext}(K) \subseteq K` gives
`\mu(K^c)=0`.
-/
theorem supportedOnCarrier (R : ChoquetRepresentation C x) :
    SupportedOn R.measure C.carrier := by
  exact supportedOn_mono C.extremePoints_subset R.supportedOnExtremePoints

/--
Generated note (NL): A representation package includes the proof that the point
being represented belongs to the Choquet set.
Generated equivalent (LaTeX): from `R` we recover `x \in K`.
-/
theorem point_mem_carrier (R : ChoquetRepresentation C x) :
    x ∈ C.carrier := by
  exact R.mem_carrier

/--
Original source (NL): The barycenter condition says affine test functions agree
at `x` with their integral against the representing measure.
Original source (LaTeX): `f(x)=\int f(y)\,d\mu(y)`.
-/
theorem barycenter_formula (R : ChoquetRepresentation C x) (f : E →ᴬ[ℝ] ℝ) :
    f x = ∫ y, f y ∂((R.measure : Measure E)) := by
  exact R.barycenter_eq f

end ChoquetRepresentation

/--
Generated note (NL): Since this mathlib environment lacks the full Choquet
representation theorem, the theorem content is isolated as an explicit
hypothesis package.
Generated equivalent (LaTeX): `\forall x \in K, \exists \mu` representing `x`
and supported on `\operatorname{Ext}(K)`.
-/
structure ChoquetTheoremHypothesis (C : ChoquetSet (E := E)) : Prop where
  exists_representation : ∀ x : E, x ∈ C.carrier → ∃ R : ChoquetRepresentation C x, True

/--
Original source (NL): Every point of the compact convex metrizable set has a
Choquet representing measure.
Original source (LaTeX): `\forall x \in K, \exists \mu,\ \mu` is supported on
`\operatorname{Ext}(K)` and represents `x`.
-/
theorem choquet_theorem {C : ChoquetSet (E := E)}
    (hC : ChoquetTheoremHypothesis C)
    {x : E}
    (hx : x ∈ C.carrier) :
    ∃ R : ChoquetRepresentation C x, True := by
  have representationExists := hC.exists_representation
  exact representationExists x hx

/--
Original source (NL): The representation can be unpacked as a supported
probability measure together with the barycenter identity.
Original source (LaTeX): `\exists \mu,\ \mu(\operatorname{Ext}(K)^c)=0 \land
\forall f,\ f(x)=\int f(y)\,d\mu(y)`.
-/
theorem choquet_exists_representing_measure {C : ChoquetSet (E := E)}
    (hC : ChoquetTheoremHypothesis C)
    {x : E}
    (hx : x ∈ C.carrier) :
    ∃ μ : ProbabilityMeasure E,
      SupportedOn μ C.extremePoints ∧
        ∀ f : E →ᴬ[ℝ] ℝ, f x = ∫ y, f y ∂((μ : Measure E)) := by
  rcases hC.exists_representation x hx with ⟨R, _⟩
  exact ⟨R.measure, R.supportedOnExtremePoints, R.barycenter_eq⟩

/--
Original source (NL): In a Choquet simplex, the representing probability measure
is unique.
Original source (LaTeX): if `R` and `S` represent the same `x`, then
`\mu_R=\mu_S`.
-/
def IsChoquetSimplex (C : ChoquetSet (E := E)) : Prop :=
  ∀ {x : E} (R S : ChoquetRepresentation C x), R.measure = S.measure

/--
Generated note (NL): This simply applies the uniqueness predicate defining a
Choquet simplex.
Generated equivalent (LaTeX): `R,S` represent the same `x` implies
`\mu_R=\mu_S`.
-/
theorem eq_measure_of_isChoquetSimplex {C : ChoquetSet (E := E)}
    (hSimplex : IsChoquetSimplex C)
    {x : E}
    (R S : ChoquetRepresentation C x) :
    R.measure = S.measure := by
  exact hSimplex R S

/--
Original source (NL): In the simplex case, each point has a unique representing
probability measure supported on extreme points.
Original source (LaTeX): `\exists! \mu,\ \mu(\operatorname{Ext}(K)^c)=0 \land
\forall f,\ f(x)=\int f(y)\,d\mu(y)`.
-/
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
