---
name: mathlib-compatibility-auditor
description: Compatibility wrapper for the legacy Lean/mathlib compatibility audit script. Use when maintaining scripts/check_mathlib_compat.py, preserving older compatibility-report calls, or routing compile and abstraction-audit work to the specialized skills.
---
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

# Mathlib Compatibility Auditor Wrapper

## Status

This skill is now a compatibility wrapper. The shared runtime remains here:

- `scripts/check_mathlib_compat.py`
- `references/mathlib_compatibility_checklist.md` as legacy checklist material

## Use The Specialized Skills

- `lean-compile-checker`: run concrete `lake env lean` checks and capture compiler diagnostics.
- `mathlib-abstraction-auditor`: audit mathlib-native reuse, abstraction-boundary discipline, theorem-layer shape, API operability, doc comments, placeholders, thin wrappers, scores, and strict gates.

## Maintenance Rules

1. Keep `scripts/check_mathlib_compat.py` as the shared runtime until a separate implementation split is planned.
2. Add canonical user-facing guidance to `lean-compile-checker` or `mathlib-abstraction-auditor` depending on the phase.
3. Preserve report fields consumed by workflow code: `compatibility_score`, `critical_review_score`, `expanded_scores`, `summary`, `findings`, and `lake_check`.
4. Keep `--run-lake-check`, `--json`, `--output`, `--reasoning-log-file`, and `--strict` behavior backward compatible.
