---
name: mathlib-import-minimizer
description: Audit and minimize Lean/mathlib import blocks after drafting or refinement. Use when generated Lean has duplicate imports, broad `import Mathlib`, unused-looking imports, or when a saved artifact needs a narrow final import block before publication.
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

# Mathlib Import Minimizer

## Purpose

Use this skill after Lean has been generated or refined. It makes the import
block smaller and more explicit while preserving a clear boundary between
verified removals and textual suggestions.

## Workflow

1. Parse the generated import block.
2. Flag duplicate imports and broad `import Mathlib`.
3. Produce a stable deduplicated import block.
4. When `--check-lean` is enabled, greedily remove imports only when Lean still
   compiles under the reduced import set.
5. Run `lean-import-context-verifier` after minimization when expected
   declarations or fixture imports are known.

## Commands

Text-only cleanup:

```bash
python3 skills/mathlib/mathlib-import-minimizer/scripts/minimize_imports.py \
  --lean-file backends/lean/Mathformer/AutoformalizedSazonov.lean \
  --json
```

Compile-checked greedy minimization:

```bash
python3 skills/mathlib/mathlib-import-minimizer/scripts/minimize_imports.py \
  --lean-file backends/lean/Mathformer/AutoformalizedSazonov.lean \
  --check-lean \
  --json
```

## References

- Read `references/import_minimization.md` before accepting a reduced import
  block as final.
