---
name: latex-expansion-review-orchestrator
description: Coordinate the pre-autoformalization LaTeX expansion review suite, running completeness and binding reviewers after prerequisite expansion and before Lean/Isabelle drafting. Use when the workflow needs a systematic review gate over expanded LaTeX statements.
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

# LaTeX Expansion Review Orchestrator

## Purpose

Use this skill to coordinate preformalization review of expanded LaTeX before the first
formal draft. The suite makes failures explicit before `AutoformalizationAgent` consumes
the expansion.

Shared runtime owner:
- `../autoformalization-agentc/scripts/agentc.py`
- method: `IterativeSelfRefinementAgentC._run_latex_expansion_review_suite`
- hook: `preformalization.review.suite`

## Workflow

1. Run only after `latex-prerequisite-expander` has produced an expanded statement.
2. Run `latex-expansion-completeness-reviewer`.
3. Run `latex-expansion-binding-reviewer`.
4. Record each review's `Explanation`, `Judgement`, raw response, and parsed pass/fail result.
5. Treat the suite as passed only when all configured reviewers return `Judgement: True`.
6. Hand the reviewed expansion to concept mapping and drafting; unresolved failures should be surfaced before trusting the first Lean draft.

## References

- Read `references/review_suite.md` for hook events and gate semantics.
