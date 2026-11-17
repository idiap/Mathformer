#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Audit repository-visible writes made by one controlled workflow action.

The auditor compares content-aware snapshots instead of relying on ``git
status`` alone.  That matters in a dirty worktree: an action can modify a file
which was already modified before the action started, and the change must still
be attributed to that action.
"""

from __future__ import annotations

from typing import Any

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Dict, Iterable, Mapping, Sequence, Tuple

EXCLUDED_DIRECTORY_NAMES = {
    ".git",
    ".lake",
    ".venv",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "node_modules",
}


@dataclass(frozen=True)
class FileState:
    """Stable content state used to compare a path across an action run."""

    size: int
    mtime_ns: int
    digest: str


Snapshot = Dict[str, FileState]


def _digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def snapshot_repository(repo_root: Path) -> Snapshot:
    """Return a content-aware snapshot excluding tool-managed cache trees."""

    snapshot: Snapshot = {}
    for path in repo_root.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(repo_root)
        if any(part in EXCLUDED_DIRECTORY_NAMES for part in relative.parts):
            continue
        try:
            stat = path.stat()
            # Generated artifact trees can be large and are never accepted as
            # source truth. Metadata is enough to attribute their writes,
            # while source/config/test files retain content hashing so edits
            # to an already-dirty same-size file remain detectable.
            digest = (
                ""
                if relative.parts and relative.parts[0] == "artifacts"
                else _digest(path)
            )
            snapshot[relative.as_posix()] = FileState(
                stat.st_size, stat.st_mtime_ns, digest
            )
        except FileNotFoundError:
            # Concurrent tools can remove a temporary file between discovery
            # and hashing.  Its stable state is represented by the next
            # snapshot rather than making the workflow itself fail.
            continue
    return snapshot


def changed_paths(
    before: Mapping[str, FileState], after: Mapping[str, FileState]
) -> Tuple[str, ...]:
    """Return added, removed, or content-modified paths."""

    paths = set(before) | set(after)
    return tuple(sorted(path for path in paths if before.get(path) != after.get(path)))


def _normalize_root(value: str) -> str:
    normalized = value.replace("\\", "/").lstrip("./")
    return normalized.rstrip("/")


def path_is_declared(path: str, declared_roots: Iterable[str]) -> bool:
    """Whether ``path`` is equal to or nested beneath a declared write root."""

    normalized_path = _normalize_root(path)
    for value in declared_roots:
        root = _normalize_root(value)
        if not root:
            continue
        if normalized_path == root or normalized_path.startswith(root + "/"):
            return True
    return False


def audit_snapshots(
    before: Mapping[str, FileState],
    after: Mapping[str, FileState],
    *,
    action_id: str,
    safety: str,
    declared_roots: Sequence[str],
) -> Dict[str, Any]:
    """Classify observed writes and expose a machine-readable contract result."""

    observed = changed_paths(before, after)
    declared = tuple(
        sorted(path for path in observed if path_is_declared(path, declared_roots))
    )
    unexpected = tuple(sorted(set(observed) - set(declared)))
    enforced = safety in {
        "read_only",
        "writes_artifacts",
        "writes_build_cache",
        "writes_environment",
        "writes_repo",
    }
    return {
        "schema_version": 1,
        "action_id": action_id,
        "safety": safety,
        "declared_roots": list(declared_roots),
        "observed_paths": list(observed),
        "declared_paths": list(declared),
        "unexpected_paths": list(unexpected),
        "enforced": enforced,
        "ok": not unexpected if enforced else True,
    }
