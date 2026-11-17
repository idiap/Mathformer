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

"""Small pure-Python Bloom filter implementation for KB membership checks."""

from __future__ import annotations

from typing import Any

from dataclasses import dataclass, field
import base64
import hashlib
import json
import math
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class BloomMembership:
    """Document the responsibility of ``BloomMembership``.

    Motivation:
        Make reusable mathematical facts searchable before they are trusted as proof premises.

    Intent:
        Group related state and behavior so callers can use this part of the MathformerKB workflow through a clear object boundary.

    Function:
        Defines storage, ingestion, indexing, and search behavior for the local premise knowledge base.

    Maintenance:
        Keep the class contract explicit when adding fields, constructor requirements, or externally visible methods.
    """

    surface: str
    query_hash: str
    probably_present: bool
    resolved_entry_ids: list[str]
    checked_surfaces: list[str] = field(default_factory=list)
    matched_surfaces: list[str] = field(default_factory=list)
    query_hashes: dict[str, str] = field(default_factory=dict)

    @property
    def definitely_absent(self) -> bool:
        """Document the responsibility of ``BloomMembership.definitely_absent``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Provide the local operation named ``BloomMembership.definitely_absent`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        return not self.probably_present

    def to_dict(self) -> dict[str, Any]:
        """Document the responsibility of ``BloomMembership.to_dict``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Provide the local operation named ``BloomMembership.to_dict`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        return {
            "surface": self.surface,
            "query_hash": self.query_hash,
            "probably_present": self.probably_present,
            "definitely_absent": self.definitely_absent,
            "resolved_entry_ids": self.resolved_entry_ids,
            "checked_surfaces": self.checked_surfaces,
            "matched_surfaces": self.matched_surfaces,
            "query_hashes": self.query_hashes,
        }


class BloomFilter:
    """A deterministic Bloom filter backed by a bytearray bitset."""

    def __init__(
        self, *, expected_items: int = 1000, false_positive_rate: float = 0.01
    ) -> None:
        """Document the responsibility of ``BloomFilter.__init__``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Initialize instance state while keeping constructor assumptions explicit for future maintainers.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        if expected_items <= 0:
            expected_items = 1
        if not 0 < false_positive_rate < 1:
            raise ValueError("false_positive_rate must be between 0 and 1.")
        bit_count = int(
            -(expected_items * math.log(false_positive_rate)) / (math.log(2) ** 2)
        )
        self.bit_count = max(64, bit_count)
        self.hash_count = max(1, int((self.bit_count / expected_items) * math.log(2)))
        self.bits = bytearray((self.bit_count + 7) // 8)
        self.item_count = 0

    def add(self, item: str) -> None:
        """Document the responsibility of ``BloomFilter.add``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Provide the local operation named ``BloomFilter.add`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        for index in self._indexes(item):
            self.bits[index // 8] |= 1 << (index % 8)
        self.item_count += 1

    def update(self, items: Iterable[str]) -> None:
        """Document the responsibility of ``BloomFilter.update``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Provide the local operation named ``BloomFilter.update`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        for item in items:
            self.add(item)

    def __contains__(self, item: str) -> bool:
        """Document the responsibility of ``BloomFilter.__contains__``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Provide the local operation named ``BloomFilter.__contains__`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        return all(
            self.bits[index // 8] & (1 << (index % 8)) for index in self._indexes(item)
        )

    def to_dict(self) -> dict[str, Any]:
        """Document the responsibility of ``BloomFilter.to_dict``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Provide the local operation named ``BloomFilter.to_dict`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        return {
            "bit_count": self.bit_count,
            "hash_count": self.hash_count,
            "item_count": self.item_count,
            "bits_base64": base64.b64encode(bytes(self.bits)).decode("ascii"),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "BloomFilter":
        """Document the responsibility of ``BloomFilter.from_dict``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Provide the local operation named ``BloomFilter.from_dict`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        obj = cls(expected_items=1)
        obj.bit_count = int(payload["bit_count"])
        obj.hash_count = int(payload["hash_count"])
        obj.item_count = int(payload.get("item_count", 0))
        obj.bits = bytearray(base64.b64decode(str(payload["bits_base64"])))
        return obj

    def save(self, path: Path) -> Path:
        """Document the responsibility of ``BloomFilter.save``.

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
        path.write_text(
            json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return path

    @classmethod
    def load(cls, path: Path) -> "BloomFilter":
        """Document the responsibility of ``BloomFilter.load``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Load data from the declared source while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def _indexes(self, item: str) -> Iterable[int]:
        """Document the responsibility of ``BloomFilter._indexes``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Provide the local operation named ``BloomFilter._indexes`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        encoded = item.encode("utf-8")
        for seed in range(self.hash_count):
            digest = hashlib.blake2b(
                encoded, digest_size=8, person=f"kb{seed:06d}".encode("ascii")
            ).digest()
            yield int.from_bytes(digest, "big") % self.bit_count


def build_bloom(
    items: Iterable[str], *, false_positive_rate: float = 0.01
) -> BloomFilter:
    """Document the responsibility of ``build_bloom``.

    Motivation:
        Make reusable mathematical facts searchable before they are trusted as proof premises.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    materialized = list(dict.fromkeys(item for item in items if item))
    bloom = BloomFilter(
        expected_items=max(1, len(materialized)),
        false_positive_rate=false_positive_rate,
    )
    bloom.update(materialized)
    return bloom
