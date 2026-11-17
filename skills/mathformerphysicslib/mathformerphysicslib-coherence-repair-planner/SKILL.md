---
name: mathformerphysicslib-coherence-repair-planner
description: Convert MathformerPhysicsLib coherence, grounding, integration, and generative critic findings into controlled repair actions.
---


# MathformerPhysicsLib Coherence Repair Planner

Use this skill when critics have produced findings and the next step must be a
controlled repair plan rather than direct edits in target formalizations.

## Workflow

1. Run `scripts/plan_coherence_repairs.py`.
2. Apply only repairs that preserve Mathlib-first grounding and single canonical
   ownership.
3. Re-run the coherence gate before target-theorem repair.

## Outputs

- `mathformerphysicslib_coherence_repair_plan`
- severity-ordered repair actions
- target-handoff constraints
