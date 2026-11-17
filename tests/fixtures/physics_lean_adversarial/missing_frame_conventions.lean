-- SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
-- SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
-- SPDX-License-Identifier: MIT
-- Neuro-symbolic AI Group
import Mathlib

namespace Mathformer.Tests.PhysicsLeanAdversarial.ConventionGap

theorem convention_gap (A B : Real) (h : A = B) : A = B := by
  exact h

end Mathformer.Tests.PhysicsLeanAdversarial.ConventionGap
