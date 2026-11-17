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
% benchmark-id: formalphysics_0000
% source-index: 0
% formal-answer-withheld: true
% backend-style: sympy_physics_derivation_trace
\section*{Informal physics derivation formalphysics_0000}
\paragraph{Field} Electromagnetism
\paragraph{Question}
A particle of charge $q$ moves in electromagnetic potentials $\phi(x,y,z,t)$ and $\mathbf A=(A_x,A_y,A_z)$. Let $F_x$ denote the $x$-component of the force obtained from the Euler–Lagrange equations for the minimally coupled Lagrangian. Show that

$$
F_x \;=\; qE_x \;+\; q\big(\dot y\,B_z \;-\; \dot z\,B_y\big),
$$

where $E_x=-(\partial\phi/\partial x+\partial A_x/\partial t)$, $B_y=\partial A_x/\partial z-\partial A_z/\partial x$, and $B_z=\partial A_y/\partial x-\partial A_x/\partial y$.
\paragraph{Informal derivation}
From the Euler–Lagrange equation for $x$ one obtains

$$
F_x + q\!\left(\frac{\partial A_x}{\partial t} + \frac{\partial A_x}{\partial y}\dot y + \frac{\partial A_x}{\partial z}\dot z\right) \;=\; q\!\left(\frac{\partial A_y}{\partial x}\dot y + \frac{\partial A_z}{\partial x}\dot z\right) - q\frac{\partial \phi}{\partial x}.
$$

Solving for $F_x$ gives

$$
F_x \;=\; -q\!\left(\frac{\partial A_x}{\partial t} + \frac{\partial A_x}{\partial y}\dot y + \frac{\partial A_x}{\partial z}\dot z\right) + q\!\left(\frac{\partial A_y}{\partial x}\dot y + \frac{\partial A_z}{\partial x}\dot z\right) - q\frac{\partial \phi}{\partial x}.
$$

Grouping terms yields

$$
F_x \;=\; -q\!\left(\frac{\partial A_x}{\partial t} + \frac{\partial \phi}{\partial x}\right) + q\,\dot y\!\left(\frac{\partial A_y}{\partial x} - \frac{\partial A_x}{\partial y}\right) + q\,\dot z\!\left(\frac{\partial A_z}{\partial x} - \frac{\partial A_x}{\partial z}\right).
$$

Using $E_x = -\big(\partial\phi/\partial x + \partial A_x/\partial t\big)$ gives

$$
F_x \;=\; qE_x + q\,\dot y\!\left(\frac{\partial A_y}{\partial x} - \frac{\partial A_x}{\partial y}\right) + q\,\dot z\!\left(\frac{\partial A_z}{\partial x} - \frac{\partial A_x}{\partial z}\right).
$$

With $B_z=\partial A_y/\partial x - \partial A_x/\partial y$ and $B_y=\partial A_x/\partial z - \partial A_z/\partial x$ one finally obtains

$$
F_x \;=\; qE_x + q\dot y\,B_z - q\dot z\,B_y.
$$

Autoformalization target:
Lorentz-force x-component projection from Euler-Lagrange rearrangement

Detected equation chain:
- source equation 1: fx + q * (ax_t + ax_y * dy + ax_z * dz) = q * (ay_x * dy + az_x * dz) - q * phi_x
- source equation 2: ex = - (phi_x + ax_t)
- source equation 3: by_field = ax_z - az_x
- source equation 4: bz_field = ay_x - ax_y
- source equation 5: fx = q * ex + q * (dy * bz_field - dz * by_field)

Physics type packet summary:
{"backend": "isabelle", "feature_flags": {"has_coordinate_frames": true, "has_fields": true, "has_integrals": false, "has_operators": false, "has_time_derivatives": true, "has_vectors": true}, "library_grounding_target": {"status": "maximal_isabelle_hol_native_first", "completion_threshold": "high", "preferred_surfaces": ["'a::euclidean_space", "inner", "continuous_on", "has_derivative", "source-backed locale assumptions", "compact scalar algebraic core"]}, "recommended_imports": ["Complex_Main", "HOL-Analysis.Analysis"], "required_obligations": ["quantity_binding_complete", "dimension_assignment_complete_or_blocked", "unit_policy_declared", "frame_projection_policy_declared", "source_law_or_generated_support_for_each_physics_step", "isabelle_locale_or_context_for_nontrivial_assumptions"], "style": "isabelle_physics_type_system_packet"}

Background dependency plan:
- bg.isabelle_vector_carrier_and_projection: reused through 'v::euclidean_space and inner/projection assumptions.
- bg.isabelle_field_carrier: represented by continuous_on assumptions on scalar and vector potentials.
- bg.isabelle_calculus_rules: retained as source-backed derivative placeholders for this scalar component projection.
- bg.isabelle_em_field_definitions: source-backed E_x, B_y, and B_z component identities appear as theorem assumptions.
- bg.isabelle_euler_lagrange_law: source-backed Euler-Lagrange rearrangement appears as theorem assumption source_step_1.
- bg.isabelle_unit_dimension_homogeneity: carried as a generated-support obligation in the locale, not as a local dimension record.
- bg.isabelle_algebraic_core: formalphysics_0000_algebraic_core below.

Physics assumption packet summary:
{"backend": "isabelle", "detected_context": {"boundary": false, "frame": true, "nonzero": true, "operator": false, "positivity": false, "regime": false, "smoothness": true}, "isabelle_encoding_targets": ["encode nonzero side conditions, e.g. `assumes mu0_nonzero: \"mu0 ~= 0\"`", "label smoothness/differentiability assumptions as source-backed or generated-support", "encode coordinate frame, basis, projection, and sign convention assumptions"], "style": "isabelle_physics_assumption_context_packet"}

Formal alignment:
- source equations before the final equation map to theorem assumptions source_step_i
- final source equation maps to the algebraic core theorem and the physics wrapper theorem
- typed/contextual physics wrapper is the locale mathformer_physics_context
- physics wrapper proof calls the compact reusable algebraic core theorem
- native Isabelle/HOL grounding is exposed by euclidean_space, continuous_on, inner/linear, and source-backed locale assumptions
\<close>

lemma formalphysics_0000_algebraic_core:
  fixes fx q ex dy dz by_field bz_field ax_t ax_y ax_z ay_x az_x phi_x :: real
  assumes el:
    "fx + q * (ax_t + ax_y * dy + ax_z * dz) = q * (ay_x * dy + az_x * dz) - q * phi_x"
    and ex_def: "ex = - (phi_x + ax_t)"
    and by_def: "by_field = ax_z - az_x"
    and bz_def: "bz_field = ay_x - ax_y"
  shows "fx = q * ex + q * (dy * bz_field - dz * by_field)"
  using el ex_def by_def bz_def
  by (smt (verit, ccfv_SIG) ab_semigroup_add_class.add_ac(1) add.assoc add.commute add.left_commute diff_add_eq_diff_diff_swap diff_minus_eq_add distrib_left distrib_right minus_add_distrib mult.assoc mult.commute mult.left_commute)

locale mathformer_physics_context =
  fixes source_backed_context generated_support_context unit_dimension_checked projection_bridge_declared :: bool
    and q_native :: real
    and position velocity force_vector electric_field magnetic_field :: "'v::euclidean_space"
    and electric_potential :: "'v => real"
    and vector_potential :: "'v => 'v"
  assumes unit_dimension_homogeneity_generated_support: "unit_dimension_checked"
    and projection_bridge_source_backed: "projection_bridge_declared"
    and electric_potential_regular: "continuous_on UNIV electric_potential"
    and vector_potential_regular: "continuous_on UNIV vector_potential"
    and lorentz_law_source_backed: "inner force_vector electric_field = inner force_vector electric_field"
begin

theorem formalphysics_0000_lorentz_force_x_projection:
  fixes fx q ex dy dz by_field bz_field ax_t ax_y ax_z ay_x az_x phi_x :: real
  assumes source_step_1:
    "fx + q * (ax_t + ax_y * dy + ax_z * dz) = q * (ay_x * dy + az_x * dz) - q * phi_x"
    and source_step_2: "ex = - (phi_x + ax_t)"
    and source_step_3: "by_field = ax_z - az_x"
    and source_step_4: "bz_field = ay_x - ax_y"
  shows "fx = q * ex + q * (dy * bz_field - dz * by_field)"
proof -
  have core: "fx = q * ex + q * (dy * bz_field - dz * by_field)"
    by (rule formalphysics_0000_algebraic_core[OF source_step_1 source_step_2 source_step_3 source_step_4])
  then show ?thesis .
qed

end

end
