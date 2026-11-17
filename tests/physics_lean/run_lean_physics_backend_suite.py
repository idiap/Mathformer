#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402 - imports follow explicit direct-script path setup
#
#

# File Documentation
#
# Motivation:
#   Keep the Lean physics backend controlled by deterministic, inspectable
#   regressions rather than relying on ad hoc manual checks.
#
# Intent:
#   Exercise one real MathformerPhysicsLib Lean artifact through the pathology
#   repair loop and ensure adversarial Lean fixtures trigger the expected
#   semantic-drift, assumption, and dimension diagnoses.
#
# Function:
#   Runs local skill scripts over a controlled artifact and fixture set, writes
#   JSON evidence under artifacts, and exits nonzero if expected controls are
#   missing.
#
# Maintenance Notes:
#   Add fixtures when new Lean physics pathology classes become release
#   blockers, and keep expected codes synchronized with the critic scripts.

"""Run the deterministic Lean physics backend suite."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
ARTIFACT_ROOT = REPO_ROOT / "artifacts/physics_lean/backend_suite"
FIXTURE_ROOT = REPO_ROOT / "tests/fixtures/physics_lean_adversarial"
CONTROLLED_CASE = "formalphysics_0000"
CONTROLLED_SOURCE = (
    REPO_ROOT
    / "data/benchmarks/formal_science/physics_top10_sources/01_formalphysics_0000.tex"
)
CONTROLLED_LEAN = (
    REPO_ROOT
    / "libraries/MathformerPhysicsLib/Lean/formalphysics_0000/MathformerPhysics.lean"
)
CONTROLLED_REPORT_ROOT = (
    REPO_ROOT / "artifacts/physics_lean/from_scratch_lean/formalphysics_0000"
)
CONTROLLED_LIB_REPORT = (
    REPO_ROOT
    / "libraries/MathformerPhysicsLib/Lean/formalphysics_0000/consistency_report.json"
)

from libraries.MathformerPhysicsLib.release_status import (
    build_release_status,
)

ADVERSARIAL_CASES: dict[str, dict[str, Any]] = {
    "raw_scalar_erasure": {
        "expected": {
            "physical_semantics": {
                "physical_quantities_erased",
                "vector_structure_erased",
            },
            "dimension": {"missing_dimension_policy", "missing_unit_obligations"},
            "drift_categories": {"notational_collapse"},
        },
    },
    "target_as_assumption": {
        "expected": {
            "drift": {"proof_reduced_to_target_shaped_substitution"},
            "drift_categories": {"abstraction_elevation"},
        },
    },
    "missing_dimensions": {
        "expected": {
            "dimension": {"missing_unit_obligations"},
        },
    },
    "silent_strengthening": {
        "expected": {
            "assumption": {"hidden_positivity_assumption"},
            "drift_categories": {"implicit_premise_selection"},
        },
    },
    "missing_frame_conventions": {
        "expected": {
            "physical_semantics": {"frame_context_missing"},
            "assumption": {"missing_frame_assumption"},
            "drift_categories": {"notational_collapse"},
        },
    },
}


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_json(args: list[str], output: Path | None = None) -> dict[str, Any]:
    command = [sys.executable, *args]
    if output is not None:
        command.extend(["--output", rel(output)])
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "command failed: "
            + " ".join(command)
            + f"\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    if output is not None and output.exists():
        return load_json(output)
    return json.loads(result.stdout)


def run_fresh_lean_compile(path: Path) -> dict[str, Any]:
    """Compile a Lean artifact now and bind the evidence to its content."""

    command = ["lake", "env", "lean", rel(path)]
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    diagnostics = result.stdout + "\n" + result.stderr
    return {
        "command": command,
        "returncode": result.returncode,
        "compiled": result.returncode == 0,
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "diagnostic_sha256": hashlib.sha256(diagnostics.encode()).hexdigest(),
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def finding_codes(report: dict[str, Any]) -> set[str]:
    return {
        str(item.get("code"))
        for item in report.get("findings", [])
        if isinstance(item, dict) and item.get("code")
    }


def finding_categories(report: dict[str, Any]) -> set[str]:
    return {
        str(item.get("category"))
        for item in report.get("findings", [])
        if isinstance(item, dict) and item.get("category")
    }


def base_type_packet(case_id: str, *, protected: bool = False) -> dict[str, Any]:
    surfaces = []
    obligations = []
    if protected:
        surfaces = [
            "EuclideanSpace Real (Fin 3)",
            "UnitDimensionCompatible Prop bridge",
            "SourceBacked Law Prop witness",
        ]
        obligations = [
            "source_law_or_generated_support_for_each_physics_step",
            "unit_dimension_bridge_formalized",
            "compact_algebraic_core_formalized",
        ]
    return {
        "case_id": case_id,
        "style": "lean_physics_type_system_packet",
        "grounding_policy": "mathlib_native_first",
        "features": {
            "vectors": protected,
            "fields": protected,
            "coordinate_frames": protected,
        },
        "lean_surfaces": surfaces,
        "required_obligations": obligations,
    }


def assumption_packet(
    case_id: str, categories: list[str] | None = None
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "style": "lean_physics_assumption_context_packet",
        "assumptions": [
            {"category": category, "status": "source-backed"}
            for category in (categories or [])
        ],
    }


def unit_report(status: str = "missing") -> dict[str, Any]:
    return {"status": status, "metrics": {}, "findings": []}


def run_critics_for_case(
    case_id: str, source: Path, lean: Path, case_dir: Path
) -> dict[str, Any]:
    type_packet_path = case_dir / "type_system_packet.json"
    assumption_packet_path = case_dir / "assumption_packet.json"
    unit_report_path = case_dir / "unit_report.json"
    write_json(type_packet_path, base_type_packet(case_id))
    write_json(assumption_packet_path, assumption_packet(case_id))
    write_json(unit_report_path, unit_report())

    unit = run_json(
        [
            "skills/physics-lean/physics-lean-unit-analysis-verifier/scripts/verify_physics_lean_units.py",
            "--lean-file",
            rel(lean),
        ],
        case_dir / "unit_verifier_report.json",
    )
    semantics = run_json(
        [
            "skills/physics-lean/physics-lean-physical-semantics-critic/scripts/critique_physics_lean_semantics.py",
            "--source-file",
            rel(source),
            "--lean-file",
            rel(lean),
            "--type-packet",
            rel(type_packet_path),
            "--assumption-packet",
            rel(assumption_packet_path),
        ],
        case_dir / "physical_semantics_critic.json",
    )
    assumptions = run_json(
        [
            "skills/physics-lean/physics-lean-assumption-critic/scripts/critique_physics_lean_assumptions.py",
            "--source-file",
            rel(source),
            "--lean-file",
            rel(lean),
            "--assumption-packet",
            rel(assumption_packet_path),
        ],
        case_dir / "assumption_critic.json",
    )
    dimensions = run_json(
        [
            "skills/physics-lean/physics-lean-dimension-critic/scripts/critique_physics_lean_dimensions.py",
            "--source-file",
            rel(source),
            "--lean-file",
            rel(lean),
            "--type-packet",
            rel(type_packet_path),
            "--unit-report",
            rel(unit_report_path),
        ],
        case_dir / "dimension_critic.json",
    )
    drift = run_json(
        [
            "skills/physics-lean/physics-lean-drift-pathology-monitor/scripts/monitor_physics_lean_drift_pathologies.py",
            "--source-file",
            rel(source),
            "--lean-file",
            rel(lean),
            "--type-packet",
            rel(type_packet_path),
            "--assumption-packet",
            rel(assumption_packet_path),
            "--unit-report",
            rel(unit_report_path),
            "--physical-semantics-report",
            rel(case_dir / "physical_semantics_critic.json"),
            "--assumption-critic-report",
            rel(case_dir / "assumption_critic.json"),
            "--dimension-critic-report",
            rel(case_dir / "dimension_critic.json"),
        ],
        case_dir / "drift_pathology_monitor.json",
    )
    return {
        "unit": unit,
        "physical_semantics": semantics,
        "assumption": assumptions,
        "dimension": dimensions,
        "drift": drift,
    }


REPAIR_SCRIPTS = [
    (
        "notational_collapse",
        "skills/physics-lean/physics-lean-notational-collapse-repairer/scripts/repair_notational_collapse.py",
    ),
    (
        "abstraction_elevation",
        "skills/physics-lean/physics-lean-abstraction-elevation-repairer/scripts/repair_abstraction_elevation.py",
    ),
    (
        "proof_strategy",
        "skills/physics-lean/physics-lean-proof-strategy-alignment-repairer/scripts/repair_proof_strategy_alignment.py",
    ),
    (
        "implicit_premise",
        "skills/physics-lean/physics-lean-implicit-premise-normalizer/scripts/normalize_implicit_premises.py",
    ),
]


def prepare_controlled() -> dict[str, Any]:
    """Collect native controlled evidence before the fixed plan traversal."""
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    case_dir = ARTIFACT_ROOT / "controlled_artifact" / CONTROLLED_CASE
    case_dir.mkdir(parents=True, exist_ok=True)
    consistency = load_json(CONTROLLED_LIB_REPORT)
    fresh_compile = run_fresh_lean_compile(CONTROLLED_LEAN)
    generative = run_json(
        [
            "skills/physics-lean/physics-lean-generative-critic-orchestrator/scripts/build_physics_lean_generative_critic_plan.py",
            "--source-file",
            rel(CONTROLLED_SOURCE),
            "--lean-file",
            rel(CONTROLLED_LEAN),
            "--high-risk",
        ],
        case_dir / "generative_critic_plan.json",
    )
    monitor = run_json(
        [
            "skills/physics-lean/physics-lean-drift-pathology-monitor/scripts/monitor_physics_lean_drift_pathologies.py",
            "--source-file",
            rel(CONTROLLED_SOURCE),
            "--lean-file",
            rel(CONTROLLED_LEAN),
            "--type-packet",
            rel(CONTROLLED_REPORT_ROOT / "type_system_packet.json"),
            "--assumption-packet",
            rel(CONTROLLED_REPORT_ROOT / "assumption_packet.json"),
            "--unit-report",
            rel(CONTROLLED_REPORT_ROOT / "unit_report.json"),
            "--physical-semantics-report",
            rel(CONTROLLED_REPORT_ROOT / "physical_semantics_critic.json"),
            "--assumption-critic-report",
            rel(CONTROLLED_REPORT_ROOT / "assumption_critic.json"),
            "--dimension-critic-report",
            rel(CONTROLLED_REPORT_ROOT / "dimension_critic.json"),
        ],
        case_dir / "drift_pathology_monitor.json",
    )
    objects = run_json(
        [
            "skills/physics-common/physics-math-object-detector/scripts/detect_physics_math_objects.py",
            "--source-file",
            rel(CONTROLLED_SOURCE),
            "--lean-file",
            rel(CONTROLLED_LEAN),
            "--monitor-report",
            rel(case_dir / "drift_pathology_monitor.json"),
        ],
        case_dir / "object_packet.json",
    )
    workbench = run_json(
        [
            "skills/mathformerphysicslib/mathformerphysicslib-object-workbench/scripts/build_mathformerphysicslib_object_workbench.py",
            "--object-packet",
            rel(case_dir / "object_packet.json"),
        ],
        case_dir / "object_workbench_plan.json",
    )
    return {
        "evidence": {
            "case_dir": rel(case_dir),
            "consistency": consistency,
            "fresh_compile": fresh_compile,
            "generative": generative,
            "monitor": monitor,
            "objects": objects,
            "workbench": workbench,
        },
        "state": {"cursor": 0, "repair_reports": {}, "repair_paths": []},
    }


def collect_plan(evidence: dict, state: dict) -> dict[str, Any]:
    """Perform exactly one native plan call, retaining insertion order."""
    cursor = state["cursor"]
    label, script = REPAIR_SCRIPTS[cursor]
    case_dir = REPO_ROOT / evidence["case_dir"]
    repair_reports = dict(state["repair_reports"])
    repair_paths = list(state["repair_paths"])
    path = case_dir / f"{label}_repair_plan.json"
    repair_reports[label] = run_json(
        [
            script,
            "--monitor-report",
            rel(case_dir / "drift_pathology_monitor.json"),
            "--object-packet",
            rel(case_dir / "object_packet.json"),
            "--workbench-plan",
            rel(case_dir / "object_workbench_plan.json"),
        ],
        path,
    )
    repair_paths.append(rel(path))
    cursor += 1
    return {
        "state": {
            "cursor": cursor,
            "repair_reports": repair_reports,
            "repair_paths": repair_paths,
        },
        "done": cursor == len(REPAIR_SCRIPTS),
    }


def begin_arguments(plans: dict) -> dict[str, Any]:
    return {"state": {"cursor": 0, "repair_args": []}}


def append_argument(plans: dict, state: dict) -> dict[str, Any]:
    cursor = state["cursor"]
    path = REPO_ROOT / plans["repair_paths"][cursor]
    repair_args = list(state["repair_args"])
    repair_args.extend(["--repair-plan", rel(path)])
    cursor += 1
    return {
        "state": {"cursor": cursor, "repair_args": repair_args},
        "done": cursor == len(plans["repair_paths"]),
    }


def finish_controlled(evidence: dict, plans: dict, args: dict) -> dict[str, Any]:
    case_dir = REPO_ROOT / evidence["case_dir"]
    consistency = evidence["consistency"]
    fresh_compile = evidence["fresh_compile"]
    generative = evidence["generative"]
    monitor = evidence["monitor"]
    objects = evidence["objects"]
    workbench = evidence["workbench"]
    repair_reports = plans["repair_reports"]
    repair_args = args["repair_args"]
    repair_loop = run_json(
        [
            "skills/physics-lean/physics-lean-pathology-repair-orchestrator/scripts/orchestrate_pathology_repair.py",
            "--monitor-report",
            rel(case_dir / "drift_pathology_monitor.json"),
            "--object-packet",
            rel(case_dir / "object_packet.json"),
            "--workbench-plan",
            rel(case_dir / "object_workbench_plan.json"),
            *repair_args,
        ],
        case_dir / "pathology_repair_loop.json",
    )
    generative_repair = run_json(
        [
            "skills/physics-lean/physics-lean-generative-repair-orchestrator/scripts/build_physics_lean_generative_repair_plan.py",
            "--source-file",
            rel(CONTROLLED_SOURCE),
            "--lean-file",
            rel(CONTROLLED_LEAN),
            "--monitor-report",
            rel(case_dir / "drift_pathology_monitor.json"),
            "--object-packet",
            rel(case_dir / "object_packet.json"),
            "--workbench-plan",
            rel(case_dir / "object_workbench_plan.json"),
            "--repair-loop",
            rel(case_dir / "pathology_repair_loop.json"),
            *repair_args,
            "--high-risk",
        ],
        case_dir / "generative_repair_plan.json",
    )
    expansion = run_json(
        [
            "skills/physics-lean/physics-lean-repair-expansion-cartographer/scripts/map_repair_expansion.py",
            "--monitor-report",
            rel(case_dir / "drift_pathology_monitor.json"),
            "--object-packet",
            rel(case_dir / "object_packet.json"),
            "--workbench-plan",
            rel(case_dir / "object_workbench_plan.json"),
            "--repair-loop",
            rel(case_dir / "pathology_repair_loop.json"),
            "--generative-repair",
            rel(case_dir / "generative_repair_plan.json"),
            *repair_args,
        ],
        case_dir / "repair_expansion_map.json",
    )
    recursive = run_json(
        [
            "skills/physics-lean/physics-lean-recursive-repair-loop-controller/scripts/control_recursive_repair_loop.py",
            "--expansion-map",
            rel(case_dir / "repair_expansion_map.json"),
            "--iteration",
            "1",
            "--max-iterations",
            "6",
        ],
        case_dir / "recursive_repair_control.json",
    )
    checks = {
        "fresh_kernel_compile": fresh_compile["compiled"],
        "stored_consistency_is_secondary_only": isinstance(consistency, dict),
        "generative_critic_full": generative.get("codex_exec_enabled") is True
        and len(generative.get("probe_prompts", [])) >= 5,
        "monitor_routes_findings": monitor.get("status") in {"fail", "warn", "pass"}
        and "category_counts" in monitor,
        "objects_detected": objects.get("object_count", 0) >= 1,
        "workbench_library_first": workbench.get("status")
        in {"library_work_required", "ready", "no_objects"},
        "repair_loop_guarded": repair_loop.get("target_refinement_policy", {}).get(
            "library_first_required"
        )
        is True,
        "generative_repair_full": generative_repair.get("codex_exec_enabled") is True
        and len(generative_repair.get("probe_prompts", [])) >= 4,
        "expansion_exhaustive": expansion.get("exhaustive") is True,
        "recursive_control_present": recursive.get("status")
        in {"complete", "recurse", "blocked"},
    }
    terminal_states = [
        str(value)
        for value in (
            repair_loop.get("status"),
            expansion.get("status"),
            recursive.get("status"),
        )
        if value
    ]
    release = build_release_status(
        workflow_executed=True,
        checks_passed=all(checks.values()),
        artifact_status="candidate",
        library_status=(
            "blocked"
            if {"recurse", "needs_expansion", "repair_required", "blocked"}
            & set(terminal_states)
            else "accepted"
        ),
        blockers=[],
        terminal_states=terminal_states,
    )
    return {
        "case_id": CONTROLLED_CASE,
        "checks": checks,
        "ok": all(checks.values()),
        **release,
        "fresh_compile": fresh_compile,
        "consistency_status": consistency.get("status"),
        "monitor_status": monitor.get("status"),
        "monitor_categories": monitor.get("category_counts", {}),
        "object_count": objects.get("object_count", 0),
        "repair_loop_status": repair_loop.get("status"),
        "generative_repair_probe_count": len(
            generative_repair.get("probe_prompts", [])
        ),
        "expansion_status": expansion.get("status"),
        "recursive_status": recursive.get("status"),
        "artifact_dir": rel(case_dir),
        "repair_plan_statuses": {
            label: report.get("status") for label, report in repair_reports.items()
        },
    }


def run_controlled_artifact_loop() -> dict[str, Any]:
    prepared = prepare_controlled()
    plans = prepared["state"]
    for _ in REPAIR_SCRIPTS:
        plans = collect_plan(prepared["evidence"], plans)["state"]
    args = begin_arguments(plans)["state"]
    for _ in plans["repair_paths"]:
        args = append_argument(plans, args)["state"]
    return finish_controlled(prepared["evidence"], plans, args)


def begin_adversarial() -> dict[str, Any]:
    return {"state": {"cursor": 0, "all_ok": True, "results": {}}}


def check_fixture(state: dict) -> dict[str, Any]:
    cursor = state["cursor"]
    case_id, spec = list(ADVERSARIAL_CASES.items())[cursor]
    results = dict(state["results"])
    all_ok = state["all_ok"]
    case_dir = ARTIFACT_ROOT / "adversarial" / case_id
    source = FIXTURE_ROOT / f"{case_id}.source.txt"
    lean = FIXTURE_ROOT / f"{case_id}.lean"
    reports = run_critics_for_case(case_id, source, lean, case_dir)
    expected = spec["expected"]
    checks = {}
    for report_name in ("physical_semantics", "assumption", "dimension", "drift"):
        if report_name in expected:
            observed = finding_codes(reports[report_name])
            checks[f"{report_name}_codes"] = expected[report_name].issubset(observed)
    if "drift_categories" in expected:
        checks["drift_categories"] = expected["drift_categories"].issubset(
            finding_categories(reports["drift"])
        )
    ok = all(checks.values())
    all_ok = all_ok and ok
    results[case_id] = {
        "ok": ok,
        "checks": checks,
        "statuses": {name: report.get("status") for name, report in reports.items()},
        "codes": {
            name: sorted(finding_codes(report)) for name, report in reports.items()
        },
        "categories": sorted(finding_categories(reports["drift"])),
        "artifact_dir": rel(case_dir),
    }
    cursor += 1
    return {
        "state": {"cursor": cursor, "all_ok": all_ok, "results": results},
        "done": cursor == len(ADVERSARIAL_CASES),
    }


def run_adversarial_suite() -> dict[str, Any]:
    state = begin_adversarial()["state"]
    for _ in ADVERSARIAL_CASES:
        state = check_fixture(state)["state"]
    return {"ok": state["all_ok"], "cases": state["results"]}


def derivation_regression() -> dict[str, Any]:
    return run_json(
        ["tests/physics_lean/run_derivation_completeness_regression.py", "--json"]
    )


def thoroughness_regression() -> dict[str, Any]:
    return run_json(
        ["tests/physics_lean/run_grounded_sample_thoroughness.py", "--json"]
    )


def write_suite(
    controlled: dict, adversarial: dict, derivation: dict, thoroughness: dict
) -> dict[str, Any]:
    derivation_completeness = derivation
    grounded_sample_thoroughness = thoroughness
    checks_passed = (
        controlled["ok"]
        and adversarial["ok"]
        and derivation_completeness["ok"]
        and grounded_sample_thoroughness["ok"]
    )
    release = build_release_status(
        workflow_executed=True,
        checks_passed=checks_passed,
        artifact_status=controlled["artifact_status"],
        library_status=controlled["library_status"],
        blockers=controlled["blockers"],
        terminal_states=controlled["terminal_states"],
    )
    payload = {
        "ok": checks_passed,
        **release,
        "style": "lean_physics_backend_suite_report",
        "controlled_artifact": controlled,
        "adversarial": adversarial,
        "derivation_completeness": derivation_completeness,
        "grounded_sample_thoroughness": grounded_sample_thoroughness,
        "artifact_root": rel(ARTIFACT_ROOT),
    }
    write_json(ARTIFACT_ROOT / "lean_physics_backend_suite_report.json", payload)
    return payload


def run_suite() -> dict[str, Any]:
    controlled = run_controlled_artifact_loop()
    adversarial = run_adversarial_suite()
    derivation = derivation_regression()
    thoroughness = thoroughness_regression()
    return write_suite(controlled, adversarial, derivation, thoroughness)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = run_suite()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Lean physics backend suite ok={payload['ok']}")
        print(
            f"Report: {payload['artifact_root']}/lean_physics_backend_suite_report.json"
        )
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
