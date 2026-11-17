# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable ports for the native single-action Lean physics backend route.

The hub owns selection, admission, process execution and write auditing. These
ports retain failed payloads as data and leave unexpected exceptions visible.
No timeout, generator arguments or promotion capability is added.
"""

from pathlib import Path
from typing import Literal
from typing_extensions import TypedDict

import mathformer as hub
from adoption_check_tools import Context

ACTION = "physics-lean:backend-suite"
ROUTE = "validate.physics.lean.backend"
LEAF = "tests/physics_lean/run_lean_physics_backend_suite.py"
ARTIFACTS = "artifacts/physics_lean/backend_suite/"
# Native regression reports are outside the hub declaration. Guard their actual
# roots too; the source write audit still rejects undeclared changes.
OUTPUT_PATHS = (
    ARTIFACTS,
    "artifacts/physics_lean/derivation_completeness_regression/",
    "artifacts/physics_lean/grounded_sample_thoroughness/",
)
ActionId = Literal["physics-lean:backend-suite"]


class State(TypedDict):
    ok: bool
    children: list[dict]


class Initialized(TypedDict):
    state: State


class Selected(TypedDict):
    action: ActionId


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
        item.command != ("{python}", LEAF, "--json")
        or item.safety != "writes_artifacts"
        or item.writes != (ARTIFACTS,)
        or item.depends_on
        or item.allows_extra_args
        or item.timeout_seconds is not None
    ):
        raise ValueError(
            "physics Lean backend capability changed; requalify the binding"
        )
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


def register_physics_lean_backend_route_tools(mcp, authorize, path_allowed):
    @mcp.tool()
    def mathformer_physics_lean_backend_route_initialize() -> Initialized:
        return {"state": hub.initialize_intent_state()}

    @mcp.tool()
    def mathformer_physics_lean_backend_route_select(state: State) -> Selected:
        check_state(state, selecting=True)
        return {
            "action": hub.select_intent_action(
                state, selected_match({"score": 0, "matched_terms": []})
            )
        }

    @mcp.tool()
    def mathformer_physics_lean_backend_route_run_action(
        action: ActionId,
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
        if not context["dry_run"] and action in native:
            authorize()
            if any(not path_allowed(root / path) for path in OUTPUT_PATHS):
                raise ValueError(
                    "physics Lean backend writes outside configured service roots"
                )
        return {
            "child": hub.run_action(
                action, native, hub.RunContext(**context), repository_root=root
            )
        }

    @mcp.tool()
    def mathformer_physics_lean_backend_route_advance(
        state: State, child: dict, context: Context
    ) -> Advanced:
        check_state(state, selecting=True)
        updated, done = hub.advance_intent_state(
            state, child, hub.RunContext(**context), 1
        )
        return {"state": updated, "done": done}

    @mcp.tool()
    def mathformer_physics_lean_backend_route_finish(
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
