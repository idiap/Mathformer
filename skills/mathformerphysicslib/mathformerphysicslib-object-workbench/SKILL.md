---
name: mathformerphysicslib-object-workbench
description: Work over detected physics mathematical objects in MathformerPhysicsLib before target theorem repair, searching reusable declarations, planning support modules, drafting candidate Lean surfaces, and naming promotion-gated handoff evidence.
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

# MathformerPhysicsLib Object Workbench

Use after `physics-math-object-detector`. This skill is the library-first stage
of pathology repair: repair plans may not edit the target theorem until the
missing physics object has been searched, reused, drafted, promoted, or
explicitly blocked in MathformerPhysicsLib evidence.

## Contract

For each object candidate:

1. Search `libraries/MathformerPhysicsLib/Lean`, `MathformerPhysicsLib`, and relevant
   Lean modules for reusable declarations.
2. If reusable support exists, emit an import/use recommendation.
3. If not, emit a minimal candidate module plan and Lean skeleton text under a
   stable `libraries/MathformerPhysicsLib/Lean/ObjectWorkbench/...` target path.
4. Mark each item as `mathformer_reused`, `candidate_required`, or `blocked`.
5. Name promotion gates: registry refresh, promotion check, compile check, and
   the affected Lean physics critics.

Prefer `scripts/build_mathformerphysicslib_object_workbench.py`.
