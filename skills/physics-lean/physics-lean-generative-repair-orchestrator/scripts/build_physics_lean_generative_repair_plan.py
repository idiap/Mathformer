#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Add a guarded generative repair surface to the Lean physics pathology loop.
#
# Intent:
#   Build Codex-exec prompts that propose repairs while preserving
#   MathformerPhysicsLib-first object work and deterministic acceptance gates.
#
# Function:
#   Reads deterministic pathology repair packets and emits a generative repair
#   plan with proposal prompts, required output schema, validation gates, and
#   forbidden shortcut repairs.
#
# Maintenance Notes:
#   Generative repair remains advisory. It must not mark any artifact complete
#   without deterministic reruns and promotion/compile evidence.

"""Build guarded generative repair plans for Lean physics pathologies."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

GEN_REPAIR_PANEL = [
    "physics-lean-generative-repair-orchestrator",
    "physics-math-object-detector",
    "mathformerphysicslib-object-workbench",
    "physics-lean-notational-collapse-repairer",
    "physics-lean-abstraction-elevation-repairer",
    "physics-lean-proof-strategy-alignment-repairer",
    "physics-lean-implicit-premise-normalizer",
    "physics-lean-review-refinement-router",
]


def load_json(path: Path | None) -> dict[str, Any]:
    """Load optional JSON."""
    if path is None:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_many(paths: Sequence[Path]) -> list[dict[str, Any]]:
    """Load multiple optional JSON reports."""
    return [load_json(path) for path in paths]


def read_text(path: Path | None, inline: str | None) -> str:
    """Read text from path or inline value."""
    if inline is not None:
        return inline
    if path is None:
        return ""
    return path.read_text(encoding="utf-8")


def active_categories(
    monitor_report: dict[str, Any], repair_loop: dict[str, Any]
) -> list[str]:
    """Return active pathology categories."""
    if repair_loop.get("active_categories"):
        return [str(item) for item in repair_loop.get("active_categories", [])]
    counts = monitor_report.get("category_counts", {})
    if isinstance(counts, dict):
        return sorted(str(key) for key, value in counts.items() if int(value) > 0)
    return []


def summarize_objects(object_packet: dict[str, Any]) -> list[str]:
    """Return detected object classes."""
    return [
        str(item.get("object_class"))
        for item in object_packet.get("objects", [])
        if isinstance(item, dict)
    ]


def build_probe_prompts(
    *,
    source_preview: str,
    lean_preview: str,
    categories: list[str],
    object_classes: list[str],
    repair_loop: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build generative repair probes."""
    blockers = repair_loop.get("blockers", [])
    common_context = (
        "Source preview:\n"
        f"{source_preview}\n\n"
        "Lean preview:\n"
        f"{lean_preview}\n\n"
        f"Active pathologies: {categories}\n"
        f"Detected physics objects: {object_classes}\n"
        f"Current deterministic blockers: {blockers}\n"
    )
    return [
        {
            "id": "library_first_object_repair_proposal",
            "repair_role": "MathformerPhysicsLib object support",
            "prompt": (
                common_context
                + "\nPropose the smallest MathformerPhysicsLib-first repair. "
                "Return compact JSON with keys skill, verdict, evidence, proposed_library_objects, "
                "proposed_target_edits, blockers, rerun_gates, regression. Proposed target edits must be empty "
                "unless each physics object is reused, candidate-promoted, or explicitly blocked."
            ),
        },
        {
            "id": "pathology_specific_target_repair_proposal",
            "repair_role": "localized target theorem refinement",
            "prompt": (
                common_context
                + "\nAssuming required library object support is available, propose localized target theorem "
                "edits for the active pathology categories. Return compact JSON with keys skill, verdict, "
                "evidence, proposed_library_objects, proposed_target_edits, blockers, rerun_gates, regression. "
                "Preserve target conclusion, source anchors, units, assumptions, and non-vacuity."
            ),
        },
        {
            "id": "implicit_premise_and_assumption_repair_proposal",
            "repair_role": "side-condition normalization",
            "prompt": (
                common_context
                + "\nList every new or existing side condition that a repair would need. Return compact JSON "
                "with keys skill, verdict, evidence, assumptions, proposed_library_objects, proposed_target_edits, "
                "blockers, rerun_gates, regression. Each assumption must be labeled source-backed, mathlib-backed, "
                "generated-support, or blocked."
            ),
        },
        {
            "id": "unsafe_repair_adversary",
            "repair_role": "reject unsafe generative repair",
            "prompt": (
                common_context
                + "\nAct as an adversary against the proposed repair. Return compact JSON with keys skill, verdict, "
                "evidence, unsafe_patterns, blockers, rerun_gates, regression. Fail any repair that adds target-shaped "
                "hypotheses, axioms, sorry/admit, scalar collapse, hidden strengthening, or a theorem weaker than the source."
            ),
        },
    ]


def build_plan(
    *,
    source_text: str,
    lean_text: str,
    monitor_report: dict[str, Any],
    object_packet: dict[str, Any],
    workbench_plan: dict[str, Any],
    repair_loop: dict[str, Any],
    repair_plans: list[dict[str, Any]],
    high_risk: bool,
) -> dict[str, Any]:
    """Build the generative repair plan."""
    data = dict(
        source_text=source_text,
        lean_text=lean_text,
        monitor_report=monitor_report,
        object_packet=object_packet,
        workbench_plan=workbench_plan,
        repair_loop=repair_loop,
        repair_plans=repair_plans,
        high_risk=high_risk,
    )
    prepared = prepare_inputs(data)
    prompts = prompts_for_inputs(data, prepared)
    flags = plan_flags(data)
    status = "not_required" if flags["monitor_pass"] else "ready"
    if flags["needs_loop"]:
        status = "needs_deterministic_repair_loop"
    return assemble_plan(data, prepared, prompts, flags, status)


def prepare_inputs(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize and bound previews, then extract categories and objects."""
    return {
        "source_preview": " ".join(data["source_text"].split())[:800],
        "lean_preview": " ".join(data["lean_text"].split())[:800],
        "active_categories": active_categories(
            data["monitor_report"], data["repair_loop"]
        ),
        "object_classes": summarize_objects(data["object_packet"]),
    }


def prompts_for_inputs(
    data: dict[str, Any], prepared: dict[str, Any]
) -> list[dict[str, Any]]:
    """Construct exactly four advisory prompts, without executing them."""
    return build_probe_prompts(
        source_preview=prepared["source_preview"],
        lean_preview=prepared["lean_preview"],
        categories=prepared["active_categories"],
        object_classes=prepared["object_classes"],
        repair_loop=data["repair_loop"],
    )


def plan_flags(data: dict[str, Any]) -> dict[str, Any]:
    """Compute the original status guards after prompt construction."""
    repair_loop_status = data["repair_loop"].get("status", "missing")
    monitor_pass = data["monitor_report"].get("status") == "pass"
    return {
        "monitor_pass": monitor_pass,
        "needs_loop": repair_loop_status in {"missing", "not_required"}
        and not monitor_pass,
        "repair_loop_status": repair_loop_status,
    }


def assemble_plan(data, prepared, prompts, flags, status) -> dict[str, Any]:
    """Package the native advisory policy and selected status."""
    categories = prepared["active_categories"]
    object_classes = prepared["object_classes"]
    high_risk = data["high_risk"]
    workbench_plan = data["workbench_plan"]
    repair_plans = data["repair_plans"]
    repair_loop_status = flags["repair_loop_status"]
    probe_prompts = prompts
    return {
        "style": "physics_lean_generative_repair_plan",
        "status": status,
        "codex_exec_enabled": True,
        "high_risk": high_risk,
        "requires_deterministic_first": True,
        "repair_panel": GEN_REPAIR_PANEL,
        "active_categories": categories,
        "detected_object_classes": object_classes,
        "workbench_status": workbench_plan.get("status", "missing"),
        "deterministic_repair_loop_status": repair_loop_status,
        "repair_plan_styles": [plan.get("style", "unknown") for plan in repair_plans],
        "probe_prompts": probe_prompts,
        "expected_report_schema": {
            "style": "physics_lean_generative_repair_report",
            "required_keys": [
                "skill",
                "verdict",
                "evidence",
                "proposed_library_objects",
                "proposed_target_edits",
                "blockers",
                "rerun_gates",
                "regression",
            ],
        },
        "forbidden_shortcuts": [
            "target-shaped hypotheses",
            "axioms, sorry, admit, exact? placeholders",
            "raw scalar replacement of physics-bearing objects",
            "hidden strengthening of assumptions",
            "unlabeled generated assumptions",
            "weakened theorem conclusion",
            "counting candidate workbench text as accepted support",
        ],
        "recommended_command": (
            "python skills/control/skill-test-program-orchestrator/scripts/run_content_skill_codex_exec_tests.py "
            "--execute --skill physics-lean-generative-repair-orchestrator --json"
        ),
        "acceptance_policy": {
            "generative_output_is_advisory": True,
            "library_first_required": True,
            "must_rerun_after_any_proposed_edit": [
                "mathformerlib.registry",
                "mathformerlib.promotion_gate",
                "lake build",
                "critique.physics_lean_drift_pathology_monitor",
                "repair.physics_lean_pathology_loop",
                "consistency.physics_lean_report",
            ],
        },
    }


def parse_args(
    argv: Sequence[str] | None = None, *, prog: str | None = None
) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__, prog=prog)
    parser.add_argument("--source-file", type=Path)
    parser.add_argument("--source-text")
    parser.add_argument("--lean-file", type=Path)
    parser.add_argument("--lean-text")
    parser.add_argument("--monitor-report", type=Path)
    parser.add_argument("--object-packet", type=Path)
    parser.add_argument("--workbench-plan", type=Path)
    parser.add_argument("--repair-loop", type=Path)
    parser.add_argument("--repair-plan", type=Path, action="append", default=[])
    parser.add_argument("--high-risk", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args(argv)


def load_inputs(
    argv: Sequence[str] | None = None,
    *,
    working_directory: Path | None = None,
    program_name: str | None = None,
):
    """Parse and load native inputs in their original order.

    Explicit working directories resolve paths without changing process-global cwd.
    Self-test deliberately bypasses all supplied input files.
    """
    args = parse_args(argv, prog=program_name)
    if working_directory is not None:
        for name in (
            "source_file",
            "lean_file",
            "monitor_report",
            "object_packet",
            "workbench_plan",
            "repair_loop",
            "output",
        ):
            value = getattr(args, name)
            if value is not None:
                setattr(args, name, working_directory / value)
        args.repair_plan = [working_directory / path for path in args.repair_plan]
    if args.self_test:
        data = dict(
            source_text="Show that the commutator [q, p] = i for quantum operators.",
            lean_text="theorem bad (q p : Real) : q * p = p * q := by ring",
            monitor_report={
                "status": "fail",
                "category_counts": {"notational_collapse": 1},
            },
            object_packet={"objects": [{"object_class": "commutator"}]},
            workbench_plan={"status": "library_work_required"},
            repair_loop={
                "status": "blocked_on_library_or_labels",
                "active_categories": ["notational_collapse"],
            },
            repair_plans=[{"style": "physics_lean_notational_collapse_repair_plan"}],
            high_risk=True,
        )
    else:
        data = dict(
            source_text=read_text(args.source_file, args.source_text),
            lean_text=read_text(args.lean_file, args.lean_text),
            monitor_report=load_json(args.monitor_report),
            object_packet=load_json(args.object_packet),
            workbench_plan=load_json(args.workbench_plan),
            repair_loop=load_json(args.repair_loop),
            repair_plans=load_many(args.repair_plan),
            high_risk=args.high_risk,
        )
    return data, {
        "self_test": args.self_test,
        "output": str(args.output) if args.output else None,
    }


def emit_plan(control: dict[str, Any], plan: dict[str, Any]) -> int:
    """Assert self-test obligations, serialize, and emit the native result."""
    if control["self_test"]:
        assert plan["style"] == "physics_lean_generative_repair_plan"
        assert plan["codex_exec_enabled"] is True
        assert len(plan["probe_prompts"]) >= 4
        assert "target-shaped hypotheses" in plan["forbidden_shortcuts"]
    output = json.dumps(plan, ensure_ascii=False, indent=2)
    if control["output"]:
        Path(control["output"]).parent.mkdir(parents=True, exist_ok=True)
        Path(control["output"]).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the same shared steps used by the registered MCP tools."""
    data, control = load_inputs(argv)
    return emit_plan(control, build_plan(**data))


if __name__ == "__main__":
    raise SystemExit(main())
