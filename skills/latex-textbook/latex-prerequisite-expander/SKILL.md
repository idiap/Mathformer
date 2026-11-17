---
name: latex-prerequisite-expander
description: Expand informal mathematical statements into equivalent LaTeX-ready statements with explicit definitions, theorem prerequisites, and implicit assumptions before formalization. Use when preparing a natural-language or LaTeX math statement for Lean/Isabelle autoformalization without generating formal code.
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

# LaTeX Prerequisite Expander

## Purpose

Use this skill for the pre-formalization expansion step only. It makes definitions,
theorem prerequisites, domain assumptions, and implicit mathematical constraints explicit
while preserving the original statement's meaning.

Shared runtime owner:
- `../autoformalization-agentc/scripts/agentc.py`
- class: `LatexExpansionAgent`

## Workflow

1. Keep the output mathematically equivalent to the source statement.
2. Expand prerequisite definitions and theorem assumptions in LaTeX-style mathematical language.
3. Do not emit Lean, Isabelle, or other formal code.
4. Preserve the `%%%%%%%%%%` fence contract from `references/prompts.md` when prompt parity matters.
5. Hand the expanded statement to `latex-expansion-review-orchestrator` before `lean-autoformalization-drafter` or the full workflow orchestrator.

## References

- Read `references/prompts.md` when exact prompt text or placeholders are needed.
