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

"""Plan localized monotonic refinement from SymPy physics reviews."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[4]
SYMPY_ROOT = REPO_ROOT / "MathformerPhysicsLib" / "SymPy"
CASE_RE = re.compile(r"formalphysics_(\d{4})")
REASONING_LOG_SCRIPTS = (
    REPO_ROOT / "skills" / "control" / "reasoning-log-schema-guardian" / "scripts"
)
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REASONING_LOG_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(REASONING_LOG_SCRIPTS))
try:
    from reasoning_log import append_reasoning_log_entry
except Exception:  # pragma: no cover - logging is optional at call sites.
    append_reasoning_log_entry = None

COMMENTARY_MARKERS = [
    "Original informal statement",
    "Informal derivation commentary",
    "SymPy alignment",
]
PASS_STATUSES = {
    "pass",
    "passed",
    "ready",
    "complete",
    "complete_sympy_physics_derivation",
    "ok",
}
PROJECTION_PASS_STATUSES = {"provided", "pass", "passed", "ready", "required"}
ASSUMPTION_SUPPORT_LABELS = {
    "source_backed",
    "generated_support",
    "api_backed",
    "blocked",
}

SURFACE_ACTIONS = {
    "source_anchor": "Repair source commentary, informal derivation summary, or SymPy alignment without changing equations.",
    "quantity_surface": "Add or repair quantity metadata without changing already-correct equations.",
    "assumption_context": "Add source-backed or generated-support assumption labels and side conditions locally.",
    "unit_dimension": "Repair the affected unit or dimension mapping and rerun unit/dimension critics.",
    "law_grounding": "Ground the affected transformation in a source-backed law, generated bridge, or SymPy rule.",
    "sympy_library_grounding": "Select an installed SymPy/dependency API surface for the affected role, or mark the local placeholder/projection as draft-only.",
    "sympy_api_grounding": "Ground the required role in installed SymPy/dependency APIs or mark the local support as draft-only.",
    "equation_parse": "Repair only the affected parsed equation node and preserve existing anchors.",
    "projection_bridge": "Add or repair the scalar projection bridge connecting components to the physical claim.",
    "transformation_step": "Repair the failing symbolic transformation certificate or local derivation step.",
    "numeric_domain": "Tighten numeric sample domains using explicit side conditions.",
    "frame_regime": "Add the missing coordinate-frame, sign-convention, or regime assumption locally.",
    "target_nonleakage": "Remove target-shaped input equations, laws, or hidden expected-answer shortcuts.",
    "trace_realness": "Replace placeholders and missing reports with executable trace evidence.",
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


def rel(path: Path) -> str:
    """Return a repository-relative display path when possible."""
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def normalize_case(case: str | None, sympy_file: Path | None = None) -> str:
    """Normalize a case id to formalphysics_####."""
    candidates = [case or "", "" if sympy_file is None else str(sympy_file)]
    for candidate in candidates:
        match = CASE_RE.search(candidate)
        if match:
            return f"formalphysics_{match.group(1)}"
    if case and case.isdigit():
        return f"formalphysics_{int(case):04d}"
    return "formalphysics_0000"


def case_path(case_id: str, sympy_file: Path | None) -> Path:
    """Resolve the SymPy artifact path for a case."""
    if sympy_file is not None:
        return sympy_file
    return SYMPY_ROOT / case_id / "MathformerPhysics.py"


def load_module(path: Path, case_id: str) -> tuple[Any | None, dict[str, Any]]:
    """Import one SymPy artifact as an isolated module."""
    try:
        spec = importlib.util.spec_from_file_location(f"physics_sympy_{case_id}", path)
        if spec is None or spec.loader is None:
            return None, {
                "status": "fail",
                "error": "missing import spec",
                "path": rel(path),
            }
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module, {"status": "pass", "path": rel(path)}
    except (
        Exception
    ) as exc:  # pragma: no cover - exact failures are environment-dependent.
        return None, {
            "status": "fail",
            "error": f"{type(exc).__name__}: {exc}",
            "path": rel(path),
        }


def report_passed(report: Any) -> bool:
    """Interpret common report pass fields without depending on one report schema."""
    if isinstance(report, bool):
        return report
    if not isinstance(report, dict):
        return False
    for key in ("passed", "ok", "symbolic_target_verified", "dimensionally_consistent"):
        if report.get(key) is True:
            return True
    status = str(report.get("status", "")).lower()
    if status in PASS_STATUSES:
        return True
    if "counterexamples" in report and report.get("counterexamples") == []:
        return True
    return False


def design_finding(
    *,
    code: str,
    severity: str,
    message: str,
    repair_surface: str,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a design-guard finding routed to one local repair surface."""
    return {
        "code": code,
        "severity": severity,
        "message": message,
        "repair_surface": repair_surface,
        "evidence": evidence or {},
    }


def append_router_event(
    reasoning_log: Path | None, report: dict[str, Any], output_path: Path | None
) -> None:
    """Append a concise consumer-ready reasoning-log event when requested."""
    if reasoning_log is None or append_reasoning_log_entry is None:
        return
    style = str(report.get("style", "physics_sympy_review_refinement_plan"))
    design_mode = style == "physics_sympy_design_guard_review"
    hook_id = (
        "physics.sympy.design_guard.review"
        if design_mode
        else "refine.physics_sympy_review"
    )
    step = (
        "physics_sympy_design_guard_review_complete"
        if design_mode
        else "physics_sympy_review_refinement_plan_complete"
    )
    case_id = str(report.get("case_id", "unspecified"))
    append_reasoning_log_entry(
        reasoning_log,
        step=step,
        payload={
            "skill": "physics-sympy-review-refinement-router",
            "hook_id": hook_id,
            "goal_id": f"sympy:{case_id}:recursive_goal",
            "case_id": case_id,
            "stage": step,
            "status": report.get("status"),
            "evidence": {
                "finding_count": len(report.get("findings", [])),
                "high_severity_finding_count": report.get(
                    "high_severity_finding_count"
                ),
                "repair_surfaces": report.get("repair_surfaces", []),
            },
            "artifacts": {"output": None if output_path is None else rel(output_path)},
            "decision": {
                "mode": "design_guard_review" if design_mode else "review_refinement",
                "status": report.get("status"),
            },
            "risks": report.get("findings", []),
            "next_action": report.get("next_action", "rerun affected local gates"),
        },
    )


def collect_surfaces(reports: Sequence[dict[str, Any]]) -> list[str]:
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
    for report in reports:
        for surface in report.get("repair_surfaces", []):
            surfaces.add(str(surface))
        handoff = report.get("refinement_handoff", {})
        for surface in handoff.get("repair_surfaces", []):
            surfaces.add(str(surface))
        for finding in report.get("findings", []) or report.get("diagnostics", []):
            if isinstance(finding, dict) and finding.get("repair_surface"):
                surfaces.add(str(finding["repair_surface"]))
    return sorted(surfaces)


def initialize_design_guard_review(
    path: Path, reasoning_log: Path | None
) -> tuple[dict[str, Any], bool]:
    """Capture initial evidence, then evaluate the native path-existence guard."""
    findings: list[dict[str, Any]] = []
    evidence: dict[str, Any] = {
        "artifact_path": rel(path),
        "artifact_exists": path.exists(),
        "reasoning_log": None if reasoning_log is None else rel(reasoning_log),
    }

    return {"findings": findings, "evidence": evidence}, path.exists()


def missing_design_guard_artifact(path: Path, state: dict[str, Any]) -> dict[str, Any]:
    """Accumulate the native missing-artifact finding."""
    findings, _evidence = state["findings"], state["evidence"]
    findings.append(
        design_finding(
            code="artifact_missing",
            severity="high",
            message=f"SymPy artifact does not exist: {rel(path)}",
            repair_surface="trace_realness",
        )
    )
    return state


def read_design_guard_artifact(
    case_id: str, path: Path, state: dict[str, Any]
) -> tuple[dict[str, Any], Any | None]:
    """Read commentary before importing exactly once; retain native module locals."""
    findings, evidence = state["findings"], state["evidence"]
    text = path.read_text(encoding="utf-8")
    evidence["source_commentary_markers"] = {
        marker: marker in text for marker in COMMENTARY_MARKERS
    }
    for marker, present in evidence["source_commentary_markers"].items():
        if not present:
            findings.append(
                design_finding(
                    code="missing_source_commentary_marker",
                    severity="high",
                    message=f"Artifact is missing commentary marker: {marker}",
                    repair_surface="source_anchor",
                )
            )

    module, import_report = load_module(path, case_id)
    evidence["import"] = import_report
    return state, None if module is None else {"text": text, "module": module}


def failed_design_guard_import(state: dict[str, Any]) -> dict[str, Any]:
    """Record failed import evidence without inspecting the module."""
    findings, evidence = state["findings"], state["evidence"]
    import_report = evidence["import"]
    findings.append(
        design_finding(
            code="artifact_import_failed",
            severity="high",
            message="Artifact cannot be imported, so design-guard checks cannot inspect real surfaces.",
            repair_surface="trace_realness",
            evidence=import_report,
        )
    )
    return state


def inspect_design_guard_module(
    state: dict[str, Any], artifact: dict[str, Any]
) -> dict[str, Any]:
    """Inspect source-owned surfaces and callbacks in their original order."""
    findings, evidence = state["findings"], state["evidence"]
    text, module = artifact["text"], artifact["module"]
    claim = getattr(module, "CLAIM", {})
    commentary_header = (
        str(claim.get("commentary_header", "")) if isinstance(claim, dict) else ""
    )
    evidence["claim_has_commentary_header"] = bool(commentary_header)
    if not commentary_header or any(
        marker not in commentary_header for marker in COMMENTARY_MARKERS
    ):
        findings.append(
            design_finding(
                code="stale_or_missing_structured_commentary",
                severity="high",
                message="CLAIM.commentary_header does not carry the full source commentary and SymPy alignment.",
                repair_surface="source_anchor",
            )
        )

    target_report = (
        module.validate_no_hidden_target()
        if hasattr(module, "validate_no_hidden_target")
        else {"passed": False, "reason": "missing validate_no_hidden_target"}
    )
    evidence["target_nonleakage"] = target_report
    if not report_passed(target_report):
        findings.append(
            design_finding(
                code="target_nonleakage_not_proven",
                severity="high",
                message="Target nonleakage evidence is missing or failing.",
                repair_surface="target_nonleakage",
                evidence={"report": target_report},
            )
        )

    assumption_context = getattr(module, "ASSUMPTION_CONTEXT", {})
    context_assumptions = (
        assumption_context.get("CONTEXT_ASSUMPTIONS", [])
        if isinstance(assumption_context, dict)
        else []
    )
    evidence["assumption_count"] = len(context_assumptions)
    assumption_text = " ".join(
        str(item.get("text", ""))
        for item in context_assumptions
        if isinstance(item, dict)
    ).lower()
    if not context_assumptions:
        findings.append(
            design_finding(
                code="assumption_provenance_missing",
                severity="high",
                message="No structured assumption provenance is available.",
                repair_surface="assumption_context",
            )
        )
    for item in context_assumptions:
        if not isinstance(item, dict):
            continue
        support = str(item.get("support", ""))
        has_anchor = bool(item.get("source_anchor") or item.get("source_anchors"))
        if support not in ASSUMPTION_SUPPORT_LABELS:
            findings.append(
                design_finding(
                    code="assumption_support_label_missing",
                    severity="high",
                    message="Assumption lacks a source-backed/generated-support/API-backed/blocker support label.",
                    repair_surface="assumption_context",
                    evidence={"assumption": item},
                )
            )
        if support == "source_backed" and not has_anchor:
            findings.append(
                design_finding(
                    code="assumption_source_anchor_missing",
                    severity="high",
                    message="Source-backed assumption lacks a source anchor.",
                    repair_surface="assumption_context",
                    evidence={"assumption": item},
                )
            )
        if support == "generated_support" and not any(
            item.get(key)
            for key in (
                "generated_from",
                "rationale",
                "justification",
                "source_anchor",
                "source_anchors",
            )
        ):
            findings.append(
                design_finding(
                    code="silent_assumption_strengthening",
                    severity="high",
                    message="Generated-support assumption lacks a generated-from/rationale/justification field.",
                    repair_surface="assumption_context",
                    evidence={"assumption": item},
                )
            )

    equation_surface = getattr(module, "EQUATION_SURFACE", {})
    equation_graph = (
        equation_surface.get("EQUATION_GRAPH", {})
        if isinstance(equation_surface, dict)
        else {}
    )
    frame_context = (
        equation_graph.get("frame_context", {})
        if isinstance(equation_graph, dict)
        else {}
    )
    evidence["frame_context_present"] = bool(frame_context)
    if (
        "component" in text.lower()
        and not frame_context
        and "frame" not in assumption_text
        and "coordinate" not in assumption_text
    ):
        findings.append(
            design_finding(
                code="missing_frame_or_regime_context",
                severity="high",
                message="Component-level derivation lacks explicit frame, coordinate, or regime context.",
                repair_surface="frame_regime",
            )
        )

    projection_bridges = getattr(module, "PROJECTION_BRIDGES", [])
    evidence["projection_bridge_count"] = (
        len(projection_bridges) if isinstance(projection_bridges, list) else 0
    )
    if not isinstance(projection_bridges, list) or not projection_bridges:
        findings.append(
            design_finding(
                code="projection_bridge_missing",
                severity="high",
                message="No scalar/vector/field projection bridge is exposed.",
                repair_surface="projection_bridge",
            )
        )
    else:
        for bridge in projection_bridges:
            status = str(bridge.get("status", "")) if isinstance(bridge, dict) else ""
            if status not in PROJECTION_PASS_STATUSES:
                findings.append(
                    design_finding(
                        code="projection_bridge_status_not_ready",
                        severity="high",
                        message="Projection bridge status is not provided/pass/ready/required.",
                        repair_surface="projection_bridge",
                        evidence={"bridge": bridge},
                    )
                )

    derivation_steps = getattr(module, "DERIVATION_STEPS", [])
    evidence["derivation_step_count"] = (
        len(derivation_steps) if isinstance(derivation_steps, list) else 0
    )
    if not isinstance(derivation_steps, list) or not derivation_steps:
        findings.append(
            design_finding(
                code="derivation_steps_missing",
                severity="high",
                message="No derivation steps are exposed for generated-support labeling.",
                repair_surface="transformation_step",
            )
        )
    else:
        for step in derivation_steps:
            if not isinstance(step, dict):
                continue
            has_generated_flag = "generated" in step
            has_support_label = bool(step.get("source") or step.get("support"))
            has_anchor = bool(step.get("source_anchors") or step.get("source_anchor"))
            if not has_generated_flag or not has_support_label:
                findings.append(
                    design_finding(
                        code="generated_support_label_missing",
                        severity="high",
                        message="Derivation step lacks generated/source support labeling.",
                        repair_surface="transformation_step",
                        evidence={"step": step},
                    )
                )
            if step.get("generated") is False and not has_anchor:
                findings.append(
                    design_finding(
                        code="source_step_anchor_missing",
                        severity="high",
                        message="Source-backed derivation step lacks source anchors.",
                        repair_surface="transformation_step",
                        evidence={"step": step},
                    )
                )

    grounding = getattr(module, "SYMPY_LIBRARY_GROUNDING", {})
    grounding_level = (
        str(grounding.get("grounding_level", "")) if isinstance(grounding, dict) else ""
    )
    evidence["sympy_library_grounding_level"] = grounding_level
    if grounding_level != "high":
        findings.append(
            design_finding(
                code="installed_library_grounding_not_high",
                severity="high",
                message="Installed SymPy/dependency grounding is missing or below high.",
                repair_surface="sympy_library_grounding",
                evidence={"grounding_level": grounding_level},
            )
        )

    if not hasattr(module, "validate_numeric_samples"):
        findings.append(
            design_finding(
                code="numeric_domain_not_exposed",
                severity="high",
                message="Artifact does not expose numeric-domain sanity evidence.",
                repair_surface="numeric_domain",
            )
        )
    else:
        try:
            numeric_report = module.validate_numeric_samples()
        except Exception as exc:  # pragma: no cover - exact artifact failures vary.
            numeric_report = {
                "passed": False,
                "error": f"{type(exc).__name__}: {exc}",
            }
        evidence["numeric_domain"] = {
            "passed": report_passed(numeric_report),
            "domain": (
                numeric_report.get("domain")
                if isinstance(numeric_report, dict)
                else None
            ),
        }
        if not report_passed(numeric_report) or not (
            isinstance(numeric_report, dict) and numeric_report.get("domain")
        ):
            findings.append(
                design_finding(
                    code="numeric_domain_hole",
                    severity="high",
                    message="Numeric sanity evidence is missing, failing, or lacks an explicit domain.",
                    repair_surface="numeric_domain",
                    evidence={"numeric_report": numeric_report},
                )
            )

    return state


def finish_design_guard_review(
    case_id: str, reasoning_log: Path | None, state: dict[str, Any]
) -> dict[str, Any]:
    """Inspect first log event and return recommendations without dispatching them."""
    findings, evidence = state["findings"], state["evidence"]
    if reasoning_log is None:
        findings.append(
            design_finding(
                code="reasoning_log_not_requested",
                severity="medium",
                message="No reasoning-log path was supplied, so consumer-ready log emission was not exercised.",
                repair_surface="consumer_reasoning_log",
            )
        )
    elif (
        not reasoning_log.exists()
        or not reasoning_log.read_text(encoding="utf-8").strip()
    ):
        findings.append(
            design_finding(
                code="reasoning_log_missing_or_empty",
                severity="high",
                message="Reasoning-log path was supplied but no parseable event evidence exists yet.",
                repair_surface="consumer_reasoning_log",
                evidence={"path": rel(reasoning_log)},
            )
        )
    else:
        first_line = reasoning_log.read_text(encoding="utf-8").splitlines()[0]
        try:
            parsed = json.loads(first_line)
            evidence["reasoning_log_first_event_step"] = parsed.get("step")
        except json.JSONDecodeError as exc:
            findings.append(
                design_finding(
                    code="reasoning_log_invalid_json",
                    severity="high",
                    message=f"Reasoning-log event is not JSON: {exc.msg}",
                    repair_surface="consumer_reasoning_log",
                    evidence={"path": rel(reasoning_log)},
                )
            )

    repair_surfaces = sorted({str(item["repair_surface"]) for item in findings})
    high_findings = [
        item for item in findings if item["severity"] in {"high", "critical"}
    ]
    return {
        "style": "physics_sympy_design_guard_review",
        "backend": "sympy",
        "case_id": case_id,
        "status": "fail" if high_findings else "pass",
        "high_severity_finding_count": len(high_findings),
        "repair_surfaces": repair_surfaces,
        "localized_actions": [
            {
                "repair_surface": surface,
                "action": SURFACE_ACTIONS.get(
                    surface, "Create the smallest local SymPy repair for this surface."
                ),
                "allowed_scope": "only the named commentary, evidence, grounding, projection, support-label, trace, or reasoning-log surface",
            }
            for surface in repair_surfaces
        ],
        "semantic_preservation_contract": {
            "source_commentary_required": True,
            "informal_to_sympy_alignment_required": True,
            "target_nonleakage_required": True,
            "assumption_provenance_required": True,
            "projection_bridge_required": True,
            "generated_support_label_required": True,
            "installed_library_grounding_minimum": "high",
            "consumer_reasoning_log_required_for_workflow_runs": True,
        },
        "evidence": evidence,
        "findings": findings,
        "next_action": (
            "run localized monotonic repairs and rerun affected SymPy gates"
            if high_findings
            else "continue recursive SymPy gate sequence"
        ),
    }


def build_design_guard_review(
    case_id: str, path: Path, reasoning_log: Path | None
) -> dict[str, Any]:
    """Review broader semantic-preservation debts through shared native steps."""
    state, present = initialize_design_guard_review(path, reasoning_log)
    if not present:
        state = missing_design_guard_artifact(path, state)
    else:
        state, artifact = read_design_guard_artifact(case_id, path, state)
        if artifact is None:
            state = failed_design_guard_import(state)
        else:
            state = inspect_design_guard_module(state, artifact)
    return finish_design_guard_review(case_id, reasoning_log, state)


def build_plan(
    reports: Sequence[dict[str, Any]], baseline_report: dict[str, Any]
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
    surfaces = collect_surfaces(reports)
    if not surfaces:
        surfaces = ["trace_realness"]
    blocking = any(str(report.get("status")) == "fail" for report in reports)
    return {
        "style": "physics_sympy_review_refinement_plan",
        "status": "ready" if blocking else "not_required",
        "localized_actions": [
            {
                "repair_surface": surface,
                "action": SURFACE_ACTIONS.get(
                    surface,
                    "Create the smallest source-anchored repair for the reviewer finding.",
                ),
                "allowed_scope": "only the equation node, assumption label, law link, projection bridge, transformation certificate, numeric domain, or trace fragment named by the finding",
            }
            for surface in surfaces
        ],
        "monotonicity_constraints": [
            "preserve every passing source anchor",
            "preserve already-correct equation nodes and transformation certificates",
            "do not weaken the target equation",
            "do not silently strengthen assumptions",
            "do not remove passing unit, dimension, projection, numeric, or review evidence",
            "do not reduce SymPy library grounding level or remove selected API evidence",
            "rerun every affected critic and final reviewer",
        ],
        "baseline_evidence": {
            "status": baseline_report.get("status", "missing"),
            "style": baseline_report.get("style", "missing"),
        },
        "rerun_gates": [
            "execute.physics_sympy_derivation",
            "physics.sympy.library_grounding.build",
            "execute.physics_sympy_interpret",
            "physics.units.verify",
            "physics.steps.verify",
            "physics.numeric.sample",
            "critique.physics_sympy_semantics",
            "critique.physics_sympy_dimensions",
            "review.physics_sympy_final_equations",
            "review.mathematical_sympy_final_equations",
        ],
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
    parser.add_argument(
        "--mode",
        choices=("review_refinement", "design_guard_review"),
        default="review_refinement",
    )
    parser.add_argument("--case")
    parser.add_argument("--sympy-file", type=Path)
    parser.add_argument("--review", action="append", type=Path, default=[])
    parser.add_argument("--baseline-report", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--reasoning-log", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true", help=argparse.SUPPRESS)
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
        if args.mode == "design_guard_review":
            case_id = "formalphysics_0000"
            plan = build_design_guard_review(
                case_id, case_path(case_id, None), args.reasoning_log
            )
            assert plan["style"] == "physics_sympy_design_guard_review"
            assert plan["status"] in {"pass", "fail"}
        else:
            plan = build_plan(
                [
                    {
                        "status": "fail",
                        "findings": [{"repair_surface": "sympy_library_grounding"}],
                    }
                ],
                {"status": "draft", "style": "baseline"},
            )
            assert plan["status"] == "ready"
            assert (
                plan["localized_actions"][0]["repair_surface"]
                == "sympy_library_grounding"
            )
    else:
        if args.mode == "design_guard_review":
            case_id = normalize_case(args.case, args.sympy_file)
            plan = build_design_guard_review(
                case_id, case_path(case_id, args.sympy_file), args.reasoning_log
            )
        else:
            plan = build_plan(
                [load_json(path) for path in args.review],
                load_json(args.baseline_report),
            )
    output = json.dumps(plan, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    append_router_event(args.reasoning_log, plan, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
