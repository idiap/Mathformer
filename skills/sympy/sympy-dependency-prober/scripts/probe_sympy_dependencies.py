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

"""Probe dependencies for the Mathformer SymPy backend."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib
import json
from pathlib import Path
import sys
from typing import Any

REQUIRED = ["sympy", "mpmath", "numpy", "pydantic", "pylatexenc"]
RECOMMENDED = [
    "hypothesis",
    "pytest",
    "lark",
    "latex2sympy2_extended",
    "bs4",
    "requests",
    "sphinx",
    "sphinx_autodoc_typehints",
    "networkx",
    "pandas",
    "plotly",
    "z3",
]


def probe_module(name: str) -> dict[str, Any]:
    """Document the responsibility of ``probe_module``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``probe_module`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    try:
        module = importlib.import_module(name)
    except Exception as exc:
        return {
            "module": name,
            "available": False,
            "error": f"{type(exc).__name__}: {exc}",
        }
    return {
        "module": name,
        "available": True,
        "version": getattr(module, "__version__", None),
        "file": getattr(module, "__file__", None),
    }


def build_report() -> dict[str, Any]:
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
    required = [probe_module(name) for name in REQUIRED]
    recommended = [probe_module(name) for name in RECOMMENDED]
    missing_required = [item["module"] for item in required if not item["available"]]
    return {
        "backend": "sympy",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "executable": sys.executable,
        "required": required,
        "recommended": recommended,
        "missing_required": missing_required,
        "ok": not missing_required,
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
    parser.add_argument("--output", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = build_report()
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text if args.json else f"SymPy dependency probe ok={report['ok']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
