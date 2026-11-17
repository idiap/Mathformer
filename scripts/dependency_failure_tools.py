# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Real MCP interfaces for the native missing-SymPy policy blocks."""

from functools import lru_cache
import importlib.util
from pathlib import Path
from typing import Any
from typing_extensions import TypedDict


@lru_cache(maxsize=1)
def source():
    path = (
        Path(__file__).resolve().parents[1]
        / "tests/physics_sympy/run_dependency_failure_policy.py"
    )
    spec = importlib.util.spec_from_file_location("dependency_failure_native", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Context(TypedDict):
    repository_root: str


class Result(TypedDict):
    script: str
    returncode: int
    stdout_json: Any
    stderr: str
    raw_stdout: str


class State(TypedDict):
    index: int
    results: list[Result]
    findings: list[dict]


class ResultsOutput(TypedDict):
    results: list[Result]


class Collected(ResultsOutput):
    done: bool


class StateOutput(TypedDict):
    state: State


class Advanced(StateOutput):
    done: bool


class Inspected(TypedDict):
    result: Result
    missing: bool


class FindingsOutput(TypedDict):
    findings: list[dict]


class ReportOutput(TypedDict):
    report: dict


def register_dependency_failure_tools(mcp):
    @mcp.tool()
    def mathformer_dependency_failure_initialize_results() -> ResultsOutput:
        return {"results": source().initialize_results()}

    @mcp.tool()
    def mathformer_dependency_failure_collect_next(
        results: list[Result], context: Context
    ) -> Collected:
        return source().collect_next(results, Path(context["repository_root"]))

    @mcp.tool()
    def mathformer_dependency_failure_begin_validation(
        results: list[Result],
    ) -> StateOutput:
        return {"state": source().begin_validation(results)}

    @mcp.tool()
    def mathformer_dependency_failure_inspect_current(state: State) -> Inspected:
        return source().inspect_current(state)

    @mcp.tool()
    def mathformer_dependency_failure_record_missing(
        state: State, result: Result
    ) -> FindingsOutput:
        return {"findings": source().record_missing(state, result)}

    @mcp.tool()
    def mathformer_dependency_failure_check_nonempty(
        state: State, result: Result
    ) -> FindingsOutput:
        return {"findings": source().check_nonempty(state, result)}

    @mcp.tool()
    def mathformer_dependency_failure_advance_validation(
        state: State, findings: list[dict]
    ) -> Advanced:
        return source().advance_validation(state, findings)

    @mcp.tool()
    def mathformer_dependency_failure_build_report(state: State) -> ReportOutput:
        return {"report": source().build_report(state)}
