---
name: physics-lean-consistency-report-orchestrator
description: Produce final Lean physics consistency reports that combine Lean execution, source anchors, realness, unit/dimension analysis, assumption context, explicit physics critic reports, recursive pathology repair expansion/control evidence, final physics and mathematical hypothesis review, mathlib grounding, reverse informalization, non-vacuity, and RFDE evidence.
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

# Physics Lean Consistency Report Orchestrator

Use before reporting a Lean physics derivation as complete, draft, or blocked.

Complete status requires:

- Lean execution/compile success under intended imports;
- no `sorry`, `admit`, target axioms, or target-as-assumption shapes;
- source-anchor coverage and no orphan anchors;
- passing unit/dimension report;
- contextual assumptions encoded and source-status labeled;
- required intermediate definitions, background results, projection bridges,
  source-law support lemmas, unit/dimension bridges, and algebraic cores
  formalized, reused, or explicitly blocked;
- passing or explicitly justified physical-semantics, assumption, dimension,
  FormalScience drift-pathology monitor, and generative critic reports;
- passing final physics and mathematical hypothesis review reports;
- high Mathlib grounding for physics-bearing theorem surfaces, or explicit
  abstraction-boundary gaps that keep the artifact draft/blocked;
- when a FormalScience pathology was detected, a pathology repair loop report
  showing MathformerPhysicsLib object work is complete or explicitly blocked;
- guarded generative repair plan or report evidence for high-risk or blocked
  pathology repairs, treated as advisory until deterministic gates rerun;
- exhaustive repair expansion map and recursive repair control evidence when
  pathology repair is active; a `recurse` or `blocked` control decision prevents
  complete status;
- reverse informalization aligned with source physics;
- non-vacuity and declaration-shape consistency;
- RFDE trajectory evidence.

Prefer `scripts/run_physics_lean_consistency_report.py` for deterministic
status aggregation from available reports.
