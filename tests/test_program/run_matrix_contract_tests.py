#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Adversarial tests for the canonical typed test-matrix contract."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER = REPO_ROOT / "tests/test_program/run_comprehensive_tests.py"


def load_runner():
    spec = importlib.util.spec_from_file_location(
        "mathformer_comprehensive_runner", RUNNER
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load comprehensive runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    runner = load_runner()
    matrix = runner.load_matrix()
    baseline = runner.validate_matrix_coverage(matrix)
    baseline_contract_errors = [
        error
        for error in baseline
        if not error.startswith("skills without matrix owner rows:")
    ]

    bad_kind = [dict(row) for row in matrix]
    bad_kind[0]["test_kind"] = "misspelled-kind"
    bad_kind_errors = runner.validate_matrix_coverage(bad_kind)

    missing_field = [dict(row) for row in matrix]
    missing_field[0].pop("write_set", None)
    missing_field_errors = runner.validate_matrix_coverage(missing_field)

    duplicate = [dict(row) for row in matrix]
    duplicate.append(dict(duplicate[0]))
    duplicate_errors = runner.validate_matrix_coverage(duplicate)

    cases = {
        "baseline_valid": not baseline_contract_errors,
        "unknown_kind_rejected": any(
            "unknown test_kind" in error for error in bad_kind_errors
        ),
        "missing_field_rejected": any(
            "missing write_set" in error for error in missing_field_errors
        ),
        "duplicate_id_rejected": any(
            "duplicate matrix id" in error for error in duplicate_errors
        ),
        "manifest_is_executable": len(matrix) >= 149,
    }
    payload = {
        "schema_version": 1,
        "suite": "test_matrix_contract",
        "ok": all(cases.values()),
        "cases": cases,
        "matrix_rows": len(matrix),
        "baseline_errors": baseline,
        "baseline_contract_errors": baseline_contract_errors,
    }
    print(
        json.dumps(payload, indent=2, sort_keys=True)
        if args.json
        else ("PASS" if payload["ok"] else "FAIL")
    )
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
