---
name: proof-expansion-difficulty-estimator
description: Estimate how difficult each part of an informal or LaTeX proof will be to expand before formalization, identify omitted lemmas and implicit theorem dependencies, and decide which segments need web-search support. Use before prerequisite expansion when proof text contains dense, cited, standard, or underexplained mathematical steps.
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

# Proof Expansion Difficulty Estimator

## Purpose

Use this skill before LaTeX prerequisite expansion to score proof parts by expansion
difficulty and decide whether external web support is needed.

Runtime:
- `scripts/estimate_proof_expansion_difficulty.py`
- hook: `preformalization.expansion_difficulty`

## Workflow

1. Segment the proof into local expansion units.
2. Score each segment for hidden dependencies, omitted arguments, citations, named theorem reliance, symbolic density, and domain-specific machinery.
3. Mark web search as recommended for high-score segments or any segment relying on external named results, citations, or "standard/well-known" claims.
4. Produce suggested queries for `proof-expansion-web-researcher`.
5. Hand the resulting report to `proof-expansion-support-orchestrator` before `latex-prerequisite-expander`.

## Command

```bash
python3 skills/autoformalization/proof-expansion-difficulty-estimator/scripts/estimate_proof_expansion_difficulty.py \
  --proof-file tests/latex/sazonov_theorem.tex \
  --json
```

## References

- Read `references/difficulty.md` for scoring bands and search-decision rules.
