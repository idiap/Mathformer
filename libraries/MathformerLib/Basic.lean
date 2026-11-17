/-
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
#
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# Neuro-symbolic AI Group
#
# SPDX-License-Identifier: MIT
-/

/-
File Documentation

Motivation:
  Collect reusable Mathformer library components separately from one-off examples and experiments.

Intent:
  Expose promoted code and documentation surfaces that other workflows can depend on.

Function:
  Defines library modules, helpers, and symbolic examples used by tests and generated docs.

Maintenance Notes:
  Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.
-/

import Mathlib

/-!
Basic namespace and seed declarations for Mathformerlib.
This file is deliberately small. Generated formalizations should be promoted into
topic-specific `MathformerLib.*` modules after registry and promotion checks.
-/

namespace MathformerLib

/--
Generated note (NL): Smoke theorem proving that the Mathformerlib root builds.
Generated equivalent (LaTeX): `\top`.
-/
theorem true_intro : True := by
  trivial

end MathformerLib
