---
name: physics-lean-generative-repair-orchestrator
description: Build guarded Codex-exec generative repair plans for Lean physics pathologies after deterministic object detection and MathformerPhysicsLib workbench planning, requiring library-first proposed edits, explicit blockers, and deterministic rerun gates before target theorem changes are accepted.
---

<!--
File Documentation

Motivation:
  Make generative repair available without weakening the deterministic,
  library-first pathology repair contract.

Intent:
  Tell agents how to ask independent Codex runs for repair proposals while
  preserving MathformerPhysicsLib-first object work and final acceptance gates.

Function:
  Contains skill instructions, prompts, references, and scripts used by
  Codex-style workflows.

Maintenance Notes:
  Keep generated prompts aligned with the deterministic pathology repair loop
  and never allow generative output to bypass promotion, realness, compile, or
  consistency gates.
-->

# Physics Lean Generative Repair Orchestrator

Use after:

1. `physics-lean-drift-pathology-monitor`
2. `physics-math-object-detector`
3. `mathformerphysicslib-object-workbench`
4. pathology-specific repair planners
5. `physics-lean-pathology-repair-orchestrator`

This skill does not directly repair a theorem. It builds Codex-exec prompts for
independent generative repair proposals. Proposed edits must remain library
first:

- repair missing objects in `MathformerPhysicsLib` before target theorem edits;
- preserve source anchors and target conclusion;
- avoid target-shaped hypotheses, new axioms, `sorry`, `admit`, and vacuity;
- label every new side condition;
- rerun deterministic monitors, critics, compile checks, registry, promotion,
  and consistency gates.

Prefer `scripts/build_physics_lean_generative_repair_plan.py`.
