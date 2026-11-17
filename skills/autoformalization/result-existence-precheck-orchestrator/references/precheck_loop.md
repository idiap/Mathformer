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

# Result Existence Precheck Loop

## Packet Shape

Return a compact packet with:

- `skill`: `result-existence-precheck-orchestrator`
- `verdict`: `reuse_existing`, `verify_candidates`, `run_web_search`, or `proceed`
- `evidence`: local candidates, web sources searched, and verification status
- `gate`: whether `draft.initial` is allowed
- `regression`: how this avoids duplicating successful existing formalizations

## Stop Conditions

- Stop with `reuse_existing` when an exact/near-exact mathlib or MathformerLib declaration
  is found.
- Stop with `verify_candidates` when overlap is strong but not yet equivalent.
- Stop with `run_web_search` when local search is inconclusive and web confirmation has
  not been performed.
- Stop with `proceed` only after local search plus required official-source web search has
  found no duplicate.

## Web Search Evidence

For actual browsing, record:

- query string,
- source URL,
- whether the source is official docs, official source, or retrieval aid,
- candidate declaration/module,
- local Lean verification handoff status.
