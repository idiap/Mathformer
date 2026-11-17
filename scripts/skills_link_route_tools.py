# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable skills.link ports sharing the native intent controller and actions.

JSON registry values select source-owned declarations, never executable code.
The native actions retain their unbounded subprocess timeouts; Lunar owns the
enclosing contract budget. No provider or alternative execution mode is used.
"""

from dataclasses import asdict
import json
from pathlib import Path
from typing import Literal
from typing_extensions import TypedDict

import mathformer as hub
from adoption_check_tools import Context

ROUTE = "skills.link"
ACTIONS = ("skills:link", "skills:client-discovery")
WRITES = (".agents/skills/", ".claude/skills/", ".opencode/skills/")


class State(TypedDict):
    ok: bool
    children: list[dict]


class Initialized(TypedDict):
    state: State


class Selected(TypedDict):
    action: Literal["skills:link", "skills:client-discovery"]


class Invoked(TypedDict):
    child: dict


class Advanced(TypedDict):
    state: State
    done: bool


class Finished(TypedDict):
    result: dict


def selected_match(match):
    """Restore native metadata while retaining the caller's scoring evidence."""
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
    """Resolve exact native registrations, including native missing-entry paths."""
    native = hub.build_registry()
    commands = (
        (
            "{python}",
            "scripts/link_agent_skills.py",
            "--profile",
            "all-repo",
            "--mode",
            "auto",
            "--replace",
        ),
        ("{python}", "tests/agent_clients/run_skill_client_discovery.py", "--json"),
    )
    paths = (
        ("scripts/link_agent_skills.py", "skills/"),
        ("tests/agent_clients/run_skill_client_discovery.py", "skills/"),
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
            raise ValueError("skills capability changed; requalify the binding")
    if any(
        key not in native or value != hub.action_to_dict(native[key])
        for key, value in projection.items()
    ):
        raise ValueError("registry projection differs from the native declaration")
    return {key: native[key] for key in projection}


def check_state(state, *, selecting=False):
    count = len(state["children"])
    if count > 2 or (selecting and count >= 2):
        raise ValueError("route cursor is out of bounds")
    if state["ok"] != all(bool(child.get("ok", False)) for child in state["children"]):
        raise ValueError("inconsistent route accumulator")


def register_skills_link_route_tools(mcp, authorize, path_allowed):
    def invoke(action_id, registry, context, repository_root):
        native = checked_registry(registry)
        mount = (
            {}
            if repository_root is None
            else {"repository_root": Path(repository_root).resolve()}
        )
        root = mount.get("repository_root", hub.REPO_ROOT)
        if not context["dry_run"] and action_id == ACTIONS[0] and action_id in native:
            authorize()
            if any(not path_allowed(root / path) for path in native[action_id].writes):
                raise ValueError(
                    "skill publication writes outside configured service roots"
                )
        return {
            "child": hub.run_action(
                action_id, native, hub.RunContext(**context), **mount
            )
        }

    @mcp.tool()
    def mathformer_skills_link_route_initialize() -> Initialized:
        return {"state": hub.initialize_intent_state()}

    @mcp.tool()
    def mathformer_skills_link_route_select(state: State, match: dict) -> Selected:
        check_state(state, selecting=True)
        return {"action": hub.select_intent_action(state, selected_match(match))}

    @mcp.tool()
    def mathformer_skills_link_route_link(
        context: Context, registry: dict, repository_root: str | None = None
    ) -> Invoked:
        return invoke(ACTIONS[0], registry, context, repository_root)

    @mcp.tool()
    def mathformer_skills_link_route_discovery(
        context: Context, registry: dict, repository_root: str | None = None
    ) -> Invoked:
        return invoke(ACTIONS[1], registry, context, repository_root)

    @mcp.tool()
    def mathformer_skills_link_route_advance(
        state: State, child: dict, context: Context
    ) -> Advanced:
        check_state(state, selecting=True)
        updated, done = hub.advance_intent_state(
            state, child, hub.RunContext(**context), len(ACTIONS)
        )
        return {"state": updated, "done": done}

    @mcp.tool()
    def mathformer_skills_link_route_finish(
        state: State, match: dict, registry: dict
    ) -> Finished:
        check_state(state)
        if not state["children"] or (len(state["children"]) < 2 and state["ok"]):
            raise ValueError(
                "route completion requires exhaustion or a failed observation"
            )
        return {
            "result": hub.finish_intent_state(
                state, selected_match(match), checked_registry(registry)
            )
        }
