#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.
#
# Intent:
#   Encode regression checks that catch parser breakage, semantic drift, and missing workflow evidence.
#
# Function:
#   Renders and validates Phase 17 human-readable physics derivation reports.
#
# Maintenance Notes:
#   Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.

"""Validate Phase 17 human-readable physics reports."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backends.sympy.MathformerPhysicsSympy.pipeline import (  # noqa: E402 - direct-script path setup above
    consistency_report,
    now,
    physics_human_report_model,
    write_artifact,
    write_core_reasoning_refinement_loop,
    write_equational_derivation,
    write_equational_derivation_html,
    write_html,
    write_markdown,
)

CASES = ["rc_discharge", "formalphysics_0000"]


REQUIRED_MARKDOWN_SECTIONS = [
    "## Side-By-Side Derivation Evidence",
    "## Derivation Graph",
    "### Source Equation Nodes",
    "### Generated Support Nodes",
    "### Law/API/Rule Edges",
    "### Blocker Nodes",
    "### Target Derivation Path",
    "## Unit-Flow Diagram",
    "## RFDE Trajectory",
]


REQUIRED_HTML_MARKERS = [
    "Side-By-Side Derivation Evidence",
    "Derivation Graph",
    "Source Equation Nodes",
    "Generated Support Nodes",
    "Law/API/Rule Edges",
    "Blocker Nodes",
    "Target Derivation Path",
    "Unit-Flow Diagram",
    "RFDE Trajectory",
    "Gap Closure",
    "Dimensional Consistency",
    "Executable Step Count",
    "Target-Derivation Residual",
    "<svg",
]


REQUIRED_EQUATIONAL_SECTIONS = [
    "# SymPy Equational Derivation",
    "## Claim",
    "## Original Informal Proof",
    "## Assumptions And Regime",
    "## Physical Definitions And Laws",
    "## Equation Chain",
    "## Expanded Equations",
    "## Target Residual",
    "## Validation Summary",
]


REQUIRED_EQUATIONAL_HTML_MARKERS = [
    "MathJax",
    "tex-svg.js",
    "--sympy-green",
    "--sympy-blue",
    "--sympy-gold",
    "math-card",
    "informal-proof",
    "Original informal proof",
    "\\[",
]


def import_module_from_path(path: Path) -> Any:
    """Import a generated Python module from a filesystem path."""
    spec = importlib.util.spec_from_file_location(
        "generated_core_sympy_reasoning", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import generated module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["generated_core_sympy_reasoning"] = module
    spec.loader.exec_module(module)
    return module


def validate_rendered_case(case_id: str, output_root: Path) -> Dict[str, Any]:
    """Render and validate one Phase 17 report case."""
    case_root = output_root / case_id
    artifact_path = (
        case_root
        / f"Autoformalized{''.join(part.title() for part in case_id.split('_'))}.py"
    )
    write_artifact(case_id, artifact_path)
    report = consistency_report(case_id, artifact_path=artifact_path)
    model = physics_human_report_model(report)
    markdown_path = case_root / "human_derivation_report.md"
    html_path = case_root / "human_derivation_report.html"
    equational_path = case_root / "equational_derivation.md"
    equational_html_path = case_root / "equational_derivation.html"
    core_reasoning_path = case_root / "core_equational_reasoning.py"
    core_refinement_report_path = case_root / "core_reasoning_refinement_loop.json"
    json_path = case_root / "human_derivation_report.model.json"
    write_markdown(report, markdown_path)
    write_html(report, html_path)
    write_equational_derivation(case_id, equational_path)
    write_equational_derivation_html(equational_path, equational_html_path)
    case_root.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(model, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    markdown = markdown_path.read_text(encoding="utf-8")
    html = html_path.read_text(encoding="utf-8")
    equational = equational_path.read_text(encoding="utf-8")
    equational_html = equational_html_path.read_text(encoding="utf-8")
    findings: List[str] = []
    for section in REQUIRED_MARKDOWN_SECTIONS:
        if section not in markdown:
            findings.append(f"missing Markdown section {section}")
    for marker in REQUIRED_HTML_MARKERS:
        if marker not in html:
            findings.append(f"missing HTML marker {marker}")
    for section in REQUIRED_EQUATIONAL_SECTIONS:
        if section not in equational:
            findings.append(f"missing equational derivation section {section}")
    if "Informal derivation commentary" in equational:
        findings.append(
            "equational derivation leaked the commentary heading instead of rendering the proof"
        )
    if "simplify(target_expression - expected_expression) = 0" not in equational:
        findings.append("equational derivation does not expose a zero target residual")
    for marker in REQUIRED_EQUATIONAL_HTML_MARKERS:
        if marker not in equational_html:
            findings.append(f"missing equational HTML marker {marker}")
    core_reasoning_report = None
    if case_id == "formalphysics_0000":
        loop_report = write_core_reasoning_refinement_loop(
            case_id, core_reasoning_path, core_refinement_report_path
        )
        core_module = import_module_from_path(core_reasoning_path)
        core_result = core_module.run_core_reasoning()
        core_reasoning_report = {
            "path": str(core_reasoning_path.relative_to(REPO_ROOT)),
            "refinement_report_path": str(
                core_refinement_report_path.relative_to(REPO_ROOT)
            ),
            "refinement_loop_ok": bool(loop_report["ok"]),
            "refinement_cycle_count": loop_report["cycle_count"],
            "passed": bool(core_result["passed"]),
            "trace_length": len(core_result["trace"]),
            "failed_steps": [
                step["step_id"] for step in core_result["trace"] if not step["passed"]
            ],
        }
        if not loop_report["ok"]:
            findings.append(
                "core executable reasoning reflective refinement loop failed"
            )
        if loop_report["cycle_count"] < 2:
            findings.append(
                "core executable reasoning refinement loop did not run at least two cycles"
            )
        if not core_result["passed"]:
            findings.append(
                f"core executable reasoning failed: {core_reasoning_report['failed_steps']}"
            )
        if len(core_result["trace"]) != 6:
            findings.append(
                f"core executable reasoning expected 6 steps, got {len(core_result['trace'])}"
            )
        if not all(
            callable(getattr(core_module, name, None))
            for name in [
                "step_01_source_euler_lagrange_x",
                "step_02_solve_for_force",
                "step_03_group_field_combinations",
                "step_04_introduce_electric_field",
                "step_05_introduce_magnetic_field_and_expand",
                "step_06_final_target_residual",
            ]
        ):
            findings.append(
                "core executable reasoning did not expose all named inference step functions"
            )
    if not model["side_by_side_rows"]:
        findings.append("side-by-side evidence rows were empty")
    if not model["graph_edges"]:
        findings.append("derivation graph edges were empty")
    if not model["unit_flow_rows"]:
        findings.append("unit-flow rows were empty")
    if len(model["trajectory"]) < 6:
        findings.append("RFDE trajectory had too few cycles")
    if set(model["rfde_plots"].keys()) != {
        "gap_closure",
        "dimension_consistency",
        "executable_step_count",
        "target_residual",
    }:
        findings.append("RFDE plots did not cover all required metrics")
    return {
        "case_id": case_id,
        "ok": not findings,
        "findings": findings,
        "markdown_path": str(markdown_path.relative_to(REPO_ROOT)),
        "html_path": str(html_path.relative_to(REPO_ROOT)),
        "equational_path": str(equational_path.relative_to(REPO_ROOT)),
        "equational_html_path": str(equational_html_path.relative_to(REPO_ROOT)),
        "core_reasoning_path": (
            str(core_reasoning_path.relative_to(REPO_ROOT))
            if core_reasoning_report
            else None
        ),
        "core_reasoning": core_reasoning_report,
        "model_path": str(json_path.relative_to(REPO_ROOT)),
        "side_by_side_rows": len(model["side_by_side_rows"]),
        "graph_edges": len(model["graph_edges"]),
        "unit_flow_rows": len(model["unit_flow_rows"]),
        "trajectory_cycles": len(model["trajectory"]),
    }


def run_check(output_root: Path) -> Dict[str, Any]:
    """Run Phase 17 report rendering checks."""
    output_root.mkdir(parents=True, exist_ok=True)
    cases = [validate_rendered_case(case_id, output_root) for case_id in CASES]
    findings = [
        f"{case['case_id']}: {finding}"
        for case in cases
        for finding in case["findings"]
    ]
    report = {
        "ok": not findings,
        "backend": "sympy",
        "style": "sympy_physics_derivation_trace",
        "phase": "phase17_documentation_human_readable_derivation_reports",
        "generated_at": now(),
        "case_count": len(cases),
        "cases": cases,
        "findings": findings,
    }
    report_path = output_root / "phase17_report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    report["report_path"] = str(report_path.relative_to(REPO_ROOT))
    return report


def main() -> int:
    """Serve as the command-line entry point for Phase 17 report validation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("artifacts/physics_sympy/phase17_human_reports"),
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = run_check((REPO_ROOT / args.output_root).resolve())
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    else:
        print(f"ok: {report['ok']}")
        print(f"case_count: {report['case_count']}")
        print(f"report: {report['report_path']}")
    return 0 if report["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
