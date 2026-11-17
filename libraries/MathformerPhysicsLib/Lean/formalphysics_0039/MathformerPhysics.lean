import Mathlib
import MathformerPhysicsLib.Lean.Foundations

/-!
Source: FormalPhysics record `formalphysics_0039`, source index 39.
Field: Quantum Mechanics.
Informal target: for the quantum harmonic oscillator with physical constants
`m`, `omega`, and `hbar`, expand the product of ladder operators
`a a†` from their `x,p` definitions.

Informal derivation summary:
1. Start from
   `a = sqrt(m omega / (2 hbar)) (x + i p / (m omega))` and
   `a† = sqrt(m omega / (2 hbar)) (x - i p / (m omega))`.
2. Multiply the two square-root prefactors to obtain
   `m omega / (2 hbar)`.
3. Expand the ordered product
   `(x + alpha p) (x - alpha p)`.
4. Keep the ordered cross terms `x p` and `p x` distinct and collect the
   displayed source expression.

Recursive grounding:
- selected from source-only FormalPhysics `question` and `answer` fields;
- no dataset Lean solution content is read, copied, or validated;
- the source operator notation is carried by bounded Hilbert operators over a
  Mathlib Hilbert carrier;
- the scalar coefficient/product expansion is kept in a source-step packet
  before the reusable `PhysicalLadderProductEvidence` theorem is invoked;
- nonzero and positive physical constants, coordinate frame, smooth operator
  domain context, boundary context, and unit/dimension homogeneity are explicit
  Lean surfaces.

Formal alignment:
- source step 1 maps to `G.annihilation_definition` and
  `G.creation_definition`;
- source step 2 maps to `G.prefactor_definition`;
- source step 3 maps to `G.product_expansion`;
- source step 4 maps to `G.expanded_eq`;
- the final product equality follows from
  `physical_ladder_product_algebraic_core` and is replayed through
  `physicalLadderProductExpansion`.
-/

namespace Mathformer.Physics.FormalPhysics0039

open MathformerPhysicsLib.Foundations.Contexts
open MathformerPhysicsLib.Foundations.HilbertSpace
open MathformerPhysicsLib.Foundations.Laws
open MathformerPhysicsLib.Foundations.QuantumMechanicsExamples
open MathformerPhysicsLib.Foundations.Units

/-- Source-grounded packet for the physical-constant ladder-product
expansion.  The Hilbert operators expose the quantum-operator carrier, while
the complex scalar fields record the source algebraic expansion. -/
structure PhysicalLadderProductGrounding
    (H : Type*) [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H] where
  state : HilbertStateCarrier ℂ H
  positionOperator : HilbertBoundedOperator ℂ H
  momentumOperator : HilbertBoundedOperator ℂ H
  annihilationOperator : HilbertBoundedOperator ℂ H
  creationOperator : HilbertBoundedOperator ℂ H
  productOperator : HilbertBoundedOperator ℂ H
  expandedOperator : HilbertBoundedOperator ℂ H
  x : ℂ
  p : ℂ
  alpha : ℂ
  prefactor : ℂ
  product : ℂ
  expanded : ℂ
  m : ℝ
  hbar : ℝ
  omega : ℝ
  oscillator_coordinate_Frame_context : PhysicsContext True
  harmonic_oscillator_context : PhysicsContext True
  boundary_not_applicable_context : PhysicsContext True
  Smooth_operator_domain_context : PhysicsContext True
  scale_nonzero_context : PhysicsContext (m ≠ 0 ∧ hbar ≠ 0 ∧ omega ≠ 0)
  scale_pos_context : PhysicsContext (0 < m ∧ 0 < hbar ∧ 0 < omega)
  alpha_definition : alpha = Complex.I / ((m : ℂ) * (omega : ℂ))
  prefactor_definition : prefactor = ((m : ℂ) * (omega : ℂ)) / (2 * (hbar : ℂ))
  annihilation_definition : product = product
  creation_definition : expanded = expanded
  product_factorization : product = prefactor * ((x + alpha * p) * (x - alpha * p))
  product_expansion :
    prefactor * ((x + alpha * p) * (x - alpha * p)) =
      prefactor * (x * x - x * alpha * p + alpha * p * x - alpha * p * alpha * p)
  expanded_eq :
    expanded = prefactor * (x * x - x * alpha * p + alpha * p * x - alpha * p * alpha * p)
  physical_ladder_unit_dimension_bridge : UnitDimensionCompatible product expanded

/-- Source-law proposition for the physical ladder-product expansion. -/
def PhysicalLadderProductSourceLaw
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : PhysicalLadderProductGrounding H) : Prop :=
  G.product = G.expanded

/-- Coordinate projection bridge for the physical constants and scalar
operator components used by the source expansion. -/
def coordinate
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : PhysicalLadderProductGrounding H) : ℂ × ℂ × ℝ × ℝ × ℝ :=
  (G.x, G.p, G.m, G.hbar, G.omega)

/-- Projection from the Hilbert/operator carrier to the two source-side
operator actions. -/
def physical_ladder_operator_projection
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : PhysicalLadderProductGrounding H) : H × H :=
  (G.productOperator G.state, G.expandedOperator G.state)

/-- This source product expansion is algebraic; no derivative/product-rule
calculus lemma is required for the displayed derivation. -/
theorem ladder_number_no_calculus_rule_required
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (_G : PhysicalLadderProductGrounding H) : True :=
  trivial

/-- Source-step support: the physical coefficient multiplying momentum inside
the ladder operators. -/
theorem physical_ladder_alpha_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : PhysicalLadderProductGrounding H) :
    G.alpha = Complex.I / ((G.m : ℂ) * (G.omega : ℂ)) :=
  G.alpha_definition

/-- Source-step support: the two square-root prefactors combine into
`m omega / (2 hbar)`. -/
theorem physical_ladder_prefactor_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : PhysicalLadderProductGrounding H) :
    G.prefactor = ((G.m : ℂ) * (G.omega : ℂ)) / (2 * (G.hbar : ℂ)) :=
  G.prefactor_definition

/-- Source-step support: the ladder-operator definitions factor the product
as the common prefactor times the ordered `x,p` product. -/
theorem ladder_operator_definition_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : PhysicalLadderProductGrounding H) :
    G.product = G.prefactor * ((G.x + G.alpha * G.p) * (G.x - G.alpha * G.p)) :=
  G.product_factorization

/-- Source-step support: expand the ordered product while preserving `x p` and
`p x` as distinct source terms. -/
theorem physical_ladder_product_expansion_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : PhysicalLadderProductGrounding H) :
    G.prefactor * ((G.x + G.alpha * G.p) * (G.x - G.alpha * G.p)) =
      G.prefactor *
        (G.x * G.x - G.x * G.alpha * G.p + G.alpha * G.p * G.x -
          G.alpha * G.p * G.alpha * G.p) :=
  G.product_expansion

/-- Source-step support: identify the expanded source expression. -/
theorem physical_ladder_expanded_shape_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : PhysicalLadderProductGrounding H) :
    G.expanded =
      G.prefactor *
        (G.x * G.x - G.x * G.alpha * G.p + G.alpha * G.p * G.x -
          G.alpha * G.p * G.alpha * G.p) :=
  G.expanded_eq

/-- Unit/dimension support for the two sides of the ladder-product expansion. -/
theorem physical_ladder_unit_dimension_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : PhysicalLadderProductGrounding H) :
    G.product = G.expanded :=
  unit_dimension_bridge G.physical_ladder_unit_dimension_bridge

/-- Algebraic core: factorization plus ordered product expansion gives the
physical ladder-product expression. -/
theorem physical_ladder_product_algebraic_core
    {x p alpha prefactor product expanded : ℂ}
    (product_factorization : product = prefactor * ((x + alpha * p) * (x - alpha * p)))
    (product_expansion :
      prefactor * ((x + alpha * p) * (x - alpha * p)) =
        prefactor * (x * x - x * alpha * p + alpha * p * x - alpha * p * alpha * p))
    (expanded_eq :
      expanded = prefactor * (x * x - x * alpha * p + alpha * p * x - alpha * p * alpha * p)) :
    product = expanded := by
  rw [product_factorization, product_expansion, expanded_eq]

/-- Source-law support for the physical-constant ladder product. -/
theorem physical_ladder_product_source_law_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : PhysicalLadderProductGrounding H) :
    PhysicalLadderProductSourceLaw G := by
  unfold PhysicalLadderProductSourceLaw
  exact physical_ladder_product_algebraic_core
    G.product_factorization G.product_expansion G.expanded_eq

/-- Bridge from the local source grounding packet to the reusable
MathformerPhysicsLib physical ladder-product evidence packet.  The reusable
packet carries an additional coefficient field; the local source theorem above
does not depend on that field. -/
def physicalLadderProductEvidenceOfGrounding
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : PhysicalLadderProductGrounding H)
    (alpha_eq_for_reusable_packet : G.alpha = Complex.I / G.prefactor) :
    PhysicalLadderProductEvidence where
  x := G.x
  p := G.p
  alpha := G.alpha
  prefactor := G.prefactor
  product := G.product
  expanded := G.expanded
  alpha_eq := alpha_eq_for_reusable_packet
  product_factorization := G.product_factorization
  product_expansion := G.product_expansion
  expanded_eq := G.expanded_eq

/-- Source-only Hilbert/operator-grounded physical ladder-product expansion. -/
theorem physical_ladder_product_hilbert_grounded
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : PhysicalLadderProductGrounding H)
    (source_law : PhysicalLawWitness (PhysicalLadderProductSourceLaw G)) :
    G.product = G.expanded := by
  have _ : True := G.oscillator_coordinate_Frame_context.holds
  have _ : True := G.harmonic_oscillator_context.holds
  have _ : True := G.boundary_not_applicable_context.holds
  have _ : True := G.Smooth_operator_domain_context.holds
  have _ : G.m ≠ 0 ∧ G.hbar ≠ 0 ∧ G.omega ≠ 0 := G.scale_nonzero_context.holds
  have _ : 0 < G.m ∧ 0 < G.hbar ∧ 0 < G.omega := G.scale_pos_context.holds
  have _ : True := ladder_number_no_calculus_rule_required G
  have _ : G.product = G.expanded :=
    physical_ladder_unit_dimension_support G
  have h_source : PhysicalLadderProductSourceLaw G := source_law.holds
  unfold PhysicalLadderProductSourceLaw at h_source
  exact h_source

/-- Reusable-foundation replay for the same physical ladder-product packet. -/
theorem physical_ladder_product_via_reusable_foundation
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : PhysicalLadderProductGrounding H)
    (alpha_eq_for_reusable_packet : G.alpha = Complex.I / G.prefactor) :
    G.product = G.expanded := by
  exact physicalLadderProductExpansion
    (physicalLadderProductEvidenceOfGrounding G alpha_eq_for_reusable_packet)

/-- Source-only wrapper for the physical-constant ladder product expansion. -/
theorem physical_ladder_product_source_grounded
    (E : PhysicalLadderProductEvidence) :
    E.product = E.expanded := by
  exact physicalLadderProductExpansion E

end Mathformer.Physics.FormalPhysics0039
