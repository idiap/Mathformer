---
name: physics-lean-assumption-critic
description: Critique contextual assumptions in Lean physics formalizations, detecting hidden strengthening, missing side conditions, unlabeled generated assumptions, frame/regime omissions, and assumption drift between source text, packets, and Lean code.
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

# Physics Lean Assumption Critic

Use this critic whenever a Lean physics artifact introduces or depends on
positivity, nonzero denominators, differentiability, smoothness, integrability,
boundary conditions, frames, gauges, constant-quantity assumptions, or
idealization regimes.

## Critic Contract

1. Compare the informal source, assumption packet, and Lean hypotheses.
2. Mark every assumption as one of:
   - source-backed,
   - mathlib-backed,
   - generated-support,
   - blocked.
3. Fail hidden strengthening when Lean assumes more than the source without a
   generated-support label.
4. Fail missing assumptions when the derivation needs a side condition but the
   Lean artifact or packet omits it.
5. Warn on under-specified frame, gauge, sign, or approximation conventions.

Prefer `scripts/critique_physics_lean_assumptions.py` for deterministic
screening.

## Generative Mode

This critic may use Codex exec. Ask independent critics to generate assumption
stress tests:

- Remove a Lean hypothesis and predict which physics step should break.
- Try a boundary, sign, or frame convention opposite to the one implied by the
  source.
- Identify source sentences that justify each Lean side condition.
- Identify Lean side conditions that have no source sentence.

Do not accept a generative assumption repair unless it preserves the source
claim and labels the new assumption explicitly.
