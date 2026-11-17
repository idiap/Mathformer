# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Value ports over the selected native portable-adoption controller.

The registry remains source-owned. Native recursion, preflight, argv, process
capture and write audits execute unchanged; no command timeout is added here.
"""

from dataclasses import asdict
import json
from pathlib import Path
from typing import Literal
from typing_extensions import TypedDict

import mathformer as hub
from adoption_check_tools import Context, State as Dependencies
from thematic_layout_route_tools import State as RouteState, check_state

ACTION = "adoption:check"
ROUTE = "repository.portable-adoption"
DEPENDENCIES = (
    "adoption:validate",
    "adoption:catalog-check",
    "adoption:test-contracts",
    "adoption:test-provenance",
)


class Admission(TypedDict):
    action_id: Literal["adoption:check"]
    accepted: bool
    status: Literal[
        "accepted", "unknown_action", "dependency_cycle", "extra_args_for_sequence"
    ]
    ancestry: list[str]


class Admitted(TypedDict):
    admission: Admission


class RouteInitialized(TypedDict):
    state: RouteState


class Traversal(TypedDict):
    accepted: bool
    dependencies: Dependencies | None
    rejection: dict | None


class DependenciesInitialized(TypedDict):
    state: Traversal


class Rejected(TypedDict):
    result: dict
    state: Traversal


class RouteAdvanced(RouteInitialized):
    done: bool


class DependenciesAdvanced(DependenciesInitialized):
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


def checked_registry(projection):
    """Restore native dataclasses, permitting native missing-action failures."""
    native = hub.build_registry()
    if native[ACTION].command or native[ACTION].depends_on != DEPENDENCIES:
        raise ValueError("portable adoption composition changed; requalify binding")
    for key in (ACTION, *DEPENDENCIES):
        item = native[key]
        if (
            item.safety != "read_only"
            or item.writes
            or item.timeout_seconds is not None
            or (key != ACTION and item.depends_on)
        ):
            raise ValueError("portable adoption effects changed; requalify binding")
    if any(
        key not in (ACTION, *DEPENDENCIES) or value != hub.action_to_dict(native[key])
        for key, value in projection.items()
    ):
        raise ValueError("registry projection differs from native declaration")
    return {key: native[key] for key in projection}


def check_dependencies(state, *, visiting=False):
    count = len(state["children"])
    if state["index"] != count or not 0 <= count <= 4 or (visiting and count == 4):
        raise ValueError("dependency cursor is out of bounds")
    if state["dependencies_ok"] != all(
        bool(child.get("ok", False)) for child in state["children"]
    ):
        raise ValueError("inconsistent dependency accumulator")
    if state["ancestry"] != [ACTION]:
        raise ValueError("selected route requires native initial ancestry")


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


def register_portable_adoption_route_tools(mcp):
    @mcp.tool()
    def mathformer_portable_route_initialize_route() -> RouteInitialized:
        return {"state": hub.initialize_intent_state()}

    @mcp.tool()
    def mathformer_portable_route_select_and_admit(
        state: RouteState, match: dict, registry: dict
    ) -> Admitted:
        check_state(state, selecting=True)
        action_id = hub.select_intent_action(state, selected_match(match))
        return {
            "admission": {
                "action_id": action_id,
                **hub.admit_action(action_id, checked_registry(registry)),
            }
        }

    @mcp.tool()
    def mathformer_portable_route_reject(admission: Admission) -> Rejected:
        if admission["accepted"]:
            raise ValueError("cannot reject accepted admission")
        result = hub.reject_action(admission["action_id"], admission)
        return {
            "result": result,
            "state": {"accepted": False, "dependencies": None, "rejection": result},
        }

    @mcp.tool()
    def mathformer_portable_route_initialize_dependencies(
        admission: Admission,
    ) -> DependenciesInitialized:
        if admission != {
            "action_id": ACTION,
            **hub.admit_action(ACTION, hub.build_registry()),
        }:
            raise ValueError("traversal requires native accepted admission")
        return {
            "state": {
                "accepted": True,
                "dependencies": hub.initialize_dependencies(admission),
                "rejection": None,
            }
        }

    @mcp.tool()
    def mathformer_portable_route_retain_rejection(
        state: Traversal,
    ) -> DependenciesAdvanced:
        """Pure transport completion, with no native dependency invocation."""
        check_traversal(state)
        if state["accepted"]:
            raise ValueError("retention requires rejected admission")
        return {"state": state, "done": True}

    @mcp.tool()
    def mathformer_portable_route_visit_leaf(
        state: Traversal,
        registry: dict,
        context: Context,
        repository_root: str | None = None,
    ) -> Finished:
        check_traversal(state, visiting=True)
        if not state["accepted"]:
            raise ValueError("cannot visit after rejection")
        native = checked_registry(registry)
        mount = (
            {}
            if repository_root is None
            else {"repository_root": Path(repository_root).resolve()}
        )
        return {
            "result": hub.visit_dependency(
                native[ACTION],
                native,
                hub.RunContext(**context),
                state["dependencies"],
                **mount,
            )
        }

    @mcp.tool()
    def mathformer_portable_route_advance_dependencies(
        state: Traversal, child: dict, context: Context
    ) -> DependenciesAdvanced:
        check_traversal(state, visiting=True)
        if not state["accepted"]:
            raise ValueError("cannot advance after rejection")
        updated, done = hub.advance_dependencies(
            hub.build_registry()[ACTION],
            state["dependencies"],
            child,
            hub.RunContext(**context),
        )
        return {"state": {**state, "dependencies": updated}, "done": done}

    @mcp.tool()
    def mathformer_portable_route_finish_dependencies(
        state: Traversal, registry: dict
    ) -> Finished:
        check_traversal(state)
        if not state["accepted"]:
            return {"result": state["rejection"]}
        dependencies = state["dependencies"]
        if not dependencies["children"] or (
            dependencies["dependencies_ok"] and dependencies["index"] != 4
        ):
            raise ValueError("dependency completion requires terminal observations")
        return {
            "result": hub.finish_dependencies(
                checked_registry(registry)[ACTION], dependencies
            )
        }

    @mcp.tool()
    def mathformer_portable_route_advance_route(
        state: RouteState, child: dict, context: Context
    ) -> RouteAdvanced:
        check_state(state, selecting=True)
        updated, done = hub.advance_intent_state(
            state, child, hub.RunContext(**context), 1
        )
        return {"state": updated, "done": done}

    @mcp.tool()
    def mathformer_portable_route_finish_route(
        state: RouteState, match: dict, registry: dict
    ) -> Finished:
        check_state(state)
        if len(state["children"]) != 1:
            raise ValueError("route completion requires exactly one observation")
        return {
            "result": hub.finish_intent_state(
                state, selected_match(match), checked_registry(registry)
            )
        }
