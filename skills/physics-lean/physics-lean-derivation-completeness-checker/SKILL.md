---
name: physics-lean-derivation-completeness-checker
description: Check whether a Lean physics artifact is a complete autoformalization rather than a compiling scaffold with target-restating hypotheses, unresolved source-step obligations, or open recursive frontier.
---

# Physics Lean Derivation Completeness Checker

Use after Lean compilation and MathformerPhysicsLib grounding checks, before an
artifact is described as a complete autoformalization.

## Workflow

1. Run `scripts/check_derivation_completeness.py` on the generated Lean file.
2. Provide the source record when available so the checker can build a
   source-step obligation ledger.
3. Provide the recursive grounding plan when available so open frontier blocks
   complete status.
4. Treat `complete_autoformalization` as the only complete status.
5. Treat `blocked_target_restating_assumption` as a repair-loop blocker.

## Outputs

- `physics_lean_derivation_completeness_report`
- status flags for compile surface, grounded scaffold, partial derivation, and
  complete autoformalization
- target-restatement findings
- source-step obligation ledger
- recursive repair frontier nodes
- deterministic-evidence-bound generative probes
