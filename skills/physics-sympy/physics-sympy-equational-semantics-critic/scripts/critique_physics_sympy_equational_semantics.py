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

"""Critique physical semantics of a SymPy equation trace."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Sequence

PHYSICS_TERMS = [
    "force",
    "mass",
    "velocity",
    "acceleration",
    "energy",
    "momentum",
    "charge",
    "field",
]
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
LAW_TERMS = ["newton", "maxwell", "lagrange", "hamilton", "conservation", "law"]
DERIVATION_TERMS = ["derive", "derivation", "show", "prove", "from"]


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


def module_header_comment(text: str) -> str:
    """Document the responsibility of ``module_header_comment``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``module_header_comment`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    match = re.match(
        r"\A\s*(?:(?:[rRuUbBfF]{1,3})\s*)?(?P<quote>\"\"\"|''')(?P<body>.*?)(?P=quote)",
        text,
        re.S,
    )
    return match.group("body") if match else ""


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


def build_report(
    *,
    source_text: str,
    artifact_text: str,
    equation_surface: dict[str, Any],
    assumption_context: dict[str, Any],
    execution_report: dict[str, Any],
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
    quantities = equation_surface.get("QUANTITY_SURFACE", [])
    graph = equation_surface.get("EQUATION_GRAPH", {})
    equations = graph.get("nodes", []) if isinstance(graph, dict) else []
    laws = equation_surface.get("LAW_TABLE", [])
    bridges = equation_surface.get("PROJECTION_BRIDGES", [])
    combined = artifact_text + "\n" + json.dumps(equation_surface, ensure_ascii=False)
    header = module_header_comment(artifact_text)
    lower_header = header.lower()
    source_physical = has_any(source_text, PHYSICS_TERMS)
    source_derivational = has_any(source_text, DERIVATION_TERMS)
    artifact_has_commentary_header = bool(
        header and "commentary_header" in artifact_text
    )
    artifact_has_full_informal_derivation = (
        "original informal statement" in lower_header
        and "informal derivation commentary" in lower_header
    )
    artifact_has_sympy_alignment = "sympy alignment" in lower_header and (
        "derivation_steps" in lower_header or "step_" in lower_header
    )

    if source_physical and not quantities:
        add(
            findings,
            "critical",
            "physical_quantities_erased",
            "Source physics has quantities but the equation surface has none.",
            "quantity_surface",
        )
    if has_any(source_text, VECTOR_TERMS) and not bridges:
        add(
            findings,
            "critical",
            "projection_bridge_missing",
            "Vector, field, or operator source content lacks scalar projection bridges.",
            "projection_bridge",
        )
    if has_any(source_text, LAW_TERMS) and not laws:
        add(
            findings,
            "error",
            "law_grounding_missing",
            "Source invokes a physical law but no law table is present.",
            "law_grounding",
        )
    if artifact_text and source_physical and not artifact_has_commentary_header:
        add(
            findings,
            "error",
            "informal_commentary_header_missing",
            "SymPy artifact does not expose a source commentary header as module data.",
            "source_alignment_commentary",
        )
    if (
        artifact_text
        and source_derivational
        and not artifact_has_full_informal_derivation
    ):
        add(
            findings,
            "error",
            "informal_derivation_commentary_missing",
            "Derivational source content is not preserved as full informal derivation commentary in the module header.",
            "source_alignment_commentary",
        )
    if artifact_text and source_derivational and not artifact_has_sympy_alignment:
        add(
            findings,
            "error",
            "informal_to_sympy_alignment_missing",
            "Module header lacks a SymPy alignment from informal steps to executable trace steps.",
            "source_alignment_commentary",
        )
    source_or_input_targets = [
        eq
        for eq in equations
        if str(eq.get("role", "")).lower() in {"source", "input"}
        and str(eq.get("support", "")).lower() not in {"source_backed", "source target"}
        and re.search("target|answer|claim", str(eq), re.I)
    ]
    if source_or_input_targets or re.search(
        r"hidden_final|expected_answer", combined, re.I
    ):
        add(
            findings,
            "critical",
            "target_leakage",
            "Target-shaped content appears in an input or hidden answer surface.",
            "target_nonleakage",
        )
    if equations and not any(
        str(eq.get("role", "")).lower() in {"derived", "target"}
        for eq in equations
        if isinstance(eq, dict)
    ):
        add(
            findings,
            "warning",
            "derived_equation_missing",
            "Equation graph does not expose derived or target nodes.",
            "transformation_step",
        )
    if quantities and not assumption_context.get("CONTEXT_ASSUMPTIONS"):
        add(
            findings,
            "warning",
            "assumption_context_absent",
            "Quantity surface exists but contextual assumptions are absent.",
            "assumption_context",
        )
    if execution_report.get("status") == "fail":
        add(
            findings,
            "error",
            "execution_failed_before_semantics",
            "Execution failure must be repaired before semantic acceptance.",
            "trace_realness",
        )

    return {
        "style": "physics_sympy_equational_semantics_critic_report",
        "status": status(findings),
        "features": {
            "source_physical": source_physical,
            "source_vectorial": has_any(source_text, VECTOR_TERMS),
            "source_law": has_any(source_text, LAW_TERMS),
            "source_derivational": source_derivational,
            "artifact_has_commentary_header": artifact_has_commentary_header,
            "artifact_has_full_informal_derivation": artifact_has_full_informal_derivation,
            "artifact_has_sympy_alignment": artifact_has_sympy_alignment,
            "quantity_count": len(quantities),
            "equation_count": len(equations),
            "law_count": len(laws),
            "projection_bridge_count": len(bridges),
        },
        "findings": findings,
        "generative_probe_hints": [
            "Can the SymPy trace pass while the physical law is missing?",
            "Can a scalar target be true while the original vector or field claim is false?",
            "Can the target equation be removed from inputs without breaking the derivation?",
            "Can each informal derivation step be located in DERIVATION_STEPS, PROJECTION_BRIDGES, LAW_TABLE, or a validation function?",
        ],
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
    parser.add_argument("--assumption-context", type=Path)
    parser.add_argument("--execution-report", type=Path)
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
            source_text="A vector force field obeys Newton's law.",
            artifact_text="F = m*a",
            equation_surface={
                "EQUATION_GRAPH": {"nodes": [{"role": "target", "equation": "F=m*a"}]}
            },
            assumption_context={},
            execution_report={},
        )
        assert report["status"] == "fail"
        assert any(
            item["code"] == "physical_quantities_erased" for item in report["findings"]
        )
    else:
        report = build_report(
            source_text=read_text(args.source_file, args.source_text),
            artifact_text=read_text(args.artifact_file, args.artifact_text),
            equation_surface=load_json(args.equation_surface),
            assumption_context=load_json(args.assumption_context),
            execution_report=load_json(args.execution_report),
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
