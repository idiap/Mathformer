# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""JSON ports for the shared single-action benchmark route controller.

Registry and route projections are checked against native declarations, never
interpreted as caller-supplied commands. Leaf admission, preflight, subprocess
timeout and write audit remain owned by mathformer.run_action.
"""

from dataclasses import asdict
import json
from pathlib import Path
from typing_extensions import TypedDict
import mathformer as hub
from adoption_check_tools import Context

ACTION = "benchmark:proofnet"
ROUTE = "benchmark.workflow"


class State(TypedDict):
    ok: bool
    children: list[dict]


class Initialized(TypedDict):
    state: State


class Invoked(TypedDict):
    child: dict


class Advanced(TypedDict):
    state: State
    done: bool


class Finished(TypedDict):
    result: dict


def selected_match(match):
    route = next(
        route for route in hub.build_intent_routes() if route.route_id == ROUTE
    )
    if route.action_ids != (ACTION,):
        raise ValueError(
            "benchmark route changed: regenerate the single-action contract"
        )
    native = json.loads(json.dumps(asdict(route)))
    projected = match["route"]
    if not {"route_id", "action_ids"} <= projected.keys() or any(
        key not in native or value != native[key] for key, value in projected.items()
    ):
        raise ValueError("selected route differs from the native declaration")
    return hub.IntentMatch(route, match["score"], tuple(match["matched_terms"]))


def checked_registry(projection):
    registry = hub.build_registry()
    if ACTION not in projection or any(
        key not in registry or value != hub.action_to_dict(registry[key])
        for key, value in projection.items()
    ):
        raise ValueError("registry projection differs from the native declaration")
    if registry[ACTION].depends_on:
        raise ValueError("benchmark action gained dependencies: regenerate contract")
    return {key: registry[key] for key in projection}


def register_benchmark_route_tools(
    mcp, authorize=lambda: None, path_allowed=lambda path: True
):
    """Bind every port to native functions and retain service write restrictions."""

    @mcp.tool()
    def mathformer_benchmark_route_initialize() -> Initialized:
        return {"state": hub.initialize_intent_state()}

    @mcp.tool()
    def mathformer_benchmark_route_run_child(
        registry: dict, context: Context, repository_root: str | None
    ) -> Invoked:
        native = checked_registry(registry)
        selected_match(
            {
                "route": {"route_id": ROUTE, "action_ids": [ACTION]},
                "score": 0,
                "matched_terms": [],
            }
        )
        root = (
            hub.REPO_ROOT
            if repository_root is None
            else Path(repository_root).resolve()
        )
        if not context["dry_run"]:
            authorize()
            if any(not path_allowed(root / path) for path in native[ACTION].writes):
                raise ValueError("benchmark writes outside configured service roots")
        return {
            "child": hub.run_action(
                ACTION, native, hub.RunContext(**context), repository_root=root
            )
        }

    @mcp.tool()
    def mathformer_benchmark_route_advance(
        state: State, child: dict, context: Context
    ) -> Advanced:
        if state != hub.initialize_intent_state():
            raise ValueError("single-action route requires the initial accumulator")
        updated, done = hub.advance_intent_state(
            state, child, hub.RunContext(**context), 1
        )
        return {"state": updated, "done": done}

    @mcp.tool()
    def mathformer_benchmark_route_finish(
        state: State, match: dict, registry: dict
    ) -> Finished:
        if len(state["children"]) != 1 or state["ok"] != bool(
            state["children"][0].get("ok", False)
        ):
            raise ValueError("single-action route requires one consistent child")
        return {
            "result": hub.finish_intent_state(
                state, selected_match(match), checked_registry(registry)
            )
        }
