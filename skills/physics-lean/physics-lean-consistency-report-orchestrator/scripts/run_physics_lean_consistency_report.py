#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.
#
# Intent:
#   Tell coding agents what context to load, what invariants to preserve, and how to validate their work.
#
# Function:
#   Contains skill instructions, prompts, references, and scripts used by Codex-style workflows.
#
# Maintenance Notes:
#   Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.

"""Aggregate Lean-physics consistency evidence into a status report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

REQUIRED_CRITIC_STYLES = {
    "physics_lean_physical_semantics_critic_report",
    "physics_lean_assumption_critic_report",
    "physics_lean_dimension_critic_report",
    "physics_lean_drift_pathology_monitor_report",
}

REQUIRED_GENERATIVE_CRITIC_STYLES = {
    "physics_lean_generative_critic_plan",
    "physics_lean_generative_critic_report",
}


def load_json(path: Path | None) -> dict[str, Any]:
    """Document the responsibility of ``load_json``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if path is None:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def build_report(
    *,
    unit_report: dict[str, Any],
    execution_report: dict[str, Any],
    type_packet: dict[str, Any],
    assumption_packet: dict[str, Any],
    background_packet: dict[str, Any] | None = None,
    critic_reports: list[dict[str, Any]],
    pathology_repair_loop: dict[str, Any] | None = None,
    generative_repair: dict[str, Any] | None = None,
    repair_expansion_map: dict[str, Any] | None = None,
    recursive_repair_control: dict[str, Any] | None = None,
    final_review: dict[str, Any],
    compile_ok: bool,
    realness_ok: bool,
    anchor_ok: bool,
) -> dict[str, Any]:
    """Document the responsibility of ``build_report``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    blockers = []
    warnings = []
    if not compile_ok:
        blockers.append("lean_compile_failed")
    if not realness_ok:
        blockers.append("realness_failed")
    if not anchor_ok:
        blockers.append("source_anchor_failed")
    unit_status = unit_report.get("status", "missing") if unit_report else "missing"
    if unit_status == "missing":
        blockers.append("missing_unit_dimension_report")
    elif unit_status == "fail":
        blockers.append("unit_dimension_failed")
    elif unit_status not in {"pass", "ok", "complete"}:
        warnings.append(f"unit_dimension_{unit_status}")
    if not type_packet:
        blockers.append("missing_physics_type_packet")
    if not assumption_packet:
        blockers.append("missing_assumption_packet")
    background_items = []
    if background_packet:
        background_items = background_packet.get("background_items", [])
        if not isinstance(background_items, list):
            background_items = []
        open_background = [
            item
            for item in background_items
            if isinstance(item, dict)
            and str(item.get("formalization_status", "needs_autoformalization"))
            not in {
                "formalized",
                "mathlib_reused",
                "mathformer_reused",
                "blocked",
                "not_required",
                "complete",
            }
        ]
        if open_background:
            blockers.append("open_background_formalization_obligations")
    else:
        blockers.append("missing_background_dependency_plan")
        open_background = []
    execution_status = (
        execution_report.get("status", "missing") if execution_report else "missing"
    )
    if execution_status in {"missing", "empty"}:
        blockers.append(f"execution_interpretation_{execution_status}")
    elif execution_status == "diagnostics_classified":
        warnings.append("execution_diagnostics_classified")
    if execution_report.get("repair_targets"):
        blockers.append("open_execution_repair_targets")
    critic_summary = []
    present_critic_styles: set[str] = set()
    for report in critic_reports:
        style = report.get("style", "unknown_critic_report")
        present_critic_styles.add(style)
        if style in REQUIRED_GENERATIVE_CRITIC_STYLES and "status" not in report:
            status = "present"
        else:
            status = report.get("status", "missing")
        finding_count = len(report.get("findings", []))
        critic_summary.append(
            {
                "style": style,
                "status": status,
                "finding_count": finding_count,
            }
        )
        if status in {"fail", "missing"}:
            blockers.append(f"critic_failed:{style}")
        elif status == "warn":
            warnings.append(f"critic_warned:{style}")
    missing_critics = sorted(REQUIRED_CRITIC_STYLES - present_critic_styles)
    if missing_critics:
        blockers.extend(f"missing_required_critic:{style}" for style in missing_critics)
    if not (present_critic_styles & REQUIRED_GENERATIVE_CRITIC_STYLES):
        blockers.append("missing_required_critic:physics_lean_generative_critic")
    pathology_repair_status = "missing"
    if pathology_repair_loop:
        pathology_repair_status = pathology_repair_loop.get("status", "missing")
        if pathology_repair_status in {
            "blocked_on_library_or_labels",
            "ready_for_target_refinement",
        }:
            blockers.append(f"pathology_repair_loop_{pathology_repair_status}")
        elif pathology_repair_status not in {"not_required", "complete", "missing"}:
            warnings.append(f"pathology_repair_loop_{pathology_repair_status}")
    generative_repair_status = "missing"
    generative_repair_style = "missing"
    if generative_repair:
        generative_repair_status = generative_repair.get(
            "status", generative_repair.get("verdict", "present")
        )
        generative_repair_style = generative_repair.get("style", "unknown")
        if generative_repair_status in {"fail", "unsafe", "blocked"}:
            blockers.append(f"generative_repair_{generative_repair_status}")
        elif generative_repair_status in {"needs_deterministic_repair_loop"}:
            warnings.append(f"generative_repair_{generative_repair_status}")
    elif pathology_repair_status not in {"missing", "not_required"}:
        warnings.append("missing_generative_repair_plan")
    repair_expansion_status = "missing"
    repair_expansion_exhaustive = None
    if repair_expansion_map:
        repair_expansion_status = repair_expansion_map.get("status", "missing")
        repair_expansion_exhaustive = bool(
            repair_expansion_map.get("exhaustive", False)
        )
        if not repair_expansion_exhaustive and pathology_repair_status not in {
            "missing",
            "not_required",
        }:
            blockers.append("repair_expansion_not_exhaustive")
        if repair_expansion_status == "blocked":
            blockers.append("repair_expansion_blocked")
        elif repair_expansion_status == "needs_expansion":
            warnings.append("repair_expansion_needs_expansion")
    elif pathology_repair_status not in {"missing", "not_required"}:
        blockers.append("missing_repair_expansion_map")
    recursive_repair_status = "missing"
    if recursive_repair_control:
        recursive_repair_status = recursive_repair_control.get(
            "status", recursive_repair_control.get("decision", "missing")
        )
        if recursive_repair_status in {"blocked", "recurse"}:
            blockers.append(f"recursive_repair_control_{recursive_repair_status}")
        elif recursive_repair_status not in {"complete", "not_required", "missing"}:
            warnings.append(f"recursive_repair_control_{recursive_repair_status}")
    elif pathology_repair_status not in {"missing", "not_required"}:
        blockers.append("missing_recursive_repair_control")
    final_review_status = (
        final_review.get("status", "missing") if final_review else "missing"
    )
    if final_review_status in {"fail", "missing"}:
        blockers.append(f"final_review_{final_review_status}")
    elif final_review_status == "warn":
        warnings.append("final_review_warned")
    final_review_style = (
        final_review.get("style", "missing") if final_review else "missing"
    )
    if final_review_style != "physics_final_hypothesis_review":
        blockers.append("missing_physics_final_hypothesis_review")
    final_review_properties = (
        final_review.get("reviewed_properties", {}) if final_review else {}
    )
    mathlib_grounding_level = final_review_properties.get(
        "mathlib_grounding_level", "missing"
    )
    if mathlib_grounding_level in {"low", "medium"}:
        blockers.append(f"mathlib_grounding_{mathlib_grounding_level}")
    elif mathlib_grounding_level == "missing":
        blockers.append("mathlib_grounding_missing")

    status = "complete" if not blockers else "blocked"
    if blockers and compile_ok and realness_ok and anchor_ok:
        status = "draft"
    return {
        "style": "lean_physics_consistency_report",
        "status": status,
        "blockers": blockers,
        "warnings": warnings,
        "evidence": {
            "compile_ok": compile_ok,
            "realness_ok": realness_ok,
            "anchor_ok": anchor_ok,
            "unit_status": unit_status,
            "type_packet_present": bool(type_packet),
            "assumption_packet_present": bool(assumption_packet),
            "background_packet_present": bool(background_packet),
            "background_item_count": len(background_items),
            "open_background_item_count": len(open_background),
            "execution_interpretation_status": execution_status,
            "critic_reports": critic_summary,
            "required_critic_styles_present": sorted(present_critic_styles),
            "pathology_repair_loop_status": pathology_repair_status,
            "generative_repair_status": generative_repair_status,
            "generative_repair_style": generative_repair_style,
            "repair_expansion_status": repair_expansion_status,
            "repair_expansion_exhaustive": repair_expansion_exhaustive,
            "recursive_repair_status": recursive_repair_status,
            "final_derivation_review_status": final_review_status,
            "final_derivation_review_style": final_review_style,
            "mathlib_grounding_level": mathlib_grounding_level,
            "mathlib_native_surface_count": final_review_properties.get(
                "mathlib_native_surface_count"
            ),
            "local_scaffold_count": final_review_properties.get("local_scaffold_count"),
        },
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Document the responsibility of ``parse_args``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Parse caller-provided input into the structured representation expected by downstream code.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--unit-report", type=Path)
    parser.add_argument("--execution-report", type=Path)
    parser.add_argument("--type-packet", type=Path)
    parser.add_argument("--assumption-packet", type=Path)
    parser.add_argument("--background-packet", type=Path)
    parser.add_argument("--critic-report", action="append", type=Path, default=[])
    parser.add_argument("--pathology-repair-loop", type=Path)
    parser.add_argument("--generative-repair", type=Path)
    parser.add_argument("--repair-expansion-map", type=Path)
    parser.add_argument("--recursive-repair-control", type=Path)
    parser.add_argument("--final-review", type=Path)
    parser.add_argument("--compile-ok", action="store_true")
    parser.add_argument("--realness-ok", action="store_true")
    parser.add_argument("--anchor-ok", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Document the responsibility of ``main``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Serve as the command-line entry point and coordinate argument parsing, execution, and reporting.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    args = parse_args(argv)
    if args.self_test:
        report = build_report(
            unit_report={"status": "pass"},
            execution_report={"status": "no_known_diagnostics"},
            type_packet={"style": "lean_physics_type_system_packet"},
            assumption_packet={"style": "lean_physics_assumption_context_packet"},
            background_packet={"background_items": []},
            critic_reports=[
                {
                    "style": "physics_lean_physical_semantics_critic_report",
                    "status": "pass",
                },
                {"style": "physics_lean_assumption_critic_report", "status": "pass"},
                {"style": "physics_lean_dimension_critic_report", "status": "pass"},
                {
                    "style": "physics_lean_drift_pathology_monitor_report",
                    "status": "pass",
                },
                {"style": "physics_lean_generative_critic_plan"},
            ],
            pathology_repair_loop={"status": "not_required"},
            generative_repair={
                "style": "physics_lean_generative_repair_plan",
                "status": "not_required",
            },
            repair_expansion_map={
                "style": "physics_lean_repair_expansion_map",
                "status": "not_required",
                "exhaustive": True,
            },
            recursive_repair_control={
                "style": "physics_lean_recursive_repair_control_plan",
                "status": "complete",
            },
            final_review={
                "style": "physics_final_hypothesis_review",
                "status": "pass",
                "reviewed_properties": {"mathlib_grounding_level": "high"},
            },
            compile_ok=True,
            realness_ok=True,
            anchor_ok=True,
        )
        assert report["status"] == "complete"
        legacy_report = build_report(
            unit_report={"status": "pass"},
            execution_report={"status": "no_known_diagnostics"},
            type_packet={"style": "lean_physics_type_system_packet"},
            assumption_packet={"style": "lean_physics_assumption_context_packet"},
            background_packet={"background_items": []},
            critic_reports=[
                {
                    "style": "physics_lean_physical_semantics_critic_report",
                    "status": "pass",
                },
                {"style": "physics_lean_assumption_critic_report", "status": "pass"},
                {"style": "physics_lean_dimension_critic_report", "status": "pass"},
                {
                    "style": "physics_lean_drift_pathology_monitor_report",
                    "status": "pass",
                },
                {"style": "physics_lean_generative_critic_plan"},
            ],
            pathology_repair_loop={"status": "not_required"},
            generative_repair={
                "style": "physics_lean_generative_repair_plan",
                "status": "not_required",
            },
            repair_expansion_map={
                "style": "physics_lean_repair_expansion_map",
                "status": "not_required",
                "exhaustive": True,
            },
            recursive_repair_control={
                "style": "physics_lean_recursive_repair_control_plan",
                "status": "complete",
            },
            final_review={
                "style": "final_derivation_hypothesis_review",
                "status": "pass",
            },
            compile_ok=True,
            realness_ok=True,
            anchor_ok=True,
        )
        assert legacy_report["status"] == "draft"
        assert "missing_physics_final_hypothesis_review" in legacy_report["blockers"]
        assert "mathlib_grounding_missing" in legacy_report["blockers"]
        physics_report = build_report(
            unit_report={"status": "pass"},
            execution_report={"status": "no_known_diagnostics"},
            type_packet={"style": "lean_physics_type_system_packet"},
            assumption_packet={"style": "lean_physics_assumption_context_packet"},
            background_packet={"background_items": []},
            critic_reports=[
                {
                    "style": "physics_lean_physical_semantics_critic_report",
                    "status": "pass",
                },
                {"style": "physics_lean_assumption_critic_report", "status": "pass"},
                {"style": "physics_lean_dimension_critic_report", "status": "pass"},
                {
                    "style": "physics_lean_drift_pathology_monitor_report",
                    "status": "pass",
                },
                {"style": "physics_lean_generative_critic_report", "status": "pass"},
            ],
            pathology_repair_loop={"status": "not_required"},
            generative_repair={
                "style": "physics_lean_generative_repair_plan",
                "status": "not_required",
            },
            repair_expansion_map={
                "style": "physics_lean_repair_expansion_map",
                "status": "not_required",
                "exhaustive": True,
            },
            recursive_repair_control={
                "style": "physics_lean_recursive_repair_control_plan",
                "status": "complete",
            },
            final_review={
                "style": "physics_final_hypothesis_review",
                "status": "pass",
                "reviewed_properties": {"mathlib_grounding_level": "medium"},
            },
            compile_ok=True,
            realness_ok=True,
            anchor_ok=True,
        )
        assert physics_report["status"] == "draft"
        assert "mathlib_grounding_medium" in physics_report["blockers"]
        background_report = build_report(
            unit_report={"status": "pass"},
            execution_report={"status": "no_known_diagnostics"},
            type_packet={"style": "lean_physics_type_system_packet"},
            assumption_packet={"style": "lean_physics_assumption_context_packet"},
            background_packet={
                "background_items": [
                    {
                        "id": "bg.calculus_support",
                        "formalization_status": "needs_autoformalization",
                    }
                ]
            },
            critic_reports=[
                {
                    "style": "physics_lean_physical_semantics_critic_report",
                    "status": "pass",
                },
                {"style": "physics_lean_assumption_critic_report", "status": "pass"},
                {"style": "physics_lean_dimension_critic_report", "status": "pass"},
                {
                    "style": "physics_lean_drift_pathology_monitor_report",
                    "status": "pass",
                },
                {"style": "physics_lean_generative_critic_report", "status": "pass"},
            ],
            pathology_repair_loop={"status": "not_required"},
            generative_repair={
                "style": "physics_lean_generative_repair_plan",
                "status": "not_required",
            },
            repair_expansion_map={
                "style": "physics_lean_repair_expansion_map",
                "status": "not_required",
                "exhaustive": True,
            },
            recursive_repair_control={
                "style": "physics_lean_recursive_repair_control_plan",
                "status": "complete",
            },
            final_review={
                "style": "physics_final_hypothesis_review",
                "status": "pass",
                "reviewed_properties": {"mathlib_grounding_level": "high"},
            },
            compile_ok=True,
            realness_ok=True,
            anchor_ok=True,
        )
        assert background_report["status"] == "draft"
        assert (
            "open_background_formalization_obligations" in background_report["blockers"]
        )
        recursive_report = build_report(
            unit_report={"status": "pass"},
            execution_report={"status": "no_known_diagnostics"},
            type_packet={"style": "lean_physics_type_system_packet"},
            assumption_packet={"style": "lean_physics_assumption_context_packet"},
            background_packet={"background_items": []},
            critic_reports=[
                {
                    "style": "physics_lean_physical_semantics_critic_report",
                    "status": "pass",
                },
                {"style": "physics_lean_assumption_critic_report", "status": "pass"},
                {"style": "physics_lean_dimension_critic_report", "status": "pass"},
                {
                    "style": "physics_lean_drift_pathology_monitor_report",
                    "status": "fail",
                },
                {"style": "physics_lean_generative_critic_report", "status": "pass"},
            ],
            pathology_repair_loop={"status": "blocked_on_library_or_labels"},
            generative_repair={
                "style": "physics_lean_generative_repair_plan",
                "status": "ready",
            },
            repair_expansion_map={
                "style": "physics_lean_repair_expansion_map",
                "status": "needs_expansion",
                "exhaustive": True,
            },
            recursive_repair_control={
                "style": "physics_lean_recursive_repair_control_plan",
                "status": "recurse",
            },
            final_review={
                "style": "physics_final_hypothesis_review",
                "status": "pass",
                "reviewed_properties": {"mathlib_grounding_level": "high"},
            },
            compile_ok=True,
            realness_ok=True,
            anchor_ok=True,
        )
        assert recursive_report["status"] == "draft"
        assert "recursive_repair_control_recurse" in recursive_report["blockers"]
    else:
        report = build_report(
            unit_report=load_json(args.unit_report),
            execution_report=load_json(args.execution_report),
            type_packet=load_json(args.type_packet),
            assumption_packet=load_json(args.assumption_packet),
            background_packet=load_json(args.background_packet),
            critic_reports=[load_json(path) for path in args.critic_report],
            pathology_repair_loop=load_json(args.pathology_repair_loop),
            generative_repair=load_json(args.generative_repair),
            repair_expansion_map=load_json(args.repair_expansion_map),
            recursive_repair_control=load_json(args.recursive_repair_control),
            final_review=load_json(args.final_review),
            compile_ok=args.compile_ok,
            realness_ok=args.realness_ok,
            anchor_ok=args.anchor_ok,
        )
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
