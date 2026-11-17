---
name: physics-sympy-review-refinement-router
description: Convert failed SymPy physics final reviews into localized monotonic repair plans. Use when physics or mathematical SymPy final equation reviews fail and the next refinement must preserve already-correct source anchors, equation nodes, transformation certificates, unit coverage, assumptions, projections, installed-library grounding, numeric domains, and target shape.
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

# Physics SymPy Review Refinement Router

Use this skill when final equation reviewers fail. It does not rewrite the
artifact; it constrains the next repair.

## Contract

Produce `physics_sympy_review_refinement_plan`.

Prefer `scripts/plan_physics_sympy_review_refinement.py` for deterministic
repair plans.

## Repair Surfaces

- `quantity_surface`
- `assumption_context`
- `unit_dimension`
- `law_grounding`
- `sympy_library_grounding`
- `equation_parse`
- `projection_bridge`
- `transformation_step`
- `numeric_domain`
- `target_nonleakage`
- `trace_realness`

## Monotonicity Rule

A repair is allowed only when it is local to the reviewer finding, preserves
passing source anchors and certificates, does not weaken the target equation,
does not silently strengthen assumptions, does not reduce installed-library
grounding, and reruns all affected critics and reviewers.
