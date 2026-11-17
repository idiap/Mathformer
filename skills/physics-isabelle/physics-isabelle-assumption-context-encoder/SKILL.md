---
name: physics-isabelle-assumption-context-encoder
description: Encode contextual physics assumptions for Isabelle/HOL, including source-backed and generated-support labels for smoothness, nonzero side conditions, frames, boundaries, regimes, and operator laws.
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

# Physics Isabelle Assumption Context Encoder

Use after physics regime/frame/unit/law packets and before Isabelle/HOL theory
drafting.

The output is intentionally Isabelle-specific and must not rewrite Lean
assumption packets.

Prefer `scripts/encode_physics_isabelle_assumptions.py`.

