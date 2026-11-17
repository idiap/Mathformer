---
name: physics-sympy-formal-answer-reflector
description: Compare a SymPy physics candidate with a withheld FormalPhysics formal_answer as inspiration only. Use after an informal-first SymPy candidate, blocker report, or final consistency report exists to extract theorem-shape, assumption, law, decomposition, or projection lessons without treating the dataset formalization as a benchmark label or ground truth.
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

# Physics SymPy Formal Answer Reflector

Use this only after the informal-first SymPy candidate or blocker report exists.
It compares against FormalPhysics `formal_answer` as inspiration, not as gold.

## Contract

Produce `physics_sympy_formal_answer_reflection`.

Prefer `scripts/compare_sympy_formal_physics_answers.py` for deterministic
first-pass comparison.

## Policy

- Do not inspect `formal_answer` before the initial SymPy candidate or blocker.
- Do not score SymPy against the dataset answer as a benchmark.
- Extract only local improvement candidates: theorem shape, assumptions, laws,
  decomposition, projection bridges, or missing side conditions.
- Route accepted changes through final reviewers and localized monotonic
  refinement.

