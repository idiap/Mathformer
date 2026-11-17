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
#   Automate repository maintenance tasks that would be error-prone if performed by hand.
#
# Intent:
#   Expose command-line entry points for setup, generation, indexing, auditing, and proof execution.
#
# Function:
#   Implements operational glue used by tests, skills, docs, and developer workflows.
#
# Maintenance Notes:
#   Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.

"""Run Vampire ATP proof search on TPTP or informal Mathformer examples."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backends.atp.MathformerATP.vampire import (
    VampireRunner,
    discover_proof,
    read_text_argument,
)


def main() -> int:
    """Document the responsibility of ``main``.

    Motivation:
        Automate repository maintenance tasks that would be error-prone if performed by hand.

    Intent:
        Serve as the command-line entry point and coordinate argument parsing, execution, and reporting.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--problem", type=Path, help="Run Vampire on an existing TPTP problem."
    )
    mode.add_argument(
        "--text", help="Autoformalize this informal statement and run Vampire."
    )
    mode.add_argument(
        "--text-file", type=Path, help="Autoformalize an informal statement file."
    )
    parser.add_argument(
        "--source-url", help="Optional provenance URL for an informal statement."
    )
    parser.add_argument(
        "--artifact-root", type=Path, default=Path("artifacts/vampire_atp/manual")
    )
    parser.add_argument("--time-limit", type=int, default=10)
    parser.add_argument(
        "--vampire-bin",
        help="Path to a Vampire executable. Overrides VAMPIRE_BIN and PATH lookup.",
    )
    parser.add_argument("--output", type=Path, help="Write JSON result/report here.")
    parser.add_argument(
        "--premise-loop",
        action="store_true",
        help="Enable premise selection, generated-lemma proof, and premise minimization for informal proof discovery.",
    )
    parser.add_argument(
        "--premise-budget",
        choices=["tiny", "small", "medium", "full"],
        default="medium",
        help="Premise-selection budget for informal proof discovery.",
    )
    parser.add_argument(
        "--no-premise-generation",
        action="store_true",
        help="Disable generated lemma attempts when --premise-loop is enabled.",
    )
    parser.add_argument(
        "--no-premise-minimization",
        action="store_true",
        help="Disable proof-preserving premise minimization when --premise-loop is enabled.",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    runner = VampireRunner(binary=args.vampire_bin)
    if args.problem:
        result = runner.run_path(
            (
                REPO_ROOT / args.problem
                if not args.problem.is_absolute()
                else args.problem
            ),
            time_limit=args.time_limit,
        )
        payload = result.to_dict()
        ok = result.ok
    else:
        statement = read_text_argument(args.text, args.text_file)
        artifact_root = (
            REPO_ROOT / args.artifact_root
            if not args.artifact_root.is_absolute()
            else args.artifact_root
        )
        payload = discover_proof(
            statement,
            artifact_root=artifact_root,
            source_url=args.source_url,
            time_limit=args.time_limit,
            runner=runner,
            premise_loop=args.premise_loop,
            premise_budget=args.premise_budget,
            generate_premises=not args.no_premise_generation,
            minimize_premises=not args.no_premise_minimization,
        )
        ok = bool(payload["ok"])

    if args.output:
        out = REPO_ROOT / args.output if not args.output.is_absolute() else args.output
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    return emit_result(payload, ok, args)


def emit_result(payload, ok, args):
    """Shared CLI rendering and exit status for staged and synchronous runs."""
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"ok: {ok}")
        if "winning_status" in payload:
            print(f"winning_status: {payload['winning_status']}")
            print(f"artifact_root: {args.artifact_root}")
            if payload.get("winning_formal_proof_path"):
                print(f"formal_proof: {payload['winning_formal_proof_path']}")
            if payload.get("winning_informal_proof_path"):
                print(f"informal_proof: {payload['winning_informal_proof_path']}")
            if payload.get("winning_premise_selection_report_path"):
                print(
                    f"premise_selection: {payload['winning_premise_selection_report_path']}"
                )
            if payload.get("winning_premise_generation_report_path"):
                print(
                    f"premise_generation: {payload['winning_premise_generation_report_path']}"
                )
            if payload.get("winning_premise_minimization_report_path"):
                print(
                    f"premise_minimization: {payload['winning_premise_minimization_report_path']}"
                )
        else:
            print(f"status: {payload.get('status')}")
            print(f"problem: {payload.get('problem_path')}")
            if payload.get("formal_proof"):
                print("formal_proof: embedded in JSON result")
            if payload.get("informal_proof"):
                print("informal_proof: embedded in JSON result")
    return 0 if ok else 3


if __name__ == "__main__":
    raise SystemExit(main())
