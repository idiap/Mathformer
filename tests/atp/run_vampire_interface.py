#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402 - imports follow explicit direct-script path setup
#
#

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

"""Run a representative informal-math-to-Vampire proof discovery test."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backends.atp.MathformerATP.vampire import (
    discover_proof,
)

DEFAULT_STATEMENT = (
    "ProofWiki states that the subset relation is transitive: "
    "if R is a subset of S and S is a subset of T, then R is a subset of T."
)
SOURCE_URL = "https://proofwiki.org/wiki/Subset_Relation_is_Transitive"


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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=Path("artifacts/vampire_atp/subset_transitive_web"),
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    artifact_root = (
        REPO_ROOT / args.artifact_root
        if not args.artifact_root.is_absolute()
        else args.artifact_root
    )
    report = discover_proof(
        DEFAULT_STATEMENT,
        artifact_root=artifact_root,
        source_url=SOURCE_URL,
        time_limit=10,
    )
    formal_proof = report.get("winning_formal_proof") or ""
    informal_proof = report.get("winning_informal_proof") or {}
    informal_text = informal_proof.get("text", "")
    assertions = {
        "szs_proof_status": report["ok"],
        "formal_proof_present": "$false" in formal_proof,
        "informal_proof_present": bool(informal_proof.get("ok"))
        and "subset(r,t)" in informal_text,
        "formal_proof_path_present": bool(report.get("winning_formal_proof_path")),
        "informal_proof_path_present": bool(report.get("winning_informal_proof_path")),
    }
    report["test_assertions"] = assertions
    report["ok"] = all(assertions.values())
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"ok: {report['ok']}")
        print(f"winning_status: {report['winning_status']}")
        print(f"formal_proof_path: {report['winning_formal_proof_path']}")
        print(f"informal_proof_path: {report['winning_informal_proof_path']}")
        print(f"artifact_root: {artifact_root.relative_to(REPO_ROOT)}")
    return 0 if report["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
