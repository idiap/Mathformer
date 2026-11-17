---
name: mathematical-isabelle-final-hypothesis-reviewer
description: Review final Isabelle/HOL mathematical theorem shape, binders, assumptions, placeholders, vacuity, and target-as-assumption risks for generated Isabelle physics or math theories.
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

# Mathematical Isabelle Final Hypothesis Reviewer

Use near the end of an Isabelle/HOL formalization run, before the final
Isabelle consistency report.

Prefer `scripts/review_mathematical_isabelle_final_hypotheses.py`.

