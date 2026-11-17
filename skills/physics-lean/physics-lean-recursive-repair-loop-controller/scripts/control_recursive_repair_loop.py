#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Keep recursive Lean physics pathology repair bounded, monotonic, and visible.
#
# Intent:
#   Decide whether an exhaustive expansion map may start another repair
#   iteration, is complete, or must block for repeated state or limits.
#
# Function:
#   Emits a recursion control plan with decision, next actions, invariants,
#   stopping criteria, and required gates.
#
# Maintenance Notes:
#   Keep accepted expansion statuses synchronized with the cartographer.

"""Control recursive Lean physics pathology repair loops."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

RECURSION_INVARIANTS = [
    "MathformerPhysicsLib-first object work precedes target theorem edits.",
    "Candidate workbench text is not accepted support until promotion and compile evidence exist.",
    "Generative repair is advisory until deterministic gates rerun.",
    "Every new object, assumption, generated support, and target edit re-enters the expansion map.",
    "A repeated iteration signature blocks instead of recursing silently.",
]

REQUIRED_RECURSION_GATES = [
    "critique.physics_lean_drift_pathology_monitor",
    "repair.physics_math_object_detect",
    "repair.mathformerphysicslib_object_workbench",
    "repair.physics_lean_pathology_loop",
    "repair.physics_lean_generative_repair",
    "repair.physics_lean_repair_expansion_cartography",
    "repair.physics_lean_recursive_repair_control",
    "consistency.physics_lean_report",
]


def load_json(path: Path | None) -> dict[str, Any]:
    """Load optional JSON."""
    if path is None:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_many(paths: Sequence[Path]) -> list[dict[str, Any]]:
    """Load multiple JSON objects."""
    return [load_json(path) for path in paths]


def frontier_to_actions(frontier: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert expansion frontier items into ordered actions."""
    actions = []
    for index, item in enumerate(frontier, 1):
        actions.append(
            {
                "order": index,
                "node_id": item.get("node_id"),
                "owner_skill": item.get("owner_skill"),
                "action": item.get("action"),
                "blockers": item.get("blockers", []),
            }
        )
    return actions


def previous_signatures(previous_expansion_maps: list[dict[str, Any]]) -> list[str]:
    """Collect prior iteration signatures."""
    signatures = []
    for expansion in previous_expansion_maps:
        signature = expansion.get("iteration_signature")
        if signature:
            signatures.append(str(signature))
    return signatures


def prepare_state(
    *,
    expansion_map: dict[str, Any],
    previous_expansion_maps: list[dict[str, Any]],
    iteration: int,
    max_iterations: int,
) -> dict[str, Any]:
    """Carry caller state and expose the ordered decision predicates.

    Keep outstanding nodes and frontier unchanged until assembly: the native
    planner projects frontier actions before computing the outstanding count.
    """
    signature = str(expansion_map.get("iteration_signature", "missing"))
    prior_signatures = previous_signatures(previous_expansion_maps)
    outstanding = expansion_map.get("outstanding_nodes", [])
    frontier = expansion_map.get("next_frontier", [])
    expansion_status = str(expansion_map.get("status", "missing"))
    exhaustive = bool(expansion_map.get("exhaustive", False))
    initial_complete = (
        expansion_status in {"complete", "not_required"} and not outstanding
    )
    non_exhaustive = not exhaustive
    repeated = (
        not initial_complete and not non_exhaustive and signature in prior_signatures
    )
    cap_reached = (
        not initial_complete
        and not non_exhaustive
        and not repeated
        and iteration >= max_iterations
    )
    return {
        "iteration": iteration,
        "max_iterations": max_iterations,
        "signature": signature,
        "prior_signatures": prior_signatures,
        "outstanding_nodes": outstanding,
        "frontier": frontier,
        "expansion_status": expansion_status,
        "initial_complete": initial_complete,
        "non_exhaustive": non_exhaustive,
        "repeated": repeated,
        "cap_reached": cap_reached,
        "empty": not outstanding,
    }


def select_branch(*, state: dict[str, Any], branch: str) -> dict[str, Any]:
    """Apply one selected decision assignment, without running any repair."""
    blockers: list[str] = []
    if branch in {"complete", "recurse"}:
        decision = branch
    elif branch == "non_exhaustive":
        decision = "blocked"
        blockers.append("expansion_map_not_exhaustive")
    elif branch == "repeated":
        decision = "blocked"
        blockers.append(f"repeated_iteration_signature:{state['signature']}")
    elif branch == "iteration_cap":
        decision = "blocked"
        blockers.append(f"max_iterations_reached:{state['max_iterations']}")
    else:
        raise ValueError(f"Unknown recursive control branch: {branch}")
    return {"decision": decision, "blockers": blockers}


def finish_plan(*, state: dict[str, Any], selection: dict[str, Any]) -> dict[str, Any]:
    """Apply the final blocked override and return native policy and actions."""
    expansion_status = state["expansion_status"]
    frontier = state["frontier"]
    signature = state["signature"]
    prior_signatures = state["prior_signatures"]
    iteration = state["iteration"]
    max_iterations = state["max_iterations"]
    decision = selection["decision"]
    blockers = list(selection["blockers"])
    if expansion_status == "blocked":
        decision = "blocked"
        blockers.append("expansion_map_blocked")

    next_actions = frontier_to_actions(frontier) if decision == "recurse" else []
    if decision == "blocked" and frontier:
        next_actions = frontier_to_actions(frontier)

    return {
        "style": "physics_lean_recursive_repair_control_plan",
        "status": decision,
        "decision": decision,
        "iteration": iteration,
        "max_iterations": max_iterations,
        "iteration_signature": signature,
        "prior_iteration_signatures": prior_signatures,
        "outstanding_node_count": len(state["outstanding_nodes"]),
        "blockers": sorted(set(blockers)),
        "next_actions": next_actions,
        "loop_policy": {
            "recursive": True,
            "exhaustive_expansion_required": True,
            "stop_on_repeated_signature": True,
            "stop_on_iteration_cap": True,
            "target_theorem_edits_allowed_only_when": "expansion map has no library-first object blockers and pathology loop allows target refinement",
        },
        "required_rerun_gates": REQUIRED_RECURSION_GATES,
        "recursion_invariants": RECURSION_INVARIANTS,
    }


def build_control_plan(
    *,
    expansion_map: dict[str, Any],
    previous_expansion_maps: list[dict[str, Any]],
    iteration: int,
    max_iterations: int,
) -> dict[str, Any]:
    """Build one recursive control plan using the shared native steps."""
    state = prepare_state(
        expansion_map=expansion_map,
        previous_expansion_maps=previous_expansion_maps,
        iteration=iteration,
        max_iterations=max_iterations,
    )
    if state["initial_complete"]:
        branch = "complete"
    elif state["non_exhaustive"]:
        branch = "non_exhaustive"
    elif state["repeated"]:
        branch = "repeated"
    elif state["cap_reached"]:
        branch = "iteration_cap"
    elif state["empty"]:
        branch = "complete"
    else:
        branch = "recurse"
    return finish_plan(state=state, selection=select_branch(state=state, branch=branch))


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expansion-map", type=Path)
    parser.add_argument(
        "--previous-expansion-map", type=Path, action="append", default=[]
    )
    parser.add_argument("--iteration", type=int, default=1)
    parser.add_argument("--max-iterations", type=int, default=6)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run recursion control."""
    args = parse_args(argv)
    if args.self_test:
        expansion = {
            "style": "physics_lean_repair_expansion_map",
            "status": "needs_expansion",
            "exhaustive": True,
            "iteration_signature": "abc123",
            "outstanding_nodes": [{"id": "workbench.commutator"}],
            "next_frontier": [
                {
                    "node_id": "workbench.commutator",
                    "owner_skill": "mathformerphysicslib-object-workbench",
                    "action": "work_object_in_mathformerphysicslib_then_rerun_workbench",
                    "blockers": ["library_object_not_ready:commutator:reuse_candidate"],
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
        plan = build_control_plan(
            expansion_map=load_json(args.expansion_map),
            previous_expansion_maps=load_many(args.previous_expansion_map),
            iteration=args.iteration,
            max_iterations=args.max_iterations,
        )
    output = json.dumps(plan, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
