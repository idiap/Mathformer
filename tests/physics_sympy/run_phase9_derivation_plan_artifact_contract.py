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
#   Contains executable tests, fixtures, and manifests used for local and CI validation.
#
# Maintenance Notes:
#   Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.

"""Check Phase 9 derivation planning and executable artifact contracts."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backends.sympy.MathformerPhysicsSympy.pipeline import (  # noqa: E402
    PHYSICS_ARTIFACT_REQUIRED_DATA_BINDINGS,
    PHYSICS_ARTIFACT_REQUIRED_FUNCTIONS,
    PHYSICS_DERIVATION_PLAN_STAGES,
    build_physics_derivation_plan_packet,
    write_artifact,
)

CASES = ["rc_discharge", "formalphysics_0000", "projectile_range_level_ground"]


def import_module_from_path(path: Path) -> Any:
    """Import a generated artifact from an explicit filesystem path."""
    spec = importlib.util.spec_from_file_location(
        "phase9_generated_physics_artifact", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import generated artifact: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["phase9_generated_physics_artifact"] = module
    spec.loader.exec_module(module)
    return module


def check_plan(case_id: str, findings: List[str]) -> Dict[str, Any]:
    """Validate one topological derivation plan packet."""
    plan = build_physics_derivation_plan_packet(case_id)
    if not plan["ok"]:
        findings.append(f"plan packet is not ok for {case_id}")
    if plan["stage_order"] != list(PHYSICS_DERIVATION_PLAN_STAGES):
        findings.append(f"stage order mismatch for {case_id}")
    if not plan["topological_order_valid"]:
        findings.append(f"topological order invalid for {case_id}")
    if plan["completion_blocked"]:
        findings.append(f"plan should not be completion-blocked for {case_id}")
    if len(plan["ordered_jobs"]) != len(PHYSICS_DERIVATION_PLAN_STAGES):
        findings.append(
            f"unexpected job count for {case_id}: {len(plan['ordered_jobs'])}"
        )
    seen = set()
    for job in plan["ordered_jobs"]:
        if any(dep not in seen for dep in job["depends_on"]):
            findings.append(
                f"job depends on a later/missing job for {case_id}: {job['id']}"
            )
        if not job["produces"]:
            findings.append(f"job has no declared outputs for {case_id}: {job['id']}")
        seen.add(job["id"])
    contract = plan["artifact_contract"]
    missing_bindings = sorted(
        set(PHYSICS_ARTIFACT_REQUIRED_DATA_BINDINGS).difference(
            contract["required_data_bindings"]
        )
    )
    missing_functions = sorted(
        set(PHYSICS_ARTIFACT_REQUIRED_FUNCTIONS).difference(
            contract["required_functions"]
        )
    )
    if missing_bindings:
        findings.append(
            f"plan contract missing data bindings for {case_id}: {missing_bindings}"
        )
    if missing_functions:
        findings.append(
            f"plan contract missing functions for {case_id}: {missing_functions}"
        )
    if "final answer" not in contract["hidden_final_answer_policy"]:
        findings.append(f"hidden-final policy missing for {case_id}")
    if not plan["target_chain_step_ids"]:
        findings.append(f"target chain has no step ids for {case_id}")
    return plan


def check_generated_artifact(case_id: str, findings: List[str]) -> Dict[str, Any]:
    """Draft, import, and validate one executable SymPy artifact."""
    with tempfile.TemporaryDirectory(prefix="mathformer_phase9_") as tmp_dir:
        artifact_path = (
            Path(tmp_dir)
            / f"Autoformalized{''.join(part.title() for part in case_id.split('_'))}.py"
        )
        draft = write_artifact(case_id, artifact_path)
        module = import_module_from_path(artifact_path)
        missing_bindings = [
            name
            for name in PHYSICS_ARTIFACT_REQUIRED_DATA_BINDINGS
            if not hasattr(module, name)
        ]
        missing_functions = [
            name
            for name in PHYSICS_ARTIFACT_REQUIRED_FUNCTIONS
            if not callable(getattr(module, name, None))
        ]
        if missing_bindings:
            findings.append(
                f"generated artifact missing data bindings: {missing_bindings}"
            )
        if missing_functions:
            findings.append(
                f"generated artifact missing functions: {missing_functions}"
            )
        if "DIMENSION_MODEL" not in draft["standard_contract"]:
            findings.append("draft report standard contract omits DIMENSION_MODEL")
        equations = module.build_equations()
        if str(module.derive_target()) != str(equations["target_expression"]):
            findings.append(
                "derive_target is not the build_equations target expression"
            )
        if not module.validate_derivation_steps()["passed"]:
            findings.append("generated artifact derivation steps did not validate")
        if not module.validate_no_hidden_target()["passed"]:
            findings.append("generated artifact appears to hide a target-like source")
        if not module.validate_numeric_samples()["passed"]:
            findings.append("generated artifact numeric samples did not validate")
        if not module.explain_trace():
            findings.append("generated artifact explain_trace is empty")
        if len(module.DERIVATION_STEPS) != len(module.explain_trace()):
            findings.append(
                "explain_trace does not cover every DERIVATION_STEPS record"
            )
        return {
            "draft": draft,
            "artifact_contract": draft["standard_contract"],
            "derivation_step_count": len(module.DERIVATION_STEPS),
            "dimension_model_count": len(module.DIMENSION_MODEL),
        }


def run_check() -> Dict[str, Any]:
    """Validate Phase 9 planning and artifact-drafting behavior."""
    findings: List[str] = []
    plans = [check_plan(case_id, findings) for case_id in CASES]
    artifact_report = check_generated_artifact("rc_discharge", findings)
    persisted = build_physics_derivation_plan_packet(
        "rc_discharge", write_default_report=True
    )
    persisted_path = REPO_ROOT / persisted.get("report_path", "")
    if not persisted.get("report_path") or not persisted_path.exists():
        findings.append("derivation plan packet was not persisted by default writer")
    return {
        "ok": not findings,
        "backend": "sympy",
        "style": "sympy_physics_derivation_trace",
        "phase": "phase9_derivation_planning_and_executable_artifact_contract",
        "findings": findings,
        "case_count": len(CASES),
        "stage_order": list(PHYSICS_DERIVATION_PLAN_STAGES),
        "plan_job_counts": {
            plan["case_id"]: len(plan["ordered_jobs"]) for plan in plans
        },
        "artifact_contract": artifact_report["artifact_contract"],
        "artifact_derivation_step_count": artifact_report["derivation_step_count"],
        "artifact_dimension_model_count": artifact_report["dimension_model_count"],
        "derivation_plan_packet_path": persisted.get("report_path"),
    }


def main() -> int:
    """Serve as the command-line entry point for the Phase 9 contract check."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = run_check()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    else:
        print(f"ok: {report['ok']}")
        print(f"case_count: {report['case_count']}")
        print(f"findings: {len(report['findings'])}")
    return 0 if report["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
