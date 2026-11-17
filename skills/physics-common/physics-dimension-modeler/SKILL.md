---
name: physics-dimension-modeler
description: Infer and represent physical dimensions for source-backed and generated quantities in physics SymPy derivations, including base and derived dimensions.
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

# Physics Dimension Modeler

Use after symbol-table construction. It emits a dimension packet for every
quantity and flags missing or conflicting dimensions.

The implementation is centered on
`backends.sympy.MathformerPhysicsSympy.pipeline.build_physics_dimension_packet()`. It models
the SI base dimensions, treats angles and pure numbers as dimensionless, and
records source anchors for source-backed dimension claims.

The inference contract covers:

- sums require equal dimensions,
- products add dimension exponents,
- powers multiply dimension exponents,
- derivatives divide by the independent variable dimension,
- integrals multiply by the integration variable dimension,
- transcendental functions, exponentials, logarithms, and trigonometric
  arguments require dimensionless inputs.

The default phase command emits:

```text
artifacts/physics_sympy/<case_id>/dimension_packet.json
```

Validate changes with:

```bash
.venv/bin/python tests/physics_sympy/run_phase4_dimension_units.py --json
```
