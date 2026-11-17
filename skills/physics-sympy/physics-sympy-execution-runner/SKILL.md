---
name: physics-sympy-execution-runner
description: Import and execute generated Mathformer physics SymPy artifacts, checking that they expose the standard derivation contract and emit unit, symbolic-step, numeric-sanity, and trace reports.
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

# Physics SymPy Execution Runner

Use immediately after `physics-sympy-derivation-drafter` writes an artifact.
The runner imports the generated Python module, calls `run_all()`, and reports
whether the artifact is executable, placeholder-free, dimensionally consistent,
step-verifiable, and numerically sane.

Prefer `scripts/run_physics_sympy_artifact.py` so execution behavior stays
shared across workflow hooks and deterministic tests.
