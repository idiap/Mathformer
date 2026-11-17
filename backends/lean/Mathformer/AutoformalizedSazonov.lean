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

import Mathlib.Analysis.InnerProductSpace.l2Space
import Mathlib.MeasureTheory.Measure.ProbabilityMeasure
import Mathlib.Probability.Distributions.Gaussian.Basic

/-!
Original source (NL): Sazonov-type theorems characterize when a Gaussian
cylindrical measure on a Hilbert space extends to a Radon probability measure
after applying an operator. In the Hilbert-space formulation represented here,
the key equivalence is between gamma-radonifying behavior and the
Hilbert--Schmidt property.

Original source (LaTeX): for a bounded linear operator `T : G \to H` between real
Hilbert spaces, `T` is `\gamma`-radonifying iff `T` is Hilbert--Schmidt; a
basis-relative Hilbert--Schmidt criterion is
`\sum_i \|T e_i\|^2 < \infty`.

Generated note (NL): This file records the cylindrical Gaussian extension
component explicitly because that construction is not yet developed locally.

Generated notes:
- Cylindrical Gaussian extension is represented as an explicit model component.
- The scalar field is restricted to `ℝ`, matching standard Gaussian/radonifying formulations.
- `IsHilbertSchmidtWith` records square summability for a chosen Hilbert basis.
- Hilbert--Schmidt definitions/lemmas live in a complete-domain section (`[CompleteSpace G]`).
- The existential witness in `IsHilbertSchmidt` is fixed to index universe `uG` for stable
  universe inference.
- The Gaussian side reuses `ProbabilityTheory.IsGaussian` from mathlib.
- `GammaRadonifyingModel` keeps only the cylindrical-extension component as a model field.
- `IsGammaRadonifying` is kept minimal at the definition layer (`[MeasurableSpace H]` only);
  downstream lemma layers can add `OpensMeasurableSpace`/`BorelSpace` as needed.
- `SazonovAssumptions`/Sazonov theorems are stated in the Hilbert-space layer
  (`CompleteSpace G`, `CompleteSpace H`).
- `SazonovAssumptions` is an explicit structure of hypotheses (not a typeclass).
-/

namespace Mathformer
namespace AutoformalizedSazonov

open scoped BigOperators

universe uG uH

variable {G : Type uG} {H : Type uH}
variable [NormedAddCommGroup G] [InnerProductSpace ℝ G]
variable [NormedAddCommGroup H] [InnerProductSpace ℝ H]

section HilbertSchmidt

/--
Original source (NL): A Hilbert--Schmidt operator has square-summable images of
an orthonormal Hilbert basis.
Original source (LaTeX): for a Hilbert basis `(e_i)`, `\sum_i \|T e_i\|^2 < \infty`.
-/
def IsHilbertSchmidtWith {ι : Type*} (b : HilbertBasis ι ℝ G) (T : G →L[ℝ] H) : Prop :=
  Summable (fun i : ι => ‖T (b i)‖ ^ (2 : ℕ))

/--
Original source (NL): A bounded linear map is Hilbert--Schmidt when the
basis-relative square-summability criterion holds for some Hilbert basis.
Original source (LaTeX): `T` is Hilbert--Schmidt iff
`\exists (e_i),\ \sum_i \|T e_i\|^2 < \infty`.
-/
def IsHilbertSchmidt [CompleteSpace G] (T : G →L[ℝ] H) : Prop :=
  ∃ (ι : Type uG) (b : HilbertBasis ι ℝ G), IsHilbertSchmidtWith b T

/--
Generated note (NL): This records basis invariance of the basis-relative
Hilbert--Schmidt predicate as an explicit hypothesis.
Generated equivalent (LaTeX): for Hilbert bases `(e_i)` and `(f_j)`,
`\sum_i \|T e_i\|^2 < \infty \iff \sum_j \|T f_j\|^2 < \infty`.
-/
def IsHilbertSchmidtBasisIndependent [CompleteSpace G] : Prop :=
  ∀ {ι κ : Type uG}
    (b : HilbertBasis ι ℝ G)
    (c : HilbertBasis κ ℝ G)
    (T : G →L[ℝ] H),
    IsHilbertSchmidtWith b T ↔ IsHilbertSchmidtWith c T

/--
Generated note (NL): From existential Hilbert--Schmidt and basis independence,
the criterion holds for any chosen Hilbert basis.
Generated equivalent (LaTeX): if `\exists (f_j),\sum_j\|T f_j\|^2<\infty`,
then for every basis `(e_i)`, `\sum_i\|T e_i\|^2<\infty`.
Operational consequence of basis independence: from existential
Hilbert--Schmidt and one basis-independence hypothesis,
we can recover the basis-relative predicate on any chosen Hilbert basis.
-/
theorem isHilbertSchmidtWith_of_isHilbertSchmidt
    [CompleteSpace G]
    {ι : Type uG}
    (b : HilbertBasis ι ℝ G)
    (hBI : IsHilbertSchmidtBasisIndependent (G := G) (H := H))
    {T : G →L[ℝ] H}
    (hHS : IsHilbertSchmidt T) :
    IsHilbertSchmidtWith b T := by
  rcases hHS with ⟨κ, c, hc⟩
  exact (hBI c b T).1 hc

/--
Generated note (NL): Under basis independence, the existential and fixed-basis
Hilbert--Schmidt formulations are equivalent.
Generated equivalent (LaTeX): `T` is Hilbert--Schmidt iff
`\sum_i \|T e_i\|^2 < \infty` for the chosen basis `(e_i)`.
Under basis independence, existential Hilbert--Schmidt is equivalent to
the basis-relative predicate on any fixed Hilbert basis.
-/
theorem isHilbertSchmidt_iff_with
    [CompleteSpace G]
    {ι : Type uG}
    (b : HilbertBasis ι ℝ G)
    (hBI : IsHilbertSchmidtBasisIndependent (G := G) (H := H))
    (T : G →L[ℝ] H) :
    IsHilbertSchmidt T ↔ IsHilbertSchmidtWith b T := by
  constructor
  · intro hHS
    exact isHilbertSchmidtWith_of_isHilbertSchmidt (b := b) hBI hHS
  · intro hb
    exact ⟨ι, b, hb⟩

end HilbertSchmidt

section Gamma

variable [MeasurableSpace H]

/--
Generated note (NL): This structure isolates the cylindrical Gaussian extension
component that is not fully developed in the local mathlib environment.
Generated equivalent (LaTeX): it provides the relation saying the Gaussian
cylindrical pushforward along `T` extends to a probability measure `\nu` on `H`.
Model for the Gaussian/cylindrical side used in Sazonov-style statements.
Only the cylindrical-extension component is represented by a field here. Gaussianity is stated with
`ProbabilityTheory.IsGaussian` directly.
-/
structure GammaRadonifyingModel where
  /--
  Explicit model point of this file:
  witness that the pushforward of the canonical Gaussian cylindrical object along `T`
  extends to the probability measure `ν` on `H`.
  -/
  HasCanonicalGaussianCylinderExtension :
    (G →L[ℝ] H) → MeasureTheory.ProbabilityMeasure H → Prop

variable (M : GammaRadonifyingModel (G := G) (H := H))

/--
Original source (NL): A map is gamma-radonifying when the relevant Gaussian
cylindrical object extends to a Gaussian probability measure after applying the map.
Original source (LaTeX): `T` is `\gamma`-radonifying iff there exists a Gaussian
probability measure `\nu` on `H` extending the canonical Gaussian cylindrical
pushforward along `T`.
-/
def IsGammaRadonifying (T : G →L[ℝ] H) : Prop :=
  ∃ ν : MeasureTheory.ProbabilityMeasure H,
    ProbabilityTheory.IsGaussian (ν : MeasureTheory.Measure H) ∧
    M.HasCanonicalGaussianCylinderExtension T ν

/-!
`IsGammaRadonifying` uses only `[MeasurableSpace H]` at the definition layer.
When proving nontrivial Gaussian-map or characteristic-function lemmas downstream, it is expected
to strengthen assumptions (typically to `OpensMeasurableSpace` and/or `BorelSpace`).
-/

section Hilbert

/--
Generated note (NL): This assumption package records the pieces needed to state
the Sazonov equivalence without asserting unavailable analytic development as
global postulates.
Generated equivalent (LaTeX): it contains basis independence and both directions
`HilbertSchmidt(T) \Rightarrow \gamma\text{-radonifying}(T)` and
`\gamma\text{-radonifying}(T) \Rightarrow HilbertSchmidt(T)`.
-/
structure SazonovAssumptions [CompleteSpace G] [CompleteSpace H] : Prop where
  /-- Basis-independence interface for Hilbert--Schmidt summability. -/
  hilbertSchmidt_basisIndependent :
    IsHilbertSchmidtBasisIndependent (G := G) (H := H)
  hilbertSchmidt_to_gammaRadonifying :
    ∀ (T : G →L[ℝ] H), IsHilbertSchmidt T → IsGammaRadonifying M T
  gammaRadonifying_to_hilbertSchmidt :
    ∀ (T : G →L[ℝ] H), IsGammaRadonifying M T → IsHilbertSchmidt T

/--
Generated note (NL): Sazonov assumptions imply the fixed-basis and existential
Hilbert--Schmidt criteria agree.
Generated equivalent (LaTeX): under the assumptions,
`HilbertSchmidt(T) \iff \sum_i \|T e_i\|^2 < \infty`.
Under Sazonov assumptions, existential Hilbert--Schmidt is equivalent to
the basis-relative criterion on any fixed Hilbert basis.
-/
theorem isHilbertSchmidt_iff_with_of_sazonovAssumptions
    [CompleteSpace G] [CompleteSpace H]
    (hS : SazonovAssumptions (M := M))
    {ι : Type uG}
    (b : HilbertBasis ι ℝ G)
    (T : G →L[ℝ] H) :
    IsHilbertSchmidt T ↔ IsHilbertSchmidtWith b T := by
  exact isHilbertSchmidt_iff_with b hS.hilbertSchmidt_basisIndependent T

/--
Original source (NL): The Hilbert--Schmidt condition implies the
gamma-radonifying condition.
Original source (LaTeX): `T \in HS(G,H) \Rightarrow T` is `\gamma`-radonifying.
-/
theorem sazonov_hilbertSchmidt_to_gammaRadonifying
    [CompleteSpace G] [CompleteSpace H]
    (hS : SazonovAssumptions (M := M))
    (T : G →L[ℝ] H) :
    IsHilbertSchmidt T →
    IsGammaRadonifying M T := by
  intro hHS
  have gammaFromHilbert := hS.hilbertSchmidt_to_gammaRadonifying
  exact gammaFromHilbert T hHS

/--
Original source (NL): The gamma-radonifying condition implies the
Hilbert--Schmidt condition.
Original source (LaTeX): `T` is `\gamma`-radonifying `\Rightarrow T \in HS(G,H)`.
-/
theorem sazonov_gammaRadonifying_to_hilbertSchmidt
    [CompleteSpace G] [CompleteSpace H]
    (hS : SazonovAssumptions (M := M))
    (T : G →L[ℝ] H) :
    IsGammaRadonifying M T →
    IsHilbertSchmidt T := by
  intro hGamma
  have fromGamma := hS.gammaRadonifying_to_hilbertSchmidt
  exact fromGamma T hGamma

/--
Original source (NL): Sazonov's equivalence identifies gamma-radonifying
operators with Hilbert--Schmidt operators in this Hilbert-space interface.
Original source (LaTeX): `T` is `\gamma`-radonifying `\iff T \in HS(G,H)`.
-/
theorem sazonov_iff
    [CompleteSpace G] [CompleteSpace H]
    (hS : SazonovAssumptions (M := M))
    (T : G →L[ℝ] H) :
    IsGammaRadonifying M T ↔
    IsHilbertSchmidt T := by
  constructor
  · exact sazonov_gammaRadonifying_to_hilbertSchmidt (M := M) hS T
  · intro hHS
    exact sazonov_hilbertSchmidt_to_gammaRadonifying (M := M) hS T hHS

end Hilbert

end Gamma

end AutoformalizedSazonov
end Mathformer
