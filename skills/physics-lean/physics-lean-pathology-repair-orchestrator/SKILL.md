---
name: physics-lean-pathology-repair-orchestrator
description: Orchestrate the library-first recursive loop that fixes detected FormalScience Lean physics pathologies by detecting missing physics objects, working over them in MathformerPhysicsLib, running pathology-specific repair planners, invoking guarded generative repair, mapping exhaustive expansion obligations, and routing target theorem refinement only after support evidence exists.
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

# Physics Lean Pathology Repair Orchestrator

Use after the drift-pathology monitor has emitted findings. This skill owns the
repair loop:

1. detect the missing physics mathematical object;
2. search or draft MathformerPhysicsLib support;
3. run the relevant pathology repair planners;
4. keep target theorem edits blocked until object support is reused, promoted,
   or explicitly blocked;
5. hand high-risk or blocked repairs to guarded generative repair proposals;
6. map the recursive expansion frontier exhaustively;
7. run recursive loop control to decide recurse, complete, or block;
8. rerun the monitor and final physics consistency gates.

Prefer `scripts/orchestrate_pathology_repair.py`.
