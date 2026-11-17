---
name: physics-sympy-repair-expansion-cartographer
description: Map the recursive repair frontier for one FormalPhysics SymPy physics derivation. Use after a SymPy goal-sample plan, final review, execution report, or design-guard finding identifies missing source anchors, quantities, units, dimensions, frames, regimes, equation nodes, law grounding, SymPy API grounding, projection bridges, transformation steps, numeric domains, target nonleakage, trace realness, or consumer reasoning-log evidence.
---



<!--
File Documentation

Motivation:
  Make SymPy physics repair recursion exhaustive and inspectable.

Intent:
  Convert goal-plan evidence and review findings into a stable expansion map
  before another SymPy repair iteration is allowed.

Function:
  Emits node coverage, outstanding obligations, next-frontier actions, rerun
  gates, and an iteration signature for one SymPy physics case.

Maintenance Notes:
  Keep terminal statuses synchronized with
  physics-sympy-recursive-repair-loop-controller.
-->

# Physics SymPy Repair Expansion Cartographer

Use this skill after the one-sample goal planner or final reviewers surface
open SymPy physics repair work. The output is an explicit map of what must be
repaired before the case can be complete.

## Contract

Produce `physics_sympy_repair_expansion_map` with:

1. One node per open support surface.
2. Evidence, owner skill, artifact path, blockers, and minimal repair surface
   for each node.
3. A stable `iteration_signature` for recursion control.
4. `next_frontier` actions ordered from source/commentary and support objects
   toward target non-leakage and final trace repair.
5. SymPy-only rerun gates.

Prefer:

```bash
.venv/bin/python skills/physics-sympy/physics-sympy-repair-expansion-cartographer/scripts/map_physics_sympy_repair_expansion.py \
  --goal-plan artifacts/physics_sympy/recursive_goal_runs/formalphysics_0000/current_evidence.json \
  --json
```

## Repair Surfaces

- `source_anchor`
- `quantity`
- `dimension`
- `unit`
- `frame`
- `regime`
- `equation_node`
- `law_grounding`
- `sympy_api_grounding`
- `projection_bridge`
- `transformation_step`
- `numeric_domain`
- `target_nonleakage`
- `trace_realness`
- `consumer_reasoning_log`

## Boundary

Do not route findings to Lean workflows. The cartographer may mention missing
physics support objects, but the repair surface must remain in SymPy artifact,
SymPy pipeline, or Physics SymPy skill space.
