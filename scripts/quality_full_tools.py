# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Typed MCP ports for the native quality:full dependency controller.

The canonical registry and RunContext are passed to the shared hub helpers.
Leaf preflight, subprocess timeouts, output and filesystem auditing remain
source-owned. Lunar enforces its additional workflow wall and call budgets.
"""

from typing import Literal
from typing_extensions import TypedDict
from pathlib import Path
import mathformer as hub

ACTION = "quality:full"


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


def register_quality_full_tools(mcp, guard):
    """Expose source steps without replacing the native execution registry."""

    @mcp.tool()
    def mathformer_quality_full_admit(
        extra_args: list[str], seen: list[str]
    ) -> Admitted:
        return {
            "admission": hub.admit_action(
                ACTION, hub.build_registry(), extra_args, seen
            )
        }

    @mcp.tool()
    def mathformer_quality_full_reject(admission: Admission) -> Finished:
        return {"result": hub.reject_action(ACTION, admission)}

    @mcp.tool()
    def mathformer_quality_full_initialize(admission: Admission) -> Initialized:
        return {"state": hub.initialize_dependencies(admission)}

    @mcp.tool()
    def mathformer_quality_full_visit(
        state: State, context: Context, repository_root: str
    ) -> Visited:
        registry = hub.build_registry()
        item = registry[ACTION]
        if not 0 <= state["index"] < len(item.depends_on):
            raise ValueError("dependency cursor is out of bounds")
        root = Path(repository_root).resolve()
        guard(context, root, registry)
        return {
            "child": hub.visit_dependency(
                item, registry, hub.RunContext(**context), state, repository_root=root
            )
        }

    @mcp.tool()
    def mathformer_quality_full_advance(
        state: State, child: dict, context: Context
    ) -> Advanced:
        updated, done = hub.advance_dependencies(
            hub.build_registry()[ACTION], state, child, hub.RunContext(**context)
        )
        return {"state": updated, "done": done}

    @mcp.tool()
    def mathformer_quality_full_finish(state: State) -> Finished:
        return {"result": hub.finish_dependencies(hub.build_registry()[ACTION], state)}

    @mcp.tool()
    def mathformer_quality_full_carry(state: State, result: dict) -> Carried:
        """Carry a rejected admission through Lunar's top-level loop exit.

        This transport adapter performs no native workflow operations.
        """
        return {"state": state, "done": True, "result": result}
