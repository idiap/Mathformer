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

"""Standalone premise knowledge base for Mathformer."""

from .bloom import BloomFilter, BloomMembership
from .canonicalize import (
    canonical_hash,
    canonicalize_formal,
    canonicalize_informal,
    canonicalize_latex,
)
from .embeddings import EmbeddingHit, EmbeddingIndex
from .schema import FormalSurface, KBEntry, ProvenanceRecord
from .search import PremiseKB, PremiseKBPacket
from .storage import KBStore

__all__ = [
    "BloomFilter",
    "BloomMembership",
    "EmbeddingHit",
    "EmbeddingIndex",
    "FormalSurface",
    "KBEntry",
    "KBStore",
    "PremiseKB",
    "PremiseKBPacket",
    "ProvenanceRecord",
    "canonical_hash",
    "canonicalize_formal",
    "canonicalize_informal",
    "canonicalize_latex",
]
