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

"""Review final physics equation graph for SymPy physics derivations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

REQUIRED_REPORTS = [
    "execution",
    "unit",
    "step",
    "numeric",
    "equation_surface",
    "assumption_context",
    "semantics",
    "dimension_projection",
    "library_grounding",
]


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


def report_status_failed(report: dict[str, Any]) -> bool:
    """Document the responsibility of ``report_status_failed``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``report_status_failed`` while preserving the surrounding module contract.

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


def report_status_warn(report: dict[str, Any]) -> bool:
    """Document the responsibility of ``report_status_warn``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``report_status_warn`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return str(report.get("status", "")).lower() in {"warn", "warning", "draft"}


def build_review(reports: dict[str, dict[str, Any]]) -> dict[str, Any]:
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
    for name in REQUIRED_REPORTS:
        if not reports.get(name):
            add(
                findings,
                "warning",
                f"missing_{name}_report",
                f"Missing {name} report.",
                "trace_realness",
            )
        elif report_status_failed(reports[name]):
            add(
                findings,
                "error",
                f"{name}_report_failed",
                f"{name} report failed.",
                "trace_realness",
            )
        elif report_status_warn(reports[name]):
            add(
                findings,
                "warning",
                f"{name}_report_warned",
                f"{name} report is warning or draft.",
                "trace_realness",
            )

    surface = reports.get("equation_surface", {})
    quantities = surface.get("QUANTITY_SURFACE", [])
    graph = surface.get("EQUATION_GRAPH", {})
    equations = graph.get("nodes", []) if isinstance(graph, dict) else []
    bridges = surface.get("PROJECTION_BRIDGES", [])
    laws = surface.get("LAW_TABLE", [])
    assumptions = reports.get("assumption_context", {}).get("CONTEXT_ASSUMPTIONS", [])
    semantics_features = reports.get("semantics", {}).get("features", {})
    library_grounding = reports.get("library_grounding", {}) or surface.get(
        "LIBRARY_GROUNDING", {}
    )

    if not quantities:
        add(
            findings,
            "error",
            "quantity_surface_missing",
            "Final physics review requires represented or projected source quantities.",
            "quantity_surface",
        )
    if not equations:
        add(
            findings,
            "error",
            "equation_graph_missing",
            "Final physics review requires an equation graph.",
            "equation_parse",
        )
    if equations and not any(
        str(eq.get("role", "")).lower() == "target"
        for eq in equations
        if isinstance(eq, dict)
    ):
        add(
            findings,
            "warning",
            "target_node_missing",
            "No equation graph node is marked as target.",
            "equation_parse",
        )
    if (
        quantities
        and any(
            str(q.get("role", "")).lower()
            in {"vector", "field", "vector_or_field", "operator"}
            for q in quantities
        )
        and not bridges
    ):
        add(
            findings,
            "error",
            "projection_bridge_missing",
            "Vector, field, or operator quantities need projection bridges for scalar SymPy equations.",
            "projection_bridge",
        )
    if not laws:
        add(
            findings,
            "warning",
            "law_table_missing",
            "No law table is present for the final physics equation graph.",
            "law_grounding",
        )
    if not assumptions:
        add(
            findings,
            "warning",
            "assumption_context_missing",
            "No contextual assumptions are present for final physics review.",
            "assumption_context",
        )
    if semantics_features.get("source_physical") and not semantics_features.get(
        "artifact_has_commentary_header"
    ):
        add(
            findings,
            "error",
            "informal_commentary_header_missing",
            "Final SymPy artifact must expose the source commentary header as inspectable module data.",
            "source_alignment_commentary",
        )
    if semantics_features.get("source_derivational") and not semantics_features.get(
        "artifact_has_full_informal_derivation"
    ):
        add(
            findings,
            "error",
            "informal_derivation_commentary_missing",
            "Final SymPy artifact must preserve the full informal derivation commentary in the module header.",
            "source_alignment_commentary",
        )
    if semantics_features.get("source_derivational") and not semantics_features.get(
        "artifact_has_sympy_alignment"
    ):
        add(
            findings,
            "error",
            "informal_to_sympy_alignment_missing",
            "Final SymPy artifact must align informal derivation steps to executable SymPy trace steps.",
            "source_alignment_commentary",
        )
    if not library_grounding:
        add(
            findings,
            "error",
            "sympy_library_grounding_missing",
            "Final physics SymPy review requires installed-library grounding evidence.",
            "sympy_library_grounding",
        )
    elif library_grounding.get("grounding_level") != "high":
        add(
            findings,
            "error",
            "sympy_library_grounding_below_complete_threshold",
            "Case-required physics/equational roles are not maximally grounded in installed SymPy/dependency APIs.",
            "sympy_library_grounding",
        )

    return {
        "style": "physics_sympy_final_equation_review",
        "status": status(findings),
        "findings": findings,
        "reviewed_properties": {
            "sympy_library_grounding_level": (
                library_grounding.get("grounding_level", "missing")
                if library_grounding
                else "missing"
            ),
            "sympy_library_required_roles": (
                library_grounding.get("required_roles", []) if library_grounding else []
            ),
        },
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
                "critique.physics_sympy_semantics",
                "critique.physics_sympy_dimensions",
                "review.physics_sympy_final_equations",
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
    for name in REQUIRED_REPORTS:
        parser.add_argument(f"--{name.replace('_', '-')}-report", type=Path)
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
            {
                "equation_surface": {
                    "QUANTITY_SURFACE": [],
                    "EQUATION_GRAPH": {"nodes": []},
                },
                "execution": {"status": "pass"},
                "unit": {"status": "pass"},
                "step": {"status": "pass"},
                "numeric": {"status": "pass"},
                "assumption_context": {},
                "semantics": {"status": "pass"},
                "dimension_projection": {"status": "pass"},
                "library_grounding": {
                    "grounding_level": "high",
                    "required_roles": ["scalar_expression_core"],
                },
            }
        )
        assert review["status"] == "fail"
        assert "quantity_surface" in review["repair_surfaces"]
    else:
        reports = {
            name: load_json(getattr(args, f"{name}_report"))
            for name in REQUIRED_REPORTS
        }
        review = build_review(reports)
    output = json.dumps(review, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
