# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP ports sharing the Lean physics backend suite's native implementations."""

from functools import lru_cache
import importlib.util
from pathlib import Path
from typing_extensions import TypedDict


@lru_cache(maxsize=1)
def source():
    path = (
        Path(__file__).resolve().parents[1]
        / "tests/physics_lean/run_lean_physics_backend_suite.py"
    )
    spec = importlib.util.spec_from_file_location("physics_backend_suite_native", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Prepared(TypedDict):
    evidence: dict
    state: dict


class State(TypedDict):
    state: dict


class Advanced(TypedDict):
    state: dict
    done: bool


class Report(TypedDict):
    report: dict


def register_physics_backend_suite_tools(mcp, write_policy):
    @mcp.tool()
    def mathformer_physics_backend_prepare_controlled() -> Prepared:
        write_policy()
        return source().prepare_controlled()

    @mcp.tool()
    def mathformer_physics_backend_collect_plan(
        evidence: dict, state: dict
    ) -> Advanced:
        write_policy()
        return source().collect_plan(evidence, state)

    @mcp.tool()
    def mathformer_physics_backend_begin_arguments(plans: dict) -> State:
        return source().begin_arguments(plans)

    @mcp.tool()
    def mathformer_physics_backend_append_argument(
        plans: dict, state: dict
    ) -> Advanced:
        return source().append_argument(plans, state)

    @mcp.tool()
    def mathformer_physics_backend_finish_controlled(
        evidence: dict, plans: dict, args: dict
    ) -> Report:
        write_policy()
        return {"report": source().finish_controlled(evidence, plans, args)}

    @mcp.tool()
    def mathformer_physics_backend_begin_adversarial() -> State:
        return source().begin_adversarial()

    @mcp.tool()
    def mathformer_physics_backend_check_fixture(state: dict) -> Advanced:
        write_policy()
        return source().check_fixture(state)

    @mcp.tool()
    def mathformer_physics_backend_derivation_regression() -> Report:
        write_policy()
        return {"report": source().derivation_regression()}

    @mcp.tool()
    def mathformer_physics_backend_thoroughness_regression() -> Report:
        write_policy()
        return {"report": source().thoroughness_regression()}

    @mcp.tool()
    def mathformer_physics_backend_write_suite(
        controlled: dict, adversarial: dict, derivation: dict, thoroughness: dict
    ) -> Report:
        write_policy()
        return {
            "report": source().write_suite(
                controlled,
                {"ok": adversarial["all_ok"], "cases": adversarial["results"]},
                derivation,
                thoroughness,
            )
        }


def create_server(*, readonly=False):
    from mcp.server.fastmcp import FastMCP

    def guard():
        if readonly:
            raise ValueError(
                "Physics backend suite writes disabled by read-only policy"
            )

    mcp = FastMCP("mathformer-physics-backend-suite")
    register_physics_backend_suite_tools(mcp, guard)
    return mcp
