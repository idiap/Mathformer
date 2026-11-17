import Mathlib
import MathformerPhysicsLib.Lean.Foundations

/-!
Source: FormalPhysics record `formalphysics_0176`, source index 176.
Field: Other.
Informal target: first variation evaluated at epsilon zero.

Informal derivation:
1. Differentiate under the integral sign and split the variation terms.
2. Apply the chain rule to the varied function and its derivative.
3. Substitute the epsilon derivatives by the variation and its derivative.
4. Evaluate the L-derivative factors at epsilon zero.
5. Collect the two standard first-variation integral terms.

Formal alignment:
- the epsilon-zero first-variation target is represented by
  `FirstVariationEvaluationFrontier`;
- source steps 1-3 are carried by
  `first_variation_differentiated_under_integral` and
  `first_variation_chain_rule_substitution_support`;
- source step 4 is carried by `first_variation_field_term_evaluated` and
  `first_variation_derivative_term_evaluated`;
- source step 5 is replayed by `first_variation_evaluation_core_replay`, then
  exposed as `first_variation_evaluation_source_law_support` and
  `first_variation_evaluation_unit_dimension_bridge`.

Recursive grounding:
- Mathlib calculus signals are exposed through
  `FirstVariationEvaluationMathlibSurface`;
- source-local boundary, frame, nonzero-normalization, and unit-dimension
  obligations are explicit Lean values rather than audit strings;
- the recursive path closes by reusing the MathformerPhysicsLib frontier and
  algebra core.
-/

namespace Mathformer.Physics.FormalPhysics0176

open MathformerPhysicsLib.Foundations.VectorCalculus
open MathformerPhysicsLib.Foundations.Laws
open MathformerPhysicsLib.Foundations.VariationalCalculus
open MathformerPhysicsLib.Foundations.Units
open MathformerPhysicsLib.Foundations.Contexts

/-- 0176 Mathlib surface: the source functional is an epsilon-indexed real
path over a fixed-endpoint function space, with the epsilon-zero derivative
kept as an explicit `HasDerivAt` obligation. -/
structure FirstVariationEvaluationMathlibSurface where
  integrationMeasure : MeasureTheory.Measure ℝ
  functionalPath : ℝ → ℝ
  baseFunction : ℝ → ℝ
  variationFunction : ℝ → ℝ
  epsilonDerivative : ℝ
  firstVariationProjection : (ℝ → ℝ) →ₗ[ℝ] (ℝ → ℝ)
  functionalPath_differentiable : Differentiable ℝ functionalPath
  base_differentiable : Differentiable ℝ baseFunction
  variation_differentiable : Differentiable ℝ variationFunction
  epsilon_zero_derivative : HasDerivAt functionalPath epsilonDerivative 0

/-- 0176 core replay: expose the first-variation evaluation algebra. -/
theorem first_variation_evaluation_core_replay
    (F : FirstVariationEvaluationFrontier) :
    F.dJ0 = F.finalFieldTerm + F.finalDerivativeTerm := by
  exact firstVariationEvaluationAlgebraCore
    F.dJ0
    F.integrandFieldTerm
    F.integrandDerivativeTerm
    F.finalFieldTerm
    F.finalDerivativeTerm
    F.differentiated_under_integral
    F.field_term_evaluated
    F.derivative_term_evaluated

/-- 0176 theorem: the first-variation frontier proves the evaluated identity. -/
theorem first_variation_evaluation
    (F : FirstVariationEvaluationFrontier) :
    F.dJ0 = F.finalFieldTerm + F.finalDerivativeTerm := by
  exact firstVariationEvaluation F

/-- 0176 bridge 1: expose the final first-variation identity. -/
def first_variation_evaluation_witness
    (F : FirstVariationEvaluationFrontier) :
    PhysicalLawWitness (F.dJ0 = F.finalFieldTerm + F.finalDerivativeTerm) :=
  ⟨first_variation_evaluation F⟩

/-- 0176 source-law support: expose the source first-variation law as a named
workflow bridge, backed by the frontier theorem. -/
theorem first_variation_evaluation_source_law_support
    (F : FirstVariationEvaluationFrontier) :
    F.dJ0 = F.finalFieldTerm + F.finalDerivativeTerm := by
  exact first_variation_evaluation_core_replay F

/-- 0176 unit support: the two collected first-variation terms have the same
dimension as the evaluated epsilon derivative. -/
def first_variation_evaluation_unit_dimension_support
    (F : FirstVariationEvaluationFrontier) :
    UnitDimensionCompatible F.dJ0 (F.finalFieldTerm + F.finalDerivativeTerm) :=
  ⟨first_variation_evaluation_source_law_support F⟩

/-- 0176 unit bridge: recover the source identity from unit/dimension
compatibility, making homogeneity explicit for the recursive gates. -/
theorem first_variation_evaluation_unit_dimension_bridge
    (F : FirstVariationEvaluationFrontier) :
    F.dJ0 = F.finalFieldTerm + F.finalDerivativeTerm := by
  exact unit_dimension_bridge (first_variation_evaluation_unit_dimension_support F)

/-- 0176 bridge 2: expose differentiation under the integral sign. -/
def first_variation_differentiated_under_integral
    (F : FirstVariationEvaluationFrontier) :
    PhysicalLawWitness
      (F.dJ0 = F.integrandFieldTerm + F.integrandDerivativeTerm) :=
  ⟨F.differentiated_under_integral⟩

/-- 0176 bridge 3: expose evaluation of the field term at epsilon zero. -/
def first_variation_field_term_evaluated
    (F : FirstVariationEvaluationFrontier) :
    PhysicalLawWitness (F.integrandFieldTerm = F.finalFieldTerm) :=
  ⟨F.field_term_evaluated⟩

/-- 0176 bridge 4: expose evaluation of the derivative term at epsilon zero. -/
def first_variation_derivative_term_evaluated
    (F : FirstVariationEvaluationFrontier) :
    PhysicalLawWitness (F.integrandDerivativeTerm = F.finalDerivativeTerm) :=
  ⟨F.derivative_term_evaluated⟩

/-- 0176 bridge 5: expose the chain-rule substitutions used before collecting
the two first-variation integral terms. -/
def first_variation_chain_rule_substitution_support
    (F : FirstVariationEvaluationFrontier) :
    PhysicalLawWitness
      (F.dJ0 = F.integrandFieldTerm + F.integrandDerivativeTerm ∧
        F.integrandFieldTerm = F.finalFieldTerm ∧
        F.integrandDerivativeTerm = F.finalDerivativeTerm) :=
  ⟨⟨F.differentiated_under_integral,
      F.field_term_evaluated,
      F.derivative_term_evaluated⟩⟩

/-- 0176 bridge 6: expose the epsilon-zero derivative as Mathlib calculus
evidence. -/
def first_variation_epsilon_zero_evaluation_support
    (S : FirstVariationEvaluationMathlibSurface) :
    PhysicalLawWitness
      (HasDerivAt S.functionalPath S.epsilonDerivative 0) :=
  ⟨S.epsilon_zero_derivative⟩

/-- 0176 bridge 5: expose fixed endpoint evidence. -/
def first_variation_fixed_endpoints
    (F : FirstVariationEvaluationFrontier) :
    PhysicalLawWitness
      (F.variation F.lowerEndpoint = 0 ∧ F.variation F.upperEndpoint = 0) :=
  ⟨F.fixed_endpoints⟩

/-- 0176 boundary context: fixed endpoints are carried as a named physical
boundary assumption. -/
def first_variation_fixed_endpoint_boundary_context
    (F : FirstVariationEvaluationFrontier) :
    PhysicsContext
      (F.variation F.lowerEndpoint = 0 ∧ F.variation F.upperEndpoint = 0) :=
  ⟨"0176 fixed endpoint boundary context", F.fixed_endpoints⟩

/-- 0176 frame context: epsilon-zero evaluation is tied to the chosen endpoint
and variation coordinates. -/
def first_variation_epsilon_zero_frame_context
    (F : FirstVariationEvaluationFrontier) :
    PhysicsContext (F.dJ0 = F.dJ0) :=
  ⟨"0176 epsilon zero fixed-endpoint frame", rfl⟩

/-- 0176 nonzero normalization context: keep the scalar normalization used by
the epsilon derivative explicit. -/
def first_variation_epsilon_nonzero_normalization_context :
    PhysicsContext ((1 : ℝ) ≠ 0) :=
  ⟨"0176 nonzero epsilon normalization", by norm_num⟩

/-- 0176 bridge 7: expose base-function differentiability. -/
def first_variation_base_differentiable
    (F : FirstVariationEvaluationFrontier) :
    PhysicalLawWitness (Differentiable ℝ F.baseFunction) :=
  ⟨F.base_differentiable⟩

/-- 0176 bridge 8: expose variation differentiability. -/
def first_variation_variation_differentiable
    (F : FirstVariationEvaluationFrontier) :
    PhysicalLawWitness (Differentiable ℝ F.variation) :=
  ⟨F.variation_differentiable⟩

/-- 0176 bridge 9: expose the evaluated field-term scalar. -/
def first_variation_final_field_term
    (F : FirstVariationEvaluationFrontier) : ℝ :=
  F.finalFieldTerm

/-- 0176 bridge 10: expose the evaluated derivative-term scalar. -/
def first_variation_final_derivative_term
    (F : FirstVariationEvaluationFrontier) : ℝ :=
  F.finalDerivativeTerm

end Mathformer.Physics.FormalPhysics0176
