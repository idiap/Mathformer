-- SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
-- SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
-- SPDX-License-Identifier: MIT
-- Neuro-symbolic AI Group
import Mathlib

namespace Mathformer.Tests.PhysicsLeanAdversarial.TargetAsAssumption

theorem target_as_assumption (F q E : Real) (hTarget : F = q * E) :
    F = q * E := by
  simpa using hTarget

end Mathformer.Tests.PhysicsLeanAdversarial.TargetAsAssumption
