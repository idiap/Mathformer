---
name: physics-sympy-derivation-drafter
description: Draft executable Python/SymPy physics derivation artifacts that expose quantities, units, assumptions, derivation steps, dimension validation, step validation, numeric samples, and a trace explanation.
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

# Physics SymPy Derivation Drafter

Use after the derivation plan is complete. Generated artifacts live under
`backends/sympy/MathformerSympyPhysics/` and must compute the target expression from prior
steps rather than store a hidden final answer.

## Required Source Commentary

Every generated SymPy artifact must begin with a module docstring that preserves:

1. The original informal statement.
2. The full informal derivation commentary used for formalization.
3. A `SymPy alignment` section mapping each informal step to the concrete
   `DERIVATION_STEPS` id, equation graph node, projection bridge, law table
   entry, or validation function that carries it.

The same text must also be exposed as module data, preferably
`COMMENTARY_HEADER`, and referenced from `CLAIM["commentary_header"]`. This is
not decorative: reviewers must be able to inspect whether the executable SymPy
trace preserves the source meaning and which generated support steps were added.

## Drafting Rules

- Keep the commentary as a header before implementation details.
- Use source-backed step ids for literal source equations and generated step ids
  only for algebraic, calculus, projection, or unit-support gaps.
- Do not align an informal physics step only to the final target expression when
  it has an intermediate law, assumption, unit condition, or projection bridge.
- If a source vector or field statement is represented by scalar placeholders,
  the alignment must name the corresponding projection bridge and typing
  surface.

## Executable Contract

Every generated Python artifact must expose:

- `CLAIM`
- `QUANTITY_TABLE`
- `DIMENSION_MODEL`
- `ASSUMPTIONS`
- `DERIVATION_STEPS`
- `build_symbols()`
- `build_units()`
- `build_equations()`
- `derive_target()`
- `validate_dimensions()`
- `validate_derivation_steps()`
- `validate_numeric_samples()`
- `explain_trace()`

The final expression must be computed by `derive_target()` and
`build_equations()` from `DERIVATION_STEPS`. It must not be treated as a hidden
hand-computed answer.

## Validation

Use the Phase 9 regression check:

```bash
python tests/physics_sympy/run_phase9_derivation_plan_artifact_contract.py --json
```

The skill entrypoint is:

```bash
python skills/physics-sympy/physics-sympy-derivation-drafter/scripts/draft_physics_sympy_derivation.py --case-id rc_discharge --output artifacts/AutoformalizedRcDischarge.py --json
```
