# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Read-only MCP ports for the native foundation API critic traversal."""

from functools import lru_cache
import importlib.util
from pathlib import Path
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "skills/mathformerphysicslib/mathformerphysicslib-coherence-inventory-builder/scripts/coherence_common.py"


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location("api_critic_native", ROOT / SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Initialized(TypedDict):
    state: dict
    empty: bool


class Visited(TypedDict):
    state: dict
    done: bool


class Finished(TypedDict):
    report: dict


def register_api_critic_tools(mcp):
    @mcp.tool()
    def mathformer_api_critic_initialize(graph: dict) -> Initialized:
        result = source().initialize_api_traversal(graph)
        if len(result["state"]["concepts"]) > 1024:
            raise ValueError("API critic workflow admits at most 1024 concepts")
        return result

    @mcp.tool()
    def mathformer_api_critic_visit(state: dict, repository_root: str) -> Visited:
        # Lunar loops execute at least once; empty traversal performs no inspection.
        if not state["concepts"] and state["index"] == 0:
            return {"state": state, "done": True}
        return source().visit_api_concept(state, Path(repository_root))

    @mcp.tool()
    def mathformer_api_critic_finish(state: dict) -> Finished:
        return {"report": source().finish_api_report(state)}
