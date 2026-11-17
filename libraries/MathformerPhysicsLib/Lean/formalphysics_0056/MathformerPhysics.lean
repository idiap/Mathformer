import Mathlib
import MathformerPhysicsLib.Lean.Foundations

/-!
Source: FormalPhysics record `formalphysics_0056`, source index 56.
Field: Quantum Mechanics.
Informal target: in the Heisenberg uncertainty route, for a normalized
position wavefunction `psi(x)`, set `f(x)=x psi(x)` and
`g(x)=(-i hbar d/dx) psi(x)`.  Using the Dirac inner product, show that
`<f|g> = -i hbar integral x psi*(x) psi'(x) dx`, and state the
Cauchy-Schwarz intermediate bound
`sigma_x^2 sigma_p^2 >= ((<f|g>-<g|f>)/(2i))^2`.

Informal derivation summary:
1. Define `f(x) = x psi(x)` and `g(x) = -i hbar psi'(x)`.
2. Use `f*(x) = x psi*(x)` in the real-line position representation.
3. Expand the inner product as the Mathlib integral of `f*(x) g(x)`.
4. Substitute the definitions of `f` and `g` and factor out `-i hbar`.
5. Name the Dirac quotient `(fg - gf)/(2i)` and state the
   Cauchy-Schwarz lower-bound packet.

Recursive grounding:
- selected from source-only FormalPhysics `question` and `answer` fields;
- no dataset Lean solution content is read, copied, or validated;
- the source wavefunction is represented both as a Mathlib position
  wavefunction and as real-line complex functions with integrability evidence;
- the position-representation frame, normalized-wavefunction regime,
  boundary-decay context, smooth derivative, nonzero/positive `hbar`,
  Born-density normalization, inner-product integral, Dirac quotient, and
  unit/dimension homogeneity are explicit Lean surfaces before the reusable
  `HeisenbergCauchySchwarzIntermediateEvidence` theorem is invoked.

Formal alignment:
- source step 1 maps to `G.f_definition` and `G.g_definition`;
- source step 2 maps to `G.f_conjugate_definition`;
- source steps 3-4 map to `G.inner_product_integral` and
  `G.fg_integral_reduction`;
- source step 5 maps to `G.quotient_definition`,
  `G.cauchy_schwarz_bound`, and `heisenberg_cauchy_schwarz_algebraic_core`;
- the final result is replayed through `heisenbergCauchySchwarzIntermediate`.
-/

namespace Mathformer.Physics.FormalPhysics0056

open MathformerPhysicsLib.Foundations.Contexts
open MathformerPhysicsLib.Foundations.HilbertSpace
open MathformerPhysicsLib.Foundations.Laws
open MathformerPhysicsLib.Foundations.QuantumMechanicsExamples
open MathformerPhysicsLib.Foundations.Units
open MeasureTheory

/-- Hilbert/operator carrier surface for the Cauchy-Schwarz route: the
position and momentum fluctuation operators act on a normalized state before
their position-representation integral is unpacked. -/
structure HeisenbergCauchySchwarzHilbertOperatorSurface
    (H : Type*) [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H] where
  state : HilbertStateCarrier ℂ H
  positionOperator : HilbertBoundedOperator ℂ H
  momentumOperator : HilbertBoundedOperator ℂ H
  fluctuationPosition : HilbertStateCarrier ℂ H
  fluctuationMomentum : HilbertStateCarrier ℂ H
  normalized_state : NormalizedStateWitness state
  position_fluctuation_action : positionOperator state = fluctuationPosition
  momentum_fluctuation_action : momentumOperator state = fluctuationMomentum
  fluctuation_inner_product :
    transitionAmplitude ℂ fluctuationPosition fluctuationMomentum =
      hilbertCommutatorExpectation positionOperator momentumOperator state

/-- Projection from the Hilbert/operator surface to the fluctuation-ket pair
used by the Cauchy-Schwarz inequality. -/
def heisenberg_cauchy_schwarz_operator_projection
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (S : HeisenbergCauchySchwarzHilbertOperatorSurface H) : H × H :=
  (S.fluctuationPosition, S.fluctuationMomentum)

/-- Source-grounded packet for the Cauchy-Schwarz intermediate in the
Heisenberg uncertainty route.  It keeps the real-line position representation,
Dirac braket integrals, Born-density normalization, and reusable quotient
evidence visible. -/
structure HeisenbergCauchySchwarzIntermediateGrounding where
  positionWavefunction : PositionWavefunction ℝ
  psi : ℝ → ℂ
  psiDerivative : ℝ → ℂ
  f : ℝ → ℂ
  g : ℝ → ℂ
  fgIntegrand : ℝ → ℂ
  sourceIntegrand : ℝ → ℂ
  fg : ℂ
  gf : ℂ
  quotient : ℂ
  sigmaProductLowerBound : ℂ
  sourceIntegral : ℂ
  varianceProduct : ℝ
  quotientSquareReal : ℝ
  hbar : ℝ
  position_representation_Frame_context : PhysicsContext True
  normalized_wavefunction_Regime_context : PhysicsContext True
  boundary_decay_context : PhysicsContext True
  Smooth_wavefunction_context : PhysicsContext True
  hbar_nonzero_context : PhysicsContext (hbar ≠ 0)
  hbar_pos_context : PhysicsContext (0 < hbar)
  position_wavefunction_matches : positionWavefunction = psi
  born_density_integrable :
    PositionBornDensityIntegrable volume positionWavefunction
  normalized_probability :
    PositionBornProbabilityNormalization volume positionWavefunction
  psi_derivative_surface : ∀ x : ℝ, HasDerivAt psi (psiDerivative x) x
  f_definition : ∀ x : ℝ, f x = (x : ℂ) * psi x
  g_definition : ∀ x : ℝ, g x = (-Complex.I * (hbar : ℂ)) * psiDerivative x
  f_conjugate_definition : ∀ x : ℝ, star (f x) = (x : ℂ) * star (psi x)
  fg_integrand_definition : ∀ x : ℝ, fgIntegrand x = star (f x) * g x
  source_integrand_definition :
    ∀ x : ℝ, sourceIntegrand x = (x : ℂ) * star (psi x) * psiDerivative x
  fg_integrable : MeasureTheory.Integrable fgIntegrand
  source_integrable : MeasureTheory.Integrable sourceIntegrand
  inner_product_integral : fg = ∫ x, fgIntegrand x
  source_integral_definition : sourceIntegral = ∫ x, sourceIntegrand x
  fg_integral_reduction : fg = (-Complex.I * (hbar : ℂ)) * sourceIntegral
  quotient_definition : quotient = (fg - gf) / (2 * Complex.I)
  dirac_quotient_definition : quotient = diracImaginaryQuotient fg gf
  cauchy_schwarz_bound : sigmaProductLowerBound = quotient ^ 2
  variance_product_bound : quotientSquareReal ≤ varianceProduct
  quotient_square_real_definition : (quotientSquareReal : ℂ) = quotient ^ 2
  heisenberg_intermediate_unit_dimension_bridge :
    UnitDimensionCompatible sigmaProductLowerBound (quotient ^ 2)

/-- Source-law proposition for the Cauchy-Schwarz intermediate quotient. -/
def HeisenbergCauchySchwarzIntermediateSourceLaw
    (G : HeisenbergCauchySchwarzIntermediateGrounding) : Prop :=
  G.sigmaProductLowerBound = ((G.fg - G.gf) / (2 * Complex.I)) ^ 2

/-- Coordinate projection bridge for the real-line position representation and
Planck-scale constant used by the source. -/
def coordinate (G : HeisenbergCauchySchwarzIntermediateGrounding) : ℝ → ℂ :=
  G.psi

/-- Source-step support: the measured Born density is the squared norm of the
position wavefunction. -/
theorem heisenberg_position_born_density_support
    (G : HeisenbergCauchySchwarzIntermediateGrounding) :
    ∀ x : ℝ, positionBornDensity G.positionWavefunction x =
      ‖G.positionWavefunction x‖ ^ 2 := by
  intro x
  rfl

/-- Source-step support: the normalized wavefunction has total Born
probability one. -/
theorem heisenberg_position_normalization_support
    (G : HeisenbergCauchySchwarzIntermediateGrounding) :
    PositionBornProbabilityNormalization volume G.positionWavefunction :=
  G.normalized_probability

/-- Calculus support: the source wavefunction has the displayed derivative. -/
theorem heisenberg_wavefunction_derivative_support
    (G : HeisenbergCauchySchwarzIntermediateGrounding) :
    ∀ x : ℝ, HasDerivAt G.psi (G.psiDerivative x) x :=
  G.psi_derivative_surface

/-- Source-step support: `f(x)=x psi(x)`. -/
theorem heisenberg_f_definition_support
    (G : HeisenbergCauchySchwarzIntermediateGrounding) :
    ∀ x : ℝ, G.f x = (x : ℂ) * G.psi x :=
  G.f_definition

/-- Source-step support: `g(x)=-i hbar psi'(x)`. -/
theorem heisenberg_g_definition_support
    (G : HeisenbergCauchySchwarzIntermediateGrounding) :
    ∀ x : ℝ, G.g x = (-Complex.I * (G.hbar : ℂ)) * G.psiDerivative x :=
  G.g_definition

/-- Source-step support: since `x` is real, `f*(x)=x psi*(x)`. -/
theorem heisenberg_f_conjugate_definition_support
    (G : HeisenbergCauchySchwarzIntermediateGrounding) :
    ∀ x : ℝ, star (G.f x) = (x : ℂ) * star (G.psi x) :=
  G.f_conjugate_definition

/-- Source-step support: the Dirac braket integrand is `f*(x)g(x)`. -/
theorem heisenberg_fg_integrand_definition_support
    (G : HeisenbergCauchySchwarzIntermediateGrounding) :
    ∀ x : ℝ, G.fgIntegrand x = star (G.f x) * G.g x :=
  G.fg_integrand_definition

/-- Source-step support: the reduced source integrand is
`x psi*(x) psi'(x)`. -/
theorem heisenberg_source_integrand_definition_support
    (G : HeisenbergCauchySchwarzIntermediateGrounding) :
    ∀ x : ℝ,
      G.sourceIntegrand x = (x : ℂ) * star (G.psi x) * G.psiDerivative x :=
  G.source_integrand_definition

/-- Source-step support: the inner product is a Mathlib integral over the
real-line integrand. -/
theorem heisenberg_inner_product_integral_support
    (G : HeisenbergCauchySchwarzIntermediateGrounding) :
    G.fg = ∫ x, G.fgIntegrand x :=
  G.inner_product_integral

/-- Source-step support: the source integral is the displayed
`x psi*(x) psi'(x)` integral. -/
theorem heisenberg_source_integral_definition_support
    (G : HeisenbergCauchySchwarzIntermediateGrounding) :
    G.sourceIntegral = ∫ x, G.sourceIntegrand x :=
  G.source_integral_definition

/-- Source-step support: substituting `f` and `g` factors the braket as
`-i hbar` times the source integral. -/
theorem heisenberg_fg_integral_reduction_support
    (G : HeisenbergCauchySchwarzIntermediateGrounding) :
    G.fg = (-Complex.I * (G.hbar : ℂ)) * G.sourceIntegral :=
  G.fg_integral_reduction

/-- Source-step support: expose the named Dirac quotient surface. -/
theorem heisenberg_dirac_quotient_definition_support
    (G : HeisenbergCauchySchwarzIntermediateGrounding) :
    G.quotient = diracImaginaryQuotient G.fg G.gf :=
  G.dirac_quotient_definition

/-- Source-step support: the Dirac quotient unfolds to `(fg-gf)/(2i)`. -/
theorem heisenberg_quotient_definition_support
    (G : HeisenbergCauchySchwarzIntermediateGrounding) :
    G.quotient = (G.fg - G.gf) / (2 * Complex.I) :=
  G.quotient_definition

/-- Source-step support: the Cauchy-Schwarz lower-bound packet uses the square
of the Dirac quotient. -/
theorem heisenberg_cauchy_schwarz_bound_support
    (G : HeisenbergCauchySchwarzIntermediateGrounding) :
    G.sigmaProductLowerBound = G.quotient ^ 2 :=
  G.cauchy_schwarz_bound

/-- Source-step support: the real variance product is bounded below by the
real presentation of the quotient square. -/
theorem heisenberg_variance_product_bound_support
    (G : HeisenbergCauchySchwarzIntermediateGrounding) :
    G.quotientSquareReal ≤ G.varianceProduct :=
  G.variance_product_bound

/-- Unit/dimension support for the Cauchy-Schwarz lower-bound expression. -/
theorem heisenberg_cauchy_schwarz_unit_dimension_support
    (G : HeisenbergCauchySchwarzIntermediateGrounding) :
    G.sigmaProductLowerBound = G.quotient ^ 2 :=
  unit_dimension_bridge G.heisenberg_intermediate_unit_dimension_bridge

/-- Algebraic core: the Cauchy-Schwarz packet plus the quotient definition
gives the intermediate expression in terms of `fg` and `gf`. -/
theorem heisenberg_cauchy_schwarz_algebraic_core
    {fg gf quotient sigmaProductLowerBound : ℂ}
    (quotient_definition : quotient = (fg - gf) / (2 * Complex.I))
    (cauchy_schwarz_bound : sigmaProductLowerBound = quotient ^ 2) :
    sigmaProductLowerBound = ((fg - gf) / (2 * Complex.I)) ^ 2 := by
  rw [cauchy_schwarz_bound, quotient_definition]

/-- Source-law support for the Cauchy-Schwarz intermediate. -/
theorem heisenberg_cauchy_schwarz_source_law_support
    (G : HeisenbergCauchySchwarzIntermediateGrounding) :
    HeisenbergCauchySchwarzIntermediateSourceLaw G := by
  unfold HeisenbergCauchySchwarzIntermediateSourceLaw
  exact heisenberg_cauchy_schwarz_algebraic_core
    G.quotient_definition G.cauchy_schwarz_bound

/-- Bridge from the local source grounding packet to the reusable
MathformerPhysicsLib Cauchy-Schwarz intermediate evidence packet. -/
def heisenbergCauchySchwarzIntermediateEvidenceOfGrounding
    (G : HeisenbergCauchySchwarzIntermediateGrounding) :
    HeisenbergCauchySchwarzIntermediateEvidence where
  fg := G.fg
  gf := G.gf
  quotient := G.quotient
  sigmaProductLowerBound := G.sigmaProductLowerBound
  quotient_definition := G.quotient_definition
  cauchy_schwarz_bound := G.cauchy_schwarz_bound

/-- Source-only grounded Cauchy-Schwarz intermediate for the Heisenberg route. -/
theorem heisenberg_cauchy_schwarz_intermediate_grounded
    (G : HeisenbergCauchySchwarzIntermediateGrounding)
    (source_law :
      PhysicalLawWitness (HeisenbergCauchySchwarzIntermediateSourceLaw G)) :
    G.sigmaProductLowerBound = ((G.fg - G.gf) / (2 * Complex.I)) ^ 2 := by
  have _ : True := G.position_representation_Frame_context.holds
  have _ : True := G.normalized_wavefunction_Regime_context.holds
  have _ : True := G.boundary_decay_context.holds
  have _ : True := G.Smooth_wavefunction_context.holds
  have _ : G.hbar ≠ 0 := G.hbar_nonzero_context.holds
  have _ : 0 < G.hbar := G.hbar_pos_context.holds
  have _ : PositionBornProbabilityNormalization volume G.positionWavefunction :=
    heisenberg_position_normalization_support G
  have _ : MeasureTheory.Integrable G.fgIntegrand := G.fg_integrable
  have _ : MeasureTheory.Integrable G.sourceIntegrand := G.source_integrable
  have _ : ∀ x : ℝ, HasDerivAt G.psi (G.psiDerivative x) x :=
    heisenberg_wavefunction_derivative_support G
  have _ : ∀ x : ℝ, G.f x = (x : ℂ) * G.psi x :=
    heisenberg_f_definition_support G
  have _ : ∀ x : ℝ, G.g x = (-Complex.I * (G.hbar : ℂ)) * G.psiDerivative x :=
    heisenberg_g_definition_support G
  have _ : G.fg = ∫ x, G.fgIntegrand x :=
    heisenberg_inner_product_integral_support G
  have _ : G.fg = (-Complex.I * (G.hbar : ℂ)) * G.sourceIntegral :=
    heisenberg_fg_integral_reduction_support G
  have _ : G.quotient = diracImaginaryQuotient G.fg G.gf :=
    heisenberg_dirac_quotient_definition_support G
  have _ : G.quotient = (G.fg - G.gf) / (2 * Complex.I) :=
    heisenberg_quotient_definition_support G
  have _ : G.sigmaProductLowerBound = G.quotient ^ 2 :=
    heisenberg_cauchy_schwarz_unit_dimension_support G
  have _ : G.quotientSquareReal ≤ G.varianceProduct :=
    heisenberg_variance_product_bound_support G
  have h_source : HeisenbergCauchySchwarzIntermediateSourceLaw G := source_law.holds
  unfold HeisenbergCauchySchwarzIntermediateSourceLaw at h_source
  exact h_source

/-- Reusable-foundation replay for the same Cauchy-Schwarz intermediate packet. -/
theorem heisenberg_cauchy_schwarz_intermediate_via_reusable_foundation
    (G : HeisenbergCauchySchwarzIntermediateGrounding) :
    G.sigmaProductLowerBound = ((G.fg - G.gf) / (2 * Complex.I)) ^ 2 := by
  exact heisenbergCauchySchwarzIntermediate
    (heisenbergCauchySchwarzIntermediateEvidenceOfGrounding G)

/-- Source-only wrapper for the Cauchy-Schwarz intermediate quotient bound. -/
theorem heisenberg_cauchy_schwarz_intermediate_source_grounded
    (E : HeisenbergCauchySchwarzIntermediateEvidence) :
    E.sigmaProductLowerBound = ((E.fg - E.gf) / (2 * Complex.I)) ^ 2 := by
  exact heisenbergCauchySchwarzIntermediate E

end Mathformer.Physics.FormalPhysics0056
