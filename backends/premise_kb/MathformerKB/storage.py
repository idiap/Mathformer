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

"""JSONL storage for the Mathformer premise KB."""

from __future__ import annotations

from typing import Any

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable

from .canonicalize import populate_canonical_fields
from .schema import CURATION_STATUSES, KBEntry, ProvenanceRecord


@dataclass(frozen=True)
class AddResult:
    """Document the responsibility of ``AddResult``.

    Motivation:
        Make reusable mathematical facts searchable before they are trusted as proof premises.

    Intent:
        Group related state and behavior so callers can use this part of the MathformerKB workflow through a clear object boundary.

    Function:
        Defines storage, ingestion, indexing, and search behavior for the local premise knowledge base.

    Maintenance:
        Keep the class contract explicit when adding fields, constructor requirements, or externally visible methods.
    """

    added: bool
    entry_id: str
    duplicate_of: str | None = None
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Document the responsibility of ``AddResult.to_dict``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Provide the local operation named ``AddResult.to_dict`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        return {
            "added": self.added,
            "entry_id": self.entry_id,
            "duplicate_of": self.duplicate_of,
            "reason": self.reason,
        }


class KBStore:
    """Append-friendly JSONL store with small rewrite-based curation updates."""

    def __init__(self, root: Path) -> None:
        """Document the responsibility of ``KBStore.__init__``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Initialize instance state while keeping constructor assumptions explicit for future maintainers.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        self.root = root
        self.entries_path = root / "entries.jsonl"
        self.rejected_path = root / "rejected.jsonl"
        self.curation_queue_path = root / "curation_queue.jsonl"
        self.curation_log_path = root / "curation_log.jsonl"
        self.report_dir = root / "reports"
        self.bloom_dir = root / "bloom"
        self.embedding_dir = root / "embeddings"

    def init(self) -> None:
        """Document the responsibility of ``KBStore.init``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Provide the local operation named ``KBStore.init`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        self.root.mkdir(parents=True, exist_ok=True)
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.bloom_dir.mkdir(parents=True, exist_ok=True)
        self.embedding_dir.mkdir(parents=True, exist_ok=True)
        for path in [
            self.entries_path,
            self.rejected_path,
            self.curation_queue_path,
            self.curation_log_path,
        ]:
            path.touch(exist_ok=True)

    def read_entries(self, *, include_rejected: bool = False) -> list[KBEntry]:
        """Document the responsibility of ``KBStore.read_entries``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Load data from the declared source while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        entries = self._read_jsonl_entries(self.entries_path)
        if include_rejected:
            entries.extend(self._read_jsonl_entries(self.rejected_path))
        return entries

    def add_entry(self, entry: KBEntry, *, allow_duplicate: bool = False) -> AddResult:
        """Document the responsibility of ``KBStore.add_entry``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Provide the local operation named ``KBStore.add_entry`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        self.init()
        entry = populate_canonical_fields(entry)
        if not allow_duplicate:
            duplicate = self.find_duplicate(entry)
            if duplicate:
                return AddResult(
                    added=False,
                    entry_id=entry.id,
                    duplicate_of=duplicate.id,
                    reason="canonical hash already exists",
                )
        target = self.rejected_path if entry.status == "rejected" else self.entries_path
        with target.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(entry.to_dict(), ensure_ascii=False, sort_keys=True) + "\n"
            )
        self._log("add_entry", entry.id, {"status": entry.status})
        return AddResult(added=True, entry_id=entry.id)

    def add_entries(
        self, entries: Iterable[KBEntry], *, allow_duplicate: bool = False
    ) -> list[AddResult]:
        """Document the responsibility of ``KBStore.add_entries``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Provide the local operation named ``KBStore.add_entries`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        return [
            self.add_entry(entry, allow_duplicate=allow_duplicate) for entry in entries
        ]

    def find_duplicate(self, entry: KBEntry) -> KBEntry | None:
        """Document the responsibility of ``KBStore.find_duplicate``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Search available candidates and return the matches needed by the caller.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        hashes = _strong_duplicate_hashes(populate_canonical_fields(entry))
        for existing in self.read_entries(include_rejected=True):
            if hashes & _strong_duplicate_hashes(existing):
                return existing
        return None

    def find_by_id(
        self, entry_id: str, *, include_rejected: bool = False
    ) -> KBEntry | None:
        """Document the responsibility of ``KBStore.find_by_id``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Search available candidates and return the matches needed by the caller.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        for entry in self.read_entries(include_rejected=include_rejected):
            if entry.id == entry_id:
                return entry
        return None

    def hash_index(
        self, *, surface: str | None = None, include_rejected: bool = False
    ) -> dict[str, list[str]]:
        """Document the responsibility of ``KBStore.hash_index``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Provide the local operation named ``KBStore.hash_index`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        index: dict[str, list[str]] = {}
        for entry in self.read_entries(include_rejected=include_rejected):
            for key, value in entry.canonical_hashes.items():
                if surface is not None and key != surface:
                    continue
                index.setdefault(value, []).append(entry.id)
        return index

    def enqueue_for_review(self, entry: KBEntry, *, reason: str) -> None:
        """Document the responsibility of ``KBStore.enqueue_for_review``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Provide the local operation named ``KBStore.enqueue_for_review`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        self.init()
        entry = populate_canonical_fields(entry)
        payload = {"reason": reason, "entry": entry.to_dict()}
        with self.curation_queue_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        self._log("enqueue_for_review", entry.id, {"reason": reason})

    def update_status(
        self,
        entry_id: str,
        status: str,
        *,
        provenance: ProvenanceRecord | None = None,
        notes: str | None = None,
    ) -> KBEntry:
        """Document the responsibility of ``KBStore.update_status``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Provide the local operation named ``KBStore.update_status`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        if status not in CURATION_STATUSES:
            raise ValueError(f"Unknown curation status {status!r}.")
        entries = self.read_entries()
        updated: KBEntry | None = None
        kept: list[KBEntry] = []
        for entry in entries:
            if entry.id == entry_id:
                if status == "proved_formal" and not _has_proof_evidence(entry):
                    raise ValueError(
                        f"Cannot promote {entry_id!r} to proved_formal without a formal surface and proof artifact."
                    )
                entry.status = status
                if provenance:
                    entry.provenance.append(provenance)
                if notes:
                    entry.notes = notes
                updated = entry
            else:
                kept.append(entry)
        if updated is None:
            raise KeyError(f"No KB entry with id {entry_id!r}.")
        if status == "rejected":
            self._write_entries(self.entries_path, kept)
            with self.rejected_path.open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(updated.to_dict(), ensure_ascii=False, sort_keys=True)
                    + "\n"
                )
        else:
            self._write_entries(self.entries_path, kept + [updated])
        self._log("update_status", entry_id, {"status": status, "notes": notes})
        return updated

    def report(self) -> dict[str, Any]:
        """Document the responsibility of ``KBStore.report``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Provide the local operation named ``KBStore.report`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        entries = self.read_entries()
        rejected = self._read_jsonl_entries(self.rejected_path)
        by_status: dict[str, int] = {}
        by_domain: dict[str, int] = {}
        for entry in entries + rejected:
            by_status[entry.status] = by_status.get(entry.status, 0) + 1
            for tag in entry.domain_tags:
                by_domain[tag] = by_domain.get(tag, 0) + 1
        return {
            "root": str(self.root),
            "entry_count": len(entries),
            "rejected_count": len(rejected),
            "by_status": dict(sorted(by_status.items())),
            "by_domain": dict(sorted(by_domain.items())),
        }

    def refresh_canonical_hashes(self) -> dict[str, int]:
        """Document the responsibility of ``KBStore.refresh_canonical_hashes``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Provide the local operation named ``KBStore.refresh_canonical_hashes`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        self.init()
        entries = [populate_canonical_fields(entry) for entry in self.read_entries()]
        rejected = [
            populate_canonical_fields(entry)
            for entry in self._read_jsonl_entries(self.rejected_path)
        ]
        self._write_entries(self.entries_path, entries)
        self._write_entries(self.rejected_path, rejected)
        self._log(
            "refresh_canonical_hashes",
            "__all__",
            {"entry_count": len(entries), "rejected_count": len(rejected)},
        )
        return {"entry_count": len(entries), "rejected_count": len(rejected)}

    def _log(self, action: str, entry_id: str, payload: dict[str, Any]) -> None:
        """Document the responsibility of ``KBStore._log``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Provide the local operation named ``KBStore._log`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        self.init()
        record = {"action": action, "entry_id": entry_id, **payload}
        with self.curation_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    @staticmethod
    def _read_jsonl_entries(path: Path) -> list[KBEntry]:
        """Document the responsibility of ``KBStore._read_jsonl_entries``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Load data from the declared source while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        if not path.exists():
            return []
        entries: list[KBEntry] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entries.append(KBEntry.from_dict(json.loads(line)))
        return entries

    @staticmethod
    def _write_entries(path: Path, entries: list[KBEntry]) -> None:
        """Document the responsibility of ``KBStore._write_entries``.

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
            "".join(
                json.dumps(entry.to_dict(), ensure_ascii=False, sort_keys=True) + "\n"
                for entry in entries
            ),
            encoding="utf-8",
        )


def _has_proof_evidence(entry: KBEntry) -> bool:
    """Document the responsibility of ``_has_proof_evidence``.

    Motivation:
        Make reusable mathematical facts searchable before they are trusted as proof premises.

    Intent:
        Provide the local operation named ``_has_proof_evidence`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return any(
        surface.statement and surface.proof_artifact
        for surface in entry.formal_statements
    )


def _strong_duplicate_hashes(entry: KBEntry) -> set[str]:
    """Document the responsibility of ``_strong_duplicate_hashes``.

    Motivation:
        Make reusable mathematical facts searchable before they are trusted as proof premises.

    Intent:
        Provide the local operation named ``_strong_duplicate_hashes`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    strong_surfaces = {
        surface
        for surface in entry.canonical_hashes
        if surface in {"informal", "latex"} or surface.startswith("formal_")
    }
    return {entry.canonical_hashes[surface] for surface in strong_surfaces}
