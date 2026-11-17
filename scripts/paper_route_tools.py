# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Value ports for the selected paper.workflow native route.

The hub owns execution, dependency traversal, preflight, argv, capture and write
audits. Wire registries are checked projections, never executable declarations.
These steps use the selected source's native timeouts; the general ask/run MCP
entrypoints continue to apply their separate configurable leaf timeout cap.
"""

from dataclasses import asdict
import json
from pathlib import Path
from typing import Literal
from typing_extensions import TypedDict

import mathformer as hub
from adoption_check_tools import Context

ROUTE = "paper.workflow"
ACTIONS = ("paper:functionality-update-suite", "paper:workflow-catalog")
DEPENDENCIES = (
    "paper:evidence-packet",
    "paper:update-plan",
    "paper:claim-audit-framework",
    "paper:claim-audit-rfde",
)
ActionId = Literal["paper:functionality-update-suite", "paper:workflow-catalog"]


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


def selected_match(match):
    """Hydrate source route metadata while retaining scoring observations."""
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
    """Reconstruct native objects without filling absent caller registry entries."""
    native = hub.build_registry()
    if native[ACTIONS[0]].depends_on != DEPENDENCIES:
        raise ValueError("paper suite dependencies changed; requalify binding")
    for key in (*ACTIONS, *DEPENDENCIES):
        item = native[key]
        expected = (
            DEPENDENCIES
            if key == ACTIONS[0]
            else (("paper:evidence-packet",) if key in DEPENDENCIES[1:] else ())
        )
        if (
            item.depends_on != expected
            or item.writes != ("artifacts/paper_skills/",)
            or item.safety != "writes_artifacts"
            or item.required_tools
            or item.timeout_seconds is not None
            or item.allows_extra_args
        ):
            raise ValueError("paper action capabilities changed; requalify binding")
    if any(
        key not in native or value != hub.action_to_dict(native[key])
        for key, value in projection.items()
    ):
        raise ValueError("registry projection differs from the native declaration")
    return {key: native[key] for key in projection}


def check_state(state, *, selecting=False):
    count = len(state["children"])
    if count > len(ACTIONS) or (selecting and count == len(ACTIONS)):
        raise ValueError("route cursor is out of bounds")
    if state["ok"] != all(bool(child.get("ok", False)) for child in state["children"]):
        raise ValueError("inconsistent route accumulator")


def register_paper_route_tools(mcp, authorize, path_allowed):
    @mcp.tool()
    def mathformer_paper_route_initialize() -> Initialized:
        return {"state": hub.initialize_intent_state()}

    @mcp.tool()
    def mathformer_paper_route_select_action(state: State, match: dict) -> Selected:
        check_state(state, selecting=True)
        return {"action_id": hub.select_intent_action(state, selected_match(match))}

    @mcp.tool()
    def mathformer_paper_route_run_child(
        action_id: ActionId,
        registry: dict,
        context: Context,
        repository_root: str | None = None,
    ) -> Invoked:
        if action_id not in ACTIONS:
            raise ValueError("action is outside the selected route")
        native = checked_registry(registry)
        mount = (
            {}
            if repository_root is None
            else {"repository_root": Path(repository_root).resolve()}
        )
        root = mount.get("repository_root", hub.REPO_ROOT)
        if not context["dry_run"] and action_id in native:
            authorize()
            # Every reachable paper action writes this root; check the actual
            # mount, including symlinks, before entering native traversal.
            if not path_allowed(root / "artifacts/paper_skills"):
                raise PermissionError("paper writes outside configured service roots")
        return {
            "child": hub.run_action(
                action_id, native, hub.RunContext(**context), **mount
            )
        }

    @mcp.tool()
    def mathformer_paper_route_advance(
        state: State, child: dict, context: Context, action_count: Literal[2]
    ) -> Advanced:
        check_state(state, selecting=True)
        if action_count != len(ACTIONS):
            raise ValueError("selected route has exactly two actions")
        updated, done = hub.advance_intent_state(
            state, child, hub.RunContext(**context), action_count
        )
        return {"state": updated, "done": done}

    @mcp.tool()
    def mathformer_paper_route_finish(
        state: State, match: dict, registry: dict
    ) -> Finished:
        check_state(state)
        if not state["children"] or (
            len(state["children"]) < len(ACTIONS) and state["ok"]
        ):
            raise ValueError("route completion requires exhaustion or a failed child")
        return {
            "result": hub.finish_intent_state(
                state, selected_match(match), checked_registry(registry)
            )
        }
