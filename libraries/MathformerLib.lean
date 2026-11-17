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

import MathformerLib.Basic

/-!
Root module for Mathformerlib, the curated Mathformer-side library of reusable
formalizations accumulated from autoformalization runs.
`MathformerLib` is intentionally separate from `Mathformer`: draft artifacts may
live under `Mathformer`, while promoted reusable entries should be collected here
only after the Mathformerlib promotion gates pass.
-/
