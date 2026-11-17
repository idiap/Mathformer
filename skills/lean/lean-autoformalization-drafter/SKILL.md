---
name: lean-autoformalization-drafter
description: Draft initial Lean4 or Isabelle/HOL formal code from informal or LaTeX mathematical statements using MASA-compatible autoformalization prompts. Use when creating the first formalization attempt, injecting dependency formalizations, mathlib alignment hints, or source-aware Natural language/LaTeX declaration and module comments.
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

# Lean Autoformalization Drafter

## Purpose

Use this skill for first-pass formal code generation. It owns the prompt contract for
`AutoformalizationAgent`, including formal-language selection, few-shot wrapping,
dependency context, mathlib alignment hints, and source-aware semantic comments.

Shared runtime owner:
- `../autoformalization-agentc/scripts/agentc.py`
- class: `AutoformalizationAgent`

## Workflow

1. Start from the original or `latex-prerequisite-expander` output.
2. Include previously formalized dependency statements when available.
3. Include verified mathlib hints from `mathlib-concept-candidate-mapper` and `mathlib-candidate-verifier` when targeting Lean4.
4. Include line-by-line source translation packets from `source-line-translation-packet-builder` when available. Treat their `src_L####` ids as literal reference points that must not be silently dropped.
5. Include core statement alignment annotations when preserving source theorem assumptions/conclusions.
6. For Lean4 output, use normal Lean formatting with blank lines between imports, namespaces, sections, and declarations.
7. Put source-aware comments at the module or declaration level. Preserve original-source natural-language and LaTeX equivalents when available; for source-backed declarations include a compact line such as `Source anchors: src_L0007-src_L0010`; for generated support declarations, add concise `Generated note` / `Generated equivalent` comments.
8. Do not repeat `NL/LaTeX:` on every line, and do not comment purely syntactic lines such as `import`, `open`, `namespace`, `section`, or `end` unless there is a non-obvious mathematical reason.
9. Emit only fenced formal code; leave proof bodies as `sorry` only when the current workflow explicitly permits a draft scaffold, and never present that artifact as complete.
10. Use `lean-line-annotation/scripts/validate_lean_line_comments.py --require-semantic-comments` and, when a line translation packet exists, `source-formalization-drift-guard/scripts/validate_source_formalization_alignment.py` to reject noisy legacy line-comment style, underspecified declaration comments, missing anchors, and orphan anchors before accepting the draft.
11. Use `lean-formal-refinement` for theorem-prover or semantic-feedback repair.
12. Use `autoformalization-result-realness-verifier` before any final-result claim; complete autoformalizations must not contain `sorry`, `admit`, target `axiom`s, mock/stub markers, legacy per-line `NL/LaTeX:` comments, missing semantic declaration comments, missing required source anchors, or scaffold-only claims.

## References

- Read `references/prompts.md` for exact system/user prompts, optional extensions, and few-shot format.
