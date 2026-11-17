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

"""Verify the shape and evidence of SymPy transformation traces."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def load_module(path: Path) -> Any:
    """Document the responsibility of ``load_module``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify(path: Path) -> dict[str, Any]:
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
    module = load_module(path)
    trace = module.explain_trace()
    symbolic = {}
    try:
        symbolic_result = module.validate_symbolic()
        symbolic = (
            symbolic_result
            if isinstance(symbolic_result, dict)
            else {"passed": bool(symbolic_result)}
        )
    except Exception as exc:
        symbolic = {"passed": False, "error": f"{type(exc).__name__}: {exc}"}
    findings = []
    for idx, step in enumerate(trace, start=1):
        missing = []
        if not (step.get("input") or step.get("source") or step.get("source_anchors")):
            missing.append("input")
        if not (step.get("output") or step.get("expression")):
            missing.append("output")
        if not (step.get("justification") or step.get("rule")):
            missing.append("justification")
        if not (step.get("api") or step.get("rule")):
            missing.append("api_or_rule")
        if missing:
            findings.append({"step": idx, "missing": missing, "severity": "high"})
    if not symbolic.get("passed"):
        findings.append(
            {
                "step": None,
                "missing": ["symbolic_preservation_evidence"],
                "severity": "high",
                "detail": symbolic.get("error"),
            }
        )
    return {
        "backend": "sympy",
        "artifact": str(path),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "step_count": len(trace),
        "findings": findings,
        "symbolic_preservation_evidence": bool(symbolic.get("passed")),
        "passed": not findings and bool(trace),
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
    parser.add_argument("--artifact", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        args.artifact = Path(
            "backends/sympy/MathformerSympy/AutoformalizedSumFirstOddNumbers.py"
        )
        if not args.artifact.exists():
            subprocess.run([sys.executable, "tests/sympy/run_wiki_case.py"], check=True)
    if args.artifact is None:
        parser.error("--artifact is required unless --self-test is used")

    report = verify(args.artifact)
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text if args.json else f"trace passed={report['passed']}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
