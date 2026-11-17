---
name: physics-symbol-table-builder
description: Build a typed quantity and symbol table for physics SymPy derivations, separating scalars, vectors, functions, constants, units, dimensions, generated support symbols, and reused notation.
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

# Physics Symbol Table Builder

Use after physics source extraction. It must report ambiguous bindings,
incompatible symbol reuse, generated support variables, and scalar/vector or
function/parameter mismatches.

The symbol table distinguishes `scalar_variable`, `vector_quantity`,
`function_of_time`, `parameter_constant`, `generated_dummy_variable`,
`coordinate_axis_or_basis`, and `unit_or_dimension`. Stable IDs must be based
on semantic meaning, dimension, and unit rather than display spelling alone.
Generated dummy variables and coordinate helpers must be marked
`source_backing=generated_support`.

Binding diagnostics must cover incompatible reuse, missing binders, ambiguous
constants such as `k`, `c`, `R`, `T`, and `E`, overloaded notation such as `v`,
mixed scalar/vector use, implicit functions of time, and generated symbols that
are accidentally source-backed.
