# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Bind the singleton alias to the hub and the existing live-child transport."""

from typing_extensions import TypedDict
import mathformer as hub
from coherence_suite_tools import (
    Context,
    Admission,
    State,
    Admitted,
    Initialized,
    Advanced,
    Finished,
    Carried,
)
from generative_critic_tools import BoundaryResult

ACTION = "physics-lib:coherence-generative-critic"


class StageResult(TypedDict):
    stage: dict


def stage(state):
    return {"stage": {"active": not bool(state["child"]), "state": state}}


def register_coherence_generative_alias_tools(mcp, leaf):
    @mcp.tool()
    def mathformer_coherence_generative_alias_admit(
        extra_args: list[str], seen: list[str]
    ) -> Admitted:
        return {
            "admission": hub.admit_action(
                ACTION, hub.build_registry(), extra_args, seen
            )
        }

    @mcp.tool()
    def mathformer_coherence_generative_alias_reject(admission: Admission) -> Finished:
        return {"result": hub.reject_action(ACTION, admission)}

    @mcp.tool()
    def mathformer_coherence_generative_alias_initialize(
        admission: Admission,
    ) -> Initialized:
        return {"state": hub.initialize_dependencies(admission)}

    @mcp.tool()
    def mathformer_coherence_generative_alias_prepare_child(
        state: State, context: Context, repository_root: str
    ) -> BoundaryResult:
        item = hub.build_registry()[ACTION]
        if not 0 <= state["index"] < len(item.depends_on):
            raise ValueError("dependency iterator exhausted")
        if (
            item.depends_on[state["index"]]
            != "mathformerphysicslib:generative-coherence-critic"
        ):
            raise ValueError("alias dependency changed; rebind workflow")
        return leaf["prepare"](context, repository_root, [], state["ancestry"])

    @mcp.tool()
    def mathformer_coherence_generative_alias_reports(boundary: dict) -> StageResult:
        return stage(leaf["reports"](boundary)["state"])

    @mcp.tool()
    def mathformer_coherence_generative_alias_plan(stage: dict) -> StageResult:
        state = leaf["plan"](stage["state"])["state"]
        return {"stage": {"active": not bool(state["child"]), "state": state}}

    @mcp.tool()
    def mathformer_coherence_generative_alias_carry_stage(stage: dict) -> StageResult:
        """Carry a terminated child without executing any remaining main stage."""
        if stage["active"]:
            raise ValueError("only a terminated child may bypass planning")
        return {"stage": stage}

    @mcp.tool()
    def mathformer_coherence_generative_alias_complete_child(
        stage: dict, boundary: dict
    ) -> Finished:
        child = leaf["complete"](stage["state"])["child"]
        return leaf["finish"](boundary, child)

    @mcp.tool()
    def mathformer_coherence_generative_alias_skip_child(boundary: dict) -> Finished:
        return leaf["skip"](boundary)

    @mcp.tool()
    def mathformer_coherence_generative_alias_advance(
        state: State, child: dict, context: Context
    ) -> Advanced:
        updated, done = hub.advance_dependencies(
            hub.build_registry()[ACTION], state, child, hub.RunContext(**context)
        )
        return {"state": updated, "done": done}

    @mcp.tool()
    def mathformer_coherence_generative_alias_finish(state: State) -> Finished:
        return {"result": hub.finish_dependencies(hub.build_registry()[ACTION], state)}

    @mcp.tool()
    def mathformer_coherence_generative_alias_carry(
        state: State, result: dict
    ) -> Carried:
        """Transport rejection across Lunar's top-level bounded loop."""
        return {"state": state, "done": True, "result": result}
