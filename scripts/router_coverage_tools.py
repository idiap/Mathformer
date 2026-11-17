# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP interfaces for the shared native router coverage audit steps."""

from functools import lru_cache
import importlib.util
from pathlib import Path
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    "skills/control/mathformer-workflow-router/scripts/route_mathformer_workflow.py"
)


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "router_coverage_native", ROOT / SOURCE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Initialized(TypedDict):
    state: dict
    has_routes: bool


class Begun(TypedDict):
    state: dict
    has_actions: bool


class Visited(TypedDict):
    state: dict
    actions_done: bool


class Finished(TypedDict):
    state: dict
    routes_done: bool


class Packed(TypedDict):
    state: dict


class Reported(TypedDict):
    report: dict


def register_router_coverage_tools(mcp):
    @mcp.tool()
    def mathformer_router_coverage_initialize(
        domain: dict, context: dict | None = None
    ) -> Initialized:
        return source().initialize_coverage(domain, context)

    @mcp.tool()
    def mathformer_router_coverage_begin_route(state: dict) -> Begun:
        return source().begin_coverage_route(state)

    @mcp.tool()
    def mathformer_router_coverage_visit_action(state: dict) -> Visited:
        return source().visit_coverage_action(state)

    @mcp.tool()
    def mathformer_router_coverage_finish_route(state: dict) -> Finished:
        return source().finish_coverage_route(state)

    @mcp.tool()
    def mathformer_router_coverage_finalize(state: dict) -> Reported:
        return {"report": source().finalize_coverage(state)}

    @mcp.tool()
    def mathformer_router_coverage_empty_state(state: dict) -> Packed:
        if state["phase"] != "done" or state["routes"]:
            raise ValueError("Empty-state adapter requires zero routes")
        return {"state": state}
