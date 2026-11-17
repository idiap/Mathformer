# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""JSON ports over the native two-action Codex judge route.

Registry projections select native capabilities; they never supply executable
commands. The accumulator is carried by the caller, with no retained route state.
"""

from dataclasses import asdict
import json
from pathlib import Path
from typing import Literal
from typing_extensions import TypedDict

import mathformer as hub
from adoption_check_tools import Context
from benchmark_route_tools import State, Initialized, Invoked, Advanced, Finished

ROUTE = "report.formalphysics.codex_exec_judges"
SOURCE = "skills/physics-common/formalphysics-judge-synthesis-reporter/scripts/run_codex_exec_judges.py"
ACTIONS = (
    "physics-lean:formalphysics-codex-exec-judge-runner-self-test",
    "physics-lean:formalphysics-codex-exec-judge-runner",
)
ActionId = Literal[
    "physics-lean:formalphysics-codex-exec-judge-runner-self-test",
    "physics-lean:formalphysics-codex-exec-judge-runner",
]


class Selected(TypedDict):
    action_id: ActionId


def selected_match(match):
    """Restore source-owned metadata while retaining caller matching evidence."""
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
    """Materialize the caller's registry subset without accepting altered argv."""
    native = hub.build_registry()
    for index, action in enumerate(ACTIONS):
        item = native[action]
        tail = ("--self-test", "--json") if index == 0 else ("--limit", "1", "--json")
        if (
            item.command != ("{python}", SOURCE, *tail)
            or item.depends_on
            or item.timeout_seconds != (120, 1200)[index]
            or item.safety != "writes_artifacts"
            or item.writes
            != ("artifacts/formalphysics_judge_synthesis/codex_exec_judges/",)
        ):
            raise ValueError("native judge capability changed; requalify binding")
    if any(
        key not in native or value != hub.action_to_dict(native[key])
        for key, value in projection.items()
    ):
        raise ValueError("registry projection differs from native declaration")
    return {key: native[key] for key in projection}


def check_state(state, *, selecting=False):
    count = len(state["children"])
    if count > 2 or (selecting and count >= 2):
        raise ValueError("route cursor is out of bounds")
    if state["ok"] != all(bool(child.get("ok", False)) for child in state["children"]):
        raise ValueError("inconsistent route accumulator")


def register_codex_exec_judges_route_tools(
    mcp, authorize=lambda: None, path_allowed=lambda path: True
):
    @mcp.tool()
    def mathformer_codex_exec_judges_initialize_intent_state() -> Initialized:
        return {"state": hub.initialize_intent_state()}

    @mcp.tool()
    def mathformer_codex_exec_judges_select_intent_action(
        state: State, match: dict
    ) -> Selected:
        check_state(state, selecting=True)
        return {"action_id": hub.select_intent_action(state, selected_match(match))}

    @mcp.tool()
    def mathformer_codex_exec_judges_run_action(
        action_id: ActionId,
        context: Context,
        registry: dict,
        repository_root: str | None,
    ) -> Invoked:
        if action_id not in ACTIONS:
            raise ValueError("action is outside the selected route")
        native = checked_registry(registry)
        root = (
            hub.REPO_ROOT
            if repository_root is None
            else Path(repository_root).resolve()
        )
        if not context["dry_run"]:
            authorize()
            if action_id in native and any(
                not path_allowed(root / path) for path in native[action_id].writes
            ):
                raise PermissionError("judge writes outside configured service roots")
        return {
            "child": hub.run_action(
                action_id, native, hub.RunContext(**context), repository_root=root
            )
        }

    @mcp.tool()
    def mathformer_codex_exec_judges_advance_intent_state(
        state: State, child: dict, context: Context, action_count: Literal[2]
    ) -> Advanced:
        check_state(state, selecting=True)
        if action_count != 2:
            raise ValueError("selected route has exactly two actions")
        updated, done = hub.advance_intent_state(
            state, child, hub.RunContext(**context), action_count
        )
        return {"state": updated, "done": done}

    @mcp.tool()
    def mathformer_codex_exec_judges_finish_intent_state(
        state: State, match: dict, registry: dict
    ) -> Finished:
        check_state(state)
        if not state["children"]:
            raise ValueError("route completion requires child observations")
        return {
            "result": hub.finish_intent_state(
                state, selected_match(match), checked_registry(registry)
            )
        }
