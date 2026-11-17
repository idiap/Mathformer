---
name: premise-kb-indexer
description: Index generated theorem/axiom seed lists, local proof artifacts, corpus entries, and review candidates into MathformerKB with Bloom filters and deterministic embeddings. Use when a user wants to build, refresh, or query the standalone premise knowledge base for premise selection.
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

# Premise KB Indexer

## Purpose

Use this skill to populate and refresh a standalone `MathformerKB` store from
generated theorem/axiom lists, local Vampire artifacts, and JSONL corpora.

## Workflow

1. Choose a KB root, usually `artifacts/kb/premise_kb`.
2. Ingest one or more sources:
   - generated seed JSONL from `premise-kb-theorem-seed-generator`;
   - local Vampire artifacts under `artifacts/vampire_atp`;
   - external corpus JSONL entries;
   - web-backed review candidates through the queue.
3. Build Bloom filters for exact membership.
4. Build deterministic embedding indexes for semantic search.
5. Run a membership or semantic-search smoke check.

## Command

```bash
python3 skills/premise-kb/premise-kb-indexer/scripts/index_premise_kb.py \
  --kb-root artifacts/kb/premise_kb \
  --seed-jsonl artifacts/kb/generated_theorem_axiom_seeds.jsonl \
  --vampire-artifact-root artifacts/vampire_atp \
  --build-bloom \
  --build-embeddings \
  --json
```

## Query Smoke Checks

```bash
python3 scripts/manage_premise_kb.py \
  --kb-root artifacts/kb/premise_kb \
  has \
  --statement "In a group, the inverse of a product is the product of the inverses in reverse order."

python3 scripts/manage_premise_kb.py \
  --kb-root artifacts/kb/premise_kb \
  search \
  --query "inverse of a triple product in a group reverses order" \
  --domain-tag group
```

## Guardrails

- Treat Bloom hits as `probably_present`; resolve them against JSONL storage.
- Keep generated entries as `generated_candidate` until reviewed or proved.
- Rebuild Bloom and embedding indexes after any substantial ingest or curation update.
- Do not wire this into main theorem workflows unless the user explicitly requests integration.
