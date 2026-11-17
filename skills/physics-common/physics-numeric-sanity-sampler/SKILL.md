---
name: physics-numeric-sanity-sampler
description: Sample physically admissible parameter domains for physics SymPy derivations and report concrete counterexamples while treating numeric evidence as supporting, not sufficient.
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

# Physics Numeric Sanity Sampler

Use after symbolic and unit checks. Samples must obey declared domains,
nonzero restrictions, positivity constraints, and approximation regimes.

## Contract

The sampler produces a Phase 12 packet with:

- explicit domain constraints for positive, nonnegative, nonzero-denominator,
  interval, and small-parameter regimes,
- deterministic admissible samples,
- target-versus-expected numeric comparisons with residuals and tolerances,
- counterexample records containing sampled values, units/dimensions, failed
  equation, failed step ID, and source anchors,
- a symbolic-step-validation dependency showing that numeric checks are
  supporting evidence only.

The standard report path is:

```text
artifacts/physics_sympy/<case_id>/numeric_sanity_report.json
```

## Validation

Run the focused regression before declaring this skill healthy:

```bash
python tests/physics_sympy/run_phase12_numeric_sanity_sampling.py --json
```

The broader physics SymPy suite also calls this check through
`tests/test_program/run_comprehensive_tests.py`.
