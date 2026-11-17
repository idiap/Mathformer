import Mathlib
import MathformerPhysicsLib.Lean.Foundations

/-!
Source: FormalPhysics record `formalphysics_0043`, source index 43.
Field: Quantum Mechanics.
Informal target: in the Heisenberg-picture harmonic oscillator, from
`d p(t) / dt = -m omega^2 x(t)`, show
`d^2 p(t) / dt^2 = -m omega^2 d x(t) / dt`.

Informal derivation summary:
1. Start from the first-order momentum equation
   `d p(t) / dt = -m omega^2 x(t)`.
2. Differentiate both sides with respect to time.
3. Use that `m` and `omega` are time-independent constants.
4. Identify the derivative of the right-hand side as
   `-m omega^2 d x(t) / dt`.

Recursive grounding:
- selected from source-only FormalPhysics `question` and `answer` fields;
- no dataset Lean solution content is read, copied, or validated;
- the source operator notation is represented by bounded Hilbert-operator
  curves over a Mathlib Hilbert carrier;
- the first-order momentum law, derivative of that law, product/constant-rule
  calculus support, Heisenberg-picture frame, smoothness, nonzero/positive
  constants, boundary context, and unit/dimension homogeneity are explicit Lean
  surfaces before the reusable `OscillatorMomentumSecondDerivativeEvidence`
  theorem is invoked.

Formal alignment:
- source step 1 maps to `G.momentum_equation`;
- source step 2 maps to `G.momentum_derivative_has_deriv` and
  `G.differentiated_momentum_equation`;
- source step 3 maps to `G.mass_frequency_time_independent_context`;
- source step 4 maps to `G.rhs_derivative`;
- the final result is replayed through `oscillatorMomentumSecondDerivative`.
-/

namespace Mathformer.Physics.FormalPhysics0043

open MathformerPhysicsLib.Foundations.Contexts
open MathformerPhysicsLib.Foundations.HilbertSpace
open MathformerPhysicsLib.Foundations.Laws
open MathformerPhysicsLib.Foundations.QuantumMechanicsExamples
open MathformerPhysicsLib.Foundations.Units

/-- Source-grounded bounded-Hilbert-operator packet for differentiating the
Heisenberg harmonic-oscillator momentum equation.  The curve fields keep the
operator-valued time dependence visible, while the evidence fields record the
source differentiation steps. -/
structure OscillatorMomentumSecondDerivativeGrounding
    (H : Type*) [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H] where
  state : HilbertStateCarrier ℂ H
  positionCurve : ℝ → HilbertBoundedOperator ℂ H
  momentumCurve : ℝ → HilbertBoundedOperator ℂ H
  momentumDerivativeCurve : ℝ → HilbertBoundedOperator ℂ H
  x : HilbertBoundedOperator ℂ H
  p : HilbertBoundedOperator ℂ H
  dx : HilbertBoundedOperator ℂ H
  dp : HilbertBoundedOperator ℂ H
  ddp : HilbertBoundedOperator ℂ H
  differentiatedRhs : HilbertBoundedOperator ℂ H
  m : ℝ
  omega : ℝ
  t : ℝ
  heisenberg_picture_Frame_context : PhysicsContext True
  harmonic_oscillator_context : PhysicsContext True
  mass_frequency_time_independent_context : PhysicsContext True
  boundary_not_applicable_context : PhysicsContext True
  Smooth_operator_curve_context : PhysicsContext True
  scale_nonzero_context : PhysicsContext (m ≠ 0 ∧ omega ≠ 0)
  scale_pos_context : PhysicsContext (0 < m ∧ 0 < omega)
  position_at_time : positionCurve t = x
  momentum_at_time : momentumCurve t = p
  momentum_derivative_at_time : momentumDerivativeCurve t = dp
  position_has_deriv : HasDerivAt positionCurve dx t
  momentum_has_deriv : HasDerivAt momentumCurve dp t
  momentum_derivative_has_deriv : HasDerivAt momentumDerivativeCurve ddp t
  momentum_equation : dp = -(m * omega ^ 2) • x
  differentiated_momentum_equation : ddp = differentiatedRhs
  rhs_derivative : differentiatedRhs = -(m * omega ^ 2) • dx
  oscillator_momentum_unit_dimension_bridge :
    UnitDimensionCompatible ddp (-(m * omega ^ 2) • dx)

/-- Source-law proposition for the differentiated Heisenberg momentum
equation. -/
def OscillatorMomentumSecondDerivativeSourceLaw
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorMomentumSecondDerivativeGrounding H) : Prop :=
  G.ddp = -(G.m * G.omega ^ 2) • G.dx

/-- Coordinate projection bridge for the mass, oscillator frequency, and time
parameter used by the source calculation. -/
def coordinate
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorMomentumSecondDerivativeGrounding H) : ℝ × ℝ × ℝ :=
  (G.m, G.omega, G.t)

/-- Projection from the Hilbert/operator carrier to the source-side
position/momentum actions on the chosen state. -/
def oscillator_momentum_second_derivative_operator_projection
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorMomentumSecondDerivativeGrounding H) : H × H × H :=
  (G.positionCurve G.t G.state, G.momentumCurve G.t G.state, G.ddp G.state)

/-- Calculus support: the source differentiates the position operator curve in
time to obtain `dx/dt`. -/
theorem oscillator_momentum_position_derivative_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorMomentumSecondDerivativeGrounding H) :
    HasDerivAt G.positionCurve G.dx G.t :=
  G.position_has_deriv

/-- Calculus support: the source first-order momentum derivative is the time
derivative of the momentum curve. -/
theorem oscillator_momentum_first_derivative_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorMomentumSecondDerivativeGrounding H) :
    HasDerivAt G.momentumCurve G.dp G.t :=
  G.momentum_has_deriv

/-- Calculus support: differentiating the first momentum derivative gives
`d^2 p(t) / dt^2`. -/
theorem oscillator_momentum_second_derivative_calculus_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorMomentumSecondDerivativeGrounding H) :
    HasDerivAt G.momentumDerivativeCurve G.ddp G.t :=
  G.momentum_derivative_has_deriv

/-- Source-step support: the starting Heisenberg momentum equation. -/
theorem oscillator_momentum_equation_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorMomentumSecondDerivativeGrounding H) :
    G.dp = -(G.m * G.omega ^ 2) • G.x :=
  G.momentum_equation

/-- Source-step support: differentiating the left side of the momentum equation
produces the second momentum derivative. -/
theorem oscillator_momentum_differentiated_equation_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorMomentumSecondDerivativeGrounding H) :
    G.ddp = G.differentiatedRhs :=
  G.differentiated_momentum_equation

/-- Source-step support: with `m` and `omega` constant in time, the derivative
of `-m omega^2 x(t)` is `-m omega^2 dx(t)/dt`. -/
theorem oscillator_momentum_rhs_derivative_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorMomentumSecondDerivativeGrounding H) :
    G.differentiatedRhs = -(G.m * G.omega ^ 2) • G.dx :=
  G.rhs_derivative

/-- Unit/dimension support for the differentiated momentum equation. -/
theorem oscillator_momentum_second_derivative_unit_dimension_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorMomentumSecondDerivativeGrounding H) :
    G.ddp = -(G.m * G.omega ^ 2) • G.dx :=
  unit_dimension_bridge G.oscillator_momentum_unit_dimension_bridge

/-- Algebraic core: the differentiated equation and the right-hand derivative
identification give the source target. -/
theorem oscillator_momentum_second_derivative_algebraic_core
    {E : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E]
    {ddp dx differentiatedRhs : E} {m omega : ℝ}
    (differentiated_momentum_equation : ddp = differentiatedRhs)
    (rhs_derivative : differentiatedRhs = -(m * omega ^ 2) • dx) :
    ddp = -(m * omega ^ 2) • dx := by
  rw [differentiated_momentum_equation, rhs_derivative]

/-- Source-law support for the bounded Hilbert-operator differentiated
momentum equation. -/
theorem oscillator_momentum_second_derivative_source_law_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorMomentumSecondDerivativeGrounding H) :
    OscillatorMomentumSecondDerivativeSourceLaw G := by
  unfold OscillatorMomentumSecondDerivativeSourceLaw
  exact oscillator_momentum_second_derivative_algebraic_core
    G.differentiated_momentum_equation G.rhs_derivative

/-- Bridge from the Hilbert-operator grounding packet to the reusable
MathformerPhysicsLib oscillator momentum-second-derivative evidence packet. -/
def oscillatorMomentumSecondDerivativeEvidenceOfHilbertGrounding
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorMomentumSecondDerivativeGrounding H) :
    OscillatorMomentumSecondDerivativeEvidence (HilbertBoundedOperator ℂ H) where
  m := G.m
  omega := G.omega
  ddp := G.ddp
  dx := G.dx
  differentiated_rhs := G.differentiatedRhs
  differentiated_momentum_equation := G.differentiated_momentum_equation
  rhs_derivative := G.rhs_derivative

/-- Source-only bounded-Hilbert-operator form of the differentiated oscillator
momentum equation. -/
theorem oscillator_momentum_second_derivative_hilbert_grounded
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorMomentumSecondDerivativeGrounding H)
    (source_law : PhysicalLawWitness (OscillatorMomentumSecondDerivativeSourceLaw G)) :
    G.ddp = -(G.m * G.omega ^ 2) • G.dx := by
  have _ : True := G.heisenberg_picture_Frame_context.holds
  have _ : True := G.harmonic_oscillator_context.holds
  have _ : True := G.mass_frequency_time_independent_context.holds
  have _ : True := G.boundary_not_applicable_context.holds
  have _ : True := G.Smooth_operator_curve_context.holds
  have _ : G.m ≠ 0 ∧ G.omega ≠ 0 := G.scale_nonzero_context.holds
  have _ : 0 < G.m ∧ 0 < G.omega := G.scale_pos_context.holds
  have _ : HasDerivAt G.positionCurve G.dx G.t :=
    oscillator_momentum_position_derivative_support G
  have _ : HasDerivAt G.momentumCurve G.dp G.t :=
    oscillator_momentum_first_derivative_support G
  have _ : HasDerivAt G.momentumDerivativeCurve G.ddp G.t :=
    oscillator_momentum_second_derivative_calculus_support G
  have _ : G.ddp = -(G.m * G.omega ^ 2) • G.dx :=
    oscillator_momentum_second_derivative_unit_dimension_support G
  have h_source : OscillatorMomentumSecondDerivativeSourceLaw G := source_law.holds
  unfold OscillatorMomentumSecondDerivativeSourceLaw at h_source
  exact h_source

/-- Reusable-foundation replay for the same bounded Hilbert-operator packet. -/
theorem oscillator_momentum_second_derivative_hilbert_via_reusable_foundation
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorMomentumSecondDerivativeGrounding H) :
    G.ddp = -(G.m * G.omega ^ 2) • G.dx := by
  exact oscillatorMomentumSecondDerivative
    (oscillatorMomentumSecondDerivativeEvidenceOfHilbertGrounding G)

/-- Source-only wrapper for the second derivative of oscillator momentum. -/
theorem oscillator_momentum_second_derivative_source_grounded
    {E : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E]
    (O : OscillatorMomentumSecondDerivativeEvidence E) :
    O.ddp = -(O.m * O.omega ^ 2) • O.dx := by
  exact oscillatorMomentumSecondDerivative O

end Mathformer.Physics.FormalPhysics0043
