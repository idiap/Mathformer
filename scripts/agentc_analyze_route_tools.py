# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable blocks for the selected native AgentC analysis route.

The route passes no analyzer arguments and has no dependencies. This adapter
retains the CLI's uncapped subprocess boundary; Lunar owns the workflow budget.
The repository mount is explicit and shared by preflight, cwd and write audits.
"""

from pathlib import Path
from typing_extensions import TypedDict
import mathformer as hub


class Context(TypedDict):
    dry_run: bool
    json_output: bool
    keep_going: bool
    allow_mutating: bool
    write_report: bool


class Match(TypedDict):
    score: int
    matched_terms: list[str]


class State(TypedDict):
    ok: bool
    children: list[dict]


class Initialized(TypedDict):
    state: State


class Invoked(TypedDict):
    child: dict


class Advanced(TypedDict):
    state: State
    done: bool


class Finished(TypedDict):
    result: dict


def selected_match(match):
    route = next(
        route
        for route in hub.build_intent_routes()
        if route.route_id == "agentc.analyze"
    )
    if route.action_ids != ("agentc:analyze-logs",):
        raise ValueError(
            "AgentC analysis route changed: regenerate the one-action contract"
        )
    return hub.IntentMatch(route, match["score"], tuple(match["matched_terms"]))


def register_agentc_analyze_route_tools(
    mcp, authorize=lambda: None, path_allowed=lambda path: True
):
    """Expose the exact shared controller blocks with typed MCP envelopes."""

    @mcp.tool()
    def mathformer_agentc_analyze_route_initialize() -> Initialized:
        return {"state": hub.initialize_intent_state()}

    @mcp.tool()
    def mathformer_agentc_analyze_route_invoke_action(
        context: Context, repository_root: str
    ) -> Invoked:
        route = selected_match({"score": 0, "matched_terms": []}).route
        root = Path(repository_root).resolve()
        registry = hub.build_registry()
        item = registry[route.action_ids[0]]
        if item.depends_on:
            raise ValueError(
                "AgentC analysis action gained dependencies: regenerate contract"
            )
        if not context["dry_run"]:
            authorize()
            if any(not path_allowed(root / path) for path in item.writes):
                raise ValueError(
                    "AgentC analysis writes outside configured service roots"
                )
        return {
            "child": hub.run_action(
                item.action_id,
                registry,
                hub.RunContext(**context),
                repository_root=root,
            )
        }

    @mcp.tool()
    def mathformer_agentc_analyze_route_advance(
        state: State, child: dict, context: Context
    ) -> Advanced:
        if state != hub.initialize_intent_state():
            raise ValueError("one-action route requires its initial accumulator")
        updated, done = hub.advance_intent_state(
            state, child, hub.RunContext(**context), 1
        )
        return {"state": updated, "done": done}

    @mcp.tool()
    def mathformer_agentc_analyze_route_finish(state: State, match: Match) -> Finished:
        if len(state["children"]) != 1 or state["ok"] != bool(
            state["children"][0].get("ok", False)
        ):
            raise ValueError("one-action route requires exactly one consistent child")
        return {
            "result": hub.finish_intent_state(
                state, selected_match(match), hub.build_registry()
            )
        }
