---
name: physics-lean-repair-expansion-cartographer
description: Map the recursive Lean physics pathology repair expansion after drift monitoring, object detection, MathformerPhysicsLib workbench planning, deterministic repair planners, and generative repair planning. Use when Codex must prove the repair loop is exhaustive, enumerate all open pathology/object/library/generative/gate obligations, and produce a controlled next frontier before another iteration.
---

<!--
File Documentation

Motivation:
  Keep recursive Lean physics pathology repair explicit instead of letting
  missing objects, generated support, or target edits disappear into hidden work.

Intent:
  Tell agents how to build an exhaustive expansion map over every active
  pathology, detected mathematical object, workbench item, repair plan,
  generative proposal, and rerun gate.

Function:
  Contains skill instructions and a deterministic script for producing
  `physics_lean_repair_expansion_map` artifacts.

Maintenance Notes:
  Keep node kinds synchronized with the repair loop controller and pathology
  repair orchestrator.
-->

# Physics Lean Repair Expansion Cartographer

Use after the deterministic pathology repair loop and generative repair plan.

Produce an expansion map before any recursive iteration is allowed. The map must:

- enumerate every active pathology category from the monitor or repair loop;
- enumerate every detected physics mathematical object;
- attach one MathformerPhysicsLib workbench item to every object or record a missing-workbench blocker;
- attach one pathology-specific repair plan to every active pathology category or record a missing-repair blocker;
- include generative repair as advisory evidence when any active pathology remains;
- record rerun gates and a stable iteration signature.

Treat candidate workbench support as open work. Do not mark the expansion complete unless all pathologies are cleared or every remaining obligation is explicitly represented for the recursive controller.

Prefer `scripts/map_repair_expansion.py`.
