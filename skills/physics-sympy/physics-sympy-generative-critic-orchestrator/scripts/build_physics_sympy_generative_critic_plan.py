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

"""Build a generative critic plan for SymPy physics artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
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


def collect_findings(reports: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Document the responsibility of ``collect_findings``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Search available candidates and return the matches needed by the caller.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    findings: list[dict[str, Any]] = []
    for report in reports:
        for item in report.get("findings", []) or report.get("diagnostics", []):
            if isinstance(item, dict):
                findings.append(item)
    return findings


def high_risk(
    findings: list[dict[str, Any]], reports: Sequence[dict[str, Any]]
) -> bool:
    """Document the responsibility of ``high_risk``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``high_risk`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if any(str(item.get("severity")) in {"error", "critical"} for item in findings):
        return True
    if any(str(report.get("status")) in {"fail", "warn"} for report in reports):
        return True
    return False


def build_plan(reports: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Document the responsibility of ``build_plan``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    findings = collect_findings(reports)
    risk = high_risk(findings, reports)
    repair_surfaces = sorted(
        {
            str(item.get("repair_surface"))
            for item in findings
            if item.get("repair_surface")
        }
    )
    probes = [
        {
            "id": "target_leakage_probe",
            "prompt": "Inspect the SymPy physics trace and identify whether the target equation is copied into an input, law, or hidden expected answer.",
            "blocks_when_supported_by": [
                "equation_surface",
                "execution_report",
                "final_review",
            ],
        },
        {
            "id": "scalar_erasure_probe",
            "prompt": "Find an interpretation where scalar algebra passes but the source vector, field, frame, or operator claim is false.",
            "blocks_when_supported_by": [
                "projection_bridge_report",
                "dimension_critic",
                "source_anchor",
            ],
        },
        {
            "id": "unit_substitution_probe",
            "prompt": "Propose unit substitutions or dimension scalings that should preserve the derivation, and identify any step that breaks.",
            "blocks_when_supported_by": ["unit_report", "dimension_critic"],
        },
        {
            "id": "side_condition_probe",
            "prompt": "List denominator, branch, positivity, smoothness, or domain assumptions needed by the SymPy transformations.",
            "blocks_when_supported_by": [
                "assumption_context",
                "mathematical_final_review",
            ],
        },
    ]
    return {
        "style": "physics_sympy_generative_critic_plan",
        "status": "ready" if risk else "not_required",
        "needs_codex_exec": risk,
        "risk_surfaces": repair_surfaces,
        "probe_policy": {
            "generative_findings_are": "hypotheses",
            "blocking_requires": [
                "source anchors",
                "execution diagnostics",
                "unit or dimension reports",
                "deterministic critic support",
                "repeated independent probes",
            ],
        },
        "probes": probes if risk else [],
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
    parser.add_argument("--report", action="append", type=Path, default=[])
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
        plan = build_plan(
            [
                {
                    "status": "fail",
                    "findings": [
                        {"severity": "critical", "repair_surface": "target_nonleakage"}
                    ],
                }
            ]
        )
        assert plan["needs_codex_exec"] is True
        assert plan["probes"]
    else:
        plan = build_plan([load_json(path) for path in args.report])
    output = json.dumps(plan, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
