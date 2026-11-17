# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP ports for the selected nine-action SymPy goal route.

Route accumulation and execution remain shared with run_intent_match. Registry
projections select native capabilities; transported metadata never supplies code.
Failed child payloads remain data. Initial artifact regeneration is mandatory
for this native route and both native write targets require service admission.
"""

from pathlib import Path
from typing import Literal
from typing_extensions import TypedDict

import mathformer as hub
from adoption_check_tools import Context

ROUTE = "formalize.physics.sympy.goal_sample_0004"
ACTIONS = (
    "physics-sympy:source-only-recursive-0004",
    "physics-sympy:goal-sample-plan-0004",
    "physics-sympy:design-guard-review-0004",
    "physics-sympy:repair-expansion-map-0004",
    "physics-sympy:recursive-repair-control-0004",
    "physics-sympy:grounded-sample-thoroughness-0004",
    "physics-sympy:cross-backend-semantic-packet-0004",
    "physics-sympy:adversarial-design-guard",
    "physics-sympy:dependency-failure-policy",
)
TIMEOUTS = (900, 300, 300, 360, 420, 360, 180, 180, 120)
WRITES = "artifacts/physics_sympy/recursive_goal_runs/formalphysics_0004/"
ARTIFACT = (
    "libraries/MathformerPhysicsLib/SymPy/formalphysics_0004/MathformerPhysics.py"
)
ActionId = Literal[
    "physics-sympy:source-only-recursive-0004",
    "physics-sympy:goal-sample-plan-0004",
    "physics-sympy:design-guard-review-0004",
    "physics-sympy:repair-expansion-map-0004",
    "physics-sympy:recursive-repair-control-0004",
    "physics-sympy:grounded-sample-thoroughness-0004",
    "physics-sympy:cross-backend-semantic-packet-0004",
    "physics-sympy:adversarial-design-guard",
    "physics-sympy:dependency-failure-policy",
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


def selected_match(metadata):
    route = next(row for row in hub.build_intent_routes() if row.route_id == ROUTE)
    if (
        route.action_ids != ACTIONS
        or set(metadata) != {"score", "matched_terms", "route"}
        or metadata["route"].get("route_id") != ROUTE
        or metadata["route"].get("action_ids") != list(ACTIONS)
    ):
        raise ValueError("selected route differs from the native declaration")
    return hub.IntentMatch(route, metadata["score"], tuple(metadata["matched_terms"]))


def checked_registry(projection):
    native = hub.build_registry()
    for index, action_id in enumerate(ACTIONS):
        item = native[action_id]
        if (
            item.depends_on
            or item.timeout_seconds != TIMEOUTS[index]
            or item.writes != ((ARTIFACT, WRITES) if index == 0 else ())
            or item.safety != ("writes_artifacts" if index == 0 else "read_only")
        ):
            raise ValueError("SymPy goal capability changed; requalify the binding")
    if "--regenerate-initial-artifact" not in native[ACTIONS[0]].command:
        raise ValueError("initial regeneration must remain enabled")
    if any(
        key not in native or value != hub.action_to_dict(native[key])
        for key, value in projection.items()
    ):
        raise ValueError("registry projection differs from the native declaration")
    return {key: native[key] for key in projection}


def check_state(state, context, *, selecting=False, finishing=False):
    count = len(state["children"])
    if not 0 <= count <= len(ACTIONS) or (selecting and count == len(ACTIONS)):
        raise ValueError("route cursor is out of bounds")
    if state["ok"] != all(bool(child.get("ok", False)) for child in state["children"]):
        raise ValueError("inconsistent route accumulator")
    for index, child in enumerate(state["children"]):
        if child.get("action_id", child.get("action", {}).get("id")) != ACTIONS[index]:
            raise ValueError("child history differs from native route order")
        if (
            index < count - 1
            and not child.get("ok", False)
            and not context["keep_going"]
        ):
            raise ValueError("history continues after native early stop")
    stopped = bool(
        count
        and not state["children"][-1].get("ok", False)
        and not context["keep_going"]
    )
    if selecting and stopped:
        raise ValueError("route already stopped")
    if finishing and count != len(ACTIONS) and not stopped:
        raise ValueError("route has unconsumed actions")


def register_physics_sympy_goal_0004_route_tools(mcp, authorize, path_allowed):
    @mcp.tool()
    def mathformer_sympy_goal_0004_route_initialize() -> Initialized:
        return {"state": hub.initialize_intent_state()}

    @mcp.tool()
    def mathformer_sympy_goal_0004_route_select(
        state: State, match: dict, context: Context
    ) -> Selected:
        check_state(state, context, selecting=True)
        return {"action_id": hub.select_intent_action(state, selected_match(match))}

    @mcp.tool()
    def mathformer_sympy_goal_0004_route_run(
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
            if not all(path_allowed(root / path) for path in (ARTIFACT, WRITES)):
                raise ValueError("SymPy goal writes outside configured service roots")
        return {
            "child": hub.run_action(
                action_id, native, hub.RunContext(**context), repository_root=root
            )
        }

    @mcp.tool()
    def mathformer_sympy_goal_0004_route_advance(
        state: State,
        child: dict,
        context: Context,
        action_count: Literal[9],
    ) -> Advanced:
        check_state(state, context, selecting=True)
        if (
            child.get("action_id", child.get("action", {}).get("id"))
            != ACTIONS[len(state["children"])]
        ):
            raise ValueError("child differs from selected native action")
        updated, done = hub.advance_intent_state(
            state, child, hub.RunContext(**context), action_count
        )
        return {"state": updated, "done": done}

    @mcp.tool()
    def mathformer_sympy_goal_0004_route_finish(
        state: State,
        match: dict,
        registry: dict,
        context: Context,
    ) -> Finished:
        check_state(state, context, finishing=True)
        return {
            "result": hub.finish_intent_state(
                state, selected_match(match), checked_registry(registry)
            )
        }
