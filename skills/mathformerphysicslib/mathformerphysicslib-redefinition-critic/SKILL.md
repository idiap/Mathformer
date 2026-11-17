---
name: mathformerphysicslib-redefinition-critic
description: Criticize MathformerPhysicsLib concepts for duplicate definitions, scattered ownership, and avoidable local replacements for Mathlib objects.
---


# MathformerPhysicsLib Redefinition Critic

Use this skill after canonicalization and grounding to detect whether a physics
concept is spread across files or locally redefined when Mathlib should be used.

## Workflow

1. Run `scripts/critic_redefinitions.py`.
2. Treat high-severity findings as repair blockers.
3. Route repair through the coherence repair planner before editing target
   formalizations.

## Outputs

- `mathformerphysicslib_redefinition_critic`
- high/medium/low findings
- desirable properties for single ownership and Mathlib reuse
