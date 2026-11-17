import Mathlib
import MathformerPhysicsLib.Lean.Foundations

/-!
Source: FormalPhysics record `formalphysics_0000`, source index 0.
Field: Electromagnetism.
Informal target: x-component Lorentz force from the minimally coupled
Euler-Lagrange equation.

Recursive grounding:
- Cartesian vectors are Mathlib `EuclideanSpace ℝ (Fin 3)` through
  `RealVector3`;
- force, velocity, and magnetic field components are ordinary Mathlib vector
  projections;
- electric and magnetic field definitions are explicit frontier fields;
- the Euler-Lagrange x-component is a separate source equation;
- the final force law is proved by `lorentzForceXComponent`, with
  the scalar algebra replayed by `lorentzForceXComponentAlgebraCore`.
-/

namespace Mathformer.Physics.FormalPhysics0000

open MathformerPhysicsLib.Foundations.Fields
open MathformerPhysicsLib.Foundations.Laws
open MathformerPhysicsLib.Foundations.Electromagnetism

/-- 0000 core replay: expose the reusable scalar algebra with the concrete
component terms carried by the frontier. -/
theorem lorentz_force_x_core_replay
    (F : LorentzForceXComponentFrontier) :
    F.force (0 : Fin 3) =
      F.charge * F.electricFieldX +
        F.charge *
          (F.velocity (1 : Fin 3) * F.magneticField (2 : Fin 3) -
            F.velocity (2 : Fin 3) * F.magneticField (1 : Fin 3)) := by
  exact lorentzForceXComponentAlgebraCore
    F.charge
    (F.force (0 : Fin 3))
    F.vectorPotentialTimeX
    F.vectorPotentialXY
    F.vectorPotentialXZ
    F.vectorPotentialYX
    F.vectorPotentialZX
    F.scalarPotentialX
    (F.velocity (1 : Fin 3))
    (F.velocity (2 : Fin 3))
    F.electricFieldX
    (F.magneticField (1 : Fin 3))
    (F.magneticField (2 : Fin 3))
    F.euler_lagrange_x_component
    F.electric_field_x_from_potentials
    F.magnetic_field_y_from_potentials
    F.magnetic_field_z_from_potentials

/-- 0000 theorem: the Lorentz-force frontier proves the x-component force law. -/
theorem lorentz_force_x
    (F : LorentzForceXComponentFrontier) :
    F.force (0 : Fin 3) =
      F.charge * F.electricFieldX +
        F.charge *
          (F.velocity (1 : Fin 3) * F.magneticField (2 : Fin 3) -
            F.velocity (2 : Fin 3) * F.magneticField (1 : Fin 3)) := by
  exact lorentzForceXComponent F

/-- 0000 bridge 1: expose the final Lorentz-force component as a law witness. -/
def lorentz_force_x_witness
    (F : LorentzForceXComponentFrontier) :
    PhysicalLawWitness
      (F.force (0 : Fin 3) =
        F.charge * F.electricFieldX +
          F.charge *
            (F.velocity (1 : Fin 3) * F.magneticField (2 : Fin 3) -
              F.velocity (2 : Fin 3) * F.magneticField (1 : Fin 3))) :=
  ⟨lorentz_force_x F⟩

/-- 0000 bridge 2: expose the Euler-Lagrange source component. -/
def lorentz_euler_lagrange_x_component
    (F : LorentzForceXComponentFrontier) :
    PhysicalLawWitness
      (F.force (0 : Fin 3) +
          F.charge *
            (F.vectorPotentialTimeX +
              F.vectorPotentialXY * F.velocity (1 : Fin 3) +
              F.vectorPotentialXZ * F.velocity (2 : Fin 3)) =
        F.charge *
            (F.vectorPotentialYX * F.velocity (1 : Fin 3) +
              F.vectorPotentialZX * F.velocity (2 : Fin 3)) -
          F.charge * F.scalarPotentialX) :=
  ⟨F.euler_lagrange_x_component⟩

/-- 0000 bridge 3: expose the electric-field x-component definition. -/
def lorentz_electric_field_x_from_potentials
    (F : LorentzForceXComponentFrontier) :
    PhysicalLawWitness
      (F.electricFieldX = -(F.scalarPotentialX + F.vectorPotentialTimeX)) :=
  ⟨F.electric_field_x_from_potentials⟩

/-- 0000 bridge 4: expose the magnetic-field y-component definition. -/
def lorentz_magnetic_field_y_from_potentials
    (F : LorentzForceXComponentFrontier) :
    PhysicalLawWitness
      (F.magneticField (1 : Fin 3) =
        F.vectorPotentialXZ - F.vectorPotentialZX) :=
  ⟨F.magnetic_field_y_from_potentials⟩

/-- 0000 bridge 5: expose the magnetic-field z-component definition. -/
def lorentz_magnetic_field_z_from_potentials
    (F : LorentzForceXComponentFrontier) :
    PhysicalLawWitness
      (F.magneticField (2 : Fin 3) =
        F.vectorPotentialYX - F.vectorPotentialXY) :=
  ⟨F.magnetic_field_z_from_potentials⟩

/-- 0000 bridge 6: expose differentiability of the potential placeholder. -/
def lorentz_potentials_differentiable
    (F : LorentzForceXComponentFrontier) :
    PhysicalLawWitness (Differentiable ℝ (fun x : ℝ => x)) :=
  ⟨F.potentials_differentiable⟩

/-- 0000 bridge 7: expose the force x component. -/
def lorentz_force_x_component
    (F : LorentzForceXComponentFrontier) : ℝ :=
  F.force (0 : Fin 3)

/-- 0000 bridge 8: expose the velocity y component. -/
def lorentz_velocity_y_component
    (F : LorentzForceXComponentFrontier) : ℝ :=
  F.velocity (1 : Fin 3)

/-- 0000 bridge 9: expose the velocity z component. -/
def lorentz_velocity_z_component
    (F : LorentzForceXComponentFrontier) : ℝ :=
  F.velocity (2 : Fin 3)

/-- 0000 bridge 10: expose the magnetic y component. -/
def lorentz_magnetic_y_component
    (F : LorentzForceXComponentFrontier) : ℝ :=
  F.magneticField (1 : Fin 3)

/-- 0000 bridge 11: expose the magnetic z component. -/
def lorentz_magnetic_z_component
    (F : LorentzForceXComponentFrontier) : ℝ :=
  F.magneticField (2 : Fin 3)

end Mathformer.Physics.FormalPhysics0000
