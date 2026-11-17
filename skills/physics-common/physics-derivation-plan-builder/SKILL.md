---
name: physics-derivation-plan-builder
description: Build a topologically ordered executable plan for physics SymPy derivations, from quantities and units through gap expansion, drafting, execution, unit analysis, step verification, and reporting.
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

# Physics Derivation Plan Builder

Use after source, symbols, dimensions, units, assumptions, frames, equations,
gaps, and law grounding are available.

## Contract

Build a topologically ordered plan with exactly these stages:

- quantities
- dimensions and units
- assumptions, regimes, and frames
- source equations
- generated gap-closure equations
- target derivation chain
- validation calls

Every job must declare its dependencies, outputs, evidence source, and local
contract. Dependencies must only point to earlier jobs.

## Output

The default report is written to:

```text
artifacts/physics_sympy/<case_id>/derivation_plan_packet.json
```

The plan must include the executable artifact contract used by the drafter,
including required data bindings, required functions, validation calls, and the
policy against hidden final answers.

## Validation

Use the Phase 9 regression check:

```bash
python tests/physics_sympy/run_phase9_derivation_plan_artifact_contract.py --json
```

The skill entrypoint is:

```bash
python skills/physics-common/physics-derivation-plan-builder/scripts/build_physics_derivation_plan.py --case-id rc_discharge --json
```
