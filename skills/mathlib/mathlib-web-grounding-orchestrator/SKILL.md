---
name: mathlib-web-grounding-orchestrator
description: Coordinate web-assisted mathlib grounding as a complement to local search. Use when local concept mapping, hierarchy navigation, candidate verification, or coverage review leaves unresolved mathlib concepts and the workflow needs official-source web search, evidence validation, and local Lean verification before drafting or refinement.
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

# Mathlib Web Grounding Orchestrator

## Purpose

Use this skill only after the local mathlib grounding loop has produced a gap, ambiguous
candidate, failed `#check`, missing import, or low-confidence coverage report.

Hook:
- `mathlib.web_grounding_loop`

## Ordered Loop

1. Confirm local search evidence exists:
   - concept map or coverage report,
   - hierarchy/declaration-neighborhood output when relevant,
   - verifier/import-context diagnostics for failed candidates.
2. Invoke `mathlib-web-search-strategist` to build a bounded search plan.
3. Browse the web using the plan. Prefer official docs/source; use retrieval aids only
   to discover candidate names.
4. Create a web evidence packet with sources, claims, queries, uncertainty notes, and
   local verification status.
5. Invoke `mathlib-web-evidence-validator`.
6. For every `needs_local_verification` API claim, run:
   - `mathlib-candidate-verifier` for declarations,
   - `lean-import-context-verifier` for imports/modules,
   - `mathlib-import-set-builder` for import plan updates.
7. Feed only grounded claims into drafting, refinement, import planning, or
   Mathformerlib promotion.

## Gates

- Do not run broad web research when local search already produced verified coverage.
- Do not present Loogle, LeanSearch, blogs, forum answers, or examples as final API evidence.
- Do not inject unverified web claims into Lean prompts as established facts.
- Preserve unresolved status when web evidence is inconclusive.

## References

- Read `references/web_grounding_loop.md` for packet fields and stop conditions.
