---
name: lean-logical-soundness-critic
description: Critique Lean4 formalizations for logical soundness, non-vacuity, theorem-shape integrity, constrained abstraction boundaries, contradictory assumptions, unconstrained axioms, and placeholder-driven target claims. Use for a logical pass after syntax and semantic preservation checks.
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

# Lean Logical Soundness Critic

## Purpose

Use this skill for the logical pass: whether the artifact is meaningful and non-vacuous as
a formal mathematical statement, even if it compiles.

Shared runtime owners:
- `../autoformalization-agentc/scripts/agentc.py` (`SoftCritiqueAgent`)
- `../mathlib-compatibility-auditor/scripts/check_mathlib_compat.py` via `mathlib-abstraction-auditor`

## Workflow

1. Check whether theorem assumptions make the claim trivial, contradictory, or disconnected from the intended conclusion.
2. Flag unconstrained axioms/predicates that directly force the target theorem.
3. Check abstract interfaces have laws or operational lemmas connecting them to use.
4. Distinguish honest interface scaffolding from a claimed full theorem.
5. Route failures to `lean-formal-refinement` or `mathlib-abstraction-auditor` depending on whether the issue is theorem shape or interface design.

## References

- Read `references/critique.md` for the logical-pass prompt and red flags.
