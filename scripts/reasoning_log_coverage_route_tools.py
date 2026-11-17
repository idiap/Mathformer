# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable native steps for the selected reasoning-log coverage route.

Wire registry values select native declarations, never caller commands. The
auditor remains an opaque native subprocess, with its uncapped finite scans and
unset timeout; Lunar owns the separate normalized workflow budget.
"""

from dataclasses import asdict
import json
from pathlib import Path
from typing import Literal
from typing_extensions import TypedDict

import mathformer as hub
from adoption_check_tools import Context
from benchmark_route_tools import State, Initialized, Invoked, Advanced, Finished
from scripts.workflow_write_audit import FileState

ACTION = "control:reasoning-log-coverage"
ROUTE = "control.reasoning.log.coverage"
ActionId = Literal["control:reasoning-log-coverage"]


class Selected(TypedDict):
    action_id: ActionId


class Boundary(TypedDict):
    execute: bool
    payload: dict
    snapshot: dict


class Prepared(TypedDict):
    boundary: Boundary


def selected_match(match):
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
    if item.safety != "read_only" or item.writes or item.depends_on:
        raise ValueError("coverage capability changed; requalify the binding")
    if any(
        key != ACTION or value != hub.action_to_dict(item)
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


def mounted(repository_root):
    return hub.REPO_ROOT if repository_root is None else Path(repository_root).resolve()


def register_reasoning_log_coverage_route_tools(mcp):
    @mcp.tool()
    def mathformer_coverage_route_initialize() -> Initialized:
        return {"state": hub.initialize_intent_state()}

    @mcp.tool()
    def mathformer_coverage_route_select_action(state: State, match: dict) -> Selected:
        check_state(state, selecting=True)
        return {"action_id": hub.select_intent_action(state, selected_match(match))}

    @mcp.tool()
    def mathformer_coverage_route_prepare_action(
        action_id: ActionId,
        context: Context,
        registry: dict,
        repository_root: str | None,
    ) -> Prepared:
        native = checked_registry(registry)
        root = mounted(repository_root)
        ctx = hub.RunContext(**context)
        prepared = hub.prepare_action(action_id, native, ctx, repository_root=root)
        if "result" in prepared:
            boundary = {"execute": False, "payload": prepared["result"], "snapshot": {}}
        else:
            boundary = hub.prepare_leaf_boundary(
                native[action_id], ctx, (), repository_root=root
            )
            boundary["snapshot"] = {
                key: asdict(value) for key, value in boundary["snapshot"].items()
            }
        return {"boundary": boundary}

    @mcp.tool()
    def mathformer_coverage_route_execute_audit(
        boundary: Boundary,
        context: Context,
        registry: dict,
        repository_root: str | None,
    ) -> Invoked:
        item = checked_registry(registry)[ACTION]
        root = mounted(repository_root)
        payload = boundary["payload"]
        if (
            not boundary["execute"]
            or context["dry_run"]
            or payload.get("argv") != hub.resolve_command(item.command)
            or payload.get("action") != hub.action_to_dict(item)
            or payload.get("cwd") != hub.rel(root)
            or payload.get("dry_run") is not False
            or payload.get("preflight_errors") != []
            or not payload.get("ok")
        ):
            raise ValueError("audit requires an executable native boundary")
        restored = {
            **boundary,
            "snapshot": {
                key: FileState(**value) for key, value in boundary["snapshot"].items()
            },
        }
        child = hub.launch_leaf_boundary(item, dict(payload), repository_root=root)
        return {
            "child": hub.finish_leaf_boundary(
                item, restored, child, repository_root=root
            )
        }

    @mcp.tool()
    def mathformer_coverage_route_return_boundary(boundary: Boundary) -> Invoked:
        if boundary["execute"]:
            raise ValueError("early return requires a stopped boundary")
        return {"child": boundary["payload"]}

    @mcp.tool()
    def mathformer_coverage_route_advance(
        state: State, child: dict, context: Context
    ) -> Advanced:
        check_state(state, selecting=True)
        updated, done = hub.advance_intent_state(
            state, child, hub.RunContext(**context), 1
        )
        return {"state": updated, "done": done}

    @mcp.tool()
    def mathformer_coverage_route_finish(
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
