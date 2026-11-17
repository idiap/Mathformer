---
name: result-existence-precheck-orchestrator
description: Coordinate the mandatory pre-autoformalization check that a target result is not already in mathlib or MathformerLib. Use before initial drafting for theorem-like results to combine local MathformerLib search, local mathlib search, official-source mathlib web search, evidence validation, and reuse-or-draft gate decisions.
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

# Result Existence Precheck Orchestrator

## Purpose

Use this skill immediately before a result is autoformalized. It answers:

> Is this theorem/result already in mathlib or MathformerLib, and should we reuse it
> instead of generating a new formalization?

Hook:
- `preformalization.result_existence_precheck`

## Ordered Loop

1. Extract the target statement, theorem title, expected names, and core concepts from the
   reviewed LaTeX expansion or original theorem statement.
2. Run `mathlib-result-existence-checker`.
3. If the checker returns `likely_existing`, stop drafting and prepare a reuse packet with
   declaration/import/source references.
4. If it returns `candidate_overlap`, verify the candidates locally and inspect whether the
   theorem shape is the same before deciding reuse vs. absence.
5. If it returns `needs_web_confirmation`, perform the planned web search:
   - official mathlib docs first,
   - official `leanprover-community/mathlib4` source second,
   - Loogle/LeanSearch only for candidate discovery.
6. Validate web-sourced claims with `mathlib-web-evidence-validator`.
7. Re-run or amend the checker with `--web-confirmed-absent` only after official-source
   search finds no duplicate.
8. Permit `draft.initial` only when the final gate says `proceed_to_autoformalization`.

## Gates

- Do not draft when an existing result is likely present.
- Do not treat local search absence as sufficient when web confirmation is required.
- Do not inject web-discovered declarations as facts until official-source corroboration
  and local Lean verification are complete.
- Prefer reuse of canonical mathlib declarations over Mathformer-side duplicates.

## Outputs

- `result_existence_report`
- `reuse_packet` when an existing declaration is found
- `official_source_absence_record` when web search confirms no duplicate
- `proceed_to_autoformalization` boolean

## References

- Read `references/precheck_loop.md` for the compact packet shape and stop conditions.
