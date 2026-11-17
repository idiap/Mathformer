# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Make reusable mathematical facts searchable before they are trusted as proof premises.
#
# Intent:
#   Combine canonical hashes, Bloom-filter membership checks, and vector-space similarity for premise retrieval.
#
# Function:
#   Defines storage, ingestion, indexing, and search behavior for the local premise knowledge base.
#
# Maintenance Notes:
#   Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.

"""Index builders for Bloom filters and deterministic embeddings."""

from __future__ import annotations

import json

from .bloom import build_bloom
from .embeddings import EmbeddingIndex
from .storage import KBStore


def build_bloom_indexes(
    store: KBStore, *, false_positive_rate: float = 0.01
) -> dict[str, str]:
    """Document the responsibility of ``build_bloom_indexes``.

    Motivation:
        Make reusable mathematical facts searchable before they are trusted as proof premises.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    store.init()
    entries = store.read_entries(include_rejected=True)
    surfaces: dict[str, list[str]] = {"proved": []}
    for entry in entries:
        for surface, value in entry.canonical_hashes.items():
            if value:
                surfaces.setdefault(surface, []).append(value)
        if entry.is_proved:
            surfaces["proved"].append(entry.id)
            surfaces["proved"].extend(entry.canonical_hashes.values())

    paths: dict[str, str] = {}
    for surface, values in surfaces.items():
        bloom = build_bloom(values, false_positive_rate=false_positive_rate)
        path = store.bloom_dir / f"{surface}.bloom.json"
        bloom.save(path)
        paths[surface] = str(path)
    manifest = {
        "surfaces": paths,
        "entry_count": len(entries),
        "false_positive_rate": false_positive_rate,
    }
    manifest_path = store.bloom_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    paths["manifest"] = str(manifest_path)
    return paths


def build_embedding_index(store: KBStore, *, dimension: int = 512) -> str:
    """Document the responsibility of ``build_embedding_index``.

    Motivation:
        Make reusable mathematical facts searchable before they are trusted as proof premises.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    store.init()
    entries = store.read_entries(include_rejected=True)
    index = EmbeddingIndex(dimension=dimension)
    index.build(entries)
    path = store.embedding_dir / "index.json"
    index.save(path)
    metadata = {
        "dimension": dimension,
        "entry_count": len(entries),
        "row_count": len(index.rows),
        "index_path": str(path),
    }
    (store.embedding_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return str(path)
