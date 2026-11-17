# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Typed MCP bindings for the native paper functionality update suite controller.

Registry identity, argv, ancestry and leaf preflight/auditing remain hub-owned.
These are the same functions used by run_action, with no alternate executor.
"""

from typing_extensions import TypedDict
import mathformer as hub

ACTION = "paper:functionality-update-suite"


class Context(TypedDict):
    dry_run: bool
    json_output: bool
    keep_going: bool
    allow_mutating: bool
    write_report: bool


class AdmissionOutput(TypedDict):
    admission: dict


class StateOutput(TypedDict):
    state: dict


class ChildOutput(TypedDict):
    child: dict


class AdvanceOutput(TypedDict):
    state: dict
    done: bool


class ResultOutput(TypedDict):
    result: dict


class GuardOutput(TypedDict):
    launch: bool


class LeafOutput(TypedDict):
    leaf: dict


def register_paper_functionality_suite_tools(mcp, guard=lambda context: None):
    """Register the fixed action with native (uncapped) leaf timeouts.

    The service guard applies deployment restrictions before visiting a leaf;
    it cannot replace or relax the native preflight and filesystem audit.
    """

    def registry():
        return hub.build_registry()

    @mcp.tool()
    def mathformer_paper_functionality_suite_admit(
        extra_args: list[str], seen: list[str]
    ) -> AdmissionOutput:
        return {
            "admission": hub.admit_action(ACTION, registry(), extra_args, set(seen))
        }

    @mcp.tool()
    def mathformer_paper_functionality_suite_reject(admission: dict) -> ResultOutput:
        return {"result": hub.reject_action(ACTION, admission)}

    @mcp.tool()
    def mathformer_paper_functionality_suite_initialize(admission: dict) -> StateOutput:
        return {"state": hub.initialize_dependencies(admission)}

    @mcp.tool()
    def mathformer_paper_functionality_suite_visit(
        state: dict, context: Context
    ) -> ChildOutput:
        actions = registry()
        item = actions[ACTION]
        if not 0 <= state["index"] < len(item.depends_on):
            raise ValueError("dependency iterator exhausted")
        guard(context)
        return {
            "child": hub.visit_dependency(
                item, actions, hub.RunContext(**context), state
            )
        }

    @mcp.tool()
    def mathformer_paper_functionality_suite_advance(
        state: dict, child: dict, context: Context
    ) -> AdvanceOutput:
        updated, done = hub.advance_dependencies(
            registry()[ACTION], state, child, hub.RunContext(**context)
        )
        return {"state": updated, "done": done}

    @mcp.tool()
    def mathformer_paper_functionality_suite_finish(state: dict) -> ResultOutput:
        return {"result": hub.finish_dependencies(registry()[ACTION], state)}
