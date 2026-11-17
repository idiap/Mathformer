# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Read-only MCP bindings for the shared integration critic steps."""

from pathlib import Path
from typing_extensions import TypedDict

from api_critic_tools import source


class Initialized(TypedDict):
    state: dict
    empty: bool


class Advanced(TypedDict):
    state: dict
    done: bool


class Report(TypedDict):
    report: dict


def register_integration_critic_tools(mcp):
    @mcp.tool()
    def mathformer_integration_critic_initialize(
        inventory: dict, concept_graph: dict, repository_root: str | None
    ) -> Initialized:
        """Initialize native findings; admit up to 1000 concepts in this workflow."""
        result = source().initialize_integration_traversal(
            inventory,
            concept_graph,
            None if repository_root is None else Path(repository_root),
        )
        if len(result["state"]["concepts"]) > 1000:
            raise ValueError("Integration critic workflow admits at most 1000 concepts")
        return result

    @mcp.tool()
    def mathformer_integration_critic_visit(state: dict) -> Advanced:
        """Inspect one concept and advance; native exceptions propagate."""
        return source().visit_integration_concept(state)

    @mcp.tool()
    def mathformer_integration_critic_finish(state: dict) -> Report:
        """Return the native report, including ok=false as ordinary report data."""
        return {"report": source().finish_integration_report(state)}
