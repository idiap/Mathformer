# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP interfaces over the native consumer-readiness dependency controller.

Transported registry entries select native declarations; they never supply code.
Leaf execution, including unbounded native timeouts and write audits, stays in
visit_dependency/run_action. Lunar budgets apply separately to this projection.
"""

from pathlib import Path
from typing import Literal
from typing_extensions import TypedDict

import mathformer as hub
from adoption_check_tools import Context
from benchmark_route_tools import State, Finished

ACTION = "control:reasoning-log-consumer-readiness"
ROUTE = "control.reasoning.logs"
DEPENDENCIES = (
    "control:reasoning-log-smoke",
    "control:reasoning-log-coverage",
    "control:reasoning-log-quality",
    "control:reasoning-log-consumer-contract",
    "control:reasoning-log-index",
    "control:reasoning-log-index-validate",
)
ActionId = Literal["control:reasoning-log-consumer-readiness"]


class Initialized(TypedDict):
    state: State
    action_id: ActionId


class Admission(TypedDict):
    accepted: bool
    status: Literal[
        "accepted", "unknown_action", "dependency_cycle", "extra_args_for_sequence"
    ]
    ancestry: list[str]


class Admitted(TypedDict):
    admission: Admission


class DependencyState(TypedDict):
    index: int
    children: list[dict]
    dependencies_ok: bool
    ancestry: list[str]


class TraversalState(TypedDict):
    accepted: bool
    dependencies: DependencyState | None
    rejection: dict | None


class Seeded(TypedDict):
    state: TraversalState


class Rejected(TypedDict):
    result: dict
    state: TraversalState


class Advanced(TypedDict):
    state: TraversalState
    done: bool


def selected_match(match):
    route = next(row for row in hub.build_intent_routes() if row.route_id == ROUTE)
    if (
        route.action_ids != (ACTION,)
        or set(match) != {"route_id", "score", "matched_terms"}
        or match["route_id"] != ROUTE
    ):
        raise ValueError("selected route differs from the native declaration")
    return hub.IntentMatch(route, match["score"], tuple(match["matched_terms"]))


def checked_registry(projection):
    native = hub.build_registry()
    item = native[ACTION]
    if (
        item.depends_on != DEPENDENCIES
        or item.command
        or item.safety != "writes_artifacts"
        or item.writes != ("artifacts/reasoning/",)
    ):
        raise ValueError("readiness composition changed; requalify the binding")
    for key in DEPENDENCIES:
        leaf = native[key]
        writing = key == "control:reasoning-log-index"
        if (
            leaf.depends_on
            or leaf.timeout_seconds is not None
            or leaf.safety != ("writes_artifacts" if writing else "read_only")
            or leaf.writes != (("artifacts/reasoning/",) if writing else ())
        ):
            raise ValueError("readiness leaf capability changed; requalify the binding")
    if any(
        key not in native or value != hub.action_to_dict(native[key])
        for key, value in projection.items()
    ):
        raise ValueError("registry projection differs from the native declaration")
    return {key: native[key] for key in projection}


def check_dependencies(state, *, visiting=False):
    count = len(state["children"])
    if (
        state["index"] != count
        or not 0 <= count <= len(DEPENDENCIES)
        or (visiting and count == len(DEPENDENCIES))
    ):
        raise ValueError("dependency cursor is out of bounds")
    if state["dependencies_ok"] != all(
        bool(child.get("ok", False)) for child in state["children"]
    ):
        raise ValueError("inconsistent dependency accumulator")
    if state["ancestry"] != [ACTION]:
        raise ValueError("selected route requires its native initial ancestry")


def check_traversal(state, *, visiting=False):
    if state["accepted"]:
        if state["dependencies"] is None or state["rejection"] is not None:
            raise ValueError("invalid accepted traversal")
        check_dependencies(state["dependencies"], visiting=visiting)
    elif (
        state["dependencies"] is not None
        or not state["rejection"]
        or state["rejection"].get("ok") is not False
    ):
        raise ValueError("invalid rejected traversal")


def register_reasoning_logs_route_tools(mcp, authorize, path_allowed):
    @mcp.tool()
    def mathformer_logs_route_initialize_route(match: dict) -> Initialized:
        state = hub.initialize_intent_state()
        return {
            "state": state,
            "action_id": hub.select_intent_action(state, selected_match(match)),
        }

    @mcp.tool()
    def mathformer_logs_route_admit(action_id: ActionId, registry: dict) -> Admitted:
        return {"admission": hub.admit_action(action_id, checked_registry(registry))}

    @mcp.tool()
    def mathformer_logs_route_reject(
        action_id: ActionId, admission: Admission
    ) -> Rejected:
        if admission["accepted"]:
            raise ValueError("cannot reject accepted admission")
        result = hub.reject_action(action_id, admission)
        return {
            "result": result,
            "state": {"accepted": False, "dependencies": None, "rejection": result},
        }

    @mcp.tool()
    def mathformer_logs_route_initialize_dependencies(admission: Admission) -> Seeded:
        if admission != hub.admit_action(ACTION, hub.build_registry()):
            raise ValueError("dependency traversal requires native accepted admission")
        return {
            "state": {
                "accepted": True,
                "dependencies": hub.initialize_dependencies(admission),
                "rejection": None,
            }
        }

    @mcp.tool()
    def mathformer_logs_route_retain_rejection(state: TraversalState) -> Advanced:
        """Carry rejection through the outer loop without visiting dependencies."""
        check_traversal(state)
        if state["accepted"]:
            raise ValueError("rejection retention requires rejected admission")
        return {"state": state, "done": True}

    @mcp.tool()
    def mathformer_logs_route_visit_dependency(
        action_id: ActionId,
        state: TraversalState,
        context: Context,
        registry: dict,
        repository_root: str | None,
    ) -> Finished:
        check_traversal(state, visiting=True)
        if not state["accepted"]:
            raise ValueError("cannot visit dependencies after rejection")
        native = checked_registry(registry)
        root = (
            hub.REPO_ROOT
            if repository_root is None
            else Path(repository_root).resolve()
        )
        if not context["dry_run"]:
            authorize()
            # The native read-only quality check also creates fixtures; its
            # writes must still pass service roots before the native audit.
            if not path_allowed(root / "artifacts/reasoning/"):
                raise ValueError("reasoning artifacts outside configured service roots")
        return {
            "result": hub.visit_dependency(
                native[action_id],
                native,
                hub.RunContext(**context),
                state["dependencies"],
                repository_root=root,
            )
        }

    @mcp.tool()
    def mathformer_logs_route_advance_dependencies(
        action_id: ActionId,
        state: TraversalState,
        child: dict,
        context: Context,
        registry: dict,
    ) -> Advanced:
        check_traversal(state, visiting=True)
        if not state["accepted"]:
            raise ValueError("cannot advance dependencies after rejection")
        updated, done = hub.advance_dependencies(
            checked_registry(registry)[action_id],
            state["dependencies"],
            child,
            hub.RunContext(**context),
        )
        return {"state": {**state, "dependencies": updated}, "done": done}

    @mcp.tool()
    def mathformer_logs_route_finish_dependencies(
        action_id: ActionId, state: TraversalState, registry: dict
    ) -> Finished:
        check_traversal(state)
        if not state["accepted"]:
            return {"result": state["rejection"]}
        if not state["dependencies"]["children"]:
            raise ValueError("dependency completion requires observations")
        if state["dependencies"]["dependencies_ok"] and state["dependencies"][
            "index"
        ] != len(DEPENDENCIES):
            raise ValueError(
                "successful dependency completion requires all six observations"
            )
        return {
            "result": hub.finish_dependencies(
                checked_registry(registry)[action_id], state["dependencies"]
            )
        }

    @mcp.tool()
    def mathformer_logs_route_finish_route(
        state: State, child: dict, context: Context, match: dict, registry: dict
    ) -> Finished:
        if state != hub.initialize_intent_state():
            raise ValueError("selected route requires the initial accumulator")
        selected = selected_match(match)
        updated, _ = hub.advance_intent_state(
            state, child, hub.RunContext(**context), len(selected.route.action_ids)
        )
        return {
            "result": hub.finish_intent_state(
                updated, selected, checked_registry(registry)
            )
        }
