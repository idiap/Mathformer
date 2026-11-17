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

"""Schema objects for the Mathformer premise knowledge base."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

CURATION_STATUSES = {
    "generated_candidate",
    "source_backed_candidate",
    "reviewed_informal",
    "formal_candidate",
    "proved_formal",
    "rejected",
    "deprecated",
}

PROVENANCE_KINDS = {
    "generated",
    "web",
    "corpus",
    "local_artifact",
    "formal_library",
    "curation",
}

FORMAL_STATUSES = {
    "candidate",
    "checked",
    "proved",
    "rejected",
}


@dataclass(frozen=True)
class ProvenanceRecord:
    """Where a KB fact or surface came from."""

    kind: str
    source: str
    retrieved_at: str
    confidence: str = "medium"
    notes: str | None = None

    def __post_init__(self) -> None:
        """Document the responsibility of ``ProvenanceRecord.__post_init__``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Provide the local operation named ``ProvenanceRecord.__post_init__`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        if self.kind not in PROVENANCE_KINDS:
            raise ValueError(f"Unknown provenance kind {self.kind!r}.")

    def to_dict(self) -> dict[str, Any]:
        """Document the responsibility of ``ProvenanceRecord.to_dict``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Provide the local operation named ``ProvenanceRecord.to_dict`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ProvenanceRecord":
        """Document the responsibility of ``ProvenanceRecord.from_dict``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Provide the local operation named ``ProvenanceRecord.from_dict`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        return cls(**payload)


@dataclass(frozen=True)
class FormalSurface:
    """A formal statement surface attached to a KB entry."""

    system: str
    statement: str
    status: str = "candidate"
    proof_artifact: str | None = None
    source_artifact: str | None = None

    def __post_init__(self) -> None:
        """Document the responsibility of ``FormalSurface.__post_init__``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Provide the local operation named ``FormalSurface.__post_init__`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        if self.status not in FORMAL_STATUSES:
            raise ValueError(f"Unknown formal status {self.status!r}.")

    def to_dict(self) -> dict[str, Any]:
        """Document the responsibility of ``FormalSurface.to_dict``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Provide the local operation named ``FormalSurface.to_dict`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "FormalSurface":
        """Document the responsibility of ``FormalSurface.from_dict``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Provide the local operation named ``FormalSurface.from_dict`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        return cls(**payload)


@dataclass
class KBEntry:
    """One logical mathematical fact with informal and formal surfaces."""

    id: str
    status: str
    domain_tags: list[str]
    informal_statement: str
    latex_statement: str | None = None
    formal_statements: list[FormalSurface] = field(default_factory=list)
    symbols: list[str] = field(default_factory=list)
    theorem_shape: list[str] = field(default_factory=list)
    provenance: list[ProvenanceRecord] = field(default_factory=list)
    canonical_hashes: dict[str, str] = field(default_factory=dict)
    notes: str | None = None

    def __post_init__(self) -> None:
        """Document the responsibility of ``KBEntry.__post_init__``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Provide the local operation named ``KBEntry.__post_init__`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        if self.status not in CURATION_STATUSES:
            raise ValueError(f"Unknown curation status {self.status!r}.")
        self.domain_tags = sorted(dict.fromkeys(self.domain_tags))
        self.symbols = sorted(dict.fromkeys(self.symbols))
        self.theorem_shape = sorted(dict.fromkeys(self.theorem_shape))

    def to_dict(self) -> dict[str, Any]:
        """Document the responsibility of ``KBEntry.to_dict``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Provide the local operation named ``KBEntry.to_dict`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        return {
            "id": self.id,
            "status": self.status,
            "domain_tags": self.domain_tags,
            "informal_statement": self.informal_statement,
            "latex_statement": self.latex_statement,
            "formal_statements": [
                surface.to_dict() for surface in self.formal_statements
            ],
            "symbols": self.symbols,
            "theorem_shape": self.theorem_shape,
            "provenance": [record.to_dict() for record in self.provenance],
            "canonical_hashes": self.canonical_hashes,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "KBEntry":
        """Document the responsibility of ``KBEntry.from_dict``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Provide the local operation named ``KBEntry.from_dict`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        return cls(
            id=payload["id"],
            status=payload["status"],
            domain_tags=list(payload.get("domain_tags", [])),
            informal_statement=payload["informal_statement"],
            latex_statement=payload.get("latex_statement"),
            formal_statements=[
                FormalSurface.from_dict(item)
                for item in payload.get("formal_statements", [])
            ],
            symbols=list(payload.get("symbols", [])),
            theorem_shape=list(payload.get("theorem_shape", [])),
            provenance=[
                ProvenanceRecord.from_dict(item)
                for item in payload.get("provenance", [])
            ],
            canonical_hashes=dict(payload.get("canonical_hashes", {})),
            notes=payload.get("notes"),
        )

    @property
    def is_proved(self) -> bool:
        """Document the responsibility of ``KBEntry.is_proved``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Provide the local operation named ``KBEntry.is_proved`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        return self.status == "proved_formal" or any(
            surface.status == "proved" for surface in self.formal_statements
        )
