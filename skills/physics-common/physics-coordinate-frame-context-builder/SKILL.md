---
name: physics-coordinate-frame-context-builder
description: Build coordinate-frame and sign-convention context for physics SymPy derivations, including axes, origin, basis, positive direction, scalar projections, and one-dimensional reductions.
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

# Physics Coordinate Frame Context Builder

Use when vector or sign-sensitive laws are involved. It makes frame assumptions
explicit before equations are reduced to executable scalar forms.

The implementation is centered on
`backends.sympy.MathformerPhysicsSympy.pipeline.build_physics_frame_context_packet()`.
It records axis orientation, origin, positive direction, basis vectors, scalar
projection from vector laws, and one-dimensional reductions. If the source
does not state an origin, keep it as `source_unspecified` with an uncertainty
note instead of inventing one.

The default phase command emits:

```text
artifacts/physics_sympy/<case_id>/frame_context_packet.json
```

Validate changes with:

```bash
.venv/bin/python tests/physics_sympy/run_phase6_assumptions_frames.py --json
```
