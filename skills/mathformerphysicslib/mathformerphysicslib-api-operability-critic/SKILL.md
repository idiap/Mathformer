---
name: mathformerphysicslib-api-operability-critic
description: Criticize whether MathformerPhysicsLib canonical concepts are usable APIs for downstream physics autoformalization.
---


# MathformerPhysicsLib API Operability Critic

Use this skill when a concept exists but may not be usable by generated physics
formalizations.

## Workflow

1. Run `scripts/critic_api_operability.py`.
2. Check that canonical records expose declarations, importable owners, and
   reuse signals.
3. Feed findings into the generative coherence critic and repair planner.

## Outputs

- `mathformerphysicslib_api_operability_critic`
- API usability findings
- importability and declaration-presence checks
