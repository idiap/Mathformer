---
name: physics-isabelle-consistency-report-orchestrator
description: Aggregate Isabelle/HOL physics execution, type, assumption, final-review, source-anchor, realness, and placeholder evidence into a backend-specific consistency report.
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

# Physics Isabelle Consistency Report Orchestrator

Use at the end of a Physics-Isabelle run. It is a sibling of the Lean physics
consistency report, not a replacement for it.

Complete status requires passing Isabelle execution/review evidence, high
Isabelle/HOL library grounding for physics-bearing sources, and no open
background formalization obligations unless the artifact is explicitly blocked.

Prefer `scripts/run_physics_isabelle_consistency_report.py`.
