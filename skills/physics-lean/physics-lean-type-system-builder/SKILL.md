---
name: physics-lean-type-system-builder
description: Build Lean-facing physics type packets for source quantities, dimensions, units, vectors, frames, laws, and regimes so physics derivations are not reduced to empty scalar algebra.
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

# Physics Lean Type System Builder

Use after the physics symbol, dimension, unit, frame, regime, and law packets
exist, before first Lean drafting.

## Output Policy

Emit a type packet that tells the Lean drafter how to represent:

- scalar quantities versus vectors, fields, operators, and functions;
- physical dimensions and unit obligations;
- coordinate frames, bases, projections, and sign conventions;
- contextual assumptions such as positivity, nonzero denominators, smoothness,
  constant parameters, boundary conditions, gauge choices, or idealizations;
- physical laws used as source-backed hypotheses, generated support lemmas, or
  mathlib-backed theorems.
- intermediate definitions and background results that must be formalized or
  reused before the target theorem can depend on them.

## Maximal Mathlib Grounding Policy

The first target is a Mathlib-native theorem surface, not local placeholder
wrappers:

- vectors and component projections should use `EuclideanSpace Real (Fin n)` or
  a Mathlib-backed `Fin n -> Real` API with existing algebraic instances;
- fields should be functions into Mathlib vector/module types, such as
  `X -> EuclideanSpace Real (Fin 3)`;
- differential assumptions should use `HasDerivAt`, `HasFDerivAt`,
  `Differentiable`, or `ContDiff` where the source needs calculus;
- linear physics operators should use `LinearMap`, continuous linear maps, or
  module homomorphisms when compatible with the proof;
- quantum/operator examples should prefer modules, inner products, matrices,
  linear maps, and self-adjoint/Hermitian predicates before creating local
  wrappers.

Local `Quantity`, `VectorQuantity`, `PhysDim`, opaque dimension markers, and
`String`-valued law/context labels are fallback scaffolds only. They must be
marked as blockers for complete status unless a Mathlib-compatible abstraction
boundary is documented.

## Background Formalization Requirements

The packet must include a queue for required support declarations:

- Mathlib-native carriers, projections, field/operator definitions, and
  smoothness predicates;
- derivative, product-rule, chain-rule, source-law, and constitutive-law
  support lemmas;
- unit/dimension homogeneity bridge lemmas;
- compact algebraic core theorems used by the physics-rich wrapper.

Every queued item must be marked `source_backed`, `mathlib_backed`,
`generated_support`, or `blocked`. Complete status requires each item to be
formalized, reused from Mathlib/MathformerPhysicsLib, or explicitly blocked;
the target theorem may not silently assume unresolved background.

## Non-Empty Formalism Rules

- Avoid theorem shapes that are merely `h : target -> target`.
- Avoid turning the final physics claim into an assumption.
- Use raw `ℝ` algebra only for explicitly dimensionless algebraic substeps or
  after a local lemma relates Mathlib-typed quantities to scalar coordinates.
- Prefer Mathlib-native interfaces over project-local uninterpreted structures.
- Every generated support abstraction must say which source law or derivation
  step it represents.
- Background lemmas must be narrower than the final theorem and must not encode
  the target conclusion as an assumption.

Prefer `scripts/build_physics_lean_type_system.py` for a deterministic initial
packet.
