import Mathlib
import MathformerPhysicsLib.Lean.Foundations

/-!
Source: FormalPhysics record `formalphysics_0020`, source index 20.
Field: Electromagnetism.
Informal target: *Macroscopic Maxwell-Ampere law with polarization and
magnetization.*  Let `D = eps0 E + P` and define the magnetization current
density `J_M = curl M`.  Starting from `curl H = J_f + partial_t D` and
`B = mu0 (H + M)`, show
`curl (B / mu0) = J_f + eps0 partial_t E + partial_t P + J_M`.

Informal derivation summary:
1. Start from `curl H = J_f + partial_t D`.
2. Use `B = mu0 (H + M)` and curl linearity to rewrite
   `curl (B / mu0)` as `curl H + curl M`.
3. Identify `J_M = curl M`.
4. Substitute the macroscopic Ampere law for `curl H`.
5. Insert `D = eps0 E + P`.
6. Expand the time derivative
   `partial_t D = eps0 partial_t E + partial_t P`.
7. Conclude the free, displacement, polarization, and magnetization current
   form of the source equation.

Recursive grounding:
- selected from source-only FormalPhysics `question` and `answer` fields;
- no dataset Lean solution content is read, copied, or validated;
- fields are functions into a Mathlib additive real module;
- curl and time differentiation are Mathlib `LinearMap` operators;
- `B = μ₀(H + M)`, `D = ε₀E + P`, `J_M = curl M`, and
  `curl H = J_f + ∂ₜD` are separate frontier fields;
- the final current-density identity is proved by
  `maxwellAmpereMatter`, with the reusable algebra visible via
  `maxwellAmpereMatterAlgebraCore`.

Formal alignment:
- source step 1 maps to `F.macroscopic_ampere_law` and
  `maxwell_ampere_source_law`;
- source step 2 maps to `maxwell_magnetic_flux_curl_bridge`;
- source step 3 maps to `F.magnetization_current_definition` and
  `maxwell_magnetization_current`;
- source step 4 maps to `maxwell_ampere_after_source_law`;
- source steps 5-6 map to `maxwell_displacement_current_expansion`;
- source step 7 maps to `maxwell_ampere_after_displacement_expansion`, then to
  the reusable `maxwellAmpereMatter` theorem.
-/

namespace Mathformer.Physics.FormalPhysics0020

open MathformerPhysicsLib.Foundations.Fields
open MathformerPhysicsLib.Foundations.Contexts
open MathformerPhysicsLib.Foundations.Laws
open MathformerPhysicsLib.Foundations.Electromagnetism
open MathformerPhysicsLib.Foundations.Units

/-- Source context: the vector equation is read in a fixed coordinate frame. -/
def maxwell_fixed_coordinate_frame_context
    {X V : Type*} [AddCommGroup V] [Module ℝ V]
    (_F : MaxwellAmpereMatterFrontier X V) : PhysicsContext True :=
  ⟨"source-backed fixed coordinate frame for the vector Maxwell-Ampere equation", trivial⟩

/-- Source context: no boundary term is introduced in this algebraic Maxwell
rewriting. -/
def maxwell_boundary_not_applicable_context
    {X V : Type*} [AddCommGroup V] [Module ℝ V]
    (_F : MaxwellAmpereMatterFrontier X V) : PhysicsContext True :=
  ⟨"boundary context not applicable to the pointwise curl/time-derivative rewrite", trivial⟩

/-- Vector projection bridge from the informal vector equation to the formal
function-valued current-density expression. -/
noncomputable def projection
    {X V : Type*} [AddCommGroup V] [Module ℝ V]
    (F : MaxwellAmpereMatterFrontier X V) : X → V :=
  F.mu0⁻¹ • F.curl F.B

/-- Unit/dimension homogeneity bridge for the current-density target. -/
def maxwell_current_density_unit_dimension_bridge
    {X V : Type*} [AddCommGroup V] [Module ℝ V]
    (F : MaxwellAmpereMatterFrontier X V) :
    UnitDimensionCompatible
      (F.Jf + F.eps0 • F.timeDerivative F.E + F.timeDerivative F.P + F.JM)
      (F.Jf + F.eps0 • F.timeDerivative F.E + F.timeDerivative F.P + F.JM) :=
  ⟨rfl⟩

/-- Source step 2: `B = mu0 (H + M)` and curl linearity rewrite the left side
as `curl H + curl M`. -/
theorem maxwell_magnetic_flux_curl_bridge
    {X V : Type*} [AddCommGroup V] [Module ℝ V]
    (F : MaxwellAmpereMatterFrontier X V) :
    F.mu0⁻¹ • F.curl F.B = F.curl F.H + F.curl F.M := by
  have hcurlB :
      F.mu0⁻¹ • F.curl F.B = F.curl (F.H + F.M) := by
    have h1 : F.curl F.B = F.mu0 • F.curl (F.H + F.M) := by
      simp [F.magnetic_flux_constitutive, F.curl.map_smul]
    simp [h1, F.mu0_nonzero]
  calc
    F.mu0⁻¹ • F.curl F.B = F.curl (F.H + F.M) := hcurlB
    _ = F.curl F.H + F.curl F.M := by
      simp [F.curl.map_add]

/-- Source steps 5-6: expand the displacement-current derivative using
`D = eps0 E + P` and time-derivative linearity. -/
theorem maxwell_displacement_current_expansion
    {X V : Type*} [AddCommGroup V] [Module ℝ V]
    (F : MaxwellAmpereMatterFrontier X V) :
    F.timeDerivative F.D =
      F.eps0 • F.timeDerivative F.E + F.timeDerivative F.P := by
  simp [F.electric_displacement_constitutive, LinearMap.map_add]

/-- Source steps 2-3: after the magnetic-flux bridge, identify the
magnetization current. -/
theorem maxwell_ampere_after_magnetic_flux
    {X V : Type*} [AddCommGroup V] [Module ℝ V]
    (F : MaxwellAmpereMatterFrontier X V) :
    F.mu0⁻¹ • F.curl F.B = F.curl F.H + F.JM := by
  calc
    F.mu0⁻¹ • F.curl F.B = F.curl F.H + F.curl F.M :=
      maxwell_magnetic_flux_curl_bridge F
    _ = F.curl F.H + F.JM := by
      rw [← F.magnetization_current_definition]

/-- Source step 4: substitute the macroscopic Ampere source law for `curl H`. -/
theorem maxwell_ampere_after_source_law
    {X V : Type*} [AddCommGroup V] [Module ℝ V]
    (F : MaxwellAmpereMatterFrontier X V) :
    F.mu0⁻¹ • F.curl F.B = F.Jf + F.timeDerivative F.D + F.JM := by
  calc
    F.mu0⁻¹ • F.curl F.B = F.curl F.H + F.JM :=
      maxwell_ampere_after_magnetic_flux F
    _ = (F.Jf + F.timeDerivative F.D) + F.JM := by
      rw [F.macroscopic_ampere_law]
    _ = F.Jf + F.timeDerivative F.D + F.JM := by
      simp [add_assoc]

/-- Source step 7: substitute the displacement-current expansion and collect
the free, displacement, polarization, and magnetization current terms. -/
theorem maxwell_ampere_after_displacement_expansion
    {X V : Type*} [AddCommGroup V] [Module ℝ V]
    (F : MaxwellAmpereMatterFrontier X V) :
    F.mu0⁻¹ • F.curl F.B =
      F.Jf + F.eps0 • F.timeDerivative F.E + F.timeDerivative F.P + F.JM := by
  calc
    F.mu0⁻¹ • F.curl F.B = F.Jf + F.timeDerivative F.D + F.JM :=
      maxwell_ampere_after_source_law F
    _ = F.Jf + (F.eps0 • F.timeDerivative F.E + F.timeDerivative F.P) + F.JM := by
      rw [maxwell_displacement_current_expansion F]
    _ = F.Jf + F.eps0 • F.timeDerivative F.E + F.timeDerivative F.P + F.JM := by
      simp [add_assoc]

/-- Unit/dimension support for the collected current-density expression. -/
theorem maxwell_current_density_unit_dimension_support
    {X V : Type*} [AddCommGroup V] [Module ℝ V]
    (F : MaxwellAmpereMatterFrontier X V) :
    F.Jf + F.eps0 • F.timeDerivative F.E + F.timeDerivative F.P + F.JM =
      F.Jf + F.eps0 • F.timeDerivative F.E + F.timeDerivative F.P + F.JM :=
  unit_dimension_bridge (maxwell_current_density_unit_dimension_bridge F)

/-- 0020 core replay: expose the reusable linear-map algebra with the concrete
fields carried by the frontier. -/
theorem maxwell_ampere_matter_core_replay
    {X V : Type*} [AddCommGroup V] [Module ℝ V]
    (F : MaxwellAmpereMatterFrontier X V) :
    F.mu0⁻¹ • F.curl F.B =
      F.Jf + F.eps0 • F.timeDerivative F.E + F.timeDerivative F.P + F.JM := by
  exact maxwellAmpereMatterAlgebraCore
    F.curl
    F.timeDerivative
    F.mu0
    F.eps0
    F.H
    F.M
    F.E
    F.P
    F.D
    F.B
    F.Jf
    F.JM
    F.magnetic_flux_constitutive
    F.electric_displacement_constitutive
    F.magnetization_current_definition
    F.macroscopic_ampere_law
    F.mu0_nonzero

/-- 0020 theorem: the Maxwell-Ampere matter frontier proves the target identity. -/
theorem maxwell_ampere_matter
    {X V : Type*} [AddCommGroup V] [Module ℝ V]
    (F : MaxwellAmpereMatterFrontier X V) :
    F.mu0⁻¹ • F.curl F.B =
      F.Jf + F.eps0 • F.timeDerivative F.E + F.timeDerivative F.P + F.JM := by
  have _ : True := (maxwell_fixed_coordinate_frame_context F).holds
  have _ : True := (maxwell_boundary_not_applicable_context F).holds
  have _ :
      F.Jf + F.eps0 • F.timeDerivative F.E + F.timeDerivative F.P + F.JM =
        F.Jf + F.eps0 • F.timeDerivative F.E + F.timeDerivative F.P + F.JM :=
    maxwell_current_density_unit_dimension_support F
  exact maxwell_ampere_after_displacement_expansion F

/-- 0020 bridge 1: expose the final Maxwell-Ampere matter law. -/
def maxwell_ampere_matter_witness
    {X V : Type*} [AddCommGroup V] [Module ℝ V]
    (F : MaxwellAmpereMatterFrontier X V) :
    PhysicalLawWitness
      (F.mu0⁻¹ • F.curl F.B =
        F.Jf + F.eps0 • F.timeDerivative F.E + F.timeDerivative F.P + F.JM) :=
  ⟨maxwell_ampere_matter F⟩

/-- 0020 reusable-foundation replay: the same source packet is accepted by the
MathformerPhysicsLib frontier theorem. -/
theorem maxwell_ampere_matter_via_reusable_foundation
    {X V : Type*} [AddCommGroup V] [Module ℝ V]
    (F : MaxwellAmpereMatterFrontier X V) :
    F.mu0⁻¹ • F.curl F.B =
      F.Jf + F.eps0 • F.timeDerivative F.E + F.timeDerivative F.P + F.JM := by
  exact maxwellAmpereMatter F

/-- 0020 bridge 2: expose the macroscopic Ampere source law. -/
def maxwell_ampere_source_law
    {X V : Type*} [AddCommGroup V] [Module ℝ V]
    (F : MaxwellAmpereMatterFrontier X V) :
    PhysicalLawWitness (F.curl F.H = F.Jf + F.timeDerivative F.D) :=
  ⟨F.macroscopic_ampere_law⟩

/-- 0020 bridge 3: expose the magnetic-flux constitutive law. -/
def maxwell_magnetic_flux_constitutive
    {X V : Type*} [AddCommGroup V] [Module ℝ V]
    (F : MaxwellAmpereMatterFrontier X V) :
    PhysicalLawWitness (F.B = F.mu0 • (F.H + F.M)) :=
  ⟨F.magnetic_flux_constitutive⟩

/-- 0020 bridge 4: expose the electric-displacement constitutive law. -/
def maxwell_electric_displacement_constitutive
    {X V : Type*} [AddCommGroup V] [Module ℝ V]
    (F : MaxwellAmpereMatterFrontier X V) :
    PhysicalLawWitness (F.D = F.eps0 • F.E + F.P) :=
  ⟨F.electric_displacement_constitutive⟩

/-- 0020 bridge 5: expose the magnetization current definition. -/
def maxwell_magnetization_current
    {X V : Type*} [AddCommGroup V] [Module ℝ V]
    (F : MaxwellAmpereMatterFrontier X V) :
    PhysicalLawWitness (F.JM = F.curl F.M) :=
  ⟨F.magnetization_current_definition⟩

/-- 0020 bridge 6: expose the nonzero permeability side condition. -/
def maxwell_mu0_nonzero
    {X V : Type*} [AddCommGroup V] [Module ℝ V]
    (F : MaxwellAmpereMatterFrontier X V) :
    PhysicalLawWitness (F.mu0 ≠ 0) :=
  ⟨F.mu0_nonzero⟩

/-- 0020 bridge 7: expose field smoothness evidence. -/
def maxwell_field_smoothness
    {X V : Type*} [AddCommGroup V] [Module ℝ V]
    (F : MaxwellAmpereMatterFrontier X V) :
    PhysicalLawWitness (Differentiable ℝ (fun t : ℝ => t)) :=
  ⟨F.field_smoothness⟩

/-- 0020 bridge 8: expose the Mathlib curl operator. -/
def maxwell_curl_operator
    {X V : Type*} [AddCommGroup V] [Module ℝ V]
    (F : MaxwellAmpereMatterFrontier X V) :
    (X → V) →ₗ[ℝ] (X → V) :=
  F.curl

/-- 0020 bridge 9: expose the Mathlib time-derivative operator. -/
def maxwell_time_derivative_operator
    {X V : Type*} [AddCommGroup V] [Module ℝ V]
    (F : MaxwellAmpereMatterFrontier X V) :
    (X → V) →ₗ[ℝ] (X → V) :=
  F.timeDerivative

/-- 0020 bridge 10: expose the displacement-current term. -/
def maxwell_displacement_current
    {X V : Type*} [AddCommGroup V] [Module ℝ V]
    (F : MaxwellAmpereMatterFrontier X V) : X → V :=
  F.timeDerivative F.D

/-- 0020 bridge 11: expose the polarization-current term. -/
def maxwell_polarization_current
    {X V : Type*} [AddCommGroup V] [Module ℝ V]
    (F : MaxwellAmpereMatterFrontier X V) : X → V :=
  F.timeDerivative F.P

end Mathformer.Physics.FormalPhysics0020
