#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Keep recursive SymPy physics repair bounded, monotonic, and visible.
#
# Intent:
#   Decide whether an exhaustive SymPy expansion map may start another repair
#   iteration, is complete, or must block for repeated state or limits.
#
# Function:
#   Emits a recursion control plan with decision, next actions, invariants,
#   stopping criteria, and required gates.
#
# Maintenance Notes:
#   Keep accepted expansion statuses synchronized with the SymPy repair
#   cartographer.

"""Control recursive SymPy physics repair loops."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[4]
CARTOGRAPHER = (
    REPO_ROOT
    / "skills"
    / "physics-sympy"
    / "physics-sympy-repair-expansion-cartographer"
    / "scripts"
    / "map_physics_sympy_repair_expansion.py"
)
REASONING_LOG_SCRIPTS = (
    REPO_ROOT / "skills" / "control" / "reasoning-log-schema-guardian" / "scripts"
)
if str(REASONING_LOG_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(REASONING_LOG_SCRIPTS))

try:
    from reasoning_log import append_reasoning_log_entry
except (
    Exception
):  # pragma: no cover - helper absence is reported as a skipped optional write.
    append_reasoning_log_entry = None

RECURSION_INVARIANTS = [
    "One FormalPhysics SymPy case is locked until complete, blocked, or explicitly handed off.",
    "Source commentary and SymPy alignment are repaired before target-shape edits.",
    "Installed SymPy/dependency API grounding is preserved or improved, never silently weakened.",
    "Generated support remains labeled and may not masquerade as source evidence.",
    "Target-shaped inputs, hidden expected answers, and post-hoc formal_answer leakage block completion.",
    "Every repair re-enters the goal planner, expansion map, controller, and affected SymPy validators.",
    "A repeated iteration signature blocks instead of recursing silently.",
]

REQUIRED_RECURSION_GATES = [
    "physics.sympy.goal_sample.plan",
    "physics.sympy.repair_expansion.map",
    "physics.sympy.recursive_repair.control",
    "physics.sympy.library_grounding.build",
    "execute.physics_sympy_derivation",
    "execute.physics_sympy_interpret",
    "physics.units.verify",
    "physics.steps.verify",
    "physics.numeric.sample",
    "critique.physics_sympy_semantics",
    "critique.physics_sympy_dimensions",
    "review.physics_sympy_final_equations",
    "review.mathematical_sympy_final_equations",
    "refine.physics_sympy_review",
    "consistency.physics_derivation_report",
]


def load_json(path: Path | None) -> dict[str, Any]:
    """Load optional JSON."""
    if path is None:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_many(paths: Sequence[Path]) -> list[dict[str, Any]]:
    """Load multiple JSON objects."""
    return [load_json(path) for path in paths]


def run_cartographer(case_id: str) -> dict[str, Any]:
    """Build an expansion map for a case when no map file is supplied."""
    proc = subprocess.run(
        [sys.executable, str(CARTOGRAPHER), "--case", case_id, "--json"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=300,
    )
    return cartographer_result(case_id, proc)


def cartographer_result(
    case_id: str, proc: subprocess.CompletedProcess
) -> dict[str, Any]:
    """Interpret the native cartographer subprocess result without changing failures."""
    try:
        parsed = json.loads(proc.stdout)
    except json.JSONDecodeError:
        parsed = {}
    if proc.returncode != 0 or not parsed:
        return {
            "style": "physics_sympy_repair_expansion_map",
            "backend": "sympy",
            "case_id": case_id,
            "status": "blocked",
            "exhaustive": False,
            "iteration_signature": "missing",
            "outstanding_nodes": [
                {
                    "id": f"{case_id}.trace_realness.cartographer_failed",
                    "owner_skill": "physics-sympy-repair-expansion-cartographer",
                    "blockers": ["cartographer_failed"],
                }
            ],
            "next_frontier": [],
            "cartographer_error": {
                "returncode": proc.returncode,
                "stdout_tail": proc.stdout[-2000:],
                "stderr_tail": proc.stderr[-2000:],
            },
        }
    return parsed


def previous_signatures(previous_expansion_maps: Sequence[dict[str, Any]]) -> list[str]:
    """Collect prior iteration signatures."""
    signatures = []
    for expansion in previous_expansion_maps:
        signature = expansion.get("iteration_signature")
        if signature:
            signatures.append(str(signature))
    return signatures


def frontier_to_actions(frontier: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert expansion frontier items into ordered actions."""
    actions = []
    for index, item in enumerate(frontier, start=1):
        actions.append(
            {
                "order": index,
                "node_id": item.get("node_id"),
                "owner_skill": item.get("owner_skill"),
                "repair_surface": item.get("repair_surface"),
                "action": item.get("action"),
                "blockers": item.get("blockers", []),
            }
        )
    return actions


def load_state(
    request: dict[str, Any], working_directory: Path | None = None
) -> dict[str, Any]:
    """Load the current map before caller history, as in the CLI entrypoint."""
    request = dict(request)
    for key in ("expansion_map", "output", "reasoning_log"):
        if request.get(key) is not None:
            path = Path(request[key])
            request[key] = str(
                working_directory / path
                if working_directory is not None and not path.is_absolute()
                else path
            )
    paths = [Path(path) for path in request.get("previous_expansion_maps", [])]
    if working_directory is not None:
        paths = [
            path if path.is_absolute() else working_directory / path for path in paths
        ]
    request["previous_expansion_maps"] = [str(path) for path in paths]
    if request.get("expansion_map"):
        expansion = load_json(Path(request["expansion_map"]))
    elif request.get("case"):
        expansion = run_cartographer(request["case"])
    else:
        raise ValueError("provide --expansion-map or --case")
    return {
        "request": request,
        "expansion_map": expansion,
        "previous_expansion_maps": load_many(paths),
        "iteration": request.get("iteration", 1),
        "max_iterations": request.get("max_iterations", 6),
    }


def compute_guards(state: dict[str, Any]) -> dict[str, bool]:
    """Prepare native predicates in order, preserving early comparison bypasses."""
    expansion_map = state["expansion_map"]
    previous_expansion_maps = state["previous_expansion_maps"]
    iteration, max_iterations = state["iteration"], state["max_iterations"]
    signature = str(expansion_map.get("iteration_signature", "missing"))
    prior_signatures = previous_signatures(previous_expansion_maps)
    outstanding = expansion_map.get("outstanding_nodes", [])
    _frontier = expansion_map.get("next_frontier", [])
    expansion_status = str(expansion_map.get("status", "missing"))
    exhaustive = bool(expansion_map.get("exhaustive", False))
    early_complete = (
        expansion_status in {"complete", "not_required"} and not outstanding
    )
    non_exhaustive = not exhaustive
    repeated = signature in prior_signatures
    # The native comparison is reached only after the first three checks.
    at_cap = (
        not (early_complete or non_exhaustive or repeated)
        and iteration >= max_iterations
    )
    return dict(
        early_complete=early_complete,
        non_exhaustive=non_exhaustive,
        repeated=repeated,
        at_cap=at_cap,
        empty=not outstanding,
    )


def choose_branch(guards: dict[str, bool]) -> str:
    """Select the first native stopping condition, without an internal loop."""
    for predicate, branch in (
        ("early_complete", "complete"),
        ("non_exhaustive", "non_exhaustive"),
        ("repeated", "repeated"),
        ("at_cap", "at_cap"),
        ("empty", "complete"),
    ):
        if guards[predicate]:
            return branch
    return "recurse"


def finish_plan(state: dict[str, Any], branch: str) -> dict[str, Any]:
    """Apply one branch and the final blocked override, then project the frontier."""
    expansion_map = state["expansion_map"]
    previous_expansion_maps = state["previous_expansion_maps"]
    iteration, max_iterations = state["iteration"], state["max_iterations"]
    signature = str(expansion_map.get("iteration_signature", "missing"))
    prior_signatures = previous_signatures(previous_expansion_maps)
    outstanding = expansion_map.get("outstanding_nodes", [])
    frontier = expansion_map.get("next_frontier", [])
    expansion_status = str(expansion_map.get("status", "missing"))
    _exhaustive = bool(expansion_map.get("exhaustive", False))
    blockers: list[str] = []
    if branch in {"complete", "recurse"}:
        decision = branch
    elif branch == "non_exhaustive":
        decision = "blocked"
        blockers.append("expansion_map_not_exhaustive")
    elif branch == "repeated":
        decision = "blocked"
        blockers.append(f"repeated_iteration_signature:{signature}")
    elif branch == "at_cap":
        decision = "blocked"
        blockers.append(f"max_iterations_reached:{max_iterations}")
    else:
        raise ValueError(f"Unknown control branch: {branch}")

    if expansion_status == "blocked":
        decision = "blocked"
        blockers.append("expansion_map_blocked")

    next_actions = (
        frontier_to_actions(frontier) if decision in {"recurse", "blocked"} else []
    )
    return {
        "style": "physics_sympy_recursive_repair_control_plan",
        "backend": "sympy",
        "case_id": expansion_map.get("case_id", "unknown"),
        "status": decision,
        "decision": decision,
        "iteration": iteration,
        "max_iterations": max_iterations,
        "iteration_signature": signature,
        "prior_iteration_signatures": prior_signatures,
        "outstanding_node_count": len(outstanding),
        "blockers": sorted(set(blockers)),
        "next_actions": next_actions,
        "loop_policy": {
            "recursive": True,
            "exhaustive_expansion_required": True,
            "stop_on_repeated_signature": True,
            "stop_on_iteration_cap": True,
            "target_artifact_edits_allowed_only_when": "the next frontier names a local SymPy repair surface and all source/commentary/frontier-preservation invariants are preserved",
        },
        "required_rerun_gates": REQUIRED_RECURSION_GATES,
        "recursion_invariants": RECURSION_INVARIANTS,
        "sympy_only_boundary": {
            "forbidden_backend_workflows": [
                "physics_lean",
                "lean_physics_derivation_trace_loop",
            ],
        },
    }


def build_control_plan(
    *,
    expansion_map: dict[str, Any],
    previous_expansion_maps: Sequence[dict[str, Any]],
    iteration: int,
    max_iterations: int,
) -> dict[str, Any]:
    """Build one plan using the same stages exposed to workflow callers."""
    state = dict(
        expansion_map=expansion_map,
        previous_expansion_maps=previous_expansion_maps,
        iteration=iteration,
        max_iterations=max_iterations,
    )
    return finish_plan(state, choose_branch(compute_guards(state)))


def append_decision_event(reasoning_log: Path | None, plan: dict[str, Any]) -> None:
    """Append the controller decision to a reasoning-log JSONL file when asked."""
    if reasoning_log is None or append_reasoning_log_entry is None:
        return
    append_reasoning_log_entry(
        reasoning_log,
        step="physics_sympy_recursive_repair_control_complete",
        payload={
            "skill": "physics-sympy-recursive-repair-loop-controller",
            "hook_id": "physics.sympy.recursive_repair.control",
            "case_id": plan.get("case_id"),
            "status": plan.get("status"),
            "decision": plan.get("decision"),
            "iteration_signature": plan.get("iteration_signature"),
            "outstanding_node_count": plan.get("outstanding_node_count"),
            "blockers": plan.get("blockers", []),
            "next_action_count": len(plan.get("next_actions", [])),
            "artifacts": {},
            "risks": plan.get("blockers", []),
        },
    )


def emit_plan(
    plan: dict[str, Any], output_path: Path | None, reasoning_log: Path | None
) -> int:
    """Emit the native reasoning event before serialization and optional output."""
    append_decision_event(reasoning_log, plan)
    output = json.dumps(plan, ensure_ascii=False, indent=2)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case")
    parser.add_argument("--expansion-map", type=Path)
    parser.add_argument(
        "--previous-expansion-map", type=Path, action="append", default=[]
    )
    parser.add_argument("--iteration", type=int, default=1)
    parser.add_argument("--max-iterations", type=int, default=6)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--reasoning-log", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run recursion control."""
    args = parse_args(argv)
    if args.self_test:
        expansion = {
            "style": "physics_sympy_repair_expansion_map",
            "backend": "sympy",
            "case_id": "formalphysics_0000",
            "status": "needs_expansion",
            "exhaustive": True,
            "iteration_signature": "abc123",
            "outstanding_nodes": [{"id": "formalphysics_0000.sympy_api_grounding.001"}],
            "next_frontier": [
                {
                    "node_id": "formalphysics_0000.sympy_api_grounding.001",
                    "owner_skill": "physics-sympy-library-grounding-builder",
                    "repair_surface": "sympy_api_grounding",
                    "action": "ground required role in installed SymPy APIs",
                    "blockers": ["missing_sympy_library_surface:vector_analysis"],
                }
            ],
        }
        plan = build_control_plan(
            expansion_map=expansion,
            previous_expansion_maps=[],
            iteration=1,
            max_iterations=6,
        )
        assert plan["status"] == "recurse"
        repeated = build_control_plan(
            expansion_map=expansion,
            previous_expansion_maps=[{"iteration_signature": "abc123"}],
            iteration=2,
            max_iterations=6,
        )
        assert repeated["status"] == "blocked"
        assert "repeated_iteration_signature:abc123" in repeated["blockers"]
    else:
        if not args.expansion_map and not args.case:
            raise SystemExit("provide --expansion-map or --case")
        state = load_state(
            dict(
                case=args.case,
                expansion_map=str(args.expansion_map) if args.expansion_map else None,
                previous_expansion_maps=[
                    str(path) for path in args.previous_expansion_map
                ],
                iteration=args.iteration,
                max_iterations=args.max_iterations,
            )
        )
        plan = build_control_plan(
            **{
                key: state[key]
                for key in (
                    "expansion_map",
                    "previous_expansion_maps",
                    "iteration",
                    "max_iterations",
                )
            }
        )
    return emit_plan(plan, args.output, args.reasoning_log)


if __name__ == "__main__":
    raise SystemExit(main())
