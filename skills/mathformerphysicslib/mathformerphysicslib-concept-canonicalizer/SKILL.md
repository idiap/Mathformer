---
name: mathformerphysicslib-concept-canonicalizer
description: Canonicalize detected MathformerPhysicsLib physics concepts into owned foundation records and spread-risk evidence.
---


# MathformerPhysicsLib Concept Canonicalizer

Use this skill after inventory when physics concepts must be organized into
canonical MathformerPhysicsLib records instead of scattered local definitions.

## Workflow

1. Run `scripts/canonicalize_physics_concepts.py` with an inventory when
   available.
2. Inspect each concept status: canonical, missing, or spread.
3. Send the concept graph to Mathlib grounding and critic skills.

## Outputs

- `mathformerphysicslib_concept_graph`
- canonical owner candidates
- spread and missing concept evidence
