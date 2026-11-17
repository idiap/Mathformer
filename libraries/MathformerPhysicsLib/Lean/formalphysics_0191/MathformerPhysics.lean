import Mathlib
import MathformerPhysicsLib.Lean.Foundations

/-!
Source: FormalPhysics record `formalphysics_0191`, source index 191.
Field: Quantum Mechanics.
Informal target: TDSE product differentiation identity.

Informal derivation:
1. Differentiate the TDSE energy expectation with respect to the parameter and
   isolate the Hamiltonian-derivative expectation.
2. Substitute the TDSE expression for the differentiated energy expectation.
3. Substitute the ket-side TDSE inner-product term.
4. Substitute the adjoint-bra TDSE inner-product term.
5. Collect the parameter-time, ket-side, and adjoint-bra terms.

Formal alignment:
- source step 1 is carried by `tdse_product_rule_decomposition`;
- source step 2 is carried by `tdse_energy_derivative_substitution`;
- source step 3 is carried by `tdse_ket_inner_substitution`;
- source step 4 is carried by `tdse_adjoint_bra_substitution`;
- source step 5 is replayed by `tdse_product_identity_core_replay`, then
  exposed as `tdse_product_source_law_support` and
  `tdse_product_unit_dimension_bridge`.

Recursive grounding:
- states live in a Mathlib complex Hilbert space;
- Hamiltonians are `HilbertBoundedOperator` values;
- the Hamiltonian-derivative expectation is `hilbertExpectation`;
- the parameter derivative of `⟪ψ_λ(t), ∂ₜψ_λ(t)⟫` is a `HasDerivAt`
  fact over `schrodingerParameterTimeConnectionCurve`;
- product-rule, ket-TDSE, adjoint-bra-TDSE, and energy-derivative
  substitutions are separate typed frontier fields;
- the TDSE target is routed through
  `MathformerPhysicsLib.Foundations.QuantumMechanicsExamples` alongside the
  Hilbert-space frontier;
- the theorem calls
  `tdseProductDifferentiation`, so the final
  target is not a restated generated law.
-/

namespace Mathformer.Physics.FormalPhysics0191

open MathformerPhysicsLib.Foundations.HilbertSpace
open MathformerPhysicsLib.Foundations.Laws
open MathformerPhysicsLib.Foundations.QuantumDynamics
open MathformerPhysicsLib.Foundations.QuantumMechanicsExamples
open MathformerPhysicsLib.Foundations.Units
open MathformerPhysicsLib.Foundations.Contexts

/-- 0191 core replay: expose the reusable algebra core with the concrete
Hilbert-space terms carried by the frontier. -/
theorem tdse_product_identity_core_replay
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : TimeDependentSchrodingerProductDifferentiationFrontier (H := H)) :
    hilbertExpectation F.dHamiltonian F.psi =
      Complex.I * (F.hbar : ℂ) * F.parameterTimeInnerDerivative -
        Complex.I * (F.hbar : ℂ) * F.lambdaTimeInner +
        Complex.I * (F.hbar : ℂ) * F.timeLambdaInner := by
  exact tdseProductDifferentiationIdentityCore
    (Complex.I * (F.hbar : ℂ))
    (hilbertExpectation F.dHamiltonian F.psi)
    F.parameterEnergyDerivative
    F.parameterTimeInnerDerivative
    (inner ℂ F.dpsi_dlambda (F.hamiltonian F.psi))
    (inner ℂ F.psi (F.hamiltonian F.dpsi_dlambda))
    F.lambdaTimeInner
    F.timeLambdaInner
    F.product_rule_decomposition
    F.energy_derivative_tdse_substitution
    F.ket_tdse_inner_substitution
    F.adjoint_tdse_bra_substitution

/-- 0191 theorem: the TDSE product-differentiation frontier proves
`⟪ψ|∂λH|ψ⟫ = iℏ ∂λ⟪ψ|∂tψ⟫ - iℏ⟪∂λψ|∂tψ⟫ + iℏ⟪∂tψ|∂λψ⟫`. -/
theorem tdse_product_identity
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : TimeDependentSchrodingerProductDifferentiationFrontier (H := H)) :
    hilbertExpectation F.dHamiltonian F.psi =
      Complex.I * (F.hbar : ℂ) * F.parameterTimeInnerDerivative -
        Complex.I * (F.hbar : ℂ) * F.lambdaTimeInner +
        Complex.I * (F.hbar : ℂ) * F.timeLambdaInner := by
  exact tdseProductDifferentiation F

/-- 0191 bridge 1: expose the final TDSE product identity as a law witness. -/
def tdse_product_identity_witness
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : TimeDependentSchrodingerProductDifferentiationFrontier (H := H)) :
    PhysicalLawWitness
      (hilbertExpectation F.dHamiltonian F.psi =
        Complex.I * (F.hbar : ℂ) * F.parameterTimeInnerDerivative -
          Complex.I * (F.hbar : ℂ) * F.lambdaTimeInner +
          Complex.I * (F.hbar : ℂ) * F.timeLambdaInner) :=
  ⟨tdse_product_identity F⟩

/-- 0191 source-law support: expose the TDSE product-differentiation identity
as a named source law backed by the reusable frontier theorem. -/
theorem tdse_product_source_law_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : TimeDependentSchrodingerProductDifferentiationFrontier (H := H)) :
    hilbertExpectation F.dHamiltonian F.psi =
      Complex.I * (F.hbar : ℂ) * F.parameterTimeInnerDerivative -
        Complex.I * (F.hbar : ℂ) * F.lambdaTimeInner +
        Complex.I * (F.hbar : ℂ) * F.timeLambdaInner := by
  exact tdse_product_identity_core_replay F

/-- 0191 unit support: all collected TDSE product-rule terms are energy-scaled
expectation terms matching the Hamiltonian-derivative expectation. -/
def tdse_product_unit_dimension_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : TimeDependentSchrodingerProductDifferentiationFrontier (H := H)) :
    UnitDimensionCompatible
      (hilbertExpectation F.dHamiltonian F.psi)
      (Complex.I * (F.hbar : ℂ) * F.parameterTimeInnerDerivative -
        Complex.I * (F.hbar : ℂ) * F.lambdaTimeInner +
        Complex.I * (F.hbar : ℂ) * F.timeLambdaInner) :=
  ⟨tdse_product_source_law_support F⟩

/-- 0191 unit bridge: recover the TDSE product identity from the explicit
unit/dimension compatibility witness. -/
theorem tdse_product_unit_dimension_bridge
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : TimeDependentSchrodingerProductDifferentiationFrontier (H := H)) :
    hilbertExpectation F.dHamiltonian F.psi =
      Complex.I * (F.hbar : ℂ) * F.parameterTimeInnerDerivative -
        Complex.I * (F.hbar : ℂ) * F.lambdaTimeInner +
        Complex.I * (F.hbar : ℂ) * F.timeLambdaInner := by
  exact unit_dimension_bridge (tdse_product_unit_dimension_support F)

/-- 0191 bridge 2: expose the Mathlib inner-product curve being differentiated. -/
def tdse_parameter_time_connection_curve
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : TimeDependentSchrodingerProductDifferentiationFrontier (H := H)) :
    ℝ → ℂ :=
  schrodingerParameterTimeConnectionCurve F.stateCurve F.timeDerivativeCurve

/-- 0191 bridge 3: expose the derivative of `λ ↦ ⟪ψ_λ(t), ∂ₜψ_λ(t)⟫`. -/
def tdse_parameter_time_connection_derivative
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : TimeDependentSchrodingerProductDifferentiationFrontier (H := H)) :
    PhysicalLawWitness
      (HasDerivAt
        (schrodingerParameterTimeConnectionCurve F.stateCurve F.timeDerivativeCurve)
        F.parameterTimeInnerDerivative F.lambda) :=
  ⟨F.parameter_time_inner_has_deriv⟩

/-- 0191 bridge 4: expose the Hilbert-space product-rule decomposition. -/
def tdse_product_rule_decomposition
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : TimeDependentSchrodingerProductDifferentiationFrontier (H := H)) :
    PhysicalLawWitness
      (F.parameterEnergyDerivative =
        inner ℂ F.dpsi_dlambda (F.hamiltonian F.psi) +
          hilbertExpectation F.dHamiltonian F.psi +
          inner ℂ F.psi (F.hamiltonian F.dpsi_dlambda)) :=
  ⟨F.product_rule_decomposition⟩

/-- 0191 bridge 5: expose the TDSE energy-derivative substitution. -/
def tdse_energy_derivative_substitution
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : TimeDependentSchrodingerProductDifferentiationFrontier (H := H)) :
    PhysicalLawWitness
      (F.parameterEnergyDerivative =
        Complex.I * (F.hbar : ℂ) * F.parameterTimeInnerDerivative) :=
  ⟨F.energy_derivative_tdse_substitution⟩

/-- 0191 bridge 6: expose the ket-side TDSE inner-product substitution. -/
def tdse_ket_inner_substitution
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : TimeDependentSchrodingerProductDifferentiationFrontier (H := H)) :
    PhysicalLawWitness
      (inner ℂ F.dpsi_dlambda (F.hamiltonian F.psi) =
        Complex.I * (F.hbar : ℂ) * F.lambdaTimeInner) :=
  ⟨F.ket_tdse_inner_substitution⟩

/-- 0191 bridge 7: expose the adjoint-bra TDSE inner-product substitution. -/
def tdse_adjoint_bra_substitution
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : TimeDependentSchrodingerProductDifferentiationFrontier (H := H)) :
    PhysicalLawWitness
      (inner ℂ F.psi (F.hamiltonian F.dpsi_dlambda) =
        -(Complex.I * (F.hbar : ℂ)) * F.timeLambdaInner) :=
  ⟨F.adjoint_tdse_bra_substitution⟩

/-- 0191 bridge 8: expose the ket TDSE at the selected parameter. -/
def tdse_ket_law
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : TimeDependentSchrodingerProductDifferentiationFrontier (H := H)) :
    PhysicalLawWitness
      (F.hamiltonian F.psi = (Complex.I * (F.hbar : ℂ)) • F.dpsi_dt) :=
  ⟨F.tdse_ket_at_parameter⟩

/-- 0191 bridge 9: expose the `⟪∂λψ|∂tψ⟫` scalar grounding. -/
def tdse_lambda_time_inner_grounding
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : TimeDependentSchrodingerProductDifferentiationFrontier (H := H)) :
    PhysicalLawWitness (F.lambdaTimeInner = inner ℂ F.dpsi_dlambda F.dpsi_dt) :=
  ⟨F.lambda_time_inner_grounding⟩

/-- 0191 bridge 10: expose the `⟪∂tψ|∂λψ⟫` scalar grounding. -/
def tdse_time_lambda_inner_grounding
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : TimeDependentSchrodingerProductDifferentiationFrontier (H := H)) :
    PhysicalLawWitness (F.timeLambdaInner = inner ℂ F.dpsi_dt F.dpsi_dlambda) :=
  ⟨F.time_lambda_inner_grounding⟩

/-- 0191 bridge 11: expose normalized state evidence. -/
def tdse_product_normalized_state
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : TimeDependentSchrodingerProductDifferentiationFrontier (H := H)) :
    PhysicalLawWitness (NormalizedStateWitness F.psi) :=
  ⟨F.normalized_state⟩

/-- 0191 bridge 12: expose Hamiltonian self-adjointness evidence. -/
def tdse_product_hamiltonian_self_adjoint
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : TimeDependentSchrodingerProductDifferentiationFrontier (H := H)) :
    PhysicalLawWitness (SelfAdjointOperatorWitness F.hamiltonian) :=
  ⟨F.hamiltonian_self_adjoint⟩

/-- 0191 bridge 13: expose the selected state from the parameter curve. -/
def tdse_product_state_at_parameter
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : TimeDependentSchrodingerProductDifferentiationFrontier (H := H)) :
    PhysicalLawWitness (F.stateCurve F.lambda = F.psi) :=
  ⟨F.state_at_parameter⟩

/-- 0191 bridge 14: expose the selected time derivative from its curve. -/
def tdse_product_time_derivative_at_parameter
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : TimeDependentSchrodingerProductDifferentiationFrontier (H := H)) :
    PhysicalLawWitness (F.timeDerivativeCurve F.lambda = F.dpsi_dt) :=
  ⟨F.time_derivative_at_parameter⟩

/-- 0191 bridge 15: expose the selected parameter derivative from its curve. -/
def tdse_product_parameter_derivative_at_parameter
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : TimeDependentSchrodingerProductDifferentiationFrontier (H := H)) :
    PhysicalLawWitness (F.parameterDerivativeCurve F.lambda = F.dpsi_dlambda) :=
  ⟨F.parameter_derivative_at_parameter⟩

/-- 0191 smoothness context: the differentiable parameter-time connection curve
is represented by the Mathlib `HasDerivAt` field. -/
def tdse_product_smoothness_context
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : TimeDependentSchrodingerProductDifferentiationFrontier (H := H)) :
    PhysicsContext
      (HasDerivAt
        (schrodingerParameterTimeConnectionCurve F.stateCurve F.timeDerivativeCurve)
        F.parameterTimeInnerDerivative F.lambda) :=
  ⟨"0191 parameter-time smoothness context", F.parameter_time_inner_has_deriv⟩

/-- 0191 frame context: the source identity is evaluated at the selected
parameter and its selected state/time/parameter derivatives. -/
def tdse_product_parameter_frame_context
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : TimeDependentSchrodingerProductDifferentiationFrontier (H := H)) :
    PhysicsContext
      (F.stateCurve F.lambda = F.psi ∧
        F.timeDerivativeCurve F.lambda = F.dpsi_dt ∧
        F.parameterDerivativeCurve F.lambda = F.dpsi_dlambda) :=
  ⟨"0191 selected parameter Hilbert frame",
    ⟨F.state_at_parameter, F.time_derivative_at_parameter, F.parameter_derivative_at_parameter⟩⟩

/-- 0191 nonzero context: the source TDSE scaling uses nonzero `i`. -/
def tdse_product_nonzero_imaginary_context :
    PhysicsContext (Complex.I ≠ 0) :=
  ⟨"0191 nonzero imaginary TDSE scale", Complex.I_ne_zero⟩

/-- 0191 boundary/domain context: normalized state evidence keeps the source
expectation value inside the intended Hilbert-domain packet. -/
def tdse_product_hilbert_domain_context
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : TimeDependentSchrodingerProductDifferentiationFrontier (H := H)) :
    PhysicsContext (NormalizedStateWitness F.psi) :=
  ⟨"0191 normalized Hilbert expectation domain", F.normalized_state⟩

end Mathformer.Physics.FormalPhysics0191
