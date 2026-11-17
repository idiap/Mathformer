---
name: lean-syntactic-correctness-critic
description: Critique Lean4 code for syntactic correctness, elaboration health, import/name resolution, typeclass synthesis, and theorem-prover diagnostics. Use when deciding whether a Lean artifact actually parses and typechecks, when classifying Lean errors before refinement, or when a formalization needs a compile-gated correctness pass.
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

# Lean Syntactic Correctness Critic

## Purpose

Use this skill for the syntactic/typechecking critique pass. It should be grounded in
`lean-compile-checker` or `HardCritiqueAgent` diagnostics whenever local Lean is available.

Shared runtime owners:
- `../autoformalization-agentc/scripts/agentc.py` (`HardCritiqueAgent`, `SoftCritiqueAgent`)
- `../mathlib-compatibility-auditor/scripts/check_mathlib_compat.py` via `lean-compile-checker`

## Workflow

1. Run `lean-compile-checker` or inspect existing hard-critique diagnostics.
2. Treat parser errors, unknown identifiers, unresolved imports, type mismatches, failed synthesis, and unsolved required goals as failures.
3. Distinguish accepted scaffolding (`sorry`) from compile failure: `sorry` may typecheck but is not proof completion.
4. Return a judgement with concrete line/error evidence when available.
5. Route failures to `lean-formal-refinement` with the original diagnostic text.

## References

- Read `references/critique.md` for the pass prompt and output checklist.
