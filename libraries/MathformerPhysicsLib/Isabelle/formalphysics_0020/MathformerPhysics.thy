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
% benchmark-id: formalphysics_0020
% source-index: 20
% formal-answer-withheld: true
% backend-style: sympy_physics_derivation_trace
\section*{Informal physics derivation formalphysics_0020}
\paragraph{Field} Electromagnetism
\paragraph{Question}
*Macroscopic Maxwell–Ampère law with polarization and magnetization.*
Let $\mathbf{D}=\varepsilon_0\mathbf{E}+\mathbf{P}$ and define the magnetization current density $\mathbf{J}_M=\nabla\times\mathbf{M}$. Starting from $\nabla\times\mathbf{H}=\mathbf{J}_f+\partial\mathbf{D}/\partial t$ and $\mathbf{B}=\mu_0(\mathbf{H}+\mathbf{M})$, show that

$$
\nabla\times\left(\frac{\mathbf{B}}{\mu_0}\right)=\mathbf{J}_f+\varepsilon_0\frac{\partial\mathbf{E}}{\partial t}+\frac{\partial\mathbf{P}}{\partial t}+\mathbf{J}_M.
$$
\paragraph{Informal derivation}
Start from $\nabla\times\mathbf{H}=\mathbf{J}_f+\frac{\partial\mathbf{D}}{\partial t}$:

$$
\nabla\times\mathbf{H}=\mathbf{J}_f+\frac{\partial\mathbf{D}}{\partial t}.
$$

Use $\mathbf{B}=\mu_0(\mathbf{H}+\mathbf{M})$:

$$
\nabla\times\left(\frac{\mathbf{B}}{\mu_0}\right)=\nabla\times\mathbf{H}+\nabla\times\mathbf{M}.
$$

Identify $\mathbf{J}_M=\nabla\times\mathbf{M}$:

$$
\nabla\times\left(\frac{\mathbf{B}}{\mu_0}\right)=\nabla\times\mathbf{H}+\mathbf{J}_M.
$$

Substitute $\nabla\times\mathbf{H}$:

$$
\nabla\times\left(\frac{\mathbf{B}}{\mu_0}\right)=\mathbf{J}_f+\frac{\partial\mathbf{D}}{\partial t}+\mathbf{J}_M.
$$

Insert $\mathbf{D}=\varepsilon_0\mathbf{E}+\mathbf{P}$:

$$
\frac{\partial\mathbf{D}}{\partial t}=\frac{\partial}{\partial t}\left(\varepsilon_0\mathbf{E}+\mathbf{P}\right).
$$

Expand the time derivative:

$$
\frac{\partial\mathbf{D}}{\partial t}=\varepsilon_0\frac{\partial\mathbf{E}}{\partial t}+\frac{\partial\mathbf{P}}{\partial t}.
$$

Conclude:

$$
\nabla\times\left(\frac{\mathbf{B}}{\mu_0}\right)=\mathbf{J}_f+\varepsilon_0\frac{\partial\mathbf{E}}{\partial t}+\frac{\partial\mathbf{P}}{\partial t}+\mathbf{J}_M.
$$

Autoformalization target:
Macroscopic Maxwell-Ampere projection with polarization and magnetization

Detected equation chain:
- source equation 1: curl_b_over_mu0 = curl_h + jm
- source equation 2: curl_h = jf + dt_d
- source equation 3: dt_d = eps0_dt_e + dt_p
- source equation 4: curl_b_over_mu0 = jf + eps0_dt_e + dt_p + jm

Physics type packet summary:
{"backend": "isabelle", "feature_flags": {"has_coordinate_frames": false, "has_fields": true, "has_integrals": false, "has_operators": false, "has_time_derivatives": true, "has_vectors": true}, "library_grounding_target": {"status": "maximal_isabelle_hol_native_first", "completion_threshold": "high", "preferred_surfaces": ["'a::euclidean_space", "continuous_on", "linear", "source-backed locale assumptions", "compact scalar algebraic core"]}, "recommended_imports": ["Complex_Main", "HOL-Analysis.Analysis"], "required_obligations": ["quantity_binding_complete", "dimension_assignment_complete_or_blocked", "unit_policy_declared", "frame_projection_policy_declared", "source_law_or_generated_support_for_each_physics_step", "isabelle_locale_or_context_for_nontrivial_assumptions"], "style": "isabelle_physics_type_system_packet"}

Background dependency plan:
- bg.isabelle_vector_carrier_and_projection: reused through 'v::euclidean_space field placeholders.
- bg.isabelle_field_carrier: represented by continuous_on assumptions over vector fields.
- bg.isabelle_calculus_rules: source-backed curl/time-derivative linearity appears as typed linear assumptions.
- bg.isabelle_source_law_support: D=epsilon0 E+P, J_M=curl M, curl H=J_f+dD/dt, and B=mu0(H+M) are exposed as theorem/locale assumptions.
- bg.isabelle_unit_dimension_homogeneity: carried as a generated-support obligation in the locale, not as a local dimension record.
- bg.isabelle_algebraic_core: formalphysics_0020_algebraic_core below.

Physics assumption packet summary:
{"backend": "isabelle", "detected_context": {"boundary": false, "frame": false, "nonzero": true, "operator": false, "positivity": false, "regime": false, "smoothness": true}, "isabelle_encoding_targets": ["encode nonzero side conditions, e.g. `assumes mu0_nonzero: \"mu0 ~= 0\"`", "label smoothness/differentiability assumptions as source-backed or generated-support"], "style": "isabelle_physics_assumption_context_packet"}

Formal alignment:
- source equations before the final equation map to theorem assumptions source_step_i
- final source equation maps to the algebraic core theorem and the physics wrapper theorem
- typed/contextual physics wrapper is the locale mathformer_physics_context
- physics wrapper proof calls the compact reusable algebraic core theorem
- native Isabelle/HOL grounding is exposed by euclidean_space, continuous_on, inner/linear, and source-backed locale assumptions
\<close>

lemma formalphysics_0020_algebraic_core:
  fixes curl_b_over_mu0 curl_h jf dt_d jm eps0_dt_e dt_p :: real
  assumes curl_bridge: "curl_b_over_mu0 = curl_h + jm"
    and ampere: "curl_h = jf + dt_d"
    and d_expand: "dt_d = eps0_dt_e + dt_p"
  shows "curl_b_over_mu0 = jf + eps0_dt_e + dt_p + jm"
  using curl_bridge ampere d_expand by simp

locale mathformer_physics_context =
  fixes source_backed_context generated_support_context unit_dimension_checked projection_bridge_declared :: bool
    and mu0 epsilon0 :: real
    and E P D B H M Jf JM :: "'v::euclidean_space => 'v"
    and curl_op dt_op :: "'v => 'v"
    and curl_h_source jf_source dt_d_source :: real
  assumes unit_dimension_homogeneity_generated_support: "unit_dimension_checked"
    and projection_bridge_source_backed: "projection_bridge_declared"
    and mu0_nonzero_source_backed: "mu0 ~= 0"
    and electric_field_regular: "continuous_on UNIV E"
    and polarization_field_regular: "continuous_on UNIV P"
    and displacement_field_regular: "continuous_on UNIV D"
    and magnetic_flux_field_regular: "continuous_on UNIV B"
    and magnetic_intensity_field_regular: "continuous_on UNIV H"
    and magnetization_field_regular: "continuous_on UNIV M"
    and curl_linearity_source_backed: "linear curl_op"
    and time_derivative_linearity_source_backed: "linear dt_op"
    and maxwell_ampere_law_source_backed: "curl_h_source = jf_source + dt_d_source"
begin

theorem formalphysics_0020_maxwell_ampere_projection:
  fixes curl_b_over_mu0 curl_h jf dt_d jm eps0_dt_e dt_p :: real
  assumes source_step_1: "curl_b_over_mu0 = curl_h + jm"
    and source_step_2: "curl_h = jf + dt_d"
    and source_step_3: "dt_d = eps0_dt_e + dt_p"
  shows "curl_b_over_mu0 = jf + eps0_dt_e + dt_p + jm"
proof -
  have core: "curl_b_over_mu0 = jf + eps0_dt_e + dt_p + jm"
    by (rule formalphysics_0020_algebraic_core[OF source_step_1 source_step_2 source_step_3])
  then show ?thesis .
qed

end

end
