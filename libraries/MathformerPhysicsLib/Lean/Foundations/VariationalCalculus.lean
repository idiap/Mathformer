-- SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
-- SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
-- SPDX-License-Identifier: MIT
-- Neuro-symbolic AI Group
import MathformerPhysicsLib.Lean.Foundations.Laws
import MathformerPhysicsLib.Lean.Foundations.VectorCalculus

/-
Mathlib grounding: this module exposes stable variational-calculus API names
over frontier evidence records from `Laws` and vector-calculus support from
`VectorCalculus`, reusing Mathlib real scalar algebra and module structure
rather than introducing a separate calculus foundation.
-/
namespace MathformerPhysicsLib
namespace Foundations
namespace VariationalCalculus

open MathformerPhysicsLib.Foundations.VectorCalculus

/-- Mathlib grounding: this facade reuses real functions, differentiability,
and scalar equality packets from `Foundations.VectorCalculus`; it introduces
only stable names for the variation APIs. -/
def variationalCalculusFacadeGrounding : Unit := ()

/-- Reusable evidence packet for the variation chain-rule integral identity. -/
abbrev VariationChainIntegralEvidence := VariationChainIntegralFrontier

/-- Stable API name for the variation chain-rule integral theorem. -/
theorem variationChainIntegral (E : VariationChainIntegralEvidence) :
    E.dJ0 = E.integralFieldTerm + E.integralDerivativeFieldTerm :=
  variationChainIntegral_of_evidence E

/-- Reusable evidence packet for first variation evaluated at epsilon zero. -/
abbrev FirstVariationEvaluationEvidence := FirstVariationEvaluationFrontier

/-- Stable API name for first variation evaluated at epsilon zero. -/
theorem firstVariationEvaluation (E : FirstVariationEvaluationEvidence) :
    E.dJ0 = E.finalFieldTerm + E.finalDerivativeTerm :=
  firstVariationEvaluation_of_evidence E

end VariationalCalculus
end Foundations
end MathformerPhysicsLib
