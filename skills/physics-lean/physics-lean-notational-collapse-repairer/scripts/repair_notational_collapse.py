#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Plan library-first repair for notational collapse."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

TARGET_CATEGORY = "notational_collapse"
STYLE = "physics_lean_notational_collapse_repair_plan"
PREFERRED_OBJECTS = {
    "quantum_state",
    "quantum_operator",
    "commutator",
    "hilbert_space_inner_product",
    "vector_field",
    "coordinate_frame",
    "basis_projection",
    "dimensioned_quantity",
    "unit_bridge",
}


def load_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def relevant_findings(monitor: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item
        for item in monitor.get("findings", [])
        if item.get("category") == TARGET_CATEGORY
    ]


def workbench_status(workbench: dict[str, Any], object_class: str) -> dict[str, Any]:
    for item in workbench.get("items", []):
        if item.get("object_class") == object_class:
            return item
    return {}


def build_plan(
    *,
    monitor_report: dict[str, Any],
    object_packet: dict[str, Any],
    workbench_plan: dict[str, Any],
) -> dict[str, Any]:
    findings = relevant_findings(monitor_report)
    actions = []
    blockers = []
    for obj in object_packet.get("objects", []):
        object_class = obj.get("object_class")
        if object_class not in PREFERRED_OBJECTS:
            continue
        wb = workbench_status(workbench_plan, str(object_class))
        status = wb.get("status", "missing_workbench_item")
        if status != "mathformer_reused":
            blockers.append(f"library_object_not_ready:{object_class}")
        actions.append(
            {
                "object_class": object_class,
                "library_status": status,
                "repair_surface": obj.get("repair_surface"),
                "target_repair": [
                    "replace raw scalar binders with the libraries/MathformerPhysicsLib/Mathlib object surface",
                    "preserve scalar algebra only as a core lemma",
                    "add a projection or interpretation bridge back to the source physics object",
                    "rerun type, dimension, semantics, and drift monitors",
                ],
                "editable_scope": "target theorem binders, local support import, and projection bridge only after library object evidence is ready",
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
        "protected_invariants": [
            "do not replace physics objects with raw scalar variables",
            "do not count local wrappers as complete without an abstraction-boundary blocker",
            "do not weaken the target conclusion",
        ],
        "rerun_gates": [
            "physics.lean.type_system.build",
            "critique.physics_lean_semantics",
            "critique.physics_lean_dimensions",
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
            object_packet={
                "objects": [
                    {
                        "object_class": "quantum_operator",
                        "repair_surface": "quantity_typing",
                    }
                ]
            },
            workbench_plan={
                "items": [
                    {"object_class": "quantum_operator", "status": "candidate_required"}
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
