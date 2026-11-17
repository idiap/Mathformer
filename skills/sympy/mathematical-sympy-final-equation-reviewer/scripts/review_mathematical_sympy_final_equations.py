#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.
#
# Intent:
#   Tell coding agents what context to load, what invariants to preserve, and how to validate their work.
#
# Function:
#   Contains skill instructions, prompts, references, and scripts used by Codex-style workflows.
#
# Maintenance Notes:
#   Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.

"""Review mathematical correctness of final SymPy equation traces."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any, Sequence


def load_json(path: Path | None) -> dict[str, Any]:
    """Document the responsibility of ``load_json``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if path is None:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def add(
    findings: list[dict[str, Any]], severity: str, code: str, message: str, surface: str
) -> None:
    """Document the responsibility of ``add``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``add`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    findings.append(
        {
            "severity": severity,
            "code": code,
            "message": message,
            "repair_surface": surface,
        }
    )


def status(findings: list[dict[str, Any]]) -> str:
    """Document the responsibility of ``status``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``status`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    score = max(
        (
            {"info": 0, "warning": 1, "error": 2, "critical": 3}[item["severity"]]
            for item in findings
        ),
        default=0,
    )
    return "fail" if score >= 2 else "warn" if score == 1 else "pass"


def is_fail(report: dict[str, Any]) -> bool:
    """Document the responsibility of ``is_fail``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``is_fail`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return str(report.get("status", "")).lower() in {
        "fail",
        "failed",
        "error",
        "blocked",
    }


def is_warn(report: dict[str, Any]) -> bool:
    """Document the responsibility of ``is_warn``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``is_warn`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return str(report.get("status", "")).lower() in {"warn", "warning", "draft"}


def side_conditions_required(assumption_context: dict[str, Any]) -> bool:
    """Document the responsibility of ``side_conditions_required``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``side_conditions_required`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    text = json.dumps(
        assumption_context.get("CONTEXT_ASSUMPTIONS", []), ensure_ascii=False
    )
    return bool(
        re.search(
            r"(!=|≠|nonzero|non-zero|positive|strictly positive|>\s*0|<\s*0|>=\s*0|≤|>=|<=|not zero)",
            text,
            re.I,
        )
    )


def build_review(
    *,
    execution_report: dict[str, Any],
    identity_report: dict[str, Any],
    counterexample_report: dict[str, Any],
    trace_report: dict[str, Any],
    assumption_context: dict[str, Any],
) -> dict[str, Any]:
    """Document the responsibility of ``build_review``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    findings: list[dict[str, Any]] = []
    named = {
        "execution": execution_report,
        "identity": identity_report,
        "counterexample": counterexample_report,
        "trace": trace_report,
    }
    for name, report in named.items():
        if not report:
            add(
                findings,
                "warning",
                f"missing_{name}_report",
                f"Missing {name} report.",
                "trace_realness",
            )
        elif is_fail(report):
            add(
                findings,
                "error",
                f"{name}_report_failed",
                f"{name} report failed.",
                "transformation_step",
            )
        elif is_warn(report):
            add(
                findings,
                "warning",
                f"{name}_report_warned",
                f"{name} report warned.",
                "transformation_step",
            )

    side_conditions = assumption_context.get("SIDE_CONDITIONS", [])
    if (
        assumption_context
        and side_conditions_required(assumption_context)
        and not side_conditions
    ):
        add(
            findings,
            "warning",
            "side_conditions_absent",
            "Assumption context exists but no side conditions are recorded.",
            "assumption_context",
        )

    for item in trace_report.get("findings", []):
        if isinstance(item, dict) and str(item.get("severity")) in {
            "error",
            "critical",
        }:
            add(
                findings,
                "error",
                "trace_finding_failed",
                "Trace verifier reported a blocking finding.",
                "transformation_step",
            )

    return {
        "style": "mathematical_sympy_final_equation_review",
        "status": status(findings),
        "findings": findings,
        "repair_surfaces": sorted({item["repair_surface"] for item in findings}),
        "refinement_handoff": {
            "repair_surfaces": sorted(
                {
                    item["repair_surface"]
                    for item in findings
                    if item["severity"] in {"error", "critical"}
                }
            ),
            "rerun_gates": [
                "physics.steps.verify",
                "physics.numeric.sample",
                "review.mathematical_sympy_final_equations",
            ],
        },
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Document the responsibility of ``parse_args``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Parse caller-provided input into the structured representation expected by downstream code.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution-report", type=Path)
    parser.add_argument("--identity-report", type=Path)
    parser.add_argument("--counterexample-report", type=Path)
    parser.add_argument("--trace-report", type=Path)
    parser.add_argument("--assumption-context", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Document the responsibility of ``main``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Serve as the command-line entry point and coordinate argument parsing, execution, and reporting.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    args = parse_args(argv)
    if args.self_test:
        review = build_review(
            execution_report={"status": "pass"},
            identity_report={"status": "fail"},
            counterexample_report={"status": "pass"},
            trace_report={"status": "pass"},
            assumption_context={"SIDE_CONDITIONS": [{"id": "nz"}]},
        )
        assert review["status"] == "fail"
        assert "transformation_step" in review["repair_surfaces"]
        no_side_conditions = build_review(
            execution_report={"status": "pass"},
            identity_report={"status": "pass"},
            counterexample_report={"status": "pass"},
            trace_report={"status": "pass"},
            assumption_context={
                "CONTEXT_ASSUMPTIONS": [{"text": "fixed Cartesian coordinate frame"}],
                "SIDE_CONDITIONS": [],
            },
        )
        assert no_side_conditions["status"] == "pass"
    else:
        review = build_review(
            execution_report=load_json(args.execution_report),
            identity_report=load_json(args.identity_report),
            counterexample_report=load_json(args.counterexample_report),
            trace_report=load_json(args.trace_report),
            assumption_context=load_json(args.assumption_context),
        )
    output = json.dumps(review, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
