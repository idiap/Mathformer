# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP ports for test.runner, using the same steps as run_intent_match.

JSON registry projections select native declarations; they never install argv.
Recursive traversal, preflight, output capture and write audits stay in the hub.
"""

from dataclasses import asdict
import json
from pathlib import Path
from typing import Literal
from typing_extensions import TypedDict

import mathformer as hub

ACTION = "test:quick"
ROUTE = "test.runner"


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
    action_id: Literal["test:quick"]


class Invoked(TypedDict):
    child: dict


class Advanced(TypedDict):
    state: State
    done: bool


class Finished(TypedDict):
    result: dict


def selected_match(match):
    """Materialize only the selected route, retaining native score/evidence."""
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
    """Resolve caller-selected native entries, including intentional omissions."""
    native = hub.build_registry()
    item = native[ACTION]
    if (
        item.command != ("{python}", "tests/run_quick.py", "--json")
        or item.depends_on
        or item.writes != ("artifacts/",)
        or item.timeout_seconds is not None
    ):
        raise ValueError("test.runner changed; requalify the binding")
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


def register_test_runner_route_tools(mcp, authorize, path_allowed, cap_timeouts):
    @mcp.tool()
    def mathformer_test_runner_route_initialize() -> Initialized:
        return {"state": hub.initialize_intent_state()}

    @mcp.tool()
    def mathformer_test_runner_route_select(state: State, match: dict) -> Selected:
        check_state(state, selecting=True)
        return {"action_id": hub.select_intent_action(state, selected_match(match))}

    @mcp.tool()
    def mathformer_test_runner_route_run_action(
        action_id: Literal["test:quick"],
        registry: dict,
        context: Context,
        repository_root: str | None = None,
    ) -> Invoked:
        if action_id != ACTION:
            raise ValueError("action is outside the selected route")
        native = checked_registry(registry)
        kwargs = (
            {}
            if repository_root is None
            else {"repository_root": Path(repository_root).resolve()}
        )
        root = kwargs.get("repository_root", hub.REPO_ROOT)
        if not context["dry_run"]:
            authorize()
            pending, seen = [action_id], set()
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
            "child": hub.run_action(
                action_id, cap_timeouts(native), hub.RunContext(**context), **kwargs
            )
        }

    @mcp.tool()
    def mathformer_test_runner_route_advance(
        state: State,
        child: dict,
        context: Context,
        action_count: Literal[1],
    ) -> Advanced:
        check_state(state, selecting=True)
        if action_count != 1:
            raise ValueError("selected route has exactly one action")
        updated, done = hub.advance_intent_state(
            state, child, hub.RunContext(**context), action_count
        )
        return {"state": updated, "done": done}

    @mcp.tool()
    def mathformer_test_runner_route_finish(
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
