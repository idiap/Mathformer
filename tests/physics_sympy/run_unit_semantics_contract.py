#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402 - imports follow explicit direct-script path setup
#
#

"""Adversarial executable checks for physics unit-flow semantics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import sympy as sp

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from libraries.MathformerPhysicsLib.unit_semantics import (
    validate_unitful_equation,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    force, mass, acceleration, time = sp.symbols("F m a t", positive=True)
    valid = validate_unitful_equation(
        sp.Eq(force, mass * acceleration, evaluate=False),
        {"F": "newton", "m": "kilogram", "a": "meter/second**2"},
    )
    bad_exponent = validate_unitful_equation(
        sp.Eq(force, mass * acceleration * time, evaluate=False),
        {"F": "newton", "m": "kilogram", "a": "meter/second**2", "t": "second"},
    )
    bad_function = validate_unitful_equation(
        sp.Eq(sp.Symbol("y"), sp.exp(time), evaluate=False),
        {"y": "dimensionless", "t": "second"},
    )
    cases = {
        "newton_second_law_passes": valid["ok"] is True,
        "unit_exponent_mutation_fails": bad_exponent["ok"] is False,
        "dimensioned_exponential_argument_fails": bad_function["ok"] is False
        and any(
            item["code"] == "dimensioned_function_argument"
            for item in bad_function["findings"]
        ),
    }
    payload = {
        "schema_version": 1,
        "suite": "physics_unit_semantics",
        "ok": all(cases.values()),
        "cases": cases,
        "witnesses": {
            "valid": valid,
            "unit_mutation": bad_exponent,
            "function_argument": bad_function,
        },
    }
    print(
        json.dumps(payload, indent=2, sort_keys=True)
        if args.json
        else ("PASS" if payload["ok"] else "FAIL")
    )
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
