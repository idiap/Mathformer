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

"""Run adversarial and regression checks for the physics SymPy pipeline."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
import sys
from typing import Any, Dict, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backends.sympy.MathformerPhysicsSympy.pipeline import (
    adversarial_suite,
)


def write_jsonl(path: Path, results: Sequence[Dict[str, Any]]) -> None:
    """Write one adversarial result per JSONL line.

    Motivation:
        Phase 16 results should be easy to ingest in CI dashboards and
        lightweight local analysis tools.

    Intent:
        Persist each fixture result independently while preserving sorted keys
        for stable diffs.

    Inputs:
        ``path`` is the JSONL destination and ``results`` are adversarial
        fixture result packets.

    Outputs:
        Creates or overwrites the JSONL file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for result in results:
            handle.write(
                json.dumps(result, ensure_ascii=False, sort_keys=True, default=str)
                + "\n"
            )


def write_junit(path: Path, results: Sequence[Dict[str, Any]]) -> None:
    """Write adversarial fixture results as a minimal JUnit XML report.

    Motivation:
        The physics backend should expose adversarial regressions in the same
        surfaces used by ordinary test infrastructure.

    Intent:
        Convert every fixture into a testcase, failing only fixtures that did
        not block complete status with their expected diagnostic code.

    Inputs:
        ``path`` is the XML destination and ``results`` are adversarial
        fixture result packets.

    Outputs:
        Creates or overwrites a JUnit-compatible XML report.
    """
    failures = [result for result in results if not result["blocked_complete_status"]]
    lines = [
        f'<testsuite name="physics-sympy-phase16-adversarial" tests="{len(results)}" failures="{len(failures)}" skipped="0">'
    ]
    for result in results:
        classname = html.escape(f"physics_sympy.{result['category']}")
        name = html.escape(result["id"])
        lines.append(f'  <testcase classname="{classname}" name="{name}">')
        if not result["blocked_complete_status"]:
            message = html.escape(
                f"expected {result['expected_code']}, observed {result['observed_codes']}"
            )
            lines.append(f'    <failure message="{message}">{message}</failure>')
        lines.append("  </testcase>")
    lines.append("</testsuite>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
        default=Path("artifacts/physics_sympy/adversarial_suite"),
    )
    parser.add_argument("--write-jsonl", type=Path)
    parser.add_argument("--write-junit", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    output_root = (REPO_ROOT / args.output_root).resolve()
    report = adversarial_suite(output_root)
    if args.write_jsonl:
        write_jsonl((REPO_ROOT / args.write_jsonl).resolve(), report["results"])
    if args.write_junit:
        write_junit((REPO_ROOT / args.write_junit).resolve(), report["results"])
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    else:
        print(f"ok: {report['ok']}")
        print(f"case_count: {len(report['results'])}")
        print(f"report: {report.get('report_path')}")
    return 0 if report["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
