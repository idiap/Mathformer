---
name: final-derivation-review-orchestrator
description: Orchestrate end-of-pipeline physics and mathematical reviewer skills for final formalized derivation hypotheses, combine their findings into an acceptance gate, and route failures to localized monotonic refinement without breaking already-correct parts.
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

# Final Derivation Review Orchestrator

Use at the end of a formalized derivation pipeline, immediately before final
consistency approval or acceptance reporting.

## Review Order

1. Run `physics-final-hypothesis-reviewer` for physics-bearing derivations.
2. Run `mathematical-final-hypothesis-reviewer` for all final formalized
   derivations.
3. Combine reviewer reports with compile, realness, source-anchor, non-vacuity,
   unit, assumption, and critic evidence.
4. If any blocking finding remains, route to
   `physics-lean-review-refinement-router` with localized repair surfaces.
5. Re-run only the affected reviewer plus all protected gates that could be
   impacted by the local edit.

Prefer `scripts/run_final_derivation_review.py` for deterministic aggregation.

## Required Properties

Final acceptance requires:

- physics review passes or is explicitly not applicable;
- mathematical review passes;
- all blockers have localized repair targets;
- no review failure is hidden as a warning;
- failed reviews produce a monotonic refinement plan;
- the final report records which already-correct properties must be preserved.

## Monotonicity Rule

Review-driven refinement must be local. It may edit only the theorem surface,
support lemma, assumption label, projection bridge, law grounding, or proof
fragment identified by the review finding. Any broader edit requires a source
anchor and reruns the full protected gate stack.
