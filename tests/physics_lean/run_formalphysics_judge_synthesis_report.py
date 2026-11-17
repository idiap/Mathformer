#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Keep the FormalPhysics judge synthesis workflow covered by a compact
#   deterministic test.
#
# Intent:
#   Validate that comparative-report evidence can be synthesized into
#   strengths, weaknesses, aspect comparisons, and follow-up TODOs.
#
# Function:
#   Runs the synthesis builder on a synthetic comparative report and checks the
#   generated JSON, Markdown, HTML, and TODO artifacts.
#
# Maintenance Notes:
#   Keep this test lightweight; full Codex-exec judge ingestion belongs to a
#   higher-cost integration workflow.

"""Validate the FormalPhysics judge synthesis report builder."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
REPORT_BUILDER = (
    REPO_ROOT
    / "skills"
    / "physics-common"
    / "formalphysics-judge-synthesis-reporter"
    / "scripts"
    / "build_synthesis_report.py"
)


METRICS = (
    "proof_integrity",
    "source_semantic_preservation",
    "derivation_coverage",
    "reference_delta_quality",
    "physics_object_fidelity",
    "physics_representation_completeness",
    "assumption_transparency",
    "mathlib_concept_grounding",
    "foundations_dependency_quality",
    "formal_physics_modeling_depth",
    "variable_naming_quality",
    "reviewability_clarity",
    "maintainability",
    "reportability",
)


def score_block(value: float) -> dict[str, Any]:
    return {"score": value, "evidence": [f"synthetic score {value}"]}


def candidate(
    candidate_id: str, *, accepted: bool, base_score: float, invoked_count: int
) -> dict[str, Any]:
    status = "accepted" if accepted else "blocked"
    blockers = [] if accepted else ["lean_does_not_compile"]
    return {
        "candidate_id": candidate_id,
        "aggregate": {"status": status, "hard_blockers": blockers},
        "hard_gates": {
            "lean_compiles": accepted,
            "no_sorry": True,
            "no_admit": True,
            "nontrivial_body": True,
        },
        "scores": {metric: score_block(base_score) for metric in METRICS},
        "critic_evidence": {
            "mathlib_grounding_critic": {
                "matched_mathlib_concept_families": ["Real", "Differentiable"]
            },
            "physics_completeness_critic": {
                "physics_complexity_hits": ["quantity", "unit", "force"]
            },
            "naming_reviewability_critic": {
                "source_step_annotation_count": int(base_score)
            },
            "formality_depth_critic": {"modeling_declaration_count": int(base_score)},
            "invoked_dependency_excerpt_critic": {
                "invoked_external_dependency_excerpt_count": invoked_count,
                "invoked_external_dependency_paths": (
                    ["libraries/MathformerPhysicsLib/Lean/Foundations/Units.lean"]
                    if invoked_count
                    else []
                ),
                "invoked_external_dependency_names": (
                    ["UnitDimensionCompatible"] if invoked_count else []
                ),
            },
        },
        "foundations_dependency": {
            "invoked_external_dependency_excerpts": (
                [
                    {
                        "path": "libraries/MathformerPhysicsLib/Lean/Foundations/Units.lean",
                        "name": "UnitDimensionCompatible",
                    }
                ]
                if invoked_count
                else []
            )
        },
        "generative_judges": {
            "prompts": [
                {
                    "judge_id": "adversarial_reference_judge",
                    "case_id": "formalphysics_0000",
                    "candidate_id": candidate_id,
                    "result_status": "pending_codex_exec",
                },
                {
                    "judge_id": "physics_expert",
                    "case_id": "formalphysics_0000",
                    "candidate_id": candidate_id,
                    "result_status": "pending_codex_exec",
                },
            ]
        },
    }


def write_comparative_report(path: Path) -> None:
    report = {
        "style": "formalphysics_comparative_analysis_report",
        "created_at": "2026-01-01T00:00:00+00:00",
        "input_json": "selected_examples.json",
        "policy": {
            "reference_answer_role": "non_gold_reference_evidence",
            "reference_answer_is_gold": False,
        },
        "summary": {"case_count": 1, "candidate_count": 2},
        "metric_criteria": {metric: f"Criterion for {metric}" for metric in METRICS},
        "cases": [
            {
                "case_id": "formalphysics_0000",
                "best_solution": {
                    "candidate_id": "current_mathformer_lean",
                    "status": "functional_best",
                },
                "candidates": [
                    candidate(
                        "external_formaldiscovery",
                        accepted=False,
                        base_score=2.0,
                        invoked_count=0,
                    ),
                    candidate(
                        "current_mathformer_lean",
                        accepted=True,
                        base_score=4.5,
                        invoked_count=3,
                    ),
                ],
            }
        ],
        "qualitative_reviews": {
            "theorem_prover_expert": {
                "aggregate": {"preference_counts": {"current_mathformer_lean": 1}},
                "cases": [
                    {
                        "case_id": "formalphysics_0000",
                        "preference": {"candidate_id": "current_mathformer_lean"},
                    }
                ],
            },
            "physics_expert": {
                "aggregate": {"preference_counts": {"current_mathformer_lean": 1}},
                "cases": [
                    {
                        "case_id": "formalphysics_0000",
                        "preference": {"candidate_id": "current_mathformer_lean"},
                    }
                ],
            },
        },
    }
    report["codex_exec_judge_prompts"] = [
        prompt
        for case in report["cases"]
        for candidate_item in case["candidates"]
        for prompt in candidate_item.get("generative_judges", {}).get("prompts", [])
    ]
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def write_codex_results(path: Path) -> None:
    results = [
        {
            "judge_id": "adversarial_reference_judge_v1",
            "case_id": "formalphysics_0000",
            "candidate_id": "current_mathformer_lean",
            "scores": {"proof_integrity": {"score": 5}, "grounding": {"score": 5}},
            "hard_gate_findings": [],
            "uncertainty": "low",
            "repair_suggestions": [],
        },
        {
            "judge_id": "adversarial_reference_judge_v1",
            "case_id": "formalphysics_0000",
            "candidate_id": "external_formaldiscovery",
            "scores": {"proof_integrity": {"score": 2}, "grounding": {"score": 2}},
            "hard_gate_findings": ["no_unsound_placeholders"],
            "uncertainty": "medium",
            "repair_suggestions": ["remove placeholders"],
        },
    ]
    path.write_text(
        json.dumps({"results": results}, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def run_report_builder(
    comparative_report: Path,
    output_dir: Path,
    codex_results: Path,
) -> tuple[int, dict[str, Any], str]:
    completed = subprocess.run(
        [
            sys.executable,
            str(REPORT_BUILDER),
            "--comparative-report",
            str(comparative_report),
            "--output-dir",
            str(output_dir),
            "--codex-results-json",
            str(codex_results),
            "--json",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        payload = {}
    return completed.returncode, payload, completed.stderr


ARTIFACT_KEYS = ("json", "html", "markdown", "todos")
HTML_MARKERS = (
    "FormalPhysics Judge Synthesis",
    "Aspect Comparison",
    "Strengths",
    "Weaknesses",
    "Prompt Readiness",
    "Completed Result Disagreements",
    "Action Register",
)


def prepare_fixture(tmp: Path) -> dict[str, str]:
    """Write the native synthetic evidence within a caller-owned temporary scope."""
    comparative_report = tmp / "comparative_report.json"
    codex_results = tmp / "codex_results.json"
    output_dir = tmp / "synthesis"
    write_comparative_report(comparative_report)
    write_codex_results(codex_results)
    return {
        "root": str(tmp),
        "comparative": str(comparative_report),
        "results": str(codex_results),
        "output": str(output_dir),
    }


def invoke_builder(workspace: dict[str, str]) -> dict[str, Any]:
    code, payload, stderr = run_report_builder(
        Path(workspace["comparative"]),
        Path(workspace["output"]),
        Path(workspace["results"]),
    )
    return {"code": code, "payload": payload, "stderr": stderr}


def start_checks(workspace: dict[str, str], result: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    code, payload, stderr = result["code"], result["payload"], result["stderr"]
    if code != 0:
        findings.append(
            {"severity": "high", "code": "synthesis_builder_failed", "stderr": stderr}
        )
    if payload.get("ok") is not True:
        findings.append(
            {"severity": "high", "code": "synthesis_builder_not_ok", "payload": payload}
        )
    return {
        "workspace": workspace,
        "artifacts": payload.get("artifacts", {}),
        "findings": findings,
        "index": 0,
        "html_text": "",
    }


def check_artifact(state: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    key = ARTIFACT_KEYS[state["index"]]
    artifacts = state["artifacts"]
    path_text = artifacts.get(key)
    if not path_text or not Path(path_text).exists():
        state["findings"].append(
            {
                "severity": "high",
                "code": f"missing_{key}_artifact",
                "artifacts": artifacts,
            }
        )
    state["index"] += 1
    return state, state["index"] == len(ARTIFACT_KEYS)


def prepare_inspection(
    state: dict[str, Any], format: str
) -> tuple[dict[str, Any], bool]:
    path = (
        Path(state["artifacts"].get(format, ""))
        if state["artifacts"].get(format)
        else None
    )
    present = bool(path and path.exists())
    if format == "html" and present:
        state["html_text"] = path.read_text(encoding="utf-8")
        state["index"] = 0
    return state, present


def check_json(state: dict[str, Any]) -> dict[str, Any]:
    report_json = Path(state["artifacts"]["json"])
    findings = state["findings"]
    synthesis = json.loads(report_json.read_text(encoding="utf-8"))
    if synthesis.get("style") != "formalphysics_judge_synthesis_report":
        findings.append({"severity": "high", "code": "wrong_synthesis_style"})
    if (
        synthesis.get("policy", {}).get("reference_answer_role")
        != "non_gold_reference_evidence"
    ):
        findings.append({"severity": "high", "code": "reference_policy_not_preserved"})
    approaches = synthesis.get("approaches", {})
    current = approaches.get("current_mathformer_lean", {})
    external = approaches.get("external_formaldiscovery", {})
    if current.get("accepted_count") != 1 or external.get("blocked_count") != 1:
        findings.append(
            {
                "severity": "high",
                "code": "approach_statuses_not_synthesized",
                "approaches": approaches,
            }
        )
    if not current.get("strengths") or not external.get("weaknesses"):
        findings.append({"severity": "high", "code": "strengths_or_weaknesses_missing"})
    if len(synthesis.get("aspect_comparison", [])) < 5:
        findings.append({"severity": "high", "code": "aspect_comparison_incomplete"})
    if not synthesis.get("synthesis_todos"):
        findings.append({"severity": "high", "code": "synthesis_todos_missing"})
    judge_summary = synthesis.get("judge_review_synthesis", {})
    if judge_summary.get("codex_exec_results_ingested") != 2:
        findings.append(
            {
                "severity": "high",
                "code": "codex_results_not_ingested",
                "judge_summary": judge_summary,
            }
        )
    patterns = judge_summary.get("codex_exec_disagreement_patterns", {})
    if not patterns.get("agreement_counts"):
        findings.append(
            {
                "severity": "high",
                "code": "codex_disagreement_patterns_missing",
                "patterns": patterns,
            }
        )
    todo_state = synthesis.get("todo_state_summary", {})
    if todo_state.get("open_repo_actionable_count") != 0:
        findings.append(
            {
                "severity": "high",
                "code": "todo_actionability_not_classified",
                "todo_state": todo_state,
            }
        )
    return state


def carry_state(state: dict[str, Any]) -> dict[str, Any]:
    return state


def check_marker(state: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    marker = HTML_MARKERS[state["index"]]
    if marker not in state["html_text"]:
        state["findings"].append(
            {"severity": "high", "code": "html_marker_missing", "marker": marker}
        )
    state["index"] += 1
    return state, state["index"] == len(HTML_MARKERS)


def finish(state: dict[str, Any]) -> dict[str, Any]:
    findings = state["findings"]
    return {
        "schema_version": 1,
        "ok": not any(item["severity"] == "high" for item in findings),
        "style": "formalphysics_judge_synthesis_report_test",
        "findings": findings,
    }


def run_check() -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as raw_tmp:
        workspace = prepare_fixture(Path(raw_tmp))
        state = start_checks(workspace, invoke_builder(workspace))
        for _ in ARTIFACT_KEYS:
            check_artifact(state)
        state, present = prepare_inspection(state, "json")
        if present:
            check_json(state)
        state, present = prepare_inspection(state, "html")
        if present:
            for _ in HTML_MARKERS:
                check_marker(state)
    return finish(state)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = run_check()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"ok: {report['ok']}")
    return 0 if report["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
