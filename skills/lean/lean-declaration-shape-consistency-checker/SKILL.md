---
name: lean-declaration-shape-consistency-checker
description: Deterministically check whether a Lean theorem-like declaration's signature preserves the logical shape advertised by its natural-language and LaTeX source annotations. Use as a preflight critic before trusting an autoformalized theorem, lemma, or axiom as semantically aligned with its source text.
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

# Lean Declaration Shape Consistency Checker

Use this skill when a Lean artifact must be checked for agreement between the
source-facing mathematical claim and the Lean declaration shape.

## Purpose

This skill is a deterministic preflight critic for final or near-final Lean
files. It checks whether theorem-like declarations preserve the logical shape
advertised by their natural-language and LaTeX annotations.

## When To Run

- After the first saved Lean artifact is available.
- Before trusting an autoformalized theorem, lemma, or axiom as semantically
  aligned with its source text.
- Inside the unified Lean consistency report loop.

## Procedure

1. Run `scripts/check_declaration_shape_consistency.py` on the target files.
2. Treat high-severity findings as blockers.
3. For every blocker, either repair the Lean signature or add an explicit
   generated note explaining the intended representation boundary, such as an
   explicit witness record or external assumption.
4. Re-run until the score is monotone nondecreasing and no blocker remains.

## Command

```bash
python3 skills/lean/lean-declaration-shape-consistency-checker/scripts/check_declaration_shape_consistency.py \
  --lean-file backends/lean/Mathformer/AutoformalizedExample.lean \
  --expect-ok --json
```

## Output Contract

The script emits a JSON report with:

- `ok`: true iff no blocking shape mismatch was found.
- `summary.shape_score`: reference-free score from 0 to 100.
- `findings`: localized declaration-shape issues.
- `extractor_report`: optional source packet when `--include-extractor-report`
  is passed.

## Hook

Canonical hook id: `consistency.declaration_shape`.
