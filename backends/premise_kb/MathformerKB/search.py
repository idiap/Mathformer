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

"""Search facade combining Bloom membership and embedding retrieval."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .bloom import BloomFilter, BloomMembership
from .canonicalize import canonical_hash, infer_theorem_shape
from .embeddings import EmbeddingHit, EmbeddingIndex
from .storage import KBStore


@dataclass(frozen=True)
class PremiseKBPacket:
    """Document the responsibility of ``PremiseKBPacket``.

    Motivation:
        Make reusable mathematical facts searchable before they are trusted as proof premises.

    Intent:
        Group related state and behavior so callers can use this part of the MathformerKB workflow through a clear object boundary.

    Function:
        Defines storage, ingestion, indexing, and search behavior for the local premise knowledge base.

    Maintenance:
        Keep the class contract explicit when adding fields, constructor requirements, or externally visible methods.
    """

    query: str
    exact: BloomMembership
    semantic_hits: list[dict[str, Any]]
    trusted_hits: list[dict[str, Any]]
    rejected_near_hits: list[dict[str, Any]]
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Document the responsibility of ``PremiseKBPacket.to_dict``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Provide the local operation named ``PremiseKBPacket.to_dict`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        return {
            "query": self.query,
            "exact": self.exact.to_dict(),
            "semantic_hits": self.semantic_hits,
            "trusted_hits": self.trusted_hits,
            "rejected_near_hits": self.rejected_near_hits,
            "notes": self.notes,
        }


class PremiseKB:
    """Loaded KB plus optional Bloom and embedding indexes."""

    def __init__(self, root: Path) -> None:
        """Document the responsibility of ``PremiseKB.__init__``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Initialize instance state while keeping constructor assumptions explicit for future maintainers.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        self.store = KBStore(root)
        self.root = root
        self.entries = self.store.read_entries(include_rejected=True)
        self.by_id = {entry.id: entry for entry in self.entries}
        self.surfaces = sorted(
            {surface for entry in self.entries for surface in entry.canonical_hashes}
        )
        self.hash_indexes = {
            surface: self.store.hash_index(surface=surface, include_rejected=True)
            for surface in self.surfaces
        }
        self.blooms: dict[str, BloomFilter] = {}
        for path in sorted(self.store.bloom_dir.glob("*.bloom.json")):
            self.blooms[path.name.removesuffix(".bloom.json")] = BloomFilter.load(path)
        embedding_path = self.store.embedding_dir / "index.json"
        self.embedding_index = (
            EmbeddingIndex.load(embedding_path) if embedding_path.exists() else None
        )

    def has_exact(
        self, statement: str, *, surface: str = "informal"
    ) -> BloomMembership:
        """Document the responsibility of ``PremiseKB.has_exact``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Provide the local operation named ``PremiseKB.has_exact`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        if surface == "any":
            return self.has_any(statement)
        query_hash = canonical_hash(statement, surface=surface)
        bloom = self.blooms.get(surface)
        probably_present = (
            query_hash in bloom
            if bloom
            else query_hash in self.hash_indexes.get(surface, {})
        )
        resolved = (
            self.hash_indexes.get(surface, {}).get(query_hash, [])
            if probably_present
            else []
        )
        return BloomMembership(
            surface=surface,
            query_hash=query_hash,
            probably_present=probably_present,
            resolved_entry_ids=resolved,
            checked_surfaces=[surface],
            matched_surfaces=[surface] if resolved else [],
            query_hashes={surface: query_hash},
        )

    def has_any(self, statement: str) -> BloomMembership:
        """Document the responsibility of ``PremiseKB.has_any``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Provide the local operation named ``PremiseKB.has_any`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        checked_surfaces = sorted(self.hash_indexes)
        matched_surfaces: list[str] = []
        query_hashes: dict[str, str] = {}
        resolved: list[str] = []
        for surface in checked_surfaces:
            query_hash = canonical_hash(statement, surface=surface)
            query_hashes[surface] = query_hash
            bloom = self.blooms.get(surface)
            probably_present = (
                query_hash in bloom
                if bloom
                else query_hash in self.hash_indexes.get(surface, {})
            )
            if not probably_present:
                continue
            surface_ids = self.hash_indexes.get(surface, {}).get(query_hash, [])
            if surface_ids:
                matched_surfaces.append(surface)
                resolved.extend(surface_ids)
        resolved = sorted(dict.fromkeys(resolved))
        return BloomMembership(
            surface="any",
            query_hash="",
            probably_present=bool(resolved),
            resolved_entry_ids=resolved,
            checked_surfaces=checked_surfaces,
            matched_surfaces=matched_surfaces,
            query_hashes=query_hashes,
        )

    def search_semantic(
        self,
        query: str,
        *,
        k: int = 10,
        domain_tags: list[str] | None = None,
        statuses: list[str] | None = None,
        proved_only: bool = False,
    ) -> list[dict[str, Any]]:
        """Document the responsibility of ``PremiseKB.search_semantic``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Search available candidates and return the matches needed by the caller.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        index = self._active_embedding_index()
        hits = index.search(
            query,
            k=k * 3,
            domain_tags=domain_tags,
            statuses=statuses,
            proved_only=proved_only,
        )
        reranked = [
            self._rerank_hit(query, hit, domain_tags=domain_tags) for hit in hits
        ]
        reranked.sort(
            key=lambda item: (
                -float(item["score"]),
                str(item["entry_id"]),
                str(item["surface"]),
            )
        )
        deduped: list[dict[str, Any]] = []
        seen: set[str] = set()
        for hit in reranked:
            entry_id = str(hit["entry_id"])
            if entry_id in seen:
                continue
            seen.add(entry_id)
            deduped.append(hit)
            if len(deduped) >= k:
                break
        return deduped

    def geometric_distance(
        self,
        query: str,
        *,
        entry_id: str,
        surface: str = "best",
    ) -> dict[str, Any]:
        """Document the responsibility of ``PremiseKB.geometric_distance``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Provide the local operation named ``PremiseKB.geometric_distance`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        if entry_id not in self.by_id:
            raise KeyError(f"No KB entry with id {entry_id!r}.")
        index = self._active_embedding_index()
        hits = index.compare(
            query,
            entry_id=entry_id,
            surface=None if surface == "best" else surface,
        )
        if not hits:
            raise KeyError(
                f"No embedding row for entry {entry_id!r} and surface {surface!r}."
            )
        hit = hits[0]
        return {
            "query": query,
            "entry_id": entry_id,
            "surface": hit.surface,
            "cosine_similarity": round(hit.score, 6),
            "cosine_distance": round(hit.distance, 6),
            "entry": self.by_id[entry_id].to_dict(),
        }

    def search_for_premises(
        self,
        query: str,
        *,
        k: int = 20,
        surface: str = "informal",
        domain_tags: list[str] | None = None,
    ) -> PremiseKBPacket:
        """Document the responsibility of ``PremiseKB.search_for_premises``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Search available candidates and return the matches needed by the caller.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        exact = self.has_exact(query, surface=surface)
        semantic_hits = self.search_semantic(query, k=k, domain_tags=domain_tags)
        trusted_hits = [
            hit
            for hit in semantic_hits
            if hit["entry"].get("status")
            in {"reviewed_informal", "formal_candidate", "proved_formal"}
        ]
        rejected_hits = [
            hit for hit in semantic_hits if hit["entry"].get("status") == "rejected"
        ]
        notes = [
            "Bloom membership is used as a fast gate; resolved_entry_ids are checked against JSONL storage.",
            "Semantic hits use deterministic hashed-vector cosine similarity and metadata reranking.",
        ]
        return PremiseKBPacket(
            query=query,
            exact=exact,
            semantic_hits=semantic_hits,
            trusted_hits=trusted_hits,
            rejected_near_hits=rejected_hits,
            notes=notes,
        )

    def _rerank_hit(
        self,
        query: str,
        hit: EmbeddingHit,
        *,
        domain_tags: list[str] | None,
    ) -> dict[str, Any]:
        """Document the responsibility of ``PremiseKB._rerank_hit``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Provide the local operation named ``PremiseKB._rerank_hit`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        entry = self.by_id[hit.entry_id]
        score = hit.score
        query_shape = infer_theorem_shape(query)
        shape_overlap = sorted(query_shape.intersection(entry.theorem_shape))
        if shape_overlap:
            score += 0.05
        if domain_tags and set(domain_tags).intersection(entry.domain_tags):
            score += 0.05
        if entry.is_proved:
            score += 0.04
        elif entry.status == "generated_candidate":
            score -= 0.02
        return {
            "entry_id": hit.entry_id,
            "score": round(score, 6),
            "base_score": round(hit.score, 6),
            "base_distance": round(hit.distance, 6),
            "cosine_similarity": round(hit.score, 6),
            "cosine_distance": round(hit.distance, 6),
            "rerank_delta": round(score - hit.score, 6),
            "surface": hit.surface,
            "shape_overlap": shape_overlap,
            "entry": entry.to_dict(),
        }

    def _active_embedding_index(self) -> EmbeddingIndex:
        """Document the responsibility of ``PremiseKB._active_embedding_index``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Provide the local operation named ``PremiseKB._active_embedding_index`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        if self.embedding_index is not None:
            return self.embedding_index
        index = EmbeddingIndex()
        index.build(self.entries)
        return index
