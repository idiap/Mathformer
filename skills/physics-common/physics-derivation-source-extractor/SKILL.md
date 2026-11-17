---
name: physics-derivation-source-extractor
description: Extract source-backed physics derivation units from NL/LaTeX, including quantities, laws, equations, assumptions, regimes, frames, conditions, approximations, derivation steps, and target equations.
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

# Physics Derivation Source Extractor

Use after source intake for physics derivations. Every extracted unit must carry
literal source text, source anchors, quantity symbols, candidate dimensions and
units, and uncertainty notes when the source is ambiguous.

The extractor emits Phase 2 units with roles from the controlled ontology:
`quantity_definition`, `physical_law`, `constitutive_relation`,
`coordinate_context`, `initial_condition`, `boundary_condition`,
`approximation_regime`, `algebraic_step`, `calculus_step`,
`substitution_step`, and `target_equation`. Use these units as the source
contract for later symbol-table, dimension, equation, and derivation-planning
phases.

Run:

```bash
python skills/physics-common/physics-derivation-source-extractor/scripts/extract_physics_derivation_source.py --source tests/physics_sympy/controlled_latex/constant_acceleration_position.tex --json
```
