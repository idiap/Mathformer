# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable ports for the native single-action Isabelle physics route.

The hub owns selection, admission, process execution and write auditing. These
ports retain failed payloads as data and leave unexpected exceptions visible.
No timeout, generator arguments or promotion capability is added.
"""

from pathlib import Path
from typing import Literal
from typing_extensions import TypedDict

import mathformer as hub
from adoption_check_tools import Context

ACTION = "formalphysics:extra-isabelle"
ROUTE = "formalize.physics.isabelle"
LEAF = "scripts/generate_formalphysics_extra_isabelle.py"
ARTIFACTS = "artifacts/physics_isabelle/from_scratch_isabelle/"
DECLARED = "libraries/MathformerPhysicsLib/backends/isabelle/Isabelle/"
ActionId = Literal["formalphysics:extra-isabelle"]


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


def selected_match(metadata):
    """Keep scoring evidence while restoring the controller-owned route."""
    route = next(row for row in hub.build_intent_routes() if row.route_id == ROUTE)
    if route.action_ids != (ACTION,) or set(metadata) != {"score", "matched_terms"}:
        raise ValueError("selected route differs from the native declaration")
    return hub.IntentMatch(route, metadata["score"], tuple(metadata["matched_terms"]))


def checked_registry(projection):
    """Resolve value projections to native capabilities, never caller commands."""
    native = hub.build_registry()
    item = native[ACTION]
    if (
        item.command != ("{python}", LEAF)
        or item.safety != "writes_repo"
        or item.writes != (DECLARED,)
        or item.required_paths != (LEAF,)
        or item.depends_on
        or item.allows_extra_args
        or item.timeout_seconds is not None
    ):
        raise ValueError("physics Isabelle capability changed; requalify the binding")
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


def register_physics_isabelle_route_tools(mcp, authorize, path_allowed):
    @mcp.tool()
    def mathformer_physics_isabelle_route_initialize() -> Initialized:
        return {"state": hub.initialize_intent_state()}

    @mcp.tool()
    def mathformer_physics_isabelle_route_select_action(state: State) -> Selected:
        check_state(state, selecting=True)
        return {
            "action_id": hub.select_intent_action(
                state, selected_match({"score": 0, "matched_terms": []})
            )
        }

    @mcp.tool()
    def mathformer_physics_isabelle_route_execute_action(
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
        if not context["dry_run"] and action_id in native:
            authorize()
            # Guard actual generator output as well as the legacy declaration;
            # the source-owned write audit must still report the mismatch.
            if any(not path_allowed(root / path) for path in (ARTIFACTS, DECLARED)):
                raise ValueError(
                    "physics Isabelle writes outside configured service roots"
                )
        return {
            "child": hub.run_action(
                action_id, native, hub.RunContext(**context), repository_root=root
            )
        }

    @mcp.tool()
    def mathformer_physics_isabelle_route_advance(
        state: State, child: dict, context: Context
    ) -> Advanced:
        check_state(state, selecting=True)
        updated, done = hub.advance_intent_state(
            state, child, hub.RunContext(**context), 1
        )
        return {"state": updated, "done": done}

    @mcp.tool()
    def mathformer_physics_isabelle_route_finish(
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
