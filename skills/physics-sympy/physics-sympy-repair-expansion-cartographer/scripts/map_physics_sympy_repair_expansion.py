#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Make recursive SymPy physics repair expansion exhaustive and inspectable.
#
# Intent:
#   Convert one-sample goal evidence and review findings into a stable expansion
#   map before another repair iteration is allowed.
#
# Function:
#   Emits node coverage, outstanding obligations, next-frontier actions, rerun
#   gates, and an iteration signature.
#
# Maintenance Notes:
#   Keep terminal statuses synchronized with the SymPy recursive repair
#   controller.

"""Map recursive SymPy physics repair expansion."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, NoReturn, Sequence

REPO_ROOT = Path(__file__).resolve().parents[4]
REASONING_LOG_SCRIPTS = (
    REPO_ROOT / "skills" / "control" / "reasoning-log-schema-guardian" / "scripts"
)
if str(REASONING_LOG_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(REASONING_LOG_SCRIPTS))
try:
    from reasoning_log import append_reasoning_log_entry
except Exception:  # pragma: no cover - logging is optional for this script.
    append_reasoning_log_entry = None
PLANNER = (
    REPO_ROOT
    / "skills"
    / "physics-sympy"
    / "physics-sympy-goal-sample-autoformalizer"
    / "scripts"
    / "plan_goal_sample_sympy_autoformalization.py"
)

SURFACE_OWNER = {
    "source_anchor": "physics-sympy-goal-sample-autoformalizer",
    "quantity": "physics-sympy-equation-surface-builder",
    "dimension": "physics-dimension-modeler",
    "unit": "physics-unit-system-grounder",
    "frame": "physics-coordinate-frame-context-builder",
    "regime": "physics-regime-assumption-modeler",
    "equation_node": "physics-sympy-equation-surface-builder",
    "law_grounding": "physics-law-concept-grounding-navigator",
    "sympy_api_grounding": "physics-sympy-library-grounding-builder",
    "projection_bridge": "physics-sympy-dimension-projection-critic",
    "transformation_step": "physics-derivation-step-verifier",
    "numeric_domain": "physics-numeric-sanity-sampler",
    "target_nonleakage": "physics-sympy-equational-semantics-critic",
    "trace_realness": "physics-sympy-execution-runner",
    "consumer_reasoning_log": "reasoning-log-schema-guardian",
}

SURFACE_ACTION = {
    "source_anchor": "repair source commentary, anchors, and SymPy alignment before changing equations",
    "quantity": "repair quantity surface metadata and preserve existing source anchors",
    "dimension": "repair the affected dimension model and rerun unit/dimension gates",
    "unit": "repair unit grounding and rerun unit analysis",
    "frame": "make coordinate frame and sign convention explicit",
    "regime": "make approximation, domain, and side-condition regime explicit",
    "equation_node": "repair only the affected equation graph node",
    "law_grounding": "ground the affected physical law or generated bridge",
    "sympy_api_grounding": "ground the required role in installed SymPy or dependency APIs",
    "projection_bridge": "repair the scalar/vector/field projection bridge",
    "transformation_step": "repair the failing executable transformation certificate",
    "numeric_domain": "tighten numeric sampling domains and counterexample policy",
    "target_nonleakage": "remove target-shaped source inputs or expected-answer shortcuts",
    "trace_realness": "make artifact import, execute, and expose real validation evidence",
    "consumer_reasoning_log": "emit consumer-grade reasoning-log events for the decision",
}

SURFACE_PRIORITY = [
    "source_anchor",
    "quantity",
    "dimension",
    "unit",
    "frame",
    "regime",
    "equation_node",
    "law_grounding",
    "sympy_api_grounding",
    "projection_bridge",
    "transformation_step",
    "numeric_domain",
    "target_nonleakage",
    "trace_realness",
    "consumer_reasoning_log",
]

RECURSIVE_RERUN_GATES = [
    "physics.sympy.goal_sample.plan",
    "physics.sympy.source_only.run",
    "physics.sympy.repair_expansion.map",
    "physics.sympy.recursive_repair.control",
    "physics.sympy.library_grounding.build",
    "physics.sympy.equation_surface.build",
    "physics.sympy.assumptions.encode",
    "execute.physics_sympy_derivation",
    "execute.physics_sympy_interpret",
    "physics.units.verify",
    "physics.steps.verify",
    "physics.numeric.sample",
    "critique.physics_sympy_semantics",
    "critique.physics_sympy_dimensions",
    "review.physics_sympy_final_equations",
    "review.mathematical_sympy_final_equations",
    "physics.sympy.design_guard.review",
    "physics.sympy.grounded_sample.thoroughness",
    "refine.physics_sympy_review",
    "consistency.physics_derivation_report",
]


def load_json(path: Path | None) -> dict[str, Any]:
    """Load an optional JSON object."""
    if path is None:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_many(paths: Sequence[Path]) -> list[dict[str, Any]]:
    """Load multiple JSON objects."""
    return [load_json(path) for path in paths]


def run_goal_planner(case_id: str) -> dict[str, Any]:
    """Build a current goal plan for a case when no plan file is supplied."""
    proc = subprocess.run(
        [sys.executable, str(PLANNER), "--case", case_id, "--run-gates", "--json"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=240,
    )
    try:
        parsed = json.loads(proc.stdout)
    except json.JSONDecodeError:
        parsed = {}
    if proc.returncode != 0 or not parsed:
        return {
            "style": "physics_sympy_goal_sample_autoformalization_plan",
            "backend": "sympy",
            "case_id": case_id,
            "goal_status": "blocked",
            "next_action": "blocked",
            "findings": [
                {
                    "code": "goal_planner_failed",
                    "severity": "high",
                    "message": "goal planner failed before expansion map construction",
                    "repair_surface": "trace_realness",
                    "evidence": {
                        "returncode": proc.returncode,
                        "stdout_tail": proc.stdout[-2000:],
                        "stderr_tail": proc.stderr[-2000:],
                    },
                }
            ],
        }
    return parsed


def stable_signature(payload: dict[str, Any]) -> str:
    """Return a stable short signature for recursion control."""
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]


def surface_sort_key(surface: str) -> tuple[int, str]:
    """Sort surfaces in repair order."""
    try:
        return (SURFACE_PRIORITY.index(surface), surface)
    except ValueError:
        return (len(SURFACE_PRIORITY), surface)


def node_from_finding(
    index: int, case_id: str, finding: dict[str, Any]
) -> dict[str, Any]:
    """Create one expansion node from a planner or reviewer finding."""
    surface = str(finding.get("repair_surface") or "trace_realness")
    code = str(finding.get("code") or "unknown_finding")
    severity = str(finding.get("severity") or "high")
    terminal = severity not in {"high", "critical"}
    return {
        "id": f"{case_id}.{surface}.{index:03d}",
        "kind": "sympy_repair_frontier",
        "status": "satisfied" if terminal else "open",
        "owner_skill": SURFACE_OWNER.get(
            surface, "physics-sympy-review-refinement-router"
        ),
        "repair_surface": surface,
        "terminal": terminal,
        "blockers": [] if terminal else [code],
        "evidence": {
            "finding_code": code,
            "message": finding.get("message"),
            "line": finding.get("line"),
            "evidence": finding.get("evidence"),
        },
    }


def findings_from_reviews(reviews: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collect compatible findings from optional review reports."""
    findings: list[dict[str, Any]] = []
    for report in reviews:
        report_findings: list[dict[str, Any]] = []
        for item in report.get("findings", []) or report.get("diagnostics", []):
            if isinstance(item, dict):
                report_findings.append(item)
        findings.extend(report_findings)
        high_surfaces = {
            str(item.get("repair_surface"))
            for item in report_findings
            if str(item.get("severity", "high")) in {"high", "critical"}
            and item.get("repair_surface")
        }
        if not report_findings and str(report.get("status")) in {"fail", "blocked"}:
            high_surfaces.update(
                str(surface) for surface in report.get("repair_surfaces", []) if surface
            )
        for surface in sorted(high_surfaces, key=surface_sort_key):
            findings.append(
                {
                    "code": "review_requested_surface",
                    "severity": "high",
                    "message": "review requested a blocking repair surface",
                    "repair_surface": surface,
                    "evidence": {"source_style": report.get("style")},
                }
            )
    return findings


def build_map(
    goal_plan: dict[str, Any], reviews: Sequence[dict[str, Any]]
) -> dict[str, Any]:
    """Build the SymPy repair expansion map."""
    case_id = str(goal_plan.get("case_id", "formalphysics_unknown"))
    findings = [
        item
        for item in goal_plan.get("findings", [])
        if isinstance(item, dict)
        and str(item.get("severity", "high")) in {"high", "critical"}
    ]
    findings.extend(findings_from_reviews(reviews))
    nodes = [
        node_from_finding(index, case_id, item)
        for index, item in enumerate(findings, start=1)
    ]
    outstanding = [item for item in nodes if not item["terminal"]]
    outstanding.sort(key=lambda item: surface_sort_key(str(item["repair_surface"])))
    status = (
        "complete"
        if str(goal_plan.get("next_action")) == "complete" and not outstanding
        else "needs_expansion"
    )
    if str(goal_plan.get("next_action")) == "blocked":
        status = "blocked"
    frontier = [
        {
            "order": index,
            "node_id": item["id"],
            "owner_skill": item["owner_skill"],
            "repair_surface": item["repair_surface"],
            "action": SURFACE_ACTION.get(
                str(item["repair_surface"]), "perform the smallest local SymPy repair"
            ),
            "blockers": item["blockers"],
        }
        for index, item in enumerate(outstanding, start=1)
    ]
    signature_payload = {
        "case_id": case_id,
        "status": status,
        "outstanding": [
            {
                "surface": item["repair_surface"],
                "blockers": item["blockers"],
            }
            for item in outstanding
        ],
    }
    return {
        "style": "physics_sympy_repair_expansion_map",
        "backend": "sympy",
        "case_id": case_id,
        "status": status,
        "exhaustive": True,
        "node_count": len(nodes),
        "outstanding_node_count": len(outstanding),
        "nodes": nodes,
        "outstanding_nodes": outstanding,
        "next_frontier": frontier,
        "iteration_signature": stable_signature(signature_payload),
        "required_rerun_gates": RECURSIVE_RERUN_GATES,
        "sympy_only_boundary": {
            "forbidden_backend_workflows": [
                "physics_lean",
                "lean_physics_derivation_trace_loop",
            ],
            "allowed_surfaces": SURFACE_PRIORITY,
        },
    }


def rel(path: Path) -> str:
    """Return a repository-relative display path when possible."""
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def append_map_event(
    reasoning_log: Path | None, expansion: dict[str, Any], output_path: Path | None
) -> None:
    """Append the repair-expansion decision to a reasoning-log JSONL file."""
    if reasoning_log is None or append_reasoning_log_entry is None:
        return
    case_id = str(expansion.get("case_id", "unspecified"))
    append_reasoning_log_entry(
        reasoning_log,
        step="physics_sympy_repair_expansion_map_complete",
        payload={
            "skill": "physics-sympy-repair-expansion-cartographer",
            "hook_id": "physics.sympy.repair_expansion.map",
            "goal_id": f"sympy:{case_id}:recursive_goal",
            "case_id": case_id,
            "stage": "physics_sympy_repair_expansion_map_complete",
            "status": expansion.get("status"),
            "evidence": {
                "exhaustive": expansion.get("exhaustive"),
                "node_count": expansion.get("node_count"),
                "outstanding_node_count": expansion.get("outstanding_node_count"),
                "iteration_signature": expansion.get("iteration_signature"),
            },
            "artifacts": {"output": None if output_path is None else rel(output_path)},
            "decision": {
                "status": expansion.get("status"),
                "next_frontier": expansion.get("next_frontier", []),
            },
            "risks": expansion.get("outstanding_nodes", []),
            "next_action": "control recursion before the next local SymPy repair",
        },
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case")
    parser.add_argument("--goal-plan", type=Path)
    parser.add_argument("--review", action="append", type=Path, default=[])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--reasoning-log", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def self_test_map() -> dict[str, Any]:
    """Run the three native probes in order and return the first map."""
    goal_plan = {
        "case_id": "formalphysics_0000",
        "next_action": "recurse",
        "findings": [
            {
                "code": "library_grounding_not_high",
                "severity": "high",
                "message": "library grounding is below complete threshold",
                "repair_surface": "sympy_api_grounding",
            }
        ],
    }
    expansion = build_map(goal_plan, [])
    assert expansion["status"] == "needs_expansion"
    assert expansion["next_frontier"][0]["repair_surface"] == "sympy_api_grounding"
    complete_plan = {
        "case_id": "formalphysics_0000",
        "next_action": "complete",
        "findings": [],
    }
    medium_review = {
        "status": "pass",
        "repair_surfaces": ["consumer_reasoning_log"],
        "findings": [
            {
                "code": "reasoning_log_not_requested",
                "severity": "medium",
                "message": "reasoning log was not requested in this standalone probe",
                "repair_surface": "consumer_reasoning_log",
            }
        ],
    }
    medium_expansion = build_map(complete_plan, [medium_review])
    assert medium_expansion["status"] == "complete"
    assert medium_expansion["outstanding_node_count"] == 0
    fail_review = {
        "status": "fail",
        "repair_surfaces": ["target_nonleakage"],
        "findings": [
            {
                "code": "target_nonleakage_not_proven",
                "severity": "high",
                "message": "target nonleakage was not proven",
                "repair_surface": "target_nonleakage",
            }
        ],
    }
    fail_expansion = build_map(complete_plan, [fail_review])
    assert fail_expansion["status"] == "needs_expansion"
    assert fail_expansion["next_frontier"][0]["repair_surface"] == "target_nonleakage"
    return expansion


def emit_map(
    expansion: dict[str, Any], output_path: Path | None, reasoning_log: Path | None
) -> dict[str, Any]:
    """Serialize, output, then append the native optional reasoning event."""
    output = json.dumps(expansion, ensure_ascii=False, indent=2)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    append_map_event(reasoning_log, expansion, output_path)
    return {"serialized_json": output, "exit_code": 0}


def missing_input_plan() -> NoReturn:
    """Raise the native missing-input exit for both CLI and callable bindings."""
    raise SystemExit("provide --goal-plan or --case")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the cartographer using the shared callable steps."""
    args = parse_args(argv)
    if args.self_test:
        expansion = self_test_map()
    else:
        if args.goal_plan:
            goal_plan = load_json(args.goal_plan)
        elif args.case:
            goal_plan = run_goal_planner(args.case)
        else:
            missing_input_plan()
        expansion = build_map(goal_plan, load_many(args.review))
    return emit_map(expansion, args.output, args.reasoning_log)["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
