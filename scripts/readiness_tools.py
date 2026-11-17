# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Typed MCP ports for the native reasoning-log consumer readiness dependency controller.

The canonical registry and RunContext are passed to the shared hub helpers.
Leaf preflight, subprocess timeouts, output and filesystem auditing remain
source-owned. Lunar enforces its additional workflow wall and call budgets.
"""

from typing import Literal
from typing_extensions import TypedDict
import mathformer as hub

ACTION = "control:reasoning-log-consumer-readiness"


class Request(TypedDict):
    action_id: Literal["control:reasoning-log-consumer-readiness"]
    extra_args: list[str]
    seen: list[str]


class Context(TypedDict):
    dry_run: bool
    json_output: bool
    keep_going: bool
    allow_mutating: bool
    write_report: bool


class Admission(TypedDict):
    accepted: bool
    status: Literal[
        "accepted", "unknown_action", "dependency_cycle", "extra_args_for_sequence"
    ]
    ancestry: list[str]


class State(TypedDict):
    index: int
    children: list[dict]
    dependencies_ok: bool
    ancestry: list[str]


class Admitted(TypedDict):
    admission: Admission


class Initialized(TypedDict):
    state: State


class Visited(TypedDict):
    child: dict


class Advanced(TypedDict):
    state: State
    done: bool


class Finished(TypedDict):
    result: dict


class Carried(TypedDict):
    state: State
    done: bool
    result: dict


def register_readiness_tools(mcp):
    """Expose source steps without replacing the native execution registry."""

    @mcp.tool()
    def mathformer_readiness_admit(request: Request) -> Admitted:
        return {
            "admission": hub.admit_action(
                request["action_id"],
                hub.build_registry(),
                request["extra_args"],
                request["seen"],
            )
        }

    @mcp.tool()
    def mathformer_readiness_reject(request: Request, admission: Admission) -> Finished:
        return {"result": hub.reject_action(request["action_id"], admission)}

    @mcp.tool()
    def mathformer_readiness_initialize(admission: Admission) -> Initialized:
        return {"state": hub.initialize_dependencies(admission)}

    @mcp.tool()
    def mathformer_readiness_visit(state: State, context: Context) -> Visited:
        registry = hub.build_registry()
        item = registry[ACTION]
        if not 0 <= state["index"] < len(item.depends_on):
            raise ValueError("dependency cursor is out of bounds")
        return {
            "child": hub.visit_dependency(
                item, registry, hub.RunContext(**context), state
            )
        }

    @mcp.tool()
    def mathformer_readiness_advance(
        state: State, child: dict, context: Context
    ) -> Advanced:
        updated, done = hub.advance_dependencies(
            hub.build_registry()[ACTION], state, child, hub.RunContext(**context)
        )
        return {"state": updated, "done": done}

    @mcp.tool()
    def mathformer_readiness_finish(state: State) -> Finished:
        return {"result": hub.finish_dependencies(hub.build_registry()[ACTION], state)}

    @mcp.tool()
    def mathformer_readiness_carry(state: State, result: dict) -> Carried:
        """Carry a rejected admission through Lunar's top-level loop exit.

        This transport adapter performs no native workflow operations.
        """
        return {"state": state, "done": True, "result": result}
