---
name: mathformerphysicslib-foundation-drafter
description: Draft conservative Lean foundation modules for MathformerPhysicsLib from surface plans, generating only missing Mathlib-backed bridge declarations and never marking drafts as promoted support.
---

# MathformerPhysicsLib Foundation Drafter

Use after `mathformerphysicslib-foundation-surface-designer`. This skill writes
or previews conservative Lean modules under `libraries/MathformerPhysicsLib/Lean/Foundations`.

Prefer `scripts/draft_foundation_modules.py`.

## Contract

- Generate only the missing bridge/support declarations from the surface plan.
- Include declaration comments naming Mathlib grounding and physics role.
- Avoid `sorry`, `admit`, generated axioms, and `Prop := True` final support.
- Treat output as candidate support until verifier and promotion gates pass.
