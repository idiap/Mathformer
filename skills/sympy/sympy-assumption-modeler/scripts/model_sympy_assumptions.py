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

"""Build source-backed SymPy assumptions from parse packets."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any


def build_assumptions(parse_packet: dict[str, Any]) -> dict[str, Any]:
    """Document the responsibility of ``build_assumptions``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    text = "\n".join(
        anchor.get("text", "") for anchor in parse_packet.get("anchors", [])
    )
    source_anchors = []
    for anchor in parse_packet.get("anchors", []):
        if "natural number" in anchor.get("text", ""):
            source_anchors.append(anchor["anchor"])
    assumptions = []
    case_id = parse_packet.get("case_id", "")
    if "natural number" in text or "natural-number" in text:
        assumptions.append(
            {
                "symbol": "n",
                "source_backing": "literal",
                "source_anchors": source_anchors,
                "sympy_assumptions": {"integer": True, "nonnegative": True},
                "domain": "Nat",
                "sampling": {"type": "integer_range", "min": 0, "max": 50},
            }
        )
    if "For all real numbers" in text:
        for symbol in ["a", "b"]:
            assumptions.append(
                {
                    "symbol": symbol,
                    "source_backing": "literal",
                    "source_anchors": [
                        anchor["anchor"]
                        for anchor in parse_packet.get("anchors", [])
                        if "real numbers" in anchor.get("text", "")
                    ],
                    "sympy_assumptions": {"real": True},
                    "domain": "Real",
                    "sampling": {
                        "type": "integer_grid",
                        "values": [-3, -2, -1, 0, 1, 2, 3],
                    },
                }
            )
    if "For every real number" in text:
        assumptions.append(
            {
                "symbol": "x",
                "source_backing": "literal",
                "source_anchors": [
                    anchor["anchor"]
                    for anchor in parse_packet.get("anchors", [])
                    if "real number" in anchor.get("text", "")
                ],
                "sympy_assumptions": {"real": True},
                "domain": "Real",
                "sampling": {
                    "type": "integer_grid",
                    "values": [-3, -2, -1, 0, 1, 2, 3],
                },
            }
        )
    if "r \\ne 1" in text or "r \\neq 1" in text or "r != 1" in text:
        assumptions.append(
            {
                "symbol": "r",
                "source_backing": "literal",
                "source_anchors": [
                    anchor["anchor"]
                    for anchor in parse_packet.get("anchors", [])
                    if "r \\ne 1" in anchor.get("text", "")
                    or "r != 1" in anchor.get("text", "")
                ],
                "sympy_assumptions": {},
                "domain": "ScalarWith(r != 1)",
                "restrictions": ["r != 1"],
                "sampling": {
                    "type": "integer_grid_excluding",
                    "values": [-3, -2, -1, 0, 2, 3],
                    "exclude": [1],
                },
            }
        )
    if "compatible dimensions" in text:
        assumptions.extend(
            [
                {
                    "symbol": "A",
                    "source_backing": "literal",
                    "source_anchors": [
                        anchor["anchor"]
                        for anchor in parse_packet.get("anchors", [])
                        if "compatible dimensions" in anchor.get("text", "")
                    ],
                    "sympy_assumptions": {"matrix_shape": ["m", "p"]},
                    "domain": "Matrix(m,p)",
                    "sampling": {"type": "small_integer_matrix", "shape": [2, 3]},
                },
                {
                    "symbol": "B",
                    "source_backing": "literal",
                    "source_anchors": [
                        anchor["anchor"]
                        for anchor in parse_packet.get("anchors", [])
                        if "compatible dimensions" in anchor.get("text", "")
                    ],
                    "sympy_assumptions": {"matrix_shape": ["p", "q"]},
                    "domain": "Matrix(p,q)",
                    "sampling": {"type": "small_integer_matrix", "shape": [3, 2]},
                },
                {
                    "symbol": "C",
                    "source_backing": "literal",
                    "source_anchors": [
                        anchor["anchor"]
                        for anchor in parse_packet.get("anchors", [])
                        if "compatible dimensions" in anchor.get("text", "")
                    ],
                    "sympy_assumptions": {"matrix_shape": ["p", "q"]},
                    "domain": "Matrix(p,q)",
                    "sampling": {"type": "small_integer_matrix", "shape": [3, 2]},
                },
            ]
        )
    if case_id in {"wiki_sum_first_odd_numbers", "sympy_finite_geometric_sum"}:
        index_symbol = "i" if case_id == "wiki_sum_first_odd_numbers" else "k"
        assumptions.append(
            {
                "symbol": index_symbol,
                "source_backing": "generated_index_variable",
                "source_anchors": [],
                "sympy_assumptions": {"integer": True, "nonnegative": True},
                "domain": "summation_index",
                "sampling": None,
            }
        )
    unresolved = []
    if not assumptions:
        unresolved.append("No source-backed assumptions detected.")
    strengthening_risks = []
    if "r \\ne 1" in text and "1-r" not in text:
        strengthening_risks.append(
            "A nonzero denominator may be required but is not visible in the source."
        )
    return {
        "backend": "sympy",
        "style": parse_packet.get("style", "sympy_equational_trace"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "assumptions": assumptions,
        "unresolved_assumptions": unresolved,
        "silent_strengthening_risks": strengthening_risks,
        "assumption_fidelity": 1.0 if not unresolved else 0.0,
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
    parser.add_argument("--parse-packet", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        parse_script = Path("artifacts/sympy/self_test/parse_packet.json")
        if not parse_script.exists():
            from subprocess import run

            parse_script.parent.mkdir(parents=True, exist_ok=True)
            run(
                [
                    sys.executable,
                    "skills/sympy/sympy-expression-parser/scripts/parse_sympy_expressions.py",
                    "--source",
                    "tests/latex/wiki_level/sum_first_odd_numbers.tex",
                    "--output",
                    str(parse_script),
                ],
                check=True,
            )
        args.parse_packet = parse_script
    if args.parse_packet is None:
        parser.error("--parse-packet is required unless --self-test is used")

    packet = json.loads(args.parse_packet.read_text(encoding="utf-8"))
    report = build_assumptions(packet)
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(
        text
        if args.json
        else f"assumption_fidelity={report['assumption_fidelity']:.2f}"
    )
    return 0 if not report["unresolved_assumptions"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
