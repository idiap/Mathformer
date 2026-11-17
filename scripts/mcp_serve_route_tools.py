# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable ports for mcp.serve, sharing the native selected-route executor.

The service owns the execution registry, timeout cap and repository mount.
Transported records are observations, never executable client declarations.
"""

from dataclasses import asdict
import json
from pathlib import Path
from typing import Literal
from typing_extensions import TypedDict

import mathformer as hub
from adoption_check_tools import Context

ACTION = "mcp:serve"
ROUTE = "mcp.serve"


class State(TypedDict):
    ok: bool
    children: list[dict]


class Initialized(TypedDict):
    state: State


class Selected(TypedDict):
    action_id: Literal["mcp:serve"]


class Executed(TypedDict):
    child: dict


class Advanced(Initialized):
    done: bool


class Finished(TypedDict):
    result: dict


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


def check_state(state, *, complete=False):
    if len(state["children"]) != int(complete):
        raise ValueError("route cursor is out of bounds")
    if state["ok"] != all(bool(child.get("ok", False)) for child in state["children"]):
        raise ValueError("inconsistent route accumulator")


def register_mcp_serve_route_tools(mcp, execution_registry, guard):
    def checked_registry(projection):
        native = execution_registry()
        item = native[ACTION]
        if (
            item.command != ("{python}", "scripts/mcp_server.py")
            or item.depends_on
            or item.writes
            or item.safety != "read_only"
            or item.allows_extra_args
        ):
            raise ValueError("mcp:serve capability changed; requalify the binding")
        if any(
            key != ACTION or value != hub.action_to_dict(item)
            for key, value in projection.items()
        ):
            raise ValueError(
                "registry projection differs from the service execution registry"
            )
        return {key: native[key] for key in projection}

    @mcp.tool()
    def mathformer_mcp_serve_route_inputs(
        dry_run: bool = False, keep_going: bool = False
    ) -> dict:
        """Discover source-owned route metadata and the configured execution cap."""
        route = next(row for row in hub.build_intent_routes() if row.route_id == ROUTE)
        return json.loads(
            json.dumps(
                {
                    "context": asdict(
                        hub.RunContext(
                            dry_run=dry_run, keep_going=keep_going, json_output=True
                        )
                    ),
                    "match": asdict(hub.IntentMatch(route, 0, ())),
                    "registry": {
                        ACTION: hub.action_to_dict(execution_registry()[ACTION])
                    },
                    "repository_root": None,
                }
            )
        )

    @mcp.tool()
    def mathformer_mcp_serve_route_initialize() -> Initialized:
        return {"state": hub.initialize_intent_state()}

    @mcp.tool()
    def mathformer_mcp_serve_route_select(state: State, match: dict) -> Selected:
        check_state(state)
        return {"action_id": hub.select_intent_action(state, selected_match(match))}

    @mcp.tool()
    def mathformer_mcp_serve_route_execute(
        action_id: Literal["mcp:serve"],
        context: Context,
        registry: dict,
        repository_root: str | None = None,
    ) -> Executed:
        if action_id != ACTION:
            raise ValueError("action is outside the selected route")
        records = checked_registry(registry)
        native_context = hub.RunContext(**context)
        root = None if repository_root is None else Path(repository_root).resolve()
        guard(action_id, native_context, root)
        mount = {} if root is None else {"repository_root": root}
        return {"child": hub.run_action(action_id, records, native_context, **mount)}

    @mcp.tool()
    def mathformer_mcp_serve_route_advance(
        state: State, child: dict, context: Context
    ) -> Advanced:
        check_state(state)
        updated, done = hub.advance_intent_state(
            state, child, hub.RunContext(**context), 1
        )
        return {"state": updated, "done": done}

    @mcp.tool()
    def mathformer_mcp_serve_route_finish(
        state: State, match: dict, registry: dict
    ) -> Finished:
        check_state(state, complete=True)
        return {
            "result": hub.finish_intent_state(
                state, selected_match(match), checked_registry(registry)
            )
        }
