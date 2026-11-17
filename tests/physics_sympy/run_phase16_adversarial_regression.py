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
#   Runs the Phase 16 adversarial and regression suite for physics SymPy derivations.
#
# Maintenance Notes:
#   Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.

"""Validate Phase 16 adversarial and regression coverage."""

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
    PHASE16_ADVERSARIAL_FIXTURES,
    adversarial_suite,
    now,
)

EXPECTED_COUNTS = {
    "unit_inconsistency": 4,
    "implicit_gap_failure": 5,
    "convention_drift": 4,
    "assumption_strengthening": 4,
}


def write_jsonl(path: Path, results: Sequence[Dict[str, Any]]) -> None:
    """Persist Phase 16 fixture results as JSONL."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for result in results:
            handle.write(
                json.dumps(result, ensure_ascii=False, sort_keys=True, default=str)
                + "\n"
            )


def write_junit(path: Path, results: Sequence[Dict[str, Any]]) -> None:
    """Persist Phase 16 fixture results as JUnit XML."""
    failures = [result for result in results if not result["blocked_complete_status"]]
    lines = [
        f'<testsuite name="physics-sympy-phase16" tests="{len(results)}" failures="{len(failures)}" skipped="0">'
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


def run_check(output_root: Path) -> Dict[str, Any]:
    """Run and validate the Phase 16 adversarial suite."""
    report = adversarial_suite(output_root)
    findings = []
    if not report["ok"]:
        findings.append(
            "adversarial suite did not block all complete-status regressions"
        )
    if report["fixture_count"] != len(PHASE16_ADVERSARIAL_FIXTURES):
        findings.append(f"fixture count mismatch: {report['fixture_count']}")
    for category, expected_count in EXPECTED_COUNTS.items():
        observed = (
            report["results_by_category"].get(category, {}).get("fixture_count", 0)
        )
        blocked = (
            report["results_by_category"].get(category, {}).get("blocked_count", 0)
        )
        if observed != expected_count:
            findings.append(
                f"{category} fixture count was {observed}, expected {expected_count}"
            )
        if blocked != expected_count:
            findings.append(
                f"{category} blocked count was {blocked}, expected {expected_count}"
            )
    missing_codes = [
        result["id"]
        for result in report["results"]
        if result["expected_code"] not in result["observed_codes"]
    ]
    if missing_codes:
        findings.append(f"fixtures missing expected diagnostic codes: {missing_codes}")
    jsonl_path = output_root / "phase16_adversarial_suite.jsonl"
    junit_path = output_root / "phase16_adversarial_suite.xml"
    write_jsonl(jsonl_path, report["results"])
    write_junit(junit_path, report["results"])
    report.update(
        {
            "ok": not findings,
            "phase": "phase16_adversarial_and_regression_tests",
            "generated_at": now(),
            "findings": findings,
            "jsonl_report_path": str(jsonl_path.relative_to(REPO_ROOT)),
            "junit_report_path": str(junit_path.relative_to(REPO_ROOT)),
        }
    )
    phase_report = output_root / "phase16_report.json"
    phase_report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    report["phase_report_path"] = str(phase_report.relative_to(REPO_ROOT))
    return report


def main() -> int:
    """Serve as the command-line entry point for Phase 16 validation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("artifacts/physics_sympy/phase16_adversarial_regression"),
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = run_check((REPO_ROOT / args.output_root).resolve())
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    else:
        print(f"ok: {report['ok']}")
        print(f"fixture_count: {report['fixture_count']}")
        print(f"phase_report: {report['phase_report_path']}")
    return 0 if report["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
