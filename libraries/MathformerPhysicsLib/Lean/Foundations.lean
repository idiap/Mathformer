-- SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
-- SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
-- SPDX-License-Identifier: MIT
-- Neuro-symbolic AI Group
import Mathlib
import MathformerPhysicsLib.Lean.Foundations.Carriers
import MathformerPhysicsLib.Lean.Foundations.Contexts
import MathformerPhysicsLib.Lean.Foundations.Electromagnetism
import MathformerPhysicsLib.Lean.Foundations.Fields
import MathformerPhysicsLib.Lean.Foundations.HilbertSpace
import MathformerPhysicsLib.Lean.Foundations.Laws
import MathformerPhysicsLib.Lean.Foundations.Operators
import MathformerPhysicsLib.Lean.Foundations.PositionMomentumModels
import MathformerPhysicsLib.Lean.Foundations.QuantumDynamics
import MathformerPhysicsLib.Lean.Foundations.QuantumMechanicsExamples
import MathformerPhysicsLib.Lean.Foundations.UnboundedOperators
import MathformerPhysicsLib.Lean.Foundations.Units
import MathformerPhysicsLib.Lean.Foundations.VariationalCalculus
import MathformerPhysicsLib.Lean.Foundations.VectorCalculus

/-!
# MathformerPhysicsLib Lean Foundations

Accepted foundation support should preserve Mathlib-native carriers and expose
level-0 physics-specific bridges for laws, units, contexts, and reusable
operator surfaces. Richer physics-facing APIs must enter the recursive
foundation promotion frontier before downstream theorem repair may depend on
them as accepted support.
-/
