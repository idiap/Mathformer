---
name: physics-implicit-gap-detector
description: Detect implicit algebraic, calculus, substitution, ODE, approximation, law-invocation, coordinate-projection, unit-conversion, and side-condition gaps in physics derivations.
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

# Physics Implicit Gap Detector

Use between parsed source steps. It identifies missing computable steps that
must be expanded before a derivation can be marked complete.

## Contract

Build an implicit-gap packet for one physics derivation case. The packet must
name every detected gap, classify it, preserve predecessor and successor source
anchors, propose the rule/API/law needed for closure, and list the side
conditions that make the transition legitimate.

Gap categories:

- `missing_algebraic_rearrangement`
- `missing_substitution`
- `missing_differentiation_or_integration`
- `missing_ode_solution`
- `missing_law_invocation`
- `missing_initial_condition_application`
- `missing_approximation_justification`
- `missing_coordinate_projection`
- `missing_unit_conversion`
- `missing_cancellation_side_condition`

## Output

The default report is written to:

```text
artifacts/physics_sympy/<case_id>/implicit_gap_packet.json
```

The packet keeps detected gaps in `implicit_gaps` and records unresolved gap
IDs in `unresolved_gaps`. This is intentional: detection creates repair
targets; expansion closes them.

## Validation

Use the Phase 7 regression check:

```bash
python tests/physics_sympy/run_phase7_gap_detection_expansion.py --json
```

The detector entrypoint is:

```bash
python skills/physics-common/physics-implicit-gap-detector/scripts/detect_physics_gaps.py --case-id rc_discharge --json
```
