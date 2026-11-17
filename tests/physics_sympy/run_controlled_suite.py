#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.
#
# Intent:
#   Encode regression checks that catch parser breakage, semantic drift, and missing workflow evidence.
#
# Function:
#   Contains executable tests, fixtures, and manifests used for local and CI validation.
#
# Maintenance Notes:
#   Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.

"""Run controlled physics derivation cases through the SymPy physics pipeline."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import socket
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def dependency_blocker(exc: BaseException) -> dict[str, Any]:
    """Return a structured dependency blocker instead of a traceback."""
    return {
        "ok": False,
        "backend": "sympy",
        "style": "physics_sympy_dependency_blocker",
        "phase": "controlled_physics_sympy_suite",
        "case_count": 0,
        "findings": [
            {
                "severity": "high",
                "code": "missing_required_dependency",
                "dependency": "sympy",
                "message": "SymPy is unavailable in this Python environment; rerun through .venv/bin/python or install the repo dependencies.",
                "exception": f"{type(exc).__name__}: {exc}",
            }
        ],
        "missing_required": ["sympy"],
        "rerun_with": ".venv/bin/python tests/physics_sympy/run_controlled_suite.py --json",
    }


def controlled_exception_report(exc: BaseException) -> dict[str, Any] | None:
    """Classify only the missing-SymPy condition owned by this CLI."""
    if (
        isinstance(exc, ModuleNotFoundError)
        and exc.name
        and exc.name.startswith("sympy")
    ):
        return dependency_blocker(exc)
    return None


def emit_controlled_report(report: dict[str, Any], json_output: bool) -> int:
    """Shared process output and exit status for CLI and staged execution."""
    if json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    else:
        print(f"ok: {report['ok']}")
        print(f"case_count: {report['case_count']}")
    return 0 if report["ok"] else 3


def staged_controlled_suite(
    output_root: Path, include_details: bool, descriptor: int
) -> dict[str, Any]:
    """Advance the same suite in its native interpreter over a private channel.

    The descriptor is inherited from the registered MCP controller. Scientific
    stdout/stderr remain on the ordinary process pipes. EOF aborts the run;
    there is no checkpoint, retry, alternate algorithm, or mock implementation.
    """
    with (
        socket.socket(fileno=descriptor) as transport,
        transport.makefile("rw", encoding="utf-8") as channel,
    ):

        def send(value):
            channel.write(json.dumps(value, ensure_ascii=False, default=str) + "\n")
            channel.flush()

        def attempt(callback):
            try:
                return callback()
            except Exception as exc:
                report = controlled_exception_report(exc)
                send(
                    {
                        "error": {
                            "kind": (
                                "missing_sympy"
                                if report is not None
                                else "unhandled_exception"
                            ),
                            "message": str(exc),
                        }
                    }
                )
                raise

        def initialize():
            from backends.sympy.MathformerPhysicsSympy import pipeline

            return pipeline, pipeline.controlled_suite_initialize(output_root)

        pipeline, cases = attempt(initialize)
        send({"cases": cases})
        for line in channel:
            command = json.loads(line)
            if command == "step":
                cases = attempt(
                    lambda: pipeline.controlled_suite_step(
                        output_root, cases, include_details
                    )
                )
                send(
                    {
                        "cases": cases,
                        "done": pipeline.controlled_suite_done(cases),
                        "error": {"kind": "none"},
                    }
                )
            elif command == "finish":
                if not pipeline.controlled_suite_done(cases):
                    raise ValueError("unconsumed controlled cases")
                return attempt(
                    lambda: pipeline.controlled_suite_finalize(output_root, cases)
                )
            else:
                raise ValueError("unknown controlled stage")
        raise RuntimeError("controlled stage channel closed before finalization")


def main() -> int:
    """Document the responsibility of ``main``.

    Motivation:
        Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.

    Intent:
        Serve as the command-line entry point and coordinate argument parsing, execution, and reporting.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("artifacts/physics_sympy/controlled_suite"),
    )
    parser.add_argument(
        "--include-details",
        action="store_true",
        help="Embed full per-case consistency reports in the suite JSON instead of only paths and summaries.",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        descriptor = os.environ.get("MATHFORMER_CONTROLLED_STAGE_FD")
        if descriptor is not None:
            report = staged_controlled_suite(
                (REPO_ROOT / args.output_root).resolve(),
                args.include_details,
                int(descriptor),
            )
        else:
            from backends.sympy.MathformerPhysicsSympy.pipeline import controlled_suite

            report = controlled_suite(
                (REPO_ROOT / args.output_root).resolve(),
                include_details=args.include_details,
            )
    except ModuleNotFoundError as exc:
        report = controlled_exception_report(exc)
        if report is None:
            raise
    return emit_controlled_report(report, args.json)


if __name__ == "__main__":
    raise SystemExit(main())
