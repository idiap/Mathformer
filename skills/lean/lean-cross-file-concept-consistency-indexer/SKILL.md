---
name: lean-cross-file-concept-consistency-indexer
description: Index Lean declarations across multiple autoformalization files to detect same-file name collisions, repeated cross-file concepts, divergent signature families, and MathformerLib promotion candidates. Use after adding or modifying Autoformalized*.lean files or before promoting declarations into MathformerLib.
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

# Lean Cross-File Concept Consistency Indexer

Use this skill when several Lean autoformalization files should be checked as a
single evolving theory rather than isolated artifacts.

## Purpose

This skill builds a lightweight concept index over Lean declarations. It detects
same-file declaration collisions, repeated cross-file concepts, divergent
signature families, and candidates for MathformerLib promotion.

## When To Run

- After adding or modifying any `backends/lean/Mathformer/Autoformalized*.lean` file.
- Before promoting declarations into MathformerLib.
- Inside the unified Lean consistency report loop.

## Procedure

1. Run `scripts/index_cross_file_concepts.py` over the target Lean file set.
2. Treat same-file duplicate declaration names as blockers.
3. Review cross-file repeated concepts with divergent signatures.
4. Promote stable shared concepts to MathformerLib through the existing
   promotion gate instead of cloning them repeatedly.

## Command

```bash
python3 skills/lean/lean-cross-file-concept-consistency-indexer/scripts/index_cross_file_concepts.py \
  --lean-file backends/lean/Mathformer/AutoformalizedExamples.lean \
  --lean-file backends/lean/Mathformer/AutoformalizedRadonsTheorem.lean \
  --expect-ok --json
```

## Output Contract

The JSON report contains:

- `ok`: true iff no blocking duplicate/collision was found.
- `concept_index`: normalized concept families and declaration references.
- `summary.cross_file_consistency_score`: reference-free score from 0 to 100.
- `findings`: duplicate, divergence, and promotion-candidate findings.

## Hook

Canonical hook id: `consistency.cross_file_concepts`.
