-- SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
-- SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
-- SPDX-License-Identifier: MIT
-- Neuro-symbolic AI Group
import Mathlib

namespace MathformerPhysicsLib
namespace Foundations
namespace Operators

/-- Mathlib grounding: fields are functions into `EuclideanSpace ℝ (Fin 3)`. -/
abbrev RealVector3 := EuclideanSpace ℝ (Fin 3)

/-- Mathlib grounding: a field operator should use `LinearMap` when linearity is required. -/
abbrev LinearFieldOperator (X : Type*) := (X → RealVector3) →ₗ[ℝ] (X → RealVector3)

/-- Physics role: apply a Mathlib-backed linear operator to a vector field. -/
def applyLinearFieldOperator {X : Type*} (L : LinearFieldOperator X) (F : X → RealVector3) :
    X → RealVector3 := L F

/-- Mathlib grounding: commutators are represented as algebraic multiplication differences. -/
def commutator {A : Type*} [Mul A] [Sub A] (x y : A) : A := x * y - y * x

end Operators
end Foundations
end MathformerPhysicsLib
