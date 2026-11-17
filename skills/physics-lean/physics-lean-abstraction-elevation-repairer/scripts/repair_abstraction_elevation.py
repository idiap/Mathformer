#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Plan library-first repair for abstraction elevation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

TARGET_CATEGORY = "abstraction_elevation"
STYLE = "physics_lean_abstraction_elevation_repair_plan"
PREFERRED_OBJECTS = {
    "basis_projection",
    "coordinate_frame",
    "gradient_divergence_curl",
    "hilbert_space_inner_product",
    "integral_or_limit",
    "physical_law",
    "quantum_operator",
    "quantum_state",
    "unbounded_position_momentum",
    "vector_field",
}


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
    workbench_by_object = {
        item.get("object_class"): item for item in workbench_plan.get("items", [])
    }
    actions = []
    blockers = []
    for obj in object_packet.get("objects", []):
        object_class = obj.get("object_class")
        if object_class not in PREFERRED_OBJECTS:
            continue
        wb = workbench_by_object.get(object_class, {})
        if wb.get("status") != "mathformer_reused":
            blockers.append(f"support_dependency_not_ready:{object_class}")
        actions.append(
            {
                "object_class": object_class,
                "library_status": wb.get("status", "missing_workbench_item"),
                "target_repair": [
                    "remove or demote target-shaped calculation hypotheses",
                    "replace hidden calculation with a named support lemma",
                    "connect support lemma to source law, calculus operation, or boundary condition",
                    "keep abstract algebra only as a reusable core below the physics wrapper",
                ],
                "forbidden_repair": "do not prove the final theorem by simpa/ring from a hypothesis equivalent to the target",
            }
        )
    return {
        "style": STYLE,
        "status": (
            "blocked_on_library"
            if blockers
            else "ready" if findings else "not_required"
        ),
        "pathology_category": TARGET_CATEGORY,
        "finding_count": len(findings),
        "actions": actions,
        "blockers": blockers,
        "rerun_gates": [
            "physics.laws.ground",
            "physics.lean.assumptions.encode",
            "critique.physics_lean_semantics",
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
            monitor_report={"findings": [{"category": TARGET_CATEGORY}]},
            object_packet={"objects": [{"object_class": "integral_or_limit"}]},
            workbench_plan={
                "items": [
                    {
                        "object_class": "integral_or_limit",
                        "status": "candidate_required",
                    }
                ]
            },
        )
        assert plan["status"] == "blocked_on_library"
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
