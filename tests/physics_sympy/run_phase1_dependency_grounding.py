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

"""Check Phase 1 dependency probing and physics package grounding."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def dependency_blocker(exc: BaseException) -> Dict[str, Any]:
    """Return a structured dependency blocker instead of a traceback."""
    return {
        "ok": False,
        "backend": "sympy",
        "style": "physics_sympy_dependency_blocker",
        "phase": "phase1_dependencies_and_physics_package_grounding",
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
        "rerun_with": ".venv/bin/python tests/physics_sympy/run_phase1_dependency_grounding.py --json",
    }


def run_check() -> Dict[str, Any]:
    """Validate Phase 1 dependency and API-shard semantics."""
    try:
        from backends.sympy.MathformerPhysicsSympy.pipeline import (
            physics_sympy_dependency_probe,
        )
    except ModuleNotFoundError as exc:
        if exc.name and exc.name.startswith("sympy"):
            return dependency_blocker(exc)
        raise
    report = physics_sympy_dependency_probe(
        "constant_acceleration_position", write_default_report=True
    )
    findings: List[str] = []
    dependencies = {item["module"]: item for item in report["dependencies"]}
    required = {
        "sympy",
        "sympy.physics.units",
        "sympy.physics.units.systems.si",
        "sympy.physics.mechanics",
        "sympy.physics.vector",
        "numpy",
    }
    optional = {"scipy", "pint", "matplotlib", "plotly"}
    if not required.issubset(dependencies):
        findings.append("required dependency probe set is incomplete")
    if not optional.issubset(dependencies):
        findings.append("optional dependency probe set is incomplete")
    if any(not dependencies[name]["required"] for name in required):
        findings.append("at least one required dependency is not marked required")
    if any(dependencies[name]["required"] for name in optional):
        findings.append(
            "at least one optional dependency is incorrectly marked required"
        )
    policy = report["optional_dependency_policy"]
    if policy["missing_optional_dependencies_fail_probe"]:
        findings.append(
            "missing optional dependencies must not fail the dependency probe"
        )
    if not policy["missing_optional_dependencies_disable_only_dependent_checks"]:
        findings.append(
            "optional dependency absence does not declare downgrade-only behavior"
        )
    report_path = report.get("report_path")
    if not report_path or not (REPO_ROOT / report_path).exists():
        findings.append("default per-case dependency report was not written")
    shard = report["physics_api_index_shard"]
    if shard["shard_version"] != "physics_sympy_api_index_v1":
        findings.append("physics API shard version is unexpected")
    categories = {item["category"] for item in shard["categories"]}
    expected_categories = {
        "sympy_physics_modules",
        "unit_systems",
        "dimension_systems",
        "mechanics_vector_apis",
        "solver_calculus_apis",
    }
    if categories != expected_categories:
        findings.append("physics API shard categories are incomplete")
    return {
        "ok": not findings,
        "backend": "sympy",
        "style": report["style"],
        "phase": "phase1_dependencies_and_physics_package_grounding",
        "findings": findings,
        "dependency_count": len(report["dependencies"]),
        "missing_required": report["missing_required"],
        "missing_optional": report["missing_optional"],
        "disabled_optional_checks": report["disabled_optional_checks"],
        "report_path": report.get("report_path"),
        "api_shard_categories": sorted(categories),
    }


def main() -> int:
    """Serve as the command-line entry point for the Phase 1 dependency check."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = run_check()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"ok: {report['ok']}")
        print(f"dependency_count: {report['dependency_count']}")
        print(f"findings: {len(report['findings'])}")
    return 0 if report["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
