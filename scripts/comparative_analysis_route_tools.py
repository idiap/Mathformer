# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""JSON ports over the native comparative-report route controller.

The hub owns action admission, preflight, argv, timeouts, write audits and
ordered observations. Registry projections select native capabilities only.
"""

from dataclasses import asdict
import json
from pathlib import Path
from typing import Literal
from typing_extensions import TypedDict

import mathformer as hub
from adoption_check_tools import Context
from physics_coherence_route_tools import (
    State,
    Initialized,
    Invoked,
    Advanced,
    Finished,
)

ROUTE = "report.formalphysics.comparative_analysis"
SOURCE = "skills/physics-common/formalphysics-comparative-analysis-reporter/scripts/build_comparative_report.py"
SMOKE = "tests/physics_lean/run_formalphysics_comparative_report.py"
ACTIONS = (
    "physics-lean:formalphysics-comparative-report-self-test",
    "physics-lean:formalphysics-comparative-report",
)
ActionId = Literal[
    "physics-lean:formalphysics-comparative-report-self-test",
    "physics-lean:formalphysics-comparative-report",
]


class Selected(TypedDict):
    action: ActionId


def selected_match(match):
    """Restore native route metadata and preserve the caller's matching evidence."""
    route = next(row for row in hub.build_intent_routes() if row.route_id == ROUTE)
    native = json.loads(json.dumps(asdict(route)))
    projection = match["route"]
    if (
        route.action_ids != ACTIONS
        or not {"route_id", "action_ids"} <= projection.keys()
        or any(
            key not in native or value != native[key]
            for key, value in projection.items()
        )
    ):
        raise ValueError("selected route differs from native declaration")
    return hub.IntentMatch(route, match["score"], tuple(match["matched_terms"]))


def checked_registry(projection):
    """Resolve a registry subset without accepting caller-supplied executable code."""
    native = hub.build_registry()
    for index, action in enumerate(ACTIONS):
        item = native[action]
        command = ("{python}", SMOKE, "--json") if index == 0 else ("{python}", SOURCE)
        if (
            item.command != command
            or item.depends_on
            or item.timeout_seconds != (180, 900)[index]
            or item.safety != "writes_artifacts"
            or item.writes != ("artifacts/formalphysics_comparative_analysis/",)
        ):
            raise ValueError("native report capability changed; requalify binding")
    if any(
        key not in native or value != hub.action_to_dict(native[key])
        for key, value in projection.items()
    ):
        raise ValueError("registry projection differs from native declaration")
    return {key: native[key] for key in projection}


def check_state(state, *, selecting=False):
    count = len(state["children"])
    if count > len(ACTIONS) or (selecting and count >= len(ACTIONS)):
        raise ValueError("route cursor is out of bounds")
    if state["ok"] != all(bool(child.get("ok", False)) for child in state["children"]):
        raise ValueError("inconsistent route accumulator")


def register_comparative_analysis_route_tools(mcp, authorize, path_allowed):
    @mcp.tool()
    def mathformer_comparative_analysis_initialize() -> Initialized:
        return {"state": hub.initialize_intent_state()}

    @mcp.tool()
    def mathformer_comparative_analysis_select_action(
        state: State, match: dict
    ) -> Selected:
        check_state(state, selecting=True)
        return {"action": hub.select_intent_action(state, selected_match(match))}

    @mcp.tool()
    def mathformer_comparative_analysis_run_child(
        action: ActionId,
        context: Context,
        registry: dict,
        repository_root: str | None,
    ) -> Invoked:
        if action not in ACTIONS:
            raise ValueError("action is outside selected route")
        native = checked_registry(registry)
        root = (
            hub.REPO_ROOT
            if repository_root is None
            else Path(repository_root).resolve()
        )
        if not context["dry_run"]:
            authorize()
            if action in native and any(
                not path_allowed(root / path) for path in native[action].writes
            ):
                raise PermissionError("report writes outside configured service roots")
        # No extra_args: the selected route deliberately retains the builder's
        # required-input error. Input-bearing report runs use the native action.
        return {
            "child": hub.run_action(
                action, native, hub.RunContext(**context), repository_root=root
            )
        }

    @mcp.tool()
    def mathformer_comparative_analysis_advance(
        state: State,
        child: dict,
        context: Context,
        action_count: Literal[2],
    ) -> Advanced:
        check_state(state, selecting=True)
        if action_count != len(ACTIONS):
            raise ValueError("selected route has exactly two actions")
        updated, done = hub.advance_intent_state(
            state, child, hub.RunContext(**context), action_count
        )
        return {"state": updated, "done": done}

    @mcp.tool()
    def mathformer_comparative_analysis_finish(
        state: State, match: dict, registry: dict
    ) -> Finished:
        check_state(state)
        if not state["children"] or (
            len(state["children"]) < len(ACTIONS) and state["ok"]
        ):
            raise ValueError("completion requires exhaustion or failed child")
        return {
            "result": hub.finish_intent_state(
                state, selected_match(match), checked_registry(registry)
            )
        }
