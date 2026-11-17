---
name: physics-lean-review-refinement-router
description: Convert failed final physics and mathematical hypothesis reviews, plus semantic-preservation design-guard warnings, into localized monotonic Lean physics refinement plans, preserving already-correct source anchors, theorem shapes, units, assumptions, proof realness, non-vacuity, mathlib grounding, and execution evidence.
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

# Physics Lean Review Refinement Router

Use when final physics or mathematical hypothesis review fails, or when the
review reports semantic-preservation design-guard warnings. This skill does not
rewrite the artifact directly; it constrains the next refinement step.

Load `artifacts/physics_lean/reviews/autoformalization_design_todos.md` when the
finding touches semantic preservation, vacuous context labels, reflexive unit
bridges, audit anchors, or other physicist/TP review TODOs.

## Routing Contract

For each reviewer finding:

1. Identify the smallest repair surface.
2. Identify protected properties that already passed.
3. Specify which file region, theorem, support lemma, assumption label, or proof
   fragment may be edited.
4. Specify which gates must rerun after the edit.
5. Block broad rewrites unless the source requires a theorem-shape correction.

Prefer `scripts/plan_review_refinement.py` for deterministic refinement plans.

## Local Repair Surfaces

- `quantity_typing`: add or repair typed quantity bindings.
- `unit_dimension_obligation`: add dimension lemmas or unit hypotheses.
- `contextual_assumption`: label or source-anchor side conditions.
- `law_grounding`: replace target-shaped law assumptions with source-backed laws.
- `frame_regime`: add frame, sign, gauge, regime, or approximation context.
- `projection_bridge`: connect scalar projections back to typed quantities.
- `mathlib_grounding`: replace avoidable local physics wrappers, opaque
  dimensions, and string context labels with Mathlib-native carriers,
  predicates, and typed Prop assumptions.
- `binder_domain`: repair variable domains or missing type parameters.
- `quantifier_shape`: restore forall, exists, unique, iff, or implication shape.
- `conclusion_shape`: restore the intended target without weakening.
- `support_dependency`: formalize or reuse the smallest missing background
  definition, background result, projection bridge, source-law support lemma,
  unit/dimension bridge, or algebraic core named by the review.
- `source_alignment_commentary`: add or repair the semantic-preservation
  contract, source/Lean target mapping, preservation status, semantic deltas,
  step alignment, and trust boundary without changing the theorem body.
- `design_guard`: apply the smallest review TODO repair for semantic
  preservation, non-vacuous contexts, non-reflexive unit evidence, audit-anchor
  cleanup, or missing source-alignment metadata.
- `proof_realness`: remove placeholders without changing theorem meaning.
- `nonvacuity`: remove contradictory or target-shaped hypotheses.

## Monotonicity Rule

A review refinement is monotonic only if:

- it does not remove a passing source anchor;
- it does not weaken the theorem conclusion;
- it does not strengthen hypotheses without a source or generated-support label;
- it does not reduce unit/dimension coverage;
- it does not reduce Mathlib-native theorem-surface coverage;
- it does not reclassify local wrappers, opaque dimensions, or string labels as
  maximal grounding;
- it does not introduce `sorry`, `admit`, target axioms, or vacuous hypotheses;
- it preserves semantic-preservation contract fields once present;
- it treats replacement of `PhysicsContext True` and reflexive
  `UnitDimensionCompatible x x` as evidence-strengthening work, not a reason to
  weaken the theorem or hide assumptions;
- it reruns the affected reviewers and all potentially impacted protected
  gates.
