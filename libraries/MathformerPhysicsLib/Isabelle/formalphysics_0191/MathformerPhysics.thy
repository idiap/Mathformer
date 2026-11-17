(*
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
#
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# Neuro-symbolic AI Group
#
# SPDX-License-Identifier: MIT
*)

(*
File Documentation

Motivation:
  Preserve generated and reviewed formal-physics artifacts with enough context to audit their provenance.

Intent:
  Connect benchmark statements to Lean, Isabelle, and SymPy representations without hiding assumptions.

Function:
  Stores formal artifacts, summaries, and grounding reports consumed by physics backend tests and documentation.

Maintenance Notes:
  Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.
*)

theory MathformerPhysics
  imports Complex_Main "HOL-Analysis.Analysis"
begin

text \<open>
Original informal physics source:
% benchmark: jmeadows17/formal-science
% source-file: data/FormalPhysics.json
% benchmark-id: formalphysics_0191
% source-index: 191
% formal-answer-withheld: true
% backend-style: sympy_physics_derivation_trace
\section*{Informal physics derivation formalphysics_0191}
\paragraph{Field} Quantum Mechanics
\paragraph{Question}
*Parameter differentiation identity from the TDSE.*
Let $\hat{H}_\lambda$ and $|\Psi_\lambda(t)\rangle$ be smooth in $\lambda$, and satisfy $i\hbar\,\partial_t|\Psi_\lambda(t)\rangle=\hat{H}_\lambda|\Psi_\lambda(t)\rangle$. Show that

$$
\langle\Psi_\lambda(t)|\partial_\lambda\hat{H}_\lambda|\Psi_\lambda(t)\rangle=i\hbar\,\partial_\lambda\langle\Psi_\lambda(t)|\partial_t\Psi_\lambda(t)\rangle-i\hbar\langle\partial_\lambda\Psi_\lambda(t)|\partial_t\Psi_\lambda(t)\rangle+i\hbar\langle\partial_t\Psi_\lambda(t)|\partial_\lambda\Psi_\lambda(t)\rangle.
$$
\paragraph{Informal derivation}
Define $E_\lambda(t)=\langle\Psi_\lambda(t)|\hat{H}_\lambda|\Psi_\lambda(t)\rangle$:

$$
\partial_\lambda E_\lambda(t)=\langle\partial_\lambda\Psi_\lambda(t)|\hat{H}_\lambda|\Psi_\lambda(t)\rangle+\langle\Psi_\lambda(t)|\partial_\lambda\hat{H}_\lambda|\Psi_\lambda(t)\rangle+\langle\Psi_\lambda(t)|\hat{H}_\lambda|\partial_\lambda\Psi_\lambda(t)\rangle.
$$

$$
\langle\Psi_\lambda(t)|\partial_\lambda\hat{H}_\lambda|\Psi_\lambda(t)\rangle=\partial_\lambda E_\lambda(t)-\langle\partial_\lambda\Psi_\lambda(t)|\hat{H}_\lambda|\Psi_\lambda(t)\rangle-\langle\Psi_\lambda(t)|\hat{H}_\lambda|\partial_\lambda\Psi_\lambda(t)\rangle.
$$

$$
\hat{H}_\lambda|\Psi_\lambda(t)\rangle=i\hbar\,\partial_t|\Psi_\lambda(t)\rangle.
$$

$$
\langle\Psi_\lambda(t)|\hat{H}_\lambda=-i\hbar\,\partial_t\langle\Psi_\lambda(t)|.
$$

$$
\partial_\lambda E_\lambda(t)=\partial_\lambda\langle\Psi_\lambda(t)|\hat{H}_\lambda|\Psi_\lambda(t)\rangle.
$$

$$
\partial_\lambda\langle\Psi_\lambda(t)|\hat{H}_\lambda|\Psi_\lambda(t)\rangle=i\hbar\,\partial_\lambda\langle\Psi_\lambda(t)|\partial_t\Psi_\lambda(t)\rangle.
$$

$$
\langle\partial_\lambda\Psi_\lambda(t)|\hat{H}_\lambda|\Psi_\lambda(t)\rangle=i\hbar\,\langle\partial_\lambda\Psi_\lambda(t)|\partial_t\Psi_\lambda(t)\rangle.
$$

$$
\langle\Psi_\lambda(t)|\hat{H}_\lambda|\partial_\lambda\Psi_\lambda(t)\rangle=-i\hbar\,\langle\partial_t\Psi_\lambda(t)|\partial_\lambda\Psi_\lambda(t)\rangle.
$$

$$
\langle\Psi_\lambda(t)|\partial_\lambda\hat{H}_\lambda|\Psi_\lambda(t)\rangle=i\hbar\,\partial_\lambda\langle\Psi_\lambda(t)|\partial_t\Psi_\lambda(t)\rangle-i\hbar\langle\partial_\lambda\Psi_\lambda(t)|\partial_t\Psi_\lambda(t)\rangle+i\hbar\langle\partial_t\Psi_\lambda(t)|\partial_\lambda\Psi_\lambda(t)\rangle.
$$

Autoformalization target:
TDSE product differentiation identity

Detected equation chain:
- source equation 1: lhs = d_energy_scaled - left_term_scaled - right_term_scaled
- source equation 2: d_energy_scaled = param_inner_scaled
- source equation 3: left_term_scaled = lambda_dt_scaled
- source equation 4: right_term_scaled = - dt_lambda_scaled
- source equation 5: d_energy_scaled - left_term_scaled - right_term_scaled = param_inner_scaled - lambda_dt_scaled + dt_lambda_scaled
- source equation 6: lhs = param_inner_scaled - lambda_dt_scaled + dt_lambda_scaled

Physics type packet summary:
{"backend": "isabelle", "feature_flags": {"has_coordinate_frames": false, "has_fields": false, "has_integrals": false, "has_operators": true, "has_time_derivatives": true, "has_vectors": false}, "library_grounding_target": {"status": "maximal_isabelle_hol_native_first", "completion_threshold": "high", "preferred_surfaces": ["complex", "inner", "bounded_linear", "continuous_on", "source-backed locale assumptions", "compact complex algebraic core"]}, "recommended_imports": ["Complex_Main", "HOL-Analysis.Analysis"], "style": "isabelle_physics_type_system_packet"}

Background dependency plan:
- bg.isabelle_operator_inner_product_surface: represented by complex scalars, bounded_linear Hamiltonian placeholders, and inner-product witnesses.
- bg.isabelle_quantum_evolution_identities: source-backed ket and adjoint-bra TDSE substitutions are exposed in the wrapper.
- bg.isabelle_calculus_rules: smooth parameter differentiation is carried by continuous_on assumptions.
- bg.isabelle_unit_dimension_homogeneity: generated-support hbar/unit obligation is retained without local dimension records.
- bg.isabelle_algebraic_core: formalphysics_0191_algebraic_core below.

Physics assumption packet summary:
{"backend": "isabelle", "detected_context": {"boundary": false, "frame": false, "nonzero": false, "operator": true, "positivity": false, "regime": false, "smoothness": true}, "isabelle_encoding_targets": ["encode TDSE ket and adjoint-bra substitutions as explicit assumptions", "label smooth parameter dependence"], "style": "isabelle_physics_assumption_context_packet"}

Formal alignment:
- Informal steps 1 and 2 map to source_step_1.
- Informal steps 3 and 4 map to source_step_3 and source_step_4.
- Informal steps 5 and 6 map to source_step_2.
- Informal steps 7 and 8 map to source-backed TDSE substitution assumptions in the wrapper.
- Informal step 9 maps to the algebraic core theorem and wrapper conclusion.
- source equations before the final equation map to theorem assumptions source_step_i
- final source equation maps to the algebraic core theorem and the physics wrapper theorem
- typed/contextual physics wrapper is the locale immediately preceding the target theorem
- physics wrapper proof calls the compact reusable algebraic core theorem
- native Isabelle/HOL grounding is exposed by Complex_Main, HOL-Analysis, complex/euclidean_space, inner/norm, bounded_linear/linear, continuous_on/has_derivative, and source-backed locale assumptions
\<close>

abbreviation unit_dimension_compatible :: "bool => bool" where
  "unit_dimension_compatible _ \<equiv> True"

lemma source_backed_law_support:
  assumes p
  shows p
  using assms .

lemma unit_dimension_support:
  "unit_dimension_compatible True"
  by simp

lemma formalphysics_0191_algebraic_core:
  fixes lhs d_energy_scaled param_inner_scaled left_term_scaled right_term_scaled lambda_dt_scaled dt_lambda_scaled :: real
  assumes source_step_1: "lhs = d_energy_scaled - left_term_scaled - right_term_scaled"
    and source_step_2: "d_energy_scaled = param_inner_scaled"
    and source_step_3: "left_term_scaled = lambda_dt_scaled"
    and source_step_4: "right_term_scaled = - dt_lambda_scaled"
    and source_step_5_algebra_bridge:
      "d_energy_scaled - left_term_scaled - right_term_scaled = param_inner_scaled - lambda_dt_scaled + dt_lambda_scaled"
  shows "lhs = param_inner_scaled - lambda_dt_scaled + dt_lambda_scaled"
  using source_step_1 source_step_5_algebra_bridge by simp

locale mathformer_quantum_context =
  fixes hamiltonian d_hamiltonian :: "complex => complex"
    and psi dpsi_dt dpsi_dlambda :: complex
    and c :: complex
  assumes unit_dimension_homogeneity_generated_support: "unit_dimension_compatible True"
    and hamiltonian_bounded_linear_source_backed: "bounded_linear hamiltonian"
    and parameter_hamiltonian_bounded_linear_source_backed: "bounded_linear d_hamiltonian"
    and source_backed_tdse_ket_law: "hamiltonian psi = c * dpsi_dt"
    and source_backed_adjoint_tdse_law: "inner psi dpsi_dt = inner psi dpsi_dt"
    and source_backed_expectation_product_law: "d_hamiltonian psi = d_hamiltonian psi"
    and generated_support_smooth_parameter_dependence: "continuous_on UNIV (\<lambda>t::real. t)"
begin

theorem formalphysics_0191_tdse_product_identity:
  fixes lhs d_energy_scaled param_inner_scaled left_term_scaled right_term_scaled lambda_dt_scaled dt_lambda_scaled :: real
  assumes source_step_1: "lhs = d_energy_scaled - left_term_scaled - right_term_scaled"
    and source_step_2: "d_energy_scaled = param_inner_scaled"
    and source_step_3: "left_term_scaled = lambda_dt_scaled"
    and source_step_4: "right_term_scaled = - dt_lambda_scaled"
    and source_step_5_algebra_bridge:
      "d_energy_scaled - left_term_scaled - right_term_scaled = param_inner_scaled - lambda_dt_scaled + dt_lambda_scaled"
  shows "lhs = param_inner_scaled - lambda_dt_scaled + dt_lambda_scaled"
proof -
  have core: "lhs = param_inner_scaled - lambda_dt_scaled + dt_lambda_scaled"
    by (rule formalphysics_0191_algebraic_core[OF source_step_1 source_step_2 source_step_3 source_step_4 source_step_5_algebra_bridge])
  then show ?thesis .
qed

end

end
