---
name: physics-lean-execution-interpreter
description: Interpret Lean execution diagnostics for physics formalizations, classifying failures as mathlib import, physics typing, unit/dimension, contextual-assumption, proof-gap, source-drift, or non-empty-formalism issues.
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

# Physics Lean Execution Interpreter

Use immediately after Lean execution or compile checks on a physics artifact.

The interpreter turns raw Lean diagnostics into physics-aware repair targets:

- import/mathlib gaps;
- type-system or quantity erasure problems;
- missing unit or dimension obligations;
- missing contextual assumptions;
- theorem statement/source drift;
- proof search gaps;
- target-as-assumption or target-axiom risks.

Prefer `scripts/interpret_physics_lean_execution.py` for deterministic log
classification before invoking refinement.

