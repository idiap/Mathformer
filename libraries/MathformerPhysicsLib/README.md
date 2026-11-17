<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Preserve generated and reviewed formal-physics artifacts with enough context to audit their provenance.

Intent:
  Connect benchmark statements to Lean, Isabelle, and SymPy representations without hiding assumptions.

Function:
  Stores formal artifacts, summaries, and grounding reports consumed by physics backend tests and documentation.

Maintenance Notes:
  Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.
-->

# Mathformer Physics Library

This folder collects the current Mathformer physics autoformalizations in one
backend-separated library tree.

## Layout

- `Lean/Foundations.lean`: accepted Lean foundations index.
- `Lean/Foundations/*.lean`: Mathlib-first reusable physics foundation
  surfaces for carriers, fields, operators, vector calculus, units, laws, and
  contexts.
- `Lean/<case>/MathformerPhysics.lean`: Lean physics candidate.
- `Lean/<case>/consistency_report.json`: Lean consistency report.
- `backends/isabelle/Isabelle/<case>/MathformerPhysics.thy`: Isabelle/HOL physics candidate.
- `backends/isabelle/Isabelle/<case>/ROOT`: Isabelle session file for local builds.
- `backends/isabelle/Isabelle/<case>/consistency_report.json`: Isabelle consistency report.
- `SymPy/<case>/MathformerPhysics.py`: executable SymPy physics derivation.
- `SymPy/<case>/summary.json`: SymPy run summary, including installed-library
  grounding roles and `grounding_level`.

## Current Coverage

- Lean: `formalphysics_0000`, `formalphysics_0020`, `formalphysics_0026`,
  `formalphysics_0054`, `formalphysics_0059`, `formalphysics_0066`,
  `formalphysics_0119`, `formalphysics_0172`, `formalphysics_0176`,
  `formalphysics_0191`.
- Isabelle/HOL: `formalphysics_0000`, `formalphysics_0020`.
- SymPy: `formalphysics_0000`, `formalphysics_0020`,
  `formalphysics_0026`, `formalphysics_0054`, `formalphysics_0059`,
  `formalphysics_0066`, `formalphysics_0119`, `formalphysics_0172`,
  `formalphysics_0176`, `formalphysics_0191`.

All Lean top-10 entries are high-grounded complete candidates: their theorem
surfaces use Mathlib-native carriers/operators where appropriate, carry
background dependency evidence, and invoke compact reusable algebraic cores
from physics-rich wrappers.

The Isabelle entries for `formalphysics_0000` and `formalphysics_0020` are
equational scalar/component projections of the source physics derivations.

All SymPy top-10 entries are high-grounded complete executable candidates:
they validate an equational scalar/projection trace, preserve the original
informal commentary, line-level SymPy alignment, and full printed derivation
trace, carry quantity/law/assumption/projection metadata, and pass execution,
unit, step, numeric, semantic, grounding, and final-equation review gates.

SymPy complete status now requires high installed-library grounding: scalar
algebra, calculus, units/dimensions, vector or mechanics surfaces when needed,
and numeric validation must be represented by concrete installed SymPy or
dependency APIs rather than by local placeholders alone.

To rebuild an Isabelle case locally, run `isabelle build -D
libraries/MathformerPhysicsLib/backends/isabelle/Isabelle/<case>`.

To refresh the Lean grounding audit and consistency statuses, run
`python3 scripts/audit_mathformer_physics_lean_grounding.py --update-consistency`.

To run the controlled foundations workflow over the priority-1 object backlog,
run `python3 scripts/mathformer.py run physics-lean:foundation-formalization-loop --json`.

To regenerate the SymPy top-10 cases, run
`uv run python scripts/generate_formalphysics_top10_sympy.py --promote-lib`.

<!-- BEGIN GENERATED PHYSICS COVERAGE -->
## Generated Artifact Coverage

| Backend | Promoted | Candidate | Total |
| --- | ---: | ---: | ---: |
| Lean | 10 | 25 | 35 |
| Isabelle | 2 | 8 | 10 |
| SymPy | 10 | 1 | 11 |

Every tracked case is registered in `MANIFEST.json`. Candidate cases are
compiled or executed by backend validation but are not exported by the Lean
public root or represented as cross-backend promotion evidence.
<!-- END GENERATED PHYSICS COVERAGE -->
