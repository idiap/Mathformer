---
name: rocq-autoformalization-drafter
description: Draft complete Rocq `.v` proof scripts from controlled Mathformer informal or LaTeX theorem cases, preserving source comments and rejecting placeholder proofs.
---

<!--
File Documentation

Motivation:
  Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

Intent:
  Tell coding agents how to create Rocq proof artifacts that match the Mathformer source-preservation contract.

Function:
  Describes the Rocq autoformalization workflow and points to the deterministic drafting script.

Maintenance Notes:
  Keep this skill aligned with `backends/rocq/MathformerRocq/autoformalize.py` and the Rocq smoke tests.
-->

# Rocq Autoformalization Drafter

Use this skill when the target formal surface is Rocq. The drafter currently
owns the deterministic controlled wiki-level suite and emits complete `.v`
files with:

- SPDX and file-documentation headers.
- Source theorem/proof comments.
- Minimal local definitions when the statement needs a concept such as
  injectivity, monotonicity, or set equality.
- Placeholder-free proofs ending in `Qed.`
- A JSON report with structural validation evidence.

## Full Controlled Suite

```bash
python skills/rocq/rocq-autoformalization-drafter/scripts/draft_rocq_wiki_case.py \
  --manifest-file tests/latex/wiki_level/manifest.json \
  --output-dir MathformerRocq \
  --report-file artifacts/rocq/wiki_level_draft.json \
  --json
```

## One Case

```bash
python skills/rocq/rocq-autoformalization-drafter/scripts/draft_rocq_wiki_case.py \
  --latex-file tests/latex/wiki_level/injective_composition.tex \
  --case-id wiki_injective_composition \
  --output-file backends/rocq/MathformerRocq/AutoformalizedWikiInjectiveComposition.v \
  --report-file artifacts/rocq/wiki_injective_composition_draft.json \
  --json
```

## Validation

Run `rocq-execution-runner` after drafting. It performs structural validation
everywhere and calls `rocq compile` or `coqc` when a compiler is installed.
