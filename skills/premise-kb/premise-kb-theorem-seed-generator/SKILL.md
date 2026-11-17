---
name: premise-kb-theorem-seed-generator
description: Generate curated seed lists of common mathematical theorems and axioms as MathformerKB JSONL entries for later premise selection. Use when a user wants theorem/axiom lists, generated KB seed facts, or reusable common-fact corpora for the premise knowledge base.
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

# Premise KB Theorem Seed Generator

## Purpose

Use this skill to create generated theorem and axiom seed lists for `MathformerKB`.
Generated entries are candidates, not trusted facts.

## Workflow

1. Choose seed families: `group`, `relation`, `set`, or `all`.
2. Choose seed kinds: axioms, theorems, or both.
3. Run the deterministic generator script and write JSONL entries.
4. Inspect the summary for duplicate IDs and generated counts.
5. Hand the output to `premise-kb-indexer` or `scripts/manage_premise_kb.py ingest-corpus`.

## Command

Generate the compact common seed list:

```bash
python3 skills/premise-kb/premise-kb-theorem-seed-generator/scripts/generate_theorem_axiom_seed_list.py \
  --family all \
  --include-axioms \
  --include-theorems \
  --output artifacts/kb/generated_theorem_axiom_seeds.jsonl \
  --json
```

Generate the 500-entry famous theorem/axiom corpus:

```bash
python3 skills/premise-kb/premise-kb-theorem-seed-generator/scripts/generate_famous_theorem_axiom_corpus.py \
  --output artifacts/kb/famous_theorems_axioms_500.jsonl \
  --json
```

## Output Contract

The script emits one `KBEntry` JSON object per line with:

- `status = generated_candidate`
- `provenance.kind = generated`
- `notes` containing `seed_kind=...` for compact seeds or
  `name_level_seed=true` for the famous corpus
- informal, optional LaTeX, and TPTP formal surfaces
- canonical hashes populated by `MathformerKB`

## Guardrails

- Do not mark generated entries as reviewed or proved.
- Do not use generated entries as trusted premises without later curation or proof evidence.
- Prefer adding new theorem families in the script data tables, not ad hoc output files.
- The famous corpus is name-level and retrieval-oriented; source-backed curation
  should enrich precise statements before trusted use.
