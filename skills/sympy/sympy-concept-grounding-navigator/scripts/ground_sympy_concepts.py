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

"""Ground mathematical concepts into SymPy APIs."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

CONCEPT_SYNONYMS = {
    "algebraic_expansion": ["expand", "algebraic expansion", "polynomial"],
    "factorization": ["factor", "factorization"],
    "finite_sum": ["summation", "Sum", "finite sum", "concrete"],
    "finite_product": ["Product", "product", "finite product"],
    "geometric_series": ["summation", "Sum", "geometric"],
    "odd_numbers": ["integer", "Symbol", "assumptions"],
    "real_scalar": ["Symbol", "real"],
    "square": ["Pow", "expand", "simplify"],
    "symbolic_simplification": ["simplify", "expand", "factor"],
    "polynomial_identity": ["Poly", "expand", "factor"],
    "natural_number": ["integer", "nonnegative", "Symbol"],
    "nonzero_denominator": ["simplify", "cancel", "fraction"],
    "derivative": ["diff", "Derivative"],
    "product_rule": ["diff", "Derivative"],
    "elementary_functions": ["sin", "cos", "functions"],
    "integral": ["integrate", "Integral"],
    "limit": ["limit", "Limit"],
    "solver": ["solve", "solveset"],
    "matrix_symbols": ["MatrixSymbol", "MatAdd", "MatMul"],
    "matrix_distributivity": ["expand", "MatMul", "MatAdd"],
    "numeric_sampling": ["lambdify", "subs", "N"],
}


def load_index(path: Path) -> dict[str, Any]:
    """Document the responsibility of ``load_index``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if not path.exists():
        return {"objects": []}
    return json.loads(path.read_text(encoding="utf-8"))


def score_object(concept: str, obj: dict[str, Any]) -> float:
    """Document the responsibility of ``score_object``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``score_object`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    terms = [concept, *CONCEPT_SYNONYMS.get(concept, [])]
    haystack = " ".join(
        str(obj.get(key, ""))
        for key in ["name", "qualified_name", "module", "doc_summary"]
    ).lower()
    score = 0.0
    for term in terms:
        term_l = term.lower()
        if term_l in haystack:
            score += 2.0 if term_l == concept.lower() else 1.0
    if obj.get("module", "").startswith("sympy.concrete") and concept == "finite_sum":
        score += 2.0
    if obj.get("module", "").startswith("sympy.matrices") and concept.startswith(
        "matrix"
    ):
        score += 2.0
    if obj.get("name") in {
        "summation",
        "Sum",
        "simplify",
        "expand",
        "Symbol",
        "Poly",
        "diff",
        "Derivative",
        "MatrixSymbol",
        "sin",
        "cos",
    }:
        score += 1.5
    return score


def ground(concepts: list[str], index: dict[str, Any], top_k: int) -> dict[str, Any]:
    """Document the responsibility of ``ground``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``ground`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    objects = index.get("objects", [])
    grounded = []
    for concept in concepts:
        candidates = []
        for obj in objects:
            score = score_object(concept, obj)
            if score > 0:
                candidates.append({"score": round(score, 3), **obj})
        candidates = sorted(
            candidates, key=lambda item: (-item["score"], item["qualified_name"])
        )[:top_k]
        grounded.append(
            {
                "concept": concept,
                "chosen_api": candidates[0]["qualified_name"] if candidates else None,
                "status": "grounded" if candidates else "unresolved",
                "candidates": candidates,
            }
        )
    return {
        "backend": "sympy",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "concepts": grounded,
        "coverage": sum(1 for item in grounded if item["status"] == "grounded")
        / max(1, len(grounded)),
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
    parser.add_argument("--concept", action="append")
    parser.add_argument(
        "--api-index", type=Path, default=Path("artifacts/sympy_api/index.json")
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        args.concept = [
            "finite_sum",
            "algebraic_expansion",
            "derivative",
            "matrix_symbols",
        ]
    if not args.concept:
        parser.error("--concept is required unless --self-test is used")

    report = ground(args.concept, load_index(args.api_index), args.top_k)
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text if args.json else f"SymPy grounding coverage={report['coverage']:.2f}")
    return 0 if report["coverage"] > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
