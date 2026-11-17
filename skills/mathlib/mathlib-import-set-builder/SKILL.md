---
name: mathlib-import-set-builder
description: Build a narrow, mathlib-compatible import set from expected imports, concept-map candidates, verified declarations, hierarchy output, or an existing Lean file. Use before Lean drafting/refinement when imports should be explicit, coherent, and not default to broad `import Mathlib`.
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

# Mathlib Import Set Builder

## Purpose

Use this skill to turn mathlib discovery evidence into an intended import
profile. It sits between concept/declaration discovery and Lean drafting.

The skill does not prove that the imports are sufficient. It builds the import
candidate set that `lean-import-context-verifier` should check.

## Workflow

1. Collect imports from expected fixture metadata, verified candidate rows,
   declaration-neighborhood output, hierarchy navigation, and existing Lean.
2. Prefer narrow `Mathlib.X.Y` modules over broad `import Mathlib`.
3. Preserve explicit local project imports such as `Mathformer.Basic` when they
   are required by the target file.
4. Record broad `Mathlib` as a policy finding unless explicitly allowed for
   exploratory draft work.
5. Hand the planned import block to `lean-import-context-verifier` before
   drafting or refinement relies on it.

## Commands

Build from explicit imports:

```bash
python3 skills/mathlib/mathlib-import-set-builder/scripts/build_import_set.py \
  --expected-import Mathlib.Data.Nat.Basic \
  --candidate-import Mathlib.Order.Basic \
  --json
```

Build from a concept-map or hierarchy JSON packet:

```bash
python3 skills/mathlib/mathlib-import-set-builder/scripts/build_import_set.py \
  --candidate-json artifacts/wiki_level_suite/report.json \
  --json
```

## References

- Read `references/import_set_policy.md` when deciding whether broad `Mathlib`
  is acceptable or whether imports should be narrowed before drafting.
