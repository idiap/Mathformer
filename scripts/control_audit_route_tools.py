# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable ports for control.audit's shared native route/dependency controller.

Registry projections select source declarations; they never supply executable
code. This binding retains the native CLI timeouts (including None), rather
than the separate mathformer_ask service timeout override. Lunar owns its own
wall time and call ceilings. Leaf output and write audits remain source-owned.
"""

from dataclasses import asdict
import json
from pathlib import Path
from typing_extensions import TypedDict

import mathformer as hub
from adoption_check_tools import (
    Context,
    Admission,
    State,
    Admitted,
    Initialized,
    Advanced,
    Finished,
)
from benchmark_route_tools import State as RouteState

ACTION = "control:all"
ROUTE = "control.audit"
DEPENDENCIES = (
    "hub:audit",
    "control:thematic-layout",
    "control:workflow-contract",
    "control:reasoning-flow-language",
    "control:reasoning-flow-catalog",
    "control:skill-coverage",
    "control:reasoning-log-coverage",
    "control:reasoning-log-smoke",
    "repo:diff-check",
)


class RouteInitialized(TypedDict):
    state: RouteState


class Visited(TypedDict):
    child: dict


class Carried(TypedDict):
    state: State
    done: bool
    result: dict


def checked_registry(projection):
    """Resolve native code only; retain missing-action behavior for subsets."""
    native = hub.build_registry()
    parent = native[ACTION]
    if parent.depends_on != DEPENDENCIES or parent.command:
        raise ValueError("control:all changed; regenerate its bounded contract")
    for key in (ACTION, *DEPENDENCIES):
        item = native[key]
        if (
            item.safety != "read_only"
            or item.writes
            or (key != ACTION and item.depends_on)
        ):
            raise ValueError("control audit capability changed; requalify the binding")
    if any(
        key not in (ACTION, *DEPENDENCIES) or value != hub.action_to_dict(native[key])
        for key, value in projection.items()
    ):
        raise ValueError("registry projection differs from the native declaration")
    return {key: native[key] for key in projection}


def selected_match(match):
    route = next(row for row in hub.build_intent_routes() if row.route_id == ROUTE)
    native = json.loads(json.dumps(asdict(route)))
    projected = match["route"]
    if (
        route.action_ids != (ACTION,)
        or not {"route_id", "action_ids"} <= projected.keys()
        or any(
            key not in native or value != native[key]
            for key, value in projected.items()
        )
    ):
        raise ValueError("selected route differs from the native declaration")
    return hub.IntentMatch(route, match["score"], tuple(match["matched_terms"]))


def check_state(state, *, visiting=False):
    """Reject invalid wire cursors without changing valid native transitions."""
    index = state["index"]
    if not 0 <= index <= len(DEPENDENCIES) or (visiting and index == len(DEPENDENCIES)):
        raise ValueError("dependency cursor is out of bounds")
    if index != len(state["children"]) or state["dependencies_ok"] != all(
        bool(child.get("ok", False)) for child in state["children"]
    ):
        raise ValueError("inconsistent dependency accumulator")
    if ACTION not in state["ancestry"] or state["ancestry"] != sorted(
        set(state["ancestry"])
    ):
        raise ValueError("invalid dependency ancestry")


def register_control_audit_route_tools(mcp):
    """Bind each graph step to the exact implementation used by the CLI."""

    @mcp.tool()
    def mathformer_control_audit_initialize_route() -> RouteInitialized:
        return {"state": hub.initialize_intent_state()}

    @mcp.tool()
    def mathformer_control_audit_admit(
        registry: dict, extra_args: list[str], seen: list[str]
    ) -> Admitted:
        return {
            "admission": hub.admit_action(
                ACTION, checked_registry(registry), extra_args, seen
            )
        }

    @mcp.tool()
    def mathformer_control_audit_initialize_dependencies(
        admission: Admission,
    ) -> Initialized:
        if not admission["accepted"] or admission["status"] != "accepted":
            raise ValueError("dependency initialization requires admission")
        return {"state": hub.initialize_dependencies(admission)}

    @mcp.tool()
    def mathformer_control_audit_visit(
        state: State, context: Context, registry: dict, repository_root: str | None
    ) -> Visited:
        native = checked_registry(registry)
        check_state(state, visiting=True)
        root = (
            hub.REPO_ROOT
            if repository_root is None
            else Path(repository_root).resolve()
        )
        return {
            "child": hub.visit_dependency(
                native[ACTION],
                native,
                hub.RunContext(**context),
                state,
                repository_root=root,
            )
        }

    @mcp.tool()
    def mathformer_control_audit_advance(
        state: State, child: dict, context: Context, registry: dict
    ) -> Advanced:
        check_state(state, visiting=True)
        updated, done = hub.advance_dependencies(
            checked_registry(registry)[ACTION], state, child, hub.RunContext(**context)
        )
        return {"state": updated, "done": done}

    @mcp.tool()
    def mathformer_control_audit_finish_dependencies(
        state: State, registry: dict
    ) -> Finished:
        check_state(state)
        if not state["index"]:
            raise ValueError("sequence requires at least one dependency observation")
        return {
            "result": hub.finish_dependencies(checked_registry(registry)[ACTION], state)
        }

    @mcp.tool()
    def mathformer_control_audit_reject(admission: Admission) -> Finished:
        if admission["accepted"] or admission["status"] == "accepted":
            raise ValueError("rejection requires failed admission")
        return {"result": hub.reject_action(ACTION, admission)}

    @mcp.tool()
    def mathformer_control_audit_carry(state: State, result: dict) -> Carried:
        """Transport rejection past Lunar's root loop; invoke no native step."""
        return {"state": state, "done": True, "result": result}

    @mcp.tool()
    def mathformer_control_audit_finish_route(
        state: RouteState, child: dict, context: Context, match: dict, registry: dict
    ) -> Finished:
        if state != hub.initialize_intent_state():
            raise ValueError("single-action route requires the initial accumulator")
        updated, _done = hub.advance_intent_state(
            state, child, hub.RunContext(**context), 1
        )
        return {
            "result": hub.finish_intent_state(
                updated, selected_match(match), checked_registry(registry)
            )
        }
