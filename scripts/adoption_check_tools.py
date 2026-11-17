# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP ports for the shared native adoption:check dependency controller.

No server timeout cap is applied: this interface retains the hub's native
unbounded child subprocess behavior. Lunar owns the contract's wall time budget.
"""

from typing import Literal
from typing_extensions import TypedDict
import mathformer as hub

ACTION = "adoption:check"


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


class Advanced(TypedDict):
    state: State
    done: bool


class Finished(TypedDict):
    result: dict


def register_adoption_check_tools(mcp):
    """Register every advertised operation against the same hub implementation."""

    @mcp.tool()
    def mathformer_adoption_admit(extra_args: list[str], seen: list[str]) -> Admitted:
        return {
            "admission": hub.admit_action(
                ACTION, hub.build_registry(), extra_args, seen
            )
        }

    @mcp.tool()
    def mathformer_adoption_reject(admission: Admission) -> Finished:
        return {"result": hub.reject_action(ACTION, admission)}

    @mcp.tool()
    def mathformer_adoption_initialize(admission: Admission) -> Initialized:
        return {"state": hub.initialize_dependencies(admission)}

    @mcp.tool()
    def mathformer_adoption_visit_child(state: State, context: Context) -> Finished:
        registry = hub.build_registry()
        item = registry[ACTION]
        if not 0 <= state["index"] < len(item.depends_on):
            raise ValueError("dependency cursor is out of bounds")
        return {
            "result": hub.visit_dependency(
                item, registry, hub.RunContext(**context), state
            )
        }

    @mcp.tool()
    def mathformer_adoption_advance(
        state: State, child: dict, context: Context
    ) -> Advanced:
        updated, done = hub.advance_dependencies(
            hub.build_registry()[ACTION], state, child, hub.RunContext(**context)
        )
        return {"state": updated, "done": done}

    @mcp.tool()
    def mathformer_adoption_finish(state: State) -> Finished:
        return {"result": hub.finish_dependencies(hub.build_registry()[ACTION], state)}
