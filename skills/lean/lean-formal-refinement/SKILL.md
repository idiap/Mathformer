---
name: lean-formal-refinement
description: Refine Lean4 or Isabelle/HOL formalizations using theorem-prover diagnostics, syntactic/type/undefined-name error categories, or semantic critique feedback. Use when repairing generated formal code while preserving the informal mathematical statement and avoiding vacuous or unconstrained axiomatizations.
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

# Lean Formal Refinement

## Purpose

Use this skill after a draft formalization exists and feedback is available. It owns both
hard-feedback refinement (`FormalRefinementAgent`) and semantic/aspect-driven refinement
(`InformalRefinementAgent`).

Shared runtime owner:
- `../autoformalization-agentc/scripts/agentc.py`
- classes: `FormalRefinementAgent`, `InformalRefinementAgent`

## Workflow

1. Preserve the informal statement's mathematical meaning.
2. Prefer concrete mathlib-native objects and explicit assumption packages.
3. Avoid unconstrained target axioms, vacuous theorem statements, contradictory assumptions, and dead abstraction interfaces.
4. Select the refinement mode that matches available feedback: `simple`, `binary`, or `detailed`.
5. Add category-specific instructions for syntax (`syn`), undefined references (`udf`), or type/unification failures (`tuf`) when diagnostics support it.
6. Preserve dependency context, mathlib hints, and meaningful source-aligned comments if they were part of the draft.
7. For Lean4 output, use normal blank-line structure and source-aware module/declaration comments. Preserve `Original source (NL)` / `Original source (LaTeX)` content when it came from the source; add `Generated note` / `Generated equivalent` comments for support declarations introduced during refinement.
8. Remove legacy per-line `NL/LaTeX:` comments when touching affected code.
9. Run or honor the `lean-line-annotation` source-comment hygiene guard with semantic-comment coverage before accepting refined Lean.
10. Hand each transition to `lean-refinement-taxonomy` when refinement dynamics need to be logged.
11. Do not resolve failures by leaving mocked proofs, target `axiom`s, legacy per-line `NL/LaTeX:` comments, missing semantic declaration comments, or scaffold-only claims in a result marked complete; final artifacts must pass `autoformalization-result-realness-verifier`.

## References

- Read `references/prompts.md` for exact prompt templates, optional extensions, and mode fragments.
