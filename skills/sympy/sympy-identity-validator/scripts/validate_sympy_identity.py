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

"""Validate a generated SymPy identity by independent normalization methods."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

from sympy import Poly, expand, simplify

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def load_module(path: Path) -> Any:
    """Document the responsibility of ``load_module``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate(path: Path) -> dict[str, Any]:
    """Document the responsibility of ``validate``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Validate assumptions or artifacts and return explicit evidence about whether the contract holds.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    module = load_module(path)
    if hasattr(module, "build_expressions"):
        expressions = module.build_expressions()
    else:
        equations = module.build_equations()
        expressions = {
            "lhs": equations["target_expression"],
            "rhs": equations["expected_expression"],
            "validation_difference": equations.get(
                "residual",
                equations["target_expression"] - equations["expected_expression"],
            ),
        }
    lhs = expressions["lhs"]
    rhs = expressions["rhs"]
    diff = expressions.get("validation_difference", lhs - rhs)
    simplified = simplify(diff)
    expanded = expand(diff)
    artifact_symbolic: dict[str, Any] = {}
    try:
        symbolic_result = module.validate_symbolic()
        artifact_symbolic = (
            symbolic_result
            if isinstance(symbolic_result, dict)
            else {"passed": bool(symbolic_result)}
        )
    except Exception as exc:
        artifact_symbolic = {"passed": False, "error": f"{type(exc).__name__}: {exc}"}
    poly_ok = None
    poly_error = None
    try:
        symbols = list(module.build_symbols().values())
        poly_ok = bool(Poly(expanded, *symbols).is_zero)
    except Exception as exc:
        poly_error = f"{type(exc).__name__}: {exc}"
    passed = bool(
        artifact_symbolic.get("passed")
        or simplified == 0
        or expanded == 0
        or poly_ok is True
    )
    return {
        "backend": "sympy",
        "artifact": str(path),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "methods": {
            "simplify_difference_zero": bool(simplified == 0),
            "expand_difference_zero": bool(expanded == 0),
            "poly_zero": poly_ok,
            "poly_error": poly_error,
            "artifact_symbolic_passed": bool(artifact_symbolic.get("passed")),
        },
        "difference": str(diff),
        "simplified": str(simplified),
        "expanded": str(expanded),
        "passed": passed,
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
    parser.add_argument("--artifact", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        args.artifact = Path(
            "backends/sympy/MathformerSympy/AutoformalizedSumFirstOddNumbers.py"
        )
        if not args.artifact.exists():
            subprocess.run([sys.executable, "tests/sympy/run_wiki_case.py"], check=True)
    if args.artifact is None:
        parser.error("--artifact is required unless --self-test is used")

    report = validate(args.artifact)
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text if args.json else f"identity passed={report['passed']}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
