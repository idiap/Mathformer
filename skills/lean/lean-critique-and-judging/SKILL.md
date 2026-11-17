---
name: lean-critique-and-judging
description: Critique Lean4 or Isabelle/HOL formalizations against a specified mathematical, structural, or semantic aspect and produce binary judgement plus explanation. Use for SoftCritiqueAgent runs, final LLM judge suites, semantic-preservation checks, and reportable formalization quality reviews.
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

# Lean Critique And Judging

## Purpose

Use this skill when a generated formalization needs qualitative review rather than direct
repair. It owns `SoftCritiqueAgent` prompts and the default LLM judge aspect set used by
systematic autoformalization reports.

For named critique passes, prefer the narrower skills:
- `lean-syntactic-correctness-critic`
- `lean-semantic-preservation-critic`
- `lean-logical-soundness-critic`
- `lean-mathlib-alignment-critic`
- `lean-critique-suite-orchestrator`

Shared runtime owner:
- `../autoformalization-agentc/scripts/agentc.py`
- class: `SoftCritiqueAgent`

## Workflow

1. Choose one explicit aspect description.
2. Evaluate the formalization against that aspect and the informal source statement.
3. Return an explanation and binary `True`/`False` judgement in the expected fence format.
4. For final reports, run the three default aspects from `references/prompts.md`.
5. Feed failed semantic/aspect judgements to `lean-formal-refinement`.
6. If the request names a specific pass, route to the matching specialized critic.

## References

- Read `references/prompts.md` for the exact critique prompt and default judge aspects.
