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

# Mathlib API Compatibility Plan

## Planning Order

1. Verified declarations with `check_ok: true`.
2. Relevant mathlib modules/imports for navigation.
3. Planned imports from `mathlib-import-set-builder` after `lean-import-context-verifier` has checked expected declarations when available.
4. Unverified candidates with source references, marked as candidates.
5. Explicit gaps for concepts without verified coverage.
6. One local abstraction boundary only when no native mathlib concept is available.

## Anti-Duplication Rules

- Do not introduce local predicates that duplicate native mathlib predicates.
- Do not create wrapper structures when typeclasses or bundled mathlib structures exist.
- Do not use broad imports as a substitute for verified declarations.
- Do not present a declaration as available under the final import block until the import-context verifier has checked it or the gap is explicit.
- Do not hide concept gaps inside theorem assumptions; name the gap explicitly.
