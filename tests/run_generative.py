#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.
#
# Intent:
#   Encode regression checks that catch parser breakage, semantic drift, and missing workflow evidence.
#
# Function:
#   Contains executable tests, fixtures, and manifests used for local and CI validation.
#
# Maintenance Notes:
#   Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.

"""Validate generative quality probes and optionally prepare Codex-exec jobs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import time
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "test_program" / "generative"
CRITERIA = REPO_ROOT / "tests" / "generative" / "quality_criteria.json"
PROBES = REPO_ROOT / "tests" / "generative" / "probes" / "probes.json"


def load_json(path: Path) -> Dict[str, Any]:
    """Document the responsibility of ``load_json``.

    Motivation:
        Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return json.loads(path.read_text(encoding="utf-8"))


def validate() -> Dict[str, Any]:
    """Document the responsibility of ``validate``.

    Motivation:
        Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.

    Intent:
        Validate assumptions or artifacts and return explicit evidence about whether the contract holds.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    state = prepare_validation()
    while state["has_more"]:
        state = inspect_probe(state)
    return build_report(state)


def prepare_validation(repository_root: Path | None = None) -> Dict[str, Any]:
    """Load fixed inputs once, in native order, and expose the probe cursor."""
    criteria = load_json(
        CRITERIA
        if repository_root is None
        else repository_root / "tests/generative/quality_criteria.json"
    )
    probes = load_json(
        PROBES
        if repository_root is None
        else repository_root / "tests/generative/probes/probes.json"
    )
    required = set(criteria["required_fields"])
    rows = probes.get("probes", [])
    return dict(
        required_fields=list(required),
        probes=rows,
        index=0,
        errors=[],
        has_more=bool(rows),
    )


def inspect_probe(state: Dict[str, Any]) -> Dict[str, Any]:
    """Consume one probe; both independent failures accumulate in source order."""
    probe = state["probes"][state["index"]]
    required = set(state["required_fields"])
    errors = state["errors"]
    missing = sorted(required - set(probe))
    if missing:
        errors.append(
            f"{probe.get('probe_id', '<missing-id>')} missing {', '.join(missing)}"
        )
    if not probe.get("forbidden_claims"):
        errors.append(
            f"{probe.get('probe_id', '<missing-id>')} has no forbidden claims"
        )
    state["index"] += 1
    state["has_more"] = state["index"] < len(state["probes"])
    return state


def build_report(state: Dict[str, Any]) -> Dict[str, Any]:
    """Finalize the native report after traversal (timestamp belongs here)."""
    return {
        "run_id": f"generative-probes-{int(time.time())}",
        "ok": not state["errors"],
        "criteria_file": str(CRITERIA.relative_to(REPO_ROOT)),
        "probes_file": str(PROBES.relative_to(REPO_ROOT)),
        "probe_count": len(state["probes"]),
        "errors": state["errors"],
        "mode": "validate-only",
        "codex_exec_policy": "Probe execution is content-generative and should write raw outputs plus deterministic rubric scores before promotion to regressions.",
    }


def main() -> int:
    """Document the responsibility of ``main``.

    Motivation:
        Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.

    Intent:
        Serve as the command-line entry point and coordinate argument parsing, execution, and reporting.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    args = parse_args()
    report = validate()
    return publish_report(report, args.json)


def parse_args(argv=None):
    """Preserve argparse exits and the ignored --validate-only option."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def publish_report(report, json_output, repository_root: Path | None = None):
    """Write and print the native report, returning its native exit code."""
    artifact_root = (
        ARTIFACT_ROOT
        if repository_root is None
        else repository_root / "artifacts/test_program/generative"
    )
    artifact_root.mkdir(parents=True, exist_ok=True)
    output = artifact_root / "probe_validation_report.json"
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"ok: {report['ok']}")
        print(f"probes: {report['probe_count']}")
        for error in report["errors"]:
            print(f"- {error}")
    return 0 if report["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
