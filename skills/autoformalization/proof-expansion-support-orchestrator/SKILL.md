---
name: proof-expansion-support-orchestrator
description: Coordinate proof expansion support before autoformalization by running difficulty estimation, deciding which proof segments require web research, invoking web-backed research packets, and handing verified expansion notes to the LaTeX prerequisite expander. Use before latex-prerequisite-expander when proof expansion risk must be controlled.
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

# Proof Expansion Support Orchestrator

## Purpose

Use this skill as the pre-expansion coordinator. It decides whether proof expansion can
proceed locally or needs web-supported evidence first.

Hooks:
- `preformalization.expansion_support`
- `preformalization.expansion_difficulty`
- `preformalization.expansion_web_support`

## Workflow

1. Run `proof-expansion-difficulty-estimator` on the proof text.
2. For segments marked `hard` or `research`, or any segment with `web_search_recommended: true`, invoke `proof-expansion-web-researcher`.
3. Build an expansion-support packet containing segment scores, source-backed facts, hypotheses to preserve, and unresolved uncertainties.
4. Pass that packet to `latex-prerequisite-expander`.
5. If web search is unavailable or forbidden, mark hard/research segments as unresolved rather than pretending the expansion is complete.

## References

- Read `references/support_loop.md` for hook order and handoff format.
