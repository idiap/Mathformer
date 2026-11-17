---
name: physics-sympy-dimension-projection-critic
description: Stress-test unit, dimension, and projection discipline in SymPy physics equation traces. Use after unit verification and equation-surface construction to detect dimension errors, invalid transcendental use, missing vector or field projection bridges, coordinate/sign omissions, or unlabeled dimensionless reductions.
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

# Physics SymPy Dimension Projection Critic

Use this critic after unit analysis and before final review. It complements the
basic unit verifier by looking for physical erasure patterns around projections
and dimension-sensitive operations.

## Contract

Produce `physics_sympy_dimension_projection_critic_report`.

Prefer `scripts/critique_physics_sympy_dimensions.py` for deterministic
screening.

## Checks

- Addition and subtraction only combine compatible dimensions.
- Exponentials, logarithms, trigonometric functions, and powers do not hide
  dimensional arguments.
- Vector and field component equations reconstruct the intended physical claim.
- Coordinate and sign conventions are visible for component-level equations.
- Dimensionless normalizations and constants are labeled.

