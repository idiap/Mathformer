-- SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
-- SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
-- SPDX-License-Identifier: MIT
-- Neuro-symbolic AI Group
import Mathlib

namespace MathformerPhysicsLib
namespace Foundations
namespace Contexts

/-- Mathlib grounding: generated support assumptions remain propositions, with provenance explicit. -/
structure GeneratedSupportAssumption (P : Prop) : Type where
  provenance : String
  holds : P

/-- Physics role: recover the proposition from an explicit generated-support assumption. -/
theorem generatedSupportHolds {P : Prop} (h : GeneratedSupportAssumption P) : P := h.holds

/-- Mathlib grounding: regimes and boundary contexts are propositions over existing carriers. -/
structure PhysicsContext (P : Prop) : Type where
  label : String
  holds : P

end Contexts
end Foundations
end MathformerPhysicsLib
