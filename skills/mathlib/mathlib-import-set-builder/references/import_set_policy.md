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

# Import Set Policy

## Default Policy

- Prefer explicit mathlib modules over `import Mathlib`.
- Keep imports justified by expected declarations, verified candidates, or
  existing project dependencies.
- Preserve local project imports when generated code depends on local files.
- Treat duplicate imports as cleanup findings.
- Treat an empty import set as incomplete unless the target is intentionally
  pure Lean core code.

## Evidence Sources

- `gold_expected_imports` from fixture manifests.
- `relevant_modules`, `top_imports`, `module`, or `import` fields from concept
  mapping and hierarchy navigation.
- Verified declaration rows produced by `mathlib-candidate-verifier`.
- Existing generated Lean import blocks.

## Handoff

The import set is a plan. Before final use, run
`lean-import-context-verifier` with the planned imports and expected
declarations.
