# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP ports for the native, single-action setup.python.all route.

JSON inputs select native objects, never replacement commands or route metadata.
The original entrypoint and these tools share the intent-state functions and
run_action, including its output capture, preflight and filesystem write audit.
Registry timeout_seconds carries the native CLI (null) or MCP capped timeout.
The enclosing contract budget belongs to Lunar and does not replace that timeout.
"""

from dataclasses import asdict, replace
import json
from pathlib import Path
from typing import Literal, Optional
from typing_extensions import TypedDict

import mathformer as hub
from adoption_check_tools import Context

ACTION = "setup:python-all"
ROUTE = "setup.python.all"


class State(TypedDict):
    ok: bool
    children: list[dict]


class Initialized(TypedDict):
    state: State


class Selected(TypedDict):
    action_id: Literal["setup:python-all"]


class Invoked(TypedDict):
    child: dict


class Advanced(TypedDict):
    state: State
    done: bool


class Finished(TypedDict):
    result: dict


def selected_match(match):
    """Hydrate authoritative route metadata and preserve scoring evidence."""
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
    """Resolve exact native registrations; caller JSON cannot supply code."""
    native = hub.build_registry()
    item = native[ACTION]
    if (
        item.command
        != ("uv", "run", "python", "scripts/install_env.py", "--all-extras")
        or item.depends_on
        or item.safety != "writes_environment"
        or item.writes != (".venv/",)
        or item.required_paths != ("scripts/install_env.py",)
        or item.required_tools != ("uv",)
        or item.timeout_seconds is not None
        or item.allows_extra_args
    ):
        raise ValueError("setup capability changed; requalify the binding")
    required = {
        "command",
        "depends_on",
        "safety",
        "writes",
        "timeout_seconds",
        "required_paths",
        "required_tools",
        "allows_extra_args",
    }
    if ACTION not in projection or not required <= projection[ACTION].keys():
        raise ValueError("selected registration is incomplete")
    hydrated = {}
    for key, fields in projection.items():
        if key not in native:
            raise ValueError("registry projection differs from the native declaration")
        timeout = fields.get("timeout_seconds", native[key].timeout_seconds)
        if timeout is not None and (type(timeout) is not int or timeout < 1):
            raise ValueError("timeout_seconds must be null or a positive integer")
        item = replace(native[key], timeout_seconds=timeout)
        expected = hub.action_to_dict(item)
        if any(
            name not in expected or value != expected[name]
            for name, value in fields.items()
        ):
            raise ValueError("registry projection differs from the native declaration")
        hydrated[key] = item
    return hydrated


def check_state(state, *, selecting=False):
    count = len(state["children"])
    if count > 1 or (selecting and count != 0):
        raise ValueError("route cursor is out of bounds")
    if state["ok"] != all(bool(child.get("ok", False)) for child in state["children"]):
        raise ValueError("inconsistent route accumulator")


def register_setup_python_all_route_tools(mcp, authorize, path_allowed):
    @mcp.tool()
    def mathformer_setup_python_all_route_initialize() -> Initialized:
        return {"state": hub.initialize_intent_state()}

    @mcp.tool()
    def mathformer_setup_python_all_route_select(state: State, match: dict) -> Selected:
        check_state(state, selecting=True)
        return {"action_id": hub.select_intent_action(state, selected_match(match))}

    @mcp.tool()
    def mathformer_setup_python_all_route_run_action(
        action_id: Literal["setup:python-all"],
        registry: dict,
        context: Context,
        repository_root: Optional[str],
    ) -> Invoked:
        if action_id != ACTION:
            raise ValueError("action is outside the selected route")
        native = checked_registry(registry)
        mount = (
            {}
            if repository_root is None
            else {"repository_root": Path(repository_root).resolve()}
        )
        root = mount.get("repository_root", hub.REPO_ROOT)
        if not context["dry_run"]:
            authorize()
            if any(not path_allowed(root / path) for path in native[ACTION].writes):
                raise ValueError("setup writes outside configured service roots")
        return {
            "child": hub.run_action(ACTION, native, hub.RunContext(**context), **mount)
        }

    @mcp.tool()
    def mathformer_setup_python_all_route_advance(
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
    def mathformer_setup_python_all_route_finish(
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
