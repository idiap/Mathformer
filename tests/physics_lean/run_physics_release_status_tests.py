#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402 - imports follow explicit direct-script path setup
#
#

"""Adversarial tests for shared physics release-status semantics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from libraries.MathformerPhysicsLib.release_status import (
    build_release_status,
    validate_release_status,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    accepted = build_release_status(
        workflow_executed=True,
        checks_passed=True,
        artifact_status="promoted",
        library_status="accepted",
    )
    recurse = build_release_status(
        workflow_executed=True,
        checks_passed=True,
        artifact_status="promoted",
        library_status="accepted",
        terminal_states=["recurse"],
    )
    diagnostic_blocker = build_release_status(
        workflow_executed=True,
        checks_passed=True,
        artifact_status="candidate",
        library_status="blocked",
        blockers=["coherence"],
        terminal_states=["complete_with_blockers"],
    )
    contradictory = dict(recurse)
    contradictory["release_ok"] = True
    cases = {
        "accepted_can_release": accepted["release_ok"] is True,
        "recurse_cannot_release": recurse["release_ok"] is False,
        "diagnostic_can_succeed_while_release_blocked": diagnostic_blocker[
            "checks_passed"
        ]
        is True
        and diagnostic_blocker["release_ok"] is False,
        "contradiction_rejected": bool(validate_release_status(contradictory)),
    }
    payload = {
        "schema_version": 1,
        "suite": "physics_release_status",
        "ok": all(cases.values()),
        "cases": cases,
    }
    print(
        json.dumps(payload, indent=2, sort_keys=True)
        if args.json
        else ("PASS" if payload["ok"] else "FAIL")
    )
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
