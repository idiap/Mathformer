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

"""Build installed-library grounding evidence for a physics SymPy case."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import backends.sympy.MathformerPhysicsSympy.pipeline as pipeline  # noqa: E402 - direct-script path setup above


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
    parser.add_argument(
        "--case-id", choices=pipeline.all_case_ids(), default="formalphysics_0000"
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def run_self_test() -> dict[str, object]:
    """Document the responsibility of ``run_self_test``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Run the local workflow step and surface success, failure, and evidence in a predictable form.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    high = pipeline.sympy_library_grounding("formalphysics_0000")
    assert high["grounding_level"] == "high", high

    original = pipeline.qualified_available
    try:

        def missing_vector(name: str) -> bool:
            """Document the responsibility of ``run_self_test.missing_vector``.

            Motivation:
                Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

            Intent:
                Run the local workflow step and surface success, failure, and evidence in a predictable form.

            Inputs:
                Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

            Outputs:
                Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
            """
            if name.startswith("sympy.vector") or name.startswith(
                "sympy.physics.vector"
            ):
                return False
            return original(name)

        pipeline.qualified_available = missing_vector
        medium = pipeline.sympy_library_grounding("formalphysics_0020")
        assert medium["grounding_level"] == "medium", medium
        assert (
            "missing_sympy_library_surface:vector_analysis"
            in medium["completion_blockers"]
        ), medium
    finally:
        pipeline.qualified_available = original

    try:

        def missing_units(name: str) -> bool:
            """Document the responsibility of ``run_self_test.missing_units``.

            Motivation:
                Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

            Intent:
                Run the local workflow step and surface success, failure, and evidence in a predictable form.

            Inputs:
                Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

            Outputs:
                Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
            """
            if name.startswith("sympy.physics.units"):
                return False
            return original(name)

        pipeline.qualified_available = missing_units
        low = pipeline.sympy_library_grounding("formalphysics_0000")
        assert low["grounding_level"] == "low", low
        assert (
            "missing_sympy_library_surface:units_dimensions"
            in low["completion_blockers"]
        ), low
    finally:
        pipeline.qualified_available = original

    return {"ok": True, "style": "physics_sympy_library_grounding_packet"}


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
    packet = (
        run_self_test()
        if args.self_test
        else pipeline.sympy_library_grounding(args.case_id)
    )
    output = json.dumps(packet, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(
            output
            if args.json or args.self_test
            else f"grounding_level={packet['grounding_level']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
