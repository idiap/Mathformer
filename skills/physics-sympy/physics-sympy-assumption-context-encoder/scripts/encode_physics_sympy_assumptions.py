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

"""Encode contextual assumptions for SymPy physics derivations."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Sequence

PATTERNS = [
    ("positive", r"\bpositive|greater than zero|> 0\b", "positivity"),
    ("nonzero", r"\bnonzero|non-zero|not zero|!= 0|\\ne 0\b", "nonzero"),
    ("real", r"\breal\b", "domain"),
    ("smooth", r"\bsmooth|differentiable|continuous\b", "smoothness"),
    ("inertial_frame", r"\binertial frame|inertial observer\b", "frame"),
    ("constant", r"\bconstant|uniform\b", "constancy"),
    ("frictionless", r"\bfrictionless|no friction\b", "idealization"),
    ("ideal", r"\bideal\b", "idealization"),
    ("initial_condition", r"\binitial|at t ?= ?0\b", "initial_condition"),
    ("boundary_condition", r"\bboundary|at x ?= ?0\b", "boundary_condition"),
    ("gauge", r"\bgauge\b", "gauge"),
    ("approximation", r"\bsmall angle|approximation|neglect|ignore\b", "approximation"),
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


def collect_packet_assumptions(
    packet: dict[str, Any], label: str
) -> list[dict[str, Any]]:
    """Document the responsibility of ``collect_packet_assumptions``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``collect_packet_assumptions`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    raw = (
        packet.get("assumptions")
        or packet.get("entries")
        or packet.get("ASSUMPTIONS")
        or []
    )
    if isinstance(raw, dict):
        raw = list(raw.values())
    assumptions: list[dict[str, Any]] = []
    for index, item in enumerate(raw if isinstance(raw, list) else [raw]):
        if isinstance(item, dict):
            name = str(
                item.get("id")
                or item.get("name")
                or item.get("assumption")
                or f"{label}_{index}"
            )
            text = str(item.get("text") or item.get("assumption") or item)
            support = item.get("support") or item.get("label") or "source_backed"
        else:
            name = f"{label}_{index}"
            text = str(item)
            support = "source_backed"
        assumptions.append(
            {
                "id": name,
                "text": text,
                "category": label,
                "support": support,
                "source_anchor": (
                    item.get("source_anchor") if isinstance(item, dict) else None
                ),
            }
        )
    return assumptions


def source_assumptions(source_text: str) -> list[dict[str, Any]]:
    """Document the responsibility of ``source_assumptions``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``source_assumptions`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    assumptions: list[dict[str, Any]] = []
    for name, pattern, category in PATTERNS:
        if re.search(pattern, source_text, re.I):
            assumptions.append(
                {
                    "id": name,
                    "text": f"Source indicates {name.replace('_', ' ')}.",
                    "category": category,
                    "support": "source_backed",
                    "source_anchor": "source_text",
                }
            )
    return assumptions


def infer_sympy_assumptions(assumptions: list[dict[str, Any]]) -> dict[str, Any]:
    """Document the responsibility of ``infer_sympy_assumptions``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``infer_sympy_assumptions`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    flags: dict[str, Any] = {}
    categories = {item["category"] for item in assumptions}
    ids = {item["id"] for item in assumptions}
    if "domain" in categories:
        flags["real"] = True
    if "positivity" in categories or "positive" in ids:
        flags["positive"] = True
        flags["nonzero"] = True
    if "nonzero" in ids:
        flags["nonzero"] = True
    return flags


def build_packet(
    *,
    source_text: str,
    regime_packet: dict[str, Any],
    frame_packet: dict[str, Any],
    symbol_packet: dict[str, Any],
    equation_surface: dict[str, Any],
) -> dict[str, Any]:
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
    assumptions = []
    assumptions.extend(source_assumptions(source_text))
    assumptions.extend(collect_packet_assumptions(regime_packet, "regime"))
    assumptions.extend(collect_packet_assumptions(frame_packet, "frame"))
    assumptions.extend(collect_packet_assumptions(symbol_packet, "symbol"))

    side_conditions = []
    for assumption in assumptions:
        if assumption["category"] in {
            "positivity",
            "nonzero",
            "smoothness",
            "initial_condition",
            "boundary_condition",
        }:
            side_conditions.append(
                {
                    "id": f"side_{assumption['id']}",
                    "source_assumption": assumption["id"],
                    "category": assumption["category"],
                    "support": assumption["support"],
                }
            )

    sympy_assumptions = infer_sympy_assumptions(assumptions)
    findings: list[dict[str, Any]] = []
    quantity_count = (
        len(equation_surface.get("QUANTITY_SURFACE", []))
        if isinstance(equation_surface, dict)
        else 0
    )
    if quantity_count and not assumptions:
        findings.append(
            {
                "severity": "warning",
                "code": "no_contextual_assumptions",
                "message": "Quantity surface exists but no contextual assumptions were found.",
                "repair_surface": "assumption_context",
            }
        )
    generated_unlabeled = [
        item
        for item in assumptions
        if "generated" in str(item.get("support", "")).lower()
        and not item.get("source_anchor")
    ]
    if generated_unlabeled:
        findings.append(
            {
                "severity": "warning",
                "code": "generated_assumption_without_anchor",
                "message": "Generated support assumptions should carry explicit provenance.",
                "repair_surface": "assumption_context",
                "assumptions": [item["id"] for item in generated_unlabeled],
            }
        )

    max_severity = max(
        (
            {"info": 0, "warning": 1, "error": 2, "critical": 3}[f["severity"]]
            for f in findings
        ),
        default=0,
    )
    return {
        "style": "physics_sympy_assumption_context_packet",
        "status": (
            "fail" if max_severity >= 2 else "warn" if max_severity == 1 else "pass"
        ),
        "CONTEXT_ASSUMPTIONS": assumptions,
        "SIDE_CONDITIONS": side_conditions,
        "SYMPY_ASSUMPTION_FLAGS": sympy_assumptions,
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
    parser.add_argument("--regime-packet", type=Path)
    parser.add_argument("--frame-packet", type=Path)
    parser.add_argument("--symbol-packet", type=Path)
    parser.add_argument("--equation-surface", type=Path)
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
        packet = build_packet(
            source_text="Assume m is positive and the motion is in an inertial frame.",
            regime_packet={},
            frame_packet={},
            symbol_packet={},
            equation_surface={"QUANTITY_SURFACE": [{"symbol": "m"}]},
        )
        assert packet["SYMPY_ASSUMPTION_FLAGS"]["positive"] is True
        assert any(
            item["id"] == "inertial_frame" for item in packet["CONTEXT_ASSUMPTIONS"]
        )
    else:
        packet = build_packet(
            source_text=read_text(args.source_file, args.source_text),
            regime_packet=load_json(args.regime_packet),
            frame_packet=load_json(args.frame_packet),
            symbol_packet=load_json(args.symbol_packet),
            equation_surface=load_json(args.equation_surface),
        )
    output = json.dumps(packet, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
