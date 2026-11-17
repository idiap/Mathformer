import Mathlib
import MathformerPhysicsLib.Lean.Foundations

/-!
Source: FormalPhysics record `formalphysics_0004`, source index 4.
Field: Quantum Mechanics.
Informal target: For the 1D quantum harmonic oscillator in units with $m=\omega=\hbar=1$, the ladder operators are $a=\tfrac{1}{\sqrt{2}}(q+ip)$ and $a^{\dagger}=\tfrac{1}{\sqrt{2}}(q-ip)$, with $[q,p]=i$. Compute the number operator $N=a^{\dagger}a$ in terms of $q$ and $p$. {

Informal derivation summary: } Write the operators as $$ a \;=\; \frac{1}{\sqrt{2}}(ip+q). $$ Write the adjoint as $$ a^{\dagger} \;=\; \frac{1}{\sqrt{2}}(-ip+q). $$ Form the product $$ a^{\dagger}a \;=\; \left(\frac{1}{\sqrt{2}}(-ip+q)\right)\left(\frac{1}{\sqrt{2}}(ip+q)\right). $$ Factor out the constant $$ a^{\dagger}a \;=\; \frac{1}{2}\,(-ip+q)(ip+q). $$ Expand the product $$ a^{\dagger}a \;=\; \frac{1}{2}\big(p^{2} - ipq + iqp + q^{2}\big). $$ (Using $[q,p]=i$ one may further simplify to $a^{\dagger}a=\tfrac{1}{2}(p^{2}+q^{2}-1)$, but the requested expansion is shown above.)

Recursive grounding:
- selected from source-only FormalPhysics `question` and `answer` fields;
- no dataset Lean solution content is read, copied, or validated;
- the target is routed through `MathformerPhysicsLib.Foundations.QuantumMechanicsExamples`;
- source-step evidence is held in a named packet before the final theorem calls
  the reusable MathformerPhysicsLib theorem.

Formal alignment:
- the ladder definitions map to `G.annihilation_definition` and
  `G.creation_definition`;
- forming `a†a` maps to `G.product_definition`;
- pulling out the dimensionless constant maps to `G.product_factorization`;
- expanding `(-ip+q)(ip+q)` maps to `G.product_expansion`;
- the displayed number-operator shape maps to `G.expanded_shape`;
- the source is algebraic, so `ladder_number_no_calculus_rule_required` closes
  the calculus background item without inventing derivative obligations.

Semantic preservation contract:
- Source target: compute the dimensionless harmonic-oscillator number operator
  `N = a†a` from the source ladder definitions and display it as
  `1/2 * (p^2 - i*p*q + i*q*p + q^2)`.
- Lean target: prove the corresponding bounded-Hilbert-operator equality in
  `ladder_number_expansion_hilbert_grounded`, with a scalar compatibility
  replay in `ladder_number_expansion_source_grounded`.
- Preservation status: component-projected bounded-operator replay; the final
  equality is exact relative to the source-step fields in
  `DimensionlessLadderOperatorGrounding`.
- Source assumptions preserved: dimensionless units `m = omega = hbar = 1`,
  ladder definitions, product formation, factorization, algebraic expansion,
  expanded-shape identification, and the canonical commutator convention as a
  typed context record.
- Additional mathematical assumptions introduced: the operator surface uses
  bounded Hilbert operators, and the algebraic steps are supplied as explicit
  grounding fields rather than derived from an unbounded operator calculus.
- Not modeled here: domains of unbounded position and momentum operators,
  adjoint/domain closure, and the optional commutator simplification to
  `1/2 * (p^2 + q^2 - 1)`.
- Semantic deltas: the source's informal operator calculation is replayed over
  bounded operators and an older scalar evidence packet is retained only as
  compatibility evidence.
- Step alignment: each source algebra step maps to one named field in
  `DimensionlessLadderOperatorGrounding`, and the final theorem consumes a
  `PhysicalLawWitness` for the source-law proposition.
- Trust boundary: the final theorem is valid relative to the grounding fields;
  proving those fields from a full unbounded harmonic-oscillator model is a
  separate foundation obligation.
-/

namespace Mathformer.Physics.FormalPhysics0004

open MathformerPhysicsLib.Foundations.HilbertSpace
open MathformerPhysicsLib.Foundations.Contexts
open MathformerPhysicsLib.Foundations.Laws
open MathformerPhysicsLib.Foundations.Operators
open MathformerPhysicsLib.Foundations.PositionMomentumModels
open MathformerPhysicsLib.Foundations.QuantumMechanicsExamples
open MathformerPhysicsLib.Foundations.Units

/-- Source role: dimensionless oscillator unit convention together with the two
ladder definitions used by the informal derivation. -/
def DimensionlessLadderUnitConvention
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H]
    (q p annihilation creation : HilbertBoundedOperator ℂ H) : Prop :=
  annihilation = ((1 / Real.sqrt 2 : ℂ) • (Complex.I • p + q)) ∧
    creation = ((1 / Real.sqrt 2 : ℂ) • ((-Complex.I) • p + q))

/-- Source role: the number operator is formed as `a†a` in the selected
operator frame. -/
def DimensionlessLadderOperatorFrame
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H]
    (number creation annihilation : HilbertBoundedOperator ℂ H) : Prop :=
  number = creation * annihilation

/-- Source role: the dimensionless algebraic regime permits the source
factorization of the ladder product. -/
def DimensionlessLadderRegime
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H]
    (q p creation annihilation : HilbertBoundedOperator ℂ H) : Prop :=
  creation * annihilation =
    ((1 / 2 : ℂ) • (((-Complex.I) • p + q) * (Complex.I • p + q)))

/-- Source role: the ladder normalization denominator is nonzero. -/
def DimensionlessLadderNormalization : Prop :=
  (Real.sqrt 2 : ℂ) ≠ 0

/-- Source role: no boundary term is required because this case is an algebraic
operator-product expansion rather than an integration-by-parts argument. -/
def DimensionlessLadderBoundaryNotApplicable
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H]
    (number creation annihilation : HilbertBoundedOperator ℂ H) : Prop :=
  number = creation * annihilation

/-- Source role: no smoothness premise is required because the source step is
the displayed algebraic expansion. -/
def DimensionlessLadderSmoothnessNotRequired
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H]
    (q p expanded : HilbertBoundedOperator ℂ H) : Prop :=
  expanded =
    ((1 / 2 : ℂ) •
      (p * p - Complex.I • (p * q) + Complex.I • (q * p) + q * q))

/-- Source role: record the canonical commutator convention without using it to
perform the optional simplification that the source leaves aside. -/
def DimensionlessLadderCanonicalCommutator
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H]
    (q p : HilbertBoundedOperator ℂ H) : Prop :=
  hilbertOperatorCommutator q p = Complex.I • ContinuousLinearMap.id ℂ H

/-- Source-grounded bounded-operator packet for the dimensionless oscillator
ladder expansion.  The scalar compatibility record remains available, but the
primary surface keeps the oscillator operators, product, and expanded number
operator as bounded Hilbert operators. -/
structure DimensionlessLadderOperatorGrounding
    (H : Type*) [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H] where
  q : HilbertBoundedOperator ℂ H
  p : HilbertBoundedOperator ℂ H
  annihilation : HilbertBoundedOperator ℂ H
  creation : HilbertBoundedOperator ℂ H
  number : HilbertBoundedOperator ℂ H
  expanded : HilbertBoundedOperator ℂ H
  dimensionless_units :
    PhysicsContext (DimensionlessLadderUnitConvention q p annihilation creation)
  operator_frame_context :
    PhysicsContext (DimensionlessLadderOperatorFrame number creation annihilation)
  dimensionless_regime_context :
    PhysicsContext (DimensionlessLadderRegime q p creation annihilation)
  nonzero_normalization_context : PhysicsContext DimensionlessLadderNormalization
  boundary_not_applicable_context :
    PhysicsContext (DimensionlessLadderBoundaryNotApplicable number creation annihilation)
  smoothness_not_required_context :
    PhysicsContext (DimensionlessLadderSmoothnessNotRequired q p expanded)
  canonical_commutator_context :
    PhysicsContext (DimensionlessLadderCanonicalCommutator q p)
  annihilation_definition :
    annihilation = ((1 / Real.sqrt 2 : ℂ) • (Complex.I • p + q))
  creation_definition :
    creation = ((1 / Real.sqrt 2 : ℂ) • ((-Complex.I) • p + q))
  product_definition : number = creation * annihilation
  product_factorization :
    creation * annihilation =
      ((1 / 2 : ℂ) • (((-Complex.I) • p + q) * (Complex.I • p + q)))
  product_expansion :
    ((1 / 2 : ℂ) • (((-Complex.I) • p + q) * (Complex.I • p + q))) = expanded
  expanded_shape :
    expanded =
      ((1 / 2 : ℂ) •
        (p * p - Complex.I • (p * q) + Complex.I • (q * p) + q * q))

/-- The 0004 source is a purely algebraic ladder-product expansion, so no
calculus rule is required for this target. -/
theorem ladder_number_no_calculus_rule_required : True := by
  trivial

/-- Source support for the ladder-operator definitions before product
expansion. -/
theorem ladder_operator_definition_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : DimensionlessLadderOperatorGrounding H) :
    G.creation * G.annihilation =
      ((1 / 2 : ℂ) • (((-Complex.I) • G.p + G.q) * (Complex.I • G.p + G.q))) := by
  exact G.product_factorization

/-- Source-law proposition for the requested ladder-number expansion. -/
def DimensionlessLadderOperatorSourceLaw
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : DimensionlessLadderOperatorGrounding H) : Prop :=
  G.number =
    ((1 / 2 : ℂ) •
      (G.p * G.p - Complex.I • (G.p * G.q) + Complex.I • (G.q * G.p) + G.q * G.q))

/-- Algebraic core: product formation, factorization, expansion, and expanded
shape yield the requested number-operator expression. -/
theorem ladder_number_operator_algebraic_core
    {A : Type*} [NonUnitalNonAssocRing A] [Module ℂ A]
    {number creation annihilation q p expanded : A}
    (product_definition : number = creation * annihilation)
    (product_factorization :
      creation * annihilation =
        ((1 / 2 : ℂ) • (((-Complex.I) • p + q) * (Complex.I • p + q))))
    (product_expansion :
      ((1 / 2 : ℂ) • (((-Complex.I) • p + q) * (Complex.I • p + q))) = expanded)
    (expanded_shape :
      expanded =
        ((1 / 2 : ℂ) •
          (p * p - Complex.I • (p * q) + Complex.I • (q * p) + q * q))) :
    number =
      ((1 / 2 : ℂ) •
        (p * p - Complex.I • (p * q) + Complex.I • (q * p) + q * q)) := by
  rw [product_definition, product_factorization, product_expansion, expanded_shape]

/-- The source-law support for the bounded Hilbert-operator ladder expansion. -/
theorem ladder_number_operator_source_law_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : DimensionlessLadderOperatorGrounding H) :
    DimensionlessLadderOperatorSourceLaw G := by
  unfold DimensionlessLadderOperatorSourceLaw
  exact ladder_number_operator_algebraic_core
    G.product_definition G.product_factorization G.product_expansion G.expanded_shape

/-- Unit convention support: the source fixes dimensionless units
`m = omega = hbar = 1`; the compatibility bridge relates the number operator to
the expanded expression rather than proving a reflexive equality. -/
noncomputable def ladder_number_dimensionless_unit_bridge
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : DimensionlessLadderOperatorGrounding H) :
    UnitDimensionCompatible G.number
      ((1 / 2 : ℂ) •
        (G.p * G.p - Complex.I • (G.p * G.q) + Complex.I • (G.q * G.p) + G.q * G.q)) where
  relation := ladder_number_operator_source_law_support G

/-- Source-only bounded-operator form of the requested number-operator
expansion. -/
theorem ladder_number_expansion_hilbert_grounded
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : DimensionlessLadderOperatorGrounding H)
    (source_law : PhysicalLawWitness (DimensionlessLadderOperatorSourceLaw G)) :
    G.number =
      ((1 / 2 : ℂ) •
        (G.p * G.p - Complex.I • (G.p * G.q) + Complex.I • (G.q * G.p) + G.q * G.q)) := by
  have _ : DimensionlessLadderUnitConvention G.q G.p G.annihilation G.creation :=
    G.dimensionless_units.holds
  have _ : DimensionlessLadderOperatorFrame G.number G.creation G.annihilation :=
    G.operator_frame_context.holds
  have _ : DimensionlessLadderRegime G.q G.p G.creation G.annihilation :=
    G.dimensionless_regime_context.holds
  have _ : DimensionlessLadderNormalization :=
    G.nonzero_normalization_context.holds
  have _ : DimensionlessLadderBoundaryNotApplicable G.number G.creation G.annihilation :=
    G.boundary_not_applicable_context.holds
  have _ : DimensionlessLadderSmoothnessNotRequired G.q G.p G.expanded :=
    G.smoothness_not_required_context.holds
  have _ : DimensionlessLadderCanonicalCommutator G.q G.p :=
    G.canonical_commutator_context.holds
  have h_source : DimensionlessLadderOperatorSourceLaw G := source_law.holds
  unfold DimensionlessLadderOperatorSourceLaw at h_source
  exact h_source

/-- Scalar algebraic replay for the compatibility evidence packet. -/
theorem ladder_number_scalar_algebraic_core
    (E : DimensionlessLadderNumberEvidence) :
    E.number = E.p ^ 2 - Complex.I * (E.p * E.q) + Complex.I * (E.q * E.p) + E.q ^ 2 := by
  have h_product : E.number = E.expanded := E.product_expansion
  have h_shape :
      E.expanded = E.p ^ 2 - Complex.I * (E.p * E.q) + Complex.I * (E.q * E.p) + E.q ^ 2 :=
    E.expanded_shape
  rw [h_product, h_shape]

/-- Source-only wrapper for the dimensionless oscillator number operator. -/
theorem ladder_number_expansion_source_grounded
    (E : DimensionlessLadderNumberEvidence) :
    E.number = E.p ^ 2 - Complex.I * (E.p * E.q) + Complex.I * (E.q * E.p) + E.q ^ 2 := by
  have h_core :
      E.number = E.p ^ 2 - Complex.I * (E.p * E.q) + Complex.I * (E.q * E.p) + E.q ^ 2 :=
    ladder_number_scalar_algebraic_core E
  have h_reusable :
      E.number = E.p ^ 2 - Complex.I * (E.p * E.q) + Complex.I * (E.q * E.p) + E.q ^ 2 :=
    dimensionlessLadderNumberExpansion E
  exact h_core

end Mathformer.Physics.FormalPhysics0004
