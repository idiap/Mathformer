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

"""Source-to-documentation smoke path."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT = REPO_ROOT / "artifacts" / "test_program" / "e2e_source_to_docs.json"


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
    command = [
        sys.executable,
        "tests/test_program/run_comprehensive_tests.py",
        "--module-family",
        "source",
        "--module-family",
        "sympy",
        "--module-family",
        "docs",
        "--output-file",
        str(OUT),
    ]
    if args.json:
        command.append("--json")
    started = time.time()
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    report = {
        "run_id": f"e2e-source-to-docs-{int(started)}",
        "ok": result.returncode == 0,
        "command": command,
        "duration_seconds": round(time.time() - started, 3),
        "stdout": result.stdout,
        "stderr": result.stderr,
        "report_file": str(OUT.relative_to(REPO_ROOT)),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    (OUT.parent / "e2e_source_to_docs_wrapper.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"ok: {report['ok']}")
        print(f"report: {report['report_file']}")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
