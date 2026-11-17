-- SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
-- SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
-- SPDX-License-Identifier: MIT
-- Neuro-symbolic AI Group
import Mathlib

namespace MathformerPhysicsLib
namespace Foundations
namespace Units

/-- Mathlib grounding: dimension compatibility is a proposition over existing Mathlib values. -/
structure DimensionCompatible {α : Type*} (lhs rhs : α) : Type where
  relation : lhs = rhs

/-- Physics role: recover the equality carried by a dimension-compatibility witness. -/
theorem dimensionCompatibleEq {α : Type*} {lhs rhs : α}
    (h : DimensionCompatible lhs rhs) : lhs = rhs := h.relation

/-- Compatibility name used by workflow gates for unit/dimension homogeneity.
It is an alias for `DimensionCompatible`, not a parallel unit system. -/
abbrev UnitDimensionCompatible {α : Type*} (lhs rhs : α) : Type :=
  DimensionCompatible lhs rhs

/-- Physics role: expose a named unit/dimension bridge for workflow-recognized
homogeneity obligations. -/
theorem unit_dimension_bridge {α : Type*} {lhs rhs : α}
    (h : UnitDimensionCompatible lhs rhs) : lhs = rhs :=
  dimensionCompatibleEq h

end Units
end Foundations
end MathformerPhysicsLib
