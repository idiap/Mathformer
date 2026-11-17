---
name: latex-expansion-binding-reviewer
description: Review a LaTeX prerequisite expansion before autoformalization for binder, quantifier, free-variable, domain, index, arity, reference, and notation correctness. Use after latex-prerequisite-expander and before Lean/Isabelle drafting when the expanded statement needs binding discipline checks.
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

# LaTeX Expansion Binding Reviewer

## Purpose

Use this skill to check whether a LaTeX-ready expansion has explicit and consistent
binders before autoformalization. It targets variable discipline, not Lean syntax.

Shared runtime owner:
- `../autoformalization-agentc/scripts/agentc.py`
- class: `LatexExpansionBindingReviewAgent`
- hook: `preformalization.review.bindings`

## Workflow

1. Compare variables, domains, quantifiers, indices, parameters, and notation across the original and expanded statements.
2. Identify dangling identifiers, hidden free variables, changed quantifier order, inconsistent arities, or overloaded symbols whose meaning is no longer clear.
3. Mark the review `False` when a Lean drafter would need to guess binders or dependency structure.
4. Do not generate Lean code and do not rewrite the full expansion.
5. Return a fenced `Explanation` and `Judgement` compatible with `references/review.md`.

## References

- Read `references/review.md` for the exact checklist and response contract.
