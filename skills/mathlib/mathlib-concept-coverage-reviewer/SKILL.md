---
name: mathlib-concept-coverage-reviewer
description: Review mapped informal mathematical concepts for verified mathlib coverage. Use after mathlib candidate discovery/verification to check whether every extracted concept has at least one Lean-checked declaration, candidate imports, or an explicit compatibility gap before drafting or refinement.
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

# Mathlib Concept Coverage Reviewer

## Purpose

Use this skill to turn a concept map into a coverage gate. It checks whether each
concept has verified mathlib declarations, candidate imports, or a documented gap.

Shared runtime owner:
- `../autoformalization-agentc/scripts/agentc.py`
- functions: `summarize_mathlib_concept_coverage`, `format_mathlib_concept_coverage_hints`
- hook: `mathlib.coverage`

## Workflow

1. Start from the JSON output of `mathlib-concept-candidate-mapper` or `mathlib-candidate-verifier`.
2. Mark a concept `verified` only when at least one candidate has `check_ok: true`.
3. Mark unverified checked candidates separately from merely unverified candidates.
4. Preserve candidate names, imports, and gaps for prompt conditioning.
5. Treat the preferred gate as all extracted concepts verified, unless the concept is explicitly documented as outside current mathlib coverage.

## References

- Read `references/coverage.md` for statuses and report fields.
