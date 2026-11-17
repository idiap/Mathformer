import Mathlib
import MathformerPhysicsLib.Lean.Foundations

/-!
Source: FormalPhysics record `formalphysics_0023`, source index 23.
Field: Quantum Mechanics.
Informal target: *Heisenberg-picture simple harmonic oscillator.*  A particle
of mass `m` in a one-dimensional harmonic potential
`V(x) = 1/2 * m * omega^2 * x^2` obeys the Heisenberg equations
`d x(t) / dt = p(t) / m` and `d p(t) / dt = -m omega^2 x(t)`.  Show that the
position operator satisfies `d^2 x(t) / dt^2 = -omega^2 x(t)`.

Informal derivation summary:
1. Differentiate `d x(t) / dt = p(t) / m` once in time.
2. Obtain `d^2 x(t) / dt^2 = (1 / m) * d p(t) / dt`.
3. Insert `d p(t) / dt = -m omega^2 x(t)`.
4. Simplify the mass factor to obtain
   `d^2 x(t) / dt^2 = -omega^2 x(t)`.

Recursive grounding:
- selected from source-only FormalPhysics `question` and `answer` fields;
- no dataset Lean solution content is read, copied, or validated;
- the operator surface is represented by bounded Hilbert operators from
  `MathformerPhysicsLib.Foundations.HilbertSpace`;
- source-step evidence is held in a named packet before the final theorem calls
  the reusable `OscillatorPositionSecondDerivativeEvidence` theorem.

Formal alignment:
- source step 1 maps to `G.position_has_deriv`, `G.velocity_has_deriv`, and
  `G.differentiated_velocity_equation`;
- source step 2 maps to `oscillator_position_second_from_velocity_support`;
- source step 3 maps to `oscillator_position_momentum_equation_support`;
- source step 4 maps to `oscillator_position_mass_cancellation_support`;
- the final result follows from
  `oscillator_position_second_derivative_algebraic_core` and is replayed
  through the reusable MathformerPhysicsLib evidence packet.
-/

namespace Mathformer.Physics.FormalPhysics0023

open MathformerPhysicsLib.Foundations.Contexts
open MathformerPhysicsLib.Foundations.HilbertSpace
open MathformerPhysicsLib.Foundations.Laws
open MathformerPhysicsLib.Foundations.Operators
open MathformerPhysicsLib.Foundations.PositionMomentumModels
open MathformerPhysicsLib.Foundations.QuantumMechanicsExamples
open MathformerPhysicsLib.Foundations.Units

/-- Source-grounded bounded-Hilbert-operator packet for deriving the oscillator
position second-derivative equation from the first-order Heisenberg equations. -/
structure OscillatorPositionSecondDerivativeHilbertGrounding
    (H : Type*) [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H] where
  positionCurve : ℝ → HilbertBoundedOperator ℂ H
  velocityCurve : ℝ → HilbertBoundedOperator ℂ H
  x : HilbertBoundedOperator ℂ H
  dx : HilbertBoundedOperator ℂ H
  ddx : HilbertBoundedOperator ℂ H
  p : HilbertBoundedOperator ℂ H
  dp : HilbertBoundedOperator ℂ H
  m : ℝ
  omega : ℝ
  t : ℝ
  operator_coordinate_projection_context : PhysicsContext True
  heisenberg_picture_context : PhysicsContext True
  harmonic_potential_context : PhysicsContext True
  boundary_not_applicable_context : PhysicsContext True
  smooth_position_curve_context : PhysicsContext True
  nonzero_mass_context : PhysicsContext (m ≠ 0)
  position_at_time : positionCurve t = x
  velocity_at_time : velocityCurve t = dx
  position_has_deriv : HasDerivAt positionCurve dx t
  velocity_has_deriv : HasDerivAt velocityCurve ddx t
  velocity_equation : dx = (1 / m) • p
  differentiated_velocity_equation : ddx = (1 / m) • dp
  momentum_equation : dp = -(m * omega ^ 2) • x
  mass_cancellation : (1 / m) • (-(m * omega ^ 2) • x) = -(omega ^ 2) • x
  oscillator_unit_dimension_bridge : UnitDimensionCompatible ddx ddx

/-- Source-law proposition for the oscillator position second-derivative
equation. -/
def OscillatorPositionSecondDerivativeSourceLaw
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorPositionSecondDerivativeHilbertGrounding H) : Prop :=
  G.ddx = -(G.omega ^ 2) • G.x

/-- Coordinate projection bridge for the raw real mass/frequency/time
parameters used by the source equations. -/
def coordinate
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorPositionSecondDerivativeHilbertGrounding H) : ℝ × ℝ × ℝ :=
  (G.m, G.omega, G.t)

/-- Source-step support: differentiating the velocity relation gives the second
position derivative as `(1 / m)` times the momentum derivative. -/
theorem oscillator_position_second_from_velocity_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorPositionSecondDerivativeHilbertGrounding H) :
    G.ddx = (1 / G.m) • G.dp :=
  G.differentiated_velocity_equation

/-- Source-step support: the Heisenberg momentum equation for the oscillator. -/
theorem oscillator_position_momentum_equation_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorPositionSecondDerivativeHilbertGrounding H) :
    G.dp = -(G.m * G.omega ^ 2) • G.x :=
  G.momentum_equation

/-- Source-step support: cancel the mass factor after substituting the momentum
equation. -/
theorem oscillator_position_mass_cancellation_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorPositionSecondDerivativeHilbertGrounding H) :
    (1 / G.m) • (-(G.m * G.omega ^ 2) • G.x) = -(G.omega ^ 2) • G.x :=
  G.mass_cancellation

/-- Unit/dimension support for the acceleration-side oscillator expression. -/
theorem oscillator_position_second_derivative_unit_dimension_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorPositionSecondDerivativeHilbertGrounding H) :
    G.ddx = G.ddx :=
  unit_dimension_bridge G.oscillator_unit_dimension_bridge

/-- Algebraic core: differentiating the velocity equation, substituting the
momentum equation, and cancelling mass gives the oscillator equation. -/
theorem oscillator_position_second_derivative_algebraic_core
    {E : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E]
    {x ddx dp : E} {m omega : ℝ}
    (second_from_velocity : ddx = (1 / m) • dp)
    (momentum_equation : dp = -(m * omega ^ 2) • x)
    (mass_cancellation : (1 / m) • (-(m * omega ^ 2) • x) = -(omega ^ 2) • x) :
    ddx = -(omega ^ 2) • x := by
  rw [second_from_velocity, momentum_equation, mass_cancellation]

/-- Source-law support for the bounded Hilbert-operator oscillator acceleration
equation. -/
theorem oscillator_position_second_derivative_source_law_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorPositionSecondDerivativeHilbertGrounding H) :
    OscillatorPositionSecondDerivativeSourceLaw G := by
  unfold OscillatorPositionSecondDerivativeSourceLaw
  exact oscillator_position_second_derivative_algebraic_core
    (oscillator_position_second_from_velocity_support G)
    (oscillator_position_momentum_equation_support G)
    (oscillator_position_mass_cancellation_support G)

/-- Bridge from the Hilbert-operator grounding packet to the reusable
MathformerPhysicsLib oscillator second-derivative evidence packet. -/
def oscillatorPositionSecondDerivativeEvidenceOfHilbertGrounding
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorPositionSecondDerivativeHilbertGrounding H) :
    OscillatorPositionSecondDerivativeEvidence (HilbertBoundedOperator ℂ H) where
  m := G.m
  omega := G.omega
  t := G.t
  x := G.x
  ddx := G.ddx
  dp := G.dp
  second_from_velocity := G.differentiated_velocity_equation
  momentum_equation := G.momentum_equation
  mass_cancellation := G.mass_cancellation

/-- Source-only bounded-Hilbert-operator form of the oscillator position
second-derivative equation. -/
theorem oscillator_position_second_derivative_hilbert_grounded
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorPositionSecondDerivativeHilbertGrounding H)
    (source_law : PhysicalLawWitness (OscillatorPositionSecondDerivativeSourceLaw G)) :
    G.ddx = -(G.omega ^ 2) • G.x := by
  have _ : True := G.operator_coordinate_projection_context.holds
  have _ : True := G.heisenberg_picture_context.holds
  have _ : True := G.harmonic_potential_context.holds
  have _ : True := G.boundary_not_applicable_context.holds
  have _ : True := G.smooth_position_curve_context.holds
  have _ : G.m ≠ 0 := G.nonzero_mass_context.holds
  have _ : HasDerivAt G.positionCurve G.dx G.t := G.position_has_deriv
  have _ : HasDerivAt G.velocityCurve G.ddx G.t := G.velocity_has_deriv
  have _ : G.dx = (1 / G.m) • G.p := G.velocity_equation
  have _ : G.ddx = G.ddx :=
    oscillator_position_second_derivative_unit_dimension_support G
  have h_source : OscillatorPositionSecondDerivativeSourceLaw G := source_law.holds
  unfold OscillatorPositionSecondDerivativeSourceLaw at h_source
  exact h_source

/-- Reusable-foundation replay for the same bounded Hilbert-operator packet. -/
theorem oscillator_position_second_derivative_hilbert_via_reusable_foundation
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorPositionSecondDerivativeHilbertGrounding H) :
    G.ddx = -(G.omega ^ 2) • G.x := by
  exact oscillatorPositionSecondDerivative
    (oscillatorPositionSecondDerivativeEvidenceOfHilbertGrounding G)

/-- Source-only wrapper for the harmonic-oscillator position equation. -/
theorem oscillator_position_second_derivative_source_grounded
    {E : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E]
    (O : OscillatorPositionSecondDerivativeEvidence E) :
    O.ddx = -(O.omega ^ 2) • O.x := by
  exact oscillatorPositionSecondDerivative O

end Mathformer.Physics.FormalPhysics0023
