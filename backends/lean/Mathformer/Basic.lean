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
  Keep Lean-facing autoformalization artifacts buildable under the pinned mathlib environment.

Intent:
  Represent mathematical statements as explicit Lean declarations that can be checked, imported, and documented.

Function:
  Defines Lean modules, examples, and the sample executable entry point for the project.

Maintenance Notes:
  Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.
-/

import Mathlib

/--
Generated note (NL): Minimal project seed definition used by the default Lean
template.
Generated equivalent (LaTeX): this declaration has no mathematical content.
-/
def hello := "world"

/--
Generated note (NL): Basic arithmetic smoke example for commutativity of natural
number addition.
Generated equivalent (LaTeX): `a+b=b+a`.
-/
example (a b : Nat) : a + b = b + a := by
  simpa using Nat.add_comm a b
