# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable validate.lean.fixture route ports over the native hub executor.

Transported metadata selects source-owned declarations; it cannot introduce
commands. The native action retains its 300 second timeout and all preflight,
capture, scientific suite traversal and write-audit behavior. Lunar owns the outer budget.
"""

from dataclasses import asdict
import json
from pathlib import Path
from typing import Literal
from typing_extensions import TypedDict

import mathformer as hub
from adoption_check_tools import Context

ACTION = "lean:wiki-level-suite"
ROUTE = "validate.lean.fixture"


class State(TypedDict):
    ok: bool
    children: list[dict]


class Initialized(TypedDict):
    state: State


class Selected(TypedDict):
    action_id: Literal["lean:wiki-level-suite"]


class Invoked(TypedDict):
    child: dict


class Advanced(Initialized):
    done: bool


class Finished(TypedDict):
    result: dict


def selected_match(match):
    """Restore the native dataclass and preserve caller scoring evidence."""
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
    item = native[ACTION]
    if (
        item.command != ("{python}", "tests/wiki_level/run_suite.py", "--json")
        or item.depends_on
        or item.safety != "writes_artifacts"
        or item.writes != ("artifacts/wiki_level_suite/",)
        or item.required_paths != ("tests/wiki_level/run_suite.py",)
        or item.required_tools
        or item.timeout_seconds != 300
        or item.allows_extra_args
    ):
        raise ValueError("wiki-level Lean capability changed; requalify the binding")
    if any(
        key not in native or value != hub.action_to_dict(native[key])
        for key, value in projection.items()
    ):
        raise ValueError("registry projection differs from the native declaration")
    # Missing entries retain native unknown_action and finalization's KeyError.
    return {key: native[key] for key in projection}


def check_state(state, *, complete=False):
    if len(state["children"]) != int(complete):
        raise ValueError("route cursor is out of bounds")
    if state["ok"] != all(bool(child.get("ok", False)) for child in state["children"]):
        raise ValueError("inconsistent route accumulator")


def register_lean_fixture_route_tools(mcp, authorize, path_allowed):
    @mcp.tool()
    def mathformer_lean_fixture_route_initialize() -> Initialized:
        return {"state": hub.initialize_intent_state()}

    @mcp.tool()
    def mathformer_lean_fixture_route_select_action(
        state: State, match: dict
    ) -> Selected:
        check_state(state)
        return {"action_id": hub.select_intent_action(state, selected_match(match))}

    @mcp.tool()
    def mathformer_lean_fixture_route_invoke_action(
        action_id: Literal["lean:wiki-level-suite"],
        registry: dict,
        context: Context,
        repository_root: str | None = None,
    ) -> Invoked:
        if action_id != ACTION:
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
                raise PermissionError(
                    "wiki-level Lean writes outside configured service roots"
                )
        mount = {} if repository_root is None else {"repository_root": root}
        return {
            "child": hub.run_action(
                action_id, native, hub.RunContext(**context), **mount
            )
        }

    @mcp.tool()
    def mathformer_lean_fixture_route_advance(
        state: State,
        child: dict,
        context: Context,
        action_count: Literal[1],
    ) -> Advanced:
        check_state(state)
        if action_count != 1:
            raise ValueError("route has exactly one action")
        updated, done = hub.advance_intent_state(
            state, child, hub.RunContext(**context), action_count
        )
        return {"state": updated, "done": done}

    @mcp.tool()
    def mathformer_lean_fixture_route_finish(
        state: State, match: dict, registry: dict
    ) -> Finished:
        check_state(state, complete=True)
        return {
            "result": hub.finish_intent_state(
                state, selected_match(match), checked_registry(registry)
            )
        }
