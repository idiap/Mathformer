#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Gate one FormalPhysics SymPy artifact for grounded derivation thoroughness."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
SYMPY_ROOT = REPO_ROOT / "MathformerPhysicsLib" / "SymPy"
CASE_RE = re.compile(r"formalphysics_(\d{4})")
DESIGN_GUARD = (
    REPO_ROOT
    / "skills"
    / "physics-sympy"
    / "physics-sympy-review-refinement-router"
    / "scripts"
    / "plan_physics_sympy_review_refinement.py"
)
REASONING_LOG_SCRIPTS = (
    REPO_ROOT / "skills" / "control" / "reasoning-log-schema-guardian" / "scripts"
)
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REASONING_LOG_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(REASONING_LOG_SCRIPTS))
try:
    from reasoning_log import append_reasoning_log_entry
except Exception:  # pragma: no cover - logging is optional for callers.
    append_reasoning_log_entry = None

COMMENTARY_MARKERS = [
    "Original informal statement",
    "Informal derivation commentary",
    "SymPy alignment",
]
PASS_STATUSES = {"pass", "passed", "ready", "complete", "ok"}


def rel(path: Path) -> str:
    """Return a repository-relative path when possible."""
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def normalize_case(case: str | None, sympy_file: Path | None) -> str:
    """Normalize a case id to formalphysics_####."""
    for candidate in (case or "", "" if sympy_file is None else str(sympy_file)):
        match = CASE_RE.search(candidate)
        if match:
            return f"formalphysics_{match.group(1)}"
    if case and case.isdigit():
        return f"formalphysics_{int(case):04d}"
    return "formalphysics_0000"


def case_path(case_id: str, sympy_file: Path | None) -> Path:
    """Resolve the artifact path for one SymPy case."""
    if sympy_file is not None:
        return sympy_file
    return SYMPY_ROOT / case_id / "MathformerPhysics.py"


def load_module(path: Path, case_id: str) -> tuple[Any | None, dict[str, Any]]:
    """Import one generated SymPy artifact."""
    try:
        spec = importlib.util.spec_from_file_location(f"grounded_{case_id}", path)
        if spec is None or spec.loader is None:
            return None, {"status": "fail", "error": "missing import spec"}
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module, {"status": "pass", "path": rel(path)}
    except Exception as exc:  # pragma: no cover - depends on artifact failures.
        return None, {
            "status": "fail",
            "error": f"{type(exc).__name__}: {exc}",
            "path": rel(path),
        }


def report_passed(report: Any) -> bool:
    """Interpret common report pass shapes."""
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
    if report.get("counterexamples") == []:
        return True
    return False


def compact_report(report: Any) -> Any:
    """Keep gate output concise while preserving the decisive evidence."""
    if not isinstance(report, dict):
        return report
    summary: dict[str, Any] = {}
    for key in (
        "style",
        "status",
        "passed",
        "ok",
        "symbolic_target_verified",
        "dimensionally_consistent",
        "grounding_level",
        "step_count",
        "target_dimension",
        "expected_dimension",
        "target_value",
        "expected_value",
    ):
        if key in report:
            summary[key] = report[key]
    for key in ("findings", "counterexamples", "completion_blockers"):
        value = report.get(key)
        if isinstance(value, list):
            summary[f"{key}_count"] = len(value)
    if "grounding" in report and isinstance(report["grounding"], dict):
        summary["grounding_level"] = report["grounding"].get("grounding_level")
    if "final_equation_reviews" in report and isinstance(
        report["final_equation_reviews"], dict
    ):
        summary["final_review_statuses"] = {
            name: item.get("status")
            for name, item in report["final_equation_reviews"].items()
            if isinstance(item, dict)
        }
    return summary or {"keys": sorted(report.keys())[:20]}


def compact_final_reviews(report: Any) -> Any:
    """Summarize final review subreports."""
    if not isinstance(report, dict):
        return report
    return {
        name: {
            "style": item.get("style"),
            "status": item.get("status"),
            "finding_count": (
                len(item.get("findings", []))
                if isinstance(item.get("findings", []), list)
                else None
            ),
            "repair_surfaces": item.get("repair_surfaces", []),
        }
        for name, item in report.items()
        if isinstance(item, dict)
    }


def safe_call(module: Any, name: str) -> tuple[bool, Any]:
    """Call a module validator and keep failures structured."""
    if not hasattr(module, name):
        return False, {"error": f"missing {name}"}
    try:
        report = getattr(module, name)()
        return report_passed(report), report
    except Exception as exc:  # pragma: no cover - exact artifact failures vary.
        return False, {"error": f"{type(exc).__name__}: {exc}"}


def run_design_guard(
    case_id: str, path: Path, reasoning_log: Path | None
) -> dict[str, Any]:
    """Run the design guard through its public CLI."""
    command = [
        sys.executable,
        str(DESIGN_GUARD),
        "--mode",
        "design_guard_review",
        "--case",
        case_id,
        "--sympy-file",
        str(path),
        "--json",
    ]
    if reasoning_log is not None:
        command.extend(["--reasoning-log", str(reasoning_log)])
    completed = subprocess.run(
        command, cwd=REPO_ROOT, check=True, text=True, capture_output=True
    )
    return json.loads(completed.stdout)


def final_reviews_passed(report: Any) -> bool:
    """Return true when every final review subreport passes."""
    if not isinstance(report, dict) or not report:
        return False
    subreports = [value for value in report.values() if isinstance(value, dict)]
    return bool(subreports) and all(report_passed(item) for item in subreports)


def initialize_gate(
    case_id: str, path: Path, reasoning_log: Path | None
) -> dict[str, Any]:
    """Import once and preserve the module and all source-local evidence."""
    findings: list[dict[str, Any]] = []
    checks: dict[str, dict[str, Any]] = {}
    module, import_report = load_module(path, case_id)
    checks["compiled_or_executed"] = {
        "passed": module is not None,
        "evidence": import_report,
    }
    design_guard = {
        "status": "blocked",
        "findings": [{"severity": "high", "code": "not_run"}],
    }

    return dict(
        case_id=case_id,
        path=path,
        reasoning_log=reasoning_log,
        module=module,
        checks=checks,
        findings=findings,
        design_guard=design_guard,
    )


def inspect_gate(state: dict[str, Any]) -> dict[str, Any]:
    """Collect source/depth/grounding checks and the ordered native validations."""
    module, path, checks = state["module"], state["path"], state["checks"]
    text = path.read_text(encoding="utf-8")
    claim = getattr(module, "CLAIM", {})
    commentary_header = (
        str(claim.get("commentary_header", "")) if isinstance(claim, dict) else ""
    )
    source_commentary = all(
        marker in text and marker in commentary_header for marker in COMMENTARY_MARKERS
    )
    checks["source_commentary"] = {
        "passed": source_commentary,
        "evidence": {
            marker: marker in text and marker in commentary_header
            for marker in COMMENTARY_MARKERS
        },
    }

    equation_surface = getattr(module, "EQUATION_SURFACE", {})
    graph_nodes = (
        equation_surface.get("EQUATION_GRAPH", {}).get("nodes", [])
        if isinstance(equation_surface, dict)
        else []
    )
    derivation_steps = getattr(module, "DERIVATION_STEPS", [])
    checks["equation_surface_depth"] = {
        "passed": isinstance(graph_nodes, list)
        and len(graph_nodes) >= 2
        and isinstance(derivation_steps, list)
        and len(derivation_steps) >= 2,
        "evidence": {
            "equation_node_count": len(graph_nodes),
            "derivation_step_count": len(derivation_steps),
        },
    }

    grounding = getattr(module, "SYMPY_LIBRARY_GROUNDING", {})
    checks["library_grounding_high"] = {
        "passed": isinstance(grounding, dict)
        and grounding.get("grounding_level") == "high",
        "evidence": {
            "grounding_level": (
                grounding.get("grounding_level")
                if isinstance(grounding, dict)
                else None
            )
        },
    }

    unit_ok, unit_report = safe_call(module, "validate_dimensions")
    numeric_ok, numeric_report = safe_call(module, "validate_numeric_samples")
    steps_ok, steps_report = safe_call(module, "validate_derivation_steps")
    target_ok, target_report = safe_call(module, "validate_no_hidden_target")
    final_ok = (
        final_reviews_passed(module.review_final_equations())
        if hasattr(module, "review_final_equations")
        else False
    )
    run_all_ok, run_all_report = safe_call(module, "run_all")
    state["validation"] = {
        "unit_ok": unit_ok,
        "unit_report": unit_report,
        "numeric_ok": numeric_ok,
        "numeric_report": numeric_report,
        "steps_ok": steps_ok,
        "steps_report": steps_report,
        "target_ok": target_ok,
        "target_report": target_report,
        "final_ok": final_ok,
        "run_all_ok": run_all_ok,
        "run_all_report": run_all_report,
    }
    return state


def design_and_review_gate(state: dict[str, Any]) -> dict[str, Any]:
    """Run the public design CLI, then review final equations a second time."""
    case_id, path, reasoning_log = (
        state["case_id"],
        state["path"],
        state["reasoning_log"],
    )
    module, checks = state["module"], state["checks"]
    unit_ok = state["validation"]["unit_ok"]
    unit_report = state["validation"]["unit_report"]
    numeric_ok = state["validation"]["numeric_ok"]
    numeric_report = state["validation"]["numeric_report"]
    steps_ok = state["validation"]["steps_ok"]
    steps_report = state["validation"]["steps_report"]
    target_ok = state["validation"]["target_ok"]
    target_report = state["validation"]["target_report"]
    final_ok = state["validation"]["final_ok"]
    run_all_ok = state["validation"]["run_all_ok"]
    run_all_report = state["validation"]["run_all_report"]
    design_guard = run_design_guard(case_id, path, reasoning_log)
    high_design = [
        item
        for item in design_guard.get("findings", [])
        if item.get("severity") in {"high", "critical"}
    ]
    final_report = (
        module.review_final_equations()
        if hasattr(module, "review_final_equations")
        else {}
    )
    checks["unit_dimension"] = {
        "passed": unit_ok,
        "evidence": compact_report(unit_report),
    }
    checks["numeric_sanity"] = {
        "passed": numeric_ok,
        "evidence": compact_report(numeric_report),
    }
    checks["final_reviews"] = {
        "passed": final_ok,
        "evidence": compact_final_reviews(final_report),
    }
    checks["target_nonleakage"] = {
        "passed": target_ok,
        "evidence": compact_report(target_report),
    }
    checks["trace_realness"] = {
        "passed": run_all_ok and steps_ok,
        "evidence": {
            "run_all": compact_report(run_all_report),
            "step_report": compact_report(steps_report),
        },
    }
    checks["design_guard"] = {
        "passed": design_guard.get("status") == "pass" or not high_design,
        "evidence": {
            "status": design_guard.get("status"),
            "high_severity_finding_count": len(high_design),
            "medium_or_low_finding_count": len(design_guard.get("findings", []))
            - len(high_design),
        },
    }

    state.update(design_guard=design_guard, high_design=high_design)
    return state


def classify_gate(state: dict[str, Any]) -> dict[str, Any]:
    """Classify the accumulated evidence without executing repairs."""
    checks, findings, high_design = (
        state["checks"],
        state["findings"],
        state["high_design"],
    )
    failed = [name for name, item in checks.items() if not item.get("passed")]
    if not failed:
        status = "complete_sympy_physics_derivation"
    elif (
        checks["compiled_or_executed"]["passed"]
        and checks["source_commentary"]["passed"]
        and checks["equation_surface_depth"]["passed"]
    ):
        status = "derivation_partial"
    elif checks["compiled_or_executed"]["passed"]:
        status = "grounded_scaffold"
    else:
        status = "compiled_or_executed"
    if high_design or any(
        name in failed
        for name in (
            "compiled_or_executed",
            "source_commentary",
            "target_nonleakage",
        )
    ):
        status = (
            "blocked"
            if high_design or not checks["compiled_or_executed"]["passed"]
            else status
        )
    findings.extend(
        {
            "severity": "high",
            "code": f"{name}_failed",
            "repair_surface": (
                "trace_realness"
                if name in {"compiled_or_executed", "trace_realness"}
                else name
            ),
        }
        for name in failed
    )
    return gate_report(state, status)


def blocked_gate_report(state: dict[str, Any]) -> dict[str, Any]:
    """Stop immediately after failed import, skipping every validator."""
    findings = state["findings"]
    status = "blocked"
    findings.append(
        {
            "severity": "high",
            "code": "artifact_import_failed",
            "repair_surface": "trace_realness",
        }
    )
    return gate_report(state, status)


def gate_report(state: dict[str, Any], status: str) -> dict[str, Any]:
    """Pack the native report for either import branch."""
    case_id, path = state["case_id"], state["path"]
    checks, findings, design_guard = (
        state["checks"],
        state["findings"],
        state["design_guard"],
    )
    return {
        "style": "physics_sympy_grounded_sample_thoroughness",
        "backend": "sympy",
        "case_id": case_id,
        "status": status,
        "artifact_path": rel(path),
        "checks": checks,
        "design_guard_summary": {
            "status": design_guard.get("status"),
            "high_severity_finding_count": len(
                [
                    item
                    for item in design_guard.get("findings", [])
                    if item.get("severity") in {"high", "critical"}
                ]
            ),
        },
        "findings": findings,
        "status_scale": [
            "compiled_or_executed",
            "grounded_scaffold",
            "derivation_partial",
            "complete_sympy_physics_derivation",
            "blocked",
        ],
    }


def build_report(
    case_id: str, path: Path, reasoning_log: Path | None
) -> dict[str, Any]:
    """Build the report through the same source steps exposed over MCP."""
    state = initialize_gate(case_id, path, reasoning_log)
    if state["module"] is None:
        return blocked_gate_report(state)
    return classify_gate(design_and_review_gate(inspect_gate(state)))


def append_gate_event(
    reasoning_log: Path | None, report: dict[str, Any], output_path: Path | None
) -> None:
    """Append a grounded-thoroughness reasoning-log event when requested."""
    if reasoning_log is None or append_reasoning_log_entry is None:
        return
    case_id = str(report.get("case_id", "unspecified"))
    append_reasoning_log_entry(
        reasoning_log,
        step="physics_sympy_grounded_sample_thoroughness_complete",
        payload={
            "skill": "physics-sympy-goal-sample-autoformalizer",
            "hook_id": "physics.sympy.grounded_sample.thoroughness",
            "goal_id": f"sympy:{case_id}:recursive_goal",
            "case_id": case_id,
            "stage": "physics_sympy_grounded_sample_thoroughness_complete",
            "status": report.get("status"),
            "evidence": {
                "checks": {
                    name: item.get("passed")
                    for name, item in report.get("checks", {}).items()
                },
                "design_guard_summary": report.get("design_guard_summary"),
            },
            "artifacts": {"output": None if output_path is None else rel(output_path)},
            "decision": {"status": report.get("status")},
            "risks": report.get("findings", []),
            "next_action": "complete or recurse through local SymPy repair surfaces",
        },
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", default="formalphysics_0000")
    parser.add_argument("--sympy-file", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--reasoning-log", type=Path)
    parser.add_argument("--json", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the grounded sample thoroughness gate."""
    args = parse_args(argv)
    case_id = normalize_case(args.case, args.sympy_file)
    report = build_report(
        case_id, case_path(case_id, args.sympy_file), args.reasoning_log
    )
    return emit_gate_report(report, args.output, args.reasoning_log)


def emit_gate_report(
    report: dict[str, Any],
    output_path: Path | None,
    reasoning_log: Path | None,
    *,
    authorize_log=None,
) -> int:
    """Emit JSON before appending the optional source-owned log event."""
    output = json.dumps(report, ensure_ascii=False, indent=2, default=str)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    if reasoning_log is not None and authorize_log is not None:
        authorize_log(reasoning_log)
    append_gate_event(reasoning_log, report, output_path)
    return 0 if report["status"] != "blocked" else 3


if __name__ == "__main__":
    raise SystemExit(main())
