---
name: physics-derivation-gap-expander
description: Expand implicit physics derivation gaps into computable SymPy substeps with rule/API/law citations, input/output expressions, side conditions, source anchors, and dimension checks.
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

# Physics Derivation Gap Expander

Use after gap detection. Generated steps must be marked generated support and
must not pretend to be literal source statements.

## Contract

Build a generated closure packet for every implicit physics gap. Each closure
substep must preserve the source transition it repairs and make the generated
work inspectable.

Required fields on every generated substep:

- source predecessor anchor
- source successor anchor
- rule/API/law used
- input expression
- output expression
- side conditions
- dimension check result
- `source_backing = generated_support`

Generated substep categories:

- `generated_algebra`
- `generated_calculus`
- `generated_law_application`
- `generated_condition_application`
- `generated_unit_conversion`
- `generated_approximation`

## Output

The default report is written to:

```text
artifacts/physics_sympy/<case_id>/gap_expansion_packet.json
```

Completion remains blocked when `unresolved_gaps` is nonempty. A generated
closure may be a symbolic SymPy step or an explicit explanatory support record,
but it must never be hidden inside the final derivation.

## Validation

Use the Phase 7 regression check:

```bash
python tests/physics_sympy/run_phase7_gap_detection_expansion.py --json
```

The expander entrypoint is:

```bash
python skills/physics-common/physics-derivation-gap-expander/scripts/expand_physics_gaps.py --case-id rc_discharge --json
```
