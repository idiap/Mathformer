#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Plan implicit-premise normalization repairs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

TARGET_CATEGORY = "implicit_premise_selection"
STYLE = "physics_lean_implicit_premise_normalization_plan"
ALLOWED_LABELS = {"source-backed", "mathlib-backed", "generated-support", "blocked"}


def load_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def labels_from_monitor(monitor_report: dict[str, Any]) -> set[str]:
    return {str(item) for item in monitor_report.get("assumption_support_labels", [])}


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
    labels = labels_from_monitor(monitor_report)
    unlabeled = bool(findings) and not bool(labels & ALLOWED_LABELS)
    workbench_objects = [
        item.get("object_class")
        for item in workbench_plan.get("items", [])
        if item.get("object_class") == "boundary_or_regime_assumption"
    ]
    return {
        "style": STYLE,
        "status": (
            "needs_labeling" if unlabeled else "ready" if findings else "not_required"
        ),
        "pathology_category": TARGET_CATEGORY,
        "finding_count": len(findings),
        "observed_labels": sorted(labels),
        "related_library_objects": workbench_objects,
        "normalization_actions": [
            "label every positivity, nonzero, smoothness, integrability, boundary, frame, and domain premise",
            "mark premise as source-backed, mathlib-backed, generated-support, or blocked",
            "reject hidden strengthening unless generated support is explicit and theorem remains draft",
            "move reusable boundary or regime context into MathformerPhysicsLib support when it recurs",
        ],
        "rerun_gates": [
            "physics.lean.assumptions.encode",
            "critique.physics_lean_assumptions",
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
            monitor_report={
                "findings": [{"category": TARGET_CATEGORY}],
                "assumption_support_labels": [],
            },
            object_packet={
                "objects": [{"object_class": "boundary_or_regime_assumption"}]
            },
            workbench_plan={
                "items": [
                    {
                        "object_class": "boundary_or_regime_assumption",
                        "status": "candidate_required",
                    }
                ]
            },
        )
        assert plan["status"] == "needs_labeling"
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
