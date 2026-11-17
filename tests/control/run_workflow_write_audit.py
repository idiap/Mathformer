#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402 - imports follow explicit direct-script path setup
#
#

"""Exercise the controlled-workflow write auditor with adversarial fixtures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.workflow_write_audit import (
    audit_snapshots,
    snapshot_repository,
)


def run_self_test() -> dict[str, object]:
    cases: list[dict[str, object]] = []
    with TemporaryDirectory(prefix="mathformer-write-audit-") as directory:
        root = Path(directory)
        (root / "artifacts" / "expected").mkdir(parents=True)

        before = snapshot_repository(root)
        (root / "unexpected.txt").write_text("violation\n", encoding="utf-8")
        after = snapshot_repository(root)
        read_only = audit_snapshots(
            before,
            after,
            action_id="fixture:read-only",
            safety="read_only",
            declared_roots=(),
        )
        cases.append(
            {
                "id": "read_only_rejects_write",
                "ok": read_only["ok"] is False
                and read_only["unexpected_paths"] == ["unexpected.txt"],
                "audit": read_only,
            }
        )

        before = snapshot_repository(root)
        (root / "artifacts" / "expected" / "report.json").write_text(
            "{}\n", encoding="utf-8"
        )
        after = snapshot_repository(root)
        allowed = audit_snapshots(
            before,
            after,
            action_id="fixture:artifact",
            safety="writes_artifacts",
            declared_roots=("artifacts/expected/",),
        )
        cases.append(
            {
                "id": "artifact_root_allows_nested_write",
                "ok": allowed["ok"] is True
                and allowed["declared_paths"] == ["artifacts/expected/report.json"],
                "audit": allowed,
            }
        )

        before = snapshot_repository(root)
        (root / "outside.json").write_text("{}\n", encoding="utf-8")
        after = snapshot_repository(root)
        artifact_violation = audit_snapshots(
            before,
            after,
            action_id="fixture:artifact-violation",
            safety="writes_artifacts",
            declared_roots=("artifacts/expected/",),
        )
        cases.append(
            {
                "id": "artifact_root_rejects_external_write",
                "ok": artifact_violation["ok"] is False
                and artifact_violation["unexpected_paths"] == ["outside.json"],
                "audit": artifact_violation,
            }
        )

        before = snapshot_repository(root)
        existing = root / "already-dirty.txt"
        existing.write_text("before\n", encoding="utf-8")
        dirty_baseline = snapshot_repository(root)
        existing.write_text("after\n", encoding="utf-8")
        dirty_after = snapshot_repository(root)
        dirty = audit_snapshots(
            dirty_baseline,
            dirty_after,
            action_id="fixture:dirty-baseline",
            safety="read_only",
            declared_roots=(),
        )
        cases.append(
            {
                "id": "already_dirty_content_change_is_detected",
                "ok": dirty["ok"] is False
                and dirty["unexpected_paths"] == ["already-dirty.txt"],
                "audit": dirty,
                "initial_snapshot_was_clean": "already-dirty.txt" not in before,
            }
        )

    return {
        "schema_version": 1,
        "suite": "workflow_write_audit",
        "ok": all(case["ok"] for case in cases),
        "cases": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    payload = run_self_test()
    print(
        json.dumps(payload, indent=2, sort_keys=True)
        if args.json
        else ("PASS" if payload["ok"] else "FAIL")
    )
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
