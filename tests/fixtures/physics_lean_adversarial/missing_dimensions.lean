-- SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
-- SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
-- SPDX-License-Identifier: MIT
-- Neuro-symbolic AI Group
import Mathlib

namespace Mathformer.Tests.PhysicsLeanAdversarial.MissingDimensions

theorem kinetic_energy_scalar (K m v : Real) (h : K = (m * v * v) / 2) :
    K = (m * v * v) / 2 := by
  exact h

end Mathformer.Tests.PhysicsLeanAdversarial.MissingDimensions
