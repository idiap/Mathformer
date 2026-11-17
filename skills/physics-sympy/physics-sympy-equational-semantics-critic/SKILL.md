---
name: physics-sympy-equational-semantics-critic
description: Critique whether an executable SymPy equation trace preserves the source physics. Use after SymPy execution and equation-surface construction to detect target leakage, law loss, scalar erasure, missing projection bridges, source drift, or generated bridge equations without support.
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

# Physics SymPy Equational Semantics Critic

Use this critic after execution, equation-surface construction, and assumption
encoding. It asks whether the equations still mean the source physics, not just
whether algebraic simplification succeeded.

## Contract

Produce `physics_sympy_equational_semantics_critic_report`.

Prefer `scripts/critique_physics_sympy_equational_semantics.py` for
deterministic screening.

## Critical Failures

- The target equation appears as an input, shortcut, or all-purpose law.
- A source law is used without law grounding.
- Vector, field, operator, frame, or regime structure is erased into unrelated
  scalar algebra.
- A scalar component equation lacks a projection bridge back to the physical
  claim.
- A source equivalence, vector claim, or general regime is weakened without a
  generated-support label.
- Generated bridge equations lack source or law support.

