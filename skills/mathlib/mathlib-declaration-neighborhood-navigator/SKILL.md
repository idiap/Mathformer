---
name: mathlib-declaration-neighborhood-navigator
description: Inspect a focused mathlib module or declaration neighborhood, including imports, nearby declarations, source references, and declaration-name filters. Use after choosing a module prefix to understand local APIs before verification or drafting.
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

# Mathlib Declaration Neighborhood Navigator

## Purpose

Use this skill once a concrete mathlib module is in focus. It lists imports and local
declarations so agents can understand the API neighborhood before using names.

Runtime:
- `../mathlib-hierarchy-navigator/scripts/navigate_mathlib_hierarchy.py`
- hook: `mathlib.hierarchy.declaration_neighborhood`

## Workflow

1. Run the navigator with `--module Mathlib.Some.Module`.
2. Add `--declaration name_part` when looking for a local declaration family.
3. Read imports first; they often reveal the intended parent API.
4. Use source references to inspect exact signatures when a declaration looks promising.
5. Send selected names to `mathlib-candidate-verifier` before prompt injection.

## References

- Read `references/declaration_neighborhood.md` for source-neighborhood rules.
