---
name: mathformerphysicslib-coherence-inventory-builder
description: Build a MathformerPhysicsLib declaration, import, and concept inventory before coherence, grounding, or repair work.
---


# MathformerPhysicsLib Coherence Inventory Builder

Use this skill when MathformerPhysicsLib needs a current inventory of Lean files,
imports, declarations, and physics concept cues before critique or repair.

## Workflow

1. Run `scripts/build_coherence_inventory.py`.
2. Treat the output as observation only; it does not promote or repair objects.
3. Pass the inventory to canonicalization, grounding, integration, and repair
   skills.

## Outputs

- `mathformerphysicslib_coherence_inventory`
- file/import/declaration records
- concept cue evidence used by downstream critics
