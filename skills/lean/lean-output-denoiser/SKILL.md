---
name: lean-output-denoiser
description: Clean noisy model text into the best fenced Lean4 or Isabelle/HOL formal code without rewriting or improving it, while preserving meaningful source-alignment comments and removing surrounding prose. Use when an autoformalization response contains prose, repeated candidates, proofs that should be removed, malformed surrounding text, or source-comment hygiene risk.
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

# Lean Output Denoiser

## Purpose

Use this skill only for extraction and cleanup. It must not repair, optimize, or reinterpret
the formalization; that belongs to `lean-formal-refinement`.

Shared runtime owner:
- `../autoformalization-agentc/scripts/agentc.py`
- class: `DenoisingAgent`

## Workflow

1. Select the best formal-code candidate from noisy model output.
2. Remove explanatory prose outside the formal code, repeated candidates, and proof bodies.
3. Preserve the formal code itself rather than rewriting it.
4. For Lean4, preserve meaningful module/declaration comments that explain source alignment.
5. Do not preserve legacy repeated `NL/LaTeX:` comments merely because they exist; convert useful source content into module/declaration comments with `Original source (NL)`, `Original source (LaTeX)`, or `Generated note` labels, then route source-comment style to `lean-line-annotation` guard or regeneration/refinement.
6. Return only fenced formal code with the `%%%%%%%%%%` contract.

## References

- Read `references/prompts.md` for the exact denoising prompt.
