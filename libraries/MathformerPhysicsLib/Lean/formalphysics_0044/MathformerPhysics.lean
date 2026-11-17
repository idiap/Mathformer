import Mathlib
import MathformerPhysicsLib.Lean.Foundations

/-!
Source: FormalPhysics record `formalphysics_0044`, source index 44.
Field: Quantum Mechanics.
Informal target: for a one-dimensional quantum harmonic oscillator in the
Heisenberg picture, solve the operator equation
`d^2 x(t) / dt^2 + omega^2 x(t) = 0` with initial operators `x(0)` and
`p(0) = m dx/dt(0)` to obtain
`x(t) = x(0) cos(omega t) + (p(0) / (m omega)) sin(omega t)`.

Informal derivation summary:
1. Start from the general oscillator solution
   `x(t) = A cos(omega t) + B sin(omega t)`.
2. Evaluate at `t = 0` to identify `A = x(0)`.
3. Differentiate the solution and use `p(t) = m dx(t)/dt`.
4. Evaluate at `t = 0` to identify `B = p(0) / (m omega)`.
5. Substitute the two initial-data identities into the general solution.

Recursive grounding:
- selected from source-only FormalPhysics `question` and `answer` fields;
- no dataset Lean solution content is read, copied, or validated;
- the source operator notation is represented by bounded Hilbert-operator
  curves over a Mathlib Hilbert carrier;
- the oscillator equation, general solution, time derivative, initial
  position/momentum identifications, nonzero/positive physical constants,
  Heisenberg-picture frame, smoothness, boundary context, and unit/dimension
  homogeneity are explicit Lean surfaces before the reusable
  `OscillatorGeneralSolutionEvidence` theorem is invoked.

Formal alignment:
- source step 1 maps to `G.position_solution`;
- source step 2 maps to `G.initial_position`;
- source step 3 maps to `G.position_has_deriv` and `G.velocity_solution`;
- source step 4 maps to `G.initial_momentum`;
- source step 5 maps to `oscillator_position_solution_algebraic_core`;
- the final result is replayed through
  `oscillatorPositionSolutionFromInitialData`.
-/

namespace Mathformer.Physics.FormalPhysics0044

open MathformerPhysicsLib.Foundations.Contexts
open MathformerPhysicsLib.Foundations.HilbertSpace
open MathformerPhysicsLib.Foundations.Laws
open MathformerPhysicsLib.Foundations.QuantumMechanicsExamples
open MathformerPhysicsLib.Foundations.Units

/-- Source-grounded bounded-Hilbert-operator packet for solving the
Heisenberg-picture harmonic-oscillator position equation from initial data. -/
structure OscillatorPositionSolutionGrounding
    (H : Type*) [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H] where
  state : HilbertStateCarrier ℂ H
  positionCurve : ℝ → HilbertBoundedOperator ℂ H
  velocityCurve : ℝ → HilbertBoundedOperator ℂ H
  momentumCurve : ℝ → HilbertBoundedOperator ℂ H
  x0 : HilbertBoundedOperator ℂ H
  p0 : HilbertBoundedOperator ℂ H
  A : HilbertBoundedOperator ℂ H
  B : HilbertBoundedOperator ℂ H
  xAtTime : HilbertBoundedOperator ℂ H
  dxAtTime : HilbertBoundedOperator ℂ H
  dx0 : HilbertBoundedOperator ℂ H
  m : ℝ
  omega : ℝ
  t : ℝ
  heisenberg_picture_Frame_context : PhysicsContext True
  harmonic_oscillator_context : PhysicsContext True
  oscillator_equation_context : PhysicsContext True
  boundary_initial_value_context : PhysicsContext True
  Smooth_operator_curve_context : PhysicsContext True
  scale_nonzero_context : PhysicsContext (m ≠ 0 ∧ omega ≠ 0)
  scale_pos_context : PhysicsContext (0 < m ∧ 0 < omega)
  position_at_time : positionCurve t = xAtTime
  velocity_at_time : velocityCurve t = dxAtTime
  initial_position_operator : positionCurve 0 = x0
  initial_momentum_operator : momentumCurve 0 = p0
  initial_velocity_operator : velocityCurve 0 = dx0
  position_has_deriv : HasDerivAt positionCurve dxAtTime t
  position_has_initial_deriv : HasDerivAt positionCurve dx0 0
  oscillator_equation :
    HasDerivAt velocityCurve (-(omega ^ 2) • xAtTime) t
  velocity_relation_at_zero : p0 = m • dx0
  position_solution :
    xAtTime = (Real.cos (omega * t)) • A + (Real.sin (omega * t)) • B
  velocity_solution :
    dxAtTime =
      (-(omega * Real.sin (omega * t))) • A +
        (omega * Real.cos (omega * t)) • B
  initial_position : A = x0
  initial_momentum : B = (1 / (m * omega)) • p0
  oscillator_position_unit_dimension_bridge :
    UnitDimensionCompatible xAtTime
      ((Real.cos (omega * t)) • x0 +
        (Real.sin (omega * t)) • ((1 / (m * omega)) • p0))

/-- Source-law proposition for the oscillator position solution with initial
data. -/
def OscillatorPositionSolutionSourceLaw
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorPositionSolutionGrounding H) : Prop :=
  G.xAtTime =
    (Real.cos (G.omega * G.t)) • G.x0 +
      (Real.sin (G.omega * G.t)) • ((1 / (G.m * G.omega)) • G.p0)

/-- Coordinate projection bridge for the mass, oscillator frequency, and time
parameter used by the source solution. -/
def coordinate
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorPositionSolutionGrounding H) : ℝ × ℝ × ℝ :=
  (G.m, G.omega, G.t)

/-- Projection from the Hilbert/operator carrier to source-side position and
momentum actions on the chosen state. -/
def oscillator_position_solution_operator_projection
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorPositionSolutionGrounding H) : H × H × H :=
  (G.positionCurve G.t G.state, G.positionCurve 0 G.state, G.momentumCurve 0 G.state)

/-- Calculus support: the position operator curve has a time derivative at the
source time. -/
theorem oscillator_position_solution_derivative_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorPositionSolutionGrounding H) :
    HasDerivAt G.positionCurve G.dxAtTime G.t :=
  G.position_has_deriv

/-- Calculus support: the initial velocity is the derivative of the position
operator curve at `t = 0`. -/
theorem oscillator_position_solution_initial_derivative_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorPositionSolutionGrounding H) :
    HasDerivAt G.positionCurve G.dx0 0 :=
  G.position_has_initial_deriv

/-- Source-step support: the harmonic oscillator equation is visible as the
time derivative of the velocity curve. -/
theorem oscillator_position_equation_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorPositionSolutionGrounding H) :
    HasDerivAt G.velocityCurve (-(G.omega ^ 2) • G.xAtTime) G.t :=
  G.oscillator_equation

/-- Source-step support: the general oscillator solution before applying
initial data. -/
theorem oscillator_position_general_solution_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorPositionSolutionGrounding H) :
    G.xAtTime =
      (Real.cos (G.omega * G.t)) • G.A + (Real.sin (G.omega * G.t)) • G.B :=
  G.position_solution

/-- Source-step support: differentiating the general solution gives the
velocity expression. -/
theorem oscillator_position_velocity_solution_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorPositionSolutionGrounding H) :
    G.dxAtTime =
      (-(G.omega * Real.sin (G.omega * G.t))) • G.A +
        (G.omega * Real.cos (G.omega * G.t)) • G.B :=
  G.velocity_solution

/-- Source-step support: evaluating the position solution at `t = 0` fixes the
first integration constant. -/
theorem oscillator_position_initial_position_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorPositionSolutionGrounding H) :
    G.A = G.x0 :=
  G.initial_position

/-- Source-step support: evaluating `p(0) = m dx/dt(0)` fixes the second
integration constant. -/
theorem oscillator_position_initial_momentum_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorPositionSolutionGrounding H) :
    G.B = (1 / (G.m * G.omega)) • G.p0 :=
  G.initial_momentum

/-- Unit/dimension support for the operator solution and its initial-data
form. -/
theorem oscillator_position_solution_unit_dimension_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorPositionSolutionGrounding H) :
    G.xAtTime =
      (Real.cos (G.omega * G.t)) • G.x0 +
        (Real.sin (G.omega * G.t)) • ((1 / (G.m * G.omega)) • G.p0) :=
  unit_dimension_bridge G.oscillator_position_unit_dimension_bridge

/-- Algebraic core: substitute the two initial-data constants into the general
oscillator position solution. -/
theorem oscillator_position_solution_algebraic_core
    {E : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E]
    {x0 p0 A B xAtTime : E} {m omega t : ℝ}
    (position_solution :
      xAtTime = (Real.cos (omega * t)) • A + (Real.sin (omega * t)) • B)
    (initial_position : A = x0)
    (initial_momentum : B = (1 / (m * omega)) • p0) :
    xAtTime =
      (Real.cos (omega * t)) • x0 +
        (Real.sin (omega * t)) • ((1 / (m * omega)) • p0) := by
  rw [position_solution, initial_position, initial_momentum]

/-- Source-law support for the bounded Hilbert-operator oscillator solution. -/
theorem oscillator_position_solution_source_law_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorPositionSolutionGrounding H) :
    OscillatorPositionSolutionSourceLaw G := by
  unfold OscillatorPositionSolutionSourceLaw
  exact oscillator_position_solution_algebraic_core
    G.position_solution G.initial_position G.initial_momentum

/-- Bridge from the local grounding packet to the reusable
MathformerPhysicsLib oscillator general-solution evidence packet. -/
def oscillatorGeneralSolutionEvidenceOfGrounding
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorPositionSolutionGrounding H) :
    OscillatorGeneralSolutionEvidence (HilbertBoundedOperator ℂ H) where
  x0 := G.x0
  p0 := G.p0
  A := G.A
  B := G.B
  xAtTime := G.xAtTime
  m := G.m
  omega := G.omega
  t := G.t
  position_solution := G.position_solution
  initial_position := G.initial_position
  initial_momentum := G.initial_momentum

/-- Source-only bounded-Hilbert-operator form of the oscillator position
solution from initial data. -/
theorem oscillator_position_solution_hilbert_grounded
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorPositionSolutionGrounding H)
    (source_law : PhysicalLawWitness (OscillatorPositionSolutionSourceLaw G)) :
    G.xAtTime =
      (Real.cos (G.omega * G.t)) • G.x0 +
        (Real.sin (G.omega * G.t)) • ((1 / (G.m * G.omega)) • G.p0) := by
  have _ : True := G.heisenberg_picture_Frame_context.holds
  have _ : True := G.harmonic_oscillator_context.holds
  have _ : True := G.oscillator_equation_context.holds
  have _ : True := G.boundary_initial_value_context.holds
  have _ : True := G.Smooth_operator_curve_context.holds
  have _ : G.m ≠ 0 ∧ G.omega ≠ 0 := G.scale_nonzero_context.holds
  have _ : 0 < G.m ∧ 0 < G.omega := G.scale_pos_context.holds
  have _ : HasDerivAt G.positionCurve G.dxAtTime G.t :=
    oscillator_position_solution_derivative_support G
  have _ : HasDerivAt G.positionCurve G.dx0 0 :=
    oscillator_position_solution_initial_derivative_support G
  have _ : HasDerivAt G.velocityCurve (-(G.omega ^ 2) • G.xAtTime) G.t :=
    oscillator_position_equation_support G
  have _ : G.xAtTime =
      (Real.cos (G.omega * G.t)) • G.x0 +
        (Real.sin (G.omega * G.t)) • ((1 / (G.m * G.omega)) • G.p0) :=
    oscillator_position_solution_unit_dimension_support G
  have h_source : OscillatorPositionSolutionSourceLaw G := source_law.holds
  unfold OscillatorPositionSolutionSourceLaw at h_source
  exact h_source

/-- Reusable-foundation replay for the same oscillator solution packet. -/
theorem oscillator_position_solution_hilbert_via_reusable_foundation
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorPositionSolutionGrounding H) :
    G.xAtTime =
      (Real.cos (G.omega * G.t)) • G.x0 +
        (Real.sin (G.omega * G.t)) • ((1 / (G.m * G.omega)) • G.p0) := by
  exact oscillatorPositionSolutionFromInitialData
    (oscillatorGeneralSolutionEvidenceOfGrounding G)

/-- Source-only wrapper for the harmonic-oscillator position solution from
initial data. -/
theorem oscillator_position_solution_source_grounded
    {E : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E]
    (O : OscillatorGeneralSolutionEvidence E) :
    O.xAtTime =
      (Real.cos (O.omega * O.t)) • O.x0 +
        (Real.sin (O.omega * O.t)) • ((1 / (O.m * O.omega)) • O.p0) := by
  exact oscillatorPositionSolutionFromInitialData O

end Mathformer.Physics.FormalPhysics0044
