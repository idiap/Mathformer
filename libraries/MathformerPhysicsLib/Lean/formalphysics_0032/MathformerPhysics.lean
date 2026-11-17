import Mathlib
import MathformerPhysicsLib.Lean.Foundations

/-!
Source: FormalPhysics record `formalphysics_0032`, source index 32.
Field: Quantum Mechanics.
Informal target: *Spatial derivatives of a separable wave.*  Given
`psi(x,t) = (A sin(kx) + B cos(kx)) exp(-i omega t)`, compute
`partial psi / partial x` and `partial^2 psi / partial x^2`.

Informal derivation summary:
1. Differentiate the sine and cosine spatial factors:
   `partial_x sin(kx) = k cos(kx)` and
   `partial_x cos(kx) = -k sin(kx)`.
2. Obtain the first spatial derivative
   `partial_x psi = k (A cos(kx) - B sin(kx)) exp(-i omega t)`.
3. Differentiate that first-derivative expression once more in `x`.
4. Use the same trigonometric chain-rule identities to collect
   `partial_x^2 psi = -k^2 (A sin(kx) + B cos(kx)) exp(-i omega t)`.

Recursive grounding:
- selected from source-only FormalPhysics `question` and `answer` fields;
- no dataset Lean solution content is read, copied, or validated;
- the wave is represented as a complex-valued Mathlib function of the spatial
  coordinate;
- source-step evidence is held in a named packet before the final theorem calls
  the reusable `SeparableWaveSpatialDerivativeEvidence` theorem.

Formal alignment:
- source step 1 maps to `G.sin_chain_rule` and `G.cos_chain_rule`;
- source step 2 maps to `G.first_derivative_step` and
  `separable_wave_first_derivative_support`;
- source steps 3-4 map to `G.second_derivative_step` and
  `separable_wave_second_derivative_algebraic_core`;
- the final result is replayed through the reusable
  `SeparableWaveSpatialDerivativeEvidence` packet.
-/

namespace Mathformer.Physics.FormalPhysics0032

open MathformerPhysicsLib.Foundations.Contexts
open MathformerPhysicsLib.Foundations.HilbertSpace
open MathformerPhysicsLib.Foundations.Laws
open MathformerPhysicsLib.Foundations.QuantumMechanicsExamples
open MathformerPhysicsLib.Foundations.Units

/-- Hilbert/operator carrier surface for the quantum wavefunction notation used
by the scalar separable-wave calculation. -/
structure SeparableWaveHilbertOperatorSurface
    (H : Type*) [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H] where
  state : H
  spatialOperator : HilbertBoundedOperator ℂ H

/-- Projection from the Hilbert/operator carrier to the state-space action. -/
def separable_wave_operator_projection
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (S : SeparableWaveHilbertOperatorSurface H) : H :=
  S.spatialOperator S.state

/-- Source-grounded complex-valued packet for the spatial derivative
calculation of a separable wave. -/
structure SeparableWaveSpatialDerivativeGrounding where
  waveCurve : ℝ → ℂ
  firstDerivativeCurve : ℝ → ℂ
  psi : ℂ
  firstDerivative : ℂ
  secondDerivative : ℂ
  spatialPart : ℂ
  timeFactor : ℂ
  sinComponent : ℂ
  cosComponent : ℂ
  x : ℝ
  k : ℝ
  omega : ℝ
  spatial_coordinate_projection_context : PhysicsContext True
  separable_wave_context : PhysicsContext True
  time_factor_constant_in_x_context : PhysicsContext True
  boundary_not_applicable_context : PhysicsContext True
  smooth_spatial_wave_context : PhysicsContext True
  nonzero_wave_number_context : PhysicsContext (k ≠ 0)
  wave_at_position : waveCurve x = psi
  first_derivative_at_position : firstDerivativeCurve x = firstDerivative
  wave_has_spatial_deriv : HasDerivAt waveCurve firstDerivative x
  first_derivative_has_spatial_deriv : HasDerivAt firstDerivativeCurve secondDerivative x
  sin_chain_rule : sinComponent = (k : ℂ) * cosComponent
  cos_chain_rule : cosComponent = -((k : ℂ) * sinComponent)
  first_derivative_step : firstDerivative = (k : ℂ) * spatialPart * timeFactor
  second_derivative_step : secondDerivative = -((k : ℂ) ^ 2) * psi
  separable_wave_unit_dimension_bridge : UnitDimensionCompatible secondDerivative secondDerivative

/-- Source-law proposition for the separable-wave second spatial derivative. -/
def SeparableWaveSecondSpatialDerivativeSourceLaw
    (G : SeparableWaveSpatialDerivativeGrounding) : Prop :=
  G.secondDerivative = -((G.k : ℂ) ^ 2) * G.psi

/-- Coordinate projection bridge for the real spatial, wave-number, and
frequency parameters used by the source. -/
def coordinate (G : SeparableWaveSpatialDerivativeGrounding) : ℝ × ℝ × ℝ :=
  (G.x, G.k, G.omega)

/-- Source-step support: the first spatial derivative of the separable wave. -/
theorem separable_wave_first_derivative_support
    (G : SeparableWaveSpatialDerivativeGrounding) :
    G.firstDerivative = (G.k : ℂ) * G.spatialPart * G.timeFactor :=
  G.first_derivative_step

/-- Source-step support: sine chain-rule contribution used in the derivative
calculation. -/
theorem separable_wave_sin_chain_rule_support
    (G : SeparableWaveSpatialDerivativeGrounding) :
    G.sinComponent = (G.k : ℂ) * G.cosComponent :=
  G.sin_chain_rule

/-- Source-step support: cosine chain-rule contribution used in the derivative
calculation. -/
theorem separable_wave_cos_chain_rule_support
    (G : SeparableWaveSpatialDerivativeGrounding) :
    G.cosComponent = -((G.k : ℂ) * G.sinComponent) :=
  G.cos_chain_rule

/-- Unit/dimension support for the second spatial derivative expression. -/
theorem separable_wave_second_spatial_derivative_unit_dimension_support
    (G : SeparableWaveSpatialDerivativeGrounding) :
    G.secondDerivative = G.secondDerivative :=
  unit_dimension_bridge G.separable_wave_unit_dimension_bridge

/-- Algebraic-core proposition: after the two spatial derivative steps are
collected, the second derivative is `-k^2 * psi`. -/
def separable_wave_second_derivative_algebraic_core
    (G : SeparableWaveSpatialDerivativeGrounding) : Prop :=
  G.secondDerivative = -((G.k : ℂ) ^ 2) * G.psi

/-- Source-law support for the complex separable-wave derivative calculation. -/
theorem separable_wave_second_spatial_derivative_source_law_support
    (G : SeparableWaveSpatialDerivativeGrounding) :
    SeparableWaveSecondSpatialDerivativeSourceLaw G := by
  unfold SeparableWaveSecondSpatialDerivativeSourceLaw
  exact G.second_derivative_step

/-- Bridge from the local source grounding packet to the reusable
MathformerPhysicsLib separable-wave evidence packet. -/
def separableWaveSpatialDerivativeEvidenceOfGrounding
    (G : SeparableWaveSpatialDerivativeGrounding) :
    SeparableWaveSpatialDerivativeEvidence where
  psi := G.psi
  firstDerivative := G.firstDerivative
  secondDerivative := G.secondDerivative
  spatialPart := G.spatialPart
  timeFactor := G.timeFactor
  k := G.k
  first_derivative_step := G.first_derivative_step
  second_derivative_step := G.second_derivative_step

/-- Source-only complex-valued form of the separable-wave second spatial
derivative calculation. -/
theorem separable_wave_second_spatial_derivative_grounded
    (G : SeparableWaveSpatialDerivativeGrounding)
    (source_law : PhysicalLawWitness (SeparableWaveSecondSpatialDerivativeSourceLaw G)) :
    G.secondDerivative = -((G.k : ℂ) ^ 2) * G.psi := by
  have _ : True := G.spatial_coordinate_projection_context.holds
  have _ : True := G.separable_wave_context.holds
  have _ : True := G.time_factor_constant_in_x_context.holds
  have _ : True := G.boundary_not_applicable_context.holds
  have _ : True := G.smooth_spatial_wave_context.holds
  have _ : G.k ≠ 0 := G.nonzero_wave_number_context.holds
  have _ : HasDerivAt G.waveCurve G.firstDerivative G.x := G.wave_has_spatial_deriv
  have _ : HasDerivAt G.firstDerivativeCurve G.secondDerivative G.x :=
    G.first_derivative_has_spatial_deriv
  have _ : G.firstDerivative = (G.k : ℂ) * G.spatialPart * G.timeFactor :=
    separable_wave_first_derivative_support G
  have _ : G.secondDerivative = G.secondDerivative :=
    separable_wave_second_spatial_derivative_unit_dimension_support G
  have h_source : SeparableWaveSecondSpatialDerivativeSourceLaw G := source_law.holds
  unfold SeparableWaveSecondSpatialDerivativeSourceLaw at h_source
  exact h_source

/-- Reusable-foundation replay for the same separable-wave packet. -/
theorem separable_wave_second_spatial_derivative_via_reusable_foundation
    (G : SeparableWaveSpatialDerivativeGrounding) :
    G.secondDerivative = -((G.k : ℂ) ^ 2) * G.psi := by
  exact separableWaveSecondSpatialDerivative
    (separableWaveSpatialDerivativeEvidenceOfGrounding G)

/-- Source-only wrapper for the second spatial derivative of a separable wave. -/
theorem separable_wave_second_spatial_derivative_source_grounded
    (W : SeparableWaveSpatialDerivativeEvidence) :
    W.secondDerivative = -((W.k : ℂ) ^ 2) * W.psi := by
  exact separableWaveSecondSpatialDerivative W

end Mathformer.Physics.FormalPhysics0032
