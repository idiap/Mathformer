---
name: physics-sympy-dependency-prober
description: Probe required and optional dependencies for executable physics derivation autoformalization over SymPy, including units, mechanics, vector, numeric, and optional unit cross-check packages.
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

# Physics SymPy Dependency Prober

Use before any `sympy_physics_derivation_trace` run. It reports required SymPy
physics modules and optional numeric/unit-reporting dependencies without
promoting missing optional packages to complete-status failures.

The standard report is written to
`artifacts/physics_sympy/<case_id>/dependency_probe.json`. It records required
and optional modules, disabled optional checks, the optional-dependency
downgrade policy, and the versioned `physics_sympy_api_index_v1` shard for
SymPy physics, units, dimensions, mechanics/vector, and solver/calculus APIs.

Run:

```bash
python skills/physics-sympy/physics-sympy-dependency-prober/scripts/probe_physics_sympy_dependencies.py --json
```
