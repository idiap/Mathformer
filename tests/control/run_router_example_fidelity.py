#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Require every documented NL route example to round-trip to its owner."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
HUB = REPO_ROOT / "scripts/mathformer.py"


def load_hub():
    spec = importlib.util.spec_from_file_location("mathformer_router_fidelity_hub", HUB)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load scripts/mathformer.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    hub = load_hub()
    registry = hub.build_registry()
    routes = hub.build_intent_routes()
    mismatches = []
    example_count = 0
    for route in routes:
        for example in route.examples:
            example_count += 1
            matches = hub.resolve_intent(example, registry, limit=3)
            selected = matches[0].route.route_id if matches else None
            if selected != route.route_id:
                mismatches.append(
                    {
                        "example": example,
                        "expected_route": route.route_id,
                        "selected_route": selected,
                        "candidates": [match.route.route_id for match in matches],
                    }
                )

    review_query = "implement the autoformalization framework review todos with particular emphasis on physics"
    review_matches = hub.resolve_intent(review_query, registry, limit=3)
    sympy_query = (
        "run the recursive goal oriented workflow for SymPy formalphysics_0004"
    )
    sympy_matches = hub.resolve_intent(sympy_query, registry, limit=3)
    ambiguity_checks = {
        "review_intent": bool(review_matches)
        and review_matches[0].route.route_id == "review.autoformalization.framework",
        "sympy_goal_not_lean": bool(sympy_matches)
        and sympy_matches[0].route.route_id
        == "formalize.physics.sympy.goal_sample_0004",
    }
    payload = {
        "schema_version": 1,
        "suite": "router_example_fidelity",
        "ok": not mismatches and all(ambiguity_checks.values()),
        "route_count": len(routes),
        "example_count": example_count,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "ambiguity_checks": ambiguity_checks,
    }
    print(
        json.dumps(payload, indent=2, sort_keys=True)
        if args.json
        else ("PASS" if payload["ok"] else "FAIL")
    )
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
