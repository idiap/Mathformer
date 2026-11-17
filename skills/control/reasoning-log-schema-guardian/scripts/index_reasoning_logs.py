#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402 - imports follow explicit direct-script path setup
#
#

"""Create a stable index of repository reasoning-log artifacts."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[4]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from audit_reasoning_log_quality import (
    audit_logs,
    write_self_test_fixtures,
)  # noqa: E402
from summarize_reasoning_log import summarize  # noqa: E402
from validate_reasoning_log import validate_reasoning_log  # noqa: E402


def repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def discover_logs(root: Path) -> List[Path]:
    if not root.exists():
        return []
    logs = [
        path
        for path in root.rglob("*.jsonl")
        if "reasoning" in path.name.lower()
        or "reasoning" in path.parent.as_posix().lower()
    ]
    return sorted(
        path
        for path in logs
        if path.is_file()
        and "bad" not in path.name.lower()
        and "adversarial" not in path.parent.as_posix().lower()
    )


def initialize_index(*, log_files, hooks_file, output_file):
    summary_dir = output_file.parent / "summaries"
    summary_dir.mkdir(parents=True, exist_ok=True)
    return {
        "logs": [str(p) for p in log_files],
        "position": 0,
        "entries": [],
        "hooks_file": str(hooks_file),
        "output_file": str(output_file),
        "summary_dir": str(summary_dir),
    }


def index_next_log(state):
    """One native for-body; validation failures remain entry data."""
    entries = state["entries"]
    hooks_file = Path(state["hooks_file"])
    summary_dir = Path(state["summary_dir"])
    if state["position"] < len(state["logs"]):
        log_file = Path(state["logs"][state["position"]])
        validation = validate_reasoning_log(
            log_file, hooks_file=hooks_file, strict=True
        )
        quality = audit_logs([log_file], hooks_file=hooks_file)
        summary = summarize(log_file, hooks_file=hooks_file)
        summary_file = (
            summary_dir / f"{log_file.stem}-{sha256(log_file)[:10]}.summary.json"
        )
        summary_file.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        entries.append(
            {
                "run_id": summary.get("run_id")
                or (summary.get("run_ids") or [None])[0],
                "skill": (summary.get("skills") or [None])[0],
                "hook_id": (summary.get("hooks") or [None])[0],
                "log_file": repo_rel(log_file),
                "log_sha256": sha256(log_file),
                "created_at_utc": datetime.fromtimestamp(
                    log_file.stat().st_mtime, tz=timezone.utc
                ).isoformat(),
                "status": "ok" if summary.get("ok") else "needs_attention",
                "event_count": summary.get("event_count", 0),
                "validation_status": "pass" if validation.get("ok") else "fail",
                "quality_status": "pass" if quality.get("ok") else "fail",
                "reports": {
                    "summary_json": repo_rel(summary_file),
                },
            }
        )
        state["position"] += 1
    return state


def write_index(state):
    entries = state["entries"]
    output_file = Path(state["output_file"])
    payload = {
        "schema_version": 1,
        "style": "reasoning_log_index",
        "ok": all(
            entry["validation_status"] == "pass" and entry["quality_status"] == "pass"
            for entry in entries
        ),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "index_file": repo_rel(output_file),
        "log_count": len(entries),
        "entries": entries,
    }
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def build_index(
    *, log_files: Sequence[Path], hooks_file: Path, output_file: Path
) -> Dict[str, Any]:
    state = initialize_index(
        log_files=log_files, hooks_file=hooks_file, output_file=output_file
    )
    while state["position"] < len(state["logs"]):
        index_next_log(state)
    return write_index(state)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT / "artifacts")
    parser.add_argument("--log-file", action="append", type=Path, default=[])
    parser.add_argument(
        "--hooks-file", type=Path, default=REPO_ROOT / "skills" / "SKILL_HOOKS.yaml"
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=REPO_ROOT / "artifacts" / "reasoning" / "index.json",
    )
    parser.add_argument("--ensure-fixtures", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    if args.ensure_fixtures:
        write_self_test_fixtures()
    log_files = list(args.log_file) if args.log_file else discover_logs(args.root)
    report = build_index(
        log_files=log_files, hooks_file=args.hooks_file, output_file=args.output_file
    )
    return emit_report(report, json_output=args.json)


def emit_report(report, *, json_output):
    if json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"indexed reasoning logs: {report['log_count']}")
        print(f"ok: {report['ok']}")
    return 0 if report["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
