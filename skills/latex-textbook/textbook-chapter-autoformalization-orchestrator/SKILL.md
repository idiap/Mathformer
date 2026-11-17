---
name: textbook-chapter-autoformalization-orchestrator
description: Extract a LaTeX book archive, select all mathematical objects chapter by chapter including proofs, build chapter-specific source bundles and autoformalization job queues, and optionally run exactly one chapter through the standard Mathformer gates at a time.
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

# Textbook Chapter Autoformalization Orchestrator

Use this skill when a book-scale LaTeX archive should be processed chapter by
chapter instead of as one global queue.

## Workflow

1. Run `scripts/orchestrate_textbook_chapters.py` on the archive or an existing
   `theory_units.json`.
2. Inspect `chapter_plan.json` for chapter order, unit counts, proof counts, and
   batch manifest paths.
3. Process one chapter at a time. Use `--run-chapter-index N` or
   `--run-chapter-id ID` only when the user wants execution, not just planning.
4. Keep proof jobs enabled unless the user explicitly asks for statement-only
   planning.

## Command

```bash
python3 skills/latex-textbook/textbook-chapter-autoformalization-orchestrator/scripts/orchestrate_textbook_chapters.py \
  --archive inputs/book.zip \
  --output-dir artifacts/textbook_chapters/book \
  --json
```

Execute one chapter slice:

```bash
python3 skills/latex-textbook/textbook-chapter-autoformalization-orchestrator/scripts/orchestrate_textbook_chapters.py \
  --theory-units-json artifacts/textbook_chapters/book/extraction/theory_units.json \
  --output-dir artifacts/textbook_chapters/book \
  --run-chapter-index 1 \
  --provider codex-cli \
  --max-jobs-per-chapter 1 \
  --json
```

## Contract

- Preserve every extracted object with source file, line span, chapter, section,
  labels, references, and original LaTeX.
- If an extracted PDF-to-LaTeX book does not use theorem environments, fall back
  to prose theorem detection for cues such as `Lemma`, `Theorem`, `Proof:`,
  `Definition`, `Corollary`, and named theorem paragraphs.
- Include proofs both as paired proof text on statement jobs and as explicit
  proof-obligation jobs.
- Do not flatten chapters into one execution queue unless explicitly requested.
- Do not mark generated Lean complete unless the standard execution, realness,
  mathlib grounding, and unified consistency gates pass.
- Standalone or unpaired proofs stay visible in chapter inventories; they are
  not silently discarded.
