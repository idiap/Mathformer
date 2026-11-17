---
name: physics-derivation-step-verifier
description: Verify executable physics derivation steps in SymPy, including algebraic transformations, substitutions, calculus steps, ODE solutions, approximations, and vector-to-scalar reductions.
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

# Physics Derivation Step Verifier

Use after unit analysis and derivation planning. The target expression must be
derived from the step chain, with zero symbolic residual or an explicit blocker.

## Contract

The verifier produces a Phase 11 packet with:

- algebraic equivalence checks for executable steps and final target residuals,
- substitution checks that compare adjacent trace expressions and preserve dimensions,
- calculus checks that re-differentiate or re-check integrated consequences where possible,
- ODE checks that substitute the solution, verify boundary or initial conditions, and run admissible numeric samples,
- approximation or branch-condition checks with explicit regimes,
- vector-to-scalar projection checks with declared axis, sign convention, and dimensional consistency.

The standard report path is:

```text
artifacts/physics_sympy/<case_id>/step_execution_report.json
```

## Validation

Run the focused regression before declaring this skill healthy:

```bash
python tests/physics_sympy/run_phase11_step_execution_equivalence.py --json
```

The broader physics SymPy suite also calls this check through
`tests/test_program/run_comprehensive_tests.py`.
