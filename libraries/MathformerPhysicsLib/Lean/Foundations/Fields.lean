-- SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
-- SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
-- SPDX-License-Identifier: MIT
-- Neuro-symbolic AI Group
import Mathlib

namespace MathformerPhysicsLib
namespace Foundations
namespace Fields

/-- Mathlib grounding: finite-dimensional real vectors use `EuclideanSpace ℝ (Fin 3)`. -/
abbrev RealVector3 := EuclideanSpace ℝ (Fin 3)

/-- Mathlib grounding: a physics vector field is a function into a Mathlib vector carrier. -/
abbrev RealVectorField3 (X : Type*) := X → RealVector3

/-- Physics role: explicit evaluation bridge for vector-field source statements. -/
def evalRealVectorField3 {X : Type*} (F : RealVectorField3 X) (x : X) : RealVector3 := F x

/-- Mathlib grounding: field evaluation is ordinary function application. -/
theorem evalRealVectorField3_apply {X : Type*} (F : RealVectorField3 X) (x : X) :
    evalRealVectorField3 F x = F x := rfl

/-- Algebra core for the Lorentz-force x component from the x
Euler-Lagrange rearrangement and electromagnetic potential definitions. -/
theorem lorentzForceXComponentAlgebraCore
    (q F Axt Axy Axz Ayx Azx phix ydot zdot Ex By Bz : ℝ)
    (hEL :
      F + q * (Axt + Axy * ydot + Axz * zdot)
        = q * (Ayx * ydot + Azx * zdot) - q * phix)
    (hEx : Ex = -(phix + Axt))
    (hBy : By = Axz - Azx)
    (hBz : Bz = Ayx - Axy) :
    F = q * Ex + q * (ydot * Bz - zdot * By) := by
  have hsolve :
      F
        = -q * (Axt + Axy * ydot + Axz * zdot)
          + q * (Ayx * ydot + Azx * zdot)
          - q * phix := by
    linarith
  calc
    F
        = -q * (Axt + Axy * ydot + Axz * zdot)
          + q * (Ayx * ydot + Azx * zdot)
          - q * phix := hsolve
    _ = -q * Axt - q * Axy * ydot
          - q * Axz * zdot
          + q * Ayx * ydot + q * Azx * zdot
          - q * phix := by
      ring
    _ = q * (-(phix + Axt))
          + q * (ydot * (Ayx - Axy))
          + q * (zdot * (Azx - Axz)) := by
      ring
    _ = q * Ex + q * (ydot * Bz)
          + q * (zdot * (-By)) := by
      simp [hEx, hBy, hBz, sub_eq_add_neg]
    _ = q * Ex + q * (ydot * Bz - zdot * By) := by
      ring

/-- Frontier 0000-1: typed source evidence for the x component of the
Lorentz force obtained from the minimally coupled Euler-Lagrange equation. -/
structure LorentzForceXComponentFrontier where
  charge : ℝ
  force : RealVector3
  velocity : RealVector3
  magneticField : RealVector3
  electricFieldX : ℝ
  vectorPotentialTimeX : ℝ
  vectorPotentialYX : ℝ
  vectorPotentialZX : ℝ
  vectorPotentialXY : ℝ
  vectorPotentialXZ : ℝ
  scalarPotentialX : ℝ
  potentials_differentiable : Differentiable ℝ (fun x : ℝ => x)
  euler_lagrange_x_component :
    force (0 : Fin 3) +
        charge *
          (vectorPotentialTimeX +
            vectorPotentialXY * velocity (1 : Fin 3) +
            vectorPotentialXZ * velocity (2 : Fin 3)) =
      charge *
          (vectorPotentialYX * velocity (1 : Fin 3) +
            vectorPotentialZX * velocity (2 : Fin 3)) -
        charge * scalarPotentialX
  electric_field_x_from_potentials :
    electricFieldX = -(scalarPotentialX + vectorPotentialTimeX)
  magnetic_field_y_from_potentials :
    magneticField (1 : Fin 3) = vectorPotentialXZ - vectorPotentialZX
  magnetic_field_z_from_potentials :
    magneticField (2 : Fin 3) = vectorPotentialYX - vectorPotentialXY

/-- Frontier support: the Lorentz-force x-component frontier proves the source
component equation from the Euler-Lagrange and potential-definition evidence. -/
theorem lorentzForceXComponent_of_evidence (F : LorentzForceXComponentFrontier) :
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

/-- Algebra core for the x component of `v × curl A` inside the Lorentz-force
projection. -/
theorem lorentzCrossCurlXAlgebraCore
    (q Ex Fx crossX ydot zdot curlAy curlAz Axy Axz Ayx Azx : ℝ)
    (cross_x_component : crossX = ydot * curlAz - zdot * curlAy)
    (curl_y_from_potential : curlAy = Axz - Azx)
    (curl_z_from_potential : curlAz = Ayx - Axy)
    (expanded_force_component :
      Fx = q * Ex + q * ydot * (Ayx - Axy) + q * zdot * (Azx - Axz)) :
    Fx = q * Ex + q * crossX := by
  rw [expanded_force_component, cross_x_component, curl_y_from_potential,
    curl_z_from_potential]
  ring

/-- Frontier 0119-1: typed source evidence for expanding the x component of
`velocity × curl A` and repackaging the Lorentz-force component. -/
structure LorentzCrossCurlXFrontier where
  charge : ℝ
  force : RealVector3
  velocity : RealVector3
  electricField : RealVector3
  curlA : RealVector3
  crossX : ℝ
  vectorPotentialXY : ℝ
  vectorPotentialXZ : ℝ
  vectorPotentialYX : ℝ
  vectorPotentialZX : ℝ
  potentials_differentiable : Differentiable ℝ (fun x : ℝ => x)
  cross_x_component :
    crossX =
      velocity (1 : Fin 3) * curlA (2 : Fin 3) -
        velocity (2 : Fin 3) * curlA (1 : Fin 3)
  curl_y_from_potential :
    curlA (1 : Fin 3) = vectorPotentialXZ - vectorPotentialZX
  curl_z_from_potential :
    curlA (2 : Fin 3) = vectorPotentialYX - vectorPotentialXY
  expanded_force_component :
    force (0 : Fin 3) =
      charge * electricField (0 : Fin 3) +
        charge * velocity (1 : Fin 3) *
          (vectorPotentialYX - vectorPotentialXY) +
        charge * velocity (2 : Fin 3) *
          (vectorPotentialZX - vectorPotentialXZ)

/-- Frontier support: the cross-curl x frontier proves the repackaged
Lorentz-force component. -/
theorem lorentzCrossCurlX_of_evidence (F : LorentzCrossCurlXFrontier) :
    F.force (0 : Fin 3) =
      F.charge * F.electricField (0 : Fin 3) + F.charge * F.crossX := by
  exact lorentzCrossCurlXAlgebraCore
    F.charge
    (F.electricField (0 : Fin 3))
    (F.force (0 : Fin 3))
    F.crossX
    (F.velocity (1 : Fin 3))
    (F.velocity (2 : Fin 3))
    (F.curlA (1 : Fin 3))
    (F.curlA (2 : Fin 3))
    F.vectorPotentialXY
    F.vectorPotentialXZ
    F.vectorPotentialYX
    F.vectorPotentialZX
    F.cross_x_component
    F.curl_y_from_potential
    F.curl_z_from_potential
    F.expanded_force_component

/-- Algebra core for the Euler-Lagrange x-force balance after the common
`A_x,x xdot` term has been cancelled and `F_x = m xddot` has been substituted. -/
theorem eulerLagrangeXForceBalanceAlgebraCore
    (mddx Fx q Axt Axx Axy Axz Ayx Azx phix xdot ydot zdot : ℝ)
    (euler_lagrange_x_before_cancellation :
      mddx + q * (Axt + Axx * xdot + Axy * ydot + Axz * zdot)
        = q * (Axx * xdot + Ayx * ydot + Azx * zdot) - q * phix)
    (force_definition : Fx = mddx) :
    Fx + q * (Axt + Axy * ydot + Axz * zdot)
      = q * (Ayx * ydot + Azx * zdot) - q * phix := by
  subst Fx
  nlinarith

/-- Frontier 0172-1: typed source evidence for the minimally coupled
Euler-Lagrange x-force balance before rewriting it into electric and magnetic
field components. -/
structure EulerLagrangeXForceBalanceFrontier where
  charge : ℝ
  force : RealVector3
  velocity : RealVector3
  acceleration : RealVector3
  vectorPotentialTimeX : ℝ
  vectorPotentialXX : ℝ
  vectorPotentialXY : ℝ
  vectorPotentialXZ : ℝ
  vectorPotentialYX : ℝ
  vectorPotentialZX : ℝ
  scalarPotentialX : ℝ
  potentials_differentiable : Differentiable ℝ (fun x : ℝ => x)
  force_definition : force (0 : Fin 3) = acceleration (0 : Fin 3)
  euler_lagrange_x_before_cancellation :
    acceleration (0 : Fin 3) +
        charge *
          (vectorPotentialTimeX +
            vectorPotentialXX * velocity (0 : Fin 3) +
            vectorPotentialXY * velocity (1 : Fin 3) +
            vectorPotentialXZ * velocity (2 : Fin 3)) =
      charge *
          (vectorPotentialXX * velocity (0 : Fin 3) +
            vectorPotentialYX * velocity (1 : Fin 3) +
            vectorPotentialZX * velocity (2 : Fin 3)) -
        charge * scalarPotentialX

/-- Frontier support: the Euler-Lagrange x-force balance frontier proves the
component equation after cancellation and force substitution. -/
theorem eulerLagrangeXForceBalance_of_evidence
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

/-- Algebra core for the macroscopic Maxwell-Ampere matter identity using
Mathlib linear maps for curl and time differentiation. -/
theorem maxwellAmpereMatterAlgebraCore
    {X V : Type*} [AddCommGroup V] [Module ℝ V]
    (curl timeDerivative : (X → V) →ₗ[ℝ] (X → V))
    (mu0 eps0 : ℝ)
    (H M E P D B Jf JM : X → V)
    (magnetic_flux_constitutive : B = mu0 • (H + M))
    (electric_displacement_constitutive : D = eps0 • E + P)
    (magnetization_current_definition : JM = curl M)
    (macroscopic_ampere_law : curl H = Jf + timeDerivative D)
    (mu0_nonzero : mu0 ≠ 0) :
    mu0⁻¹ • curl B = Jf + eps0 • timeDerivative E + timeDerivative P + JM := by
  classical
  have hcurlB :
      mu0⁻¹ • curl B = curl (H + M) := by
    have h1 : curl B = mu0 • curl (H + M) := by
      simp [magnetic_flux_constitutive, curl.map_smul]
    simp [h1, mu0_nonzero]
  have htdD : timeDerivative D = eps0 • timeDerivative E + timeDerivative P := by
    simp [electric_displacement_constitutive, LinearMap.map_add]
  have hsum :
      curl (H + M) = Jf + (eps0 • timeDerivative E + timeDerivative P) + curl M := by
    calc
      curl (H + M) = curl H + curl M := by
        simp [curl.map_add]
      _ = (Jf + timeDerivative D) + curl M := by
        simp [macroscopic_ampere_law]
      _ = Jf + (eps0 • timeDerivative E + timeDerivative P) + curl M := by
        simp [htdD, add_assoc]
  calc
    mu0⁻¹ • curl B = curl (H + M) := hcurlB
    _ = Jf + (eps0 • timeDerivative E + timeDerivative P) + curl M := hsum
    _ = Jf + eps0 • timeDerivative E + timeDerivative P + JM := by
      simp [magnetization_current_definition, add_assoc]

/-- Frontier 0020-1: typed source evidence for the macroscopic
Maxwell-Ampere law with polarization and magnetization current terms. -/
structure MaxwellAmpereMatterFrontier (X V : Type*) [AddCommGroup V] [Module ℝ V] where
  curl : (X → V) →ₗ[ℝ] (X → V)
  timeDerivative : (X → V) →ₗ[ℝ] (X → V)
  mu0 : ℝ
  eps0 : ℝ
  H : X → V
  M : X → V
  E : X → V
  P : X → V
  D : X → V
  B : X → V
  Jf : X → V
  JM : X → V
  field_smoothness : Differentiable ℝ (fun t : ℝ => t)
  mu0_nonzero : mu0 ≠ 0
  magnetic_flux_constitutive : B = mu0 • (H + M)
  electric_displacement_constitutive : D = eps0 • E + P
  magnetization_current_definition : JM = curl M
  macroscopic_ampere_law : curl H = Jf + timeDerivative D

/-- Frontier support: the Maxwell-Ampere matter frontier proves the
free-current, displacement-current, polarization-current, and
magnetization-current form of the source equation. -/
theorem maxwellAmpereMatter_of_evidence
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

/-- Frontier 0054-1: the macroscopic Maxwell-Ampere matter frontier with an
explicit named polarization current `J_P = ∂ₜP`. -/
structure MaxwellAmpereBoundCurrentsFrontier (X V : Type*) [AddCommGroup V] [Module ℝ V] where
  matter : MaxwellAmpereMatterFrontier X V
  JP : X → V
  polarization_current_definition : JP = matter.timeDerivative matter.P

/-- Frontier support: the bound-current frontier rewrites the polarization
current term into the explicit `J_P` current used by the source statement. -/
theorem maxwellAmpereBoundCurrents_of_evidence
    {X V : Type*} [AddCommGroup V] [Module ℝ V]
    (F : MaxwellAmpereBoundCurrentsFrontier X V) :
    F.matter.mu0⁻¹ • F.matter.curl F.matter.B =
      F.matter.Jf + F.matter.eps0 • F.matter.timeDerivative F.matter.E +
        F.JP + F.matter.JM := by
  simpa [F.polarization_current_definition, add_assoc] using
    maxwellAmpereMatter_of_evidence F.matter

end Fields
end Foundations
end MathformerPhysicsLib
