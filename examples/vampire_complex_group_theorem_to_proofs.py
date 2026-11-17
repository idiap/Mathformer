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
#   Give users concrete starting points for running Mathformer workflows on small theorem tasks.
#
# Intent:
#   Show how informal inputs, ATP candidates, premise selection, and proof artifacts connect in practice.
#
# Function:
#   Contains runnable or readable examples that double as smoke-test material for documentation.
#
# Maintenance Notes:
#   Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.

"""Demo: informal group theorem -> Vampire formal proof + informal proof."""

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backends.atp.MathformerATP.vampire import (
    discover_proof,
)

INPUT_PATH = REPO_ROOT / "examples" / "vampire_group_inverse_product_input.md"
ARTIFACT_ROOT = (
    REPO_ROOT / "artifacts" / "vampire_atp" / "group_inverse_product_example"
)


def proof_excerpt(proof: str, *, max_lines: int = 22) -> str:
    """Document the responsibility of ``proof_excerpt``.

    Motivation:
        Give users concrete starting points for running Mathformer workflows on small theorem tasks.

    Intent:
        Provide the local operation named ``proof_excerpt`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    lines = proof.strip().splitlines()
    if len(lines) <= max_lines:
        return proof.strip()
    return "\n".join(lines[:max_lines] + ["..."])


def main() -> int:
    """Document the responsibility of ``main``.

    Motivation:
        Give users concrete starting points for running Mathformer workflows on small theorem tasks.

    Intent:
        Serve as the command-line entry point and coordinate argument parsing, execution, and reporting.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    statement = INPUT_PATH.read_text(encoding="utf-8")
    report = discover_proof(statement, artifact_root=ARTIFACT_ROOT, time_limit=10)
    return 0 if print_and_check(statement, report) else 3


def print_and_check(statement: str, report: dict) -> bool:
    """Print native proof evidence and evaluate the example acceptance predicate."""
    informal_proof = report["winning_informal_proof"]
    formal_proof = report["winning_formal_proof"] or ""

    print("Informal input:")
    print(statement.strip())
    print()
    print(f"Proof status: {report['winning_status']}")
    print(f"Formal proof path: {report['winning_formal_proof_path']}")
    print(f"Informal proof path: {report['winning_informal_proof_path']}")
    print()
    print("Formal proof excerpt:")
    print(proof_excerpt(formal_proof))
    print()
    print("Informal proof:")
    print(informal_proof["text"].strip())
    return bool(report["ok"] and informal_proof["ok"] and "$false" in formal_proof)


if __name__ == "__main__":
    raise SystemExit(main())
