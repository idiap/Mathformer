---
name: lean-line-annotation
description: Produce stable line-by-line annotations for Lean4 source files and validate generated Lean source-comment hygiene and semantic alignment coverage. Use when generated Lean artifacts need an explanatory Markdown table, source-aware Natural language/LaTeX declaration comments, or rejection of legacy per-line NL/LaTeX comments and syntax-only comments.
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

# Lean Line Annotation

## Purpose

Use this skill for two line-level contracts:

- explanatory annotations of existing Lean source, where every input line appears once
  in the output table;
- generated Lean source-comment validation, where comments should be compact,
  source-aligned, semantically informative, and absent from purely syntactic lines.

Shared runtime owner:
- `../autoformalization-agentc/scripts/agentc.py`
- class: `LeanLineAnnotationAgent`
- validator: `scripts/validate_lean_line_comments.py`

## Workflow

1. Read the Lean file exactly as-is.
2. Emit one row for every input line, including blank lines.
3. Preserve exact 1-based line numbers.
4. Keep annotations concise and technically precise.
5. Do not rewrite, reorder, repair, or omit code.
6. For generated Lean artifacts, preserve original-source natural-language and
   LaTeX equivalents in module/declaration comments when the source provides them.
7. When a line translation packet is available, preserve compact `Source anchors:
   src_L####` references in the declaration comments for source-backed Lean.
8. For generated support declarations that do not come directly from the source,
   add concise `Generated note` / `Generated equivalent` comments explaining the
   mathematical role and intended formula.
9. Run the source-comment hygiene validator before accepting the artifact. Blank
   lines are allowed; legacy `NL/LaTeX:` line markers, syntax-only comments, and
   missing semantic declaration comments are failures when semantic coverage is
   required.
10. Treat noisy or underspecified generated comments as an artifact-quality failure, not as a
   cosmetic issue.

## References

- Read `references/prompts.md` for the exact annotation prompt, embedded-comment
  prompt, and table contract.
