---
name: lean-refinement-taxonomy
description: Classify formalization refinement transitions with the fixed taxonomy over trigger family, reasoning mode, syntactic edits, semantic edits, artifact effects, preservation risk, summary, and confidence. Use when logging or analyzing how Lean/Isabelle artifacts changed between refinement rounds.
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

# Lean Refinement Taxonomy

## Purpose

Use this skill for refinement-dynamics logging only. It classifies a previous/current formal
artifact pair plus feedback context; it does not produce or repair Lean code.

Shared runtime owner:
- `../autoformalization-agentc/scripts/agentc.py`
- class: `RefinementTaxonomyAgent`

## Workflow

1. Provide previous and current code, hard feedback, soft feedback, deterministic diff metrics, and allowed taxonomy labels.
2. Use only labels supplied in the taxonomy payload.
3. Output exactly one JSON object with the required keys.
4. Keep summaries short and assign a confidence between `0` and `1`.

## References

- Read `references/prompts.md` for the exact taxonomy classification prompt.
