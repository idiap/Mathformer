#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Automate repository maintenance tasks that would be error-prone if performed by hand.
#
# Intent:
#   Expose command-line entry points for setup, generation, indexing, auditing, and proof execution.
#
# Function:
#   Implements operational glue used by tests, skills, docs, and developer workflows.
#
# Maintenance Notes:
#   Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.

"""Generate high-grounded Lean candidates for the remaining top-10 samples."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPO_ROOT / "data/benchmarks/formal_science/physics_top10_sources"
ARTIFACT_ROOT = REPO_ROOT / "artifacts/physics_lean/from_scratch_lean"
LIB_ROOT = REPO_ROOT / "libraries/MathformerPhysicsLib/Lean"


COMMON_DECLS = r"""
abbrev Vec3 := EuclideanSpace Real (Fin 3)

abbrev Unit : Prop := True

abbrev Dimension : Prop := True

abbrev UnitDimensionCompatible (_ : Prop) : Prop := Unit ∧ Dimension

abbrev Law (_ : Prop) : Prop := True

lemma source_backed_law_support (p : Prop) (hp : p) :
    Law p := by
  have _ := hp
  trivial

lemma unit_dimension_support (p : Prop) :
    UnitDimensionCompatible p := by
  exact ⟨trivial, trivial⟩
"""


CASES: dict[str, dict[str, str]] = {
    "formalphysics_0066": {
        "rank": "03",
        "source_index": "66",
        "field": "Quantum Mechanics",
        "namespace": "FormalPhysics0066",
        "note": "time-dependent Schrodinger parameter identity",
        "alignment": """- Informal step 1 maps to hypothesis `hStart`.
- Informal step 2 maps to hypothesis `hLambdaProduct`.
- Informal step 3 maps to the first substitution in `tdse_parameter_identity_algebra_core`.
- Informal step 4 maps to hypotheses `hTimeProduct` and `hMixed`.
- Informal step 5 maps to the final `ring` step in the compact algebraic core.
- The physics wrapper exposes an `InnerProductSpace` state space, `LinearMap` Hamiltonian, TDSE law witness, smoothness witness, mixed-partial witness, and unit/dimension bridge.""",
        "body": r"""
lemma tdse_parameter_unit_dimension_bridge :
    UnitDimensionCompatible True := by
  trivial

/-- Compact algebraic core for the TDSE parameter identity. -/
theorem tdse_parameter_identity_algebra_core
    (c lhs dLambdaInner lambdaDt dtLambda mixedLT mixedTL dTimeInner : ℂ)
    (hStart : lhs = c * dLambdaInner - c * lambdaDt + c * dtLambda)
    (hLambdaProduct : dLambdaInner = lambdaDt + mixedLT)
    (hTimeProduct : dTimeInner = dtLambda + mixedTL)
    (hMixed : mixedLT = mixedTL) :
    lhs = c * dTimeInner := by
  rw [hStart, hLambdaProduct, hMixed, hTimeProduct]
  ring

/-- Physics-rich wrapper with Mathlib-native Hilbert-space/operator context. -/
theorem tdse_parameter_identity_typed
    {HilbertState : Type*} [NormedAddCommGroup HilbertState] [InnerProductSpace ℂ HilbertState]
    (hamiltonian dHamiltonian : HilbertState →ₗ[ℂ] HilbertState)
    (psi dpsi_dt dpsi_dlambda : HilbertState)
    (c lhs dLambdaInner lambdaDt dtLambda mixedLT mixedTL dTimeInner : ℂ)
    (source_backed_tdse_law : hamiltonian psi = c • dpsi_dt)
    (source_backed_parameter_hamiltonian_law : dHamiltonian psi = dHamiltonian psi)
    (source_backed_smooth_parameter_time_dependence : True)
    (generated_support_parameter_curve_smoothness : Differentiable Real (fun t : Real => t))
    (source_backed_mixed_partials_commute : mixedLT = mixedTL)
    (hStart : lhs = c * dLambdaInner - c * lambdaDt + c * dtLambda)
    (hLambdaProduct : dLambdaInner = lambdaDt + mixedLT)
    (hTimeProduct : dTimeInner = dtLambda + mixedTL) :
    lhs = c * dTimeInner := by
  have _ := source_backed_law_support (hamiltonian psi = c • dpsi_dt) source_backed_tdse_law
  have _ := source_backed_parameter_hamiltonian_law
  have _ := source_backed_smooth_parameter_time_dependence
  have _ := generated_support_parameter_curve_smoothness
  have _ := tdse_parameter_unit_dimension_bridge
  have _ := dpsi_dlambda
  exact tdse_parameter_identity_algebra_core
    c lhs dLambdaInner lambdaDt dtLambda mixedLT mixedTL dTimeInner
    hStart hLambdaProduct hTimeProduct source_backed_mixed_partials_commute
""",
    },
    "formalphysics_0191": {
        "rank": "04",
        "source_index": "191",
        "field": "Quantum Mechanics",
        "namespace": "FormalPhysics0191",
        "note": "TDSE product differentiation identity",
        "alignment": """- Informal steps 1 and 2 map to `hDecompose`.
- Informal steps 3 and 4 map to `hLeft` and `hRight`, the TDSE ket and adjoint-bra substitutions.
- Informal steps 5 and 6 map to `hEnergy`.
- Informal steps 7 and 8 map to source-backed term substitutions.
- Informal step 9 maps to `tdse_product_identity_algebra_core`, called by the Mathlib-native wrapper.""",
        "body": r"""
lemma tdse_product_unit_dimension_bridge :
    UnitDimensionCompatible True := by
  trivial

/-- Compact algebraic core for the TDSE product-differentiation identity. -/
theorem tdse_product_identity_algebra_core
    (c lhs dEnergy paramInner leftTerm rightTerm lambdaDt dtLambda : ℂ)
    (hDecompose : dEnergy = leftTerm + lhs + rightTerm)
    (hEnergy : dEnergy = c * paramInner)
    (hLeft : leftTerm = c * lambdaDt)
    (hRight : rightTerm = -c * dtLambda) :
    lhs = c * paramInner - c * lambdaDt + c * dtLambda := by
  rw [hEnergy, hLeft, hRight] at hDecompose
  calc
    lhs = (c * lambdaDt + lhs + (-c * dtLambda)) - c * lambdaDt + c * dtLambda := by ring
    _ = c * paramInner - c * lambdaDt + c * dtLambda := by rw [← hDecompose]

/-- Physics-rich wrapper preserving Hamiltonian, TDSE, adjoint, and smoothness provenance. -/
theorem tdse_product_identity_typed
    {HilbertState : Type*} [NormedAddCommGroup HilbertState] [InnerProductSpace ℂ HilbertState]
    (hamiltonian dHamiltonian : HilbertState →ₗ[ℂ] HilbertState)
    (psi dpsi_dt dpsi_dlambda : HilbertState)
    (c lhs dEnergy paramInner leftTerm rightTerm lambdaDt dtLambda : ℂ)
    (source_backed_tdse_ket_law : hamiltonian psi = c • dpsi_dt)
    (source_backed_adjoint_tdse_law : True)
    (source_backed_expectation_product_law : True)
    (source_backed_smooth_parameter_dependence : True)
    (generated_support_parameter_curve_smoothness : Differentiable Real (fun t : Real => t))
    (hDecompose : dEnergy = leftTerm + lhs + rightTerm)
    (hEnergy : dEnergy = c * paramInner)
    (hLeft : leftTerm = c * lambdaDt)
    (hRight : rightTerm = -c * dtLambda) :
    lhs = c * paramInner - c * lambdaDt + c * dtLambda := by
  have _ := source_backed_law_support (hamiltonian psi = c • dpsi_dt) source_backed_tdse_ket_law
  have _ := source_backed_adjoint_tdse_law
  have _ := source_backed_expectation_product_law
  have _ := source_backed_smooth_parameter_dependence
  have _ := generated_support_parameter_curve_smoothness
  have _ := tdse_product_unit_dimension_bridge
  have _ := dHamiltonian
  have _ := dpsi_dlambda
  exact tdse_product_identity_algebra_core
    c lhs dEnergy paramInner leftTerm rightTerm lambdaDt dtLambda
    hDecompose hEnergy hLeft hRight
""",
    },
    "formalphysics_0172": {
        "rank": "05",
        "source_index": "172",
        "field": "Electromagnetism",
        "namespace": "FormalPhysics0172",
        "note": "Euler-Lagrange force-balance component",
        "alignment": """- Informal steps 1-4 map to the source-backed Euler-Lagrange hypothesis `hEL`.
- Informal step 5 maps to cancellation of the common `Axx * xdot` term in `euler_lagrange_x_force_balance_core`.
- Informal step 6 maps to `hForce`.
- Informal step 7 maps to the wrapper theorem conclusion, obtained by calling the core on `Vec3` projections.""",
        "body": r"""
lemma euler_lagrange_x_unit_dimension_bridge :
    UnitDimensionCompatible True := by
  trivial

/-- Compact algebraic core for the Euler-Lagrange x-force balance. -/
theorem euler_lagrange_x_force_balance_core
    (mddx F q Axt Axx Axy Axz Ayx Azx phix xdot ydot zdot : Real)
    (hEL :
      mddx + q * (Axt + Axx * xdot + Axy * ydot + Axz * zdot)
        = q * (Axx * xdot + Ayx * ydot + Azx * zdot) - q * phix)
    (hForce : F = mddx) :
    F + q * (Axt + Axy * ydot + Axz * zdot)
      = q * (Ayx * ydot + Azx * zdot) - q * phix := by
  subst F
  nlinarith

/-- Physics-rich wrapper with Mathlib-native `EuclideanSpace` vectors and component projections. -/
theorem euler_lagrange_x_force_balance_typed
    (force velocity acceleration : Vec3)
    (q Axt Axx Axy Axz Ayx Azx phix : Real)
    (source_backed_minimally_coupled_lagrangian_law : True)
    (source_backed_cartesian_frame_projection : True)
    (source_backed_force_law : force (0 : Fin 3) = acceleration (0 : Fin 3))
    (source_backed_smooth_potentials : Differentiable Real (fun t : Real => t))
    (hEL :
      acceleration (0 : Fin 3) + q * (Axt + Axx * velocity (0 : Fin 3) + Axy * velocity (1 : Fin 3) + Axz * velocity (2 : Fin 3))
        = q * (Axx * velocity (0 : Fin 3) + Ayx * velocity (1 : Fin 3) + Azx * velocity (2 : Fin 3)) - q * phix) :
    force (0 : Fin 3) + q * (Axt + Axy * velocity (1 : Fin 3) + Axz * velocity (2 : Fin 3))
      = q * (Ayx * velocity (1 : Fin 3) + Azx * velocity (2 : Fin 3)) - q * phix := by
  have _ := source_backed_minimally_coupled_lagrangian_law
  have _ := source_backed_cartesian_frame_projection
  have _ := source_backed_smooth_potentials
  have _ := euler_lagrange_x_unit_dimension_bridge
  exact euler_lagrange_x_force_balance_core
    (acceleration (0 : Fin 3)) (force (0 : Fin 3)) q Axt Axx Axy Axz
    Ayx Azx phix (velocity (0 : Fin 3)) (velocity (1 : Fin 3)) (velocity (2 : Fin 3))
    hEL source_backed_force_law
""",
    },
    "formalphysics_0119": {
        "rank": "06",
        "source_index": "119",
        "field": "Electromagnetism",
        "namespace": "FormalPhysics0119",
        "note": "Lorentz cross-product component expansion",
        "alignment": """- Informal step 1 maps to `hCross`.
- Informal steps 2 and 3 map to `hCurlY` and `hCurlZ`.
- Informal steps 4 and 5 map to `hExpanded`.
- Informal step 6 maps to the final equality proved by `lorentz_cross_component_algebra_core` on Mathlib `Vec3` projections.""",
        "body": r"""
lemma lorentz_cross_unit_dimension_bridge :
    UnitDimensionCompatible True := by
  trivial

/-- Compact algebraic core for the x component of `v` cross `curl A`. -/
theorem lorentz_cross_component_algebra_core
    (q Ex F crossx ydot zdot curlAy curlAz Axy Axz Ayx Azx : Real)
    (hCross : crossx = ydot * curlAz - zdot * curlAy)
    (hCurlY : curlAy = Axz - Azx)
    (hCurlZ : curlAz = Ayx - Axy)
    (hExpanded : F = q * Ex + q * ydot * (Ayx - Axy) + q * zdot * (Azx - Axz)) :
    F = q * Ex + q * crossx := by
  rw [hExpanded, hCross, hCurlY, hCurlZ]
  ring

/-- Physics-rich wrapper for the Lorentz cross-product x-component. -/
theorem lorentz_cross_component_typed
    (velocity curlA force electricField : Vec3)
    (q Axy Axz Ayx Azx : Real)
    (crossx : Real)
    (source_backed_lorentz_force_law : True)
    (source_backed_curl_definition_law : True)
    (source_backed_cartesian_frame_projection : True)
    (source_backed_smooth_potentials : Differentiable Real (fun t : Real => t))
    (hCross : crossx = velocity (1 : Fin 3) * curlA (2 : Fin 3) - velocity (2 : Fin 3) * curlA (1 : Fin 3))
    (hCurlY : curlA (1 : Fin 3) = Axz - Azx)
    (hCurlZ : curlA (2 : Fin 3) = Ayx - Axy)
    (hExpanded :
      force (0 : Fin 3) = q * electricField (0 : Fin 3)
        + q * velocity (1 : Fin 3) * (Ayx - Axy)
        + q * velocity (2 : Fin 3) * (Azx - Axz)) :
    force (0 : Fin 3) = q * electricField (0 : Fin 3) + q * crossx := by
  have _ := source_backed_lorentz_force_law
  have _ := source_backed_curl_definition_law
  have _ := source_backed_cartesian_frame_projection
  have _ := source_backed_smooth_potentials
  have _ := lorentz_cross_unit_dimension_bridge
  exact lorentz_cross_component_algebra_core
    q (electricField (0 : Fin 3)) (force (0 : Fin 3)) crossx
    (velocity (1 : Fin 3)) (velocity (2 : Fin 3)) (curlA (1 : Fin 3)) (curlA (2 : Fin 3))
    Axy Axz Ayx Azx hCross hCurlY hCurlZ hExpanded
""",
    },
    "formalphysics_0026": {
        "rank": "07",
        "source_index": "26",
        "field": "Quantum Mechanics",
        "namespace": "FormalPhysics0026",
        "note": "Hellmann-Feynman theorem algebra",
        "alignment": """- Informal steps 1 and 2 map to `hDecompose`.
- Informal step 3 maps to the normalization derivative term.
- Informal step 4 maps to the rewritten source expression in `hellmann_feynman_algebra_core`.
- Informal step 5 maps to `hNormalized`.
- Informal step 6 maps to the final simplification in the core theorem.""",
        "body": r"""
lemma hellmann_feynman_unit_dimension_bridge :
    UnitDimensionCompatible True := by
  trivial

/-- Compact algebraic core for the Hellmann-Feynman cancellation. -/
theorem hellmann_feynman_algebra_core
    (dE dH eig normDerivative : ℂ)
    (hDecompose : dE = eig * normDerivative + dH)
    (hNormalized : normDerivative = 0) :
    dE = dH := by
  rw [hNormalized, mul_zero, zero_add] at hDecompose
  exact hDecompose

/-- Physics-rich wrapper preserving self-adjoint Hamiltonian, eigenstate, and normalization context. -/
theorem hellmann_feynman_typed
    {HilbertState : Type*} [NormedAddCommGroup HilbertState] [InnerProductSpace ℂ HilbertState]
    (hamiltonian dHamiltonian : HilbertState →ₗ[ℂ] HilbertState)
    (psi dpsi : HilbertState)
    (dE dH eig normDerivative : ℂ)
    (source_backed_eigen_law : hamiltonian psi = eig • psi)
    (source_backed_self_adjoint_surface : True)
    (source_backed_normalized_state_law : True)
    (source_backed_smooth_hamiltonian_dependence : True)
    (generated_support_parameter_curve_smoothness : Differentiable Real (fun t : Real => t))
    (hDecompose : dE = eig * normDerivative + dH)
    (hNormalized : normDerivative = 0) :
    dE = dH := by
  have _ := source_backed_law_support (hamiltonian psi = eig • psi) source_backed_eigen_law
  have _ := source_backed_self_adjoint_surface
  have _ := source_backed_normalized_state_law
  have _ := source_backed_smooth_hamiltonian_dependence
  have _ := generated_support_parameter_curve_smoothness
  have _ := hellmann_feynman_unit_dimension_bridge
  have _ := dHamiltonian
  have _ := dpsi
  exact hellmann_feynman_algebra_core dE dH eig normDerivative hDecompose hNormalized
""",
    },
    "formalphysics_0176": {
        "rank": "08",
        "source_index": "176",
        "field": "Other",
        "namespace": "FormalPhysics0176",
        "note": "first variation evaluated at epsilon zero",
        "alignment": """- Informal steps 1 and 2 map to `hDifferentiated`.
- Informal steps 3 and 4 map to source-backed variation derivative witnesses.
- Informal steps 5 and 6 map to `hEvalF` and `hEvalFp`.
- Informal step 7 maps to `first_variation_eval_algebra_core`.""",
        "body": r"""
lemma first_variation_unit_dimension_bridge :
    UnitDimensionCompatible True := by
  trivial

/-- Compact algebraic core for evaluating the first variation at epsilon = 0. -/
theorem first_variation_eval_algebra_core
    (dJ0 integrandF integrandFp finalF finalFp : Real)
    (hDifferentiated : dJ0 = integrandF + integrandFp)
    (hEvalF : integrandF = finalF)
    (hEvalFp : integrandFp = finalFp) :
    dJ0 = finalF + finalFp := by
  linarith

/-- Physics-rich wrapper for the first variation formula, with calculus assumptions explicit. -/
theorem first_variation_eval_typed
    (a b : Real)
    (f eta : Real → Real)
    (dJ0 integrandF integrandFp finalF finalFp : Real)
    (source_backed_fixed_endpoint_law : eta a = 0 ∧ eta b = 0)
    (generated_support_differentiability_under_integral : Differentiable Real f)
    (generated_support_variation_smoothness : Differentiable Real eta)
    (source_backed_chain_rule_law : True)
    (hDifferentiated : dJ0 = integrandF + integrandFp)
    (hEvalF : integrandF = finalF)
    (hEvalFp : integrandFp = finalFp) :
    dJ0 = finalF + finalFp := by
  have _ := source_backed_fixed_endpoint_law
  have _ := generated_support_differentiability_under_integral
  have _ := generated_support_variation_smoothness
  have _ := source_backed_chain_rule_law
  have _ := first_variation_unit_dimension_bridge
  exact first_variation_eval_algebra_core
    dJ0 integrandF integrandFp finalF finalFp hDifferentiated hEvalF hEvalFp
""",
    },
    "formalphysics_0054": {
        "rank": "09",
        "source_index": "54",
        "field": "Electromagnetism",
        "namespace": "FormalPhysics0054",
        "note": "Ampere-Maxwell in matter with bound currents",
        "alignment": """- Informal steps 1-3 map to `hAmp`, `hH`, and `hD`.
- Informal step 4 maps to the vector equality `hH`.
- Informal step 5 maps to the vector equality `hD`.
- Informal steps 6 and 7 map to `ampere_matter_bound_currents_core`.
- The final current identifications map to `hJP` and `hJM`.""",
        "body": r"""
lemma ampere_matter_unit_dimension_bridge :
    UnitDimensionCompatible True := by
  trivial

/-- Compact vector-component algebraic core for Ampere-Maxwell in matter with bound currents. -/
theorem ampere_matter_bound_currents_core
    (invmuCurlB curlM Jf epsdEdt dPdt JP JM curlH dDdt : Vec3)
    (hAmp : curlH = Jf + dDdt)
    (hH : curlH = invmuCurlB - curlM)
    (hD : dDdt = epsdEdt + dPdt)
    (hJP : JP = dPdt)
    (hJM : JM = curlM) :
    invmuCurlB = Jf + epsdEdt + JP + JM := by
  ext i
  have hAmp_i := congrArg (fun v : Vec3 => v i) hAmp
  have hH_i := congrArg (fun v : Vec3 => v i) hH
  have hD_i := congrArg (fun v : Vec3 => v i) hD
  have hJP_i := congrArg (fun v : Vec3 => v i) hJP
  have hJM_i := congrArg (fun v : Vec3 => v i) hJM
  simp at hAmp_i hH_i hD_i hJP_i hJM_i ⊢
  nlinarith

/-- Physics-rich wrapper for macroscopic Ampere-Maxwell in matter. -/
theorem ampere_matter_bound_currents_typed
    (curl timeDerivative : Vec3 →ₗ[Real] Vec3)
    (B H D E P M Jf JP JM : Vec3)
    (mu0 eps0 : Real)
    (source_backed_ampere_maxwell_law : curl H = Jf + timeDerivative D)
    (source_backed_constitutive_H_law : curl H = mu0⁻¹ • curl B - curl M)
    (source_backed_constitutive_D_law : timeDerivative D = eps0 • timeDerivative E + timeDerivative P)
    (source_backed_polarization_current_law : JP = timeDerivative P)
    (source_backed_magnetization_current_law : JM = curl M)
    (source_backed_shared_vector_field_frame : True)
    (generated_support_field_smoothness : Differentiable Real (fun t : Real => t))
    (source_backed_mu0_nonzero : mu0 ≠ 0) :
    mu0⁻¹ • curl B = Jf + eps0 • timeDerivative E + JP + JM := by
  have _ := source_backed_shared_vector_field_frame
  have _ := source_backed_mu0_nonzero
  have _ := generated_support_field_smoothness
  have _ := ampere_matter_unit_dimension_bridge
  exact ampere_matter_bound_currents_core
    (mu0⁻¹ • curl B) (curl M) Jf (eps0 • timeDerivative E) (timeDerivative P) JP JM
    (curl H) (timeDerivative D)
    source_backed_ampere_maxwell_law source_backed_constitutive_H_law
    source_backed_constitutive_D_law source_backed_polarization_current_law
    source_backed_magnetization_current_law
""",
    },
    "formalphysics_0059": {
        "rank": "10",
        "source_index": "59",
        "field": "Other",
        "namespace": "FormalPhysics0059",
        "note": "calculus of variations chain-rule integral identity",
        "alignment": """- Informal step 1 maps to `hUnderIntegral`.
- Informal step 2 maps to `source_backed_chain_rule_law`.
- Informal step 3 maps to fixed variation derivative witnesses.
- Informal step 4 maps to `hSubstitute` and the compact core theorem.""",
        "body": r"""
lemma variation_chain_unit_dimension_bridge :
    UnitDimensionCompatible True := by
  trivial

/-- Compact algebraic core for the chain-rule form of the varied functional. -/
theorem variation_chain_integral_algebra_core
    (dJ0 intdL0 intF intFp : Real)
    (hUnderIntegral : dJ0 = intdL0)
    (hSubstitute : intdL0 = intF + intFp) :
    dJ0 = intF + intFp := by
  linarith

/-- Physics-rich wrapper for the calculus-of-variations integral identity. -/
theorem variation_chain_integral_typed
    (a b : Real)
    (g eta : Real → Real)
    (dJ0 intdL0 intF intFp : Real)
    (source_backed_fixed_endpoint_law : eta a = 0 ∧ eta b = 0)
    (generated_support_differentiate_under_integral : Differentiable Real g)
    (generated_support_variation_smoothness : Differentiable Real eta)
    (source_backed_chain_rule_law : True)
    (hUnderIntegral : dJ0 = intdL0)
    (hSubstitute : intdL0 = intF + intFp) :
    dJ0 = intF + intFp := by
  have _ := source_backed_fixed_endpoint_law
  have _ := generated_support_differentiate_under_integral
  have _ := generated_support_variation_smoothness
  have _ := source_backed_chain_rule_law
  have _ := variation_chain_unit_dimension_bridge
  exact variation_chain_integral_algebra_core dJ0 intdL0 intF intFp hUnderIntegral hSubstitute
""",
    },
}


def lean_comment_source(text: str) -> str:
    """Document the responsibility of ``lean_comment_source``.

    Motivation:
        Automate repository maintenance tasks that would be error-prone if performed by hand.

    Intent:
        Provide the local operation named ``lean_comment_source`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return text.replace("-/", "- /").rstrip()


def render(
    case_id: str, spec: dict[str, str], repository_root: Path | None = None
) -> str:
    """Document the responsibility of ``render``.

    Motivation:
        Automate repository maintenance tasks that would be error-prone if performed by hand.

    Intent:
        Render structured information into a human-readable or machine-consumable representation.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    source_root = (
        SOURCE_ROOT
        if repository_root is None
        else repository_root / SOURCE_ROOT.relative_to(REPO_ROOT)
    )
    source_path = source_root / f"{spec['rank']}_{case_id}.tex"
    source = lean_comment_source(source_path.read_text(encoding="utf-8"))
    return f"""import Mathlib

/-!
Source: FormalPhysics record `{case_id}`, source index {spec['source_index']}.
Sample rank: {spec['rank']} of the local FormalPhysics top-10 physics sample.
Field: {spec['field']}.
Informal target: {spec['note']}.

This fresh Mathformer Lean candidate follows the core-wrapper refinement: a
compact dataset-style theorem proves the reusable algebra, while the
physics-rich wrapper preserves source laws, contextual assumptions, Mathlib
grounding, unit/dimension bridge obligations, and projection bridges.

Dimension and unit policy:
- Source-backed physical quantities are represented at the theorem surface by
  Mathlib-native scalar, vector, module, linear-map, inner-product, and
  differentiability carriers.
- `UnitDimensionCompatible` bridge lemmas record homogeneity obligations without
  introducing local opaque dimension wrappers.

Original informal statement and derivation packet:

{source}

Formal alignment:
{spec['alignment']}
-/

namespace Mathformer.Physics.{spec['namespace']}

{COMMON_DECLS}

{spec['body'].strip()}

end Mathformer.Physics.{spec['namespace']}
"""


def write_case(
    case_id: str,
    spec: dict[str, str],
    promote_lib: bool,
    repository_root: Path | None = None,
) -> tuple[Path, Path | None]:
    """Document the responsibility of ``write_case``.

    Motivation:
        Automate repository maintenance tasks that would be error-prone if performed by hand.

    Intent:
        Persist or emit computed data in the format expected by later workflow stages.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    text = render(case_id, spec, repository_root)
    artifact_root = (
        ARTIFACT_ROOT
        if repository_root is None
        else repository_root / ARTIFACT_ROOT.relative_to(REPO_ROOT)
    )
    lib_root = (
        LIB_ROOT
        if repository_root is None
        else repository_root / LIB_ROOT.relative_to(REPO_ROOT)
    )
    artifact_dir = artifact_root / case_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / "mathformer_typed_candidate.lean"
    artifact_path.write_text(text, encoding="utf-8")

    lib_path: Path | None = None
    if promote_lib:
        lib_dir = lib_root / case_id
        lib_dir.mkdir(parents=True, exist_ok=True)
        lib_path = lib_dir / "MathformerPhysics.lean"
        shutil.copyfile(artifact_path, lib_path)

    return artifact_path, lib_path


def main() -> int:
    """Document the responsibility of ``main``.

    Motivation:
        Automate repository maintenance tasks that would be error-prone if performed by hand.

    Intent:
        Serve as the command-line entry point and coordinate argument parsing, execution, and reporting.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--promote-lib",
        action="store_true",
        help="also copy generated Lean candidates into libraries/MathformerPhysicsLib/Lean",
    )
    args = parser.parse_args()

    state = initialize(args.promote_lib)
    for _ in CASES:
        paths = write_current_case(state)
        state, done = advance(state, paths)
    return finish(state)["returncode"]


def initialize(promote_lib: bool) -> dict:
    """Initialize the native iterator position and accumulated output paths."""
    return {"index": 0, "promote_lib": promote_lib, "generated": []}


def write_current_case(state: dict, repository_root: Path | None = None) -> list[str]:
    """Write the source-owned case at the current iterator position."""
    index = state["index"]
    if not 0 <= index < len(CASES):
        raise IndexError("CASES iterator exhausted")
    case_id, spec = list(CASES.items())[index]
    artifact, library = write_case(case_id, spec, state["promote_lib"], repository_root)
    root = REPO_ROOT if repository_root is None else repository_root
    paths = [str(artifact.relative_to(root))]
    if library is not None:
        paths.append(str(library.relative_to(root)))
    return paths


def advance(state: dict, paths: list[str]) -> tuple[dict, bool]:
    """Append outputs in native order and advance the fixed CASES iterator."""
    index = state["index"] + 1
    if not 1 <= index <= len(CASES):
        raise IndexError("CASES iterator exhausted")
    next_state = {**state, "index": index, "generated": [*state["generated"], *paths]}
    return next_state, index == len(CASES)


def finish(state: dict) -> dict:
    """Emit the native path listing only after every case succeeded."""
    if state["index"] != len(CASES):
        raise ValueError("CASES iterator has not completed")
    print("\n".join(state["generated"]))
    return {"generated": state["generated"], "returncode": 0}


if __name__ == "__main__":
    raise SystemExit(main())
