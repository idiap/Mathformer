---
name: informal-proof-mathlib-concepts
description: Compatibility wrapper for the legacy mathlib concept mapping script. Use when maintaining scripts/map_mathlib_concepts.py, preserving older workflow calls, or routing mathlib lookup work to the specialized mapper and verifier skills.
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

# Informal Proof Mathlib Concepts Compatibility Wrapper

## Status

This skill is now a compatibility wrapper. The shared runtime remains here:

- `scripts/map_mathlib_concepts.py`
- `references/lean_mathlib_lookup.md` as legacy detailed command/reference material

## Use The Specialized Skills

- `mathlib-concept-candidate-mapper`: extract or accept concepts, rank mathlib declarations, rank relevant modules, emit imports/source refs, and produce JSON handoff data without Lean verification.
- `mathlib-candidate-verifier`: rerun candidate mapping with `--verify-checks`, execute bounded `lake env lean` `#check` calls, and preserve `check_ok` plus checker errors.

## Maintenance Rules

1. Keep `scripts/map_mathlib_concepts.py` as the shared runtime until a separate implementation split is planned.
2. Add canonical usage guidance to the specialized skill that owns the phase.
3. Preserve legacy options because `autoformalization-workflow-orchestrator` and older AgentC calls may still invoke this path.
4. Keep JSON output fields stable for downstream prompt conditioning: `relevant_modules`, `candidates`, `qualified_name`, `import`, `source_ref`, `source_path`, and verification fields when enabled.
