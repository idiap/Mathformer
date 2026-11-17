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

"""Draft the controlled Wikipedia sum-of-odd-numbers SymPy artifact."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

TEMPLATE = '''"""SymPy autoformalization of the sum of the first odd numbers.

Original source (NL): For every natural number n, the sum of the first n odd
numbers is n^2.
Original source (LaTeX): 1 + 3 + 5 + \\\\cdots + (2n-1) = n^2.
Formalized source formula: \\\\sum_{{i=0}}^{{n-1}} (2i+1) = n^2.
Source anchors: {anchors}

Generated support note: The Python implementation exposes a symbolic equality,
numeric sampling over the source-backed natural-number domain, and an
executable transformation trace. It is not a Lean proof; it is the first
Mathformer SymPy backend style, `sympy_equational_trace`.
"""

from __future__ import annotations

import json
from typing import Any

from sympy import Symbol, expand, simplify, summation


CLAIM = {{
    "id": "wiki_sum_first_odd_numbers",
    "backend": "sympy",
    "style": "sympy_equational_trace",
    "source_anchors": {anchors_json},
    "statement_nl": "For every natural number n, the sum of the first n odd numbers is n^2.",
    "statement_latex": "1 + 3 + 5 + \\\\cdots + (2n-1) = n^2",
    "formal_latex": "\\\\sum_{{i=0}}^{{n-1}} (2i+1) = n^2",
    "assumptions": {{
        "n": {{"integer": True, "nonnegative": True}},
        "i": {{"integer": True, "nonnegative": True, "role": "summation_index"}},
    }},
}}


def build_symbols() -> dict[str, Any]:
    n = Symbol("n", integer=True, nonnegative=True)
    i = Symbol("i", integer=True, nonnegative=True)
    return {{"n": n, "i": i}}


def build_expressions() -> dict[str, Any]:
    symbols = build_symbols()
    n = symbols["n"]
    i = symbols["i"]
    lhs = summation(2 * i + 1, (i, 0, n - 1))
    rhs = n**2
    return {{
        "symbols": symbols,
        "lhs": lhs,
        "rhs": rhs,
        "difference": simplify(lhs - rhs),
        "expanded_difference": expand(lhs - rhs),
    }}


def validate_symbolic() -> dict[str, Any]:
    expressions = build_expressions()
    difference = simplify(expressions["lhs"] - expressions["rhs"])
    expanded_difference = expand(expressions["lhs"] - expressions["rhs"])
    return {{
        "passed": bool(difference == 0 and expanded_difference == 0),
        "lhs": str(expressions["lhs"]),
        "rhs": str(expressions["rhs"]),
        "difference": str(difference),
        "expanded_difference": str(expanded_difference),
        "method": "summation followed by simplify and expand normalization",
    }}


def validate_numeric_samples(max_n: int = 50) -> dict[str, Any]:
    samples = []
    counterexamples = []
    for n_value in range(0, max_n + 1):
        lhs_value = sum(2 * i_value + 1 for i_value in range(n_value))
        rhs_value = n_value**2
        sample = {{"n": n_value, "lhs": lhs_value, "rhs": rhs_value, "passed": lhs_value == rhs_value}}
        samples.append(sample)
        if not sample["passed"]:
            counterexamples.append(sample)
    return {{
        "passed": not counterexamples,
        "sample_count": len(samples),
        "domain": "n in {{0, ..., max_n}}",
        "max_n": max_n,
        "counterexamples": counterexamples,
        "first_samples": samples[:6],
        "last_sample": samples[-1] if samples else None,
    }}


def explain_trace() -> list[dict[str, Any]]:
    expressions = build_expressions()
    return [
        {{
            "step": 1,
            "input": "sum_{{i=0}}^{{n-1}} (2*i + 1)",
            "api": "sympy.concrete.summations.summation",
            "output": str(expressions["lhs"]),
            "justification": "Evaluate the finite arithmetic progression sum.",
        }},
        {{
            "step": 2,
            "input": f"{{expressions['lhs']}} - {{expressions['rhs']}}",
            "api": "sympy.simplify.simplify.simplify",
            "output": str(simplify(expressions["lhs"] - expressions["rhs"])),
            "justification": "Normalize the claimed equality to a zero difference.",
        }},
        {{
            "step": 3,
            "input": f"{{expressions['lhs']}} - {{expressions['rhs']}}",
            "api": "sympy.core.function.expand",
            "output": str(expand(expressions["lhs"] - expressions["rhs"])),
            "justification": "Confirm the normalized polynomial difference is zero.",
        }},
    ]


def main() -> int:
    payload = {{
        "claim": CLAIM,
        "symbolic": validate_symbolic(),
        "numeric": validate_numeric_samples(),
        "trace": explain_trace(),
    }}
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["symbolic"]["passed"] and payload["numeric"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
'''


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
    parser.add_argument("--parse-packet", type=Path, required=True)
    parser.add_argument("--assumptions", type=Path, required=True)
    parser.add_argument("--grounding", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "backends/sympy/MathformerSympy/AutoformalizedSumFirstOddNumbers.py"
        ),
    )
    parser.add_argument("--report", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    parse_packet = json.loads(args.parse_packet.read_text(encoding="utf-8"))
    _assumptions = json.loads(args.assumptions.read_text(encoding="utf-8"))
    _grounding = json.loads(args.grounding.read_text(encoding="utf-8"))
    anchors: list[str] = []
    for unit in parse_packet.get("units", []):
        anchors.extend(unit.get("source_anchors", []))
    anchors = sorted(set(anchors))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        TEMPLATE.format(anchors=", ".join(anchors), anchors_json=json.dumps(anchors)),
        encoding="utf-8",
    )
    report = {
        "backend": "sympy",
        "style": "sympy_equational_trace",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "output": str(args.output),
        "source_anchors": anchors,
        "status": "drafted",
        "placeholder_free": True,
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(
        json.dumps(report, indent=2, sort_keys=True)
        if args.json
        else f"wrote {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
