---
name: physics-sympy-goal-sample-autoformalizer
description: Run one FormalPhysics SymPy sample through a recursive, goal-oriented physics autoformalization loop. Use when Codex is asked to plan, inspect, finish, repair, or assess a specific libraries/MathformerPhysicsLib/SymPy/formalphysics_####/MathformerPhysics.py case one sample at a time, especially when the workflow must stay source-only and recurse through SymPy physics support surfaces before editing the target artifact.
---



<!--
File Documentation

Motivation:
  Keep FormalPhysics SymPy autoformalization goal loops one-sample scoped,
  recursive, source-only, and explicit.

Intent:
  Tell agents how to lock one SymPy physics case, inspect current evidence,
  and route missing support through SymPy-specific recursive repair surfaces.

Function:
  Contains skill instructions and scripts used to plan one-case SymPy physics
  recursive autoformalization.

Maintenance Notes:
  Keep this synchronized with physics-sympy-repair-expansion-cartographer,
  physics-sympy-recursive-repair-loop-controller, and tests/physics_sympy/.
-->

# Physics SymPy Goal Sample Autoformalizer

Use this as the outer meta-skill for a single `formalphysics_####` SymPy
sample. Do not batch multiple samples under one goal. Finish, block, or
explicitly hand off the current sample before moving to another one.

## One-Sample Contract

1. Normalize the requested case to one `formalphysics_####` id and one
   `libraries/MathformerPhysicsLib/SymPy/formalphysics_####/MathformerPhysics.py` file.
2. State the goal as: this one sample reaches
   `complete_sympy_physics_derivation`, or the loop emits an explicit blocker
   with evidence.
3. Keep first-pass new-example work source-only. Do not inspect or use dataset
   `formal_answer` before a source-derived candidate, blocker report, or final
   consistency report already exists.
4. Inspect the artifact for:
   - source task text, source anchors, informal commentary, and SymPy alignment;
   - `CLAIM`, `QUANTITY_TABLE`, `ASSUMPTIONS`, `DERIVATION_STEPS`,
     `EQUATION_SURFACE`, `QUANTITY_SURFACE`, `EQUATION_GRAPH`, `LAW_TABLE`,
     `PROJECTION_BRIDGES`, `EQUIVALENCE_CERTIFICATES`,
     `SYMPY_LIBRARY_GROUNDING`, and `ASSUMPTION_CONTEXT`;
   - validators for dimensions, derivation steps, numeric samples, symbolic
     validation, equation semantics, assumptions, projection bridges,
     target non-leakage, law usage, library grounding, final reviews, and
     `run_all`.
5. If evidence is missing, route through the SymPy recursive surfaces:
   - `physics-sympy-repair-expansion-cartographer`
   - `physics-sympy-recursive-repair-loop-controller`
   - existing SymPy review/refinement, grounding, equation-surface,
     assumption-context, unit/dimension, numeric, and final-review skills.
6. Complete status requires source preservation, executable trace evidence,
   high installed-library grounding, unit/dimension checks, step checks,
   numeric checks, final reviews, target non-leakage, and no open recursive
   frontier.

## Planner

Prefer:

```bash
.venv/bin/python skills/physics-sympy/physics-sympy-goal-sample-autoformalizer/scripts/plan_goal_sample_sympy_autoformalization.py \
  --case formalphysics_0000 --json
```

Use `--run-gates` when current executable evidence is needed:

```bash
.venv/bin/python skills/physics-sympy/physics-sympy-goal-sample-autoformalizer/scripts/plan_goal_sample_sympy_autoformalization.py \
  --case formalphysics_0000 --run-gates --json
```

The script emits `physics_sympy_goal_sample_autoformalization_plan` with the
sample lock, current evidence, open markers, design-guard findings, recursive
workflow, commands, controller conditions, and next action.

## SymPy-Only Boundary

This skill must not call Lean planners, Lean repair controllers, Lean
thoroughness gates, or MathformerPhysicsLib Lean files. Cross-backend
comparison is a later review task and is not part of the one-sample SymPy
recursive loop.
