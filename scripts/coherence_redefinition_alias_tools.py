# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable stages of the fixed physics-lib redefinition critic alias.

The hub owns registry admission, recursion, preflight, the single subprocess,
and its write audit. The specialization adds no concept bound or timeout.
"""

from pathlib import Path
import mathformer as hub
from coherence_suite_tools import (
    Context,
    Admission,
    State,
    Admitted,
    Initialized,
    Visited,
    Advanced,
    Finished,
    Carried,
)

ACTION = "physics-lib:coherence-redefinition-critic"


def register_coherence_redefinition_alias_tools(mcp):
    @mcp.tool()
    def mathformer_coherence_redefinition_alias_admit(
        extra_args: list[str] = [], seen: list[str] = []
    ) -> Admitted:
        return {
            "admission": hub.admit_action(
                ACTION, hub.build_registry(), extra_args, seen
            )
        }

    @mcp.tool()
    def mathformer_coherence_redefinition_alias_reject(
        admission: Admission,
    ) -> Finished:
        return {"result": hub.reject_action(ACTION, admission)}

    @mcp.tool()
    def mathformer_coherence_redefinition_alias_initialize(
        admission: Admission,
    ) -> Initialized:
        return {"state": hub.initialize_dependencies(admission)}

    @mcp.tool()
    def mathformer_coherence_redefinition_alias_visit(
        state: State, context: Context, repository_root: str
    ) -> Visited:
        registry = hub.build_registry()
        item = registry[ACTION]
        if not 0 <= state["index"] < len(item.depends_on):
            raise ValueError("dependency iterator exhausted")
        if (
            item.depends_on != ("mathformerphysicslib:redefinition-critic",)
            or item.command
        ):
            raise ValueError("alias registry changed; rebind workflow")
        return {
            "child": hub.visit_dependency(
                item,
                registry,
                hub.RunContext(**context),
                state,
                repository_root=Path(repository_root),
            )
        }

    @mcp.tool()
    def mathformer_coherence_redefinition_alias_advance(
        state: State, child: dict, context: Context
    ) -> Advanced:
        updated, done = hub.advance_dependencies(
            hub.build_registry()[ACTION], state, child, hub.RunContext(**context)
        )
        return {"state": updated, "done": done}

    @mcp.tool()
    def mathformer_coherence_redefinition_alias_finish(state: State) -> Finished:
        return {"result": hub.finish_dependencies(hub.build_registry()[ACTION], state)}

    @mcp.tool()
    def mathformer_coherence_redefinition_alias_carry(
        state: State, result: dict
    ) -> Carried:
        """Transport rejected admission across Lunar's top-level loop exit."""
        return {"state": state, "done": True, "result": result}
