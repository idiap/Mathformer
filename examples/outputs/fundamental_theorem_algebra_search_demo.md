<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Preserve a compact demonstration output for README-level premise search.

Intent:
  Show exact presence, semantic search, and geometric distance for a known
  theorem query without requiring the reader to open the full KB index.

Function:
  Summarizes the local KB response for the query "Fundamental theorem of
  algebra" against the generated famous theorem and axiom corpus.

Maintenance Notes:
  Regenerate this summary when the famous theorem corpus, canonicalization, or
  embedding index changes.
-->

# Fundamental Theorem Of Algebra Search Demo

Query:

```text
Fundamental theorem of algebra
```

Generated KB root:

```text
artifacts/kb/famous_corpus_test/kb
```

## Exact Presence

- `probably_present`: `true`
- matched surface: `name`
- resolved entry: `famous.complex_analysis.fundamental_theorem_of_algebra`

## Top Semantic Hits

| Rank | Entry | Score | Cosine Distance |
| --- | --- | ---: | ---: |
| 1 | `famous.complex_analysis.fundamental_theorem_of_algebra` | `0.846497` | `0.183503` |
| 2 | `famous.linear_algebra.polar_decomposition_theorem` | `0.700820` | `0.329180` |
| 3 | `famous.number_theory.fundamental_theorem_of_arithmetic` | `0.642372` | `0.387628` |
| 4 | `famous.algebra.cayley_s_theorem` | `0.607350` | `0.422650` |
| 5 | `famous.algebra.lagrange_s_theorem` | `0.607350` | `0.422650` |

## Geometric Distance To Intended Entry

- entry: `famous.complex_analysis.fundamental_theorem_of_algebra`
- surface: `latex`
- cosine similarity: `0.816497`
- cosine distance: `0.183503`

## Generated Local Artifacts

- `artifacts/kb/famous_corpus_test/famous_theorems_axioms_500.jsonl`
- `artifacts/kb/famous_corpus_test/kb/entries.jsonl`
- `artifacts/kb/famous_corpus_test/kb/bloom/manifest.json`
- `artifacts/kb/famous_corpus_test/kb/embeddings/metadata.json`
