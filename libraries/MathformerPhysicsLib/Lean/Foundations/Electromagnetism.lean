-- SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
-- SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
-- SPDX-License-Identifier: MIT
-- Neuro-symbolic AI Group
import MathformerPhysicsLib.Lean.Foundations.Fields
import MathformerPhysicsLib.Lean.Foundations.Laws

/-
Mathlib grounding: this module exposes stable electromagnetism API names over
frontier evidence records defined in `Fields` and `Laws`, whose carrier and
module structure is grounded in Mathlib additive groups, real modules, finite
indices, and scalar algebra. No independent vector-calculus replacement is
introduced here.
-/
namespace MathformerPhysicsLib
namespace Foundations
namespace Electromagnetism

open MathformerPhysicsLib.Foundations.Fields

/-- Mathlib grounding: this facade does not introduce new electromagnetic
carriers; it gives stable API names to the Mathlib-backed vector, linear-map,
and scalar evidence records owned by `Foundations.Fields`. -/
def electromagnetismFacadeGrounding : Unit := ()

/-- Reusable evidence packet for the Lorentz-force x component. -/
abbrev LorentzForceXComponentEvidence := LorentzForceXComponentFrontier

/-- Stable API name for the Lorentz-force x-component theorem. -/
theorem lorentzForceXComponent (E : LorentzForceXComponentEvidence) :
    E.force (0 : Fin 3) =
      E.charge * E.electricFieldX +
        E.charge *
          (E.velocity (1 : Fin 3) * E.magneticField (2 : Fin 3) -
            E.velocity (2 : Fin 3) * E.magneticField (1 : Fin 3)) :=
  lorentzForceXComponent_of_evidence E

/-- Reusable evidence packet for the x component of `v × curl A`. -/
abbrev LorentzCrossCurlXEvidence := LorentzCrossCurlXFrontier

/-- Stable API name for the Lorentz cross-curl x-component theorem. -/
theorem lorentzCrossCurlXComponent (E : LorentzCrossCurlXEvidence) :
    E.force (0 : Fin 3) =
      E.charge * E.electricField (0 : Fin 3) + E.charge * E.crossX :=
  lorentzCrossCurlX_of_evidence E

/-- Reusable evidence packet for the minimally-coupled Euler-Lagrange
x-force balance. -/
abbrev EulerLagrangeXForceBalanceEvidence := EulerLagrangeXForceBalanceFrontier

/-- Stable API name for the Euler-Lagrange x-force balance theorem. -/
theorem eulerLagrangeXForceBalance (E : EulerLagrangeXForceBalanceEvidence) :
    E.force (0 : Fin 3) +
        E.charge *
          (E.vectorPotentialTimeX +
            E.vectorPotentialXY * E.velocity (1 : Fin 3) +
            E.vectorPotentialXZ * E.velocity (2 : Fin 3)) =
      E.charge *
          (E.vectorPotentialYX * E.velocity (1 : Fin 3) +
            E.vectorPotentialZX * E.velocity (2 : Fin 3)) -
        E.charge * E.scalarPotentialX :=
  eulerLagrangeXForceBalance_of_evidence E

/-- Reusable evidence packet for the macroscopic Maxwell-Ampere matter law. -/
abbrev MaxwellAmpereMatterEvidence (X V : Type*) [AddCommGroup V] [Module ℝ V] :=
  MaxwellAmpereMatterFrontier X V

/-- Stable API name for the macroscopic Maxwell-Ampere matter theorem. -/
theorem maxwellAmpereMatter
    {X V : Type*} [AddCommGroup V] [Module ℝ V]
    (E : MaxwellAmpereMatterEvidence X V) :
    E.mu0⁻¹ • E.curl E.B =
      E.Jf + E.eps0 • E.timeDerivative E.E + E.timeDerivative E.P + E.JM :=
  maxwellAmpereMatter_of_evidence E

/-- Reusable evidence packet for Maxwell-Ampere with named bound currents. -/
abbrev MaxwellAmpereBoundCurrentsEvidence
    (X V : Type*) [AddCommGroup V] [Module ℝ V] :=
  MaxwellAmpereBoundCurrentsFrontier X V

/-- Stable API name for Maxwell-Ampere with named bound currents. -/
theorem maxwellAmpereBoundCurrents
    {X V : Type*} [AddCommGroup V] [Module ℝ V]
    (E : MaxwellAmpereBoundCurrentsEvidence X V) :
    E.matter.mu0⁻¹ • E.matter.curl E.matter.B =
      E.matter.Jf + E.matter.eps0 • E.matter.timeDerivative E.matter.E +
        E.JP + E.matter.JM :=
  maxwellAmpereBoundCurrents_of_evidence E

end Electromagnetism
end Foundations
end MathformerPhysicsLib
