---
name: lean-import-context-verifier
description: Verify Lean/mathlib import contexts for generated files, snippets, and expected declarations. Use when declarations must be checked under intended narrow imports instead of broad `import Mathlib`, when generated Lean may have missing imports, or when a theorem only works under an over-broad import context.
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

# Lean Import Context Verifier

## Purpose

Use this skill to check whether expected declarations and generated Lean are
valid under the intended import context. It closes the gap between "works under
`import Mathlib`" and "works under the imports the artifact actually declares."

## Workflow

1. Receive a planned import set from `mathlib-import-set-builder` or fixture
   metadata.
2. Compare planned imports with actual generated imports.
3. Flag broad `import Mathlib`, duplicate imports, and missing expected imports.
4. When `--check-lean` is enabled, run Lean on the file/snippet and on
   declaration `#check`s under the intended imports.
5. Route failures to `mathlib-import-set-builder`, `mathlib-hierarchy-navigator`,
   `mathlib-declaration-neighborhood-navigator`, or `lean-formal-refinement`.

## Commands

Text-only import contract check:

```bash
python3 skills/lean/lean-import-context-verifier/scripts/verify_import_context.py \
  --text "import Mathlib.Data.Nat.Basic\n#check Nat" \
  --expected-import Mathlib.Data.Nat.Basic \
  --json
```

Declaration check under intended imports:

```bash
python3 skills/lean/lean-import-context-verifier/scripts/verify_import_context.py \
  --expected-import Mathlib.Data.Nat.Basic \
  --expected-declaration Nat \
  --check-lean \
  --json
```

## References

- Read `references/import_context_policy.md` when deciding whether a broad import
  is an acceptable draft convenience or a final-artifact failure.
