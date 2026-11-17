# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""JSON ports over the native textbook.autoformalization route accumulator and controller.

Transported declarations assert native selections; they cannot install commands.
The CLI and these ports share every execution and aggregation implementation.
"""

from dataclasses import asdict
import json
from pathlib import Path
from typing import Literal
from typing_extensions import TypedDict

import mathformer as hub

ACTION = "test:family:textbook"
ROUTE = "textbook.autoformalization"


class Context(TypedDict):
    dry_run: bool
    json_output: bool
    keep_going: bool
    allow_mutating: bool
    write_report: bool


class State(TypedDict):
    ok: bool
    children: list[dict]


class Initialized(TypedDict):
    state: State


class Selected(TypedDict):
    action: Literal["test:family:textbook"]


class Invoked(TypedDict):
    child: dict


class Advanced(TypedDict):
    state: State
    done: bool


class Finished(TypedDict):
    result: dict


def selected_match(match):
    route = next(row for row in hub.build_intent_routes() if row.route_id == ROUTE)
    native = json.loads(json.dumps(asdict(route)))
    projection = match["route"]
    if (
        route.action_ids != (ACTION,)
        or not {"route_id", "action_ids"} <= projection.keys()
        or any(
            key not in native or value != native[key]
            for key, value in projection.items()
        )
    ):
        raise ValueError("selected route differs from the native declaration")
    return hub.IntentMatch(route, match["score"], tuple(match["matched_terms"]))


def checked_registry(projection):
    native = hub.build_registry()
    item = native[ACTION]
    if (
        item.command
        != (
            "{python}",
            "tests/test_program/run_comprehensive_tests.py",
            "--module-family",
            "textbook",
            "--json",
        )
        or item.depends_on
        or item.timeout_seconds != 900
    ):
        raise ValueError("Textbook action changed; requalify the binding")
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


def register_textbook_route_tools(mcp, authorize, path_allowed):
    @mcp.tool()
    def mathformer_textbook_route_initialize() -> Initialized:
        return {"state": hub.initialize_intent_state()}

    @mcp.tool()
    def mathformer_textbook_route_select(state: State, match: dict) -> Selected:
        check_state(state, selecting=True)
        return {"action": hub.select_intent_action(state, selected_match(match))}

    @mcp.tool()
    def mathformer_textbook_route_execute(
        action: Literal["test:family:textbook"],
        registry: dict,
        context: Context,
        repository_root: str | None = None,
    ) -> Invoked:
        if action != ACTION:
            raise ValueError("action is outside the selected route")
        native = checked_registry(registry)
        mount = (
            {}
            if repository_root is None
            else {"repository_root": Path(repository_root).resolve()}
        )
        if not context["dry_run"]:
            authorize()
            root = mount.get("repository_root", hub.REPO_ROOT)
            if ACTION in native and any(
                not path_allowed(root / path) for path in native[ACTION].writes
            ):
                raise PermissionError(
                    "Textbook writes outside configured service roots"
                )
        return {
            "child": hub.run_action(action, native, hub.RunContext(**context), **mount)
        }

    @mcp.tool()
    def mathformer_textbook_route_advance(
        state: State,
        child: dict,
        context: Context,
        action_count: Literal[1],
    ) -> Advanced:
        check_state(state, selecting=True)
        if action_count != 1:
            raise ValueError("Textbook route requires exactly one action")
        updated, done = hub.advance_intent_state(
            state, child, hub.RunContext(**context), action_count
        )
        return {"state": updated, "done": done}

    @mcp.tool()
    def mathformer_textbook_route_finish(
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
