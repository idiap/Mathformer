#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Capture the research-paper production workflow as auditable agent skills and helper scripts.
#
# Intent:
#   Separate scientific writing, evidence mapping, figure generation, and theory-evolution modeling roles.
#
# Function:
#   Provides structured guidance and automation for paper-oriented artifacts.
#
# Maintenance Notes:
#   Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.

"""Build predictive theory-evolution model priors for backends/lean/Mathformer/RFDE."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

METRICS = [
    "lean_executability",
    "anchor_coverage",
    "anchor_validity",
    "semantic_shape",
    "reverse_informal_consistency",
    "mathlib_grounding",
    "nonvacuity",
    "dependency_closure",
    "proof_coherence",
    "realness",
    "workflow_evidence",
    "instrumentation_density",
    "dashboard_inspection",
]


def vector(**values: float) -> dict[str, float]:
    """Document the responsibility of ``vector``.

    Motivation:
        Capture the research-paper production workflow as auditable agent skills and helper scripts.

    Intent:
        Provide the local operation named ``vector`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return {metric: float(values.get(metric, 0.0)) for metric in METRICS}


def default_model() -> dict:
    """A plausible chapter-scale Mathformer prior, not fitted evidence."""

    return {
        "schema_version": 1,
        "model_id": "default-mathformer-theory",
        "description": (
            "Plausible prior for theory evolution across a chapter-scale "
            "source-anchored Mathformer autoformalization run."
        ),
        "metrics": METRICS,
        "protected_metrics": [
            "lean_executability",
            "anchor_coverage",
            "anchor_validity",
            "nonvacuity",
            "realness",
        ],
        "delta_notation": {
            "signed": "Delta_t^q = m_{t+1}^q - m_t^q",
            "relative_up": "Dhat_t^{q,up} = max(0,Delta_t^q)/(eps + 1 - m_t^q)",
            "relative_down": "Dhat_t^{q,down} = max(0,-Delta_t^q)/(eps + m_t^q)",
            "epsilon": 1e-6,
        },
        "initial_state": vector(
            lean_executability=0.0,
            anchor_coverage=0.05,
            anchor_validity=0.75,
            semantic_shape=0.15,
            reverse_informal_consistency=0.0,
            mathlib_grounding=0.10,
            nonvacuity=0.55,
            dependency_closure=0.10,
            proof_coherence=0.0,
            realness=0.50,
            workflow_evidence=0.05,
            instrumentation_density=0.10,
            dashboard_inspection=0.0,
        ),
        "phases": [
            {
                "id": "intake",
                "duration_steps": 6,
                "cost_per_step": 1.0,
                "gain_rate": 0.28,
                "regression_probability": 0.02,
                "target": vector(
                    anchor_coverage=0.35,
                    anchor_validity=0.92,
                    workflow_evidence=0.25,
                    instrumentation_density=0.28,
                ),
            },
            {
                "id": "preformalization",
                "duration_steps": 8,
                "cost_per_step": 1.4,
                "gain_rate": 0.22,
                "regression_probability": 0.03,
                "target": vector(
                    anchor_coverage=0.58,
                    anchor_validity=0.96,
                    semantic_shape=0.45,
                    dependency_closure=0.42,
                    nonvacuity=0.72,
                    workflow_evidence=0.38,
                    instrumentation_density=0.42,
                ),
            },
            {
                "id": "mathlib_grounding",
                "duration_steps": 8,
                "cost_per_step": 1.8,
                "gain_rate": 0.24,
                "regression_probability": 0.04,
                "target": vector(
                    mathlib_grounding=0.78,
                    semantic_shape=0.58,
                    dependency_closure=0.55,
                    workflow_evidence=0.48,
                    instrumentation_density=0.50,
                ),
            },
            {
                "id": "drafting",
                "duration_steps": 6,
                "cost_per_step": 2.2,
                "gain_rate": 0.26,
                "regression_probability": 0.10,
                "target": vector(
                    lean_executability=0.38,
                    anchor_coverage=0.72,
                    semantic_shape=0.62,
                    proof_coherence=0.32,
                    realness=0.72,
                    workflow_evidence=0.55,
                    instrumentation_density=0.60,
                    dashboard_inspection=0.12,
                ),
            },
            {
                "id": "execution_critique",
                "duration_steps": 7,
                "cost_per_step": 2.0,
                "gain_rate": 0.20,
                "regression_probability": 0.12,
                "target": vector(
                    lean_executability=0.66,
                    reverse_informal_consistency=0.48,
                    proof_coherence=0.45,
                    realness=0.82,
                    workflow_evidence=0.62,
                    instrumentation_density=0.70,
                    dashboard_inspection=0.32,
                ),
            },
            {
                "id": "repair",
                "duration_steps": 10,
                "cost_per_step": 2.4,
                "gain_rate": 0.30,
                "regression_probability": 0.08,
                "target": vector(
                    lean_executability=0.93,
                    semantic_shape=0.82,
                    reverse_informal_consistency=0.80,
                    proof_coherence=0.78,
                    realness=0.96,
                    nonvacuity=0.92,
                    workflow_evidence=0.72,
                    instrumentation_density=0.78,
                    dashboard_inspection=0.55,
                ),
            },
            {
                "id": "consistency",
                "duration_steps": 7,
                "cost_per_step": 1.7,
                "gain_rate": 0.24,
                "regression_probability": 0.03,
                "target": vector(
                    lean_executability=0.98,
                    anchor_coverage=0.90,
                    anchor_validity=0.99,
                    semantic_shape=0.92,
                    reverse_informal_consistency=0.92,
                    mathlib_grounding=0.90,
                    nonvacuity=0.96,
                    dependency_closure=0.92,
                    proof_coherence=0.90,
                    realness=0.99,
                    workflow_evidence=0.82,
                    instrumentation_density=0.88,
                    dashboard_inspection=0.72,
                ),
            },
            {
                "id": "evaluation_reflection",
                "duration_steps": 5,
                "cost_per_step": 1.2,
                "gain_rate": 0.18,
                "regression_probability": 0.01,
                "target": vector(
                    lean_executability=0.99,
                    anchor_coverage=0.94,
                    anchor_validity=1.0,
                    semantic_shape=0.94,
                    reverse_informal_consistency=0.94,
                    mathlib_grounding=0.94,
                    nonvacuity=0.98,
                    dependency_closure=0.96,
                    proof_coherence=0.93,
                    realness=1.0,
                    workflow_evidence=0.90,
                    instrumentation_density=0.94,
                    dashboard_inspection=0.86,
                ),
            },
        ],
        "couplings": [
            {"source": "mathlib_grounding", "target": "semantic_shape", "weight": 0.08},
            {
                "source": "dependency_closure",
                "target": "proof_coherence",
                "weight": 0.10,
            },
            {
                "source": "anchor_validity",
                "target": "reverse_informal_consistency",
                "weight": 0.05,
            },
            {"source": "realness", "target": "lean_executability", "weight": 0.04},
            {
                "source": "instrumentation_density",
                "target": "workflow_evidence",
                "weight": 0.07,
            },
            {
                "source": "dashboard_inspection",
                "target": "proof_coherence",
                "weight": 0.03,
            },
        ],
        "acceptance_thresholds": {
            "complete": {
                "lean_executability": 0.95,
                "anchor_coverage": 0.85,
                "anchor_validity": 0.98,
                "nonvacuity": 0.90,
                "realness": 0.98,
                "reverse_informal_consistency": 0.88,
                "mathlib_grounding": 0.85,
                "instrumentation_density": 0.75,
            },
            "draft": {
                "lean_executability": 0.55,
                "anchor_coverage": 0.45,
                "realness": 0.70,
            },
        },
        "observability_scenarios": [
            {
                "id": "observability_before_success",
                "evidence_status": "simulated_prior",
                "description": (
                    "Instrumentation density and dashboard inspection improve while "
                    "Lean executability remains below completion threshold."
                ),
            },
            {
                "id": "legacy_trace_gap_detection",
                "evidence_status": "simulated_prior",
                "description": (
                    "Dashboard inspection increases after validation detects missing "
                    "skill-application lifecycle stages in older traces."
                ),
            },
            {
                "id": "monitor_calibration_candidate",
                "evidence_status": "empirical_candidate",
                "description": (
                    "Reference-free monitor CSV/JSON/SVG outputs can later calibrate "
                    "weakest-dimension and regression-rate priors."
                ),
            },
        ],
        "noise": {
            "gain_sigma": 0.08,
            "regression_scale": 0.04,
            "cost_sigma": 0.15,
        },
    }


PRESETS = {
    "default-mathformer-theory": default_model,
}


def parse_arguments(argv: list[str] | None = None) -> dict:
    """Parse native CLI options; keep argparse's help and error termination."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--preset", choices=sorted(PRESETS), default="default-mathformer-theory"
    )
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    return vars(parser.parse_args(argv))


def construct_prior(args: dict) -> dict:
    """Call the selected preset once; serialized phases are never executed."""
    return PRESETS[args["preset"]]()


def persist_prior(args: dict, prior: dict) -> str:
    """Create parents and write native JSON once; propagate I/O failures."""
    output = Path(args["output"])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(prior, indent=2, sort_keys=True) + "\n")
    return str(output)


def report_and_return(args: dict, prior: dict, output: str) -> dict:
    """Print the native success report, returning only after printing succeeds."""
    result = {
        "ok": True,
        "output": str(output),
        "model_id": prior["model_id"],
        "metric_count": len(prior["metrics"]),
        "phase_count": len(prior["phases"]),
    }
    if args["json"]:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"Wrote {output}")
    return {"result": result, "exit_code": 0}


def main() -> int:
    """Parse, construct, write and report once using the shared native steps."""
    args = parse_arguments()
    prior = construct_prior(args)
    output = persist_prior(args, prior)
    return report_and_return(args, prior, output)["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
