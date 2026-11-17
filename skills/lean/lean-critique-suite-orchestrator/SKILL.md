---
name: lean-critique-suite-orchestrator
description: Run a systematic multi-pass critique suite over Lean4 formalizations, coordinating syntactic correctness, semantic preservation, logical soundness, mathlib alignment, optional LLM judging, and refinement handoff. Use when a Lean artifact needs a structured review gate rather than a single generic critique.
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

# Lean Critique Suite Orchestrator

## Purpose

Use this skill when a Lean formalization needs a release-style critique gate. It does not
replace the focused critics; it coordinates them and records an ordered decision.

## Pass Order

1. `lean-syntactic-correctness-critic`: Lean parser/elaboration/import/typecheck health.
2. `lean-semantic-preservation-critic`: source-to-Lean meaning preservation.
3. `lean-logical-soundness-critic`: non-vacuity, constrained abstractions, theorem shape.
4. `lean-mathlib-alignment-critic`: mathlib-native object/API alignment.
5. `autoformalization-result-realness-verifier`: no mocks, unexecuted states, placeholders, or scaffold-only final claims.
6. `lean-critique-and-judging`: optional generic SoftCritiqueAgent aspects or final LLM judge suite.
7. `reference-free-critic-monitor`: benchmark-free trend snapshot for scores, hard risks, and anti-gaming checks.

## Gate Policy

- Syntax failure blocks semantic pass/final approval and routes to `lean-formal-refinement`.
- Semantic preservation failure routes to semantic realignment through `lean-formal-refinement`.
- Logical soundness failure blocks approval even if Lean compiles.
- Mathlib alignment failure may block approval when compatibility scoring is a release gate; otherwise it becomes a required follow-up.
- Realness failure blocks approval and either routes to refinement or marks the artifact draft/blocked.
- Reference-free monitor regressions block prompt/skill acceptance even when the current artifact passes the local critique suite.
- The suite passes only when required passes are `True` or explicitly waived with a reason.

## References

- Read `references/critique_suite.md` for the expected report shape and hook mapping.
