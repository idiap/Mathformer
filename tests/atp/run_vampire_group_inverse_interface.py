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

"""Run the group inverse-of-product Vampire proof test."""

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
    "Let G be a group with multiplication mul, identity element e, and inverse operation inv. "
    "Prove that for all elements x and y of G, the inverse of the product mul(x,y) "
    "is the product of the inverses in reverse order: inv(mul(x,y)) = mul(inv(y),inv(x))."
)


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
        default=Path("artifacts/vampire_atp/group_inverse_product_test"),
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    artifact_root = (
        REPO_ROOT / args.artifact_root
        if not args.artifact_root.is_absolute()
        else args.artifact_root
    )
    report = discover_proof(
        DEFAULT_STATEMENT, artifact_root=artifact_root, time_limit=10
    )
    formal_proof = report.get("winning_formal_proof") or ""
    informal_proof = report.get("winning_informal_proof") or {}
    informal_text = informal_proof.get("text", "")
    assertions = {
        "szs_proof_status": report["ok"],
        "group_problem_selected": report.get("winner", {}).get("problem_id")
        == "group_inverse_of_product_reverses_order",
        "formal_proof_present": "$false" in formal_proof,
        "formal_uses_equality": "inv(mul" in formal_proof and "mul(inv" in formal_proof,
        "informal_proof_present": bool(informal_proof.get("ok"))
        and "two-sided inverse" in informal_text,
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
