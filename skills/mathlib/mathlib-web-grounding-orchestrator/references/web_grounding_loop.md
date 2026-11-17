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

# Mathlib Web Grounding Loop

## Input Packet

- `local_gap`: concept, failed declaration, missing import, or ambiguous API decision
- `local_evidence`: concept-map rows, hierarchy rows, verifier errors, coverage gaps
- `search_plan`: output from `mathlib-web-search-strategist`

## Web Evidence Packet

- `sources`: source id, URL, source kind, date accessed
- `claims`: claim type, claim text, source id or URL, search query, evidence summary
- `local_verification`: `#check`, import-context, or compile result when available
- `uncertainties`: what remains unresolved and what must not be assumed

## Stop Conditions

Stop the web loop when one of the following holds:

- every unresolved API concept has an official source and local Lean verification,
- web search finds only retrieval-aid or non-official evidence,
- the source suggests a candidate but local Lean verification fails,
- the round cap is reached and gaps are explicitly recorded.

## Downstream Use

- Grounded claims may be used in API planning, import planning, and drafting hints.
- Candidate-only claims may be used as search hints for another local verification pass.
- Blocked claims must not influence theorem statements, imports, or Mathformerlib acceptance.
