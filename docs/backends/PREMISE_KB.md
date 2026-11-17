<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Make the framework understandable without requiring readers to inspect implementation details first.

Intent:
  Explain architecture, installation, principles, tutorials, licensing, and generated library outputs.

Function:
  Provides human-facing documentation that should stay aligned with tested behavior and code paths.

Maintenance Notes:
  Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.
-->

# Premise Knowledge Base

MathformerKB is a standalone premise knowledge base for theorem discovery. It is
not yet wired into the main autoformalization workflows.

## Purpose

The KB stores mostly informal mathematical facts while allowing formal surfaces
and proof artifacts to accumulate over time. It supports:

- exact membership checks through Bloom filters over canonical hashes;
- semantic retrieval through deterministic hashed-vector embeddings;
- structured filtering by domain tags, symbols, theorem shape, source, and
  curation status;
- curation actions for review, promotion, rejection, and source queues.

## Storage

Default root:

```text
artifacts/kb/premise_kb/
```

Important files:

```text
entries.jsonl
rejected.jsonl
curation_queue.jsonl
curation_log.jsonl
bloom/*.bloom.json
embeddings/index.json
embeddings/metadata.json
reports/
```

## Entry Model

Each KB entry is one mathematical fact with several surfaces:

- `informal_statement`
- optional `latex_statement`
- zero or more `formal_statements`
- `domain_tags`
- `symbols`
- `theorem_shape`
- `provenance`
- `canonical_hashes`
- `status`

Statuses include:

```text
generated_candidate
source_backed_candidate
reviewed_informal
formal_candidate
proved_formal
rejected
deprecated
```

## Commands

Skill-backed commands:

```bash
python skills/premise-kb/premise-kb-theorem-seed-generator/scripts/generate_theorem_axiom_seed_list.py \
  --family all \
  --include-axioms \
  --include-theorems \
  --output artifacts/kb/generated_theorem_axiom_seeds.jsonl

python skills/premise-kb/premise-kb-theorem-seed-generator/scripts/generate_famous_theorem_axiom_corpus.py \
  --output artifacts/kb/famous_theorems_axioms_500.jsonl

python skills/premise-kb/premise-kb-indexer/scripts/index_premise_kb.py \
  --kb-root artifacts/kb/premise_kb \
  --seed-jsonl artifacts/kb/generated_theorem_axiom_seeds.jsonl \
  --seed-jsonl artifacts/kb/famous_theorems_axioms_500.jsonl \
  --vampire-artifact-root artifacts/vampire_atp \
  --build-bloom \
  --build-embeddings
```

Initialize a KB:

```bash
python scripts/manage_premise_kb.py --kb-root artifacts/kb/premise_kb init
```

Ingest generated common-theorem seeds:

```bash
python scripts/manage_premise_kb.py --kb-root artifacts/kb/premise_kb ingest-seeds
```

Ingest local Vampire theorem artifacts:

```bash
python scripts/manage_premise_kb.py \
  --kb-root artifacts/kb/premise_kb \
  ingest-vampire \
  --artifact-root artifacts/vampire_atp
```

Build exact-membership Bloom filters and deterministic embedding index:

```bash
python scripts/manage_premise_kb.py --kb-root artifacts/kb/premise_kb build-bloom
python scripts/manage_premise_kb.py --kb-root artifacts/kb/premise_kb build-embeddings
```

Refresh canonical surfaces after changing canonicalization rules:

```bash
python scripts/manage_premise_kb.py --kb-root artifacts/kb/premise_kb refresh-canonical
```

Check exact membership:

```bash
python scripts/manage_premise_kb.py \
  --kb-root artifacts/kb/premise_kb \
  has \
  --statement "In a group, the inverse of a product is the product of the inverses in reverse order."
```

By default `has` checks every indexed surface. Use `--surface name` to check a
generated theorem title such as `Fundamental theorem of algebra`.

Semantic search:

```bash
python scripts/manage_premise_kb.py \
  --kb-root artifacts/kb/premise_kb \
  search \
  --query "inverse of a triple product in a group reverses order" \
  --domain-tag group
```

Geometric cosine distance between a query and a specific KB entry:

```bash
python scripts/manage_premise_kb.py \
  --kb-root artifacts/kb/premise_kb \
  distance \
  --query "Fundamental theorem of algebra" \
  --entry-id famous.complex_analysis.fundamental_theorem_of_algebra
```

Queue a URL-backed candidate for later review:

```bash
python scripts/manage_premise_kb.py \
  --kb-root artifacts/kb/premise_kb \
  enqueue-web \
  --url https://example.org/theorem-page \
  --statement "Source-backed theorem statement to review" \
  --domain-tag group
```

Run the standalone regression:

```bash
python tests/kb/run_premise_kb_e2e.py
```

## Design Rules

- Generated facts enter as `generated_candidate`, not trusted premises.
- Bloom filters answer "definitely absent" or "probably present"; a probable hit
  is resolved against JSONL storage before it is reported as a KB match.
- Semantic search is a retrieval aid, not a proof obligation. Reported
  `cosine_distance` values are geometric distances in the deterministic hashed
  vector space.
- Promotion to `proved_formal` should require a formal surface and proof artifact.
