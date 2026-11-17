#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402 - imports follow explicit direct-script path setup
#
#

"""Calibrate concept reuse against an actual competing-owner fixture."""

from __future__ import annotations

from typing import Any

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_ROOT = (
    REPO_ROOT
    / "skills/mathformerphysicslib/mathformerphysicslib-coherence-inventory-builder/scripts"
)
sys.path.insert(0, str(SCRIPT_ROOT))

from coherence_common import (
    audit_grounding,
    canonicalize,
    critic_redefinitions,
)


def report_for(occurrences: list[dict[str, Any]]) -> dict[str, Any]:
    inventory = {
        "concept_occurrence_index": {"vector_field.real.euclidean3": occurrences},
        "foundations_index_exists": True,
        "manifest_has_foundations": True,
    }
    graph = canonicalize(inventory)
    return critic_redefinitions(graph, audit_grounding(graph))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    foundation = {
        "path": "libraries/MathformerPhysicsLib/Lean/Foundations/Fields.lean",
        "is_foundation": True,
        "imports_foundation": False,
        "ownership_declarations": [
            {
                "kind": "abbrev",
                "name": "RealVector3",
                "line": 12,
                "evidence": "abbrev RealVector3 := ...",
            }
        ],
    }
    healthy = report_for(
        [
            foundation,
            {
                "path": "libraries/MathformerPhysicsLib/Lean/formalphysics_0000/MathformerPhysics.lean",
                "is_foundation": False,
                "imports_foundation": True,
                "ownership_declarations": [],
                "occurrence_kind": "theorem_use",
            },
            {
                "path": "libraries/MathformerPhysicsLib/Lean/formalphysics_0020/MathformerPhysics.lean",
                "is_foundation": False,
                "imports_foundation": True,
                "ownership_declarations": [],
                "occurrence_kind": "hypothesis_or_term_use",
            },
        ]
    )
    duplicate = report_for(
        [
            foundation,
            {
                "path": "libraries/MathformerPhysicsLib/Lean/formalphysics_bad/MathformerPhysics.lean",
                "is_foundation": False,
                "imports_foundation": False,
                "ownership_declarations": [
                    {
                        "kind": "abbrev",
                        "name": "RealVector3",
                        "line": 7,
                        "evidence": "abbrev RealVector3 := ...",
                    }
                ],
                "occurrence_kind": "declaration",
            },
        ]
    )
    duplicate_findings = duplicate["findings"]
    cases = {
        "imported_downstream_use_is_healthy": healthy["finding_count"] == 0
        and healthy["reuse_metrics"]["healthy_downstream_uses"] == 2,
        "duplicate_owner_is_blocking": duplicate["ok"] is False
        and any(
            item["kind"] == "confirmed_competing_concept_owner"
            for item in duplicate_findings
        ),
        "duplicate_names_and_spans_reported": any(
            item.get("evidence", {}).get("exact_duplicate_names") == ["RealVector3"]
            and item.get("evidence", {})
            .get("downstream_declarations", [{}])[0]
            .get("line")
            == 7
            for item in duplicate_findings
        ),
    }
    payload = {
        "schema_version": 1,
        "suite": "mathformerphysicslib_redefinition_calibration",
        "ok": all(cases.values()),
        "cases": cases,
        "healthy": healthy,
        "duplicate": duplicate,
    }
    print(
        json.dumps(payload, indent=2, sort_keys=True)
        if args.json
        else ("PASS" if payload["ok"] else "FAIL")
    )
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
