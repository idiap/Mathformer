# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Pure MCP bindings for the native one-invocation recursion controller."""

import importlib.util
from functools import lru_cache
from pathlib import Path
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "skills/physics-lean/physics-lean-recursive-repair-loop-controller/scripts/control_recursive_repair_loop.py"


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "recursive_repair_control_native", ROOT / SOURCE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Prepared(TypedDict):
    state: dict


class Selected(TypedDict):
    selection: dict


class Finished(TypedDict):
    plan: dict


def register_recursive_repair_control_tools(mcp):
    @mcp.tool()
    def mathformer_recursive_repair_control_prepare_state(
        expansion_map: dict,
        previous_expansion_maps: list[dict],
        iteration: int,
        max_iterations: int,
    ) -> Prepared:
        """Prepare caller-owned expansion/history state without changing it."""
        return {
            "state": source().prepare_state(
                expansion_map=expansion_map,
                previous_expansion_maps=previous_expansion_maps,
                iteration=iteration,
                max_iterations=max_iterations,
            )
        }

    @mcp.tool()
    def mathformer_recursive_repair_control_select_branch(
        state: dict, branch: str
    ) -> Selected:
        """Apply the assignment chosen by the ordered workflow switch."""
        return {"selection": source().select_branch(state=state, branch=branch)}

    @mcp.tool()
    def mathformer_recursive_repair_control_finish_plan(
        state: dict, selection: dict
    ) -> Finished:
        """Apply the native blocked override and return ordered actions and gates."""
        return {"plan": source().finish_plan(state=state, selection=selection)}
