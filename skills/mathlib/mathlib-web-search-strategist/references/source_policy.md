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

# Mathlib Web Source Policy

## Source Priority

Use web search only to complement local mathlib search.

1. Official mathlib docs: `leanprover-community.github.io/mathlib4_docs`
2. Official mathlib source: `github.com/leanprover-community/mathlib4`
3. Official Lean/mathlib documentation for API conventions
4. Retrieval aids such as Loogle or LeanSearch, only to discover candidates
5. General mathematical sources, only for informal terminology or theorem context

## Acceptance Rules

- A declaration, module, import, notation, instance, or theorem-shape claim needs an
  official mathlib docs/source URL.
- Retrieval aids may suggest candidates, but the final packet must corroborate them
  with official docs/source and local Lean checks.
- If a packet records a retrieval-aid discovery URL, it must also include an official
  mathlib docs/source corroboration URL before the claim can become grounded.
- General web pages must not be used as direct evidence for mathlib API availability.
- Every accepted API claim must hand off to `#check` or import-context verification.
- Preserve uncertainty: if a web hit suggests a possible declaration but local Lean
  verification has not run, mark it as candidate-only.

## Query Patterns

- Exact declaration: `site:leanprover-community.github.io/mathlib4_docs "Declaration.Name"`
- Retrieval-aid follow-up: search the candidate name in official docs/source, then
  locally run `#check Candidate.Name`.
- Concept plus module family: `site:leanprover-community.github.io/mathlib4_docs "compact" "Mathlib.Topology"`
- Source fallback: `repo:leanprover-community/mathlib4 "Declaration.Name"`
- Notation search: `site:leanprover-community.github.io/mathlib4_docs "notation" "Finset"`
- Import search: `site:leanprover-community.github.io/mathlib4_docs "import Mathlib.Data.Finset.Basic"`
