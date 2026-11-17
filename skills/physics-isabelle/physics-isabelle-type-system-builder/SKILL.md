---
name: physics-isabelle-type-system-builder
description: Build Isabelle/HOL-facing physics type packets for quantities, dimensions, units, fields, vectors, frames, laws, and generated-support projection boundaries.
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

# Physics Isabelle Type System Builder

Use after physics source, symbol, dimension, unit, frame, law, and informal
grounding-expansion packets exist and before drafting an Isabelle/HOL theory.

The packet is the Isabelle counterpart of the Lean physics type packet. It must
not change Lean packets or Lean theorem statements.

The builder should maximize reuse of installed Isabelle/HOL libraries before
introducing local physics scaffolds:

- prefer `Complex_Main` and `HOL-Analysis.Analysis` surfaces such as `real`,
  `complex`, `'a::euclidean_space`, `real ^ 'n`, `inner`, `norm`,
  `continuous_on`, `DERIV`, `has_derivative`, `has_vector_derivative`,
  `bounded_linear`, and `linear`;
- represent context with locale/context assumptions carrying typed propositions,
  not only string or bool labels;
- allow raw scalar equations only as explicit projections from native carriers
  and pair them with a compact reusable algebraic core theorem;
- emit background formalization requirements for definitions, physical laws,
  calculus facts, unit/dimension bridges, and algebraic cores that must be
  resolved before complete status.

Prefer `scripts/build_physics_isabelle_type_system.py`.
