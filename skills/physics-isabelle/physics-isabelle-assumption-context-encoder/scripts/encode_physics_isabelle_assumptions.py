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

"""Build an Isabelle/HOL-facing contextual-assumption packet for physics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any, Sequence

PATTERNS = {
    "positivity": r"> 0|positive|mass|temperature|radius|frequency",
    "nonzero": r"nonzero|non-zero|not zero|denominator|divide|division|ratio|fraction|\\frac",
    "smoothness": r"smooth|differentiable|partial|derivative|gradient|curl|divergence",
    "boundary": r"boundary|endpoint|infinity|vanish|surface|closed",
    "frame": r"Cartesian|spherical|coordinate|component|projection|unit vector|basis",
    "regime": r"constant|ideal|nonrelativistic|time-independent|charge-free|normalized|non-degenerate",
    "operator": r"Hamiltonian|self-adjoint|operator|commutator|ket|bra|Hilbert|curl|divergence",
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
    obligations: list[str] = []
    if flags["positivity"]:
        obligations.append(
            'encode positivity as an Isabelle assumes clause, e.g. `assumes m_pos: "m > 0"`'
        )
    if flags["nonzero"]:
        obligations.append(
            'encode nonzero side conditions, e.g. `assumes mu0_nonzero: "mu0 ~= 0"`'
        )
    if flags["smoothness"]:
        obligations.append(
            "label smoothness/differentiability assumptions as source-backed or generated-support"
        )
    if flags["boundary"]:
        obligations.append(
            "encode boundary conditions in a locale/context or theorem assumptions"
        )
    if flags["frame"]:
        obligations.append(
            "encode coordinate frame, basis, projection, and sign convention assumptions"
        )
    if flags["regime"]:
        obligations.append(
            "encode physical regime assumptions without silent strengthening"
        )
    if flags["operator"]:
        obligations.append(
            "encode operator laws as explicit assumptions or supporting lemmas"
        )
    if not obligations:
        obligations.append(
            "record no detected contextual assumptions; require reviewer confirmation"
        )
    return {
        "case_id": case_id,
        "style": "isabelle_physics_assumption_context_packet",
        "backend": "isabelle",
        "detected_context": flags,
        "isabelle_encoding_targets": obligations,
        "source_status_policy": {
            "source_backed": "assumption appears in question, derivation, or benchmark metadata",
            "generated_support": "assumption needed for a valid Isabelle abstraction but not directly stated",
            "blocked": "assumption would materially strengthen the source and needs review",
        },
        "complete_status_blockers": [
            "silent_strengthening",
            "target_claim_as_assumption",
            "unexplained_operator_law",
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
    parser.add_argument("--case-id", default="physics_isabelle_case")
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
        "Assume mu0 is nonzero, fields are smooth, and coordinates are Cartesian."
        if args.self_test
        else read_source(args.source_file, args.source_text)
    )
    packet = build_packet(source, args.case_id)
    if args.self_test:
        assert packet["detected_context"]["nonzero"]
        assert packet["detected_context"]["frame"]
        assert packet["backend"] == "isabelle"
    text = json.dumps(packet, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
