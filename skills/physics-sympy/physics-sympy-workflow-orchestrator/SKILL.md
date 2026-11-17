---
name: physics-sympy-workflow-orchestrator
description: Plan a controlled equational SymPy physics autoformalization workflow. Use when a physics derivation should run through the enriched SymPy pipeline with informal expansion, quantity surfaces, installed-library grounding, assumption context, equation graphs, critics, final reviewers, localized monotonic refinement, and optional FormalPhysics formal-answer reflection.
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

# Physics SymPy Workflow Orchestrator

Use this skill before drafting or refining an enriched SymPy physics artifact.
It converts the Lean-inspired physics pipeline into an equational workflow
plan, preserving SymPy's role as an executable algebra system rather than a
theorem prover.

## Contract

Produce `physics_sympy_workflow_plan` with:

1. Required preformalization hooks.
2. Required SymPy equation-surface, assumption, execution, critic, final review,
   refinement, and consistency gates.
3. Required `physics_sympy_library_grounding_packet` with `grounding_level =
   high` for complete status.
4. Protected evidence for monotonic refinement.
5. A clear policy that FormalPhysics `formal_answer` comparison is optional,
   post-hoc, and inspiration-only.
6. A required source-commentary contract: the generated artifact must preserve
   the original informal statement, full informal proof/commentary, and a
   `SymPy alignment` from each informal step to the executable trace surface.
7. RFDE trajectory integration through `critique.reference_free_monitor` and
   `evaluation.rfde_report`.
8. Cost-accounting fields `duration_ms` and `agent_usage` for each loop phase.

Prefer `scripts/build_physics_sympy_workflow_plan.py` for deterministic plans.

## Planning Rules

- Reuse existing mathematical SymPy and physics preformalization skills before
  adding backend-specific logic.
- Keep the target style `sympy_physics_derivation_trace`.
- Treat Lean-style typing as metadata and validators over equations.
- Treat Lean proof obligations as executable equation certificates.
- Prefer installed SymPy/dependency APIs for scalar algebra, calculus, units,
  vector analysis, mechanics, matrices, quantum operators, and numeric checks
  before accepting local placeholders.
- Route failures to localized repair surfaces instead of broad rewrites.
- Treat missing or stale informal-to-SymPy alignment as a semantic-preservation
  failure, not a documentation nit.
