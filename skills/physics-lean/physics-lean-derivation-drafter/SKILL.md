---
name: physics-lean-derivation-drafter
description: Draft Lean 4 physics derivation artifacts from source packets, typed physics packets, contextual assumptions, unit obligations, physical-law grounding, mathlib hints, and source anchors.
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

# Physics Lean Derivation Drafter

Use after the Lean physics workflow plan, type-system packet, assumption packet,
unit packet, and mathlib import context are available.

## Drafting Requirements

- Put the full original informal statement and informal derivation in a module
  doc-comment header immediately after imports and before the namespace or first
  declaration.
- In that same header, include a concise alignment map from each numbered
  informal derivation step to the corresponding Lean theorem hypothesis,
  generated-support lemma, local proof block, or final `calc` line.
- Keep declaration-level comments short; do not move the full commentary out of
  the header.
- Preserve source anchors in declaration-level comments.
- Include a physics context comment naming quantities, dimensions, units,
  frames, regimes, and physical laws.
- Start from Mathlib-native carriers and predicates whenever they exist:
  `EuclideanSpace Real (Fin n)` for finite vectors, `X -> EuclideanSpace Real
  (Fin 3)` for vector fields, `LinearMap`/`→ₗ` for linear physics operators,
  `HasDerivAt`/`HasFDerivAt`/`Differentiable`/`ContDiff` for calculus, and
  matrices/modules/inner products for quantum/operator claims.
- Treat local `Quantity`, `VectorQuantity`, `PhysDim`, opaque dimension names,
  and `String`-valued law/context fields as fallback scaffolds. Do not use them
  as the only final typing surface for complete status.
- When the final physics theorem contains a mostly algebraic proof, extract a
  compact reusable core theorem first. The core should use the smallest
  dataset-style mathematical surface needed for the proof, while the
  physics-rich wrapper theorem preserves Mathlib-typed quantities, dimensions
  or explicit blockers, contextual assumptions as typed propositions,
  source-law assumptions, and projection bridges, then proves the final claim by
  calling the core theorem.
- Prefer mathlib-native calculus, algebra, inner-product, vector, and measure
  APIs when available.
- Before the target theorem, materialize every required background item from
  the background dependency plan: Mathlib-native carrier definitions, field or
  operator definitions, projection bridges, source-law support lemmas,
  unit/dimension bridge lemmas, calculus support lemmas, and compact algebraic
  core theorems.
- Emit support declarations in dependency order. Each declaration must have a
  short source-aware comment: `Source-backed`, `Mathlib-backed`,
  `Generated-support`, or `Blocked`, plus the informal step or background item
  it supports.
- Reuse verified Mathlib or existing `MathformerPhysicsLib` declarations before
  creating local support. If a required background item cannot be formalized,
  keep it as an explicit blocker and do not mark the target theorem complete.
- Use small local structures only when they carry actual obligations used by the
  theorem and the mathlib grounding report records why a native surface is not
  available.
- Prove unit/dimension lemmas or emit explicit blockers before claiming
  complete status.
- Use generated-support lemmas for unavoidable physics abstractions, with
  comments that say what source law they represent.
- Do not use `axiom` for the final claim, and do not assume the target equation.
- Do not create background lemmas that are equivalent to the final target under
  a renamed conclusion; background results must be proper prerequisites or
  bridge facts.

The initial artifact should compile as soon as possible, but not by weakening
the source physics.
