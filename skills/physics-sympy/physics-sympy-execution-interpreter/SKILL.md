---
name: physics-sympy-execution-interpreter
description: Interpret execution diagnostics from generated SymPy physics artifacts. Use after running a physics SymPy artifact to classify dependency, parse, symbol, assumption, unit, residual, numeric, projection, law-grounding, hidden-target, or empty-equation failures before refinement.
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

# Physics SymPy Execution Interpreter

Use this skill immediately after a generated physics SymPy artifact is run. It
turns raw Python/SymPy output into refinement classes.

## Contract

Produce `physics_sympy_execution_interpretation` with:

- diagnostic class;
- severity;
- localized repair hint;
- evidence excerpts;
- status `pass`, `warn`, or `fail`.

Prefer `scripts/interpret_physics_sympy_execution.py` for deterministic
classification.

## Diagnostic Classes

- `dependency_import`
- `parse`
- `symbol_assumption`
- `unit_dimension`
- `transformation_residual`
- `numeric_counterexample`
- `projection_bridge`
- `law_grounding`
- `hidden_target`
- `empty_equation`

