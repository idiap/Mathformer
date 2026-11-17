import Mathlib
import MathformerPhysicsLib.Lean.Foundations

/-!
Source: FormalPhysics record `formalphysics_0054`, source index 54.
Field: Electromagnetism.
Informal target: Ampere-Maxwell in matter with named bound polarization and
magnetization currents.

Recursive grounding:
- fields are Mathlib module-valued functions as in the 0020 Maxwell-Ampere
  frontier;
- the 0054-specific layer adds the named polarization current `J_P = ∂ₜP`;
- the magnetization current remains the source-backed `J_M = curl M` field in
  the underlying matter frontier;
- the final bound-current equation is proved by
  `maxwellAmpereBoundCurrents`.
-/

namespace Mathformer.Physics.FormalPhysics0054

open MathformerPhysicsLib.Foundations.Fields
open MathformerPhysicsLib.Foundations.Laws
open MathformerPhysicsLib.Foundations.Electromagnetism

/-- 0054 core replay: expose the bound-current rewrite on top of the 0020
Maxwell-Ampere matter derivation. -/
theorem ampere_matter_bound_currents_core_replay
    {X V : Type*} [AddCommGroup V] [Module ℝ V]
    (F : MaxwellAmpereBoundCurrentsFrontier X V) :
    F.matter.mu0⁻¹ • F.matter.curl F.matter.B =
      F.matter.Jf + F.matter.eps0 • F.matter.timeDerivative F.matter.E +
        F.JP + F.matter.JM := by
  have h_matter := maxwellAmpereMatter F.matter
  simpa [F.polarization_current_definition, add_assoc] using h_matter

/-- 0054 theorem: the bound-current frontier proves the source target. -/
theorem ampere_matter_bound_currents
    {X V : Type*} [AddCommGroup V] [Module ℝ V]
    (F : MaxwellAmpereBoundCurrentsFrontier X V) :
    F.matter.mu0⁻¹ • F.matter.curl F.matter.B =
      F.matter.Jf + F.matter.eps0 • F.matter.timeDerivative F.matter.E +
        F.JP + F.matter.JM := by
  exact maxwellAmpereBoundCurrents F

/-- 0054 bridge 1: expose the final bound-current law. -/
def ampere_matter_bound_currents_witness
    {X V : Type*} [AddCommGroup V] [Module ℝ V]
    (F : MaxwellAmpereBoundCurrentsFrontier X V) :
    PhysicalLawWitness
      (F.matter.mu0⁻¹ • F.matter.curl F.matter.B =
        F.matter.Jf + F.matter.eps0 • F.matter.timeDerivative F.matter.E +
          F.JP + F.matter.JM) :=
  ⟨ampere_matter_bound_currents F⟩

/-- 0054 bridge 2: expose the polarization-current definition. -/
def ampere_polarization_current
    {X V : Type*} [AddCommGroup V] [Module ℝ V]
    (F : MaxwellAmpereBoundCurrentsFrontier X V) :
    PhysicalLawWitness (F.JP = F.matter.timeDerivative F.matter.P) :=
  ⟨F.polarization_current_definition⟩

/-- 0054 bridge 3: expose the magnetization-current definition. -/
def ampere_magnetization_current
    {X V : Type*} [AddCommGroup V] [Module ℝ V]
    (F : MaxwellAmpereBoundCurrentsFrontier X V) :
    PhysicalLawWitness (F.matter.JM = F.matter.curl F.matter.M) :=
  ⟨F.matter.magnetization_current_definition⟩

/-- 0054 bridge 4: expose the underlying macroscopic Ampere source law. -/
def ampere_bound_currents_source_law
    {X V : Type*} [AddCommGroup V] [Module ℝ V]
    (F : MaxwellAmpereBoundCurrentsFrontier X V) :
    PhysicalLawWitness
      (F.matter.curl F.matter.H = F.matter.Jf + F.matter.timeDerivative F.matter.D) :=
  ⟨F.matter.macroscopic_ampere_law⟩

/-- 0054 bridge 5: expose `B = μ₀(H + M)`. -/
def ampere_bound_currents_magnetic_flux_constitutive
    {X V : Type*} [AddCommGroup V] [Module ℝ V]
    (F : MaxwellAmpereBoundCurrentsFrontier X V) :
    PhysicalLawWitness (F.matter.B = F.matter.mu0 • (F.matter.H + F.matter.M)) :=
  ⟨F.matter.magnetic_flux_constitutive⟩

/-- 0054 bridge 6: expose `D = ε₀E + P`. -/
def ampere_bound_currents_electric_displacement_constitutive
    {X V : Type*} [AddCommGroup V] [Module ℝ V]
    (F : MaxwellAmpereBoundCurrentsFrontier X V) :
    PhysicalLawWitness (F.matter.D = F.matter.eps0 • F.matter.E + F.matter.P) :=
  ⟨F.matter.electric_displacement_constitutive⟩

/-- 0054 bridge 7: expose nonzero permeability. -/
def ampere_bound_currents_mu0_nonzero
    {X V : Type*} [AddCommGroup V] [Module ℝ V]
    (F : MaxwellAmpereBoundCurrentsFrontier X V) :
    PhysicalLawWitness (F.matter.mu0 ≠ 0) :=
  ⟨F.matter.mu0_nonzero⟩

/-- 0054 bridge 8: expose the named polarization-current field. -/
def ampere_bound_currents_JP
    {X V : Type*} [AddCommGroup V] [Module ℝ V]
    (F : MaxwellAmpereBoundCurrentsFrontier X V) : X → V :=
  F.JP

/-- 0054 bridge 9: expose the named magnetization-current field. -/
def ampere_bound_currents_JM
    {X V : Type*} [AddCommGroup V] [Module ℝ V]
    (F : MaxwellAmpereBoundCurrentsFrontier X V) : X → V :=
  F.matter.JM

/-- 0054 bridge 10: expose the underlying matter frontier for recursive reuse. -/
def ampere_bound_currents_matter_frontier
    {X V : Type*} [AddCommGroup V] [Module ℝ V]
    (F : MaxwellAmpereBoundCurrentsFrontier X V) :
    MaxwellAmpereMatterFrontier X V :=
  F.matter

end Mathformer.Physics.FormalPhysics0054
