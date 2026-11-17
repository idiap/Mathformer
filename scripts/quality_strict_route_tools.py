# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Typed MCP bindings for the source-owned quality.strict route.

The hub retains admission, preflight, dry-run, process capture and write audit.
The strict leaf timeout remains the native 3600 seconds; Lunar enforces its
enclosing budget. Registry values select native declarations, never new code.
"""

from dataclasses import asdict
import json
from pathlib import Path
from typing import Literal
from typing_extensions import TypedDict

import mathformer as hub
from adoption_check_tools import Context

ACTION = "quality:strict"
ROUTE = "quality.strict"


class Mount(TypedDict, total=False):
    repository_root: str


class State(TypedDict):
    ok: bool
    children: list[dict]


class Initialized(TypedDict):
    state: State


class Selected(TypedDict):
    action: Literal["quality:strict"]


class Invoked(TypedDict):
    result: dict


class Advanced(TypedDict):
    state: State
    done: bool


class Finished(TypedDict):
    result: dict


def selected_match(match):
    """Restore the native route while preserving caller scoring evidence."""
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
    item, leaf = native[ACTION], native["test:comprehensive-strict"]
    if (
        item.depends_on != ("control:all", "test:comprehensive-strict")
        or item.command
        or leaf.command
        != (
            "{python}",
            "tests/test_program/run_comprehensive_tests.py",
            "--module-family",
            "all",
            "--profile",
            "strict",
            "--write-jsonl",
            "--write-junit",
            "--json",
        )
        or leaf.timeout_seconds != 3600
    ):
        raise ValueError("strict quality capability changed; requalify the binding")
    if any(
        key not in native or value != hub.action_to_dict(native[key])
        for key, value in projection.items()
    ):
        raise ValueError("registry projection differs from the native declaration")
    # An absent action retains native unknown_action and finish's KeyError.
    return {key: native[key] for key in projection}


def check_state(state, *, selecting=False):
    count = len(state["children"])
    if count > 1 or (selecting and count != 0):
        raise ValueError("route cursor is out of bounds")
    if state["ok"] != all(bool(child.get("ok", False)) for child in state["children"]):
        raise ValueError("inconsistent route accumulator")


def register_quality_strict_route_tools(mcp, authorize, path_allowed):
    @mcp.tool()
    def mathformer_quality_strict_route_initialize() -> Initialized:
        return {"state": hub.initialize_intent_state()}

    @mcp.tool()
    def mathformer_quality_strict_route_select(state: State, match: dict) -> Selected:
        check_state(state, selecting=True)
        return {"action": hub.select_intent_action(state, selected_match(match))}

    @mcp.tool()
    def mathformer_quality_strict_route_execute(
        action: Literal["quality:strict"],
        registry: dict,
        context: Context,
        mount: Mount,
    ) -> Invoked:
        if action != ACTION:
            raise ValueError("action is outside the selected route")
        if set(mount) - {"repository_root"}:
            raise ValueError("unknown repository mount field")
        native = checked_registry(registry)
        kwargs = (
            {}
            if "repository_root" not in mount
            else {"repository_root": Path(mount["repository_root"]).resolve()}
        )
        root = kwargs.get("repository_root", hub.REPO_ROOT)
        if not context["dry_run"]:
            authorize()
            pending, seen = [action], set()
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
            "result": hub.run_action(
                action, native, hub.RunContext(**context), **kwargs
            )
        }

    @mcp.tool()
    def mathformer_quality_strict_route_advance(
        state: State, child: dict, context: Context
    ) -> Advanced:
        check_state(state, selecting=True)
        updated, done = hub.advance_intent_state(
            state, child, hub.RunContext(**context), 1
        )
        return {"state": updated, "done": done}

    @mcp.tool()
    def mathformer_quality_strict_route_finish(
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
