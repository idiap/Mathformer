---
name: mathlib-module-tree-cartographer
description: Map mathlib module-prefix hierarchy, parent-child relationships, sibling modules, leaf counts, and source files. Use when selecting a mathlib area to inspect before declaration search or import planning.
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

# Mathlib Module Tree Cartographer

## Purpose

Use this skill to inspect the mathlib module tree without jumping directly to declarations.
It helps choose the right library region and nearby sibling modules.

Runtime:
- `../mathlib-hierarchy-navigator/scripts/navigate_mathlib_hierarchy.py`
- hook: `mathlib.hierarchy.module_tree`

## Workflow

1. Run the navigator with `--module-prefix`.
2. Read `children` to choose the next narrower prefix.
3. Use `leaf_count` to identify rich subtrees.
4. Use `siblings` to compare nearby alternatives.
5. Stop at a concrete module and hand off to `mathlib-declaration-neighborhood-navigator`.

## References

- Read `references/module_tree.md` for node kinds and selection rules.
