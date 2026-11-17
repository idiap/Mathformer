import Mathlib
import MathformerPhysicsLib.Lean.Foundations

/-!
Source: FormalPhysics record `formalphysics_0066`, source index 66.
Field: Quantum Mechanics.
Informal target: time-dependent Schrodinger parameter identity.

Recursive grounding:
- state curves live in a Mathlib complex Hilbert space;
- Hamiltonians use `HilbertBoundedOperator`;
- the connection scalar is the Mathlib inner-product curve
  `t ↦ ⟪ψ_λ(t), ∂_λ ψ_λ(t)⟫`;
- the final identity is proved by
  `tdseParameterIdentity`;
- mixed-partial cancellation is an explicit typed field of the frontier rather
  than a hidden generated assumption.
-/

namespace Mathformer.Physics.FormalPhysics0066

open MathformerPhysicsLib.Foundations.HilbertSpace
open MathformerPhysicsLib.Foundations.Laws
open MathformerPhysicsLib.Foundations.QuantumDynamics

/-- 0066 theorem: the time-dependent Schrodinger parameter frontier proves
`⟪ψ|∂λH|ψ⟫ = iℏ ∂t ⟪ψ|∂λψ⟫`. -/
theorem tdse_parameter_identity
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : TimeDependentSchrodingerParameterIdentityFrontier (H := H)) :
    hilbertExpectation F.dHamiltonian F.psi =
      Complex.I * (F.hbar : ℂ) * F.connectionDerivative := by
  exact tdseParameterIdentity F

/-- 0066 bridge 1: expose the final TDSE parameter identity as a physics-law
witness. -/
def tdse_parameter_identity_witness
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : TimeDependentSchrodingerParameterIdentityFrontier (H := H)) :
    PhysicalLawWitness
      (hilbertExpectation F.dHamiltonian F.psi =
        Complex.I * (F.hbar : ℂ) * F.connectionDerivative) :=
  ⟨tdse_parameter_identity F⟩

/-- 0066 bridge 2: expose the Mathlib inner-product connection curve. -/
def tdse_parameter_connection_curve
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : TimeDependentSchrodingerParameterIdentityFrontier (H := H)) :
    ℝ → ℂ :=
  schrodingerParameterConnectionCurve F.stateCurve F.parameterDerivativeCurve

/-- 0066 bridge 3: expose the derivative of the parameter-connection curve. -/
def tdse_parameter_connection_derivative
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : TimeDependentSchrodingerParameterIdentityFrontier (H := H)) :
    PhysicalLawWitness
      (HasDerivAt
        (schrodingerParameterConnectionCurve F.stateCurve F.parameterDerivativeCurve)
        F.connectionDerivative F.time) :=
  ⟨F.connection_has_deriv⟩

/-- 0066 bridge 4: expose the time-dependent Schrodinger equation at the
selected time and parameter. -/
def tdse_law_at_time
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : TimeDependentSchrodingerParameterIdentityFrontier (H := H)) :
    PhysicalLawWitness
      (F.hamiltonian F.psi =
        (Complex.I * (F.hbar : ℂ)) • F.timeDerivativeState) :=
  ⟨F.tdse_at_time⟩

/-- 0066 bridge 5: expose mixed-partial cancellation as its own source-backed
constraint. -/
def tdse_mixed_partial_cancellation
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : TimeDependentSchrodingerParameterIdentityFrontier (H := H)) :
    PhysicalLawWitness (F.mixedPartialLeft = F.mixedPartialRight) :=
  ⟨F.mixed_partials_commute⟩

/-- 0066 bridge 6: expose the differentiated-TDSE balance before cancellation. -/
def tdse_differentiated_balance
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : TimeDependentSchrodingerParameterIdentityFrontier (H := H)) :
    PhysicalLawWitness
      (hilbertExpectation F.dHamiltonian F.psi =
        Complex.I * (F.hbar : ℂ) * F.connectionDerivative +
          F.mixedPartialLeft - F.mixedPartialRight) :=
  ⟨F.differentiated_tdse_balance⟩

/-- 0066 bridge 7: expose the normalized state evidence at the selected time. -/
def tdse_normalized_state
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : TimeDependentSchrodingerParameterIdentityFrontier (H := H)) :
    PhysicalLawWitness (NormalizedStateWitness F.psi) :=
  ⟨F.normalized_state⟩

/-- 0066 bridge 8: expose self-adjointness of the Hamiltonian used by the TDSE. -/
def tdse_hamiltonian_self_adjoint
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : TimeDependentSchrodingerParameterIdentityFrontier (H := H)) :
    PhysicalLawWitness (SelfAdjointOperatorWitness F.hamiltonian) :=
  ⟨F.hamiltonian_self_adjoint⟩

/-- 0066 bridge 9: expose the selected state from the time-dependent curve. -/
def tdse_state_at_time
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : TimeDependentSchrodingerParameterIdentityFrontier (H := H)) :
    PhysicalLawWitness (F.stateCurve F.time = F.psi) :=
  ⟨F.state_at_time⟩

end Mathformer.Physics.FormalPhysics0066
