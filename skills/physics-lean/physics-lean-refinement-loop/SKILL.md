---
name: physics-lean-refinement-loop
description: Coordinate iterative refinement for Lean physics artifacts using Lean diagnostics, physics type packets, unit analysis, explicit physics critic reports, final hypothesis review findings, contextual-assumption checks, source-anchor drift, reverse informalization, mathlib grounding, and RFDE process reflection.
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

# Physics Lean Refinement Loop

Use after a Lean physics draft has execution, unit, critique, or consistency
findings.

## Loop Order

1. Classify Lean diagnostics with `physics-lean-execution-interpreter`.
2. Repair imports and mathlib APIs before changing theorem meaning.
3. Repair type-system and projection lemmas before proof search.
4. Repair unit/dimension obligations before semantic acceptance.
5. Run deterministic critics, and run Codex-exec generative critics when an
   artifact is high-risk, near-final, or critic disagreement persists.
6. Run final hypothesis reviewers before acceptance; if they fail, hand off to
   `physics-lean-review-refinement-router`.
7. Repair contextual assumptions only with source-backed or generated-support
   notes.
8. Run source-anchor, realness, informalization, declaration-shape, and
   non-vacuity gates after each material statement change.
9. Use RFDE/process reflection only after repeated blockers or costly plateaus.

## Stop Conditions

- `complete`: Lean executes and all protected physics/Lean gates pass.
- `draft`: useful formal content exists but a noncritical gate is open.
- `blocked`: the same high-severity blocker persists after repeated localized
  repair attempts.
