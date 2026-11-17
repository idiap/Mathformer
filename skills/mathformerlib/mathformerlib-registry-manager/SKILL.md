---
name: mathformerlib-registry-manager
description: Build and validate the Mathformerlib registry of accumulated Lean formalizations, including modules, declarations, imports, provenance, draft/candidate/accepted status, placeholder/scaffold markers, and duplicate declaration findings. Use when indexing MathformerLib as a parallel curated library or refreshing formalization inventory.
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

# Mathformerlib Registry Manager

## Purpose

Use this skill to produce the authoritative registry for Mathformerlib. The
registry is a machine-readable catalog of modules, declarations, imports,
statuses, and quality markers.

Runtime:
- `scripts/manage_mathformerlib_registry.py`
- hook: `mathformerlib.registry`

## Commands

```bash
python3 skills/mathformerlib/mathformerlib-registry-manager/scripts/manage_mathformerlib_registry.py \
  --json
```

```bash
python3 skills/mathformerlib/mathformerlib-registry-manager/scripts/manage_mathformerlib_registry.py \
  --include-root MathformerLib \
  --include-root Mathformer \
  --output-file artifacts/mathformerlib/registry.json \
  --json
```

## Status Semantics

- `accepted`: under `libraries/MathformerLib/` and no local placeholder/scaffold markers.
- `candidate`: outside `libraries/MathformerLib/` and no local placeholder/scaffold markers.
- `draft`: contains proof placeholders, TODOs, mock markers, or scaffold markers.

The registry status is not enough for promotion. Promotion still requires
`mathformerlib-promotion-gate`.
