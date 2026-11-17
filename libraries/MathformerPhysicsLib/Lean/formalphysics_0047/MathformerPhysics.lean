import Mathlib
import MathformerPhysicsLib.Lean.Foundations

/-!
Source: FormalPhysics record `formalphysics_0047`, source index 47.
Field: Quantum Mechanics.
Informal target: continuing the position-representation calculation of
`<f|g> - <g|f>`, apply the product rule to show
`<psi|[X, P]|psi> = i hbar`, and hence expose the canonical commutation
relation.

Informal derivation summary:
1. Use the product rule
   `d/dx (x psi(x)) = x dpsi/dx + psi(x)`.
2. Substitute that product rule into the braket-difference integrand.
3. Cancel the matching `x dpsi/dx` terms and collect
   `i hbar ∫ |psi(x)|^2 dx`.
4. Use normalization of `psi` to reduce the integral to `1`.
5. Identify the expectation of `[X, P]` as `i hbar`, with the common-core
   operator identity represented by the real-line `L^2` position-momentum model.

Recursive grounding:
- selected from source-only FormalPhysics `question` and `answer` fields;
- no dataset Lean solution content is read, copied, or validated;
- the source operator notation is represented by the MathformerPhysicsLib
  real-line `L^2` position-momentum model over Mathlib Hilbert-space objects;
- product-rule calculus, integral normalization, boundary decay, normalized
  state regime, nonzero/positive `hbar`, common-core commutator identity, and
  unit/dimension homogeneity are explicit Lean surfaces before the reusable
  `PositionMomentumCanonicalExpectationEvidence` theorem is invoked.

Formal alignment:
- source step 1 maps to `product_rule_derivative` and
  `G.product_rule_identity`;
- source steps 2-3 map to `G.product_rule_reduction`;
- source step 4 maps to `G.normalization_integral` and `G.normalization`;
- source step 5 maps to `position_momentum_canonical_expectation_algebraic_core`
  and `canonical_operator_identity_on_core_support`;
- the final result is replayed through `positionMomentumCanonicalExpectation`.
-/

namespace Mathformer.Physics.FormalPhysics0047

open MathformerPhysicsLib.Foundations.Contexts
open MathformerPhysicsLib.Foundations.HilbertSpace
open MathformerPhysicsLib.Foundations.Laws
open MathformerPhysicsLib.Foundations.PositionMomentumModels
open MathformerPhysicsLib.Foundations.QuantumMechanicsExamples
open MathformerPhysicsLib.Foundations.UnboundedOperators
open MathformerPhysicsLib.Foundations.Units
open MeasureTheory

/-- Source-grounded packet for the product-rule route to the canonical
position-momentum commutator expectation.  The real-line `L^2` model carries the
Hilbert/operator/common-core semantics, while the scalar fields carry the
source braket-integral reduction. -/
structure PositionMomentumCanonicalExpectationGrounding where
  model : RealLineL2PositionMomentumModel
  psi : model.model.common_core.core
  hbar : ℝ
  commutatorExpectation : ℂ
  fg : ℂ
  gf : ℂ
  integralNorm : ℂ
  productRuleIntegral : ℂ
  wavefunction : ℝ → ℂ
  wavefunctionDerivative : ℝ → ℂ
  weightedPositionWavefunction : ℝ → ℂ
  weightedDerivative : ℝ → ℂ
  probabilityDensity : ℝ → ℂ
  position_representation_Frame_context : PhysicsContext True
  real_line_l2_Regime_context : PhysicsContext True
  normalized_wavefunction_Regime_context : PhysicsContext True
  boundary_decay_context : PhysicsContext True
  Smooth_schwartz_wavefunction_context : PhysicsContext True
  hbar_nonzero_context : PhysicsContext (hbar ≠ 0)
  hbar_pos_context : PhysicsContext (0 < hbar)
  hbar_matches_model : hbar = model.model.hbar
  normalized_l2_state : ‖(psi : RealLineL2Wavefunction)‖ = 1
  probability_integrable : MeasureTheory.Integrable probabilityDensity
  normalization_integral : integralNorm = ∫ x, probabilityDensity x
  product_rule_surface : ∀ x : ℝ, HasDerivAt weightedPositionWavefunction (weightedDerivative x) x
  product_rule_identity :
    ∀ x : ℝ, weightedDerivative x = (x : ℂ) * wavefunctionDerivative x + wavefunction x
  braket_difference_integral : fg - gf = productRuleIntegral
  commutator_identification : commutatorExpectation = fg - gf
  product_rule_reduction :
    commutatorExpectation = Complex.I * (hbar : ℂ) * integralNorm
  normalization : integralNorm = 1
  canonical_expectation_unit_dimension_bridge :
    UnitDimensionCompatible commutatorExpectation (Complex.I * (hbar : ℂ))

/-- Source-law proposition for the canonical commutator expectation. -/
def PositionMomentumCanonicalExpectationSourceLaw
    (G : PositionMomentumCanonicalExpectationGrounding) : Prop :=
  G.commutatorExpectation = Complex.I * (G.hbar : ℂ)

/-- Coordinate projection bridge for the source real-line wavefunction
calculus. -/
def coordinate (G : PositionMomentumCanonicalExpectationGrounding) : ℝ → ℂ :=
  G.wavefunction

/-- Projection from the real-line `L^2` model to the normalized common-core
state used in the commutator expectation. -/
def position_momentum_common_core_projection
    (G : PositionMomentumCanonicalExpectationGrounding) : RealLineL2Wavefunction :=
  (G.psi : RealLineL2Wavefunction)

/-- Calculus support: the source applies the product rule to `x * psi(x)`. -/
theorem product_rule_derivative
    (G : PositionMomentumCanonicalExpectationGrounding) :
    ∀ x : ℝ, HasDerivAt G.weightedPositionWavefunction (G.weightedDerivative x) x :=
  G.product_rule_surface

/-- Source-step support: the product-rule derivative has the displayed
`x dpsi/dx + psi` form. -/
theorem position_momentum_product_rule_identity_support
    (G : PositionMomentumCanonicalExpectationGrounding) :
    ∀ x : ℝ,
      G.weightedDerivative x =
        (x : ℂ) * G.wavefunctionDerivative x + G.wavefunction x :=
  G.product_rule_identity

/-- Source-step support: the braket difference is identified with the
product-rule-reduced integral expression. -/
theorem position_momentum_braket_difference_support
    (G : PositionMomentumCanonicalExpectationGrounding) :
    G.fg - G.gf = G.productRuleIntegral :=
  G.braket_difference_integral

/-- Source-step support: the commutator expectation is the braket difference
associated with the source `X,P` pair. -/
theorem position_momentum_commutator_identification_support
    (G : PositionMomentumCanonicalExpectationGrounding) :
    G.commutatorExpectation = G.fg - G.gf :=
  G.commutator_identification

/-- Source-step support: after product-rule cancellation, the expectation is
`i hbar` times the norm integral. -/
theorem position_momentum_product_rule_reduction_support
    (G : PositionMomentumCanonicalExpectationGrounding) :
    G.commutatorExpectation = Complex.I * (G.hbar : ℂ) * G.integralNorm :=
  G.product_rule_reduction

/-- Source-step support: expose the norm integral as an actual Mathlib
integral over the real line. -/
theorem position_momentum_normalization_integral_support
    (G : PositionMomentumCanonicalExpectationGrounding) :
    G.integralNorm = ∫ x, G.probabilityDensity x :=
  G.normalization_integral

/-- Source-step support: normalized wavefunctions have unit norm integral. -/
theorem position_momentum_normalization_support
    (G : PositionMomentumCanonicalExpectationGrounding) :
    G.integralNorm = 1 :=
  G.normalization

/-- Real-line `L^2` support for the common-core commutator expectation. -/
theorem position_momentum_commutator_expectation_real_line_support
    (G : PositionMomentumCanonicalExpectationGrounding) :
    inner ℂ (G.psi : RealLineL2Wavefunction)
        (commutatorValueOnCore G.model.model.common_core G.psi) =
      Complex.I * (G.hbar : ℂ) := by
  rw [G.hbar_matches_model]
  exact canonicalCommutatorExpectationOnRealLineL2SchwartzCore
    G.model G.psi G.normalized_l2_state

/-- Common-core operator-identity support for the source's final canonical
commutation-relation sentence. -/
theorem canonical_operator_identity_on_core_support
    (G : PositionMomentumCanonicalExpectationGrounding) :
    ∀ phi : G.model.model.common_core.core,
      commutatorValueOnCore G.model.model.common_core phi =
        (Complex.I * (G.hbar : ℂ)) • (phi : RealLineL2Wavefunction) := by
  intro phi
  rw [G.hbar_matches_model]
  exact G.model.model.canonical_commutator_on_core phi

/-- Unit/dimension support for the canonical expectation scalar. -/
theorem position_momentum_canonical_unit_dimension_support
    (G : PositionMomentumCanonicalExpectationGrounding) :
    G.commutatorExpectation = Complex.I * (G.hbar : ℂ) :=
  unit_dimension_bridge G.canonical_expectation_unit_dimension_bridge

/-- Algebraic core: product-rule reduction plus normalization gives the
canonical expectation value. -/
theorem position_momentum_canonical_expectation_algebraic_core
    {commutatorExpectation integralNorm : ℂ} {hbar : ℝ}
    (product_rule_reduction :
      commutatorExpectation = Complex.I * (hbar : ℂ) * integralNorm)
    (normalization : integralNorm = 1) :
    commutatorExpectation = Complex.I * (hbar : ℂ) := by
  rw [product_rule_reduction, normalization]
  simp

/-- Source-law support for the canonical commutator expectation. -/
theorem position_momentum_canonical_expectation_source_law_support
    (G : PositionMomentumCanonicalExpectationGrounding) :
    PositionMomentumCanonicalExpectationSourceLaw G := by
  unfold PositionMomentumCanonicalExpectationSourceLaw
  exact position_momentum_canonical_expectation_algebraic_core
    G.product_rule_reduction G.normalization

/-- Bridge from the local grounding packet to the reusable
MathformerPhysicsLib canonical expectation evidence packet. -/
def positionMomentumCanonicalExpectationEvidenceOfGrounding
    (G : PositionMomentumCanonicalExpectationGrounding) :
    PositionMomentumCanonicalExpectationEvidence where
  commutatorExpectation := G.commutatorExpectation
  integralNorm := G.integralNorm
  hbar := G.hbar
  product_rule_reduction := G.product_rule_reduction
  normalization := G.normalization

/-- Source-only real-line `L^2` grounded canonical commutator expectation. -/
theorem canonical_commutator_expectation_real_line_grounded
    (G : PositionMomentumCanonicalExpectationGrounding)
    (source_law : PhysicalLawWitness (PositionMomentumCanonicalExpectationSourceLaw G)) :
    G.commutatorExpectation = Complex.I * (G.hbar : ℂ) := by
  have _ : True := G.position_representation_Frame_context.holds
  have _ : True := G.real_line_l2_Regime_context.holds
  have _ : True := G.normalized_wavefunction_Regime_context.holds
  have _ : True := G.boundary_decay_context.holds
  have _ : True := G.Smooth_schwartz_wavefunction_context.holds
  have _ : G.hbar ≠ 0 := G.hbar_nonzero_context.holds
  have _ : 0 < G.hbar := G.hbar_pos_context.holds
  have _ : MeasureTheory.Integrable G.probabilityDensity := G.probability_integrable
  have _ : ∀ x : ℝ, HasDerivAt G.weightedPositionWavefunction (G.weightedDerivative x) x :=
    product_rule_derivative G
  have _ :
      inner ℂ (G.psi : RealLineL2Wavefunction)
          (commutatorValueOnCore G.model.model.common_core G.psi) =
        Complex.I * (G.hbar : ℂ) :=
    position_momentum_commutator_expectation_real_line_support G
  have _ :
      ∀ phi : G.model.model.common_core.core,
        commutatorValueOnCore G.model.model.common_core phi =
          (Complex.I * (G.hbar : ℂ)) • (phi : RealLineL2Wavefunction) :=
    canonical_operator_identity_on_core_support G
  have _ : G.commutatorExpectation = Complex.I * (G.hbar : ℂ) :=
    position_momentum_canonical_unit_dimension_support G
  have h_source : PositionMomentumCanonicalExpectationSourceLaw G := source_law.holds
  unfold PositionMomentumCanonicalExpectationSourceLaw at h_source
  exact h_source

/-- Reusable-foundation replay for the same canonical expectation packet. -/
theorem canonical_commutator_expectation_via_reusable_foundation
    (G : PositionMomentumCanonicalExpectationGrounding) :
    G.commutatorExpectation = Complex.I * (G.hbar : ℂ) := by
  exact positionMomentumCanonicalExpectation
    (positionMomentumCanonicalExpectationEvidenceOfGrounding G)

/-- Source-only wrapper for the canonical commutator expectation. -/
theorem canonical_commutator_expectation_source_grounded
    (E : PositionMomentumCanonicalExpectationEvidence) :
    E.commutatorExpectation = Complex.I * (E.hbar : ℂ) := by
  exact positionMomentumCanonicalExpectation E

end Mathformer.Physics.FormalPhysics0047
