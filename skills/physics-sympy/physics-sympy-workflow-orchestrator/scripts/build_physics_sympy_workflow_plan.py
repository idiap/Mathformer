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

"""Build a deterministic enriched SymPy physics workflow plan."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[4]
REASONING_LOG_SCRIPTS = (
    REPO_ROOT / "skills" / "control" / "reasoning-log-schema-guardian" / "scripts"
)
if str(REASONING_LOG_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(REASONING_LOG_SCRIPTS))
try:
    from reasoning_log import append_reasoning_log_entry
except Exception:  # pragma: no cover - logging remains optional.
    append_reasoning_log_entry = None

STYLE = "sympy_physics_derivation_trace"

REQUIRED_HOOKS = [
    "physics.sympy.goal_sample.plan",
    "physics.sympy.source_only.run",
    "physics.dependencies.probe",
    "physics.source.extract",
    "physics.informal.elicit",
    "physics.informal.expand",
    "physics.informal.review",
    "physics.symbols.build",
    "physics.dimensions.model",
    "physics.units.ground",
    "physics.equations.parse",
    "physics.regimes.model",
    "physics.frames.build",
    "physics.gaps.detect",
    "physics.gaps.expand",
    "physics.laws.ground",
    "physics.sympy.library_grounding.build",
    "physics.sympy.workflow.plan",
    "physics.sympy.equation_surface.build",
    "physics.sympy.assumptions.encode",
    "draft.physics_sympy_derivation",
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
    "refine.physics_sympy_review",
    "physics.sympy.repair_expansion.map",
    "physics.sympy.recursive_repair.control",
    "physics.sympy.grounded_sample.thoroughness",
    "consistency.physics_derivation_report",
]

RECOMMENDED_HOOKS = [
    "critique.physics_sympy_generative_panel",
    "reflection.physics_sympy_formal_answer_compare",
    "critique.reference_free_monitor",
    "evaluation.rfde_report",
]


def read_source(path: Path | None, text: str | None) -> tuple[str, str]:
    """Document the responsibility of ``read_source``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if text is not None:
        return text, "inline"
    if path is not None:
        return path.read_text(encoding="utf-8"), str(path)
    return "", "unspecified"


def build_plan(source: str, source_ref: str, case_id: str) -> dict[str, Any]:
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
    return {
        "style": "physics_sympy_workflow_plan",
        "backend_style": STYLE,
        "case_id": case_id,
        "source_ref": source_ref,
        "source_sha256": (
            hashlib.sha256(source.encode("utf-8")).hexdigest() if source else None
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "required_hooks": REQUIRED_HOOKS,
        "recommended_hooks": RECOMMENDED_HOOKS,
        "equational_scope": {
            "allowed": [
                "source-anchored equations",
                "generated bridge equations",
                "SymPy transformation certificates",
                "installed SymPy/dependency API grounding packets",
                "unit and dimension validators",
                "numeric sanity and counterexample probes",
            ],
            "not_allowed_as_complete": [
                "target equation copied as input",
                "unconnected scalar algebra for dimensioned physics",
                "silent assumption strengthening",
                "unlabeled vector, field, or frame erasure",
            ],
        },
        "protected_evidence": [
            "source anchors",
            "quantity surface",
            "equation graph nodes",
            "SymPy library grounding roles and selected APIs",
            "projection bridges",
            "assumption labels",
            "unit and dimension reports",
            "step certificates",
            "numeric domains",
            "final review findings",
            "design-guard semantic-preservation findings",
            "one-sample recursive goal evidence",
            "source-only recursive run report",
            "SymPy repair expansion map and controller decision",
            "grounded sample thoroughness gate",
            "RFDE trajectory metrics",
            "duration and agent-usage cost trace",
        ],
        "refinement_order": [
            "dependency_import",
            "parse_symbol_binding",
            "assumption_context",
            "unit_dimension",
            "projection_bridge",
            "law_grounding",
            "sympy_library_grounding",
            "transformation_residual",
            "numeric_domain",
            "equational_semantics",
            "final_review",
        ],
        "formal_answer_policy": {
            "status": "inspiration_only_not_benchmark",
            "timing": "after an informal-first SymPy candidate, blocker report, or consistency report exists",
            "forbidden_use": "do not inspect withheld formal_answer before first-pass SymPy drafting or blocker reporting",
            "allowed_use": [
                "extract theorem-shape inspiration",
                "extract assumption or law decomposition inspiration",
                "identify projection or side-condition gaps",
            ],
            "required_route_for_changes": "review.physics_sympy_final_equations -> refine.physics_sympy_review",
        },
        "rfde_trajectory_reporting": {
            "required_report": "consistency.physics_derivation_report",
            "recommended_hooks": [
                "critique.reference_free_monitor",
                "evaluation.rfde_report",
            ],
            "tracked_surfaces": [
                "phase13_reference_free_physics_consistency_report",
                "physics_rfde_metrics",
                "packet_inventory",
                "critical_blockers",
                "completion_semantics",
            ],
            "phase_transition_policy": "report metric changes and blockers across source, grounding, execution, validation, review, and consistency cycles",
        },
        "cost_accounting": {
            "required_payload_fields": ["duration_ms", "agent_usage"],
            "scope": "all required hooks in sympy_physics_derivation_trace_loop",
            "policy": "cost traces are preserved as audit evidence and interpreted with RFDE trajectory reports",
        },
        "sympy_library_grounding_policy": {
            "status": "maximal_installed_library_first",
            "minimum_complete_level": "high",
            "required_packet": "physics_sympy_library_grounding_packet",
            "preferred_surfaces": [
                "sympy.core / simplify / polys / solvers for scalar algebra",
                "sympy.diff, integrate, Derivative, Integral, dsolve for calculus",
                "sympy.physics.units Quantity, Dimension, SI, quantity_simplify for units",
                "sympy.vector and sympy.physics.vector for vector/field/curl/divergence roles",
                "sympy.physics.mechanics for Lagrangian, frame, particle, or dynamics roles",
                "sympy.matrices for finite linear-algebra/operator surrogates",
                "sympy.physics.quantum for TDSE/operator/bra-ket roles when present",
                "sympy.N, lambdify, mpmath, and numpy for numeric validation",
            ],
            "complete_status_blocks": [
                "case-required role missing from installed API inventory",
                "unit/dimension claims represented only by local dictionaries when SymPy units are available",
                "vector/field/mechanics/operator erasure without explicit projection bridge and library role",
                "trace certificate lacks API role or executable algebraic certificate",
            ],
        },
        "status": "ready",
    }


def rel(path: Path) -> str:
    """Return a repository-relative display path when possible."""
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def append_workflow_event(
    reasoning_log: Path | None, plan: dict[str, Any], output_path: Path | None
) -> None:
    """Append a concise workflow-plan reasoning-log event when requested."""
    if reasoning_log is None or append_reasoning_log_entry is None:
        return
    case_id = str(plan.get("case_id", "unspecified"))
    append_reasoning_log_entry(
        reasoning_log,
        step="physics_sympy_workflow_plan_complete",
        payload={
            "skill": "physics-sympy-workflow-orchestrator",
            "hook_id": "physics.sympy.workflow.plan",
            "goal_id": f"sympy:{case_id}:workflow_plan",
            "case_id": case_id,
            "stage": "physics_sympy_workflow_plan_complete",
            "status": plan.get("status"),
            "evidence": {
                "required_hook_count": len(plan.get("required_hooks", [])),
                "recommended_hook_count": len(plan.get("recommended_hooks", [])),
                "source_ref": plan.get("source_ref"),
            },
            "artifacts": {"output": None if output_path is None else rel(output_path)},
            "decision": {
                "status": plan.get("status"),
                "required_hooks": plan.get("required_hooks", []),
            },
            "risks": plan.get("equational_scope", {}).get(
                "not_allowed_as_complete", []
            ),
            "next_action": "run the one-sample source-only SymPy recursive gate sequence",
        },
    )


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
    parser.add_argument("--source-file", type=Path)
    parser.add_argument("--source-text")
    parser.add_argument("--case-id", default="unspecified")
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
        plan = build_plan("derive F = m*a from Newton's law", "self-test", "case")
        assert plan["status"] == "ready"
        assert "physics.sympy.library_grounding.build" in plan["required_hooks"]
        assert "physics.sympy.design_guard.review" in plan["required_hooks"]
        assert "physics.sympy.grounded_sample.thoroughness" in plan["required_hooks"]
        assert (
            plan["sympy_library_grounding_policy"]["minimum_complete_level"] == "high"
        )
        assert "physics.sympy.equation_surface.build" in plan["required_hooks"]
        assert (
            plan["formal_answer_policy"]["status"] == "inspiration_only_not_benchmark"
        )
        assert "evaluation.rfde_report" in plan["recommended_hooks"]
        assert plan["cost_accounting"]["required_payload_fields"] == [
            "duration_ms",
            "agent_usage",
        ]
    else:
        source, ref = read_source(args.source_file, args.source_text)
        plan = build_plan(source, ref, args.case_id)
    output = json.dumps(plan, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    append_workflow_event(args.reasoning_log, plan, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
