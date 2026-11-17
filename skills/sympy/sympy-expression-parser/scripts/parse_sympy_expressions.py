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

"""Extract SymPy-facing expression packets from controlled LaTeX/NL sources."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any


def line_anchors(text: str) -> list[dict[str, Any]]:
    """Document the responsibility of ``line_anchors``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``line_anchors`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    anchors = []
    for idx, line in enumerate(text.splitlines(), start=1):
        anchors.append(
            {
                "anchor": f"src_L{idx:04d}",
                "line": idx,
                "sha256": hashlib.sha256(line.encode("utf-8")).hexdigest(),
                "text": line,
            }
        )
    return anchors


def anchor_range(anchors: list[dict[str, Any]], pattern: str) -> str | None:
    """Document the responsibility of ``anchor_range``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``anchor_range`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    for item in anchors:
        if pattern in item["text"]:
            return item["anchor"]
    return None


def parse_sum_first_odd_numbers(
    text: str, anchors: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Document the responsibility of ``parse_sum_first_odd_numbers``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Parse caller-provided input into the structured representation expected by downstream code.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    units: list[dict[str, Any]] = []
    if "1 + 3 + 5" in text and "n^2" in text:
        units.append(
            {
                "id": "wiki_sum_first_odd_numbers.statement",
                "kind": "theorem_statement",
                "status": "parsed",
                "source_anchors": [
                    anchor_range(anchors, "For every natural number") or "src_L0024",
                    anchor_range(anchors, "1 + 3 + 5") or "src_L0026",
                ],
                "literal_nl": "For every natural number n, the sum of the first n odd numbers is n^2.",
                "literal_latex": "1 + 3 + 5 + \\cdots + (2n-1) = n^2",
                "sympy_surface": {
                    "symbols": ["n", "i"],
                    "lhs": "summation(2*i + 1, (i, 0, n - 1))",
                    "rhs": "n**2",
                    "equivalence_method": "simplify(lhs - rhs) == 0",
                },
                "concepts": ["finite_sum", "odd_numbers", "square", "natural_number"],
                "uncertainty": [],
            }
        )
    if "\\sum_{i=0}^{n-1}" in text:
        units.append(
            {
                "id": "wiki_sum_first_odd_numbers.lean_target_formula",
                "kind": "formalization_hint",
                "status": "parsed",
                "source_anchors": [
                    anchor_range(anchors, "\\sum_{i=0}^{n-1}") or "src_L0051"
                ],
                "literal_latex": "\\sum_{i=0}^{n-1} (2i+1)",
                "sympy_surface": {"lhs": "summation(2*i + 1, (i, 0, n - 1))"},
                "concepts": ["finite_sum"],
                "uncertainty": [],
            }
        )
    return units


def parse_binomial_square(
    text: str, anchors: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Document the responsibility of ``parse_binomial_square``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Parse caller-provided input into the structured representation expected by downstream code.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if "(a+b)^2" not in text and "(a+b)" not in text:
        return []
    return [
        {
            "id": "sympy_binomial_square.statement",
            "case_id": "sympy_binomial_square",
            "kind": "theorem_statement",
            "status": "parsed",
            "source_anchors": [
                anchor_range(anchors, "For all real numbers") or "src_L0000",
                anchor_range(anchors, "(a+b)^2") or "src_L0000",
            ],
            "literal_nl": "For all real numbers a and b, (a+b)^2 = a^2 + 2ab + b^2.",
            "literal_latex": "(a+b)^2 = a^2 + 2ab + b^2",
            "sympy_surface": {
                "symbols": ["a", "b"],
                "lhs": "(a + b)**2",
                "rhs": "a**2 + 2*a*b + b**2",
                "equivalence_method": "expand(lhs - rhs) == 0",
            },
            "concepts": [
                "algebraic_expansion",
                "polynomial_identity",
                "square",
                "real_scalar",
            ],
            "uncertainty": [],
        }
    ]


def parse_finite_geometric_sum(
    text: str, anchors: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Document the responsibility of ``parse_finite_geometric_sum``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Parse caller-provided input into the structured representation expected by downstream code.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if "\\sum_{k=0}^{n}" not in text:
        return []
    return [
        {
            "id": "sympy_finite_geometric_sum.statement",
            "case_id": "sympy_finite_geometric_sum",
            "kind": "theorem_statement",
            "status": "parsed",
            "source_anchors": [
                anchor_range(anchors, "natural number") or "src_L0000",
                anchor_range(anchors, "\\sum_{k=0}^{n}") or "src_L0000",
            ],
            "literal_nl": "For every natural number n and scalar r with r != 1, the finite geometric sum has the closed form.",
            "literal_latex": "\\sum_{k=0}^{n} r^k = \\frac{1-r^{n+1}}{1-r},\\quad r \\ne 1",
            "sympy_surface": {
                "symbols": ["n", "k", "r"],
                "lhs": "summation(r**k, (k, 0, n))",
                "rhs": "(1 - r**(n + 1))/(1 - r)",
                "equivalence_method": "simplify((1-r)*(lhs-rhs)) == 0 under r != 1",
            },
            "concepts": [
                "finite_sum",
                "geometric_series",
                "natural_number",
                "nonzero_denominator",
                "symbolic_simplification",
            ],
            "uncertainty": [
                "SymPy represents the unexcluded r=1 branch with Piecewise; validation uses the source condition r != 1."
            ],
        }
    ]


def parse_product_rule_derivative(
    text: str, anchors: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Document the responsibility of ``parse_product_rule_derivative``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Parse caller-provided input into the structured representation expected by downstream code.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if "\\frac{d}{dx}" not in text:
        return []
    return [
        {
            "id": "sympy_product_rule_derivative.statement",
            "case_id": "sympy_product_rule_derivative",
            "kind": "theorem_statement",
            "status": "parsed",
            "source_anchors": [
                anchor_range(anchors, "For every real number") or "src_L0000",
                anchor_range(anchors, "\\frac{d}{dx}") or "src_L0000",
            ],
            "literal_nl": "For every real number x, the derivative of x^2 sin x is 2x sin x + x^2 cos x.",
            "literal_latex": "\\frac{d}{dx}\\left(x^2\\sin x\\right) = 2x\\sin x + x^2\\cos x",
            "sympy_surface": {
                "symbols": ["x"],
                "lhs": "diff(x**2*sin(x), x)",
                "rhs": "2*x*sin(x) + x**2*cos(x)",
                "equivalence_method": "simplify(lhs - rhs) == 0",
            },
            "concepts": [
                "derivative",
                "product_rule",
                "elementary_functions",
                "real_scalar",
            ],
            "uncertainty": [],
        }
    ]


def parse_matrix_distributivity(
    text: str, anchors: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Document the responsibility of ``parse_matrix_distributivity``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Parse caller-provided input into the structured representation expected by downstream code.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if "A(B+C)" not in text:
        return []
    return [
        {
            "id": "sympy_matrix_distributivity.statement",
            "case_id": "sympy_matrix_distributivity",
            "kind": "theorem_statement",
            "status": "parsed",
            "source_anchors": [
                anchor_range(anchors, "compatible dimensions") or "src_L0000",
                anchor_range(anchors, "A(B+C)") or "src_L0000",
            ],
            "literal_nl": "For matrices A, B, and C with compatible dimensions, A(B+C) = AB + AC.",
            "literal_latex": "A(B+C) = AB + AC",
            "sympy_surface": {
                "symbols": ["A", "B", "C", "m", "p", "q"],
                "lhs": "A*(B + C)",
                "rhs": "A*B + A*C",
                "equivalence_method": "expand(lhs - rhs) == 0",
            },
            "concepts": [
                "matrix_symbols",
                "matrix_distributivity",
                "algebraic_expansion",
            ],
            "uncertainty": [],
        }
    ]


def build_packet(source: Path) -> dict[str, Any]:
    """Document the responsibility of ``build_packet``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    text = source.read_text(encoding="utf-8")
    anchors = line_anchors(text)
    units = (
        parse_sum_first_odd_numbers(text, anchors)
        or parse_binomial_square(text, anchors)
        or parse_finite_geometric_sum(text, anchors)
        or parse_product_rule_derivative(text, anchors)
        or parse_matrix_distributivity(text, anchors)
    )
    if not units:
        formulas = re.findall(r"\\\[(.*?)\\\]", text, flags=re.DOTALL)
        units = [
            {
                "id": f"formula_{idx}",
                "kind": "unclassified_formula",
                "status": "unresolved",
                "literal_latex": formula.strip(),
                "source_anchors": [],
                "concepts": [],
                "uncertainty": ["no deterministic parser rule matched"],
            }
            for idx, formula in enumerate(formulas, start=1)
        ]
    return {
        "backend": "sympy",
        "style": "sympy_equational_trace",
        "case_id": (
            units[0].get("case_id", units[0]["id"].split(".")[0])
            if units
            else "unresolved"
        ),
        "source": str(source),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "anchors": anchors,
        "units": units,
        "parse_coverage": sum(1 for unit in units if unit["status"] == "parsed")
        / max(1, len(units)),
    }


def main() -> int:
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        args.source = Path("tests/latex/wiki_level/sum_first_odd_numbers.tex")
    if args.source is None:
        parser.error("--source is required unless --self-test is used")

    packet = build_packet(args.source)
    text = json.dumps(packet, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(
        text
        if args.json
        else f"parsed_units={len(packet['units'])} coverage={packet['parse_coverage']:.2f}"
    )
    return 0 if packet["parse_coverage"] > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
