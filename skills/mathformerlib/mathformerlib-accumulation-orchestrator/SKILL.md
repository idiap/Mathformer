---
name: mathformerlib-accumulation-orchestrator
description: Coordinate accumulation of generated Lean formalizations into Mathformerlib, the curated parallel mathlib-style library for Mathformer outputs. Use when deciding where a formalization should live, promoting draft/candidate artifacts into MathformerLib modules, updating the registry, or preserving draft versus accepted boundaries.
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

# Mathformerlib Accumulation Orchestrator

## Purpose

Use this skill to treat Mathformerlib as a parallel, curated mathlib-style
library of reusable formalizations. Draft autoformalizations may remain in
`backends/lean/Mathformer/` or artifacts, but accepted reusable formalizations belong under
`libraries/MathformerLib/` only after promotion gates pass.

Cooperating skills:
- `mathformerlib-registry-manager`
- `mathformerlib-promotion-gate`
- `autoformalization-result-realness-verifier`
- `lean-compile-checker`
- `lean-import-context-verifier`

Hook: `mathformerlib.accumulate`

## Workflow

1. Classify the source artifact as `draft`, `candidate`, or `accepted`.
2. Run `mathformerlib-promotion-gate` before moving or importing a candidate
   into `libraries/MathformerLib/`.
3. Keep draft/scaffold outputs registered, but do not add them to accepted
   Mathformerlib root imports.
4. Put promoted modules under domain-specific paths such as
   `libraries/MathformerLib/Topology/Compactness.lean`.
5. Rebuild the registry with `mathformerlib-registry-manager`.
6. Compile the affected module or `lake build MathformerLib`.

## Acceptance Rules

Accepted Mathformerlib entries must:
- compile under the intended imports;
- pass the realness gate as final artifacts;
- contain no `sorry`, `admit`, target `axiom`, mock/stub marker, or scaffold-only
  completion claim;
- record source/provenance metadata in the registry;
- avoid broad imports unless explicitly justified.

Draft entries may be tracked in the registry with gaps, but they are not a
library success.
