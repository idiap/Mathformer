#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Keep FormalPhysics Lean autoformalization goal loops one-sample scoped,
#   recursive, and explicit.
#
# Intent:
#   Build a deterministic plan that tells agents which sample is locked, which
#   gates matter, and how to recurse through MathformerPhysicsLib object work
#   before target theorem repair.
#
# Function:
#   Emits a physics_lean_goal_sample_autoformalization_plan and optionally runs
#   the current Lean/thoroughness gates for one formalphysics_#### sample.
#
# Maintenance Notes:
#   Keep the workflow steps aligned with physics-lean-repair-expansion-
#   cartographer and physics-lean-recursive-repair-loop-controller.

"""Plan one-sample recursive Lean physics autoformalization."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]
LEAN_ROOT = REPO_ROOT / "MathformerPhysicsLib" / "Lean"
THOROUGHNESS = (
    REPO_ROOT / "tests" / "physics_lean" / "run_grounded_sample_thoroughness.py"
)
FOUNDATION_VERIFIER = (
    REPO_ROOT
    / "skills"
    / "mathformerphysicslib"
    / "mathformerphysicslib-foundation-verifier"
    / "scripts"
    / "verify_foundation_modules.py"
)
DESIGN_TODO_ARTIFACT = (
    REPO_ROOT
    / "artifacts"
    / "physics_lean"
    / "reviews"
    / "autoformalization_design_todos.md"
)

CASE_RE = re.compile(r"formalphysics_(\d{4})")
OPEN_MARKERS = [
    ("sorry", re.compile(r"\bsorry\b")),
    ("admit", re.compile(r"\badmit\b")),
    ("todo", re.compile(r"\bTODO\b|\bFIXME\b", re.IGNORECASE)),
    ("generated_support_assumption", re.compile(r"GeneratedSupportAssumption")),
    (
        "target_restating_shortcut",
        re.compile(r"exact physicalLawHolds|exact generatedSupportHolds"),
    ),
    (
        "cycle_named_declaration",
        re.compile(r"\bdef\s+\w*cycle\d+\w*|\btheorem\s+\w*cycle\d+\w*"),
    ),
    (
        "unnecessary_from_frontier_name",
        re.compile(r"\b(?:def|theorem|abbrev)\s+\w+_from_frontier\b"),
    ),
]
SEMANTIC_CONTRACT_FIELDS = [
    "Semantic preservation contract",
    "Source target",
    "Lean target",
    "Preservation status",
    "Semantic deltas",
    "Step alignment",
    "Trust boundary",
]


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def normalize_case(raw: str | None, lean_file: Path | None) -> str:
    if raw:
        match = CASE_RE.search(raw)
        if match:
            return f"formalphysics_{match.group(1)}"
        if raw.isdigit():
            return f"formalphysics_{int(raw):04d}"
    if lean_file:
        match = CASE_RE.search(lean_file.as_posix())
        if match:
            return f"formalphysics_{match.group(1)}"
    raise SystemExit(
        "provide --case formalphysics_#### or --lean-file under formalphysics_####"
    )


def case_path(case_id: str, lean_file: Path | None) -> Path:
    if lean_file:
        return lean_file if lean_file.is_absolute() else REPO_ROOT / lean_file
    return LEAN_ROOT / case_id / "MathformerPhysics.lean"


def scan_open_markers(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return [{"kind": "missing_lean_file", "line": None, "text": rel(path)}]
    findings: list[dict[str, Any]] = []
    for index, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        for kind, pattern in OPEN_MARKERS:
            if pattern.search(line):
                findings.append({"kind": kind, "line": index, "text": line.strip()})
    return findings


def module_header_comment(text: str) -> str:
    match = re.search(r"/-!(.*?)\-/", text, re.S)
    return match.group(1) if match else ""


def scan_design_guards(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return [
            {"kind": "design_guard_missing_lean_file", "line": None, "text": rel(path)}
        ]
    text = path.read_text(encoding="utf-8")
    header = module_header_comment(text)
    findings: list[dict[str, Any]] = []
    for field in SEMANTIC_CONTRACT_FIELDS:
        if field.lower() not in header.lower():
            findings.append(
                {
                    "kind": "missing_semantic_preservation_contract_field",
                    "field": field,
                    "line": None,
                    "text": "module header does not expose the semantic-preservation contract field",
                }
            )
    for index, line in enumerate(text.splitlines(), start=1):
        if "PhysicsContext True" in line:
            findings.append(
                {
                    "kind": "vacuous_physics_context_true",
                    "line": index,
                    "text": line.strip(),
                }
            )
        if "required_grounding_terms" in line or "Audit anchor" in line:
            findings.append(
                {
                    "kind": "legacy_audit_anchor",
                    "line": index,
                    "text": line.strip(),
                }
            )
    reflexive_unit_pattern = re.compile(
        r"UnitDimensionCompatible\s+([A-Za-z0-9_.]+)\s+\1\b"
    )
    for index, line in enumerate(text.splitlines(), start=1):
        if reflexive_unit_pattern.search(line):
            findings.append(
                {
                    "kind": "reflexive_unit_dimension_bridge",
                    "line": index,
                    "text": line.strip(),
                }
            )
    return findings


def run_command(command: list[str], timeout: int = 240) -> dict[str, Any]:
    start = time.time()
    proc = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )
    duration = round(time.time() - start, 3)
    payload: Any = None
    stripped = proc.stdout.strip()
    if stripped.startswith("{"):
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            payload = None
    return {
        "command": command,
        "returncode": proc.returncode,
        "ok": proc.returncode == 0,
        "duration_seconds": duration,
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
        "json": payload,
    }


def workflow_steps(case_id: str) -> list[dict[str, Any]]:
    return [
        {
            "step": "lock_one_sample_goal",
            "owner_skill": "physics-lean-goal-sample-autoformalizer",
            "purpose": f"Only work on {case_id} until complete or explicitly blocked.",
        },
        {
            "step": "monitor_drift_pathologies",
            "owner_skill": "physics-lean-drift-pathology-monitor",
            "purpose": "Find semantic drift, notation collapse, shallow assumptions, and proof-strategy mismatch.",
        },
        {
            "step": "apply_autoformalization_design_todos",
            "owner_skill": "mathformerphysicslib-coherence-repair-planner",
            "purpose": (
                "Apply semantic-preservation contract, non-vacuous context, "
                "unit/dimension, unbounded-operator, metadata, and trust-state "
                "guards from the review TODO artifact before accepting new or repaired cases."
            ),
        },
        {
            "step": "detect_physics_objects",
            "owner_skill": "physics-math-object-detector",
            "purpose": "Identify concrete physics mathematical objects that must be grounded before theorem edits.",
        },
        {
            "step": "workbench_mathformerphysicslib_objects",
            "owner_skill": "mathformerphysicslib-object-workbench",
            "purpose": "Search, reuse, draft, or promote MathformerPhysicsLib support before target repair.",
        },
        {
            "step": "audit_mathlib_grounding",
            "owner_skill": "mathformerphysicslib-mathlib-grounding-auditor",
            "purpose": "Prevent duplicate local definitions when Mathlib or accepted foundations already provide a surface.",
        },
        {
            "step": "build_lean_workflow_packets",
            "owner_skill": "physics-lean-workflow-orchestrator",
            "purpose": "Build Lean workflow and background dependency plans before repair decisions.",
        },
        {
            "step": "build_lean_type_system",
            "owner_skill": "physics-lean-type-system-builder",
            "purpose": "Expose Mathlib-native carriers, calculus surfaces, operator surfaces, and background obligations.",
        },
        {
            "step": "encode_contextual_assumptions",
            "owner_skill": "physics-lean-assumption-context-encoder",
            "purpose": "Label source-backed, Mathlib-backed, generated-support, and blocked assumptions.",
        },
        {
            "step": "verify_unit_analysis",
            "owner_skill": "physics-lean-unit-analysis-verifier",
            "purpose": "Check visible unit and dimension obligations before acceptance.",
        },
        {
            "step": "critique_physical_semantics",
            "owner_skill": "physics-lean-physical-semantics-critic",
            "purpose": "Detect erased physics quantities, laws, vector/operator surfaces, and source alignment gaps.",
        },
        {
            "step": "critique_assumptions",
            "owner_skill": "physics-lean-assumption-critic",
            "purpose": "Detect hidden, missing, or unlabeled contextual assumptions.",
        },
        {
            "step": "critique_dimensions",
            "owner_skill": "physics-lean-dimension-critic",
            "purpose": "Detect missing dimension policy, scalar collapse, and unit-obligation gaps.",
        },
        {
            "step": "repair_notational_collapse",
            "owner_skill": "physics-lean-notational-collapse-repairer",
            "purpose": "Plan library-first repairs for collapsed physics notation.",
        },
        {
            "step": "repair_abstraction_elevation",
            "owner_skill": "physics-lean-abstraction-elevation-repairer",
            "purpose": "Plan library-first repairs when calculus, laws, or operators were abstracted away.",
        },
        {
            "step": "repair_proof_strategy_alignment",
            "owner_skill": "physics-lean-proof-strategy-alignment-repairer",
            "purpose": "Plan repairs when proof strategy bypasses required source transformations.",
        },
        {
            "step": "normalize_implicit_premises",
            "owner_skill": "physics-lean-implicit-premise-normalizer",
            "purpose": "Normalize side conditions and premise labels before target edits.",
        },
        {
            "step": "repair_deterministic_pathologies",
            "owner_skill": "physics-lean-pathology-repair-orchestrator",
            "purpose": "Aggregate all pathology-specific repair plans under the library-first policy.",
        },
        {
            "step": "plan_generative_repair",
            "owner_skill": "physics-lean-generative-repair-orchestrator",
            "purpose": "Use generative interpretation as advisory repair evidence with explicit rerun gates.",
        },
        {
            "step": "plan_generative_critique",
            "owner_skill": "physics-lean-generative-critic-orchestrator",
            "purpose": "Stress-test the candidate repair with advisory generative probes.",
        },
        {
            "step": "map_expansion",
            "owner_skill": "physics-lean-repair-expansion-cartographer",
            "purpose": "Enumerate every open pathology, object, library, generative, and rerun-gate obligation.",
        },
        {
            "step": "control_recursion",
            "owner_skill": "physics-lean-recursive-repair-loop-controller",
            "purpose": "Decide complete, recurse, or blocked from the exhaustive expansion map.",
        },
        {
            "step": "interpret_lean_execution",
            "owner_skill": "physics-lean-execution-interpreter",
            "purpose": "Classify Lean diagnostics and proof-realness evidence after compilation.",
        },
        {
            "step": "run_consistency_report",
            "owner_skill": "physics-lean-consistency-report-orchestrator",
            "purpose": "Combine unit, execution, critic, repair, generative, controller, and final-review evidence.",
        },
        {
            "step": "plan_review_refinement",
            "owner_skill": "physics-lean-review-refinement-router",
            "purpose": "If final review fails, emit localized monotonic refinement actions; otherwise mark not required.",
        },
        {
            "step": "rerun_gates",
            "owner_skill": "physics-lean-derivation-completeness-checker",
            "purpose": "Compile and prove the one sample reached complete_autoformalization.",
        },
    ]


def gate_commands(case_id: str, lean_path: Path) -> dict[str, list[str]]:
    return {
        "lean_compile": ["lake", "env", "lean", rel(lean_path)],
        "case_thoroughness": [
            sys.executable,
            rel(THOROUGHNESS),
            "--case",
            case_id,
            "--json",
        ],
        "foundation_verifier_if_foundations_changed": [
            sys.executable,
            rel(FOUNDATION_VERIFIER),
            "--json",
        ],
    }


def summarize_thoroughness(
    case_id: str, report: dict[str, Any] | None
) -> dict[str, Any] | None:
    if not report:
        return None
    cases = report.get("cases", [])
    for row in cases:
        if row.get("case_id") == case_id:
            return {
                "ok": row.get("ok"),
                "status": row.get("status"),
                "checks": row.get("checks", {}),
                "missing_terms": row.get("missing_terms", []),
                "forbidden_hits": row.get("forbidden_hits", []),
                "metrics": row.get("metrics", {}),
            }
    return {"ok": False, "status": "case_missing_from_thoroughness_report"}


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    lean_file = Path(args.lean_file) if args.lean_file else None
    case_id = normalize_case(args.case, lean_file)
    lean_path = case_path(case_id, lean_file)
    marker_findings = scan_open_markers(lean_path)
    design_guard_findings = scan_design_guards(lean_path)
    commands = gate_commands(case_id, lean_path)
    gate_results: dict[str, Any] = {}
    if args.run_gates:
        gate_results["lean_compile"] = run_command(commands["lean_compile"])
        gate_results["case_thoroughness"] = run_command(commands["case_thoroughness"])
    thoroughness_summary = summarize_thoroughness(
        case_id, (gate_results.get("case_thoroughness") or {}).get("json")
    )
    complete_by_gates = bool(
        thoroughness_summary
        and thoroughness_summary.get("ok")
        and thoroughness_summary.get("status") == "complete_autoformalization"
    )
    complete_by_scan = not marker_findings
    if not lean_path.exists():
        next_action = "blocked_missing_lean_file"
    elif args.run_gates and complete_by_gates and complete_by_scan:
        next_action = "complete"
    elif marker_findings or (args.run_gates and not complete_by_gates):
        next_action = "recurse"
    else:
        next_action = "run_gates"

    blockers = []
    if not lean_path.exists():
        blockers.append({"kind": "missing_lean_file", "path": rel(lean_path)})
    if args.max_iterations < 1:
        blockers.append(
            {"kind": "invalid_max_iterations", "max_iterations": args.max_iterations}
        )

    payload = {
        "schema_version": 1,
        "style": "physics_lean_goal_sample_autoformalization_plan",
        "ok": not blockers,
        "case_id": case_id,
        "lean_path": rel(lean_path),
        "goal": {
            "target_status": "complete_autoformalization",
            "scope": "one_sample_only",
            "max_iterations": args.max_iterations,
        },
        "current_evidence": {
            "lean_file_exists": lean_path.exists(),
            "open_marker_count": len(marker_findings),
            "open_markers": marker_findings,
            "design_guard_count": len(design_guard_findings),
            "design_guard_findings": design_guard_findings,
            "thoroughness": thoroughness_summary,
            "gate_results": gate_results,
        },
        "autoformalization_design_guard": {
            "todo_artifact": rel(DESIGN_TODO_ARTIFACT),
            "migration_status": "warning_until_existing_cases_are_migrated",
            "required_for_new_or_repaired_cases": [
                "semantic preservation contract in module header",
                "typed non-vacuous PhysicsContext propositions",
                "non-reflexive or dimension-algebra-backed UnitDimensionCompatible evidence",
                "explicit semantic deltas for scalar/component/operator projections",
                "dependency trust-state ledger for final theorem dependencies",
            ],
        },
        "recursive_policy": {
            "mathformerphysicslib_first": True,
            "generative_repair_advisory_until_deterministic_gates_pass": True,
            "batching_denied": True,
            "allowed_controller_decisions": ["complete", "recurse", "blocked"],
            "stop_conditions": [
                "case thoroughness status is complete_autoformalization and no open markers remain",
                "recursive controller reports repeated signature",
                "max iterations reached",
                "hard missing dependency blocker",
            ],
        },
        "workflow_steps": workflow_steps(case_id),
        "commands": commands,
        "next_action": next_action,
        "blockers": blockers,
    }
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case", help="FormalPhysics case id, e.g. formalphysics_0014 or 14."
    )
    parser.add_argument(
        "--lean-file",
        help="Path to MathformerPhysics.lean under a formalphysics_#### directory.",
    )
    parser.add_argument("--max-iterations", type=int, default=8)
    parser.add_argument(
        "--run-gates",
        action="store_true",
        help="Run Lean compile and per-case thoroughness gates.",
    )
    parser.add_argument("--output", type=Path, help="Optional output JSON path.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    payload = build_plan(args)
    if args.output:
        output = args.output if args.output.is_absolute() else REPO_ROOT / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
        )
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"{payload['next_action']} {payload['case_id']} {payload['lean_path']}")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
