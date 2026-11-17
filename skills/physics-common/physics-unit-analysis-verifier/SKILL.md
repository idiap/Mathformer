---
name: physics-unit-analysis-verifier
description: Verify dimensional and unit consistency for every equation and generated transformation in a physics SymPy derivation.
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

# Physics Unit Analysis Verifier

Use after drafting or directly on a case. Unit inconsistency is a critical
blocker for complete status.

## Contract

Build a unit-analysis packet that verifies:

- every parsed equation has consistent dimensions,
- additive terms have identical dimensions,
- `sin`, `cos`, `tan`, `exp`, and `log` arguments are dimensionless,
- substitution steps preserve dimensions,
- target-equation steps match the expected target dimension,
- generated unit-conversion steps are recorded or dimensionally checked.

## Output

The default report is written to:

```text
artifacts/physics_sympy/<case_id>/unit_analysis_report.json
```

The report must include per-equation checks, per-step checks, generated
unit-conversion checks, conflicting unit diagnostics, missing unit diagnostics,
dimensionless-argument diagnostics, and `completion_blocked`.

## Validation

Use the Phase 10 regression check:

```bash
python tests/physics_sympy/run_phase10_unit_dimension_validation.py --json
```

The skill entrypoint is:

```bash
python skills/physics-common/physics-unit-analysis-verifier/scripts/verify_physics_units.py --case-id rc_discharge --json
```
