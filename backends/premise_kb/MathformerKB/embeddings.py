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

"""Deterministic sparse-vector embedding index for premise KB entries."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Iterable

from .canonicalize import canonicalize_informal, semantic_card
from .schema import KBEntry


@dataclass(frozen=True)
class EmbeddingHit:
    """Document the responsibility of ``EmbeddingHit``.

    Motivation:
        Make reusable mathematical facts searchable before they are trusted as proof premises.

    Intent:
        Group related state and behavior so callers can use this part of the MathformerKB workflow through a clear object boundary.

    Function:
        Defines storage, ingestion, indexing, and search behavior for the local premise knowledge base.

    Maintenance:
        Keep the class contract explicit when adding fields, constructor requirements, or externally visible methods.
    """

    entry_id: str
    score: float
    surface: str
    text: str
    metadata: dict[str, object]

    @property
    def distance(self) -> float:
        """Document the responsibility of ``EmbeddingHit.distance``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Provide the local operation named ``EmbeddingHit.distance`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        return max(0.0, 1.0 - self.score)

    def to_dict(self) -> dict[str, object]:
        """Document the responsibility of ``EmbeddingHit.to_dict``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Provide the local operation named ``EmbeddingHit.to_dict`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        return {
            "entry_id": self.entry_id,
            "score": self.score,
            "cosine_similarity": self.score,
            "cosine_distance": self.distance,
            "surface": self.surface,
            "text": self.text,
            "metadata": self.metadata,
        }


class EmbeddingIndex:
    """A small sparse-vector index using feature hashing and cosine similarity."""

    def __init__(self, *, dimension: int = 512) -> None:
        """Document the responsibility of ``EmbeddingIndex.__init__``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Initialize instance state while keeping constructor assumptions explicit for future maintainers.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        self.dimension = dimension
        self.rows: list[dict[str, object]] = []

    def add_entry(self, entry: KBEntry) -> None:
        """Document the responsibility of ``EmbeddingIndex.add_entry``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Provide the local operation named ``EmbeddingIndex.add_entry`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        surfaces = {
            "semantic_card": semantic_card(entry),
            "informal": entry.informal_statement,
        }
        if entry.latex_statement:
            surfaces["latex"] = entry.latex_statement
        for formal in entry.formal_statements:
            surfaces[f"formal_{formal.system.lower()}"] = formal.statement
        for surface, text in surfaces.items():
            vector = embed_text(text, dimension=self.dimension)
            if not vector:
                continue
            self.rows.append(
                {
                    "entry_id": entry.id,
                    "surface": surface,
                    "text": text,
                    "vector": vector,
                    "metadata": {
                        "status": entry.status,
                        "domain_tags": entry.domain_tags,
                        "symbols": entry.symbols,
                        "theorem_shape": entry.theorem_shape,
                        "proved": entry.is_proved,
                    },
                }
            )

    def build(self, entries: Iterable[KBEntry]) -> None:
        """Document the responsibility of ``EmbeddingIndex.build``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Build the local data structure or artifact used by the next workflow stage.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        self.rows = []
        for entry in entries:
            self.add_entry(entry)

    def search(
        self,
        query: str,
        *,
        k: int = 10,
        domain_tags: list[str] | None = None,
        statuses: list[str] | None = None,
        proved_only: bool = False,
    ) -> list[EmbeddingHit]:
        """Document the responsibility of ``EmbeddingIndex.search``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Search available candidates and return the matches needed by the caller.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        query_vector = embed_text(query, dimension=self.dimension)
        hits: list[EmbeddingHit] = []
        for row in self.rows:
            metadata = row["metadata"]
            if not isinstance(metadata, dict):
                continue
            if domain_tags:
                row_domains = set(metadata.get("domain_tags", []))
                if not row_domains.intersection(domain_tags):
                    continue
            if statuses and metadata.get("status") not in statuses:
                continue
            if proved_only and not metadata.get("proved"):
                continue
            score = cosine(query_vector, row["vector"])  # type: ignore[arg-type]
            if score <= 0:
                continue
            hits.append(
                EmbeddingHit(
                    entry_id=str(row["entry_id"]),
                    score=score,
                    surface=str(row["surface"]),
                    text=str(row["text"]),
                    metadata=metadata,
                )
            )
        hits.sort(key=lambda hit: (-hit.score, hit.entry_id, hit.surface))
        return hits[:k]

    def compare(
        self,
        query: str,
        *,
        entry_id: str,
        surface: str | None = None,
    ) -> list[EmbeddingHit]:
        """Document the responsibility of ``EmbeddingIndex.compare``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Provide the local operation named ``EmbeddingIndex.compare`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        query_vector = embed_text(query, dimension=self.dimension)
        hits: list[EmbeddingHit] = []
        for row in self.rows:
            if str(row["entry_id"]) != entry_id:
                continue
            if surface and str(row["surface"]) != surface:
                continue
            score = cosine(query_vector, row["vector"])  # type: ignore[arg-type]
            metadata = row["metadata"] if isinstance(row["metadata"], dict) else {}
            hits.append(
                EmbeddingHit(
                    entry_id=entry_id,
                    score=score,
                    surface=str(row["surface"]),
                    text=str(row["text"]),
                    metadata=metadata,
                )
            )
        hits.sort(key=lambda hit: (-hit.score, hit.surface))
        return hits

    def save(self, path: Path) -> Path:
        """Document the responsibility of ``EmbeddingIndex.save``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Persist or emit computed data in the format expected by later workflow stages.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "dimension": self.dimension,
            "row_count": len(self.rows),
            "rows": self.rows,
        }
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return path

    @classmethod
    def load(cls, path: Path) -> "EmbeddingIndex":
        """Document the responsibility of ``EmbeddingIndex.load``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Load data from the declared source while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        payload = json.loads(path.read_text(encoding="utf-8"))
        obj = cls(dimension=int(payload["dimension"]))
        obj.rows = list(payload.get("rows", []))
        return obj


def embed_text(text: str, *, dimension: int = 512) -> dict[str, float]:
    """Document the responsibility of ``embed_text``.

    Motivation:
        Make reusable mathematical facts searchable before they are trusted as proof premises.

    Intent:
        Provide the local operation named ``embed_text`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    counts: dict[int, float] = {}
    for token in _tokens(text):
        index = _feature_index(token, dimension)
        counts[index] = counts.get(index, 0.0) + 1.0
    norm = math.sqrt(sum(value * value for value in counts.values()))
    if norm == 0:
        return {}
    return {str(index): value / norm for index, value in sorted(counts.items())}


def cosine(left: dict[str, float], right: dict[str, float]) -> float:
    """Document the responsibility of ``cosine``.

    Motivation:
        Make reusable mathematical facts searchable before they are trusted as proof premises.

    Intent:
        Provide the local operation named ``cosine`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if not left or not right:
        return 0.0
    if len(left) > len(right):
        left, right = right, left
    return sum(value * right.get(key, 0.0) for key, value in left.items())


def _tokens(text: str) -> list[str]:
    """Document the responsibility of ``_tokens``.

    Motivation:
        Make reusable mathematical facts searchable before they are trusted as proof premises.

    Intent:
        Provide the local operation named ``_tokens`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    base = canonicalize_informal(text)
    tokens = re.findall(r"\b[a-z0-9_]{2,}\b|[=^*/+-]", base)
    expanded: list[str] = []
    for token in tokens:
        expanded.append(token)
        if token == "triple":
            expanded.append("three")
        elif token == "three":
            expanded.append("triple")
        if "_" in token:
            expanded.extend(part for part in token.split("_") if part)
    return expanded


def _feature_index(token: str, dimension: int) -> int:
    """Document the responsibility of ``_feature_index``.

    Motivation:
        Make reusable mathematical facts searchable before they are trusted as proof premises.

    Intent:
        Provide the local operation named ``_feature_index`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    digest = hashlib.blake2b(
        token.encode("utf-8"), digest_size=8, person=b"kbembed"
    ).digest()
    return int.from_bytes(digest, "big") % dimension
