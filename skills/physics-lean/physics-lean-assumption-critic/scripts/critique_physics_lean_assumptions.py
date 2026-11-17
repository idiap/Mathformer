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

"""Critique contextual assumption drift in Lean physics artifacts."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Sequence

ASSUMPTION_PATTERNS = {
    "nonzero": [
        r"!=\s*0",
        r"≠\s*0",
        r"nonzero",
        r"denominator",
        r"divide",
        r"division",
        r"reciprocal",
    ],
    "positivity": [r"0\s*<", r"positive", r"positivity", r"sqrt", r"log"],
    "smoothness": [
        r"smooth",
        r"differentiable",
        r"derivative",
        r"∂",
        r"\bd/d",
        r"gradient",
        r"curl",
        r"divergence",
    ],
    "boundary": [r"boundary", r"initial condition", r"terminal condition"],
    "frame": [r"frame", r"coordinate", r"inertial", r"basis", r"gauge", r"observer"],
    "regime": [
        r"approx",
        r"ideal",
        r"neglect",
        r"small",
        r"linearized",
        r"nonrelativistic",
    ],
}


LEAN_ASSUMPTION_PATTERNS = {
    "nonzero": [r"≠\s*0", r"!=\s*0", r"NeZero", r"Nonzero"],
    "positivity": [r"0\s*<", r"Positive", r"pos"],
    "smoothness": [r"Differentiable", r"ContDiff", r"Continuous", r"Smooth"],
    "boundary": [r"boundary", r"Boundary", r"initial", r"Initial"],
    "frame": [r"Frame", r"frame", r"Coordinate", r"Gauge"],
    "regime": [r"Regime", r"regime", r"approx", r"Approx"],
}


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
    if path is None:
        return ""
    return path.read_text(encoding="utf-8")


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


def category_present(text: str, category: str, table: dict[str, list[str]]) -> bool:
    """Document the responsibility of ``category_present``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``category_present`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return any(re.search(pattern, text, re.I) for pattern in table[category])


def packet_categories(packet: dict[str, Any]) -> set[str]:
    """Document the responsibility of ``packet_categories``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``packet_categories`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    text = json.dumps(packet, ensure_ascii=False)
    found: set[str] = set()
    for category in ASSUMPTION_PATTERNS:
        if category_present(text, category, ASSUMPTION_PATTERNS):
            found.add(category)
    return found


def packet_has_labels(packet: dict[str, Any]) -> bool:
    """Document the responsibility of ``packet_has_labels``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``packet_has_labels`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    text = json.dumps(packet, ensure_ascii=False).lower()
    return any(
        label in text
        for label in ["source-backed", "mathlib-backed", "generated-support", "blocked"]
    )


def build_report(
    *, source_text: str, lean_text: str, assumption_packet: dict[str, Any]
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
    source_categories = {
        category
        for category in ASSUMPTION_PATTERNS
        if category_present(source_text, category, ASSUMPTION_PATTERNS)
    }
    lean_categories = {
        category
        for category in LEAN_ASSUMPTION_PATTERNS
        if category_present(lean_text, category, LEAN_ASSUMPTION_PATTERNS)
    }
    packet_cats = packet_categories(assumption_packet)
    introduced = sorted(lean_categories - source_categories - packet_cats)
    missing = sorted((source_categories | packet_cats) - lean_categories)

    for category in introduced:
        findings.append(
            {
                "severity": (
                    "critical"
                    if category in {"positivity", "nonzero", "smoothness"}
                    else "error"
                ),
                "code": f"hidden_{category}_assumption",
                "message": f"Lean appears to introduce {category} assumptions not backed by source text or the assumption packet.",
            }
        )
    for category in missing:
        findings.append(
            {
                "severity": (
                    "error" if category in {"nonzero", "frame", "regime"} else "warning"
                ),
                "code": f"missing_{category}_assumption",
                "message": f"Source or packet indicates {category} context, but the Lean artifact does not expose it.",
            }
        )
    if assumption_packet and not packet_has_labels(assumption_packet):
        findings.append(
            {
                "severity": "error",
                "code": "unlabeled_assumptions",
                "message": "Assumption packet exists but does not visibly label assumptions as source-backed, mathlib-backed, generated-support, or blocked.",
            }
        )
    if not assumption_packet and (source_categories or lean_categories):
        findings.append(
            {
                "severity": "error",
                "code": "missing_assumption_packet",
                "message": "Assumption-bearing source or Lean artifact lacks an assumption packet.",
            }
        )

    severity_rank = {"info": 0, "warning": 1, "error": 2, "critical": 3}
    max_severity = max(
        (severity_rank[item["severity"]] for item in findings), default=0
    )
    status = "fail" if max_severity >= 2 else "warn" if max_severity == 1 else "pass"
    return {
        "style": "physics_lean_assumption_critic_report",
        "status": status,
        "source_categories": sorted(source_categories),
        "lean_categories": sorted(lean_categories),
        "packet_categories": sorted(packet_cats),
        "findings": findings,
        "generative_probe_hints": [
            "Ask Codex exec to remove each Lean side condition and identify the first broken physics step.",
            "Ask Codex exec to cite the exact source phrase for every positivity, nonzero, smoothness, frame, and regime assumption.",
            "Ask Codex exec to construct an opposite frame or sign convention and test whether the theorem statement changes.",
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
    parser.add_argument("--lean-file", type=Path)
    parser.add_argument("--lean-text")
    parser.add_argument("--assumption-packet", type=Path)
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
    if args.self_test:
        report = build_report(
            source_text="Derive the relation in an inertial frame.",
            lean_text="theorem bad (x : Real) (hx : 0 < x) : x = x := by rfl",
            assumption_packet={},
        )
        assert report["status"] == "fail"
        assert any(
            item["code"] == "hidden_positivity_assumption"
            for item in report["findings"]
        )
    else:
        report = build_report(
            source_text=read_text(args.source_file, args.source_text),
            lean_text=read_text(args.lean_file, args.lean_text),
            assumption_packet=load_json(args.assumption_packet),
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
