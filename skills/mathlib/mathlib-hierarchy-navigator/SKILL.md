---
name: mathlib-hierarchy-navigator
description: Navigate mathlib hierarchically from broad module areas to child prefixes, concrete imports, sibling modules, and declaration neighborhoods. Use when exploring mathlib structure, choosing where to search next, or moving from a concept to module families before selecting declarations.
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

# Mathlib Hierarchy Navigator

## Purpose

Use this skill to move through mathlib as a tree: broad domains, module prefixes,
concrete imports, nearby sibling modules, and local declarations. It complements flat
candidate ranking by showing where a concept lives in the library structure.

Runtime:
- `scripts/navigate_mathlib_hierarchy.py`
- hooks: `mathlib.hierarchy.navigate`, `mathlib.hierarchy.module_tree`, `mathlib.hierarchy.declaration_neighborhood`

## Workflow

1. Start broad with `--module-prefix Mathlib` or a domain prefix such as `Mathlib.Topology`.
2. Move down to child prefixes until a concrete module looks relevant.
3. Inspect module imports and declarations with `--module`.
4. Use `--query` or `--declaration` to find local declaration neighborhoods.
5. Hand promising modules/imports to `mathlib-concept-candidate-mapper`, `mathlib-candidate-verifier`, or `mathlib-api-compatibility-planner`.

## Commands

```bash
python3 skills/mathlib/mathlib-hierarchy-navigator/scripts/navigate_mathlib_hierarchy.py \
  --module-prefix Mathlib.Topology \
  --json
```

```bash
python3 skills/mathlib/mathlib-hierarchy-navigator/scripts/navigate_mathlib_hierarchy.py \
  --module Mathlib.Topology.Basic \
  --declaration Continuous \
  --json
```

```bash
python3 skills/mathlib/mathlib-hierarchy-navigator/scripts/navigate_mathlib_hierarchy.py \
  --query compact \
  --module-prefix Mathlib.Topology \
  --json
```

## References

- Read `references/navigation.md` for traversal strategy and output interpretation.
