---
name: source-line-translation-packet-builder
description: Build a line-by-line NL/LaTeX-to-Lean translation packet with stable literal source anchors before autoformalization. Use when informal mathematics from a page, paper, textbook chapter, theory-unit JSON, or source-unit inventory must be exposed to the drafter as anchored source lines, candidate Lean surfaces, and reference points that prevent semantic drift.
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

# Source Line Translation Packet Builder

## Purpose

Use this skill after source extraction and expansion review, before first Lean
drafting. It creates a compact bridge from the original informal mathematics to
Lean-facing obligations:

- stable source line ids such as `src_L0007`;
- exact literal text and a hash for each line group;
- NL/LaTeX fragments that the LLM should reason over;
- candidate Lean declaration surfaces;
- a prompt-ready alignment context.

Hook:
- `preformalization.line_translation_packet`

Runtime:
- `scripts/build_line_translation_packet.py`

## Workflow

1. Start from the most literal source available: original text/LaTeX lines, a
   theory-unit JSON file, or a source-unit inventory.
2. Preserve exact text in `source_lines`; do not normalize away notation before
   the source line ids and hashes are created.
3. Group nearby nonblank lines into translation units, splitting at theorem-like
   environments, proof environments, displayed formulas, and blank lines.
4. For each unit, assign:
   - `source_line_ids`;
   - `literal_text`;
   - `latex_fragments`;
   - `informal_kind`;
   - `target_lean_surface`;
   - `candidate_declaration_name`;
   - `drafting_instruction`.
5. Pass `lean_prompt_context` to `lean-autoformalization-drafter` as core
   statement alignment annotations.
6. Require declarations generated from source material to include a compact
   doc-comment line such as `Source anchors: src_L0007-src_L0010`. Do not add
   per-line Lean comments.

## Commands

From a text or TeX file:

```bash
python3 skills/autoformalization/source-line-translation-packet-builder/scripts/build_line_translation_packet.py \
  --source-file path/to/chapter1.tex \
  --title "Chapter 1" \
  --output-file artifacts/source_alignment/chapter1.line_translation.json \
  --expect-nonempty \
  --json
```

From source text:

```bash
python3 skills/autoformalization/source-line-translation-packet-builder/scripts/build_line_translation_packet.py \
  --text "A theorem. If n = 0, then n = n." \
  --title "Toy theorem" \
  --json
```

## Output Contract

The packet must contain:

- `source`: title, source id, created timestamp, line count.
- `source_lines`: exact lines with stable ids and line hashes.
- `translation_units`: source-line groups with Lean-facing instructions.
- `lean_prompt_context`: text safe to inject into the drafter prompt.
- `summary`: counts and coverage metrics.

The packet is an aid for generation, not a proof of correctness. The generated
Lean must still pass compile, realness, semantic, non-vacuity, and consistency
gates.
