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

"""Classify Lean diagnostics for physics formalization refinement."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
from typing import Any, Sequence

RULES = [
    (
        "mathlib_or_import",
        r"unknown identifier|unknown constant|module .* not found|invalid import",
    ),
    (
        "type_system",
        r"type mismatch|application type mismatch|failed to synthesize|invalid field notation",
    ),
    (
        "proof_gap",
        r"unsolved goals|tactic .* failed|no goals to be solved|declaration uses 'sorry'",
    ),
    ("unit_dimension", r"dimension|unit|quantity|Dim|PhysDim"),
    (
        "assumption_context",
        r"failed to prove|nonzero|positive|differentiable|integrable|smooth|side condition",
    ),
    ("syntax", r"unexpected token|expected|invalid syntax|parser"),
    ("empty_formalism_risk", r"axiom|admit|sorry|exact h|assumption"),
]


def classify(text: str) -> dict[str, Any]:
    """Document the responsibility of ``classify``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``classify`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    findings = []
    warning_findings = []
    counts: Counter[str] = Counter()
    for line_no, line in enumerate(text.splitlines(), start=1):
        if "warning:" in line.lower():
            warning_findings.append(
                {
                    "line": line_no,
                    "category": "lean_warning",
                    "message": line.strip()[:400],
                }
            )
            continue
        for category, pattern in RULES:
            if re.search(pattern, line, re.I):
                counts[category] += 1
                findings.append(
                    {
                        "line": line_no,
                        "category": category,
                        "message": line.strip()[:400],
                    }
                )
    if not text.strip():
        status = "empty"
    elif counts:
        status = "diagnostics_classified"
    elif warning_findings:
        status = "warning_only"
    else:
        status = "no_known_diagnostics"
    repair_targets = []
    if counts["mathlib_or_import"]:
        repair_targets.append("run mathlib/import grounding before proof repair")
    if counts["type_system"]:
        repair_targets.append("repair physics quantity types or projection lemmas")
    if counts["unit_dimension"]:
        repair_targets.append("repair dimension/unit packet or dimension lemmas")
    if counts["assumption_context"]:
        repair_targets.append("encode missing contextual side conditions explicitly")
    if counts["proof_gap"]:
        repair_targets.append("run Lean formal refinement on localized goals")
    if counts["empty_formalism_risk"]:
        repair_targets.append(
            "run realness and non-empty-formalism gate before acceptance"
        )
    return {
        "status": status,
        "category_counts": dict(counts),
        "findings": findings,
        "warning_findings": warning_findings,
        "repair_targets": repair_targets,
    }


def read_text(path: Path | None, text: str | None) -> str:
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
    if text is not None:
        return text
    if path is not None:
        return path.read_text(encoding="utf-8", errors="replace")
    return ""


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
    parser.add_argument("--log-file", type=Path)
    parser.add_argument("--text")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
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
    text = (
        "error: unknown identifier PhysDim\nerror: type mismatch\nunsolved goals"
        if args.self_test
        else read_text(args.log_file, args.text)
    )
    report = classify(text)
    if args.self_test:
        assert report["category_counts"]["mathlib_or_import"] == 1
        assert report["category_counts"]["type_system"] == 1
        assert report["category_counts"]["proof_gap"] == 1
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
