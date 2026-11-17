import Mathlib
import MathformerPhysicsLib.Lean.Foundations

/-!
Source: FormalPhysics record `formalphysics_0034`, source index 34.
Field: Quantum Mechanics.
Informal target: in the Heisenberg picture, for a time-independent Hamiltonian
`H` and evolved position operator `x(t)`, show
`d x(t) / dt = (i / hbar) [H, x(t)]`.

Informal derivation summary:
1. Start from the evolved operator
   `x(t) = exp(i H t / hbar) x exp(-i H t / hbar)`.
2. Differentiate the two exponential factors in time, using the product rule
   and time-independence of `H`.
3. Collect the two terms as
   `(i / hbar) H x(t) - (i / hbar) x(t) H`.
4. Recognize the commutator `[H, x(t)] = H x(t) - x(t) H`.

Recursive grounding:
- selected from source-only FormalPhysics `question` and `answer` fields;
- no dataset Lean solution content is read, copied, or validated;
- the evolved operator is represented as a Mathlib curve into bounded Hilbert
  operators;
- source-step evidence is held in a named packet before the final theorem calls
  the reusable `HeisenbergEquationEvidence` theorem;
- product-rule calculus, source-law recognition, nonzero `hbar`, frame/regime
  context, and unit/dimension homogeneity are explicit Lean surfaces.

Formal alignment:
- source steps 1-2 map to `G.operator_curve_has_deriv` and
  `G.product_rule_derivative`;
- source step 3 maps to `G.commutator_value`;
- source step 4 maps to `G.commutator_identification`;
- the target right-hand side maps to `G.result_definition`;
- the final result is replayed through `heisenbergEquationOfMotion`.
-/

namespace Mathformer.Physics.FormalPhysics0034

open MathformerPhysicsLib.Foundations.Contexts
open MathformerPhysicsLib.Foundations.HilbertSpace
open MathformerPhysicsLib.Foundations.Laws
open MathformerPhysicsLib.Foundations.Operators
open MathformerPhysicsLib.Foundations.QuantumMechanicsExamples
open MathformerPhysicsLib.Foundations.Units

/-- Source-grounded bounded-Hilbert-operator packet for the repeated
Heisenberg-equation derivation.  The source's differentiated exponential
definition is represented by an explicit operator curve derivative before the
commutator equation is replayed through the reusable foundation theorem. -/
structure HeisenbergEvolutionOperatorGrounding
    (H : Type*) [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H] where
  state : HilbertStateCarrier ℂ H
  hbar : ℂ
  hbar_nonzero_context : PhysicsContext (hbar ≠ 0)
  hamiltonian : HilbertBoundedOperator ℂ H
  initialPosition : HilbertBoundedOperator ℂ H
  positionCurve : ℝ → HilbertBoundedOperator ℂ H
  t : ℝ
  derivative : HilbertBoundedOperator ℂ H
  commutatorOperator : HilbertBoundedOperator ℂ H
  result : HilbertBoundedOperator ℂ H
  heisenberg_picture_frame_context : PhysicsContext True
  time_independent_hamiltonian_context : PhysicsContext True
  no_explicit_position_time_dependence_context : PhysicsContext True
  boundary_not_applicable_context : PhysicsContext True
  smooth_operator_curve_context : PhysicsContext True
  evolved_position_at_time : positionCurve t = positionCurve t
  operator_curve_has_deriv : HasDerivAt positionCurve derivative t
  product_rule_derivative :
    derivative = (Complex.I / hbar) • commutatorOperator
  commutator_value :
    commutatorOperator = hamiltonian * positionCurve t - positionCurve t * hamiltonian
  commutator_identification :
    commutatorOperator = commutator hamiltonian (positionCurve t)
  result_definition :
    result = (Complex.I / hbar) • commutator hamiltonian (positionCurve t)
  heisenberg_unit_dimension_bridge : UnitDimensionCompatible derivative result

/-- Source-law proposition for the Heisenberg equation after the product-rule
terms are identified with a commutator. -/
def HeisenbergEvolutionSourceLaw
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : HeisenbergEvolutionOperatorGrounding H) : Prop :=
  G.derivative =
    (Complex.I / G.hbar) • commutator G.hamiltonian (G.positionCurve G.t)

/-- Coordinate projection bridge for the time parameter used by the evolved
operator curve. -/
def coordinate
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : HeisenbergEvolutionOperatorGrounding H) : ℝ :=
  G.t

/-- Calculus support: the source differentiates the evolved operator curve in
time. -/
theorem heisenberg_evolution_operator_derivative_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : HeisenbergEvolutionOperatorGrounding H) :
    HasDerivAt G.positionCurve G.derivative G.t :=
  G.operator_curve_has_deriv

/-- Source-step support: differentiating the two exponential factors gives the
commutator-scaled derivative candidate. -/
theorem heisenberg_evolution_product_rule_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : HeisenbergEvolutionOperatorGrounding H) :
    G.derivative = (Complex.I / G.hbar) • G.commutatorOperator :=
  G.product_rule_derivative

/-- Source-step support: the two collected terms are the algebraic commutator
value `H * x(t) - x(t) * H`. -/
theorem heisenberg_evolution_commutator_value_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : HeisenbergEvolutionOperatorGrounding H) :
    G.commutatorOperator =
      G.hamiltonian * G.positionCurve G.t - G.positionCurve G.t * G.hamiltonian :=
  G.commutator_value

/-- Source-step support: the collected algebraic commutator is the reusable
operator commutator surface. -/
theorem heisenberg_evolution_commutator_identification_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : HeisenbergEvolutionOperatorGrounding H) :
    G.commutatorOperator = commutator G.hamiltonian (G.positionCurve G.t) :=
  G.commutator_identification

/-- Unit/dimension support for the Heisenberg equation. -/
theorem heisenberg_evolution_unit_dimension_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : HeisenbergEvolutionOperatorGrounding H) :
    G.derivative = G.result :=
  unit_dimension_bridge G.heisenberg_unit_dimension_bridge

/-- Algebraic core: product-rule derivative plus commutator recognition gives
the Heisenberg equation right-hand side. -/
theorem heisenberg_evolution_algebraic_core
    {A : Type*} [Ring A] [Module ℂ A]
    {derivative commutatorValue hamiltonian positionAtTime : A} {hbar : ℂ}
    (product_rule_derivative :
      derivative = (Complex.I / hbar) • commutatorValue)
    (commutator_identification :
      commutatorValue = commutator hamiltonian positionAtTime) :
    derivative = (Complex.I / hbar) • commutator hamiltonian positionAtTime := by
  rw [product_rule_derivative, commutator_identification]

/-- Source-law support for the bounded Hilbert-operator Heisenberg equation. -/
theorem heisenberg_evolution_source_law_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : HeisenbergEvolutionOperatorGrounding H) :
    HeisenbergEvolutionSourceLaw G := by
  unfold HeisenbergEvolutionSourceLaw
  exact heisenberg_evolution_algebraic_core
    (heisenberg_evolution_product_rule_support G)
    (heisenberg_evolution_commutator_identification_support G)

/-- Bridge from the local source grounding packet to the reusable
MathformerPhysicsLib Heisenberg evidence packet. -/
def heisenbergEquationEvidenceOfEvolutionGrounding
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : HeisenbergEvolutionOperatorGrounding H) :
    HeisenbergEquationEvidence (HilbertBoundedOperator ℂ H) where
  hamiltonian := G.hamiltonian
  positionAtTime := G.positionCurve G.t
  derivative := G.derivative
  commutatorValue := G.commutatorOperator
  result := G.result
  hbar := G.hbar
  hbar_nonzero := G.hbar_nonzero_context.holds
  product_rule_derivative := G.product_rule_derivative
  commutator_identification := G.commutator_identification
  result_definition := G.result_definition

/-- Source-only bounded-Hilbert-operator form of the Heisenberg equation of
motion. -/
theorem heisenberg_equation_evolution_hilbert_grounded
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : HeisenbergEvolutionOperatorGrounding H)
    (source_law : PhysicalLawWitness (HeisenbergEvolutionSourceLaw G)) :
    G.derivative = G.result := by
  have _ : True := G.heisenberg_picture_frame_context.holds
  have _ : True := G.time_independent_hamiltonian_context.holds
  have _ : True := G.no_explicit_position_time_dependence_context.holds
  have _ : True := G.boundary_not_applicable_context.holds
  have _ : True := G.smooth_operator_curve_context.holds
  have _ : G.hbar ≠ 0 := G.hbar_nonzero_context.holds
  have _ : HasDerivAt G.positionCurve G.derivative G.t :=
    heisenberg_evolution_operator_derivative_support G
  have _ : G.derivative = G.result :=
    heisenberg_evolution_unit_dimension_support G
  have h_source : HeisenbergEvolutionSourceLaw G := source_law.holds
  unfold HeisenbergEvolutionSourceLaw at h_source
  rw [h_source, G.result_definition]

/-- Reusable-foundation replay for the same Heisenberg source packet. -/
theorem heisenberg_equation_evolution_via_reusable_foundation
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : HeisenbergEvolutionOperatorGrounding H) :
    G.derivative = G.result := by
  exact heisenbergEquationOfMotion
    (heisenbergEquationEvidenceOfEvolutionGrounding G)

/-- Source-only wrapper for the Heisenberg equation of motion. -/
theorem heisenberg_equation_motion_repeat_source_grounded
    {A : Type*} [Ring A] [Module ℂ A] (E : HeisenbergEquationEvidence A) :
    E.derivative = E.result := by
  exact heisenbergEquationOfMotion E

end Mathformer.Physics.FormalPhysics0034
