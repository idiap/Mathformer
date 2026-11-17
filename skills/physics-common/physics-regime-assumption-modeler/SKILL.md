---
name: physics-regime-assumption-modeler
description: Model physics assumptions and regimes for SymPy derivations, including constant quantities, positivity, small-angle regimes, idealizations, no-damping/no-drag assumptions, and nonzero side conditions.
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

# Physics Regime Assumption Modeler

Use before gap expansion and drafting. It must prevent silent strengthening:
real does not become positive, varying quantities do not become constant, and
omitted forces or losses are not removed without source support.

The implementation is centered on
`backends.sympy.MathformerPhysicsSympy.pipeline.build_physics_regime_assumption_packet()`.
It records source-backed assumptions, regime categories, condition records,
SymPy assumption hints, and silent-strengthening policy checks.

The supported assumption catalog covers constant acceleration,
frictionless/no-damping/no-drag regimes, small-angle approximations,
nonrelativistic speed, massless spring/string assumptions, ideal gas, lumped
circuit elements, steady or quasistatic regimes, and positivity/nonzero
restrictions.

The default phase command emits:

```text
artifacts/physics_sympy/<case_id>/regime_assumption_packet.json
```

Validate changes with:

```bash
.venv/bin/python tests/physics_sympy/run_phase6_assumptions_frames.py --json
```
