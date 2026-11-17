-- SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
-- SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
-- SPDX-License-Identifier: MIT
-- Neuro-symbolic AI Group
import Mathlib

namespace Mathformer.Tests.PhysicsLeanAdversarial.RawScalarErasure

theorem raw_scalar_force (F m a : Real) : F = m * a -> F = m * a := by
  intro h
  exact h

end Mathformer.Tests.PhysicsLeanAdversarial.RawScalarErasure
