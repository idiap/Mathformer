---
name: physics-sympy-assumption-context-encoder
description: Encode contextual physics assumptions for SymPy equation traces. Use when positivity, nonzero, realness, smoothness, differentiability, frames, gauges, regimes, idealizations, boundary or initial conditions, and generated-support assumptions must be made explicit before drafting or review.
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

# Physics SymPy Assumption Context Encoder

Use this skill after regime, frame, equation, and symbol packets exist. It maps
physics context into SymPy-compatible symbol assumptions plus an explicit
side-condition ledger.

## Contract

Produce `physics_sympy_assumption_context_packet` with:

- source-backed assumptions;
- generated-support assumptions;
- SymPy symbol assumptions;
- side conditions for transformations;
- blockers for missing or silently strengthened assumptions.

Prefer `scripts/encode_physics_sympy_assumptions.py` for deterministic
first-pass encoding.

## Requirements

- Label every assumption as `source_backed`, `generated_support`,
  `api_backed`, or `blocked`.
- Do not silently strengthen the source.
- Keep frame, sign convention, gauge, regime, approximation, boundary, initial,
  smoothness, positivity, and nonzero assumptions visible to reviewers.

