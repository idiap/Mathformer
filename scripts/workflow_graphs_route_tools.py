# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable steps for the native workflow graph reporting route.

Wire registry values select source declarations, never executable caller code.
The native admission, argv, preflight, capture and write audit remain inside
run_action. In particular, its None subprocess timeouts are not service-capped;
the contract's wall time is a separate Lunar budget.
"""

from dataclasses import asdict
import json
from pathlib import Path
from typing import Literal
from typing_extensions import TypedDict

import mathformer as hub
from adoption_check_tools import Context
from benchmark_route_tools import State, Initialized, Invoked, Advanced, Finished

ROUTE = "workflow.graphs"
ACTIONS = (
    "docs:workflow-graph-render",
    "docs:workflow-graph-layout",
    "control:workflow-skill-integration-audit",
)
ActionId = Literal[
    "docs:workflow-graph-render",
    "docs:workflow-graph-layout",
    "control:workflow-skill-integration-audit",
]


class Selected(TypedDict):
    action_id: ActionId


def selected_match(match):
    route = next(row for row in hub.build_intent_routes() if row.route_id == ROUTE)
    native = json.loads(json.dumps(asdict(route)))
    projected = match["route"]
    if (
        route.action_ids != ACTIONS
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
    for key, script in zip(
        ACTIONS,
        (
            "render_workflow_graphs.py",
            "plan_workflow_graph_layout.py",
            "audit_workflow_skill_integration.py",
        ),
    ):
        item = native[key]
        if (
            item.safety != "writes_artifacts"
            or item.writes != ("artifacts/workflow_graphs/",)
            or item.depends_on
            or item.timeout_seconds is not None
            or item.allows_extra_args
            or item.command != ("{python}", "scripts/" + script, "--json")
        ):
            raise ValueError("workflow graph capability changed; requalify the binding")
    if any(
        key not in ACTIONS or value != hub.action_to_dict(native[key])
        for key, value in projection.items()
    ):
        raise ValueError("registry projection differs from the native declaration")
    # Missing actions retain native unknown_action/metadata failure behavior.
    return {key: native[key] for key in projection}


def check_state(state, *, selecting=False):
    count = len(state["children"])
    if count > len(ACTIONS) or (selecting and count == len(ACTIONS)):
        raise ValueError("route cursor is out of bounds")
    if state["ok"] != all(bool(child.get("ok", False)) for child in state["children"]):
        raise ValueError("inconsistent route accumulator")


def register_workflow_graphs_route_tools(mcp, authorize, path_allowed):
    @mcp.tool()
    def mathformer_workflow_graphs_initialize() -> Initialized:
        return {"state": hub.initialize_intent_state()}

    @mcp.tool()
    def mathformer_workflow_graphs_select(state: State, match: dict) -> Selected:
        check_state(state, selecting=True)
        return {"action_id": hub.select_intent_action(state, selected_match(match))}

    @mcp.tool()
    def mathformer_workflow_graphs_execute(
        action_id: ActionId,
        context: Context,
        registry: dict,
        repository_root: str | None = None,
    ) -> Invoked:
        if action_id not in ACTIONS:
            raise ValueError("action is outside the selected route")
        native = checked_registry(registry)
        root = (
            hub.REPO_ROOT
            if repository_root is None
            else Path(repository_root).resolve()
        )
        if not context["dry_run"] and action_id in native:
            authorize()
            if any(not path_allowed(root / path) for path in native[action_id].writes):
                raise ValueError(
                    "workflow graph writes outside configured service roots"
                )
        return {
            "child": hub.run_action(
                action_id, native, hub.RunContext(**context), repository_root=root
            )
        }

    @mcp.tool()
    def mathformer_workflow_graphs_advance(
        state: State, child: dict, context: Context
    ) -> Advanced:
        check_state(state, selecting=True)
        updated, done = hub.advance_intent_state(
            state, child, hub.RunContext(**context), len(ACTIONS)
        )
        return {"state": updated, "done": done}

    @mcp.tool()
    def mathformer_workflow_graphs_finish(
        state: State, match: dict, registry: dict
    ) -> Finished:
        check_state(state)
        if not state["children"] or (
            len(state["children"]) < len(ACTIONS) and state["ok"]
        ):
            raise ValueError("route completion requires exhaustion or failed child")
        return {
            "result": hub.finish_intent_state(
                state, selected_match(match), checked_registry(registry)
            )
        }
