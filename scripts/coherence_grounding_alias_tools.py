# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Transport bindings for the native one-child Mathlib grounding alias.

Admission, iteration, recursive dispatch, preflight, subprocess execution and
write auditing belong to mathformer. The invocation carries the caller's
repository mount and leaf timeout (None preserves CLI behavior).
"""

from dataclasses import replace
from pathlib import Path
from typing_extensions import TypedDict

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

ACTION = "physics-lib:coherence-mathlib-grounding"
CHILD = "mathformerphysicslib:mathlib-grounding-audit"


class Invocation(TypedDict):
    extra_args: list[str]
    seen: list[str]
    repository_root: str | None
    leaf_timeout_seconds: int | None


def register_coherence_grounding_alias_tools(mcp):
    """Register real callable operations without executing the audit at import."""

    @mcp.tool()
    def mathformer_coherence_grounding_alias_admit(invocation: Invocation) -> Admitted:
        return {
            "admission": hub.admit_action(
                ACTION,
                hub.build_registry(),
                invocation["extra_args"],
                invocation["seen"],
            )
        }

    @mcp.tool()
    def mathformer_coherence_grounding_alias_reject(admission: Admission) -> Finished:
        return {"result": hub.reject_action(ACTION, admission)}

    @mcp.tool()
    def mathformer_coherence_grounding_alias_initialize(
        admission: Admission,
    ) -> Initialized:
        return {"state": hub.initialize_dependencies(admission)}

    @mcp.tool()
    def mathformer_coherence_grounding_alias_visit(
        state: State, context: Context, invocation: Invocation
    ) -> Visited:
        registry = hub.build_registry()
        item = registry[ACTION]
        if item.depends_on != (CHILD,) or item.command:
            raise ValueError("alias registry changed; rebind workflow")
        if not 0 <= state["index"] < len(item.depends_on):
            raise ValueError("dependency iterator exhausted")
        timeout = invocation["leaf_timeout_seconds"]
        if timeout is not None:
            if timeout < 1:
                raise ValueError("leaf timeout must be positive")
            registry[CHILD] = replace(registry[CHILD], timeout_seconds=timeout)
        mount = invocation["repository_root"]
        return {
            "child": hub.visit_dependency(
                item,
                registry,
                hub.RunContext(**context),
                state,
                repository_root=Path(mount) if mount is not None else None,
            )
        }

    @mcp.tool()
    def mathformer_coherence_grounding_alias_advance(
        state: State, child: dict, context: Context
    ) -> Advanced:
        updated, done = hub.advance_dependencies(
            hub.build_registry()[ACTION], state, child, hub.RunContext(**context)
        )
        return {"state": updated, "done": done}

    @mcp.tool()
    def mathformer_coherence_grounding_alias_finish(state: State) -> Finished:
        return {"result": hub.finish_dependencies(hub.build_registry()[ACTION], state)}

    @mcp.tool()
    def mathformer_coherence_grounding_alias_carry(
        state: State, result: dict
    ) -> Carried:
        """Preserve rejection through Lunar's required top-level loop scope."""
        return {"state": state, "done": True, "result": result}
