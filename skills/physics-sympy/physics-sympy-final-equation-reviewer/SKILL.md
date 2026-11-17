---
name: physics-sympy-final-equation-reviewer
description: Review final SymPy physics equation graphs before complete status. Use at the end of the enriched SymPy physics pipeline to validate quantities, dimensions, units, installed-library grounding, frames, regimes, contextual assumptions, law grounding, projection bridges, target derivation, numeric domains, and non-leakage of the target equation.
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

# Physics SymPy Final Equation Reviewer

Use this final reviewer after execution, unit checks, step verification, numeric
sampling, SymPy library grounding, equation-surface building, assumption
encoding, and deterministic critics.

## Contract

Produce `physics_sympy_final_equation_review`.

Prefer `scripts/review_physics_sympy_final_equations.py` for deterministic
screening.

## Required Properties

- Every source quantity is represented or explicitly projected.
- Case-required roles have `grounding_level = high` in
  `physics_sympy_library_grounding_packet`.
- Units and dimensions pass for source, bridge, and derived equations.
- Frames, regimes, approximations, and side conditions are explicit.
- Each transformation cites a physical law, generated bridge, or SymPy rule.
- The target is derived from prior equations, not copied into the inputs.
- Numeric samples obey physical domains.
- The equation graph is non-vacuous.

Failed reviews must route to `physics-sympy-review-refinement-router`.
