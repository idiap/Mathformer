---
name: physics-lean-unit-analysis-verifier
description: Verify Lean physics artifacts for unit and dimension discipline, checking that source quantities are typed or explicitly projected, dimension obligations are present, and raw scalar erasure is reported before complete status.
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

# Physics Lean Unit Analysis Verifier

Use after drafting, after each major refinement, and before final acceptance of
a Lean physics artifact.

## Gate

Complete status requires:

- a declared dimension/unit policy;
- typed or explicitly projected source quantities;
- unit/dimension consistency lemmas or explicit blockers;
- contextual assumptions needed for unit transformations;
- no raw-`ℝ` erasure for physical quantities without projection lemmas.

Prefer `scripts/verify_physics_lean_units.py` for deterministic artifact
screening.

