---
name: physics-unit-system-grounder
description: Ground physics quantities to concrete units and SymPy unit-system concepts, including SI base units, derived units, and source-specific units.
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

# Physics Unit System Grounder

Use after dimension modeling. It records unit choices and distinguishes source
units from generated unit-normalization support.

The implementation is centered on
`backends.sympy.MathformerPhysicsSympy.pipeline.build_physics_unit_packet()`. It records the
standard unit catalog for meter, kilogram, second, ampere, kelvin, mole,
newton, joule, watt, pascal, coulomb, volt, ohm, and radian. Composite or
source-specific units stay visible as explicit strings.

The packet grounds the model in SymPy unit-system surfaces when available:
`Quantity`, `Dimension`, `DimensionSystem`, `UnitSystem`, and SI from
`sympy.physics.units.systems.si`.

Validate changes with:

```bash
.venv/bin/python tests/physics_sympy/run_phase4_dimension_units.py --json
```
