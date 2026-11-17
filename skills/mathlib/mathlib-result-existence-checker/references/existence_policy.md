<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

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

# Result Existence Policy

## Blocking Semantics

- Exact or suffix matches against expected declaration names block drafting and route to
  reuse or inspection.
- Strong token overlap candidates block automatic drafting until a human or local Lean
  verification step rules them out as non-duplicates.
- A retrieval-aid hit from Loogle or LeanSearch is never enough to claim a result exists.
  It must be corroborated by official mathlib docs/source and then checked locally.
- A local miss is not a completed absence proof when official-source web search has not run.

## Required Search Surfaces

Use the surfaces in this order:

1. `MathformerLib` registry for locally accumulated reusable results.
2. Local mathlib concept/declaration search.
3. Official mathlib HTML documentation.
4. Official `leanprover-community/mathlib4` source.
5. Loogle or LeanSearch only as candidate discovery aids.

## Handoff Rules

- Existing mathlib result: prefer importing and reusing the canonical declaration.
- Existing MathformerLib result: import the accumulated module, or promote if still in
  candidate status.
- Ambiguous candidate: use `mathlib-candidate-verifier` and `lean-import-context-verifier`.
- Confirmed absence: record the web queries searched and pass `--web-confirmed-absent`
  before enabling first-pass drafting.
