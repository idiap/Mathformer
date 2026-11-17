# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable JSON ports for the native skills.plugin-sync route.

The registry projection selects native declarations, never executable caller
code. A positive leaf timeout may preserve the MCP caller's capped registry;
None preserves CLI behavior. No enclosing native deadline is introduced.
"""

from dataclasses import asdict, replace
import json
from pathlib import Path
from typing import Literal
from typing_extensions import TypedDict

import mathformer as hub
from adoption_check_tools import Context

ROUTE = "skills.plugin-sync"
ACTIONS = ("skills:plugin-sync", "skills:plugin-check")
WRITES = ("plugins/mathformer/", ".agents/plugins/", ".claude-plugin/")
ActionId = Literal["skills:plugin-sync", "skills:plugin-check"]


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
    """Hydrate the source route, retaining caller-owned ranking evidence."""
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
    """Restore native actions, accepting only the native MCP timeout override."""
    native = hub.build_registry()
    commands = (
        ("{python}", "scripts/sync_agent_plugins.py"),
        ("{python}", "scripts/sync_agent_plugins.py", "--check"),
    )
    paths = (
        ("scripts/sync_agent_plugins.py", "skills/"),
        ("scripts/sync_agent_plugins.py", "skills/"),
    )
    for index, key in enumerate(ACTIONS):
        item = native[key]
        if (
            item.command != commands[index]
            or item.required_paths != paths[index]
            or item.safety != ("writes_environment" if index == 0 else "read_only")
            or item.writes != (WRITES if index == 0 else ())
            or item.depends_on
            or item.required_tools
            or item.timeout_seconds is not None
            or item.allows_extra_args
        ):
            raise ValueError(
                "plugin synchronization capability changed; requalify the binding"
            )
    restored = {}
    for key, value in projection.items():
        if key not in native:
            raise ValueError("registry projection differs from the native declaration")
        timeout = value.get("timeout_seconds")
        if timeout is not None and (type(timeout) is not int or timeout <= 0):
            raise ValueError("leaf timeout must be a positive integer or null")
        item = replace(native[key], timeout_seconds=timeout)
        if value != hub.action_to_dict(item):
            raise ValueError("registry projection differs from the native declaration")
        restored[key] = item
    return restored


def check_state(state, *, selecting=False):
    count = len(state["children"])
    if count > len(ACTIONS) or (selecting and count >= len(ACTIONS)):
        raise ValueError("route cursor is out of bounds")
    if state["ok"] != all(bool(child.get("ok", False)) for child in state["children"]):
        raise ValueError("inconsistent route accumulator")


def register_skills_plugin_sync_route_tools(mcp, authorize, path_allowed):
    """Bind every graph operation to the implementation used by the CLI."""

    @mcp.tool()
    def mathformer_skills_plugin_sync_route_initialize() -> Initialized:
        return {"state": hub.initialize_intent_state()}

    @mcp.tool()
    def mathformer_skills_plugin_sync_route_select(
        state: State, match: dict
    ) -> Selected:
        check_state(state, selecting=True)
        return {"action_id": hub.select_intent_action(state, selected_match(match))}

    @mcp.tool()
    def mathformer_skills_plugin_sync_route_run(
        action_id: ActionId,
        registry: dict,
        context: Context,
        repository_root: str | None = None,
    ) -> Invoked:
        if action_id not in ACTIONS:
            raise ValueError("action is outside the selected route")
        mount = (
            {}
            if repository_root is None
            else {"repository_root": Path(repository_root).resolve()}
        )
        native = checked_registry(registry)
        if not context["dry_run"] and action_id == ACTIONS[0] and action_id in native:
            authorize()
            root = mount.get("repository_root", hub.REPO_ROOT)
            if any(not path_allowed(root / path) for path in native[action_id].writes):
                raise ValueError(
                    "plugin synchronization writes outside configured service roots"
                )
        return {
            "child": hub.run_action(
                action_id, native, hub.RunContext(**context), **mount
            )
        }

    @mcp.tool()
    def mathformer_skills_plugin_sync_route_advance(
        state: State, child: dict, context: Context, action_count: Literal[2]
    ) -> Advanced:
        check_state(state, selecting=True)
        if action_count != len(ACTIONS):
            raise ValueError("action count differs from the selected route")
        updated, done = hub.advance_intent_state(
            state, child, hub.RunContext(**context), action_count
        )
        return {"state": updated, "done": done}

    @mcp.tool()
    def mathformer_skills_plugin_sync_route_finish(
        state: State, match: dict, registry: dict
    ) -> Finished:
        check_state(state)
        if not state["children"] or (
            len(state["children"]) < len(ACTIONS) and state["ok"]
        ):
            raise ValueError(
                "route completion requires exhaustion or a failed observation"
            )
        return {
            "result": hub.finish_intent_state(
                state, selected_match(match), checked_registry(registry)
            )
        }
