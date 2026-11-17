---
name: physics-lean-recursive-repair-loop-controller
description: Control recursive Lean physics pathology repair iterations from an exhaustive expansion map. Use when Codex must decide whether to recurse, complete, or block based on outstanding pathology/object/library/generative obligations, iteration signatures, max-iteration limits, deterministic rerun gates, and repeated-state detection.
---

<!--
File Documentation

Motivation:
  Prevent Lean physics pathology repair from becoming an unbounded hidden loop.

Intent:
  Tell agents how to turn an expansion map into a controlled recursion decision
  with explicit next actions and stopping criteria.

Function:
  Contains skill instructions and a deterministic script for producing
  `physics_lean_recursive_repair_control_plan` artifacts.

Maintenance Notes:
  Keep status semantics synchronized with
  `physics-lean-repair-expansion-cartographer`.
-->

# Physics Lean Recursive Repair Loop Controller

Use after `physics-lean-repair-expansion-cartographer`.

Decide exactly one of:

- `complete`: no outstanding expansion nodes remain;
- `recurse`: outstanding nodes remain, the iteration signature has changed, and the max-iteration limit has not been reached;
- `blocked`: the signature repeated, the iteration limit was reached, the expansion map is not exhaustive, or the map reports a hard blocker.

Every recursive step must preserve these invariants:

- MathformerPhysicsLib-first object work before target theorem edits;
- generative repair remains advisory until deterministic gates rerun;
- every new object, assumption, generated support, and target edit must re-enter the expansion map;
- no loop iteration may be accepted without a fresh drift monitor, object detection, workbench plan, pathology loop, generative repair plan, expansion map, recursive controller plan, and consistency report.

Prefer `scripts/control_recursive_repair_loop.py`.
