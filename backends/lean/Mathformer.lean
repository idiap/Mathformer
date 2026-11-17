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

-- This module serves as the root of the `Mathformer` library.
-- Import modules here that should be built as part of the library.
import Mathformer.Basic
import Mathformer.AutoformalizedExamples
import Mathformer.AutoformalizedSazonov
import Mathformer.AutoformalizedHilleYosida
import Mathformer.AutoformalizedChoquetTheory
import Mathformer.AutoformalizedHellysTheorem
import Mathformer.AutoformalizedRadonsTheorem
import Mathformer.AutoformalizedVCDimension
import Mathformer.AutoformalizedGrowthFunction
import Mathformer.AutoformalizedRepresenterTheorem
import Mathformer.AutoformalizedTransformerScalingLaws
import Mathformer.AutoformalizedCBTChapter1
import Mathformer.AutoformalizedCBTChapter2
import Mathformer.AutoformalizedCBTChapter3
