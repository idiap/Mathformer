---
name: mathematical-sympy-final-equation-reviewer
description: Review mathematical correctness of final SymPy equation traces. Use at the end of a SymPy or physics-SymPy pipeline to validate parsing, equality direction, equivalence preservation, symbolic residuals, branch and denominator side conditions, matrix shapes, function domains, counterexample search, trace executability, and non-vacuity.
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

# Mathematical SymPy Final Equation Reviewer

Use this final reviewer after SymPy execution, identity validation,
counterexample search, and trace verification. It reviews the mathematics
independently of the physics context.

## Contract

Produce `mathematical_sympy_final_equation_review`.

Prefer `scripts/review_mathematical_sympy_final_equations.py` for deterministic
screening.

## Required Properties

- Expressions parse into intended SymPy objects.
- Equality direction and equivalence claims are preserved.
- Symbolic residuals are zero under declared assumptions.
- Branch, denominator, invertibility, matrix-shape, and function-domain side
  conditions are explicit.
- Counterexample search finds no admissible counterexample.
- Trace steps are executable, justified, and non-vacuous.

