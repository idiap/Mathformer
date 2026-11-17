#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Validate the machine-readable reasoning-log index."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parents[4]
REQUIRED_FIELDS = {
    "run_id",
    "skill",
    "hook_id",
    "log_file",
    "created_at_utc",
    "status",
    "event_count",
    "validation_status",
    "quality_status",
    "reports",
}


def resolve_repo_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else REPO_ROOT / path


def load_index(index: Path) -> Dict[str, Any]:
    """Load once, retaining the native early reports and decoding exceptions."""
    findings: List[Dict[str, Any]] = []
    if not index.exists():
        return {
            "schema_version": 1,
            "style": "reasoning_log_index_validation",
            "ok": False,
            "index": str(index),
            "findings": [
                {
                    "severity": "high",
                    "code": "index_missing",
                    "message": f"Index not found: {index}",
                }
            ],
        }
    try:
        payload = json.loads(index.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {
            "schema_version": 1,
            "style": "reasoning_log_index_validation",
            "ok": False,
            "index": str(index),
            "findings": [
                {"severity": "high", "code": "invalid_json", "message": exc.msg}
            ],
        }
    entries = payload.get("entries")
    if not isinstance(entries, list):
        findings.append(
            {
                "severity": "high",
                "code": "entries_not_list",
                "message": "entries must be a list.",
            }
        )
        entries = []
    return {
        "index": str(index),
        "entries": entries,
        "offset": 0,
        "findings": findings,
        "terminal_report": None,
    }


def load_initialize(index: Path) -> Dict[str, Any]:
    loaded = load_index(index)
    if "terminal_report" not in loaded:
        loaded = {
            "index": str(index),
            "entries": [],
            "offset": 0,
            "findings": [],
            "terminal_report": loaded,
        }
    return {"state": loaded, "scan": bool(loaded["entries"])}


def validate_entry(entry: Any, offset: int, findings: List[Dict[str, Any]]) -> None:
    """One native enumeration body, including the non-object short circuit."""
    if not isinstance(entry, dict):
        findings.append(
            {"severity": "high", "code": "entry_not_object", "entry_offset": offset}
        )
        return
    missing = sorted(field for field in REQUIRED_FIELDS if field not in entry)
    if missing:
        findings.append(
            {
                "severity": "high",
                "code": "entry_missing_fields",
                "entry_offset": offset,
                "missing": missing,
            }
        )
    log_file = entry.get("log_file")
    if isinstance(log_file, str):
        resolved = resolve_repo_path(log_file)
        try:
            resolved.relative_to(REPO_ROOT / "artifacts")
        except ValueError:
            findings.append(
                {
                    "severity": "high",
                    "code": "log_file_outside_artifacts",
                    "entry_offset": offset,
                    "log_file": log_file,
                }
            )
        if not resolved.exists():
            findings.append(
                {
                    "severity": "high",
                    "code": "log_file_missing",
                    "entry_offset": offset,
                    "log_file": log_file,
                }
            )
    event_count = entry.get("event_count")
    if not isinstance(event_count, int) or event_count < 0:
        findings.append(
            {
                "severity": "high",
                "code": "invalid_event_count",
                "entry_offset": offset,
            }
        )
    for status_field in ("validation_status", "quality_status"):
        if entry.get(status_field) not in {"pass", "fail", "unknown"}:
            findings.append(
                {
                    "severity": "high",
                    "code": "invalid_status",
                    "entry_offset": offset,
                    "field": status_field,
                }
            )


def validate_entry_advance(state: Dict[str, Any]) -> Dict[str, Any]:
    validate_entry(
        state["entries"][state["offset"]], state["offset"], state["findings"]
    )
    state["offset"] += 1
    return {"state": state, "done": state["offset"] == len(state["entries"])}


def finalize(state: Dict[str, Any]) -> Dict[str, Any]:
    if state["terminal_report"] is not None:
        return state["terminal_report"]
    findings, entries, index = state["findings"], state["entries"], state["index"]
    blocking = [item for item in findings if item["severity"] == "high"]
    return {
        "schema_version": 1,
        "style": "reasoning_log_index_validation",
        "ok": not blocking,
        "index": str(index),
        "entry_count": len(entries),
        "findings": findings,
    }


def validate_index(index: Path) -> Dict[str, Any]:
    loaded = load_initialize(index)
    state = loaded["state"]
    while state["offset"] < len(state["entries"]):
        state = validate_entry_advance(state)["state"]
    return finalize(state)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--index",
        type=Path,
        default=REPO_ROOT / "artifacts" / "reasoning" / "index.json",
    )
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    report = validate_index(args.index)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"ok: {report['ok']}")
        print(f"entries: {report.get('entry_count', 0)}")
    return 0 if report["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
