---
name: source-formalization-drift-guard
description: Validate that generated Lean declarations preserve literal source anchors from a line-by-line NL/LaTeX translation packet. Use after initial autoformalization, refinement, or denoising to detect missing source anchors, orphan anchors, weak source coverage, or declaration drift away from the original informal mathematics.
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

# Source Formalization Drift Guard

## Purpose

Use this skill after a Lean draft exists and before accepting it as complete.
It checks whether Lean declaration comments still cite the literal source line
ids created by `source-line-translation-packet-builder`.

Hook:
- `postformalization.source_anchor_drift_guard`

Runtime:
- `scripts/validate_source_formalization_alignment.py`

## Workflow

1. Load the line translation packet for the source unit or chapter.
2. Parse each Lean declaration and its attached doc comment.
3. Extract `Source anchors:` references, including ranges such as
   `src_L0007-src_L0010`.
4. Report:
   - anchored declarations;
   - source lines covered by Lean declarations;
   - uncovered formalizable translation units;
   - orphan anchor references not present in the packet;
   - declarations with source-like comments but no anchor.
5. Block final acceptance when coverage is below the configured threshold, when
   orphan anchors appear, or when theorem-like units are left uncovered without
   an explicit representation-boundary note.

## Commands

```bash
python3 skills/autoformalization/source-formalization-drift-guard/scripts/validate_source_formalization_alignment.py \
  --packet artifacts/source_alignment/chapter1.line_translation.json \
  --lean-file backends/lean/Mathformer/AutoformalizedCBTChapter1.lean \
  --min-anchor-coverage 0.85 \
  --json
```

For a strict fixture or CI expectation:

```bash
python3 skills/autoformalization/source-formalization-drift-guard/scripts/validate_source_formalization_alignment.py \
  --packet artifacts/source_alignment/example.line_translation.json \
  --lean-file backends/lean/Mathformer/Example.lean \
  --min-anchor-coverage 1.0 \
  --expect-ok \
  --json
```

## Comment Contract

Generated declarations should keep source-aware comments compact:

```lean
/--
Original source (NL): ...
Original source (LaTeX): ...
Source anchors: src_L0007-src_L0010
-/
theorem ...
```

Do not use legacy per-line `NL/LaTeX:` comments. The anchor line belongs in the
declaration or module doc comment, not on every Lean line.
