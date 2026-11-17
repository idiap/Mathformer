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

"""Build a Lean-facing contextual-assumption packet for physics derivations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any, Sequence

PATTERNS = {
    "positivity": r"> 0|positive|mass|temperature|radius|frequency",
    "nonzero": r"nonzero|not zero|denominator|divide|/",
    "smoothness": r"smooth|differentiable|partial|derivative|gradient|curl|divergence",
    "boundary": r"boundary|endpoint|infinity|vanish|surface|closed",
    "frame": r"Cartesian|spherical|coordinate|component|projection|unit vector|basis",
    "regime": r"constant|ideal|nonrelativistic|time-independent|charge-free|normalized|non-degenerate",
    "operator": r"Hamiltonian|self-adjoint|operator|commutator|ket|bra|Hilbert",
}


def detect(source: str) -> dict[str, bool]:
    """Document the responsibility of ``detect``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``detect`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return {
        name: bool(re.search(pattern, source, re.I))
        for name, pattern in PATTERNS.items()
    }


def build_packet(source: str, case_id: str) -> dict[str, Any]:
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
    flags = detect(source)
    obligations = []
    labeled_obligations = []
    if flags["positivity"]:
        obligations.append(
            "encode positivity hypotheses, e.g. `0 < m`, `0 < T`, or source-specific positivity"
        )
        labeled_obligations.append(
            {"kind": "positivity", "source_status": "source-backed"}
        )
    if flags["nonzero"]:
        obligations.append("encode nonzero side conditions for division and field_simp")
        labeled_obligations.append(
            {"kind": "nonzero", "source_status": "source-backed"}
        )
    if flags["smoothness"]:
        obligations.append(
            "encode differentiability/smoothness assumptions before derivative laws"
        )
        labeled_obligations.append(
            {"kind": "smoothness", "source_status": "source-backed"}
        )
    if flags["boundary"]:
        obligations.append(
            "encode boundary conditions and whether they are source-backed or generated-support"
        )
        labeled_obligations.append(
            {"kind": "boundary", "source_status": "source-backed"}
        )
    if flags["frame"]:
        obligations.append(
            "encode coordinate frame, basis, projection, and sign convention"
        )
        labeled_obligations.append({"kind": "frame", "source_status": "source-backed"})
    if flags["regime"]:
        obligations.append("encode physical regime and idealization assumptions")
        labeled_obligations.append({"kind": "regime", "source_status": "source-backed"})
    if flags["operator"]:
        obligations.append(
            "encode operator algebra assumptions without pretending Lean has a full quantum model"
        )
        labeled_obligations.append(
            {"kind": "operator", "source_status": "source-backed"}
        )
    if not obligations:
        obligations.append(
            "record that no extra contextual assumptions were detected; require reviewer confirmation"
        )
        labeled_obligations.append(
            {"kind": "none_detected", "source_status": "blocked"}
        )

    return {
        "case_id": case_id,
        "style": "lean_physics_assumption_context_packet",
        "detected_context": flags,
        "lean_encoding_targets": obligations,
        "assumption_support_labels": sorted(
            {item["source_status"] for item in labeled_obligations}
        ),
        "labeled_contextual_assumptions": labeled_obligations,
        "source_status_policy": {
            "source_backed": "assumption appears in question, derivation, or benchmark metadata",
            "generated_support": "assumption needed to type/check Lean but not directly stated",
            "blocked": "assumption would materially strengthen source and needs review",
        },
        "complete_status_blockers": [
            "silent_strengthening",
            "target_claim_as_assumption",
            "unexplained_smoothness_or_domain_requirement",
            "missing_frame_or_sign_convention_for_component_claim",
        ],
    }


def read_source(path: Path | None, text: str | None) -> str:
    """Document the responsibility of ``read_source``.

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
        return path.read_text(encoding="utf-8")
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
    parser.add_argument("--source-file", type=Path)
    parser.add_argument("--source-text")
    parser.add_argument("--case-id", default="physics_lean_case")
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
    source = (
        "For a nonrelativistic particle in Cartesian coordinates, assume m > 0 and A is smooth."
        if args.self_test
        else read_source(args.source_file, args.source_text)
    )
    packet = build_packet(source, args.case_id)
    if args.self_test:
        assert packet["detected_context"]["positivity"]
        assert packet["detected_context"]["frame"]
    text = json.dumps(packet, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
