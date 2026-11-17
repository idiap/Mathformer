-- SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
-- SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
-- SPDX-License-Identifier: MIT
-- Neuro-symbolic AI Group
import Mathlib

namespace MathformerPhysicsLib
namespace Foundations
namespace Carriers

/-- Mathlib grounding: finite-dimensional real vectors use `EuclideanSpace ℝ (Fin 3)`. -/
abbrev RealVector3 := EuclideanSpace ℝ (Fin 3)

/-- Mathlib grounding: component projection is ordinary function application on `Fin 3`. -/
def realVector3Component (v : RealVector3) (i : Fin 3) : ℝ := v i

/-- Mathlib grounding: the component bridge is definitional for `EuclideanSpace` coordinates. -/
theorem realVector3Component_apply (v : RealVector3) (i : Fin 3) :
    realVector3Component v i = v i := rfl

/-- Mathlib grounding: Hilbert-style states should use existing inner-product-space structures. -/
abbrev HilbertStateCarrier (𝕜 : Type*) (H : Type*) [RCLike 𝕜] [NormedAddCommGroup H]
    [InnerProductSpace 𝕜 H] := H

end Carriers
end Foundations
end MathformerPhysicsLib
