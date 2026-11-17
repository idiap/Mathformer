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
  Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.

Intent:
  Encode regression checks that catch parser breakage, semantic drift, and missing workflow evidence.

Function:
  Contains executable tests, fixtures, and manifests used for local and CI validation.

Maintenance Notes:
  Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.
-/

/--
Original source (NL): For every natural number n, n = n.
Original source (LaTeX): \forall n \in \mathbb{N}, n = n.
Source anchors: src_L0001
-/
theorem source_drift_missing_anchor (n : Nat) : n = n := rfl

theorem source_backed_without_anchor (n : Nat) : n = n := rfl
