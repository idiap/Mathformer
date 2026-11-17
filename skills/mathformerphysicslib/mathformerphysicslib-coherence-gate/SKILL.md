---
name: mathformerphysicslib-coherence-gate
description: Gate MathformerPhysicsLib coherence using deterministic critics, generative probes, and repair-plan evidence.
---


# MathformerPhysicsLib Coherence Gate

Use this skill as the final loop step before a generated physics formalization is
allowed to reuse or extend MathformerPhysicsLib.

## Workflow

1. Run `scripts/gate_coherence.py` with critic reports and repair evidence.
2. Treat `blocked` as a stop condition for target formalization edits.
3. Treat `accepted` as permission to reuse promoted foundation surfaces.

## Outputs

- `mathformerphysicslib_coherence_gate`
- accepted/warn/blocked decision
- markdown handoff report when requested
