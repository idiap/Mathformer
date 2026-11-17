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

"""End-to-end smoke over Lean, Isabelle, SymPy, RFDE, and docs families."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT = REPO_ROOT / "artifacts" / "test_program" / "e2e_all_backends.json"


def prepare_command(json_output: bool) -> dict:
    """Build exactly the native seven-family invocation."""
    command = [
        sys.executable,
        "tests/test_program/run_comprehensive_tests.py",
        "--module-family",
        "lean",
        "--module-family",
        "isabelle",
        "--module-family",
        "sympy",
        "--module-family",
        "physics_sympy",
        "--module-family",
        "rfde",
        "--module-family",
        "docs",
        "--module-family",
        "mathformerlib",
        "--output-file",
        str(OUT),
    ]
    if json_output:
        command.append("--json")
    return {
        "command": command,
        "cwd": str(REPO_ROOT),
        "report_file": str(OUT),
        "json_output": json_output,
    }


def run_suite(plan: dict) -> dict:
    """Launch once, capturing nonzero exits as data; launch errors propagate."""
    command = plan["command"]
    started = time.time()
    result = subprocess.run(
        command,
        cwd=Path(plan["cwd"]),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "started": started,
        "duration_seconds": time.time() - started,
    }


def write_wrapper_and_return(plan: dict, child: dict) -> dict:
    """Persist and print the native wrapper report even after child failure."""
    report = {
        "run_id": f"e2e-all-backends-{int(child['started'])}",
        "ok": child["returncode"] == 0,
        "command": plan["command"],
        "duration_seconds": round(child["duration_seconds"], 3),
        "stdout": child["stdout"],
        "stderr": child["stderr"],
        "report_file": str(OUT.relative_to(REPO_ROOT)),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    (OUT.parent / "e2e_all_backends_wrapper.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if plan["json_output"]:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"ok: {report['ok']}")
        print(f"report: {report['report_file']}")
    return {"report": report, "exit_code": child["returncode"]}


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
    plan = prepare_command(args.json)
    child = run_suite(plan)
    return write_wrapper_and_return(plan, child)["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
