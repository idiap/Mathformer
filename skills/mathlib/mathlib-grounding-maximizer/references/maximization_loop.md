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

# Mathlib Grounding Maximization Loop

## Loop Order

1. **Import loop**: replace broad imports with verified narrow modules, then run Lean.
2. **Native API loop**: replace custom objects with mathlib-native declarations when available.
3. **Concept coverage loop**: verify every extracted concept or record an explicit gap.
4. **Web grounding loop**: use only official mathlib docs/source or corroborated retrieval aids, then return to local Lean verification.
5. **Scaffold and realness loop**: remove scaffold markers, placeholders, missing semantic comments, and unexecuted artifact claims.
6. **Monotonicity loop**: compare compatibility, reference-free confidence, broad imports, blockers, and source-anchor coverage against the accepted baseline.

## Acceptance Rules

- No broad `import Mathlib` remains unless the artifact is explicitly draft/blocked with a waiver.
- Every expected declaration used in prompts or proof terms checks under the intended import set.
- Compatibility score should reach the configured target, normally `100` for final artifacts.
- Realness must have no blocking findings for final artifacts.
- Reference-free confidence and hard-risk counts must not regress relative to the accepted baseline.
- If mathlib lacks a concept, keep exactly one explicit abstraction boundary and document the gap.

## Fix Priority

1. Hard Lean failures or target axioms.
2. Proof placeholders, scaffold markers, mocks, and false finality claims.
3. Broad imports and broad-only declarations.
4. Custom concepts duplicating verified mathlib APIs.
5. Missing source-aware declaration comments.
6. Thin wrappers and cosmetic import/doc cleanup.
