---
name: mathformer-library-docs-generator
description: Generate browsable Markdown and aligned HTML documentation for the Mathformer and MathformerLib Lean libraries, including indexes, rendered Lean code blocks, rendered LaTeX/source annotations, declaration inventories, source-to-formal alignment pages, and repository-friendly links. Use at the end of autoformalization or after library files change.
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

# Mathformer Library Docs Generator

## Purpose

Use this skill to publish Mathformer formalizations as repository-browsable
documentation. It is a final workflow step: run it only after Lean artifacts
have passed the intended compile, consistency, realness, and registry gates, or
when refreshing docs for existing library files.

Runtime:
- `scripts/generate_mathformer_library_docs.py`
- `scripts/generate_aligned_html_docs.py`
- hook: `library.documentation`
- hook: `library.aligned_html_documentation`

## Workflow

1. Select Lean roots to document. Defaults are `MathformerLib`, `libraries/MathformerLib.lean`,
   and `Mathformer`.
2. Prefer a fresh Mathformerlib registry when available, but never rely on the
   registry as a substitute for parsing the actual Lean source.
3. Generate one Markdown page per Lean module under `docs/libraries/mathformerlib/modules/`.
4. Generate `docs/libraries/mathformerlib/INDEX.md` with module, declaration, status, and
   source links.
5. For source-sensitive formalizations, generate one aligned HTML page per Lean
   module under `docs/libraries/mathformerlib/aligned/`, plus `INDEX.html`.
6. Preserve semantic comments:
   - keep `Original source (NL)` separately from generated notes;
   - keep `Original source (LaTeX)` and generated LaTeX/equivalents rendered as
     MathJax previews with raw LaTeX available;
   - keep exact Lean snippets as code blocks with syntax highlighting;
   - align each textual mention with the formal declaration in source order.
7. Treat documentation as derived output. Regenerate it instead of hand-editing
   per-module pages.

## Commands

```bash
python3 skills/mathformerlib/mathformer-library-docs-generator/scripts/generate_mathformer_library_docs.py \
  --output-dir docs/libraries/mathformerlib \
  --json
```

```bash
python3 skills/mathformerlib/mathformer-library-docs-generator/scripts/generate_mathformer_library_docs.py \
  --include-root MathformerLib \
  --include-root libraries/MathformerLib.lean \
  --registry-file artifacts/mathformerlib/registry.json \
  --expect-docs \
  --json
```

```bash
python3 skills/mathformerlib/mathformer-library-docs-generator/scripts/generate_aligned_html_docs.py \
  --lean-file backends/lean/Mathformer/AutoformalizedCBTChapter1.lean \
  --lean-file backends/lean/Mathformer/AutoformalizedCBTChapter2.lean \
  --output-dir docs/libraries/mathformerlib/aligned \
  --registry-file artifacts/mathformerlib/registry.json \
  --expect-docs \
  --json
```

## Acceptance Rules

Generated documentation is acceptable when:
- every included Lean file has a module page and index entry;
- every parsed declaration has a stable anchor and a Lean code block;
- source-aware comments are rendered as prose plus LaTeX/source sections;
- aligned HTML pages keep original text, original LaTeX, generated notes, and
  Lean code visually paired in source order;
- aligned HTML pages load MathJax for LaTeX and highlight.js-compatible Lean
  code blocks;
- the index links back to repository Lean files and module pages;
- the script exits nonzero under `--expect-docs` if no module pages are produced.
