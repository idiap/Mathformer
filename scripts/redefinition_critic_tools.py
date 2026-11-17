# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Read-only MCP ports for the shared native redefinition critic traversal."""

from typing_extensions import TypedDict
from api_critic_tools import source


class Initialized(TypedDict):
    state: dict
    has_concepts: bool


class Visited(TypedDict):
    state: dict
    done: bool


class Finished(TypedDict):
    report: dict


def register_redefinition_critic_tools(mcp):
    @mcp.tool()
    def mathformer_redefinition_critic_initialize(
        concept_graph: dict, grounding: dict
    ) -> Initialized:
        """Index grounding and admit the contract's bounded concept sequence."""
        result = source().initialize_redefinition_traversal(concept_graph, grounding)
        if len(result["state"]["concepts"]) > 1024:
            raise ValueError(
                "Redefinition critic workflow admits at most 1024 concepts"
            )
        return result

    @mcp.tool()
    def mathformer_redefinition_critic_visit_concept(state: dict) -> Visited:
        """Inspect exactly the next concept; native exceptions propagate."""
        # Lunar loops are at least once; an empty scan inspects no concept.
        if not state["concepts"] and state["cursor"] == 0:
            return {"state": state, "done": True}
        return source().visit_redefinition_concept(state)

    @mcp.tool()
    def mathformer_redefinition_critic_finish_report(state: dict) -> Finished:
        """Return the native report, including ok=false as ordinary data."""
        return {"report": source().finish_redefinition_report(state)}
