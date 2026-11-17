-- SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
-- SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
-- SPDX-License-Identifier: MIT
-- Neuro-symbolic AI Group
import Mathlib

namespace MathformerPhysicsLib
namespace Foundations
namespace Laws

/-- Mathlib grounding: a physical law witness is evidence for a proposition over Mathlib carriers. -/
structure PhysicalLawWitness (P : Prop) : Type where
  holds : P

/-- Physics role: classify why a physical-law witness is allowed in a generated theorem. -/
inductive PhysicalLawWitnessRole where
  | sourceLaw
  | constitutiveAssumption
  | domainAssumption
  | bridgeLemma
  | generatedSupport
  deriving DecidableEq, Repr

/-- Physics role: companion metadata for auditing `PhysicalLawWitness` usage. -/
structure PhysicalLawWitnessMetadata (P : Prop) where
  role : PhysicalLawWitnessRole
  sourceAnchor : Option String := none
  recursiveFrontier : Bool := false

/-- Physics role: recover the source-backed law proposition for downstream theorem use. -/
theorem physicalLawHolds {P : Prop} (law : PhysicalLawWitness P) : P := law.holds

end Laws
end Foundations
end MathformerPhysicsLib
