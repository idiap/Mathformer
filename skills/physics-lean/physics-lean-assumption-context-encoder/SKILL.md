---
name: physics-lean-assumption-context-encoder
description: Encode contextual physics assumptions for Lean, including regimes, frames, smoothness, positivity, nonzero side conditions, boundary conditions, idealizations, and generated-support notes without silently strengthening the source.
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

# Physics Lean Assumption Context Encoder

Use after regime, frame, unit, and law grounding packets exist and before Lean
drafting or refinement changes theorem statements.

## Encoding Choices

Represent assumptions as one of:

- typed variables and hypotheses in theorem statements;
- fields of a small context structure;
- local lemmas for source-backed laws;
- generated-support assumptions with explicit comments and blockers;
- namespace/section parameters when shared by several declarations.

## Gates

- Every assumption must be source-backed, mathlib-backed, or generated-support.
- Positivity, nonzero, smoothness, differentiability, integrability, boundary,
  gauge, frame, and approximation assumptions must be explicit.
- Silent strengthening blocks complete status.
- The final target must not be moved into assumptions.

Prefer `scripts/encode_physics_lean_assumptions.py` for an initial assumption
packet from source text.

