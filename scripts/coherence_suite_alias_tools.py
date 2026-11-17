# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native ports for the physics-lib coherence alias and its expanded suite.

The registry owns commands, arguments and dependency ordering. The explicit
repository mount is used by native preflight, launch and both audit snapshots.
These ports retain CLI timeout semantics; Lunar owns its workflow budgets.
"""

from pathlib import Path
import mathformer as hub
from coherence_suite_tools import (
    Context,
    Admission,
    State,
    Admitted,
    Initialized,
    Advanced,
    Finished,
)

ALIAS = "physics-lib:coherence-suite"
SUITE = "mathformerphysicslib:coherence-suite"


def sequence(action):
    if action not in (ALIAS, SUITE):
        raise ValueError("only the coherence alias and suite are supported")
    return hub.build_registry()[action]


def register_coherence_suite_alias_tools(mcp, path_allowed):
    @mcp.tool()
    def mathformer_coherence_alias_admit(
        action: str, extra_args: list[str], seen: list[str]
    ) -> Admitted:
        return {
            "admission": hub.admit_action(
                action, hub.build_registry(), extra_args, seen
            )
        }

    @mcp.tool()
    def mathformer_coherence_alias_reject(
        action: str, admission: Admission
    ) -> Finished:
        return {"result": hub.reject_action(action, admission)}

    @mcp.tool()
    def mathformer_coherence_alias_initialize(admission: Admission) -> Initialized:
        return {"state": hub.initialize_dependencies(admission)}

    @mcp.tool()
    def mathformer_coherence_alias_visit(
        state: State, context: Context, repository_root: str
    ) -> Finished:
        root = Path(repository_root).resolve()
        if not root.is_dir() or not path_allowed(root):
            raise ValueError("repository mount is unavailable or outside service roots")
        registry = hub.build_registry()
        item = registry[SUITE]
        if not 0 <= state["index"] < len(item.depends_on):
            raise ValueError("dependency cursor is out of bounds")
        return {
            "result": hub.visit_dependency(
                item, registry, hub.RunContext(**context), state, repository_root=root
            )
        }

    @mcp.tool()
    def mathformer_coherence_alias_advance(
        action: str, state: State, child: dict, context: Context
    ) -> Advanced:
        updated, done = hub.advance_dependencies(
            sequence(action), state, child, hub.RunContext(**context)
        )
        return {"state": updated, "done": done}

    @mcp.tool()
    def mathformer_coherence_alias_finish(action: str, state: State) -> Finished:
        return {"result": hub.finish_dependencies(sequence(action), state)}

    @mcp.tool()
    def mathformer_coherence_alias_carry(state: State) -> Advanced:
        """Transport an inactive loop frame unchanged after admission rejection."""
        return {"state": state, "done": True}

    @mcp.tool()
    def mathformer_coherence_alias_return_result(result: dict) -> Finished:
        """Transport a previously rejected native result without finalization."""
        return {"result": result}
