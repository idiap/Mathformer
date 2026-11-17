# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable ports for framework review, sharing the authoritative hub controller.

Registry projections can omit entries (the native unknown-action path), but
cannot supply commands or alter declarations. Child recursion, process limits,
preflight, output capture and filesystem audits stay in the native executor.
"""

from dataclasses import asdict
import json
from pathlib import Path
from typing_extensions import TypedDict

import mathformer as hub
from adoption_check_tools import Context, Admission
from review_framework_tools import State as Dependencies
from environment_validate_route_tools import (
    Mount,
    State,
    Initialized,
    Advanced,
    Finished,
    check_state,
)

ACTION = "review:autoformalization-framework"
ROUTE = "review.autoformalization.framework"
DEPENDENCIES = ("control:all", "test:docs", "mathformerphysicslib:release-gate")


class Admitted(TypedDict):
    admission: Admission


class DependenciesInitialized(TypedDict):
    state: Dependencies


class DependenciesAdvanced(TypedDict):
    state: Dependencies
    done: bool


class Child(TypedDict):
    child: dict


class Carried(TypedDict):
    state: Dependencies
    done: bool
    child: dict


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
    native = hub.build_registry()
    item, release = native[ACTION], native["mathformerphysicslib:release-gate"]
    if (
        item.depends_on != DEPENDENCIES
        or item.command
        or release.command
        != (
            "{python}",
            "tests/physics_lean/run_mathformerphysicslib_release_gate.py",
            "--json",
        )
        or release.timeout_seconds != 1200
    ):
        raise ValueError("framework review capability changed; requalify the binding")
    if any(
        key not in native or value != hub.action_to_dict(native[key])
        for key, value in projection.items()
    ):
        raise ValueError("registry projection differs from the native declaration")
    return {key: native[key] for key in projection}


def check_dependencies(state, *, visiting=False):
    index = state["index"]
    if (
        not 0 <= index <= 3
        or len(state["children"]) != index
        or (visiting and index == 3)
    ):
        raise ValueError("dependency cursor is out of bounds")
    if state["dependencies_ok"] != all(
        bool(child.get("ok", False)) for child in state["children"]
    ):
        raise ValueError("inconsistent dependency accumulator")


def register_framework_review_route_tools(mcp, authorize, path_allowed):
    @mcp.tool()
    def mathformer_framework_review_initialize_route() -> Initialized:
        return {"state": hub.initialize_intent_state()}

    @mcp.tool()
    def mathformer_framework_review_select_and_admit(
        state: State, match: dict, registry: dict
    ) -> Admitted:
        check_state(state, selecting=True)
        action_id = hub.select_intent_action(state, selected_match(match))
        return {"admission": hub.admit_action(action_id, checked_registry(registry))}

    @mcp.tool()
    def mathformer_framework_review_initialize_dependencies(
        admission: Admission,
    ) -> DependenciesInitialized:
        return {"state": hub.initialize_dependencies(admission)}

    @mcp.tool()
    def mathformer_framework_review_visit_dependency(
        state: Dependencies, context: Context, registry: dict, mount: Mount
    ) -> Child:
        check_dependencies(state, visiting=True)
        native = checked_registry(registry)
        if set(mount) - {"repository_root"}:
            raise ValueError("unknown repository mount field")
        kwargs = (
            {}
            if "repository_root" not in mount
            else {"repository_root": Path(mount["repository_root"]).resolve()}
        )
        root = kwargs.get("repository_root", hub.REPO_ROOT)
        if not context["dry_run"]:
            authorize()
            pending, seen = [native[ACTION].depends_on[state["index"]]], set()
            while pending:
                key = pending.pop()
                if key in seen or key not in native:
                    continue
                seen.add(key)
                item = native[key]
                pending.extend(item.depends_on)
                if any(not path_allowed(root / path) for path in item.writes):
                    raise PermissionError(
                        f"{key} writes outside configured service roots"
                    )
        return {
            "child": hub.visit_dependency(
                native[ACTION], native, hub.RunContext(**context), state, **kwargs
            )
        }

    @mcp.tool()
    def mathformer_framework_review_advance_dependencies(
        state: Dependencies, child: dict, context: Context, registry: dict
    ) -> DependenciesAdvanced:
        check_dependencies(state, visiting=True)
        updated, done = hub.advance_dependencies(
            checked_registry(registry)[ACTION], state, child, hub.RunContext(**context)
        )
        return {"state": updated, "done": done}

    @mcp.tool()
    def mathformer_framework_review_finish_dependencies(
        state: Dependencies, registry: dict
    ) -> Child:
        check_dependencies(state)
        return {
            "child": hub.finish_dependencies(checked_registry(registry)[ACTION], state)
        }

    @mcp.tool()
    def mathformer_framework_review_reject_review(admission: Admission) -> Child:
        return {"child": hub.reject_action(ACTION, admission)}

    @mcp.tool()
    def mathformer_framework_review_carry_rejection(
        state: Dependencies, child: dict
    ) -> Carried:
        """Transport a rejection around PRISM's loop; execute no native step."""
        return {"state": state, "done": True, "child": child}

    @mcp.tool()
    def mathformer_framework_review_advance_route(
        state: State, child: dict, context: Context
    ) -> Advanced:
        check_state(state, selecting=True)
        updated, done = hub.advance_intent_state(
            state, child, hub.RunContext(**context), 1
        )
        return {"state": updated, "done": done}

    @mcp.tool()
    def mathformer_framework_review_finish_route(
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
