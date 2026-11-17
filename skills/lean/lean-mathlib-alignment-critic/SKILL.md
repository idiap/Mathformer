---
name: lean-mathlib-alignment-critic
description: Critique Lean4 formalizations for mathlib-native alignment, reuse of existing declarations, appropriate imports, duplicate abstractions, API operability, and representation choices. Use when reviewing whether generated Lean code should use existing mathlib objects or verified candidate declarations instead of local ad hoc definitions.
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

# Lean Mathlib Alignment Critic

## Purpose

Use this skill for critique of library alignment and representation choices. It is narrower
than the full `mathlib-abstraction-auditor` score report and broader than candidate lookup.

Shared runtime owners:
- `mathlib-concept-candidate-mapper`
- `mathlib-candidate-verifier`
- `mathlib-abstraction-auditor`

## Workflow

1. Inspect imports, declarations, local definitions, and theorem statements.
2. Compare core concepts against verified mathlib candidates when available.
3. Prefer native mathlib predicates/types over duplicate local interfaces.
4. Flag overly broad imports, unused/floating abstractions, and missing operational API lemmas.
5. Route concrete candidate search to `mathlib-concept-candidate-mapper` and verification to `mathlib-candidate-verifier`.

## References

- Read `references/critique.md` for the alignment-pass prompt and finding categories.
