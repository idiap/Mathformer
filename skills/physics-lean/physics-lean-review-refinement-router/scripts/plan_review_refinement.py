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

"""Plan localized monotonic refinement from final review findings."""

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

SURFACE_ACTIONS = {
    "quantity_typing": "Add or repair typed quantity bindings without changing the target conclusion.",
    "unit_dimension_obligation": "Add local dimension/unit hypotheses or lemmas for the affected transformation.",
    "contextual_assumption": "Label or source-anchor side conditions; do not silently strengthen hypotheses.",
    "law_grounding": "Replace target-shaped law assumptions with source-backed or generated-support law lemmas.",
    "frame_regime": "Add frame, sign, gauge, observer, or regime context near the affected theorem.",
    "projection_bridge": "Add a projection lemma connecting scalar coordinates back to typed physical quantities.",
    "mathlib_grounding": (
        "Replace avoidable local wrappers, opaque dimension placeholders, and String context labels with "
        "Mathlib-native theorem surfaces while preserving the proven scalar core as a support lemma."
    ),
    "target_nonvacuity": "Remove target-shaped axioms, target hypotheses, or vacuous premises.",
    "binder_domain": "Repair only the affected binders and domains.",
    "quantifier_shape": "Restore forall, exists, uniqueness, iff, or implication shape from the source.",
    "side_condition": "Add only necessary side conditions with source or generated-support labels.",
    "conclusion_shape": "Restore the source conclusion; rerun all semantic and non-vacuity gates.",
    "support_dependency": (
        "Formalize or reuse only the missing intermediate definition, background result, projection bridge, "
        "source-law support lemma, unit/dimension bridge, or algebraic core named by the review finding."
    ),
    "source_alignment_commentary": (
        "Add or repair the semantic-preservation contract fields, source/Lean target mapping, "
        "preservation status, semantic deltas, step alignment, and trust boundary without changing "
        "the theorem body."
    ),
    "design_guard": (
        "Apply the smallest autoformalization design TODO repair for the named warning, preserving "
        "the current theorem shape and all passing reviewer evidence."
    ),
    "proof_realness": "Replace placeholders in the proof without changing the theorem statement.",
    "nonvacuity": "Remove contradictory or target-shaped hypotheses and rerun non-vacuity checks.",
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


def collect_surfaces(report: dict[str, Any]) -> list[str]:
    """Document the responsibility of ``collect_surfaces``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``collect_surfaces`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    surfaces: set[str] = set()
    handoff = report.get("refinement_handoff", {})
    for surface in handoff.get("repair_surfaces", []):
        surfaces.add(str(surface))
    for review in report.get("reviews", {}).values():
        for surface in review.get("repair_surfaces", []):
            surfaces.add(str(surface))
    for finding in report.get("findings", []):
        if finding.get("repair_surface"):
            surfaces.add(str(finding["repair_surface"]))
    return sorted(surfaces)


def collect_design_guard_findings(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Collect semantic-preservation and vacuity warnings that need review follow-up."""
    findings: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()

    def add(raw: Any, source_review: str) -> None:
        if not isinstance(raw, dict):
            return
        code = str(raw.get("code", ""))
        message = str(raw.get("message", ""))
        repair_surface = str(raw.get("repair_surface", ""))
        if code in DESIGN_GUARD_SURFACE_BY_CODE and not repair_surface:
            repair_surface = DESIGN_GUARD_SURFACE_BY_CODE[code]
        is_semantic_surface = repair_surface == "source_alignment_commentary" and (
            "semantic" in code.lower() or "semantic" in message.lower()
        )
        if code not in DESIGN_GUARD_WARNING_CODES and not is_semantic_surface:
            return
        normalized = {
            "severity": str(raw.get("severity", "warning")),
            "code": code or "semantic_preservation_design_guard",
            "message": message
            or "Semantic-preservation design guard requires review follow-up.",
            "repair_surface": repair_surface or "design_guard",
            "source_review": str(raw.get("source_review", source_review)),
        }
        key = (
            normalized["code"],
            normalized["message"],
            normalized["repair_surface"],
            normalized["source_review"],
        )
        if key not in seen:
            findings.append(normalized)
            seen.add(key)

    for finding in report.get("findings", []):
        add(finding, "top_level")
    for finding in report.get("design_guard_warnings", []):
        add(finding, "final_derivation")
    handoff = report.get("refinement_handoff", {})
    for finding in handoff.get("design_guard_warnings", []):
        add(finding, "refinement_handoff")
    for review_name, review in report.get("reviews", {}).items():
        if not isinstance(review, dict):
            continue
        for finding in review.get("findings", []):
            add(finding, str(review_name))
        for finding in review.get("design_guard_warnings", []):
            add(finding, str(review_name))
    return findings


def build_plan(
    *,
    final_review: dict[str, Any],
    baseline_report: dict[str, Any],
    reasoning_log_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Document the responsibility of ``build_plan``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    design_guard_findings = collect_design_guard_findings(final_review)
    surfaces = set(collect_surfaces(final_review))
    for finding in design_guard_findings:
        surfaces.add(str(finding.get("repair_surface", "design_guard")))
    if not surfaces:
        surfaces = {"review_packet_missing"}
    localized_actions = [
        {
            "repair_surface": surface,
            "action": SURFACE_ACTIONS.get(
                surface,
                "Inspect the review finding and create the smallest source-anchored repair.",
            ),
            "allowed_scope": "only the declaration, support lemma, assumption label, projection bridge, or proof fragment named by the review finding",
        }
        for surface in sorted(surfaces)
    ]
    rerun_gates = list(
        dict.fromkeys(
            final_review.get("refinement_handoff", {}).get(
                "rerun_gates",
                [
                    "review.physics_final_hypotheses",
                    "review.mathematical_final_hypotheses",
                    "review.final_derivation_hypotheses",
                ],
            )
        )
    )
    source_review_status = final_review.get("status", "missing")
    design_guard_required = bool(design_guard_findings)
    status = (
        "ready"
        if source_review_status == "fail"
        else "design_guard_review" if design_guard_required else "not_required"
    )
    return {
        "style": "physics_lean_review_refinement_plan",
        "status": status,
        "source_review_status": source_review_status,
        "review_followup_required": status in {"ready", "design_guard_review"},
        "design_review_todo_artifact": DESIGN_TODO_ARTIFACT,
        "design_guard_required": design_guard_required,
        "design_guard_findings": design_guard_findings,
        "localized_actions": localized_actions,
        "monotonicity_constraints": [
            "preserve every passing source anchor from the baseline",
            "preserve Lean executability unless the next step is a proof-local repair followed by execution",
            "do not weaken the theorem conclusion",
            "do not strengthen hypotheses without source-backed or generated-support labels",
            "do not remove passing unit, dimension, assumption, mathlib, realness, or non-vacuity evidence",
            "do not reduce Mathlib-native theorem-surface coverage",
            "do not reclassify local wrappers, opaque dimensions, or String labels as maximal grounding",
            "preserve semantic-preservation contract fields once present",
            "replace PhysicsContext True and reflexive UnitDimensionCompatible x x only with stronger source-backed evidence",
            "do not edit unrelated declarations",
            "rerun affected reviewers and protected gates before reporting complete status",
        ],
        "baseline_evidence": {
            "baseline_status": baseline_report.get("status", "missing"),
            "baseline_style": baseline_report.get("style", "missing"),
            "reasoning_log_summary": compact_reasoning_log_summary(
                reasoning_log_summary or {}
            ),
        },
        "rerun_gates": list(
            dict.fromkeys(
                [*rerun_gates, "tests/physics_lean/run_grounded_sample_thoroughness.py"]
            )
        ),
        "blocked_if": [
            "repair requires broad rewrite without source anchor",
            "repair would reduce a protected passing score",
            "repair would make another reviewer fail without explicit source-driven justification",
        ],
    }


def compact_reasoning_log_summary(summary: dict[str, Any]) -> dict[str, Any]:
    """Extract review-relevant reasoning-log fields without embedding the full log."""
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
    }


def plan_reasoning_evidence(plan: dict[str, Any]) -> dict[str, Any]:
    """Build compact structured evidence for a refinement-router event."""
    surfaces = [
        item.get("repair_surface") for item in plan.get("localized_actions", [])
    ]
    return {
        "status": plan.get("status"),
        "source_alignment_status": (
            "needs_repair"
            if "source_alignment_commentary" in surfaces
            else "not_flagged"
        ),
        "semantic_preservation_contract_status": (
            "needs_repair" if plan.get("design_guard_required") else "not_flagged"
        ),
        "unit_dimension_status": (
            "needs_repair" if "unit_dimension_obligation" in surfaces else "not_flagged"
        ),
        "nonvacuity_status": (
            "needs_repair"
            if "nonvacuity" in surfaces or "target_nonvacuity" in surfaces
            else "not_flagged"
        ),
        "next_repair_action": surfaces[0] if surfaces else "none",
        "blocked_if": plan.get("blocked_if", []),
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
    parser.add_argument("--final-review", type=Path)
    parser.add_argument("--baseline-report", type=Path)
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
        plan = build_plan(
            final_review={
                "style": "final_derivation_hypothesis_review",
                "status": "fail",
                "refinement_handoff": {
                    "repair_surfaces": [
                        "quantity_typing",
                        "conclusion_shape",
                        "mathlib_grounding",
                    ],
                    "rerun_gates": ["review.final_derivation_hypotheses"],
                },
            },
            baseline_report={
                "style": "physics_lean_consistency_report",
                "status": "draft",
            },
            reasoning_log_summary=reasoning_summary,
        )
        assert plan["status"] == "ready"
        assert len(plan["localized_actions"]) == 3
        assert any(
            item["repair_surface"] == "mathlib_grounding"
            for item in plan["localized_actions"]
        )
        warning_plan = build_plan(
            final_review={
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
            baseline_report={
                "style": "physics_lean_consistency_report",
                "status": "draft",
            },
            reasoning_log_summary={
                "ok": True,
                "run_id": "self-test",
                "event_count": 2,
                "skills": ["reasoning-log-schema-guardian"],
                "hooks": ["refine.physics_lean_review"],
                "validation": {"ok": True},
                "quality": {"ok": True},
                "next_actions": ["repair semantic commentary"],
            },
        )
        assert warning_plan["status"] == "design_guard_review"
        assert warning_plan["design_guard_required"]
        assert warning_plan["design_review_todo_artifact"] == DESIGN_TODO_ARTIFACT
        assert any(
            item["repair_surface"] == "source_alignment_commentary"
            for item in warning_plan["localized_actions"]
        )
        assert (
            warning_plan["baseline_evidence"]["reasoning_log_summary"]["status"]
            == "attached"
        )
    else:
        plan = build_plan(
            final_review=load_json(args.final_review),
            baseline_report=load_json(args.baseline_report),
            reasoning_log_summary=reasoning_summary,
        )
    if args.reasoning_log_file:
        call_id = append_skill_start(
            args.reasoning_log_file,
            skill="physics-lean-review-refinement-router",
            hook_id="refine.physics_lean_review",
            intent="Plan localized monotonic refinement from final review findings.",
            inputs={
                "final_review": str(args.final_review) if args.final_review else None,
                "baseline_report": (
                    str(args.baseline_report) if args.baseline_report else None
                ),
            },
            artifacts={"output": str(args.output) if args.output else None},
            human_summary="Started physics Lean review-refinement planning.",
        )
        append_skill_complete(
            args.reasoning_log_file,
            skill="physics-lean-review-refinement-router",
            hook_id="refine.physics_lean_review",
            skill_call_id=call_id,
            intent="Plan localized monotonic refinement from final review findings.",
            inputs={"final_review_status": plan.get("source_review_status")},
            artifacts={"output": str(args.output) if args.output else None},
            evidence=plan_reasoning_evidence(plan),
            decision={"status": plan.get("status")},
            risks={"blocked_if": plan.get("blocked_if", [])},
            next_action=(plan.get("localized_actions") or [{"repair_surface": "none"}])[
                0
            ]["repair_surface"],
            human_summary="Completed physics Lean review-refinement planning.",
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
