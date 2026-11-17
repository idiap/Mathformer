---
name: textbook-theory-tex-organizer
description: Organize extracted textbook theorem-like units into thematically coherent TeX bundle files by chapter or section while preserving original LaTeX source, provenance comments, labels, and proof adjacency.
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

# Textbook Theory TeX Organizer

Use this skill after `latex-archive-theory-extractor` has emitted `theory_units.json`.
It groups source-preserved definitions, lemmas, theorems, corollaries, propositions, and
proofs into reviewable TeX fragments for batch autoformalization.

## Workflow

1. Run `scripts/organize_theory_tex.py` with `--theory-units-json`.
2. Use `--group-by section` for textbook-scale archives; use `--group-by chapter` for
   smaller sources.
3. Pass the emitted `organized_manifest.json` to
   `textbook-autoformalization-batch-orchestrator`.

## Command

```bash
python3 skills/latex-textbook/textbook-theory-tex-organizer/scripts/organize_theory_tex.py \
  --theory-units-json artifacts/textbook_theory/example/theory_units.json \
  --output-dir artifacts/textbook_theory/example/organized \
  --group-by section \
  --json
```

## Contract

- Do not rewrite mathematical content; bundle the original LaTeX blocks.
- Keep source comments concise: file, lines, unit id, kind, label, and paired proof ids.
- Split very large groups with `--max-units-per-file` instead of making unwieldy files.
- Do not claim Lean autoformalization. This skill creates source bundles only.
