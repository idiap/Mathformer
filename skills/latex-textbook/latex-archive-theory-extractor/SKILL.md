---
name: latex-archive-theory-extractor
description: Extract theorem-like units, definitions, lemmas, corollaries, theorems, propositions, assumptions, notation blocks, and proofs from LaTeX archives or textbook source trees with line provenance and proof pairing before downstream TeX organization or autoformalization.
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

# LaTeX Archive Theory Extractor

Use this skill when the input is a `.tar.gz`/`.zip` LaTeX source archive or a local
LaTeX textbook directory and the task is to inventory autoformalizable mathematical
content before drafting Lean.

## Workflow

1. Run `scripts/extract_latex_theory.py` on the archive or source directory.
2. Inspect the JSON summary for unit counts, proof counts, and unpaired proofs.
3. Pass the emitted `theory_units.json` to `textbook-theory-tex-organizer`.
4. Do not autoformalize directly from the raw archive; use the extracted unit ids and
   source provenance as the stable interface.

## Command

```bash
python3 skills/latex-textbook/latex-archive-theory-extractor/scripts/extract_latex_theory.py \
  --archive inputs/source.tar.gz \
  --output-dir artifacts/textbook_theory/example \
  --json
```

Use `--source-dir` instead of `--archive` for an already-unpacked tree. Use
`--self-test --json` after editing the script.

## Contract

- Preserve original LaTeX blocks exactly in the JSON payload.
- Record `file`, `line_start`, `line_end`, `label`, section context, references, and
  citations for each unit.
- Pair proof environments with labelled or nearest preceding theorem-like units when
  possible; leave unpaired proofs explicit instead of guessing silently.
- Never generate Lean or completion claims. This skill only extracts source units.
