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

"""Aggregate final physics and mathematical derivation reviews."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[4]
REASONING_LOG_SCRIPTS = (
    REPO_ROOT / "skills" / "control" / "reasoning-log-schema-guardian" / "scripts"
)
if str(REASONING_LOG_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(REASONING_LOG_SCRIPTS))

from reasoning_log import append_skill_complete, append_skill_start  # noqa: E402

DESIGN_TODO_ARTIFACT = (
    "artifacts/physics_lean/reviews/autoformalization_design_todos.md"
)

DESIGN_GUARD_WARNING_CODES = frozenset(
    {
        "semantic_preservation_contract_incomplete",
        "vacuous_physics_context_true",
        "reflexive_unit_dimension_bridge",
        "legacy_required_grounding_terms_anchor",
    }
)

DESIGN_GUARD_SURFACE_BY_CODE = {
    "semantic_preservation_contract_incomplete": "source_alignment_commentary",
    "vacuous_physics_context_true": "contextual_assumption",
    "reflexive_unit_dimension_bridge": "unit_dimension_obligation",
    "legacy_required_grounding_terms_anchor": "design_guard",
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


def normalize_report(
    report: dict[str, Any], style: str, not_applicable: bool = False
) -> dict[str, Any]:
    """Document the responsibility of ``normalize_report``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``normalize_report`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if not report and not_applicable:
        return {"style": style, "status": "not_applicable", "findings": []}
    if not report:
        return {"style": style, "status": "missing", "findings": []}
    return report


def collect_design_guard_warnings(
    report: dict[str, Any], source_review: str
) -> list[dict[str, Any]]:
    """Collect review findings that should drive semantic-design follow-up."""
    warnings: list[dict[str, Any]] = []
    for raw in report.get("findings", []):
        if not isinstance(raw, dict):
            continue
        code = str(raw.get("code", ""))
        message = str(raw.get("message", ""))
        repair_surface = str(raw.get("repair_surface", ""))
        if code in DESIGN_GUARD_SURFACE_BY_CODE and not repair_surface:
            repair_surface = DESIGN_GUARD_SURFACE_BY_CODE[code]
        is_semantic_surface = repair_surface == "source_alignment_commentary" and (
            "semantic" in code.lower() or "semantic" in message.lower()
        )
        if code not in DESIGN_GUARD_WARNING_CODES and not is_semantic_surface:
            continue
        warnings.append(
            {
                "severity": str(raw.get("severity", "warning")),
                "code": code or "semantic_preservation_design_guard",
                "message": message
                or "Semantic-preservation design guard requires review follow-up.",
                "repair_surface": repair_surface or "design_guard",
                "source_review": source_review,
            }
        )
    return warnings


def build_report(
    *,
    physics_review: dict[str, Any],
    mathematical_review: dict[str, Any],
    consistency_report: dict[str, Any],
    physics_not_applicable: bool,
    reasoning_log_summary: dict[str, Any] | None = None,
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
    physics = normalize_report(
        physics_review, "physics_final_hypothesis_review", physics_not_applicable
    )
    math = normalize_report(mathematical_review, "mathematical_final_hypothesis_review")
    blockers: list[str] = []
    warnings: list[str] = []
    design_guard_warnings: list[dict[str, Any]] = []
    repair_surfaces: set[str] = set()
    protected_properties = [
        "source anchors",
        "original-informal to formal commentary alignment",
        "semantic-preservation contract fields",
        "theorem names",
        "Lean executability",
        "proof realness",
        "non-vacuity",
        "non-vacuous context and unit evidence",
        "unit and dimension coverage",
        "contextual assumption labels",
        "mathlib grounding",
        "previously passing reviewer findings",
    ]

    for report in [physics, math]:
        status = report.get("status", "missing")
        style = report.get("style", "unknown_review")
        if status in {"fail", "missing"}:
            blockers.append(f"{style}:{status}")
        elif status == "warn":
            warnings.append(f"{style}:warn")
        handoff = report.get("refinement_handoff", {})
        for surface in handoff.get("repair_surfaces", []):
            repair_surfaces.add(str(surface))
        source_review = "physics" if report is physics else "mathematical"
        for finding in collect_design_guard_warnings(report, source_review):
            design_guard_warnings.append(finding)
            repair_surfaces.add(str(finding["repair_surface"]))

    for finding in design_guard_warnings:
        warnings.append(f"design_guard:{finding['source_review']}:{finding['code']}")

    if consistency_report.get("status") == "blocked":
        blockers.append("upstream_consistency_blocked")
    elif consistency_report.get("status") == "draft":
        warnings.append("upstream_consistency_draft")

    status = "pass" if not blockers else "fail"
    compact_reasoning_summary = compact_reasoning_log_summary(
        reasoning_log_summary or {}
    )
    report = {
        "style": "final_derivation_hypothesis_review",
        "status": status,
        "blockers": blockers,
        "warnings": warnings,
        "design_guard_warnings": design_guard_warnings,
        "reviews": {
            "physics": {
                "style": physics.get("style"),
                "status": physics.get("status"),
                "finding_count": len(physics.get("findings", [])),
                "design_guard_warning_count": len(
                    collect_design_guard_warnings(physics, "physics")
                ),
            },
            "mathematical": {
                "style": math.get("style"),
                "status": math.get("status"),
                "finding_count": len(math.get("findings", [])),
                "design_guard_warning_count": len(
                    collect_design_guard_warnings(math, "mathematical")
                ),
            },
        },
        "refinement_required": bool(blockers),
        "review_followup_required": bool(blockers or design_guard_warnings),
        "design_guard_refinement_recommended": bool(design_guard_warnings),
        "design_review_todo_artifact": DESIGN_TODO_ARTIFACT,
        "reasoning_log_consumer_summary": compact_reasoning_summary,
        "refinement_handoff": {
            "router": "physics-lean-review-refinement-router",
            "repair_surfaces": sorted(repair_surfaces),
            "design_review_todo_artifact": DESIGN_TODO_ARTIFACT,
            "design_guard_warnings": design_guard_warnings,
            "protected_properties": protected_properties,
            "rerun_gates": [
                "review.physics_final_hypotheses",
                "review.mathematical_final_hypotheses",
                "review.final_derivation_hypotheses",
                "consistency.physics_lean_report",
            ],
        },
    }
    return report


def compact_reasoning_log_summary(summary: dict[str, Any]) -> dict[str, Any]:
    """Extract dashboard-safe reasoning-log evidence for final review reports."""
    if not summary:
        return {"status": "not_attached"}
    return {
        "status": "attached" if summary.get("ok") else "attached_with_findings",
        "run_id": summary.get("run_id"),
        "event_count": summary.get("event_count"),
        "skills": summary.get("skills", []),
        "hooks": summary.get("hooks", []),
        "validation_ok": summary.get("validation", {}).get("ok"),
        "quality_ok": summary.get("quality", {}).get("ok"),
        "next_actions": summary.get("next_actions", [])[:5],
        "risk_count": (
            len(summary.get("risks", []))
            if isinstance(summary.get("risks"), list)
            else 0
        ),
    }


def review_reasoning_evidence(report: dict[str, Any]) -> dict[str, Any]:
    """Build compact structured evidence for a review reasoning-log event."""
    surfaces = set(report.get("refinement_handoff", {}).get("repair_surfaces", []))
    return {
        "status": report.get("status"),
        "source_alignment_status": (
            "needs_repair"
            if "source_alignment_commentary" in surfaces
            else "not_flagged"
        ),
        "semantic_preservation_contract_status": (
            "needs_repair"
            if any(
                "semantic_preservation" in warning
                for warning in report.get("warnings", [])
            )
            else "not_flagged"
        ),
        "unit_dimension_status": (
            "needs_repair" if "unit_dimension_obligation" in surfaces else "not_flagged"
        ),
        "nonvacuity_status": (
            "needs_repair"
            if "nonvacuity" in surfaces or "target_nonvacuity" in surfaces
            else "not_flagged"
        ),
        "next_repair_action": (
            report.get("refinement_handoff", {}).get("repair_surfaces") or ["none"]
        )[0],
        "blockers": report.get("blockers", []),
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
    parser.add_argument("--physics-review", type=Path)
    parser.add_argument("--mathematical-review", type=Path)
    parser.add_argument("--consistency-report", type=Path)
    parser.add_argument("--physics-not-applicable", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--reasoning-log-summary", type=Path)
    parser.add_argument("--reasoning-log-file", type=Path)
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
    reasoning_summary = load_json(args.reasoning_log_summary)
    if args.self_test:
        report = build_report(
            physics_review={
                "style": "physics_final_hypothesis_review",
                "status": "fail",
                "findings": [{"repair_surface": "unit_dimension_obligation"}],
                "refinement_handoff": {
                    "repair_surfaces": ["unit_dimension_obligation"]
                },
            },
            mathematical_review={
                "style": "mathematical_final_hypothesis_review",
                "status": "pass",
                "findings": [],
            },
            consistency_report={"status": "draft"},
            physics_not_applicable=False,
            reasoning_log_summary=reasoning_summary,
        )
        assert report["status"] == "fail"
        assert (
            "unit_dimension_obligation"
            in report["refinement_handoff"]["repair_surfaces"]
        )
        warning_report = build_report(
            physics_review={
                "style": "physics_final_hypothesis_review",
                "status": "warn",
                "findings": [
                    {
                        "severity": "warning",
                        "code": "semantic_preservation_contract_incomplete",
                        "message": "Missing Semantic preservation contract fields.",
                        "repair_surface": "source_alignment_commentary",
                    }
                ],
            },
            mathematical_review={
                "style": "mathematical_final_hypothesis_review",
                "status": "pass",
                "findings": [],
            },
            consistency_report={"status": "pass"},
            physics_not_applicable=False,
            reasoning_log_summary={
                "ok": True,
                "run_id": "self-test",
                "event_count": 2,
                "skills": ["reasoning-log-schema-guardian"],
                "hooks": ["review.final_derivation_hypotheses"],
                "validation": {"ok": True},
                "quality": {"ok": True},
                "next_actions": ["inspect design guard"],
                "risks": [],
            },
        )
        assert warning_report["status"] == "pass"
        assert warning_report["design_guard_refinement_recommended"]
        assert warning_report["review_followup_required"]
        assert (
            "source_alignment_commentary"
            in warning_report["refinement_handoff"]["repair_surfaces"]
        )
        assert warning_report["reasoning_log_consumer_summary"]["status"] == "attached"
    else:
        report = build_report(
            physics_review=load_json(args.physics_review),
            mathematical_review=load_json(args.mathematical_review),
            consistency_report=load_json(args.consistency_report),
            physics_not_applicable=args.physics_not_applicable,
            reasoning_log_summary=reasoning_summary,
        )
    if args.reasoning_log_file:
        call_id = append_skill_start(
            args.reasoning_log_file,
            skill="final-derivation-review-orchestrator",
            hook_id="review.final_derivation_hypotheses",
            intent="Aggregate final physics and mathematical derivation reviews.",
            inputs={
                "physics_review": (
                    str(args.physics_review) if args.physics_review else None
                ),
                "mathematical_review": (
                    str(args.mathematical_review) if args.mathematical_review else None
                ),
                "consistency_report": (
                    str(args.consistency_report) if args.consistency_report else None
                ),
            },
            artifacts={"output": str(args.output) if args.output else None},
            human_summary="Started final derivation review aggregation.",
        )
        append_skill_complete(
            args.reasoning_log_file,
            skill="final-derivation-review-orchestrator",
            hook_id="review.final_derivation_hypotheses",
            skill_call_id=call_id,
            intent="Aggregate final physics and mathematical derivation reviews.",
            inputs={"physics_not_applicable": bool(args.physics_not_applicable)},
            artifacts={"output": str(args.output) if args.output else None},
            evidence=review_reasoning_evidence(report),
            decision={"status": report.get("status")},
            risks={
                "warnings": report.get("warnings", []),
                "blockers": report.get("blockers", []),
            },
            next_action=(
                report.get("refinement_handoff", {}).get("repair_surfaces")
                or ["No repair required."]
            )[0],
            human_summary="Completed final derivation review aggregation.",
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
