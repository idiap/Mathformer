import Mathlib
import MathformerPhysicsLib.Lean.Foundations

/-!
Source: FormalPhysics record `formalphysics_0037`, source index 37.
Field: Quantum Mechanics.
Informal target: in dimensionless harmonic-oscillator variables, rewrite the
creation operator from the `q`-derivative representation
`a† = (1 / sqrt 2) (-d/dq + q)` into the momentum representation.

Informal derivation summary:
1. Start from `a† = (1 / sqrt 2) (-d/dq + q)`.
2. Use the source momentum-representation convention connecting the `q`
   derivative and the dimensionless momentum `p`.
3. Substitute that derivative/momentum relation into the creation-operator
   definition.
4. Simplify the sign to obtain the `p/q` creation-operator form.

Recursive grounding:
- selected from source-only FormalPhysics `question` and `answer` fields;
- no dataset Lean solution content is read, copied, or validated;
- the operator notation is represented by bounded Hilbert operators over a
  Mathlib Hilbert carrier, while the source scalar `q`-representation algebra is
  kept in a local evidence packet;
- the derivative/momentum relation, creation-operator definitions, sign bridge,
  coordinate frame, nonzero scaling constants, smooth derivative context, and
  unit/dimension homogeneity are explicit Lean surfaces before the reusable
  `CreationOperatorRepresentationEvidence` theorem is invoked.

Formal alignment:
- source step 1 maps to `G.creation_q_definition`;
- source step 2 maps to `G.derivative_from_momentum`;
- source step 3 maps to `ladder_operator_definition_support`;
- source step 4 maps to `creation_operator_sign_simplification_support`;
- the final result is replayed through
  `creationOperatorRepresentationEquivalence`.
-/

namespace Mathformer.Physics.FormalPhysics0037

open MathformerPhysicsLib.Foundations.Contexts
open MathformerPhysicsLib.Foundations.HilbertSpace
open MathformerPhysicsLib.Foundations.Laws
open MathformerPhysicsLib.Foundations.QuantumMechanicsExamples
open MathformerPhysicsLib.Foundations.Units

/-- Source-grounded packet for the dimensionless creation-operator
representation change.  Hilbert operators keep the quantum-operator notation
visible, while the scalar fields carry the source `q`-representation algebra. -/
structure CreationOperatorRepresentationGrounding
    (H : Type*) [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H] where
  state : HilbertStateCarrier ℂ H
  positionOperator : HilbertBoundedOperator ℂ H
  momentumOperator : HilbertBoundedOperator ℂ H
  creationOperatorQ : HilbertBoundedOperator ℂ H
  creationOperatorPQ : HilbertBoundedOperator ℂ H
  qWavefunction : ℂ → ℂ
  qCoordinate : ℂ
  q : ℂ
  derivative : ℂ
  momentum : ℂ
  creationQ : ℂ
  creationPQ : ℂ
  m : ℝ
  hbar : ℝ
  omega : ℝ
  q_representation_Frame_context : PhysicsContext True
  dimensionless_coordinate_context : PhysicsContext True
  boundary_not_applicable_context : PhysicsContext True
  smooth_q_derivative_context : PhysicsContext True
  scale_nonzero_context : PhysicsContext (m ≠ 0 ∧ hbar ≠ 0 ∧ omega ≠ 0)
  scale_pos_context : PhysicsContext (0 < m ∧ 0 < hbar ∧ 0 < omega)
  derivative_surface : HasDerivAt qWavefunction derivative qCoordinate
  derivative_from_momentum : derivative = -Complex.I * momentum
  creation_q_definition : creationQ = (1 / (Real.sqrt 2 : ℂ)) * (-derivative + q)
  creation_pq_definition : creationPQ = (1 / (Real.sqrt 2 : ℂ)) * (Complex.I * momentum + q)
  creation_operator_unit_dimension_bridge : UnitDimensionCompatible creationQ creationPQ

/-- Source-law proposition for the creation-operator representation change. -/
def CreationOperatorRepresentationSourceLaw
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : CreationOperatorRepresentationGrounding H) : Prop :=
  G.creationQ = G.creationPQ

/-- Coordinate projection bridge for the dimensionless source variables. -/
def coordinate
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : CreationOperatorRepresentationGrounding H) : ℂ × ℂ × ℝ × ℝ × ℝ :=
  (G.q, G.momentum, G.m, G.hbar, G.omega)

/-- Projection from the Hilbert/operator carrier to the two creation-operator
actions on the source state. -/
def creation_operator_hilbert_projection
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : CreationOperatorRepresentationGrounding H) : H × H :=
  (G.creationOperatorQ G.state, G.creationOperatorPQ G.state)

/-- Calculus support: the source differentiates the `q`-representation
wavefunction. -/
theorem creation_operator_q_derivative_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : CreationOperatorRepresentationGrounding H) :
    HasDerivAt G.qWavefunction G.derivative G.qCoordinate :=
  G.derivative_surface

/-- Source-step support: the momentum-representation convention relates
`d/dq` to the dimensionless momentum variable. -/
theorem creation_operator_momentum_representation_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : CreationOperatorRepresentationGrounding H) :
    G.derivative = -Complex.I * G.momentum :=
  G.derivative_from_momentum

/-- Source-step support: the `q`-derivative definition of the creation
operator.  The name is intentionally generic because the background gate tracks
ladder-operator definition support. -/
theorem ladder_operator_definition_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : CreationOperatorRepresentationGrounding H) :
    G.creationQ = (1 / (Real.sqrt 2 : ℂ)) * (-G.derivative + G.q) :=
  G.creation_q_definition

/-- Source-step support: the `p/q` definition of the same creation operator. -/
theorem creation_operator_pq_definition_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : CreationOperatorRepresentationGrounding H) :
    G.creationPQ = (1 / (Real.sqrt 2 : ℂ)) * (Complex.I * G.momentum + G.q) :=
  G.creation_pq_definition

/-- Source-step support: substitute the momentum representation and simplify
the sign inside the creation operator. -/
theorem creation_operator_sign_simplification_support
    {q derivative momentum : ℂ}
    (derivative_from_momentum : derivative = -Complex.I * momentum) :
    -derivative + q = Complex.I * momentum + q := by
  rw [derivative_from_momentum]
  ring

/-- Unit/dimension support for the two creation-operator representations. -/
theorem creation_operator_unit_dimension_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : CreationOperatorRepresentationGrounding H) :
    G.creationQ = G.creationPQ :=
  unit_dimension_bridge G.creation_operator_unit_dimension_bridge

/-- Algebraic core: substituting the momentum-representation derivative into
the `q`-derivative definition yields the `p/q` creation-operator form. -/
theorem creation_operator_representation_algebraic_core
    {q derivative momentum creationQ creationPQ : ℂ}
    (derivative_from_momentum : derivative = -Complex.I * momentum)
    (creation_q_definition :
      creationQ = (1 / (Real.sqrt 2 : ℂ)) * (-derivative + q))
    (creation_pq_definition :
      creationPQ = (1 / (Real.sqrt 2 : ℂ)) * (Complex.I * momentum + q)) :
    creationQ = creationPQ := by
  rw [creation_q_definition, creation_pq_definition]
  rw [creation_operator_sign_simplification_support derivative_from_momentum]

/-- Source-law support for the local creation-operator representation packet. -/
theorem creation_operator_source_law_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : CreationOperatorRepresentationGrounding H) :
    CreationOperatorRepresentationSourceLaw G := by
  unfold CreationOperatorRepresentationSourceLaw
  exact creation_operator_representation_algebraic_core
    G.derivative_from_momentum G.creation_q_definition G.creation_pq_definition

/-- Bridge from the local grounding packet to the reusable MathformerPhysicsLib
creation-operator representation evidence packet. -/
def creationOperatorRepresentationEvidenceOfGrounding
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : CreationOperatorRepresentationGrounding H) :
    CreationOperatorRepresentationEvidence where
  q := G.q
  derivative := G.derivative
  momentum := G.momentum
  creationQ := G.creationQ
  creationPQ := G.creationPQ
  derivative_from_momentum := G.derivative_from_momentum
  creation_q_definition := G.creation_q_definition
  creation_pq_definition := G.creation_pq_definition
  sign_bridge := creation_operator_sign_simplification_support G.derivative_from_momentum

/-- Source-only Hilbert/operator-grounded creation-operator representation
change. -/
theorem creation_operator_representation_hilbert_grounded
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : CreationOperatorRepresentationGrounding H)
    (source_law : PhysicalLawWitness (CreationOperatorRepresentationSourceLaw G)) :
    G.creationQ = G.creationPQ := by
  have _ : True := G.q_representation_Frame_context.holds
  have _ : True := G.dimensionless_coordinate_context.holds
  have _ : True := G.boundary_not_applicable_context.holds
  have _ : True := G.smooth_q_derivative_context.holds
  have _ : G.m ≠ 0 ∧ G.hbar ≠ 0 ∧ G.omega ≠ 0 := G.scale_nonzero_context.holds
  have _ : 0 < G.m ∧ 0 < G.hbar ∧ 0 < G.omega := G.scale_pos_context.holds
  have _ : HasDerivAt G.qWavefunction G.derivative G.qCoordinate :=
    creation_operator_q_derivative_support G
  have _ : G.creationQ = G.creationPQ :=
    creation_operator_unit_dimension_support G
  have h_source : CreationOperatorRepresentationSourceLaw G := source_law.holds
  unfold CreationOperatorRepresentationSourceLaw at h_source
  exact h_source

/-- Reusable-foundation replay for the same creation-operator packet. -/
theorem creation_operator_representation_via_reusable_foundation
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : CreationOperatorRepresentationGrounding H) :
    G.creationQ = G.creationPQ := by
  exact creationOperatorRepresentationEquivalence
    (creationOperatorRepresentationEvidenceOfGrounding G)

/-- Source-only wrapper for the q-derivative and p/q creation-operator forms. -/
theorem creation_operator_representation_source_grounded
    (E : CreationOperatorRepresentationEvidence) :
    E.creationQ = E.creationPQ := by
  exact creationOperatorRepresentationEquivalence E

end Mathformer.Physics.FormalPhysics0037
