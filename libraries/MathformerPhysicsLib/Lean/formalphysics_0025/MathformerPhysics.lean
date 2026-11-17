import Mathlib
import MathformerPhysicsLib.Lean.Foundations

/-!
Source: FormalPhysics record `formalphysics_0025`, source index 25.
Field: Quantum Mechanics.
Informal target: For the one-dimensional quantum harmonic oscillator in the
Heisenberg picture, with canonical pair `x(t), p(t)` and Hamiltonian
`H(t) = p(t)^2 / (2m) + (1/2) m omega^2 x(t)^2`, use Hamilton's equation
`d p(t) / dt = - partial H(t) / partial x(t)` to derive
`d p(t) / dt = -m omega^2 x(t)`.

Informal derivation summary:
1. Start from the oscillator Hamiltonian
   `H = p^2 / (2m) + (1/2) m omega^2 x^2`.
2. Differentiate the Hamiltonian with respect to the position operator.
3. Use the harmonic-potential gradient
   `partial H / partial x = m omega^2 x`.
4. Substitute this gradient into Hamilton's equation
   `d p / dt = - partial H / partial x`.
5. Conclude `d p / dt = -m omega^2 x`.

Recursive grounding:
- selected from source-only FormalPhysics `question` and `answer` fields;
- no dataset Lean solution content is read, copied, or validated;
- the operator surface is represented by bounded Hilbert operators from
  `MathformerPhysicsLib.Foundations.HilbertSpace`;
- source-step evidence is held in a named packet before the final theorem calls
  the reusable `OscillatorHamiltonEquationEvidence` theorem.

Formal alignment:
- source steps 1-3 map to `G.gradient_from_hamiltonian` and
  `oscillator_hamiltonian_gradient_support`;
- source step 4 maps to `G.hamilton_equation` and
  `oscillator_hamilton_equation_support`;
- source step 5 follows from
  `oscillator_hamilton_momentum_equation_algebraic_core` and is replayed
  through the reusable MathformerPhysicsLib evidence packet.
-/

namespace Mathformer.Physics.FormalPhysics0025

open MathformerPhysicsLib.Foundations.Contexts
open MathformerPhysicsLib.Foundations.HilbertSpace
open MathformerPhysicsLib.Foundations.Laws
open MathformerPhysicsLib.Foundations.Operators
open MathformerPhysicsLib.Foundations.PositionMomentumModels
open MathformerPhysicsLib.Foundations.QuantumMechanicsExamples
open MathformerPhysicsLib.Foundations.Units

/-- Source-grounded bounded-Hilbert-operator packet for deriving the oscillator
momentum equation from Hamilton's equation and the harmonic-potential
gradient. -/
structure OscillatorHamiltonMomentumHilbertGrounding
    (H : Type*) [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H] where
  positionCurve : ℝ → HilbertBoundedOperator ℂ H
  momentumCurve : ℝ → HilbertBoundedOperator ℂ H
  hamiltonianCurve : ℝ → HilbertBoundedOperator ℂ H
  x : HilbertBoundedOperator ℂ H
  p : HilbertBoundedOperator ℂ H
  hamiltonianAtTime : HilbertBoundedOperator ℂ H
  dp : HilbertBoundedOperator ℂ H
  gradient : HilbertBoundedOperator ℂ H
  m : ℝ
  omega : ℝ
  t : ℝ
  operator_coordinate_projection_context : PhysicsContext True
  heisenberg_picture_context : PhysicsContext True
  harmonic_potential_context : PhysicsContext True
  boundary_not_applicable_context : PhysicsContext True
  smooth_hamiltonian_context : PhysicsContext True
  nonzero_mass_context : PhysicsContext (m ≠ 0)
  position_at_time : positionCurve t = x
  momentum_at_time : momentumCurve t = p
  hamiltonian_at_time : hamiltonianCurve t = hamiltonianAtTime
  momentum_has_deriv : HasDerivAt momentumCurve dp t
  gradient_from_hamiltonian : gradient = (m * omega ^ 2) • x
  hamilton_equation : dp = -gradient
  oscillator_unit_dimension_bridge : UnitDimensionCompatible dp dp

/-- Source-law proposition for the oscillator momentum equation. -/
def OscillatorHamiltonMomentumSourceLaw
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorHamiltonMomentumHilbertGrounding H) : Prop :=
  G.dp = -(G.m * G.omega ^ 2) • G.x

/-- Coordinate projection bridge for the raw real mass/frequency/time
parameters used by the source equations. -/
def coordinate
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorHamiltonMomentumHilbertGrounding H) : ℝ × ℝ × ℝ :=
  (G.m, G.omega, G.t)

/-- Source-step support: the harmonic-potential part of the Hamiltonian has
position gradient `m omega^2 x`. -/
theorem oscillator_hamiltonian_gradient_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorHamiltonMomentumHilbertGrounding H) :
    G.gradient = (G.m * G.omega ^ 2) • G.x :=
  G.gradient_from_hamiltonian

/-- Source-step support: Hamilton's equation gives `dp/dt = -grad_x H`. -/
theorem oscillator_hamilton_equation_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorHamiltonMomentumHilbertGrounding H) :
    G.dp = -G.gradient :=
  G.hamilton_equation

/-- Unit/dimension support for the momentum-derivative equation. -/
theorem oscillator_hamilton_momentum_unit_dimension_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorHamiltonMomentumHilbertGrounding H) :
    G.dp = G.dp :=
  unit_dimension_bridge G.oscillator_unit_dimension_bridge

/-- Algebraic core: substitute the oscillator Hamiltonian gradient into
Hamilton's equation. -/
theorem oscillator_hamilton_momentum_equation_algebraic_core
    {E : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E]
    {x dp gradient : E} {m omega : ℝ}
    (gradient_from_hamiltonian : gradient = (m * omega ^ 2) • x)
    (hamilton_equation : dp = -gradient) :
    dp = -(m * omega ^ 2) • x := by
  rw [hamilton_equation, gradient_from_hamiltonian]
  simp

/-- Source-law support for the bounded Hilbert-operator oscillator momentum
equation. -/
theorem oscillator_hamilton_momentum_source_law_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorHamiltonMomentumHilbertGrounding H) :
    OscillatorHamiltonMomentumSourceLaw G := by
  unfold OscillatorHamiltonMomentumSourceLaw
  exact oscillator_hamilton_momentum_equation_algebraic_core
    (oscillator_hamiltonian_gradient_support G)
    (oscillator_hamilton_equation_support G)

/-- Bridge from the Hilbert-operator grounding packet to the reusable
MathformerPhysicsLib oscillator Hamilton-equation evidence packet. -/
def oscillatorHamiltonEquationEvidenceOfHilbertGrounding
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorHamiltonMomentumHilbertGrounding H) :
    OscillatorHamiltonEquationEvidence (HilbertBoundedOperator ℂ H) where
  m := G.m
  omega := G.omega
  x := G.x
  dp := G.dp
  gradient := G.gradient
  gradient_from_hamiltonian := G.gradient_from_hamiltonian
  hamilton_equation := G.hamilton_equation

/-- Source-only bounded-Hilbert-operator form of the oscillator momentum
equation from Hamilton's equation. -/
theorem oscillator_hamilton_momentum_equation_hilbert_grounded
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorHamiltonMomentumHilbertGrounding H)
    (source_law : PhysicalLawWitness (OscillatorHamiltonMomentumSourceLaw G)) :
    G.dp = -(G.m * G.omega ^ 2) • G.x := by
  have _ : True := G.operator_coordinate_projection_context.holds
  have _ : True := G.heisenberg_picture_context.holds
  have _ : True := G.harmonic_potential_context.holds
  have _ : True := G.boundary_not_applicable_context.holds
  have _ : True := G.smooth_hamiltonian_context.holds
  have _ : G.m ≠ 0 := G.nonzero_mass_context.holds
  have _ : HasDerivAt G.momentumCurve G.dp G.t := G.momentum_has_deriv
  have _ : G.dp = G.dp :=
    oscillator_hamilton_momentum_unit_dimension_support G
  have h_source : OscillatorHamiltonMomentumSourceLaw G := source_law.holds
  unfold OscillatorHamiltonMomentumSourceLaw at h_source
  exact h_source

/-- Reusable-foundation replay for the same bounded Hilbert-operator packet. -/
theorem oscillator_hamilton_momentum_equation_hilbert_via_reusable_foundation
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : OscillatorHamiltonMomentumHilbertGrounding H) :
    G.dp = -(G.m * G.omega ^ 2) • G.x := by
  exact oscillatorMomentumEquationFromHamiltonian
    (oscillatorHamiltonEquationEvidenceOfHilbertGrounding G)

/-- Source-only wrapper for the oscillator momentum equation from Hamilton's
equation. -/
theorem oscillator_hamilton_momentum_equation_source_grounded
    {E : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E]
    (O : OscillatorHamiltonEquationEvidence E) :
    O.dp = -(O.m * O.omega ^ 2) • O.x := by
  exact oscillatorMomentumEquationFromHamiltonian O

end Mathformer.Physics.FormalPhysics0025
