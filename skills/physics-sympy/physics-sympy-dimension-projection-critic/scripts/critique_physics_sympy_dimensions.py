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

"""Critique dimensions, units, and projection bridges in SymPy physics traces."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Sequence

VECTOR_TERMS = [
    "vector",
    "field",
    "curl",
    "gradient",
    "divergence",
    "\\vec",
    "\\times",
    "cross",
]
TRANSCENDENTAL_PATTERN = re.compile(
    r"\b(exp|log|sin|cos|tan)\s*\(([^)]*(time|length|mass|force|energy|velocity|acceleration|meter|second|kg|m/s)[^)]*)\)",
    re.I,
)


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


def read_text(path: Path | None, inline: str | None) -> str:
    """Document the responsibility of ``read_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if inline is not None:
        return inline
    if path is not None:
        return path.read_text(encoding="utf-8")
    return ""


def has_any(text: str, terms: Sequence[str]) -> bool:
    """Document the responsibility of ``has_any``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``has_any`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    lower = text.lower()
    return any(term.lower() in lower for term in terms)


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


def report_failed(packet: dict[str, Any]) -> bool:
    """Document the responsibility of ``report_failed``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``report_failed`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return str(packet.get("status", "")).lower() in {
        "fail",
        "failed",
        "error",
        "blocked",
    }


def build_report(
    *,
    source_text: str,
    artifact_text: str,
    equation_surface: dict[str, Any],
    unit_report: dict[str, Any],
    dimension_report: dict[str, Any],
) -> dict[str, Any]:
    """Document the responsibility of ``build_report``.

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
    bridges = equation_surface.get("PROJECTION_BRIDGES", [])
    quantities = equation_surface.get("QUANTITY_SURFACE", [])
    combined = artifact_text + "\n" + json.dumps(equation_surface, ensure_ascii=False)

    if report_failed(unit_report) or report_failed(dimension_report):
        add(
            findings,
            "error",
            "unit_or_dimension_report_failed",
            "Unit or dimension report is failing.",
            "unit_dimension",
        )
    if TRANSCENDENTAL_PATTERN.search(combined):
        add(
            findings,
            "error",
            "dimensioned_transcendental_argument",
            "A transcendental function appears to receive a dimensioned argument.",
            "unit_dimension",
        )
    if has_any(source_text, VECTOR_TERMS) and not bridges:
        add(
            findings,
            "critical",
            "missing_projection_bridge",
            "Vector or field source content lacks a projection bridge.",
            "projection_bridge",
        )
    if bridges:
        incomplete = [
            bridge
            for bridge in bridges
            if str(bridge.get("status", "required")).lower()
            not in {"pass", "provided", "ready", "required"}
        ]
        if incomplete:
            add(
                findings,
                "error",
                "projection_bridge_incomplete",
                "One or more projection bridges are marked incomplete.",
                "projection_bridge",
            )
    dimensionless = [
        q
        for q in quantities
        if str(q.get("dimension", "")).lower() in {"1", "dimensionless", "none"}
        and not q.get("unit")
    ]
    if (
        dimensionless
        and re.search(r"\b(normalized|dimensionless|ratio)\b", combined, re.I) is None
    ):
        add(
            findings,
            "warning",
            "unlabeled_dimensionless_quantity",
            "Dimensionless quantities should be labeled as normalized, ratios, or pure numbers.",
            "unit_dimension",
        )

    return {
        "style": "physics_sympy_dimension_projection_critic_report",
        "status": status(findings),
        "features": {
            "projection_bridge_count": len(bridges),
            "quantity_count": len(quantities),
            "unit_report_status": unit_report.get("status"),
            "dimension_report_status": dimension_report.get("status"),
        },
        "findings": findings,
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
    parser.add_argument("--source-file", type=Path)
    parser.add_argument("--source-text")
    parser.add_argument("--artifact-file", type=Path)
    parser.add_argument("--artifact-text")
    parser.add_argument("--equation-surface", type=Path)
    parser.add_argument("--unit-report", type=Path)
    parser.add_argument("--dimension-report", type=Path)
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
        report = build_report(
            source_text="A vector field is reduced to a scalar.",
            artifact_text="sin(length)",
            equation_surface={
                "QUANTITY_SURFACE": [{"symbol": "x", "dimension": "length"}]
            },
            unit_report={},
            dimension_report={},
        )
        assert report["status"] == "fail"
        assert any(
            item["code"] == "dimensioned_transcendental_argument"
            for item in report["findings"]
        )
    else:
        report = build_report(
            source_text=read_text(args.source_file, args.source_text),
            artifact_text=read_text(args.artifact_file, args.artifact_text),
            equation_surface=load_json(args.equation_surface),
            unit_report=load_json(args.unit_report),
            dimension_report=load_json(args.dimension_report),
        )
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
