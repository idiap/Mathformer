#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402 - imports follow explicit direct-script path setup
#
#

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

"""Run the MathformerLib SymPy physics KdV entry end to end."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from libraries.MathformerLib.SympyPhysics.Solvers.AnalyticSoliton import (
    KdVOneSoliton,
)
from libraries.MathformerLib.SympyPhysics.Solvers.PseudoSpectralPDE import (
    KdVOneSolitonSimulation,
)


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
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    derivation = KdVOneSoliton.run_all()
    simulation = KdVOneSolitonSimulation.run_all()
    report = {
        "ok": bool(derivation["ok"] and simulation["passed"]),
        "derivation": derivation,
        "simulation": simulation,
        "library_path": "libraries/MathformerLib/SympyPhysics/Solvers",
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    else:
        print(f"ok: {report['ok']}")
        print(f"derivation_status: {derivation['status']}")
        print(f"simulation_max_abs_error: {simulation['max_abs_error']:.3e}")
    return 0 if report["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
