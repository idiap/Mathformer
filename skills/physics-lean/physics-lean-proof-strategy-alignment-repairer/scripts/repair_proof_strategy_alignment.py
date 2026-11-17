#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Plan proof-strategy alignment repairs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

TARGET_CATEGORY = "proof_strategy_substitution"
STYLE = "physics_lean_proof_strategy_alignment_repair_plan"


def load_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def build_plan(
    *,
    monitor_report: dict[str, Any],
    object_packet: dict[str, Any],
    workbench_plan: dict[str, Any],
) -> dict[str, Any]:
    findings = [
        item
        for item in monitor_report.get("findings", [])
        if item.get("category") == TARGET_CATEGORY
    ]
    missing_library = [
        item.get("object_class")
        for item in workbench_plan.get("items", [])
        if item.get("status") not in {"mathformer_reused"}
    ]
    status = (
        "blocked_on_library"
        if findings and missing_library
        else "ready" if findings else "not_required"
    )
    return {
        "style": STYLE,
        "status": status,
        "pathology_category": TARGET_CATEGORY,
        "finding_count": len(findings),
        "missing_library_objects": missing_library,
        "alignment_checks": [
            "same source physics object classes appear in theorem binders or support lemmas",
            "same target relation, direction, quantifier shape, and conclusion strength are preserved",
            "source laws or transformations are either proved, imported, or explicitly blocked",
            "alternate strategy does not bypass required calculus, vector, operator, unit, or frame obligations",
        ],
        "repair_actions": [
            "if checks pass, annotate proof strategy substitution as acceptable and rerun semantic monitors",
            "if checks fail, route to notational-collapse or abstraction-elevation repair based on missing object",
            "add a library support lemma only for the missing transformation, not for the final target",
        ],
        "rerun_gates": [
            "critique.semantic_preservation",
            "critique.physics_lean_semantics",
            "critique.physics_lean_drift_pathology_monitor",
            "review.physics_final_hypotheses",
        ],
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--monitor-report", type=Path)
    parser.add_argument("--object-packet", type=Path)
    parser.add_argument("--workbench-plan", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        plan = build_plan(
            monitor_report={"findings": [{"category": TARGET_CATEGORY}]},
            object_packet={"objects": [{"object_class": "integral_or_limit"}]},
            workbench_plan={
                "items": [
                    {"object_class": "integral_or_limit", "status": "mathformer_reused"}
                ]
            },
        )
        assert plan["status"] == "ready"
    else:
        plan = build_plan(
            monitor_report=load_json(args.monitor_report),
            object_packet=load_json(args.object_packet),
            workbench_plan=load_json(args.workbench_plan),
        )
    output = json.dumps(plan, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
