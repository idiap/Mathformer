---
name: physics-isabelle-final-hypothesis-reviewer
description: Review final Isabelle/HOL physics hypotheses for source-aligned quantities, dimensions, units, frames, laws, generated-support assumptions, theorem non-vacuity, and explanatory Isar comments.
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

# Physics Isabelle Final Hypothesis Reviewer

Use near the end of an Isabelle/HOL physics formalization run after drafting,
execution, type packets, and assumption packets exist.

The reviewer enforces maximal Isabelle/HOL grounding for physics-bearing
sources: final candidates must expose native `Complex_Main`/`HOL-Analysis`
surfaces or an explicit dependency blocker, must not complete with local
quantity/context records as the main semantics, and must close background
definition/result obligations before complete status.

Prefer `scripts/review_physics_isabelle_final_hypotheses.py`.
