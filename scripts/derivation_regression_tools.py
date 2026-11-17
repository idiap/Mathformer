# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable MCP ports for the native derivation completeness regression."""

from contextlib import redirect_stdout
from functools import lru_cache
import importlib.util
import io
from pathlib import Path
import sys
from typing import Literal
from typing_extensions import TypedDict


@lru_cache(maxsize=1)
def source():
    path = (
        Path(__file__).resolve().parents[1]
        / "tests/physics_lean/run_derivation_completeness_regression.py"
    )
    spec = importlib.util.spec_from_file_location("derivation_regression_native", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Report(TypedDict):
    report: dict


class ReportPath(TypedDict):
    path: str


class Finished(TypedDict):
    exit_code: int
    stdout: str


def register_derivation_regression_tools(mcp, write_policy):
    @mcp.tool()
    def mathformer_derivation_self_test() -> Report:
        write_policy()
        return {"report": source().run_self_test()}

    @mcp.tool()
    def mathformer_derivation_fixture(
        name: Literal[
            "direct_target_hypothesis",
            "witness_target_restatement",
            "source_law_witness_not_target",
        ],
        frontier: Literal[1] | None,
    ) -> Report:
        return {"report": source().run_fixture(name, frontier)}

    @mcp.tool()
    def mathformer_derivation_formal_case(
        case_id: Literal[
            "formalphysics_0014",
            "formalphysics_0015",
            "formalphysics_0021",
            "formalphysics_0052",
            "formalphysics_0074",
        ],
    ) -> Report:
        return {
            "report": source().run_formalphysics_case(
                case_id, recursive_frontier_count=0
            )
        }

    @mcp.tool()
    def mathformer_derivation_assertions(
        self_test: dict,
        direct: dict,
        wrapped: dict,
        legitimate: dict,
        frontier_blocked: dict,
        case0014: dict,
        case0015: dict,
        case0021: dict,
        case0052: dict,
        case0074: dict,
    ) -> Report:
        return {
            "report": source().build_regression_report(
                self_test,
                direct,
                wrapped,
                legitimate,
                frontier_blocked,
                case0014,
                case0015,
                case0021,
                case0052,
                case0074,
            )
        }

    @mcp.tool()
    def mathformer_derivation_persist(report: dict) -> ReportPath:
        write_policy()
        return {"path": source().persist_report(report)}

    @mcp.tool()
    def mathformer_derivation_emit_return(
        report: dict,
        json_output: bool,
        code: Literal[0, 1],
    ) -> Finished:
        # Keep source printing observable without corrupting the stdio transport.
        with redirect_stdout(io.StringIO()) as output:
            exit_code = source().emit_return(report, json_output, code)
        text = output.getvalue()
        sys.stderr.write(text)
        return {"exit_code": exit_code, "stdout": text}


def create_server(*, readonly=False):
    from mcp.server.fastmcp import FastMCP

    def guard():
        if readonly:
            raise ValueError(
                "Derivation regression writes disabled by read-only policy"
            )

    mcp = FastMCP("mathformer-derivation-regression")
    register_derivation_regression_tools(mcp, guard)
    return mcp
