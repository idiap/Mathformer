# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""JSON/MCP ports for the native workflow.router coverage route.

Only registry projections are accepted: executable argv stays source-owned.
The coverage audit reads definitions without executing referenced workflows. No
timeout cap is added; Lunar enforces the descriptor's enclosing budget.
"""

from dataclasses import asdict
import json
from pathlib import Path
from typing import Literal
from typing_extensions import TypedDict

import mathformer as hub
from adoption_check_tools import Context


class State(TypedDict):
    ok: bool
    children: list[dict]


class Initialized(TypedDict):
    state: State


class Invoked(TypedDict):
    child: dict


class Advanced(Initialized):
    done: bool


class Finished(TypedDict):
    result: dict


ACTION = "control:workflow-router-coverage"
ROUTE = "workflow.router"
ActionId = Literal["control:workflow-router-coverage"]


class Selected(TypedDict):
    action_id: ActionId


def selected_match(match):
    """Restore native route metadata, rejecting changes to the declaration."""
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


def checked_registry(projection):
    """Deserialize capabilities, retaining native unknown-action behavior."""
    native = hub.build_registry()
    item = native[ACTION]
    if (
        item.safety != "read_only"
        or item.writes
        or item.depends_on
        or item.command
        != (
            "{python}",
            "skills/control/mathformer-workflow-router/scripts/route_mathformer_workflow.py",
            "--audit-coverage",
            "--json",
        )
        or item.timeout_seconds is not None
        or item.allows_extra_args
    ):
        raise ValueError("workflow router capability changed; requalify the binding")
    if any(
        key not in native or value != hub.action_to_dict(native[key])
        for key, value in projection.items()
    ):
        raise ValueError("registry projection differs from the native declaration")
    return {key: native[key] for key in projection}


def check_state(state, *, selecting=False):
    count = len(state["children"])
    if count > 1 or (selecting and count != 0):
        raise ValueError("route cursor is out of bounds")
    if state["ok"] != all(bool(child.get("ok", False)) for child in state["children"]):
        raise ValueError("inconsistent route accumulator")


def register_workflow_router_route_tools(mcp):
    @mcp.tool()
    def mathformer_workflow_router_initialize() -> Initialized:
        return {"state": hub.initialize_intent_state()}

    @mcp.tool()
    def mathformer_workflow_router_select(state: State, match: dict) -> Selected:
        check_state(state, selecting=True)
        return {"action_id": hub.select_intent_action(state, selected_match(match))}

    @mcp.tool()
    def mathformer_workflow_router_execute(
        action_id: ActionId,
        registry: dict,
        context: Context,
        repository_root: str | None = None,
    ) -> Invoked:
        if action_id != ACTION:
            raise ValueError("action is outside the selected route")
        root = (
            hub.REPO_ROOT
            if repository_root is None
            else Path(repository_root).resolve()
        )
        return {
            "child": hub.run_action(
                action_id,
                checked_registry(registry),
                hub.RunContext(**context),
                repository_root=root,
            )
        }

    @mcp.tool()
    def mathformer_workflow_router_advance(
        state: State, child: dict, context: Context, match: dict
    ) -> Advanced:
        check_state(state, selecting=True)
        updated, done = hub.advance_intent_state(
            state,
            child,
            hub.RunContext(**context),
            len(selected_match(match).route.action_ids),
        )
        return {"state": updated, "done": done}

    @mcp.tool()
    def mathformer_workflow_router_finish(
        state: State, match: dict, registry: dict
    ) -> Finished:
        check_state(state)
        if len(state["children"]) != 1:
            raise ValueError("route completion requires exactly one observation")
        return {
            "result": hub.finish_intent_state(
                state, selected_match(match), checked_registry(registry)
            )
        }
