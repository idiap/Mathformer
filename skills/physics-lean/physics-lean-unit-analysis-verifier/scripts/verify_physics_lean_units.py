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

"""Heuristic unit/dimension discipline verifier for Lean physics artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any, Sequence

THEOREM_RE = re.compile(r"^\s*(theorem|lemma)\s+([A-Za-z0-9_'.]+)", re.MULTILINE)
RAW_REAL_BINDER_RE = re.compile(r"\([^)]*:\s*(?:ℝ|Real)\)")
DIM_MARKERS = [
    "PhysDim",
    "Dimension",
    "dimension",
    "dimensional",
    "Quantity",
    "Unit",
    "unit",
]
CONTEXT_MARKERS = [
    "PhysicsContext",
    "Assumptions",
    "assumption",
    "regime",
    "frame",
    "law",
    "Source anchors",
]
FORBIDDEN_RE = re.compile(
    r"\baxiom\b|target.*axiom|final.*axiom|\badmit\b|\bsorry\b", re.I
)


def verify(text: str) -> dict[str, Any]:
    """Document the responsibility of ``verify``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Validate assumptions or artifacts and return explicit evidence about whether the contract holds.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    theorem_count = len(THEOREM_RE.findall(text))
    raw_real_binders = len(RAW_REAL_BINDER_RE.findall(text))
    dim_marker_hits = sum(text.count(marker) for marker in DIM_MARKERS)
    context_marker_hits = sum(text.count(marker) for marker in CONTEXT_MARKERS)
    forbidden_hits = [m.group(0) for m in FORBIDDEN_RE.finditer(text)]

    findings = []
    if theorem_count == 0:
        findings.append(
            {
                "severity": "high",
                "code": "no_theorem_or_lemma",
                "message": "No theorem-like Lean declaration found.",
            }
        )
    if dim_marker_hits == 0:
        findings.append(
            {
                "severity": "high",
                "code": "missing_dimension_policy",
                "message": "No dimension/unit/quantity markers found.",
            }
        )
    if context_marker_hits == 0:
        findings.append(
            {
                "severity": "medium",
                "code": "missing_context_policy",
                "message": "No physics context, regime, frame, law, or source-anchor markers found.",
            }
        )
    if raw_real_binders >= 4 and dim_marker_hits == 0:
        findings.append(
            {
                "severity": "high",
                "code": "raw_real_erasure_risk",
                "message": "Many raw Real binders and no dimension policy.",
            }
        )
    if forbidden_hits:
        findings.append(
            {
                "severity": "high",
                "code": "forbidden_completion_marker",
                "message": "Artifact contains forbidden completion markers.",
                "matches": forbidden_hits[:10],
            }
        )

    high = sum(1 for finding in findings if finding["severity"] == "high")
    status = "pass" if high == 0 and dim_marker_hits > 0 else "fail"
    return {
        "status": status,
        "metrics": {
            "theorem_count": theorem_count,
            "raw_real_binder_count": raw_real_binders,
            "dimension_marker_hits": dim_marker_hits,
            "context_marker_hits": context_marker_hits,
            "forbidden_marker_count": len(forbidden_hits),
        },
        "findings": findings,
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
    parser.add_argument("--lean-file", type=Path)
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
        (
            "/- Source anchors: src_L0001; PhysicsContext; Quantity; PhysDim -/\n"
            "theorem force_units (F : Quantity forceDim) : True := by trivial\n"
        )
        if args.self_test
        else read_text(args.lean_file, args.text)
    )
    report = verify(text)
    if args.self_test:
        assert report["status"] == "pass"
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
