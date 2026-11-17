# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Typed MCP ports for the native premise-selection route accumulator.

Commands and route metadata remain source-owned. The action boundary retains
native admission, preflight, process capture and write audit, without adding a
timeout or passing CLI arguments that the selected route never supplied.
"""

from dataclasses import asdict
import json
from pathlib import Path
from typing import Literal
from typing_extensions import TypedDict

import mathformer as hub
from adoption_check_tools import Context

ACTION = "kb:e2e"
ROUTE = "kb.premise.selection"
ActionId = Literal["kb:e2e"]


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
    """Restore the native declaration and retain caller-owned scoring evidence."""
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
    """Accept value projections, never executable caller-supplied declarations."""
    native = hub.build_registry()
    item = native[ACTION]
    if (
        item.safety != "writes_artifacts"
        or item.writes != ("artifacts/kb/",)
        or item.depends_on
        or item.command != ("{python}", "tests/kb/run_premise_kb_e2e.py", "--json")
        or item.required_paths
        != ("tests/kb/run_premise_kb_e2e.py", "backends/premise_kb/MathformerKB/")
        or item.required_tools
        or item.timeout_seconds is not None
        or item.allows_extra_args
    ):
        raise ValueError("premise selection capability changed; requalify the binding")
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


def register_premise_selection_route_tools(mcp):
    @mcp.tool()
    def mathformer_premise_selection_route_initialize() -> Initialized:
        return {"state": hub.initialize_intent_state()}

    @mcp.tool()
    def mathformer_premise_selection_route_select(
        state: State, match: dict
    ) -> Selected:
        check_state(state, selecting=True)
        return {"action_id": hub.select_intent_action(state, selected_match(match))}

    @mcp.tool()
    def mathformer_premise_selection_route_execute(
        action_id: ActionId,
        registry: dict,
        context: Context,
        repository_root: str | None = None,
    ) -> Invoked:
        if action_id != ACTION:
            raise ValueError("action is outside the selected route")
        mount = (
            {}
            if repository_root is None
            else {"repository_root": Path(repository_root)}
        )
        return {
            "child": hub.run_action(
                action_id,
                checked_registry(registry),
                hub.RunContext(**context),
                **mount,
            )
        }

    @mcp.tool()
    def mathformer_premise_selection_route_advance(
        state: State, child: dict, context: Context
    ) -> Advanced:
        check_state(state, selecting=True)
        updated, done = hub.advance_intent_state(
            state, child, hub.RunContext(**context), 1
        )
        return {"state": updated, "done": done}

    @mcp.tool()
    def mathformer_premise_selection_route_finish(
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
