#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402 - imports follow explicit direct-script path setup
#
#

"""Validate current release evidence and prove that artifact edits stale it."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
REPORT = REPO_ROOT / "artifacts/physics_lean/release_gate/report.json"

from libraries.MathformerPhysicsLib.provenance import (
    release_evidence_staleness,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = json.loads(REPORT.read_text(encoding="utf-8")) if REPORT.exists() else {}
    current = release_evidence_staleness(report, REPO_ROOT)
    with TemporaryDirectory(prefix="mathformer-release-staleness-") as directory:
        root = Path(directory)
        root_file = root / str(
            report.get("public_root") or "libraries/MathformerPhysicsLib.lean"
        )
        root_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO_ROOT / report["public_root"], root_file)
        for row in report.get("imported_modules") or []:
            destination = root / row["path"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO_ROOT / row["path"], destination)
        mutated = root / report["imported_modules"][0]["path"]
        mutated.write_text(
            mutated.read_text(encoding="utf-8") + "\n-- mutation fixture\n",
            encoding="utf-8",
        )
        stale = release_evidence_staleness(report, root)
    cases = {
        "current_release_evidence_fresh": current["ok"] is True,
        "artifact_mutation_invalidates_report": stale["stale"] is True
        and any(item["code"] == "module_hash_changed" for item in stale["mismatches"]),
    }
    payload = {
        "schema_version": 1,
        "suite": "physics_release_evidence_staleness",
        "ok": all(cases.values()),
        "cases": cases,
        "current": current,
        "mutated": stale,
    }
    print(
        json.dumps(payload, indent=2, sort_keys=True)
        if args.json
        else ("PASS" if payload["ok"] else "FAIL")
    )
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
