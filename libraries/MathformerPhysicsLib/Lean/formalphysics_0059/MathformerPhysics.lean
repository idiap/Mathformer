import Mathlib
import MathformerPhysicsLib.Lean.Foundations

/-!
Source: FormalPhysics record `formalphysics_0059`, source index 59.
Field: Other.
Informal target: calculus-of-variations chain-rule integral identity.

Recursive grounding:
- the varied functional identity is represented by
  `VariationChainIntegralFrontier`;
- fixed endpoints and differentiability are explicit frontier fields;
- differentiation under the integral and the chain-rule substitution are
  separate source-step equalities;
- the final identity is proved by `variationChainIntegral`.
-/

namespace Mathformer.Physics.FormalPhysics0059

open MathformerPhysicsLib.Foundations.VectorCalculus
open MathformerPhysicsLib.Foundations.Laws
open MathformerPhysicsLib.Foundations.VariationalCalculus

/-- 0059 core replay: expose the reusable variation-chain algebra. -/
theorem variation_chain_integral_core_replay
    (F : VariationChainIntegralFrontier) :
    F.dJ0 = F.integralFieldTerm + F.integralDerivativeFieldTerm := by
  exact variationChainIntegralAlgebraCore
    F.dJ0
    F.integralDerivativeAtZero
    F.integralFieldTerm
    F.integralDerivativeFieldTerm
    F.differentiate_under_integral
    F.chain_rule_integral_substitution

/-- 0059 theorem: the variation chain frontier proves the source identity. -/
theorem variation_chain_integral
    (F : VariationChainIntegralFrontier) :
    F.dJ0 = F.integralFieldTerm + F.integralDerivativeFieldTerm := by
  exact variationChainIntegral F

/-- 0059 bridge 1: expose the final variation-chain identity. -/
def variation_chain_integral_witness
    (F : VariationChainIntegralFrontier) :
    PhysicalLawWitness
      (F.dJ0 = F.integralFieldTerm + F.integralDerivativeFieldTerm) :=
  ⟨variation_chain_integral F⟩

/-- 0059 bridge 2: expose differentiation under the integral sign. -/
def variation_differentiate_under_integral
    (F : VariationChainIntegralFrontier) :
    PhysicalLawWitness (F.dJ0 = F.integralDerivativeAtZero) :=
  ⟨F.differentiate_under_integral⟩

/-- 0059 bridge 3: expose the chain-rule integral substitution. -/
def variation_chain_rule_integral_substitution
    (F : VariationChainIntegralFrontier) :
    PhysicalLawWitness
      (F.integralDerivativeAtZero =
        F.integralFieldTerm + F.integralDerivativeFieldTerm) :=
  ⟨F.chain_rule_integral_substitution⟩

/-- 0059 bridge 4: expose fixed endpoint evidence. -/
def variation_fixed_endpoints
    (F : VariationChainIntegralFrontier) :
    PhysicalLawWitness
      (F.variation F.lowerEndpoint = 0 ∧ F.variation F.upperEndpoint = 0) :=
  ⟨F.fixed_endpoints⟩

/-- 0059 bridge 5: expose base-function differentiability. -/
def variation_base_differentiable
    (F : VariationChainIntegralFrontier) :
    PhysicalLawWitness (Differentiable ℝ F.baseFunction) :=
  ⟨F.base_differentiable⟩

/-- 0059 bridge 6: expose variation differentiability. -/
def variation_variation_differentiable
    (F : VariationChainIntegralFrontier) :
    PhysicalLawWitness (Differentiable ℝ F.variation) :=
  ⟨F.variation_differentiable⟩

/-- 0059 bridge 7: expose the field-term integral scalar. -/
def variation_integral_field_term
    (F : VariationChainIntegralFrontier) : ℝ :=
  F.integralFieldTerm

/-- 0059 bridge 8: expose the derivative-field-term integral scalar. -/
def variation_integral_derivative_field_term
    (F : VariationChainIntegralFrontier) : ℝ :=
  F.integralDerivativeFieldTerm

end Mathformer.Physics.FormalPhysics0059
