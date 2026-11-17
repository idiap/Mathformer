---
name: physics-sympy-recursive-repair-loop-controller
description: Decide whether a FormalPhysics SymPy repair loop is complete, should recurse, or must block. Use after physics-sympy-repair-expansion-cartographer emits an expansion map for one SymPy physics case, especially when repeated blockers, iteration caps, open frontiers, or missing executable/source-preservation evidence must be handled explicitly.
---



<!--
File Documentation

Motivation:
  Keep recursive SymPy physics repair bounded, monotonic, and visible.

Intent:
  Decide whether an exhaustive SymPy expansion map may start another repair
  iteration, is complete, or must block for repeated state or limits.

Function:
  Emits a recursion control plan with decision, next actions, invariants,
  stopping criteria, and required SymPy-only gates.

Maintenance Notes:
  Keep accepted expansion statuses synchronized with the SymPy repair
  cartographer.
-->

# Physics SymPy Recursive Repair Loop Controller

Use this skill after a SymPy repair expansion map exists. The controller does
not edit artifacts; it decides whether another local repair iteration is
allowed.

## Contract

Produce `physics_sympy_recursive_repair_control_plan` with:

1. `decision`: `complete`, `recurse`, or `blocked`.
2. `next_actions` copied from the expansion frontier when recursion is allowed.
3. blockers for repeated signatures, non-exhaustive maps, explicit blocked
   expansion maps, or max-iteration limits.
4. SymPy-only recursion invariants and rerun gates.

Prefer:

```bash
.venv/bin/python skills/physics-sympy/physics-sympy-recursive-repair-loop-controller/scripts/control_physics_sympy_recursive_repair.py \
  --expansion-map artifacts/physics_sympy/recursive_goal_runs/formalphysics_0000/repair_expansion.json \
  --json
```

## Control Policy

- Complete only when the expansion map is exhaustive and no outstanding nodes
  remain.
- Recurse only when the map is exhaustive, the iteration signature is new, and
  at least one local SymPy repair frontier is open.
- Block on repeated signatures, max-iteration limits, non-exhaustive maps, or
  explicit blocked expansion status.
- Preserve source anchors, equation nodes, transformation certificates, unit
  coverage, assumptions, projection bridges, numeric domains, target shape, and
  installed-library grounding across repairs.

## Boundary

Do not call or require Lean repair controllers. This controller governs only
SymPy physics artifact and skill evidence.
