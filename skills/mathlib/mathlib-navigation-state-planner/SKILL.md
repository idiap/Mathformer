---
name: mathlib-navigation-state-planner
description: Plan bounded Mathlib navigation as an auditable state process with module frontiers, declaration candidates, neighborhood evidence, import-cost scoring, theorem-shape hints, gap ledger entries, and monotonic regression checks. Use after term annotation and before verified Mathlib hints are handed to Lean drafting.
---


# Mathlib Navigation State Planner

Use this skill after term expansion has produced probable annotations.

Run:

```bash
python skills/mathlib/mathlib-navigation-state-planner/scripts/plan_mathlib_navigation_state.py \
  --text "A compact set has a finite subcover." --json
```

Self-test:

```bash
python skills/mathlib/mathlib-navigation-state-planner/scripts/plan_mathlib_navigation_state.py --self-test --json
```

Navigation state records the current focus, candidate module frontier, allowed
next operation, budgets, candidate declarations, import-cost estimates, gap
ledger entries, and monotonic baseline checks.
