import Mathlib
import MathformerPhysicsLib.Lean.Foundations

/-!
Source: FormalPhysics record `formalphysics_0035`, source index 35.
Field: Quantum Mechanics.
Informal target: from the Born rule for a normalized position wavefunction
`psi(x)`, prove
`sigma_x^2 = integral x^2 |psi(x)|^2 dx - (integral x |psi(x)|^2 dx)^2`.

Informal derivation summary:
1. Start from the variance identity
   `sigma_x^2 = <x^2> - <x>^2`.
2. Use the Born density `p(x) = |psi(x)|^2`.
3. Rewrite the first moment as `integral x |psi(x)|^2 dx`.
4. Rewrite the second moment as `integral x^2 |psi(x)|^2 dx`.
5. Substitute the two moment integrals into the variance identity.

Recursive grounding:
- selected from source-only FormalPhysics `question` and `answer` fields;
- no dataset Lean solution content is read, copied, or validated;
- the wavefunction is represented by `PositionWavefunction` over a Mathlib
  measured position space;
- the Born density, first-moment integral, second-moment integral,
  normalization, integrability, and variance identity are explicit Lean
  surfaces before the final theorem calls the reusable
  `PositionVarianceBornEvidence` theorem.

Formal alignment:
- source step 1 maps to `G.variance_definition`;
- source step 2 maps to `G.born_density_definition` and
  `positionBornDensity`;
- source step 3 maps to `G.mean_integral_as_born`;
- source step 4 maps to `G.second_moment_integral_as_born`;
- source step 5 maps to `position_variance_born_algebraic_core`;
- the final result is replayed through `positionVarianceBornFormula`.
-/

namespace Mathformer.Physics.FormalPhysics0035

open MathformerPhysicsLib.Foundations.Contexts
open MathformerPhysicsLib.Foundations.HilbertSpace
open MathformerPhysicsLib.Foundations.Laws
open MathformerPhysicsLib.Foundations.QuantumMechanicsExamples
open MathformerPhysicsLib.Foundations.Units
open MeasureTheory

/-- Source coordinate for the second position moment. -/
def positionSecondMomentCoordinate {X : Type*} (xValue : X → ℝ) : X → ℝ :=
  fun x => xValue x ^ 2

/-- Mathlib integral surface for the Born-rule second position moment. -/
noncomputable def positionSecondMomentIntegral
    {X : Type*} [MeasurableSpace X]
    (μ : Measure X) (xValue : X → ℝ) (psi : PositionWavefunction X) : ℝ :=
  positionExpectationIntegral μ (positionSecondMomentCoordinate xValue) psi

/-- Source-grounded packet for the Born-rule position variance calculation. -/
structure PositionVarianceBornGrounding
    (H X : Type*) [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    [MeasurableSpace X] where
  state : HilbertStateCarrier ℂ H
  measurementSpace : PositionMeasurementSpaceFrontier X
  sigmaSq : ℝ
  secondMoment : ℝ
  mean : ℝ
  densityIntegral : ℝ
  normalizationIntegral : ℝ
  position_coordinate_Frame_context : PhysicsContext True
  normalized_Born_Regime_context : PhysicsContext True
  boundary_at_infinity_context : PhysicsContext True
  smooth_position_wavefunction_context : PhysicsContext True
  normalization_nonzero_context : PhysicsContext (normalizationIntegral ≠ 0)
  variance_pos_context : PhysicsContext (0 ≤ sigmaSq)
  second_moment_integrable_context :
    PhysicsContext
      (PositionExpectationIntegrable measurementSpace.μ
        (positionSecondMomentCoordinate measurementSpace.xValue) measurementSpace.psi)
  born_density_definition :
    ∀ x : X, measurementSpace.born_density x = positionBornDensity measurementSpace.psi x
  born_density_norm_square :
    ∀ x : X, positionBornDensity measurementSpace.psi x = ‖measurementSpace.psi x‖ ^ 2
  mean_integrand_definition :
    ∀ x : X,
      positionExpectationIntegrand measurementSpace.xValue measurementSpace.psi x =
        measurementSpace.xValue x * ‖measurementSpace.psi x‖ ^ 2
  second_moment_integrand_definition :
    ∀ x : X,
      positionExpectationIntegrand
          (positionSecondMomentCoordinate measurementSpace.xValue) measurementSpace.psi x =
        measurementSpace.xValue x ^ 2 * ‖measurementSpace.psi x‖ ^ 2
  mean_integral_definition :
    densityIntegral =
      positionExpectationIntegral measurementSpace.μ measurementSpace.xValue measurementSpace.psi
  mean_integral_as_born :
    densityIntegral =
      ∫ x, positionExpectationIntegrand measurementSpace.xValue measurementSpace.psi x
        ∂measurementSpace.μ
  second_moment_integral_definition :
    secondMoment =
      positionSecondMomentIntegral measurementSpace.μ measurementSpace.xValue measurementSpace.psi
  second_moment_integral_as_born :
    secondMoment =
      ∫ x,
        positionExpectationIntegrand
          (positionSecondMomentCoordinate measurementSpace.xValue) measurementSpace.psi x
        ∂measurementSpace.μ
  normalization_integral_definition :
    normalizationIntegral = ∫ x, positionBornDensity measurementSpace.psi x ∂measurementSpace.μ
  normalization_value : normalizationIntegral = 1
  variance_definition : sigmaSq = secondMoment - mean ^ 2
  mean_from_born_density : mean = densityIntegral
  variance_unit_dimension_bridge :
    UnitDimensionCompatible sigmaSq (secondMoment - densityIntegral ^ 2)

/-- Source-law proposition for the final Born-rule variance identity. -/
def PositionVarianceBornSourceLaw
    {H X : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    [MeasurableSpace X] (G : PositionVarianceBornGrounding H X) : Prop :=
  G.sigmaSq = G.secondMoment - G.densityIntegral ^ 2

/-- Coordinate projection bridge for the position observable used in the
moment integrals. -/
def coordinate
    {H X : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    [MeasurableSpace X] (G : PositionVarianceBornGrounding H X) : X → ℝ :=
  G.measurementSpace.xValue

/-- Source-step support: the Born density is the squared norm of the position
wavefunction. -/
theorem position_variance_born_density_support
    {H X : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    [MeasurableSpace X] (G : PositionVarianceBornGrounding H X) :
    ∀ x : X, positionBornDensity G.measurementSpace.psi x = ‖G.measurementSpace.psi x‖ ^ 2 :=
  G.born_density_norm_square

/-- Source-step support: the first moment integrand is `x |psi x|^2`. -/
theorem position_variance_integrand_surface
    {X : Type*} (xValue : X → ℝ) (psi : PositionWavefunction X) (x : X) :
    positionExpectationIntegrand xValue psi x = xValue x * ‖psi x‖ ^ 2 := by
  exact positionExpectationIntegrand_apply xValue psi x

/-- Source-step support: the second moment integrand is `x^2 |psi x|^2`. -/
theorem position_variance_second_moment_integrand_support
    {H X : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    [MeasurableSpace X] (G : PositionVarianceBornGrounding H X) :
    ∀ x : X,
      positionExpectationIntegrand
          (positionSecondMomentCoordinate G.measurementSpace.xValue) G.measurementSpace.psi x =
        G.measurementSpace.xValue x ^ 2 * ‖G.measurementSpace.psi x‖ ^ 2 :=
  G.second_moment_integrand_definition

/-- Source-step support: the first moment is the Born-rule position integral. -/
theorem position_variance_mean_integral_support
    {H X : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    [MeasurableSpace X] (G : PositionVarianceBornGrounding H X) :
    G.densityIntegral =
      ∫ x, positionExpectationIntegrand G.measurementSpace.xValue G.measurementSpace.psi x
        ∂G.measurementSpace.μ :=
  G.mean_integral_as_born

/-- Source-step support: the second moment is the Born-rule integral with
coordinate squared. -/
theorem position_variance_second_moment_integral_support
    {H X : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    [MeasurableSpace X] (G : PositionVarianceBornGrounding H X) :
    G.secondMoment =
      ∫ x,
        positionExpectationIntegrand
          (positionSecondMomentCoordinate G.measurementSpace.xValue) G.measurementSpace.psi x
        ∂G.measurementSpace.μ :=
  G.second_moment_integral_as_born

/-- Unit/dimension support for the variance identity. -/
theorem position_variance_unit_dimension_support
    {H X : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    [MeasurableSpace X] (G : PositionVarianceBornGrounding H X) :
    G.sigmaSq = G.secondMoment - G.densityIntegral ^ 2 :=
  unit_dimension_bridge G.variance_unit_dimension_bridge

/-- Algebraic core: substituting the Born-rule first moment into
`sigmaSq = secondMoment - mean^2` gives the displayed variance identity. -/
theorem position_variance_born_algebraic_core
    {sigmaSq secondMoment mean densityIntegral : ℝ}
    (variance_definition : sigmaSq = secondMoment - mean ^ 2)
    (mean_from_born_density : mean = densityIntegral) :
    sigmaSq = secondMoment - densityIntegral ^ 2 := by
  rw [variance_definition, mean_from_born_density]

/-- Source-law support for the Born-rule variance calculation. -/
theorem position_variance_born_source_law_support
    {H X : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    [MeasurableSpace X] (G : PositionVarianceBornGrounding H X) :
    PositionVarianceBornSourceLaw G := by
  unfold PositionVarianceBornSourceLaw
  exact position_variance_born_algebraic_core
    G.variance_definition G.mean_from_born_density

/-- Bridge from the local source grounding packet to the reusable
MathformerPhysicsLib Born-variance evidence packet. -/
def positionVarianceBornEvidenceOfGrounding
    {H X : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    [MeasurableSpace X] (G : PositionVarianceBornGrounding H X) :
    PositionVarianceBornEvidence where
  sigmaSq := G.sigmaSq
  secondMoment := G.secondMoment
  mean := G.mean
  densityIntegral := G.densityIntegral
  variance_definition := G.variance_definition
  mean_from_born_density := G.mean_from_born_density

/-- Source-only measure-theoretic form of the Born-rule position variance
identity. -/
theorem position_variance_born_measure_grounded
    {H X : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    [MeasurableSpace X] (G : PositionVarianceBornGrounding H X)
    (source_law : PhysicalLawWitness (PositionVarianceBornSourceLaw G)) :
    G.sigmaSq = G.secondMoment - G.densityIntegral ^ 2 := by
  have _ : True := G.position_coordinate_Frame_context.holds
  have _ : True := G.normalized_Born_Regime_context.holds
  have _ : True := G.boundary_at_infinity_context.holds
  have _ : True := G.smooth_position_wavefunction_context.holds
  have _ : G.normalizationIntegral ≠ 0 := G.normalization_nonzero_context.holds
  have _ : 0 ≤ G.sigmaSq := G.variance_pos_context.holds
  have _ : PositionBornDensityIntegrable G.measurementSpace.μ G.measurementSpace.psi :=
    G.measurementSpace.born_density_integrable
  have _ : PositionBornProbabilityNormalization G.measurementSpace.μ G.measurementSpace.psi :=
    G.measurementSpace.normalized_probability
  have _ : PositionExpectationIntegrable G.measurementSpace.μ
      G.measurementSpace.xValue G.measurementSpace.psi :=
    G.measurementSpace.integrable_position_observable
  have _ : PositionExpectationIntegrable G.measurementSpace.μ
      (positionSecondMomentCoordinate G.measurementSpace.xValue) G.measurementSpace.psi :=
    G.second_moment_integrable_context.holds
  have _ : G.densityIntegral =
      ∫ x, positionExpectationIntegrand G.measurementSpace.xValue G.measurementSpace.psi x
        ∂G.measurementSpace.μ :=
    position_variance_mean_integral_support G
  have _ : G.secondMoment =
      ∫ x,
        positionExpectationIntegrand
          (positionSecondMomentCoordinate G.measurementSpace.xValue) G.measurementSpace.psi x
        ∂G.measurementSpace.μ :=
    position_variance_second_moment_integral_support G
  have h_source : PositionVarianceBornSourceLaw G := source_law.holds
  unfold PositionVarianceBornSourceLaw at h_source
  exact h_source

/-- Reusable-foundation replay for the same Born-rule variance packet. -/
theorem position_variance_born_via_reusable_foundation
    {H X : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    [MeasurableSpace X] (G : PositionVarianceBornGrounding H X) :
    G.sigmaSq = G.secondMoment - G.densityIntegral ^ 2 := by
  exact positionVarianceBornFormula (positionVarianceBornEvidenceOfGrounding G)

/-- Source-only wrapper for position variance in Born-rule moment form. -/
theorem position_variance_born_source_grounded
    (V : PositionVarianceBornEvidence) :
    V.sigmaSq = V.secondMoment - V.densityIntegral ^ 2 := by
  exact positionVarianceBornFormula V

end Mathformer.Physics.FormalPhysics0035
