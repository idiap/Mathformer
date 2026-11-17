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
#   Runs the Phase 18 release criteria gate for the first Physics SymPy slice.
#
# Maintenance Notes:
#   Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.

"""Validate Phase 18 release criteria for the first physics slice."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict, List, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backends.sympy.MathformerPhysicsSympy.pipeline import (  # noqa: E402
    adversarial_suite,
    all_case_ids,
    build_physics_step_execution_packet,
    build_physics_unit_analysis_packet,
    consistency_report,
    controlled_case_ids,
    controlled_suite,
    now,
    physics_sympy_dependency_probe,
    write_artifact,
)


def run_json_command(command: Sequence[str], timeout: int = 240) -> Dict[str, Any]:
    """Run a JSON-emitting command and return its parsed result."""
    result = subprocess.run(
        list(command),
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )
    parsed: Dict[str, Any]
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError:
        parsed = {}
    return {
        "ok": result.returncode == 0 and bool(parsed.get("ok", result.returncode == 0)),
        "returncode": result.returncode,
        "stdout_json": parsed,
        "stderr": result.stderr,
    }


def release_check(check_id: str, ok: bool, details: Dict[str, Any]) -> Dict[str, Any]:
    """Create one release-criteria check record."""
    return {"id": check_id, "ok": ok, "details": details}


def check_physics_skill_agent_surfaces() -> Dict[str, Any]:
    """Check every physics skill has both skill instructions and agent metadata."""
    skill_dirs = sorted(
        path.parent
        for path in (REPO_ROOT / "skills").glob("*/*/SKILL.md")
        if path.parent.name.startswith("physics-")
    )
    missing = []
    for skill_dir in skill_dirs:
        missing_items = []
        if not (skill_dir / "SKILL.md").exists():
            missing_items.append("SKILL.md")
        if not (skill_dir / "agents" / "openai.yaml").exists():
            missing_items.append("agents/openai.yaml")
        if missing_items:
            missing.append({"skill": skill_dir.name, "missing": missing_items})
    return release_check(
        "physics_skills_have_skill_md_and_openai_agent",
        not missing and bool(skill_dirs),
        {"skill_count": len(skill_dirs), "missing": missing},
    )


def check_hook_contracts() -> List[Dict[str, Any]]:
    """Run strict hook contract and hook coverage release checks."""
    strict = run_json_command(
        [
            sys.executable,
            "skills/control/workflow-contract-validator/scripts/validate_skill_hooks.py",
            "--strict",
            "--json",
        ]
    )
    coverage = run_json_command(
        [
            sys.executable,
            "skills/control/skill-hook-coverage-maximizer/scripts/audit_skill_hook_coverage.py",
            "--json",
        ]
    )
    strict_json = strict["stdout_json"]
    coverage_json = coverage["stdout_json"]
    return [
        release_check(
            "hook_contract_strict_validation_passes",
            bool(
                strict["ok"]
                and strict_json.get("strict") is True
                and strict_json.get("summary", {}).get("blocking_findings") == 0
            ),
            strict,
        ),
        release_check(
            "hook_coverage_remains_100_percent",
            bool(
                coverage["ok"]
                and coverage_json.get("summary", {}).get("non_wrapper_coverage_ratio")
                == 1.0
                and coverage_json.get("summary", {}).get("blocking_finding_count") == 0
            ),
            coverage,
        ),
    ]


def check_dependency_probe() -> Dict[str, Any]:
    """Check dependency probing has no missing required dependencies."""
    probe = physics_sympy_dependency_probe(
        "constant_acceleration_position", write_default_report=True
    )
    return release_check(
        "dependency_probe_passes_or_reports_optional_blockers_truthfully",
        bool(probe["ok"] and not probe["missing_required"]),
        {
            "missing_required": probe["missing_required"],
            "missing_optional": probe["missing_optional"],
            "disabled_optional_checks": probe["disabled_optional_checks"],
            "report_path": probe.get("report_path"),
        },
    )


def check_unit_and_step_verifiers() -> List[Dict[str, Any]]:
    """Check unit-analysis and step-verification verifier surfaces."""
    unit = build_physics_unit_analysis_packet("rc_discharge", write_default_report=True)
    step = build_physics_step_execution_packet(
        "rc_discharge", write_default_report=True
    )
    return [
        release_check(
            "unit_analysis_verifier_self_test_passes",
            bool(
                unit["ok"]
                and unit["dimensionally_consistent"]
                and not unit["completion_blocked"]
            ),
            {
                "case_id": unit["case_id"],
                "report_path": unit.get("report_path"),
                "critical_blockers": unit["critical_blockers"],
            },
        ),
        release_check(
            "step_verifier_self_test_passes",
            bool(
                step["ok"]
                and not step["completion_blocked"]
                and step["legacy_step_verification"]["passed"]
            ),
            {
                "case_id": step["case_id"],
                "report_path": step.get("report_path"),
                "critical_blockers": step["critical_blockers"],
            },
        ),
    ]


def check_controlled_suite(output_root: Path) -> Dict[str, Any]:
    """Check controlled physics suite passes all initial cases."""
    report = controlled_suite(output_root / "controlled_suite", include_details=False)
    return release_check(
        "controlled_physics_suite_passes_initial_cases",
        bool(report["ok"] and report["case_count"] == len(controlled_case_ids())),
        {
            "case_count": report["case_count"],
            "controlled_case_ids": report["controlled_case_ids"],
        },
    )


def check_nontrivial_gap_closure() -> Dict[str, Any]:
    """Check at least one nontrivial generated gap closure reaches complete status."""
    report = consistency_report("rc_discharge")
    expanded_steps = report["packets"]["expanded"].get("expanded_steps", [])
    generated_closures = [
        step for step in expanded_steps if step.get("status") == "expanded"
    ]
    return release_check(
        "nontrivial_generated_gap_closure_reaches_complete_status",
        bool(report["status"] == "complete" and generated_closures),
        {
            "case_id": "rc_discharge",
            "status": report["status"],
            "generated_gap_closure_count": len(generated_closures),
        },
    )


def check_inconsistent_units_block() -> Dict[str, Any]:
    """Check at least one inconsistent-units fixture blocks complete status."""
    report = adversarial_suite()
    unit_failures = [
        result
        for result in report["results"]
        if result["category"] == "unit_inconsistency"
        and result["blocked_complete_status"]
    ]
    return release_check(
        "deliberately_inconsistent_units_block_complete_status",
        bool(report["ok"] and unit_failures),
        {
            "blocked_unit_fixture_count": len(unit_failures),
            "fixture_ids": [result["id"] for result in unit_failures],
        },
    )


def check_generated_artifacts_import_cleanly(output_root: Path) -> Dict[str, Any]:
    """Check generated Python physics artifacts import and execute in clean processes."""
    failures = []
    artifacts = []
    artifact_root = output_root / "generated_artifacts"
    for case_id in controlled_case_ids():
        artifact = (
            artifact_root
            / f"Autoformalized{''.join(part.title() for part in case_id.split('_'))}.py"
        )
        write_artifact(case_id, artifact)
        command = [
            sys.executable,
            "-c",
            (
                "import importlib.util, json, pathlib, sys; "
                f"path = pathlib.Path({str(artifact)!r}); "
                "spec = importlib.util.spec_from_file_location('physics_artifact', path); "
                "module = importlib.util.module_from_spec(spec); "
                "sys.modules['physics_artifact'] = module; "
                "spec.loader.exec_module(module); "
                "report = module.run_all(); "
                "print(json.dumps({'ok': bool(report.get('ok', False)), 'case_id': report.get('case_id')}))"
            ),
        ]
        result = subprocess.run(
            command,
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
        )
        artifacts.append(str(artifact.relative_to(REPO_ROOT)))
        if result.returncode != 0:
            failures.append(
                {
                    "case_id": case_id,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                }
            )
            continue
        try:
            parsed = json.loads(result.stdout)
        except json.JSONDecodeError:
            failures.append(
                {"case_id": case_id, "stdout": result.stdout, "stderr": result.stderr}
            )
            continue
        if not parsed.get("ok"):
            failures.append(
                {"case_id": case_id, "stdout_json": parsed, "stderr": result.stderr}
            )
    return release_check(
        "generated_python_physics_artifacts_import_and_execute_cleanly",
        not failures,
        {
            "artifact_count": len(artifacts),
            "artifacts": artifacts,
            "failures": failures,
        },
    )


def check_rfde_metrics_present() -> Dict[str, Any]:
    """Check RFDE report contains physics-specific metrics."""
    required = {
        "source_anchor_coverage",
        "equation_parse_coverage",
        "quantity_binding_completeness",
        "dimension_consistency",
        "unit_grounding_density",
        "law_grounding_density",
        "implicit_gap_closure",
        "step_executability",
        "assumption_regime_fidelity",
        "coordinate_frame_explicitness",
        "target_derivation_success",
        "artifact_realness",
    }
    report = consistency_report("rc_discharge", write_default_report=True)
    missing = sorted(required - set(report["physics_rfde_metrics"]))
    return release_check(
        "rfde_report_includes_physics_specific_metrics",
        not missing
        and all(
            report["physics_rfde_metrics"].get(metric) == 1.0 for metric in required
        ),
        {
            "case_id": "rc_discharge",
            "missing": missing,
            "metrics": report["physics_rfde_metrics"],
            "report_path": report.get("report_path"),
        },
    )


def check_documentation_rendering() -> Dict[str, Any]:
    """Check documentation renders equations, code, units, and derivation graph."""
    phase17 = run_json_command(
        [sys.executable, "tests/physics_sympy/run_phase17_human_reports.py", "--json"]
    )
    html_paths = [
        Path(case["html_path"]) for case in phase17["stdout_json"].get("cases", [])
    ]
    missing_markers = []
    for html_path in html_paths:
        text = (REPO_ROOT / html_path).read_text(encoding="utf-8")
        for marker in [
            "Trace",
            "Side-By-Side Derivation Evidence",
            "Unit-Flow Diagram",
            "Derivation Graph",
            "<svg",
        ]:
            if marker not in text:
                missing_markers.append({"path": str(html_path), "marker": marker})
    return release_check(
        "documentation_renders_equations_code_units_and_derivation_graph",
        bool(phase17["ok"] and html_paths and not missing_markers),
        {
            "phase17": phase17,
            "html_paths": [str(path) for path in html_paths],
            "missing_markers": missing_markers,
        },
    )


def check_no_unresolved_gaps_marked_complete() -> Dict[str, Any]:
    """Check complete generated artifacts do not carry unresolved gaps."""
    violations = []
    for case_id in all_case_ids():
        report = consistency_report(case_id)
        unresolved = report["packets"]["expanded"].get("unresolved_gaps", [])
        if report["status"] == "complete" and unresolved:
            violations.append({"case_id": case_id, "unresolved_gaps": unresolved})
    return release_check(
        "no_generated_artifact_with_unresolved_gaps_marked_complete",
        not violations,
        {"case_count": len(all_case_ids()), "violations": violations},
    )


def run_check(output_root: Path) -> Dict[str, Any]:
    """Run all Phase 18 release criteria."""
    output_root.mkdir(parents=True, exist_ok=True)
    checks: List[Dict[str, Any]] = []
    checks.append(check_physics_skill_agent_surfaces())
    checks.extend(check_hook_contracts())
    checks.append(check_dependency_probe())
    checks.extend(check_unit_and_step_verifiers())
    checks.append(check_controlled_suite(output_root))
    checks.append(check_nontrivial_gap_closure())
    checks.append(check_inconsistent_units_block())
    checks.append(check_generated_artifacts_import_cleanly(output_root))
    checks.append(check_rfde_metrics_present())
    checks.append(check_documentation_rendering())
    checks.append(check_no_unresolved_gaps_marked_complete())
    failed = [check for check in checks if not check["ok"]]
    report = {
        "ok": not failed,
        "backend": "sympy",
        "style": "sympy_physics_derivation_trace",
        "phase": "phase18_release_criteria_for_first_physics_slice",
        "generated_at": now(),
        "check_count": len(checks),
        "passed": len(checks) - len(failed),
        "failed": len(failed),
        "checks": checks,
        "failed_checks": failed,
    }
    report_path = output_root / "phase18_release_report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    report["report_path"] = str(report_path.relative_to(REPO_ROOT))
    return report


def main() -> int:
    """Serve as the command-line entry point for the Phase 18 release gate."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("artifacts/physics_sympy/phase18_release"),
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = run_check((REPO_ROOT / args.output_root).resolve())
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    else:
        print(f"ok: {report['ok']}")
        print(f"passed: {report['passed']}/{report['check_count']}")
        print(f"report: {report['report_path']}")
    return 0 if report["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
