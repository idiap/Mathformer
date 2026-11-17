---
name: physics-sympy-equation-surface-builder
description: Build an equational physics surface for SymPy derivations. Use before SymPy drafting or review when quantities, dimensions, units, equation graph nodes, law links, installed SymPy/dependency grounding, vector or field projections, and target/source/generated equation roles must be explicit.
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

# Physics SymPy Equation Surface Builder

Use this skill after source extraction, symbol tables, dimension/unit modeling,
equation parsing, frame modeling, law grounding, and SymPy library grounding. It
builds the equational analogue of the Lean physics type surface.

## Contract

Produce `physics_sympy_equation_surface_packet` with:

- `QUANTITY_SURFACE`
- `EQUATION_GRAPH`
- `PROJECTION_BRIDGES`
- `LAW_TABLE`
- `LIBRARY_GROUNDING`
- blockers and warnings for missing source support

Prefer `scripts/build_physics_sympy_equation_surface.py` for deterministic
first-pass packets.

## Requirements

- Distinguish scalar, vector, field, operator, parameter, and generated-support
  symbols.
- Attach dimensions and units when available.
- Classify each equation as `source`, `generated_bridge`, `target`, `derived`,
  or `blocked`.
- Add projection bridges whenever vector, tensor, field, or operator claims are
  reduced to scalar component equations.
- Attach `physics_sympy_library_grounding_packet`; complete status requires
  `grounding_level = high`.
- Reject derived equations that are actually target assumptions.
