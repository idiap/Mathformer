-- SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
-- SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
-- SPDX-License-Identifier: MIT
-- Neuro-symbolic AI Group
import Mathlib

structure PhysicalLawWitness (P : Prop) : Type where
  holds : P

theorem physicalLawHolds {P : Prop} (law : PhysicalLawWitness P) : P := law.holds

theorem source_law_witness_not_target
    (x y z : Nat)
    (source_law : PhysicalLawWitness (x = y))
    (bridge : y = z) :
    x = z := by
  exact Eq.trans (physicalLawHolds source_law) bridge
