---
name: proof-expansion-web-researcher
description: Perform source-backed web research for proof segments whose expansion difficulty requires outside support. Use after proof-expansion-difficulty-estimator flags hard or research-level segments, especially when named theorems, citations, definitions, hypotheses, or proof techniques must be verified before LaTeX expansion.
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

# Proof Expansion Web Researcher

## Purpose

Use this skill to support difficult proof expansion with web evidence. It should produce
a compact research packet, not a full literature review.

Hook:
- `preformalization.expansion_web_support`

## Workflow

1. Start from segments flagged by `proof-expansion-difficulty-estimator`.
2. Search only for the exact theorem, definition, hypothesis, citation, or proof technique needed for expansion.
3. Prefer primary sources: papers, books/preprints, official project documentation, theorem statements, or library docs.
4. Record source URL, source type, and what was verified.
5. Summarize only what is needed to expand the proof part safely.
6. Hand the research packet to `proof-expansion-support-orchestrator` and `latex-prerequisite-expander`.

## Web Use

When this skill triggers for an actual proof segment, use web search unless the user
explicitly forbids it. Cite sources in the final packet.

## References

- Read `references/web_research.md` for query strategy and packet format.
