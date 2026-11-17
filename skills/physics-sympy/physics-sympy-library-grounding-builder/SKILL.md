---
name: physics-sympy-library-grounding-builder
description: Build a maximal installed-library grounding packet for physics SymPy derivations. Use before SymPy physics drafting, equation-surface review, or consistency reporting when scalar algebra, calculus, units, vectors, mechanics, matrices, quantum operators, or numeric validation should be grounded in concrete installed SymPy/dependency APIs rather than local placeholders.
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

# Physics SymPy Library Grounding Builder

Use this skill after dependency probing, informal expansion, and law grounding,
and before `physics-sympy-equation-surface-builder` or final review.

It produces `physics_sympy_library_grounding_packet` with:

- installed SymPy/dependency surface inventory
- case-required roles
- selected concrete APIs for each role
- missing APIs and completion blockers
- `grounding_level` with `high` required for complete status

Prefer the deterministic script:

```bash
PYTHONPATH=. python skills/physics-sympy/physics-sympy-library-grounding-builder/scripts/build_physics_sympy_library_grounding.py \
  --case-id formalphysics_0000 \
  --output artifacts/physics_sympy/formalphysics_0000/library_grounding.json
```

Completion policy:

- `high`: every case-required role has installed API support.
- `medium`: core scalar/equational support exists but a physics-specific role is missing.
- `low`: required scalar, unit, or numeric grounding is missing.

Do not treat a scalar-only SymPy trace as complete for vector, field, mechanics,
operator, or unit-bearing physics unless the packet records explicit projection
bridges and selected installed APIs for the relevant role.
