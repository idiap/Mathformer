# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Typed MCP ports for the native e2e.all.backends route accumulator.

Commands and route metadata remain source-owned. The action boundary retains
native admission, preflight, process capture and write audit, and the native 900-second timeout. No additional CLI arguments are supplied.
"""

from dataclasses import asdict
import json
from pathlib import Path
from typing import Literal
from typing_extensions import TypedDict

import mathformer as hub
from adoption_check_tools import Context

ACTION = "e2e:all-backends"
ROUTE = "e2e.all.backends"
ActionId = Literal["e2e:all-backends"]


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
        or item.writes != ("artifacts/e2e/",)
        or item.depends_on
        or item.command != ("{python}", "tests/e2e/run_all_backends.py", "--json")
        or item.required_paths != ("tests/e2e/run_all_backends.py",)
        or item.required_tools
        or item.timeout_seconds != 900
        or item.allows_extra_args
    ):
        raise ValueError("e2e capability changed; requalify the binding")
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


def register_e2e_all_backends_route_tools(mcp, authorize, path_allowed):
    @mcp.tool()
    def mathformer_e2e_route_initialize() -> Initialized:
        return {"state": hub.initialize_intent_state()}

    @mcp.tool()
    def mathformer_e2e_route_select(state: State, match: dict) -> Selected:
        check_state(state, selecting=True)
        return {"action_id": hub.select_intent_action(state, selected_match(match))}

    @mcp.tool()
    def mathformer_e2e_route_run(
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
            else {"repository_root": Path(repository_root).resolve()}
        )
        native = checked_registry(registry)
        root = mount.get("repository_root", hub.REPO_ROOT)
        if not context["dry_run"] and action_id in native:
            authorize()
            if any(not path_allowed(root / path) for path in native[action_id].writes):
                raise ValueError("e2e writes outside configured service roots")
        return {
            "child": hub.run_action(
                action_id, native, hub.RunContext(**context), **mount
            )
        }

    @mcp.tool()
    def mathformer_e2e_route_advance(
        state: State, child: dict, context: Context, action_count: Literal[1]
    ) -> Advanced:
        check_state(state, selecting=True)
        if action_count != 1:
            raise ValueError("selected route has exactly one action")
        updated, done = hub.advance_intent_state(
            state, child, hub.RunContext(**context), action_count
        )
        return {"state": updated, "done": done}

    @mcp.tool()
    def mathformer_e2e_route_finish(
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
