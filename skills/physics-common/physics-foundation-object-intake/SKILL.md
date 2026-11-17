---
name: physics-foundation-object-intake
description: Normalize user-provided physics concepts, benchmark clusters, or detected physics mathematical objects into a controlled MathformerPhysicsLib foundations object packet before Mathlib grounding and Lean drafting.
---

# Physics Foundation Object Intake

Use at the start of the MathformerPhysicsLib foundations workflow. This skill
turns informal concepts such as "vector field", "curl operator", "unit
compatibility", or detector output from `physics-math-object-detector` into a
canonical `physics_foundation_object_packet`.

Prefer `scripts/intake_physics_foundation_objects.py`.

## Contract

- Preserve the user-facing concept text.
- Assign stable `object_id`, `object_class`, Mathlib search terms, module
  family, required semantics, source examples, and priority.
- Split overloaded concepts into separate objects when needed.
- Merge duplicates by canonical `object_id`, not surface wording.
- Mark the output as concept intake only; do not claim promotion or compile
  success at this stage.
