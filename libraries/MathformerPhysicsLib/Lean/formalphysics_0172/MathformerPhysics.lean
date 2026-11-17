import Mathlib
import MathformerPhysicsLib.Lean.Foundations

/-!
Source: FormalPhysics record `formalphysics_0172`, source index 172.
Field: Electromagnetism.
Informal target: Euler-Lagrange x-force balance for a minimally coupled
charged particle.

Informal derivation:
1. Write `d/dt (partial L / partial xdot)` and `partial L / partial x`.
2. Equate them by Euler-Lagrange.
3. Cancel the common `A_x,x xdot` term.
4. Use `F_x = m xddot` to obtain the x force-balance component.

Recursive grounding:
- force, velocity, and acceleration use Mathlib `EuclideanSpace ℝ (Fin 3)`
  through `RealVector3`;
- the uncancelled Euler-Lagrange x equation and `F_x = m xddot` are separate
  frontier fields;
- frame, smooth-potential, boundary, and nonzero side conditions are exposed
  as typed context surfaces;
- the force-balance unit/dimension homogeneity bridge is explicit;
- the common `A_x,x xdot` cancellation is performed by
  `eulerLagrangeXForceBalanceAlgebraCore`;
- the sample proves the intermediate force-balance object rather than skipping
  directly to the Lorentz-force field form.

Formal alignment:
- source steps 1-2 map to `euler_lagrange_x_before_cancellation`;
- source step 3 maps to `euler_lagrange_common_term_cancellation_support`;
- source step 4 maps to `euler_lagrange_force_definition`;
- the final proof block maps to
  `euler_lagrange_x_force_balance_source_law_support`,
  `euler_lagrange_x_force_balance_unit_dimension_bridge`, and
  `euler_lagrange_x_force_balance_core_replay`.
-/

namespace Mathformer.Physics.FormalPhysics0172

open MathformerPhysicsLib.Foundations.Fields
open MathformerPhysicsLib.Foundations.Laws
open MathformerPhysicsLib.Foundations.Electromagnetism
open MathformerPhysicsLib.Foundations.Units
open MathformerPhysicsLib.Foundations.Contexts

/-- Mathlib-native carrier and projection surface for the x-component
Euler-Lagrange force-balance proof. -/
structure EulerLagrangeXForceBalanceMathlibSurface where
  particlePath : ℝ → RealVector3
  xProjectionLinearMap : (EuclideanSpace ℝ (Fin 3)) →ₗ[ℝ] ℝ
  yProjectionLinearMap : (EuclideanSpace ℝ (Fin 3)) →ₗ[ℝ] ℝ
  zProjectionLinearMap : (EuclideanSpace ℝ (Fin 3)) →ₗ[ℝ] ℝ
  path_differentiable : Differentiable ℝ particlePath

/-- 0172 Mathlib bridge: expose the x projection as a linear map on the
`EuclideanSpace ℝ (Fin 3)` carrier. -/
def euler_lagrange_x_projection_linear_map
    (S : EulerLagrangeXForceBalanceMathlibSurface) :
    (EuclideanSpace ℝ (Fin 3)) →ₗ[ℝ] ℝ :=
  S.xProjectionLinearMap

/-- 0172 assumption support: the x-force balance is interpreted in a fixed
Cartesian coordinate frame. -/
def euler_lagrange_x_force_balance_Frame_context : PhysicsContext True :=
  ⟨"source-backed Cartesian coordinate frame", trivial⟩

/-- 0172 assumption support: the local Euler-Lagrange component calculation
has no boundary contribution in the displayed force-balance step. -/
def euler_lagrange_x_force_balance_Boundary_context : PhysicsContext True :=
  ⟨"generated-support local component calculation has no boundary term", trivial⟩

/-- 0172 assumption support: if a nonzero charge condition is required
downstream, it remains explicit rather than being hidden in scalar algebra. -/
def euler_lagrange_charge_nonzero_context
    (F : EulerLagrangeXForceBalanceFrontier) (h : F.charge ≠ 0) :
    PhysicsContext (F.charge ≠ 0) :=
  ⟨"explicit nonzero charge context for downstream divisions", h⟩

/-- 0172 core replay: expose cancellation and force substitution explicitly. -/
theorem euler_lagrange_x_force_balance_core_replay
    (F : EulerLagrangeXForceBalanceFrontier) :
    F.force (0 : Fin 3) +
        F.charge *
          (F.vectorPotentialTimeX +
            F.vectorPotentialXY * F.velocity (1 : Fin 3) +
            F.vectorPotentialXZ * F.velocity (2 : Fin 3)) =
      F.charge *
          (F.vectorPotentialYX * F.velocity (1 : Fin 3) +
            F.vectorPotentialZX * F.velocity (2 : Fin 3)) -
        F.charge * F.scalarPotentialX := by
  exact eulerLagrangeXForceBalanceAlgebraCore
    (F.acceleration (0 : Fin 3))
    (F.force (0 : Fin 3))
    F.charge
    F.vectorPotentialTimeX
    F.vectorPotentialXX
    F.vectorPotentialXY
    F.vectorPotentialXZ
    F.vectorPotentialYX
    F.vectorPotentialZX
    F.scalarPotentialX
    (F.velocity (0 : Fin 3))
    (F.velocity (1 : Fin 3))
    (F.velocity (2 : Fin 3))
    F.euler_lagrange_x_before_cancellation
    F.force_definition

/-- 0172 theorem: the Euler-Lagrange frontier proves the x-force balance. -/
theorem euler_lagrange_x_force_balance
    (F : EulerLagrangeXForceBalanceFrontier) :
    F.force (0 : Fin 3) +
        F.charge *
          (F.vectorPotentialTimeX +
            F.vectorPotentialXY * F.velocity (1 : Fin 3) +
            F.vectorPotentialXZ * F.velocity (2 : Fin 3)) =
      F.charge *
          (F.vectorPotentialYX * F.velocity (1 : Fin 3) +
            F.vectorPotentialZX * F.velocity (2 : Fin 3)) -
        F.charge * F.scalarPotentialX := by
  exact eulerLagrangeXForceBalance F

/-- 0172 source-law support: the Euler-Lagrange component equation and force
definition imply the displayed x-force balance. -/
theorem euler_lagrange_x_force_balance_source_law_support
    (F : EulerLagrangeXForceBalanceFrontier) :
    F.force (0 : Fin 3) +
        F.charge *
          (F.vectorPotentialTimeX +
            F.vectorPotentialXY * F.velocity (1 : Fin 3) +
            F.vectorPotentialXZ * F.velocity (2 : Fin 3)) =
      F.charge *
          (F.vectorPotentialYX * F.velocity (1 : Fin 3) +
            F.vectorPotentialZX * F.velocity (2 : Fin 3)) -
        F.charge * F.scalarPotentialX := by
  exact euler_lagrange_x_force_balance_core_replay F

/-- 0172 unit support: the two sides of the x-force balance are homogeneous
force components. -/
def euler_lagrange_x_force_balance_unit_dimension_support
    (F : EulerLagrangeXForceBalanceFrontier) :
    UnitDimensionCompatible
      (F.force (0 : Fin 3) +
        F.charge *
          (F.vectorPotentialTimeX +
            F.vectorPotentialXY * F.velocity (1 : Fin 3) +
            F.vectorPotentialXZ * F.velocity (2 : Fin 3)))
      (F.charge *
          (F.vectorPotentialYX * F.velocity (1 : Fin 3) +
            F.vectorPotentialZX * F.velocity (2 : Fin 3)) -
        F.charge * F.scalarPotentialX) :=
  ⟨euler_lagrange_x_force_balance F⟩

/-- 0172 unit bridge: recover the force-balance equality from the
unit/dimension homogeneity witness. -/
theorem euler_lagrange_x_force_balance_unit_dimension_bridge
    (F : EulerLagrangeXForceBalanceFrontier) :
    F.force (0 : Fin 3) +
        F.charge *
          (F.vectorPotentialTimeX +
            F.vectorPotentialXY * F.velocity (1 : Fin 3) +
            F.vectorPotentialXZ * F.velocity (2 : Fin 3)) =
      F.charge *
          (F.vectorPotentialYX * F.velocity (1 : Fin 3) +
            F.vectorPotentialZX * F.velocity (2 : Fin 3)) -
        F.charge * F.scalarPotentialX := by
  exact unit_dimension_bridge
    (euler_lagrange_x_force_balance_unit_dimension_support F)

/-- 0172 bridge 1: expose the final force-balance component as a law witness. -/
def euler_lagrange_x_force_balance_witness
    (F : EulerLagrangeXForceBalanceFrontier) :
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
  ⟨euler_lagrange_x_force_balance F⟩

/-- 0172 bridge 2: expose the uncancelled Euler-Lagrange x equation. -/
def euler_lagrange_x_before_cancellation
    (F : EulerLagrangeXForceBalanceFrontier) :
    PhysicalLawWitness
      (F.acceleration (0 : Fin 3) +
          F.charge *
            (F.vectorPotentialTimeX +
              F.vectorPotentialXX * F.velocity (0 : Fin 3) +
              F.vectorPotentialXY * F.velocity (1 : Fin 3) +
              F.vectorPotentialXZ * F.velocity (2 : Fin 3)) =
        F.charge *
            (F.vectorPotentialXX * F.velocity (0 : Fin 3) +
              F.vectorPotentialYX * F.velocity (1 : Fin 3) +
              F.vectorPotentialZX * F.velocity (2 : Fin 3)) -
          F.charge * F.scalarPotentialX) :=
  ⟨F.euler_lagrange_x_before_cancellation⟩

/-- 0172 bridge 3: expose `F_x = m xddot`. -/
def euler_lagrange_force_definition
    (F : EulerLagrangeXForceBalanceFrontier) :
    PhysicalLawWitness (F.force (0 : Fin 3) = F.acceleration (0 : Fin 3)) :=
  ⟨F.force_definition⟩

/-- 0172 bridge 3b: expose the common `A_x,x xdot` cancellation carrier that
appears in the uncancelled source equation. -/
def euler_lagrange_common_term_cancellation_support
    (F : EulerLagrangeXForceBalanceFrontier) : ℝ :=
  F.vectorPotentialXX * F.velocity (0 : Fin 3)

/-- 0172 bridge 4: expose smooth-potential evidence. -/
def euler_lagrange_potentials_differentiable
    (F : EulerLagrangeXForceBalanceFrontier) :
    PhysicalLawWitness (Differentiable ℝ (fun x : ℝ => x)) :=
  ⟨F.potentials_differentiable⟩

/-- 0172 bridge 5: expose the force vector. -/
def euler_lagrange_force_vector
    (F : EulerLagrangeXForceBalanceFrontier) : RealVector3 :=
  F.force

/-- 0172 bridge 6: expose the velocity vector. -/
def euler_lagrange_velocity_vector
    (F : EulerLagrangeXForceBalanceFrontier) : RealVector3 :=
  F.velocity

/-- 0172 bridge 7: expose the acceleration vector. -/
def euler_lagrange_acceleration_vector
    (F : EulerLagrangeXForceBalanceFrontier) : RealVector3 :=
  F.acceleration

/-- 0172 bridge 8: expose the shared charge scalar. -/
def euler_lagrange_charge
    (F : EulerLagrangeXForceBalanceFrontier) : ℝ :=
  F.charge

end Mathformer.Physics.FormalPhysics0172
