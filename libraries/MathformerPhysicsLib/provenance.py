# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Content binding and staleness checks for physics release evidence."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def release_evidence_staleness(report: Mapping[str, Any], repo_root: Path) -> dict[str, Any]:
    mismatches: list[dict[str, Any]] = []
    root_path = repo_root / str(report.get("public_root") or "")
    expected_root = report.get("public_root_sha256")
    if not root_path.is_file() or not expected_root:
        mismatches.append({"code": "public_root_binding_missing", "path": str(root_path)})
    elif digest(root_path) != expected_root:
        mismatches.append({"code": "public_root_hash_changed", "path": str(root_path)})
    for row in report.get("imported_modules") or []:
        if not isinstance(row, Mapping):
            continue
        path = repo_root / str(row.get("path") or "")
        expected = row.get("sha256")
        if not path.is_file() or not expected:
            mismatches.append({"code": "module_binding_missing", "path": str(path)})
        elif digest(path) != expected:
            mismatches.append({"code": "module_hash_changed", "path": str(path)})
    return {
        "schema_version": 1,
        "style": "physics_release_evidence_staleness",
        "stale": bool(mismatches),
        "ok": not mismatches,
        "mismatches": mismatches,
    }
