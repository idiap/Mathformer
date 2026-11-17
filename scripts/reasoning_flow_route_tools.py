# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable steps for the native selected ERFL validation route.

Wire registry values select source declarations, never executable caller code.
The native admission, argv, preflight, capture and write audit remain inside
run_action. In particular, its None subprocess timeouts are not service-capped;
the contract's wall time is a separate Lunar budget.
"""

from dataclasses import asdict
import json
from pathlib import Path
from typing import Literal
from typing_extensions import TypedDict

import mathformer as hub
from adoption_check_tools import Context
from benchmark_route_tools import State, Initialized, Invoked, Advanced, Finished

ROUTE = "control.reasoning.flow.language"
ACTIONS = ("control:reasoning-flow-language", "control:reasoning-flow-catalog")
ActionId = Literal["control:reasoning-flow-language", "control:reasoning-flow-catalog"]


class Selected(TypedDict):
    action_id: ActionId


def selected_match(match):
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
    native = hub.build_registry()
    for key in ACTIONS:
        item = native[key]
        if item.safety != "read_only" or item.writes or item.depends_on:
            raise ValueError("reasoning-flow capability changed; requalify the binding")
    if any(
        key not in ACTIONS or value != hub.action_to_dict(native[key])
        for key, value in projection.items()
    ):
        raise ValueError("registry projection differs from the native declaration")
    # Missing actions retain native unknown_action/metadata failure behavior.
    return {key: native[key] for key in projection}


def check_state(state, *, selecting=False):
    count = len(state["children"])
    if count > len(ACTIONS) or (selecting and count == len(ACTIONS)):
        raise ValueError("route cursor is out of bounds")
    if state["ok"] != all(bool(child.get("ok", False)) for child in state["children"]):
        raise ValueError("inconsistent route accumulator")


def register_reasoning_flow_route_tools(mcp):
    @mcp.tool()
    def mathformer_reasoning_route_initialize() -> Initialized:
        return {"state": hub.initialize_intent_state()}

    @mcp.tool()
    def mathformer_reasoning_route_select_action(state: State, match: dict) -> Selected:
        check_state(state, selecting=True)
        return {"action_id": hub.select_intent_action(state, selected_match(match))}

    @mcp.tool()
    def mathformer_reasoning_route_run_action(
        action_id: ActionId,
        context: Context,
        registry: dict,
        repository_root: str | None,
    ) -> Invoked:
        native = checked_registry(registry)
        root = (
            hub.REPO_ROOT
            if repository_root is None
            else Path(repository_root).resolve()
        )
        return {
            "child": hub.run_action(
                action_id, native, hub.RunContext(**context), repository_root=root
            )
        }

    @mcp.tool()
    def mathformer_reasoning_route_advance(
        state: State, child: dict, context: Context
    ) -> Advanced:
        check_state(state, selecting=True)
        updated, done = hub.advance_intent_state(
            state, child, hub.RunContext(**context), len(ACTIONS)
        )
        return {"state": updated, "done": done}

    @mcp.tool()
    def mathformer_reasoning_route_finish(
        state: State, match: dict, registry: dict
    ) -> Finished:
        check_state(state)
        if not state["children"]:
            raise ValueError("route completion requires at least one observation")
        return {
            "result": hub.finish_intent_state(
                state, selected_match(match), checked_registry(registry)
            )
        }
