---
name: paper-docling-layout-extractor
description: Extract robust structured layout from mathematical papers, especially PDF URLs, using docling when available and explicit fallback engines otherwise. Use before autoformalizing a paper's main theory to produce section blocks, theorem/proof neighborhoods, equations, citation markers, and references with provenance.
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

# Paper Docling Layout Extractor

## Purpose

Use this skill at paper intake, before source-unit extraction or theorem localization. It
converts a PDF URL/file or paper text into a layout-aware JSON packet.

Hook:
- `intake.paper_layout_extract`

## Workflow

1. Prefer docling for PDF and layout-rich inputs.
2. Preserve source provenance: URL/path, extraction engine, title if available, block ids,
   page numbers when available, section labels, citations, and references.
3. Emit warnings when docling is unavailable or a fallback engine is used.
4. Do not select the main theorem here; hand the layout packet to
   `paper-main-theory-localizer`.
5. Keep raw text spans compact enough to be reusable by proof expansion and source comments.

## Engine Setup

For local PDF extraction, use the repository environment with paper extraction enabled:

```bash
scripts/install_uv_env.sh --with-paper-extraction --skip-lean
```

Then run the extraction script with `python` if the active `python` does not
have docling installed. If docling is unavailable, the script must return an explicit
`engine.name: unavailable` report rather than inventing layout blocks.

## Commands

PDF URL:

```bash
python skills/paper/paper-docling-layout-extractor/scripts/extract_paper_layout.py \
  --url "https://proceedings.neurips.cc/paper_files/paper/2024/file/4a68bb0e075a3215d4ff37382ea598dc-Paper-Conference.pdf" \
  --json
```

Text-mode smoke path:

```bash
python skills/paper/paper-docling-layout-extractor/scripts/extract_paper_layout.py \
  --text-file paper.txt \
  --json
```

## Output Contract

The JSON packet contains:

- `source`: input URL/path/title and retrieval timestamp.
- `engine`: `docling`, `text`, or explicit unavailable/fallback status.
- `sections`: ordered section ids, titles, and block ids.
- `blocks`: ordered text blocks with section, page if known, citations, labels, and role hints.
- `references`: parsed bibliography-like entries keyed by citation id when possible.
- `warnings`: extraction limitations that downstream skills must preserve.

Read `references/layout_packet_schema.json` when validating stored packets.
