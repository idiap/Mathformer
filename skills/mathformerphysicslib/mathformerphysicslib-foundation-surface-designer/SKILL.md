---
name: mathformerphysicslib-foundation-surface-designer
description: Design Mathlib-first Lean foundation surfaces for normalized physics objects, choosing reuse, thin bridge modules, abstraction boundaries, imports, and promotion gates before drafting MathformerPhysicsLib code.
---

# MathformerPhysicsLib Foundation Surface Designer

Use after `physics-foundation-object-intake` and before Lean drafting. This
skill decides whether each physics foundation object should reuse Mathlib
directly, reuse accepted MathformerPhysicsLib support, draft a small bridge, or
remain blocked.

Prefer `scripts/design_foundation_surfaces.py`.

## Contract

- Start from Mathlib-native carriers and operators.
- Keep local surfaces thin and physics-specific.
- Emit module paths, declaration plans, import plans, acceptance gates, and
  explicit abstraction boundaries.
- Never turn a missing foundation into a target-theorem hypothesis.
