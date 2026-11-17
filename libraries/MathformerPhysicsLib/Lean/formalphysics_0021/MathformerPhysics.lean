import Mathlib
import MathformerPhysicsLib.Lean.Foundations

/-!
Source: FormalPhysics record `formalphysics_0021`, source index 21.
Field: Quantum Mechanics.
Informal target: parameter-dependent Hamiltonian expectation value.

Recursive grounding:
- Hamiltonians use `HilbertBoundedOperator`;
- expectation values use `hilbertExpectation`;
- parameter dependence is represented by explicit energy, operator, and state curves;
- the local energy/expectation identity is derived from eigenstate and
  normalization evidence near the parameter;
- the derivative value is derived from a differentiated eigenstate equation,
  self-adjointness, and real-eigenvalue cancellation.
- a generated derivative frontier derives the differentiated eigenstate
  equation from near equality of the action/eigenvalue-side curves and Mathlib
  derivative uniqueness, avoiding a target-shaped differentiated-equation
  assumption at the recursive layer.
- the recursive layer now exposes the action/eigenvalue-side derivative curves,
  spectral-branch tracking, and unbounded-domain obligations for the next
  controlled expansion.
-/


namespace Mathformer.Physics.FormalPhysics0021

open MathformerPhysicsLib.Foundations.HilbertSpace
open MathformerPhysicsLib.Foundations.Laws
open MathformerPhysicsLib.Foundations.Contexts

/-- Dirac-grounded Hamiltonian expectation differentiation bridge. -/
theorem parameter_hamiltonian_expectation_dirac_grounded
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (energy : ℝ → ℂ)
    (hamiltonianCurve : ℝ → HilbertBoundedOperator ℂ H)
    (stateCurve : ℝ → HilbertStateCarrier ℂ H)
    (lambda : ℝ)
    (dHamiltonian : HilbertBoundedOperator ℂ H)
    (stateDerivativeAtLambda : HilbertStateCarrier ℂ H)
    (psi : HilbertStateCarrier ℂ H)
    (dE : ℂ)
    (normalized : NormalizedStateWitness psi)
    (state_at_lambda : stateCurve lambda = psi)
    (near_eigenstate_identity :
      EigenstateExpectationIdentityNear energy hamiltonianCurve stateCurve lambda)
    (eigen_eq_at_lambda :
      ParameterizedEigenstateEquation hamiltonianCurve stateCurve energy lambda)
    (hamiltonian_self_adjoint :
      SelfAdjointOperatorWitness (hamiltonianCurve lambda))
    (eigenvalue_real_at_lambda : star (energy lambda) = energy lambda)
    (differentiated_eigen_eq :
      DifferentiatedEigenstateEquation (hamiltonianCurve lambda) dHamiltonian
        psi stateDerivativeAtLambda (energy lambda) dE)
    (energy_has_deriv : HasDerivAt energy dE lambda) :
    dE = hilbertExpectation dHamiltonian psi := by
  have _ := normalized
  have _ := state_at_lambda
  have _ := energy_has_deriv
  have h_energy_expectation_near :
      energy =ᶠ[nhds lambda]
        (fun mu => parameterizedHilbertExpectation hamiltonianCurve stateCurve mu) :=
    energy_eq_parameterizedExpectation_near_of_eigenstate
      energy hamiltonianCurve stateCurve lambda near_eigenstate_identity
  have _ := h_energy_expectation_near
  have h_eigen_psi : hamiltonianCurve lambda psi = energy lambda • psi := by
    unfold ParameterizedEigenstateEquation at eigen_eq_at_lambda
    rwa [state_at_lambda] at eigen_eq_at_lambda
  have h_hf : dE = hilbertExpectation dHamiltonian psi :=
    hellmannFeynmanDerivativeFromDifferentiatedEigenEquation
      (hamiltonianCurve lambda) dHamiltonian psi stateDerivativeAtLambda
      (energy lambda) dE normalized hamiltonian_self_adjoint h_eigen_psi
      eigenvalue_real_at_lambda differentiated_eigen_eq
  have h_expectation_has_deriv_dE :
      HasDerivAt
        (fun mu => parameterizedHilbertExpectation hamiltonianCurve stateCurve mu)
        dE lambda :=
    energy_has_deriv.congr_of_eventuallyEq h_energy_expectation_near.symm
  have h_expectation_has_deriv :
      HasDerivAt
        (fun mu => parameterizedHilbertExpectation hamiltonianCurve stateCurve mu)
        (hilbertExpectation dHamiltonian psi) lambda := by
    simpa [h_hf] using h_expectation_has_deriv_dE
  exact energyDerivativeEqExpectationDerivative
    energy hamiltonianCurve stateCurve h_energy_expectation_near
    energy_has_deriv h_expectation_has_deriv

/-- 0021 frontier bridge 1: the complete local parameterized-Hamiltonian
packet proves the Hellmann-Feynman expectation value. -/
def parameterized_hamiltonian_expectation
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : ParameterizedHamiltonianDerivativeFrontier (H := H)) :
    PhysicalLawWitness (F.dE = hilbertExpectation F.dHamiltonian F.psi) :=
  ⟨parameterizedHamiltonianDerivativeFrontier_expectation F⟩

/-- 0021 frontier bridge 2: the same packet proves the derivative of the
parameterized expectation curve. -/
def parameterized_hamiltonian_expectation_derivative
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : ParameterizedHamiltonianDerivativeFrontier (H := H)) :
    PhysicalLawWitness
      (HasDerivAt
        (parameterizedHamiltonianExpectationCurve F.hamiltonianCurve F.stateCurve)
        (hilbertExpectation F.dHamiltonian F.psi) F.lambda) :=
  ⟨parameterizedHamiltonianDerivativeFrontier_expectation_has_deriv F⟩

/-- 0021 frontier bridge 3: retrieve the local derivative packet from the
recursive Hamiltonian handoff. -/
def parameterized_hamiltonian_local_derivative_from_recursive_frontier
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (R : ParameterizedHamiltonianRecursiveFrontier (H := H)) :
    ParameterizedHamiltonianDerivativeFrontier (H := H) :=
  R.local_derivative

/-- 0021 frontier bridge 4: the recursive packet preserves the local
Hellmann-Feynman derivative value as explicit evidence. -/
def parameterized_hamiltonian_recursive_expectation_witness
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (R : ParameterizedHamiltonianRecursiveFrontier (H := H)) :
    PhysicalLawWitness
      (R.local_derivative.dE =
        hilbertExpectation R.local_derivative.dHamiltonian R.local_derivative.psi) :=
  ⟨R.local_derivative_ready⟩

/-- 0021 frontier bridge 5: expose smoothness, spectral-projection, and
unbounded-domain obligations for the next recursive expansion. -/
def parameterized_hamiltonian_recursive_frontier_handoff
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (R : ParameterizedHamiltonianRecursiveFrontier (H := H)) :
    PhysicalLawWitness
        (HasDerivAt R.local_derivative.hamiltonianCurve
          R.local_derivative.dHamiltonian R.local_derivative.lambda) ×
      PhysicalLawWitness
        (HasDerivAt R.local_derivative.stateCurve
          R.local_derivative.stateDerivativeAtLambda R.local_derivative.lambda) ×
      ParameterizedHamiltonianSpectralBranchFrontier (H := H) ×
      ParameterizedHamiltonianLocalUnboundedDomainFrontier R.local_derivative :=
  (⟨R.operator_curve_has_deriv⟩, ⟨R.state_curve_has_deriv⟩,
    R.spectral_branch, R.unbounded_domain)

/-- 0021 frontier bridge 6: expose the Mathlib-grounded action curve
`λ ↦ H(λ) ψ(λ)`. -/
noncomputable def parameterized_hamiltonian_action_curve
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : ParameterizedHamiltonianDerivativeFrontier (H := H)) : ℝ → H :=
  parameterizedHamiltonianActionCurve F.hamiltonianCurve F.stateCurve

/-- 0021 frontier bridge 7: expose the eigenvalue-side curve
`λ ↦ E(λ) • ψ(λ)`. -/
noncomputable def parameterized_hamiltonian_eigenvalue_state_curve
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : ParameterizedHamiltonianDerivativeFrontier (H := H)) : ℝ → H :=
  parameterizedEigenvalueStateCurve F.energy F.stateCurve

/-- 0021 frontier bridge 8: recover the differentiated eigenstate equation
from the explicit differentiability frontier. -/
def parameterized_hamiltonian_differentiated_eigen_eq
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (D : ParameterizedHamiltonianDifferentiabilityFrontier (H := H)) :
    PhysicalLawWitness
      (DifferentiatedEigenstateEquation
        (D.local_derivative.hamiltonianCurve D.local_derivative.lambda)
        D.local_derivative.dHamiltonian D.local_derivative.psi
        D.local_derivative.stateDerivativeAtLambda
        (D.local_derivative.energy D.local_derivative.lambda)
        D.local_derivative.dE) :=
  ⟨parameterizedHamiltonianDifferentiabilityFrontier_differentiated_eigen_eq D⟩

/-- 0021 frontier bridge 9: the differentiability frontier preserves the
Hellmann-Feynman expectation value. -/
def parameterized_hamiltonian_differentiability_expectation
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (D : ParameterizedHamiltonianDifferentiabilityFrontier (H := H)) :
    PhysicalLawWitness
      (D.local_derivative.dE =
        hilbertExpectation D.local_derivative.dHamiltonian D.local_derivative.psi) :=
  ⟨parameterizedHamiltonianDifferentiabilityFrontier_expectation D⟩

/-- 0021 frontier bridge 10: expose spectral-branch tracking obligations
without hiding the local derivative proof. -/
def parameterized_hamiltonian_spectral_branch
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (S : ParameterizedHamiltonianSpectralBranchFrontier (H := H)) :
    PhysicalLawWitness
      (S.differentiability.local_derivative.dE =
        hilbertExpectation S.differentiability.local_derivative.dHamiltonian
          S.differentiability.local_derivative.psi) ×
      PhysicalLawWitness
        (∀ᶠ mu in nhds S.differentiability.local_derivative.lambda,
          HilbertProjectionWitness (S.spectralProjection mu)) ×
      PhysicalLawWitness (0 < S.simple_eigenvalue_gap_radius) ×
      PhysicalLawWitness
        (ParameterizedEigenstatePhaseGaugeCondition
          S.differentiability.local_derivative.psi
          S.differentiability.local_derivative.stateDerivativeAtLambda) :=
  (⟨parameterizedHamiltonianSpectralBranchFrontier_expectation S⟩,
    ⟨S.projection_witness_near⟩, ⟨S.simple_eigenvalue_gap_positive⟩,
    ⟨S.phase_gauge_condition⟩)

/-- 0021 frontier bridge 11: final recursive handoff for the parameterized
Hamiltonian sample, naming the unbounded-domain obligations alongside the
checked bounded-core theorem. -/
def parameterized_hamiltonian_fully_grounded_recursive_frontier_handoff
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : ParameterizedHamiltonianFullyGroundedRecursiveFrontier (H := H)) :
    PhysicalLawWitness
      (F.spectral_branch.differentiability.local_derivative.dE =
        hilbertExpectation
          F.spectral_branch.differentiability.local_derivative.dHamiltonian
          F.spectral_branch.differentiability.local_derivative.psi) ×
      ParameterizedHamiltonianLocalUnboundedDomainFrontier
        F.spectral_branch.differentiability.local_derivative :=
  (⟨parameterizedHamiltonianFullyGroundedRecursiveFrontier_expectation F⟩,
    F.unbounded_domain)

/-- 0021 frontier bridge 12: generated derivative packets expose the
near-parameter action/eigenvalue-side curve equality used for differentiation. -/
def parameterized_hamiltonian_action_eq_eigenvalue_near
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : ParameterizedHamiltonianGeneratedDerivativeFrontier (H := H)) :
    PhysicalLawWitness
      (parameterizedHamiltonianActionCurve G.hamiltonianCurve G.stateCurve =ᶠ[nhds G.lambda]
        parameterizedEigenvalueStateCurve G.energy G.stateCurve) :=
  ⟨parameterizedActionCurve_eq_eigenvalueStateCurve_near_of_eigenstate
    G.energy G.hamiltonianCurve G.stateCurve G.lambda G.near_eigenstate_identity⟩

/-- 0021 frontier bridge 13: the generated derivative frontier derives the
differentiated eigen-equation instead of assuming it. -/
def parameterized_hamiltonian_generated_differentiated_eigen_eq
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : ParameterizedHamiltonianGeneratedDerivativeFrontier (H := H)) :
    PhysicalLawWitness
      (DifferentiatedEigenstateEquation (G.hamiltonianCurve G.lambda)
        G.dHamiltonian G.psi G.stateDerivativeAtLambda
        (G.energy G.lambda) G.dE) :=
  ⟨differentiatedEigenstateEquation_of_actionCurve_derivatives
    G.energy G.hamiltonianCurve G.stateCurve G.lambda G.dHamiltonian G.psi
    G.stateDerivativeAtLambda G.dE
    (parameterizedHamiltonianGeneratedDerivativeFrontier_action_eq_eigenvalue_near G)
    G.action_curve_has_deriv G.eigenvalue_state_curve_has_deriv⟩

/-- 0021 frontier bridge 14: expose the generated-frontier helper theorem as a
stable sample API for workflows that do not need the primitive proof inputs. -/
def parameterized_hamiltonian_generated_differentiated_eigen_eq_helper
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : ParameterizedHamiltonianGeneratedDerivativeFrontier (H := H)) :
    PhysicalLawWitness
      (DifferentiatedEigenstateEquation (G.hamiltonianCurve G.lambda)
        G.dHamiltonian G.psi G.stateDerivativeAtLambda
        (G.energy G.lambda) G.dE) :=
  ⟨parameterizedHamiltonianGeneratedDerivativeFrontier_differentiated_eigen_eq G⟩

/-- 0021 frontier bridge 15: generated derivative packets project to the
older local derivative API only after filling the differentiated equation by
the generated theorem. -/
def parameterized_hamiltonian_generated_local_derivative
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : ParameterizedHamiltonianGeneratedDerivativeFrontier (H := H)) :
    ParameterizedHamiltonianDerivativeFrontier (H := H) :=
  G.toDerivativeFrontier

/-- 0021 frontier bridge 16: the generated derivative frontier proves the
Hellmann-Feynman expectation value. -/
def parameterized_hamiltonian_generated_expectation
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : ParameterizedHamiltonianGeneratedDerivativeFrontier (H := H)) :
    PhysicalLawWitness (G.dE = hilbertExpectation G.dHamiltonian G.psi) :=
  ⟨parameterizedHamiltonianGeneratedDerivativeFrontier_expectation G⟩

/-- 0021 frontier bridge 17: the generated derivative frontier proves the
derivative of the parameterized expectation curve. -/
def parameterized_hamiltonian_generated_expectation_derivative
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : ParameterizedHamiltonianGeneratedDerivativeFrontier (H := H)) :
    PhysicalLawWitness
      (HasDerivAt
        (parameterizedHamiltonianExpectationCurve G.hamiltonianCurve G.stateCurve)
        (hilbertExpectation G.dHamiltonian G.psi) G.lambda) :=
  ⟨parameterizedHamiltonianGeneratedDerivativeFrontier_expectation_has_deriv G⟩

/-- 0021 frontier: operator-curve derivative grounding. -/
def parameterized_hamiltonian_operator_curve_derivative
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    PhysicalLawWitness
      (HasDerivAt C.generated.hamiltonianCurve C.generated.dHamiltonian
        C.generated.lambda) :=
  ⟨C.operator_curve_derivative_grounding⟩

/-- 0021 frontier: state-curve derivative grounding. -/
def parameterized_hamiltonian_state_curve_derivative
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    PhysicalLawWitness
      (HasDerivAt C.generated.stateCurve C.generated.stateDerivativeAtLambda
        C.generated.lambda) :=
  ⟨C.state_curve_derivative_grounding⟩

/-- 0021 frontier: energy-curve derivative grounding. -/
def parameterized_hamiltonian_energy_curve_derivative
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    PhysicalLawWitness
      (HasDerivAt C.generated.energy C.generated.dE C.generated.lambda) :=
  ⟨C.energy_curve_derivative_grounding⟩

/-- 0021 frontier: action-curve product-rule grounding. -/
def parameterized_hamiltonian_action_curve_derivative
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    PhysicalLawWitness
      (HasDerivAt
        (parameterizedHamiltonianActionCurve C.generated.hamiltonianCurve
          C.generated.stateCurve)
        (C.generated.dHamiltonian C.generated.psi +
          C.generated.hamiltonianCurve C.generated.lambda
            C.generated.stateDerivativeAtLambda)
        C.generated.lambda) :=
  ⟨C.action_curve_derivative_grounding⟩

/-- 0021 frontier: eigenvalue-side scalar product-rule grounding. -/
def parameterized_hamiltonian_eigenvalue_state_curve_derivative
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    PhysicalLawWitness
      (HasDerivAt
        (parameterizedEigenvalueStateCurve C.generated.energy
          C.generated.stateCurve)
        (C.generated.dE • C.generated.psi +
          C.generated.energy C.generated.lambda •
            C.generated.stateDerivativeAtLambda)
        C.generated.lambda) :=
  ⟨C.eigenvalue_state_curve_derivative_grounding⟩

/-- 0021 frontier: action/eigenvalue-side near equality. -/
def parameterized_hamiltonian_recursive_action_eigenvalue_near
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    PhysicalLawWitness
      (parameterizedHamiltonianActionCurve C.generated.hamiltonianCurve
        C.generated.stateCurve =ᶠ[nhds C.generated.lambda]
          parameterizedEigenvalueStateCurve C.generated.energy
            C.generated.stateCurve) :=
  ⟨C.action_eigenvalue_near_equality⟩

/-- 0021 frontier: generated differentiated equation. -/
def parameterized_hamiltonian_recursive_differentiated_equation
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    PhysicalLawWitness
      (DifferentiatedEigenstateEquation
        (C.generated.hamiltonianCurve C.generated.lambda)
        C.generated.dHamiltonian C.generated.psi
        C.generated.stateDerivativeAtLambda
        (C.generated.energy C.generated.lambda) C.generated.dE) :=
  ⟨C.differentiated_equation_generated⟩

/-- 0021 frontier: generated packet projection into the local API. -/
def parameterized_hamiltonian_generated_local_packet_projection
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    PhysicalLawWitness
      (C.generated_local_packet = C.generated.toDerivativeFrontier) :=
  ⟨C.generated_local_packet_eq⟩

/-- 0021 frontier: structured gauge evidence. -/
def parameterized_hamiltonian_gauge_frontier_from_recursive_expansion
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    ParameterizedHamiltonianGaugeFrontier C.generated :=
  C.gauge_frontier

/-- 0021 frontier: structured spectral projection branch evidence. -/
def parameterized_hamiltonian_spectral_projection_branch_from_recursive_expansion
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    ParameterizedHamiltonianSpectralProjectionBranch C.generated :=
  C.spectral_branch

/-- 0021 frontier: structured unbounded-domain evidence. -/
def parameterized_hamiltonian_unbounded_domain_frontier_from_recursive_expansion
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    ParameterizedHamiltonianUnboundedDomainFrontier C.generated :=
  C.unbounded_domain

/-- 0021 frontier: local Hellmann-Feynman value closure. -/
def parameterized_hamiltonian_local_expectation_closure
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    PhysicalLawWitness
      (C.generated.dE =
        hilbertExpectation C.generated.dHamiltonian C.generated.psi) :=
  ⟨C.local_expectation_value_closed⟩

/-- 0021 frontier: expectation-curve derivative closure. -/
def parameterized_hamiltonian_expectation_derivative_closure
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    PhysicalLawWitness
      (HasDerivAt
        (parameterizedHamiltonianExpectationCurve C.generated.hamiltonianCurve
          C.generated.stateCurve)
        (hilbertExpectation C.generated.dHamiltonian C.generated.psi)
        C.generated.lambda) :=
  ⟨C.expectation_derivative_closed⟩

/-- 0021 frontier: normalization near the target parameter. -/
def parameterized_hamiltonian_normalization_near
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    PhysicalLawWitness
      (∀ᶠ mu in nhds C.generated.lambda,
        NormalizedStateWitness (C.generated.stateCurve mu)) :=
  ⟨C.gauge_frontier.normalization_near_parameter⟩

/-- 0021 frontier: normalization derivative constraint. -/
def parameterized_hamiltonian_normalization_derivative_constraint
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    PhysicalLawWitness
      (ParameterizedStateNormalizationDerivativeConstraint
        C.generated.psi C.generated.stateDerivativeAtLambda) :=
  ⟨C.gauge_frontier.normalization_derivative_constraint⟩

/-- 0021 frontier: phase gauge selection. -/
def parameterized_hamiltonian_phase_gauge_selected
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    PhysicalLawWitness
      (ParameterizedEigenstatePhaseGaugeCondition
        C.generated.psi C.generated.stateDerivativeAtLambda) :=
  ⟨C.gauge_frontier.phase_gauge_selected⟩

/-- 0021 frontier: phase gauge derivative constraint. -/
def parameterized_hamiltonian_phase_gauge_derivative_constraint
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    PhysicalLawWitness
      (HasDerivAt
        (fun mu => inner ℂ (C.generated.stateCurve mu) C.generated.psi)
        0 C.generated.lambda) :=
  ⟨C.gauge_frontier.phase_gauge_derivative_constraint⟩

/-- 0021 frontier: self-adjointness near the parameter. -/
def parameterized_hamiltonian_self_adjointness_near
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    PhysicalLawWitness
      (∀ᶠ mu in nhds C.generated.lambda,
        SelfAdjointOperatorWitness (C.generated.hamiltonianCurve mu)) :=
  ⟨C.self_adjointness_near_parameter⟩

/-- 0021 frontier: real eigenvalue branch near the parameter. -/
def parameterized_hamiltonian_real_eigenvalue_branch
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    PhysicalLawWitness
      (∀ᶠ mu in nhds C.generated.lambda,
        star (C.generated.energy mu) = C.generated.energy mu) :=
  ⟨C.real_eigenvalue_branch_near_parameter⟩

/-- 0021 frontier: spectral projection family selection. -/
def parameterized_hamiltonian_spectral_projection_family
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    ℝ → HilbertBoundedOperator ℂ H :=
  C.spectral_branch.projectionCurve

/-- 0021 frontier: spectral projection self-adjointness. -/
def parameterized_hamiltonian_spectral_projection_self_adjoint
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    PhysicalLawWitness
      (∀ᶠ mu in nhds C.generated.lambda,
        SelfAdjointOperatorWitness (C.spectral_branch.projectionCurve mu)) :=
  ⟨C.spectral_branch.projection_self_adjoint_near⟩

/-- 0021 frontier: spectral projection idempotence. -/
def parameterized_hamiltonian_spectral_projection_idempotent
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    PhysicalLawWitness
      (∀ᶠ mu in nhds C.generated.lambda,
        HilbertProjectionWitness (C.spectral_branch.projectionCurve mu)) :=
  ⟨C.spectral_branch.projection_witness_near⟩

/-- 0021 frontier: spectral projection tracks the state branch. -/
def parameterized_hamiltonian_spectral_projection_tracks_state
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    PhysicalLawWitness
      (∀ᶠ mu in nhds C.generated.lambda,
        C.spectral_branch.projectionCurve mu (C.generated.stateCurve mu) =
          C.generated.stateCurve mu) :=
  ⟨C.spectral_branch.projection_tracks_state_near⟩

/-- 0021 frontier: simple eigenvalue gap tracking. -/
def parameterized_hamiltonian_simple_eigenvalue_gap
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    PhysicalLawWitness (0 < C.spectral_branch.simple_eigenvalue_gap_radius) :=
  ⟨C.spectral_branch.simple_eigenvalue_gap_positive⟩

/-- 0021 frontier: isolated spectral window tracking. -/
def parameterized_hamiltonian_isolated_spectral_window
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    PhysicalLawWitness
      (∀ᶠ mu in nhds C.generated.lambda,
        ∀ z : ℂ, z ∈ C.spectral_branch.spectralWindow →
          z ≠ C.generated.energy mu →
            C.spectral_branch.simple_eigenvalue_gap_radius ≤
              ‖z - C.generated.energy mu‖) :=
  ⟨C.spectral_branch.isolated_spectral_window_near⟩

/-- 0021 frontier: spectral projection differentiability. -/
def parameterized_hamiltonian_spectral_projection_differentiability
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    PhysicalLawWitness
      (HasDerivAt C.spectral_branch.projectionCurve
        C.spectral_branch.dProjection C.generated.lambda) :=
  ⟨C.spectral_branch.spectral_projection_has_deriv⟩

/-- 0021 frontier: eigenvector branch differentiability. -/
def parameterized_hamiltonian_eigenvector_branch_differentiability
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    PhysicalLawWitness
      (HasDerivAt C.generated.stateCurve
        C.generated.stateDerivativeAtLambda C.generated.lambda) :=
  ⟨C.spectral_branch.eigenvector_branch_has_deriv⟩

/-- 0021 frontier: unbounded-operator domain model selection. -/
def parameterized_hamiltonian_unbounded_domain_model
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    ℝ → MathformerPhysicsLib.Foundations.UnboundedOperators.UnboundedHilbertOperator ℂ H :=
  C.unbounded_domain.unboundedHamiltonianCurve

/-- 0021 frontier: common-domain density. -/
def parameterized_hamiltonian_common_domain_density
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    PhysicalLawWitness
      (Dense ((C.unbounded_domain.commonCore : Set H))) :=
  ⟨C.unbounded_domain.common_core_dense⟩

/-- 0021 frontier: Hamiltonian domain stability. -/
def parameterized_hamiltonian_domain_stability
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    PhysicalLawWitness
      (∀ᶠ mu in nhds C.generated.lambda,
        C.unbounded_domain.commonCore ≤
          (C.unbounded_domain.unboundedHamiltonianCurve mu).domain) :=
  ⟨C.unbounded_domain.common_core_in_hamiltonian_domain_near⟩

/-- 0021 frontier: operator-derivative domain stability. -/
def parameterized_hamiltonian_operator_derivative_domain_stability
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    PhysicalLawWitness
      (C.unbounded_domain.commonCore ≤
        C.unbounded_domain.unboundedDerivative.domain) :=
  ⟨C.unbounded_domain.common_core_in_derivative_domain⟩

/-- 0021 frontier: state-branch domain membership. -/
def parameterized_hamiltonian_state_branch_domain_membership
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    PhysicalLawWitness
      (∀ᶠ mu in nhds C.generated.lambda,
        MathformerPhysicsLib.Foundations.UnboundedOperators.MemDomain
          (C.unbounded_domain.unboundedHamiltonianCurve mu)
          (C.generated.stateCurve mu)) :=
  ⟨C.unbounded_domain.state_branch_mem_domain_near⟩

/-- 0021 frontier: unbounded-to-bounded-core completion gate. -/
def parameterized_hamiltonian_unbounded_to_bounded_completion
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    PhysicalLawWitness
      (∀ᶠ mu in nhds C.generated.lambda,
        ∃ hcore : C.unbounded_domain.commonCore ≤
            (C.unbounded_domain.unboundedHamiltonianCurve mu).domain,
          ∀ x : C.unbounded_domain.commonCore,
            MathformerPhysicsLib.Foundations.UnboundedOperators.apply
              (C.unbounded_domain.unboundedHamiltonianCurve mu)
              (x : H) (hcore x.property) =
                C.generated.hamiltonianCurve mu (x : H)) :=
  ⟨C.unbounded_domain.bounded_core_matches_hamiltonian_near⟩

/-- 0021 bridge: the recursive expansion preserves the generated
Hellmann-Feynman value theorem. -/
def parameterized_hamiltonian_recursive_expansion_expectation
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    PhysicalLawWitness
      (C.generated.dE =
        hilbertExpectation C.generated.dHamiltonian C.generated.psi) :=
  ⟨parameterizedHamiltonianRecursiveExpansionFrontier_expectation C⟩

/-- 0021 bridge: the recursive expansion preserves the generated
expectation-curve derivative theorem. -/
def parameterized_hamiltonian_recursive_expansion_expectation_derivative
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    PhysicalLawWitness
      (HasDerivAt
        (parameterizedHamiltonianExpectationCurve C.generated.hamiltonianCurve
          C.generated.stateCurve)
        (hilbertExpectation C.generated.dHamiltonian C.generated.psi)
        C.generated.lambda) :=
  ⟨parameterizedHamiltonianRecursiveExpansionFrontier_expectation_has_deriv C⟩

end Mathformer.Physics.FormalPhysics0021
