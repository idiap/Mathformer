<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.

Intent:
  Encode regression checks that catch parser breakage, semantic drift, and missing workflow evidence.

Function:
  Contains executable tests, fixtures, and manifests used for local and CI validation.

Maintenance Notes:
  Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.
-->

# Informal ATP Test: Subset Relation Is Transitive

Source: https://proofwiki.org/wiki/Subset_Relation_is_Transitive

Informal statement:

If `R` is a subset of `S` and `S` is a subset of `T`, then `R` is a subset of `T`.

Expected ATP behavior:

The autoformalizer should emit a TPTP FOF problem using the definition of subset
in terms of element membership, then Vampire should find an SZS `Theorem` proof.
