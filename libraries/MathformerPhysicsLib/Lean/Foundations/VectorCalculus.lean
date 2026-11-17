-- SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
-- SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
-- SPDX-License-Identifier: MIT
-- Neuro-symbolic AI Group
import Mathlib

namespace MathformerPhysicsLib
namespace Foundations
namespace VectorCalculus

/-- Mathlib grounding: vector calculus acts on fields over `EuclideanSpace ℝ (Fin 3)`. -/
abbrev RealVector3 := EuclideanSpace ℝ (Fin 3)

/-- Physics role: a curl-like operator is a reusable field-to-field surface.
It is a bridge until specialized Mathlib vector-calculus APIs are selected. -/
abbrev CurlLikeOperator (X : Type*) := (X → RealVector3) → X → RealVector3

/-- Physics role: time-derivative operators expose regularity obligations separately. -/
abbrev TimeDerivativeOperator (α : Type*) := (ℝ → α) → ℝ → α

/-- Algebra core for the chain-rule form of a varied functional after
differentiation under the integral sign. -/
theorem variationChainIntegralAlgebraCore
    (dJ0 integralDerivativeAtZero integralFieldTerm integralDerivativeFieldTerm : ℝ)
    (differentiate_under_integral :
      dJ0 = integralDerivativeAtZero)
    (chain_rule_integral_substitution :
      integralDerivativeAtZero = integralFieldTerm + integralDerivativeFieldTerm) :
    dJ0 = integralFieldTerm + integralDerivativeFieldTerm := by
  linarith

/-- Frontier 0059-1: typed source evidence for the calculus-of-variations
chain-rule integral identity evaluated at epsilon zero. -/
structure VariationChainIntegralFrontier where
  lowerEndpoint : ℝ
  upperEndpoint : ℝ
  baseFunction : ℝ → ℝ
  variation : ℝ → ℝ
  dJ0 : ℝ
  integralDerivativeAtZero : ℝ
  integralFieldTerm : ℝ
  integralDerivativeFieldTerm : ℝ
  fixed_endpoints :
    variation lowerEndpoint = 0 ∧ variation upperEndpoint = 0
  base_differentiable : Differentiable ℝ baseFunction
  variation_differentiable : Differentiable ℝ variation
  differentiate_under_integral :
    dJ0 = integralDerivativeAtZero
  chain_rule_integral_substitution :
    integralDerivativeAtZero = integralFieldTerm + integralDerivativeFieldTerm

/-- Frontier support: the variation chain-rule frontier proves the evaluated
integral identity. -/
theorem variationChainIntegral_of_evidence
    (F : VariationChainIntegralFrontier) :
    F.dJ0 = F.integralFieldTerm + F.integralDerivativeFieldTerm := by
  exact variationChainIntegralAlgebraCore
    F.dJ0
    F.integralDerivativeAtZero
    F.integralFieldTerm
    F.integralDerivativeFieldTerm
    F.differentiate_under_integral
    F.chain_rule_integral_substitution

/-- Algebra core for evaluating the first variation at epsilon zero after the
two chain-rule terms have been individually evaluated. -/
theorem firstVariationEvaluationAlgebraCore
    (dJ0 integrandFieldTerm integrandDerivativeTerm finalFieldTerm finalDerivativeTerm : ℝ)
    (differentiated_under_integral :
      dJ0 = integrandFieldTerm + integrandDerivativeTerm)
    (field_term_evaluated :
      integrandFieldTerm = finalFieldTerm)
    (derivative_term_evaluated :
      integrandDerivativeTerm = finalDerivativeTerm) :
    dJ0 = finalFieldTerm + finalDerivativeTerm := by
  linarith

/-- Frontier 0176-1: typed source evidence for the first variation evaluated at
epsilon zero. -/
structure FirstVariationEvaluationFrontier where
  lowerEndpoint : ℝ
  upperEndpoint : ℝ
  baseFunction : ℝ → ℝ
  variation : ℝ → ℝ
  dJ0 : ℝ
  integrandFieldTerm : ℝ
  integrandDerivativeTerm : ℝ
  finalFieldTerm : ℝ
  finalDerivativeTerm : ℝ
  fixed_endpoints :
    variation lowerEndpoint = 0 ∧ variation upperEndpoint = 0
  base_differentiable : Differentiable ℝ baseFunction
  variation_differentiable : Differentiable ℝ variation
  differentiated_under_integral :
    dJ0 = integrandFieldTerm + integrandDerivativeTerm
  field_term_evaluated :
    integrandFieldTerm = finalFieldTerm
  derivative_term_evaluated :
    integrandDerivativeTerm = finalDerivativeTerm

/-- Frontier support: the first-variation evaluation frontier proves the
source target after evaluating both chain-rule terms at epsilon zero. -/
theorem firstVariationEvaluation_of_evidence
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

end VectorCalculus
end Foundations
end MathformerPhysicsLib
