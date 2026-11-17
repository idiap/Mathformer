---
name: physics-formal-answer-comparison-reflector
description: Compare completed or draft Mathformer Lean physics formalizations with withheld FormalScience/FormalPhysics `formal_answer` code after the informal-first run. Use when post-hoc dataset formal answers should provide inspiration, portability checks, theorem-shape contrasts, or monotonic pipeline refinements without being treated as benchmark labels or ground truth.
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

# Physics Formal Answer Comparison Reflector

Use only after the informal-first formalization path has produced a candidate,
review packet, or explicit draft blockers. Do not inspect the dataset
`formal_answer` field before first-pass drafting, informal expansion, typing,
assumption encoding, or reviewer critique.

## Workflow

1. Load the selected FormalPhysics records and their withheld `formal_answer`
   fields.
2. Optionally compile each withheld Lean snippet with the local Lean toolchain.
3. Analyze theorem shape, imports, proof tactics, abstraction level, source
   anchors, unit/dimension surfaces, and physics-context encoding.
4. Compare against the Mathformer candidate when one is available. If no local
   candidate exists, emit a dataset-only inspiration report.
5. Propose localized monotonic refinements only. A dataset formal answer can
   suggest an abstraction, lemma split, or proof tactic, but cannot override
   source semantics, unit discipline, or final reviewers.

## Required Policy

- Mark every report as `inspiration_only_not_benchmark`.
- Keep dataset formal answers out of prompts for first-pass drafting.
- Separate Lean executability from physical-semantic adequacy.
- Prefer improvements that preserve already passing gates: source anchors,
  theorem shape, unit coverage, assumption labels, realness, non-vacuity, and
  mathlib grounding.
- Route any accepted improvement through the normal physics Lean review
  refinement path.

Prefer `scripts/compare_formal_physics_answers.py` for deterministic reports.
