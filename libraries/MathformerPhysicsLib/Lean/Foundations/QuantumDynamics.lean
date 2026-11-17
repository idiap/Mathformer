-- SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
-- SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
-- SPDX-License-Identifier: MIT
-- Neuro-symbolic AI Group
import MathformerPhysicsLib.Lean.Foundations.HilbertSpace
import MathformerPhysicsLib.Lean.Foundations.Laws

/-
Mathlib grounding: this module exposes stable quantum-dynamics API names over
Hilbert-space and law evidence records grounded in Mathlib
`InnerProductSpace`, `CompleteSpace`, complex scalar algebra, and continuous
linear maps. It does not introduce a parallel Hilbert-space hierarchy.
-/
namespace MathformerPhysicsLib
namespace Foundations
namespace QuantumDynamics

open MathformerPhysicsLib.Foundations.HilbertSpace

/-- Mathlib grounding: this facade keeps Hilbert states, bounded operators,
inner products, and differentiability facts in the Mathlib-backed surfaces
defined by `Foundations.HilbertSpace`; it only adds stable theorem names for
downstream autoformalizers. -/
def quantumDynamicsFacadeGrounding : Unit := ()

/-- Reusable evidence packet for the Hellmann-Feynman generated derivative
identity. -/
abbrev HellmannFeynmanDerivativeEvidence {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H] :=
  ParameterizedHamiltonianGeneratedDerivativeFrontier (H := H)

/-- Stable API name for the Hellmann-Feynman expectation identity. -/
theorem hellmannFeynmanDerivative
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (E : HellmannFeynmanDerivativeEvidence (H := H)) :
    E.dE = hilbertExpectation E.dHamiltonian E.psi :=
  parameterizedHamiltonianGeneratedDerivativeFrontier_expectation E

/-- Reusable evidence packet for the TDSE parameter identity. -/
abbrev TDSEParameterIdentityEvidence {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H] :=
  TimeDependentSchrodingerParameterIdentityFrontier (H := H)

/-- Stable API name for the TDSE parameter identity. -/
theorem tdseParameterIdentity
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (E : TDSEParameterIdentityEvidence (H := H)) :
    hilbertExpectation E.dHamiltonian E.psi =
      Complex.I * (E.hbar : ℂ) * E.connectionDerivative :=
  timeDependentSchrodingerParameterIdentity_of_evidence E

/-- Reusable evidence packet for TDSE product differentiation. -/
abbrev TDSEProductDifferentiationEvidence {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H] :=
  TimeDependentSchrodingerProductDifferentiationFrontier (H := H)

/-- Stable API name for the TDSE product-differentiation identity. -/
theorem tdseProductDifferentiation
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (E : TDSEProductDifferentiationEvidence (H := H)) :
    hilbertExpectation E.dHamiltonian E.psi =
      Complex.I * (E.hbar : ℂ) * E.parameterTimeInnerDerivative -
        Complex.I * (E.hbar : ℂ) * E.lambdaTimeInner +
        Complex.I * (E.hbar : ℂ) * E.timeLambdaInner :=
  timeDependentSchrodingerProductDifferentiation_of_evidence E

end QuantumDynamics
end Foundations
end MathformerPhysicsLib
