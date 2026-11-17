<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

Intent:
  Tell coding agents what context to load, what invariants to preserve, and how to validate their work.

Function:
  Contains skill instructions, prompts, references, and scripts used by Codex-style workflows.

Maintenance Notes:
  Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.
-->

# Mathlib Compatibility Loops

## Pre-Draft Concept Loop

Runtime event sequence:

- `mathlib_concept_compatibility_loop_start`
- `mathlib_concept_compatibility_loop_iteration_start`
- `mathlib_concept_coverage_review_complete`
- `mathlib_concept_compatibility_loop_iteration_error`
- `mathlib_concept_compatibility_loop_complete`

Stop when:

- every extracted concept has a verified declaration, or
- the configured round cap is reached, or
- mapping fails before any usable concept map is produced.

## Post-Save Audit Loop

The outer workflow uses compatibility auditing after saved Lean output. Stop when:

- `compatibility_score >= compatibility_target_score`, and
- the saved Lean hard check passes when the gate requires hard success.
- the final import block has no broad `import Mathlib` unless waived and expected declarations pass under the intended imports.

If the score fails, prioritize high-severity findings, duplicate abstractions, missing native
APIs, and broad-import issues before cosmetic rewrites.
