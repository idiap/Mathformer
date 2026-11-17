import Mathlib
import MathformerPhysicsLib.Lean.Foundations

/-!
Source: FormalPhysics record `formalphysics_0026`, source index 26.
Field: Quantum Mechanics.
Informal target: Hellmann-Feynman theorem for a smooth non-degenerate
parameterized Hamiltonian eigenbranch.

Recursive grounding:
- Hamiltonians are Mathlib continuous linear maps through `HilbertBoundedOperator`;
- state vectors live in a Mathlib complex inner-product space;
- the eigenstate equation, normalization, self-adjointness, and differentiated
  eigen-equation are packaged by `ParameterizedHamiltonianGeneratedDerivativeFrontier`;
- the final identity is the shared MathformerPhysicsLib theorem
  `parameterizedHamiltonianGeneratedDerivativeFrontier_expectation`;
- non-degeneracy, phase-gauge, spectral-projection, and domain-bearing
  obligations are exposed as typed frontiers rather than local placeholders.
-/

namespace Mathformer.Physics.FormalPhysics0026

open MathformerPhysicsLib.Foundations.HilbertSpace
open MathformerPhysicsLib.Foundations.Laws

/-- 0026 theorem: the generated Hellmann-Feynman frontier proves
`dE/dλ = ⟨ψ|dH/dλ|ψ⟩` at the selected parameter. -/
theorem hellmann_feynman_from_generated_frontier
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : ParameterizedHamiltonianGeneratedDerivativeFrontier (H := H)) :
    G.dE = hilbertExpectation G.dHamiltonian G.psi :=
  by
    exact parameterizedHamiltonianGeneratedDerivativeFrontier_expectation G

/-- 0026 bridge 1: expose the Hellmann-Feynman value theorem as a physics-law
witness for downstream autoformalization workflows. -/
def hellmann_feynman_value_witness_from_generated_frontier
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : ParameterizedHamiltonianGeneratedDerivativeFrontier (H := H)) :
    PhysicalLawWitness (G.dE = hilbertExpectation G.dHamiltonian G.psi) :=
  ⟨hellmann_feynman_from_generated_frontier G⟩

/-- 0026 bridge 2: the same frontier proves the derivative of the expectation
curve, not only the scalar value equality. -/
def hellmann_feynman_expectation_derivative_witness_from_generated_frontier
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : ParameterizedHamiltonianGeneratedDerivativeFrontier (H := H)) :
    PhysicalLawWitness
      (HasDerivAt
        (parameterizedHamiltonianExpectationCurve G.hamiltonianCurve G.stateCurve)
        (hilbertExpectation G.dHamiltonian G.psi) G.lambda) :=
  ⟨parameterizedHamiltonianGeneratedDerivativeFrontier_expectation_has_deriv G⟩

/-- 0026 bridge 3: the generated packet can be projected to the older local
derivative API only after the differentiated eigen-equation has been generated. -/
def hellmann_feynman_local_derivative_packet_from_generated_frontier
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : ParameterizedHamiltonianGeneratedDerivativeFrontier (H := H)) :
    ParameterizedHamiltonianDerivativeFrontier (H := H) :=
  G.toDerivativeFrontier

/-- 0026 bridge 4: expose the source eigenstate identity near the parameter as
the equality between action and eigenvalue-side curves. -/
def hellmann_feynman_action_eigenvalue_near_from_generated_frontier
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : ParameterizedHamiltonianGeneratedDerivativeFrontier (H := H)) :
    PhysicalLawWitness
      (parameterizedHamiltonianActionCurve G.hamiltonianCurve G.stateCurve =ᶠ[nhds G.lambda]
        parameterizedEigenvalueStateCurve G.energy G.stateCurve) :=
  ⟨parameterizedHamiltonianGeneratedDerivativeFrontier_action_eq_eigenvalue_near G⟩

/-- 0026 bridge 5: expose the generated differentiated eigenstate equation
that replaces the informal differentiated eigen-equation line. -/
def hellmann_feynman_differentiated_eigen_eq_from_generated_frontier
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : ParameterizedHamiltonianGeneratedDerivativeFrontier (H := H)) :
    PhysicalLawWitness
      (DifferentiatedEigenstateEquation (G.hamiltonianCurve G.lambda)
        G.dHamiltonian G.psi G.stateDerivativeAtLambda
        (G.energy G.lambda) G.dE) :=
  ⟨parameterizedHamiltonianGeneratedDerivativeFrontier_differentiated_eigen_eq G⟩

/-- 0026 bridge 6: retrieve the full recursive expansion packet when the
non-degenerate spectral branch, gauge, and domain obligations are available. -/
def hellmann_feynman_generated_frontier_from_recursive_expansion
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    ParameterizedHamiltonianGeneratedDerivativeFrontier (H := H) :=
  C.generated

/-- 0026 bridge 7: non-degeneracy is represented by the typed spectral branch
with a positive isolated eigenvalue gap. -/
def hellmann_feynman_nondegenerate_spectral_branch_from_recursive_expansion
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    ParameterizedHamiltonianSpectralProjectionBranch C.generated :=
  C.spectral_branch

/-- 0026 bridge 8: expose the positive simple-eigenvalue gap required by the
non-degenerate eigenstate hypothesis. -/
def hellmann_feynman_simple_eigenvalue_gap_from_recursive_expansion
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    PhysicalLawWitness (0 < C.spectral_branch.simple_eigenvalue_gap_radius) :=
  ⟨C.spectral_branch.simple_eigenvalue_gap_positive⟩

/-- 0026 bridge 9: normalization and phase-gauge constraints are exposed as a
typed gauge frontier rather than as unlabeled assumptions. -/
def hellmann_feynman_gauge_frontier_from_recursive_expansion
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    ParameterizedHamiltonianGaugeFrontier C.generated :=
  C.gauge_frontier

/-- 0026 bridge 10: the normalization derivative cancellation used in the
informal proof is represented by an explicit inner-product constraint. -/
def hellmann_feynman_normalization_derivative_constraint_from_recursive_expansion
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    PhysicalLawWitness
      (ParameterizedStateNormalizationDerivativeConstraint
        C.generated.psi C.generated.stateDerivativeAtLambda) :=
  ⟨C.gauge_frontier.normalization_derivative_constraint⟩

/-- 0026 bridge 11: self-adjointness is carried near the selected parameter,
matching the source self-adjoint Hamiltonian hypothesis. -/
def hellmann_feynman_self_adjointness_near_from_recursive_expansion
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    PhysicalLawWitness
      (∀ᶠ mu in nhds C.generated.lambda,
        SelfAdjointOperatorWitness (C.generated.hamiltonianCurve mu)) :=
  ⟨C.self_adjointness_near_parameter⟩

/-- 0026 bridge 12: expose the unbounded-domain frontier needed when the
Hamiltonian is interpreted as a domain-bearing physics operator. -/
def hellmann_feynman_unbounded_domain_frontier_from_recursive_expansion
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    ParameterizedHamiltonianUnboundedDomainFrontier C.generated :=
  C.unbounded_domain

end Mathformer.Physics.FormalPhysics0026
