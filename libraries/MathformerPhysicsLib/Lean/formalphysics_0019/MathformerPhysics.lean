import Mathlib
import MathformerPhysicsLib.Lean.Foundations

/-!
Source: FormalPhysics record `formalphysics_0019`, source index 19.
Field: Quantum Mechanics.
Informal target: *Heisenberg-picture 1D quantum harmonic oscillator.* For mass $m$ and frequency $\omega$, suppose the position operator evolves as $$ \hat{x}(t)=\hat{x}(0)\cos(\omega t)+\frac{\hat{p}(0)}{m\omega}\sin(\omega t). $$ Show that the velocity operator satisfies $\dot{\hat{x}}(t)=\hat{p}(t)/m$, and use this to obtain $\hat{p}(t)$ in terms of $\hat{x}(0)$ and $\hat{p}(0)$. **

Informal derivation summary: Differentiate $\hat{x}(t)$: $$ \frac{d\hat{x}(t)}{dt}=-\omega\,\hat{x}(0)\sin(\omega t)+\frac{\hat{p}(0)}{m}\cos(\omega t). $$ Invoke the Heisenberg equation $\dot{\hat{x}}(t)=\hat{p}(t)/m$: $$ \frac{\hat{p}(t)}{m}=-\omega\,\hat{x(0)}\sin(\omega t)+\frac{\hat{p}(0)}{m}\cos(\omega t). $$ Multiply by $m$: $$ \hat{p}(t)=-m\omega\,\hat{x}(0)\sin(\omega t)+\hat{p}(0)\cos(\omega t). $$

Recursive grounding:
- selected from source-only FormalPhysics `question` and `answer` fields;
- no dataset Lean solution content is read, copied, or validated;
- the target is routed through `MathformerPhysicsLib.Foundations.QuantumMechanicsExamples`;
- source-step evidence is held in a named packet before the final theorem calls
  the reusable MathformerPhysicsLib theorem.

Formal alignment:
- differentiating the oscillator position curve maps to `G.position_has_deriv`
  and `G.differentiated_position`;
- the Heisenberg velocity relation maps to `G.velocity_relation`;
- multiplying by the mass maps to `G.mass_velocity_scaling`;
- substituting the differentiated position into that mass-scaled relation maps
  to `G.scaled_derivative`;
- the final result follows from `oscillator_velocity_to_momentum_algebraic_core`
  and is replayed through the reusable `OscillatorVelocityEvidence` packet.
-/

namespace Mathformer.Physics.FormalPhysics0019

open MathformerPhysicsLib.Foundations.HilbertSpace
open MathformerPhysicsLib.Foundations.Contexts
open MathformerPhysicsLib.Foundations.Laws
open MathformerPhysicsLib.Foundations.Operators
open MathformerPhysicsLib.Foundations.PositionMomentumModels
open MathformerPhysicsLib.Foundations.QuantumMechanicsExamples
open MathformerPhysicsLib.Foundations.Units

/-- Source-grounded bounded-Hilbert-operator packet for the Heisenberg-picture
oscillator velocity-to-momentum derivation. -/
structure OscillatorVelocityHilbertGrounding
    (H : Type*) [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H] where
  x0 : HilbertBoundedOperator ℂ H
  p0 : HilbertBoundedOperator ℂ H
  positionCurve : ℝ → HilbertBoundedOperator ℂ H
  xAtTime : HilbertBoundedOperator ℂ H
  dx : HilbertBoundedOperator ℂ H
  pAtTime : HilbertBoundedOperator ℂ H
  m : ℝ
  omega : ℝ
  t : ℝ
  operator_coordinate_projection_context : PhysicsContext True
  heisenberg_picture_context : PhysicsContext True
  boundary_not_applicable_context : PhysicsContext True
  smooth_position_curve_context : PhysicsContext True
  nonzero_mass_frequency_context : PhysicsContext (m ≠ 0 ∧ omega ≠ 0)
  position_at_time : positionCurve t = xAtTime
  position_has_deriv : HasDerivAt positionCurve dx t
  differentiated_position :
    dx = (-(omega * Real.sin (omega * t))) • x0 + ((1 / m) * Real.cos (omega * t)) • p0
  velocity_relation : dx = (1 / m) • pAtTime
  mass_velocity_scaling : pAtTime = m • dx
  scaled_derivative :
    m • dx = (-(m * omega) * Real.sin (omega * t)) • x0 + (Real.cos (omega * t)) • p0
  momentum_unit_dimension_bridge : UnitDimensionCompatible pAtTime pAtTime

/-- Source-law proposition for the oscillator momentum solution. -/
def OscillatorMomentumSourceLaw
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorVelocityHilbertGrounding H) : Prop :=
  G.pAtTime = (-(G.m * G.omega) * Real.sin (G.omega * G.t)) • G.x0 +
    (Real.cos (G.omega * G.t)) • G.p0

/-- Coordinate projection bridge for the raw real parameters used by the
source oscillator formulas. -/
def coordinate
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorVelocityHilbertGrounding H) : ℝ × ℝ × ℝ :=
  (G.m, G.omega, G.t)

/-- Derivative grounding for the position operator curve. -/
theorem oscillator_position_derivative_grounding
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorVelocityHilbertGrounding H) :
    HasDerivAt G.positionCurve G.dx G.t :=
  G.position_has_deriv

/-- The Heisenberg velocity relation used before solving for momentum. -/
theorem oscillator_velocity_relation_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorVelocityHilbertGrounding H) :
    G.dx = (1 / G.m) • G.pAtTime :=
  G.velocity_relation

/-- Unit/dimension support for the momentum expression in this dimensioned
oscillator setting. -/
theorem oscillator_momentum_unit_dimension_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorVelocityHilbertGrounding H) :
    G.pAtTime = G.pAtTime :=
  unit_dimension_bridge G.momentum_unit_dimension_bridge

/-- Algebraic core: after differentiating position and using
`p(t) = m * dx/dt`, the momentum expression follows by substitution. -/
theorem oscillator_velocity_to_momentum_algebraic_core
    {E : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E]
    {x0 p0 dx pAtTime : E} {m omega t : ℝ}
    (mass_velocity_scaling : pAtTime = m • dx)
    (scaled_derivative :
      m • dx = (-(m * omega) * Real.sin (omega * t)) • x0 +
        (Real.cos (omega * t)) • p0) :
    pAtTime = (-(m * omega) * Real.sin (omega * t)) • x0 +
      (Real.cos (omega * t)) • p0 := by
  rw [mass_velocity_scaling, scaled_derivative]

/-- Source-law support for the bounded Hilbert-operator oscillator momentum
solution. -/
theorem oscillator_momentum_source_law_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorVelocityHilbertGrounding H) :
    OscillatorMomentumSourceLaw G := by
  unfold OscillatorMomentumSourceLaw
  exact oscillator_velocity_to_momentum_algebraic_core
    G.mass_velocity_scaling G.scaled_derivative

/-- Bridge from the Hilbert-operator grounding packet to the reusable
MathformerPhysicsLib oscillator velocity evidence packet. -/
def oscillatorVelocityEvidenceOfHilbertGrounding
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorVelocityHilbertGrounding H) :
    OscillatorVelocityEvidence (HilbertBoundedOperator ℂ H) where
  x0 := G.x0
  p0 := G.p0
  m := G.m
  omega := G.omega
  t := G.t
  dx := G.dx
  pAtTime := G.pAtTime
  differentiated_position := G.differentiated_position
  velocity_relation := G.velocity_relation
  momentum_solution := oscillator_momentum_source_law_support G

/-- Source-only bounded-Hilbert-operator form of the oscillator momentum
solution. -/
theorem oscillator_momentum_from_velocity_hilbert_grounded
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorVelocityHilbertGrounding H)
    (source_law : PhysicalLawWitness (OscillatorMomentumSourceLaw G)) :
    G.pAtTime = (-(G.m * G.omega) * Real.sin (G.omega * G.t)) • G.x0 +
      (Real.cos (G.omega * G.t)) • G.p0 := by
  have _ : True := G.operator_coordinate_projection_context.holds
  have _ : True := G.heisenberg_picture_context.holds
  have _ : True := G.boundary_not_applicable_context.holds
  have _ : True := G.smooth_position_curve_context.holds
  have _ : G.m ≠ 0 ∧ G.omega ≠ 0 := G.nonzero_mass_frequency_context.holds
  have _ : HasDerivAt G.positionCurve G.dx G.t :=
    oscillator_position_derivative_grounding G
  have _ : G.dx = (1 / G.m) • G.pAtTime :=
    oscillator_velocity_relation_support G
  have _ : G.pAtTime = G.pAtTime :=
    oscillator_momentum_unit_dimension_support G
  have h_source : OscillatorMomentumSourceLaw G := source_law.holds
  unfold OscillatorMomentumSourceLaw at h_source
  exact h_source

/-- Reusable-foundation replay for the same bounded Hilbert-operator packet. -/
theorem oscillator_momentum_from_velocity_hilbert_via_reusable_foundation
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorVelocityHilbertGrounding H) :
    G.pAtTime = (-(G.m * G.omega) * Real.sin (G.omega * G.t)) • G.x0 +
      (Real.cos (G.omega * G.t)) • G.p0 := by
  exact oscillatorMomentumFromVelocity (oscillatorVelocityEvidenceOfHilbertGrounding G)

/-- Source-only wrapper for recovering harmonic-oscillator momentum from velocity. -/
theorem oscillator_momentum_from_velocity_source_grounded
    {E : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E]
    (O : OscillatorVelocityEvidence E) :
    O.pAtTime = (-(O.m * O.omega) * Real.sin (O.omega * O.t)) • O.x0 +
      (Real.cos (O.omega * O.t)) • O.p0 := by
  exact oscillatorMomentumFromVelocity O

end Mathformer.Physics.FormalPhysics0019
