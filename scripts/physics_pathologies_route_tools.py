# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP ports for the six-action native physics Lean pathology planning route.

The controller owns recursion, preflight, process output and write audits. These
ports retain native unbounded leaf timeouts; Lunar owns the descriptor budget.
Legacy ask/run_workflow service timeout caps remain at their original boundary.
"""

from dataclasses import asdict
import json
from pathlib import Path
from typing import Literal
from typing_extensions import TypedDict

import mathformer as hub
from adoption_check_tools import Context

ROUTE = "repair.physics.lean.pathologies"
ACTIONS = (
    "physics-lean:detect-pathology-objects",
    "physics-lean:object-workbench",
    "physics-lean:pathology-repair-loop",
    "physics-lean:generative-repair-plan",
    "physics-lean:repair-expansion-map",
    "physics-lean:recursive-repair-control",
)
ActionId = Literal[
    "physics-lean:detect-pathology-objects",
    "physics-lean:object-workbench",
    "physics-lean:pathology-repair-loop",
    "physics-lean:generative-repair-plan",
    "physics-lean:repair-expansion-map",
    "physics-lean:recursive-repair-control",
]


class State(TypedDict):
    ok: bool
    children: list[dict]


class Initialized(TypedDict):
    state: State


class Selected(TypedDict):
    action_id: ActionId


class Invoked(TypedDict):
    child: dict


class Advanced(TypedDict):
    state: State
    done: bool


class Finished(TypedDict):
    result: dict


def selected_match(match):
    """Restore source-owned route metadata, retaining NL scoring evidence."""
    route = next(row for row in hub.build_intent_routes() if row.route_id == ROUTE)
    native = json.loads(json.dumps(asdict(route)))
    projected = match["route"]
    if (
        route.action_ids != ACTIONS
        or not {"route_id", "action_ids"} <= projected.keys()
        or any(
            key not in native or value != native[key]
            for key, value in projected.items()
        )
    ):
        raise ValueError("selected route differs from the native declaration")
    return hub.IntentMatch(route, match["score"], tuple(match["matched_terms"]))


def checked_registry(projection):
    """Resolve projections to native capabilities; never accept caller code."""
    native = hub.build_registry()
    if any(
        key not in native or value != hub.action_to_dict(native[key])
        for key, value in projection.items()
    ):
        raise ValueError("registry projection differs from the native declaration")
    return {key: native[key] for key in projection}


def check_state(state, *, selecting=False):
    count = len(state["children"])
    if count > len(ACTIONS) or (selecting and count >= len(ACTIONS)):
        raise ValueError("route cursor is out of bounds")
    if state["ok"] != all(bool(child.get("ok", False)) for child in state["children"]):
        raise ValueError("inconsistent route accumulator")


def register_physics_pathologies_route_tools(mcp, authorize, path_allowed):
    @mcp.tool()
    def mathformer_physics_pathologies_route_initialize() -> Initialized:
        return {"state": hub.initialize_intent_state()}

    @mcp.tool()
    def mathformer_physics_pathologies_route_select(
        state: State, match: dict
    ) -> Selected:
        check_state(state, selecting=True)
        return {"action_id": hub.select_intent_action(state, selected_match(match))}

    @mcp.tool()
    def mathformer_physics_pathologies_route_run_child(
        action_id: ActionId,
        context: Context,
        registry: dict,
        repository_root: str | None,
    ) -> Invoked:
        if action_id not in ACTIONS:
            raise ValueError("action is outside the selected route")
        native = checked_registry(registry)
        root = (
            hub.REPO_ROOT
            if repository_root is None
            else Path(repository_root).resolve()
        )
        if not context["dry_run"] and action_id in native:
            authorize()
            # Qualify every reachable native write root, including alias children.
            pending, visited = [action_id], set()
            while pending:
                key = pending.pop()
                if key in visited or key not in native:
                    continue
                visited.add(key)
                item = native[key]
                if any(not path_allowed(root / path) for path in item.writes):
                    raise ValueError(
                        "pathology planner writes outside configured service roots"
                    )
                pending.extend(item.depends_on)
        return {
            "child": hub.run_action(
                action_id, native, hub.RunContext(**context), repository_root=root
            )
        }

    @mcp.tool()
    def mathformer_physics_pathologies_route_advance(
        state: State, child: dict, context: Context
    ) -> Advanced:
        check_state(state, selecting=True)
        updated, done = hub.advance_intent_state(
            state, child, hub.RunContext(**context), len(ACTIONS)
        )
        return {"state": updated, "done": done}

    @mcp.tool()
    def mathformer_physics_pathologies_route_finish(
        state: State, match: dict, registry: dict
    ) -> Finished:
        check_state(state)
        if not state["children"] or (
            len(state["children"]) < len(ACTIONS) and state["ok"]
        ):
            raise ValueError("route completion requires exhaustion or failed child")
        return {
            "result": hub.finish_intent_state(
                state, selected_match(match), checked_registry(registry)
            )
        }
