---
name: physics-lean-physical-semantics-critic
description: Critique whether a Lean physics formalization preserves the physical meaning of the informal derivation, including quantities, vectors, fields, frames, regimes, laws, source anchors, and non-empty theorem substance. Use after Lean drafting or refinement, especially before claiming a physics artifact is complete.
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

# Physics Lean Physical Semantics Critic

Use this critic after a Lean physics draft compiles or nearly compiles. It asks
whether the Lean artifact still says the same physics, not merely whether it is
syntactically legal mathematics.

## Critic Contract

Check these surfaces:

1. Source quantities remain represented as typed quantities, vectors, fields,
   operators, or explicit scalar projections.
2. Coordinate frames, bases, sign conventions, and regimes are not silently
   erased.
3. Named or implied laws are represented as source-backed hypotheses,
   generated-support lemmas, or mathlib/MathformerLib facts.
4. The final claim is not introduced as an axiom, hypothesis, or vacuous target.
5. Raw scalar algebra is permitted only for dimensionless or projection-backed
   substeps.

Prefer `scripts/critique_physics_lean_semantics.py` for deterministic first-pass
screening.

## Generative Mode

This critic may use Codex exec through
`skill-test-program-orchestrator/scripts/run_content_skill_codex_exec_tests.py`.
In generative mode, ask an independent Codex run to propose adversarial
interpretations:

- What physical interpretation would make the Lean theorem true but the source
  derivation false?
- Which vector, frame, boundary, or regime information could have been lost?
- Can a smaller Lean statement be constructed that compiles while proving only
  empty scalar algebra?
- What source law is needed for each transformation, and where is it missing?

Treat generative findings as hypotheses until they are backed by source anchors,
Lean diagnostics, unit analysis, or deterministic critic reports.
