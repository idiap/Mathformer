# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Typed MCP ports over the native, ordered judge-synthesis route.

The hub retains admission, preflight, subprocesses, timeouts and write auditing.
The JSON registry is a checked projection, never caller-supplied executable code.
"""

from pathlib import Path
from typing import Literal
from typing_extensions import TypedDict

import mathformer as hub
from adoption_check_tools import Context
from physics_coherence_route_tools import (
    State,
    Initialized,
    Invoked,
    Advanced,
    Finished,
)

ROUTE = "report.formalphysics.judge_synthesis"
SOURCE = "skills/physics-common/formalphysics-judge-synthesis-reporter/scripts/build_synthesis_report.py"
SMOKE = "tests/physics_lean/run_formalphysics_judge_synthesis_report.py"
ACTIONS = (
    "physics-lean:formalphysics-judge-synthesis-report-self-test",
    "physics-lean:formalphysics-judge-synthesis-report",
)
ActionId = Literal[
    "physics-lean:formalphysics-judge-synthesis-report-self-test",
    "physics-lean:formalphysics-judge-synthesis-report",
]


class Match(TypedDict):
    score: float
    matched_terms: list[str]


class Selected(TypedDict):
    action_id: ActionId


def selected_match(match):
    """Reconstruct fixed source-owned route metadata; retain matching evidence."""
    route = next(row for row in hub.build_intent_routes() if row.route_id == ROUTE)
    if route.action_ids != ACTIONS:
        raise ValueError("selected route changed; requalify binding")
    return hub.IntentMatch(route, match["score"], tuple(match["matched_terms"]))


def checked_registry(projection):
    """Resolve native capabilities, retaining missing-action failure behavior."""
    native = hub.build_registry()
    commands = (
        ("{python}", SMOKE, "--json"),
        (
            "{python}",
            SOURCE,
            "--comparative-report",
            "artifacts/formalphysics_comparative_analysis/hub_selected_examples_report/comparative_report.json",
            "--output-dir",
            "artifacts/formalphysics_judge_synthesis/hub_selected_examples",
            "--json",
        ),
    )
    for index, action_id in enumerate(ACTIONS):
        item = native[action_id]
        if (
            item.command != commands[index]
            or item.depends_on
            or item.timeout_seconds != (180, 300)[index]
            or item.safety != "writes_artifacts"
            or item.writes != ("artifacts/formalphysics_judge_synthesis/",)
        ):
            raise ValueError("native synthesis capability changed; requalify binding")
    if any(
        key not in native or value != hub.action_to_dict(native[key])
        for key, value in projection.items()
    ):
        raise ValueError("registry projection differs from native declaration")
    return {key: native[key] for key in projection}


def check_state(state, *, selecting=False):
    count = len(state["children"])
    if count > len(ACTIONS) or (selecting and count >= len(ACTIONS)):
        raise ValueError("route cursor is out of bounds")
    if state["ok"] != all(bool(child.get("ok", False)) for child in state["children"]):
        raise ValueError("inconsistent route accumulator")


def register_judge_synthesis_route_tools(mcp, authorize, path_allowed):
    @mcp.tool()
    def mathformer_judge_synthesis_route_initialize() -> Initialized:
        return {"state": hub.initialize_intent_state()}

    @mcp.tool()
    def mathformer_judge_synthesis_route_select_action(
        state: State, match: Match
    ) -> Selected:
        check_state(state, selecting=True)
        return {"action_id": hub.select_intent_action(state, selected_match(match))}

    @mcp.tool()
    def mathformer_judge_synthesis_route_execute_action(
        action_id: ActionId,
        registry: dict,
        context: Context,
        repository_root: str | None,
    ) -> Invoked:
        if action_id not in ACTIONS:
            raise ValueError("action is outside selected route")
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
                raise PermissionError(
                    "synthesis writes outside configured service roots"
                )
        # Deliberately no extra_args, environment rewrite or timeout override.
        return {
            "child": hub.run_action(
                action_id, native, hub.RunContext(**context), repository_root=root
            )
        }

    @mcp.tool()
    def mathformer_judge_synthesis_route_advance(
        state: State, child: dict, context: Context
    ) -> Advanced:
        check_state(state, selecting=True)
        updated, done = hub.advance_intent_state(
            state, child, hub.RunContext(**context), len(ACTIONS)
        )
        return {"state": updated, "done": done}

    @mcp.tool()
    def mathformer_judge_synthesis_route_finish(
        state: State, match: Match, registry: dict
    ) -> Finished:
        check_state(state)
        if not state["children"] or (
            len(state["children"]) < len(ACTIONS) and state["ok"]
        ):
            raise ValueError("completion requires exhausted actions or failed child")
        return {
            "result": hub.finish_intent_state(
                state, selected_match(match), checked_registry(registry)
            )
        }
