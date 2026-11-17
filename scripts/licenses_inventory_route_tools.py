# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Typed ports for the source-owned singleton license inventory route.

Registry projections carry context, never executable caller-supplied commands.
The source controller retains admission, preflight, capture and write auditing.
These ports preserve CLI timeout semantics; Lunar owns its enclosing budget.
"""

from pathlib import Path
from typing import Literal
from typing_extensions import TypedDict

import mathformer as hub
from adoption_check_tools import Context

ACTION = "licenses:inventory"
ROUTE = "licenses.inventory"
Action = Literal["licenses:inventory"]


class State(TypedDict):
    ok: bool
    children: list[dict]


class Initialized(TypedDict):
    state: State


class Selected(TypedDict):
    action: Action


class Invoked(TypedDict):
    child: dict


class Advanced(TypedDict):
    state: State
    done: bool


class Finished(TypedDict):
    result: dict


def selected_match(match):
    route = next(row for row in hub.build_intent_routes() if row.route_id == ROUTE)
    if match["route_id"] != ROUTE or route.action_ids != (ACTION,):
        raise ValueError("selected route differs from the native declaration")
    return hub.IntentMatch(route, match["score"], tuple(match["matched_terms"]))


def checked_registry(projection):
    native = hub.build_registry()
    item = native[ACTION]
    if (
        item.safety != "writes_repo"
        or item.writes != ("docs/",)
        or item.depends_on
        or item.command != ("{python}", "scripts/generate_python_license_inventory.py")
        or item.timeout_seconds is not None
        or item.allows_extra_args
    ):
        raise ValueError("license inventory capability changed; requalify the binding")
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


def register_licenses_inventory_route_tools(
    mcp, write_policy=lambda: None, path_allowed=lambda path: True
):
    @mcp.tool()
    def mathformer_licenses_route_initialize() -> Initialized:
        return {"state": hub.initialize_intent_state()}

    @mcp.tool()
    def mathformer_licenses_route_select(state: State, match: dict) -> Selected:
        check_state(state, selecting=True)
        return {"action": hub.select_intent_action(state, selected_match(match))}

    @mcp.tool()
    def mathformer_licenses_route_run(
        action: Action,
        registry: dict,
        context: Context,
        repository_root: str | None = None,
    ) -> Invoked:
        if action != ACTION:
            raise ValueError("action is outside the selected route")
        native = checked_registry(registry)
        root = (
            hub.REPO_ROOT
            if repository_root is None
            else Path(repository_root).resolve()
        )
        if not context["dry_run"] and context["allow_mutating"] and action in native:
            write_policy()
            if not path_allowed(root / "docs"):
                raise ValueError("Inventory destination is outside allowed write roots")
        mount = {} if repository_root is None else {"repository_root": root}
        return {
            "child": hub.run_action(action, native, hub.RunContext(**context), **mount)
        }

    @mcp.tool()
    def mathformer_licenses_route_advance(
        state: State, child: dict, context: Context
    ) -> Advanced:
        check_state(state, selecting=True)
        count = len(
            selected_match(
                {"route_id": ROUTE, "score": 0, "matched_terms": []}
            ).route.action_ids
        )
        updated, done = hub.advance_intent_state(
            state, child, hub.RunContext(**context), count
        )
        return {"state": updated, "done": done}

    @mcp.tool()
    def mathformer_licenses_route_finish(
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
