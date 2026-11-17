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

"""Run the optional premise-guided triple product inverse proof regression."""

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
    "Prove that for all three elements x, y, and z of G, the inverse of the triple "
    "product mul(mul(x,y),z) is the product of the inverses in reverse order: "
    "inv(mul(mul(x,y),z)) = mul(inv(z),mul(inv(y),inv(x)))."
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
        default=Path("artifacts/vampire_atp/premise_guided_triple_inverse_test"),
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    artifact_root = (
        REPO_ROOT / args.artifact_root
        if not args.artifact_root.is_absolute()
        else args.artifact_root
    )
    report = discover_proof(
        DEFAULT_STATEMENT, artifact_root=artifact_root, time_limit=3, premise_loop=True
    )
    check_report(report)
    return emit_report(report, json_output=args.json)


def check_report(report):
    """Apply the native triple regression assertions in CLI and MCP execution."""
    attempt = report["attempts"][0]
    generation = attempt["premise_generation_report"]
    generated = {lemma["id"]: lemma for lemma in generation["generated_lemmas"]}
    final_ids = set(report["winning_final_premise_ids"])
    formal_proof = report.get("winning_formal_proof") or ""

    assertions = {
        "proof_found": report["ok"],
        "triple_problem_selected": report.get("winner", {}).get("problem_id")
        == "group_inverse_of_triple_product_reverses_order",
        "premise_loop_enabled": report["premise_loop"]["enabled"],
        "binary_helper_promoted": generation["promoted_ids"]
        == ["binary_product_inverse_reverse_order"],
        "unsafe_shortcut_rejected": generated["unsafe_group_commutativity_shortcut"][
            "proof_status"
        ]
        == "rejected",
        "final_minimized_to_binary_helper": final_ids
        == {"generated_binary_product_inverse_reverse_order"},
        "formal_proof_present": "$false" in formal_proof,
        "triple_goal_present": "inv(mul(mul" in formal_proof
        and "mul(inv" in formal_proof,
        "selection_report_written": Path(
            report["winning_premise_selection_report_path"]
        ).is_file(),
        "generation_report_written": Path(
            report["winning_premise_generation_report_path"]
        ).is_file(),
        "minimization_report_written": Path(
            report["winning_premise_minimization_report_path"]
        ).is_file(),
    }
    report["test_assertions"] = assertions
    report["ok"] = all(assertions.values())
    return report


def emit_report(report, *, json_output=True):
    """Print the native regression report and return its exit status."""
    if json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"ok: {report['ok']}")
        print(f"winning_status: {report['winning_status']}")
        print(f"final_premises: {', '.join(report['winning_final_premise_ids'])}")
        print(f"premise_selection: {report['winning_premise_selection_report_path']}")
        print(f"premise_generation: {report['winning_premise_generation_report_path']}")
        print(
            f"premise_minimization: {report['winning_premise_minimization_report_path']}"
        )
    return 0 if report["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
