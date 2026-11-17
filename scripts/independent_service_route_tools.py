# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""JSON ports for the selected independent-service route's native controller.

Registry records are transported explicitly, but must match the server-owned
execution registry. A client cannot use this interface to register commands.
The MCP timeout cap and service write-root admission remain server-owned.
"""

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any, Literal
from typing_extensions import TypedDict

import mathformer as hub

ROUTE = "mcp.independent.service"
ACTION_IDS = (
    "mcp:service-config",
    "mcp:service-dependencies",
    "mcp:service-self-check",
)


class StateOutput(TypedDict):
    state: dict[str, Any]


class SelectOutput(TypedDict):
    action_id: str


class ChildOutput(TypedDict):
    child: dict[str, Any]


class AdvanceOutput(StateOutput):
    done: bool


class ResultOutput(TypedDict):
    result: dict[str, Any]


def unpack_match(match):
    route = dict(match["route"])
    if route["route_id"] != ROUTE or tuple(route["action_ids"]) != ACTION_IDS:
        raise ValueError("expected the fixed independent service route")
    # Positive terms belong to NL selection; this boundary is already selected.
    route.setdefault("positive_terms", ())
    for name in ("action_ids", "positive_terms", "skill_routes", "examples"):
        route[name] = tuple(route.get(name, ()))
    return hub.IntentMatch(
        hub.IntentRoute(**route), match["score"], tuple(match["matched_terms"])
    )


def register_independent_service_route_tools(mcp, execution_registry, guard):
    def unpack_registry(registry):
        registered = execution_registry()
        for key in ACTION_IDS:
            expected = json.loads(json.dumps(asdict(registered[key])))
            if registry.get(key) != expected:
                raise ValueError(
                    f"{key} must match the advertised service execution registry"
                )
        if set(registry) != set(ACTION_IDS):
            raise ValueError(
                "only the three selected registered actions may be transported"
            )
        return {key: registered[key] for key in ACTION_IDS}

    @mcp.tool()
    def mathformer_independent_service_inputs(
        dry_run: bool = False, keep_going: bool = False
    ) -> dict[str, Any]:
        """Discover JSON inputs including the service's configured timeout caps."""
        route = next(
            route for route in hub.build_intent_routes() if route.route_id == ROUTE
        )
        return json.loads(
            json.dumps(
                {
                    "match": asdict(hub.IntentMatch(route, 0, ())),
                    "registry": {
                        key: asdict(execution_registry()[key]) for key in ACTION_IDS
                    },
                    "context": asdict(
                        hub.RunContext(
                            dry_run=dry_run, keep_going=keep_going, json_output=True
                        )
                    ),
                    "repository_root": None,
                }
            )
        )

    @mcp.tool()
    def mathformer_independent_service_initialize() -> StateOutput:
        """Initialize the native selected-route accumulator."""
        return {"state": hub.initialize_intent_state()}

    @mcp.tool()
    def mathformer_independent_service_select_action(
        state: dict[str, Any], match: dict[str, Any]
    ) -> SelectOutput:
        """Select by the length of native ordered child history."""
        return {"action_id": hub.select_intent_action(state, unpack_match(match))}

    @mcp.tool()
    def mathformer_independent_service_run_child(
        action_id: Literal[
            "mcp:service-config", "mcp:service-dependencies", "mcp:service-self-check"
        ],
        registry: dict[str, Any],
        context: dict[str, Any],
        repository_root: str | None,
    ) -> ChildOutput:
        """Run a registered child with native preflight, launch, and write audit."""
        records = unpack_registry(registry)
        native_context = hub.RunContext(**context)
        root = None if repository_root is None else Path(repository_root)
        guard(action_id, native_context, root)
        mount = {} if root is None else {"repository_root": root}
        return {"child": hub.run_action(action_id, records, native_context, **mount)}

    @mcp.tool()
    def mathformer_independent_service_advance(
        state: dict[str, Any],
        child: dict[str, Any],
        context: dict[str, Any],
        action_count: Literal[3],
    ) -> AdvanceOutput:
        """Append the child and apply native sticky failure and stop semantics."""
        state, done = hub.advance_intent_state(
            state, child, hub.RunContext(**context), action_count
        )
        return {"state": state, "done": done}

    @mcp.tool()
    def mathformer_independent_service_finish(
        state: dict[str, Any],
        match: dict[str, Any],
        registry: dict[str, Any],
    ) -> ResultOutput:
        """Return source-owned route metadata and ordered observations."""
        return {
            "result": hub.finish_intent_state(
                state, unpack_match(match), unpack_registry(registry)
            )
        }
