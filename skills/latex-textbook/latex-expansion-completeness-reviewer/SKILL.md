---
name: latex-expansion-completeness-reviewer
description: Review a LaTeX prerequisite expansion before autoformalization for completeness of definitions, theorem prerequisites, assumptions, side conditions, and target conclusion preservation. Use after latex-prerequisite-expander and before Lean/Isabelle drafting when the expanded statement must be checked for formalization readiness.
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

# LaTeX Expansion Completeness Reviewer

## Purpose

Use this skill to check whether a LaTeX-ready expansion contains the mathematical content
needed before autoformalization. It reviews the expansion, not the Lean output.

Shared runtime owner:
- `../autoformalization-agentc/scripts/agentc.py`
- class: `LatexExpansionCompletenessReviewAgent`
- hook: `preformalization.review.completeness`

## Workflow

1. Compare the original statement against the expanded statement.
2. Check that definitions, named theorem prerequisites, hypotheses, domains, side conditions, and the conclusion are all present.
3. Mark the review `False` when the expansion omits source content, changes theorem strength, introduces unjustified assumptions, or is too vague for drafting.
4. Do not generate Lean code and do not rewrite the full expansion.
5. Return a fenced `Explanation` and `Judgement` compatible with `references/review.md`.

## References

- Read `references/review.md` for the exact checklist and response contract.
