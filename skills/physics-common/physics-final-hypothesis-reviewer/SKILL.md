---
name: physics-final-hypothesis-reviewer
description: Review final formalized physics derivation hypotheses before acceptance, checking that physical quantities, dimensions, units, laws, frames, regimes, contextual assumptions, and derived target hypotheses match the source and downstream Lean artifact. Use at the end of the Lean physics pipeline before final consistency approval or when a review failure must route to localized refinement.
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

# Physics Final Hypothesis Reviewer

Use this at the end of a Lean physics derivation run, after drafting,
execution, unit analysis, physics critics, reverse informalization, and
non-vacuity checks have produced evidence.

## Review Contract

Validate the final formalized derivation hypotheses against the source physics:

1. Every source physical quantity is represented on the most Mathlib-native
   available surface: `EuclideanSpace`, vector fields, calculus predicates,
   `LinearMap`/operator structures, matrices, modules, inner products, or
   explicitly justified scalar projections before local wrappers are accepted.
2. Unit and dimension hypotheses are present where the derivation needs them.
3. Coordinate frame, basis, sign convention, gauge, observer, and regime
   assumptions are explicit.
4. Positivity, nonzero, smoothness, integrability, boundary, and initial
   conditions are source-backed or generated-support labeled.
5. Physical laws and constitutive assumptions are named and connected to source
   anchors or generated support lemmas.
6. Required intermediate definitions, background results, projection bridges,
   source-law support lemmas, unit/dimension bridge lemmas, and algebraic cores
   are formalized, Mathlib/MathformerPhysicsLib-reused, or explicitly blocked
   before the target theorem is accepted.
7. Approximation, idealization, and limiting assumptions are not silently
   strengthened.
8. The final target is not hidden as a hypothesis, axiom, constant, or
   all-purpose law.
9. The artifact reaches high Mathlib grounding for physics-bearing theorem
   surfaces, or records a concrete abstraction-boundary blocker and remains
   draft/blocked.

Prefer `scripts/review_physics_final_hypotheses.py` for deterministic screening.

## Common Failure Modes

- Raw scalar erasure of dimensioned quantities.
- Vector or tensor equations reduced to unrelated scalar claims.
- Missing inertial-frame, coordinate, gauge, or sign convention.
- Unlabeled positivity or nonzero assumptions introduced only to satisfy Lean.
- Missing smoothness or boundary hypotheses for differential/integral steps.
- Law grounding replaced by a target-shaped law assumption.
- Unit report passes globally but individual transformation hypotheses omit
  dimension obligations.
- Required background definitions or support lemmas remain informal while the
  target theorem treats them as assumptions.
- Generated support lemmas are equivalent to the final target instead of proper
  prerequisites or bridge facts.
- Local `Quantity`, `VectorQuantity`, `PhysDim`, opaque dimension markers, or
  `String` context labels counted as maximal grounding instead of fallback
  scaffolds.
- Scalar `Real` core theorem accepted without a Mathlib-typed wrapper or
  projection theorem that preserves the physics semantics.

## Refinement Handoff

When the review fails, emit findings with localized repair surfaces:

- `quantity_typing`
- `unit_dimension_obligation`
- `contextual_assumption`
- `law_grounding`
- `frame_regime`
- `projection_bridge`
- `support_dependency`
- `target_nonvacuity`
- `mathlib_grounding`

Route failures to `physics-lean-review-refinement-router`. Repairs must preserve
passing source anchors, theorem names, imports, proof realness, non-vacuity,
unit consistency, and already-passing reviewer findings unless the source itself
forces a documented statement change.
