# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable ports over the shared native calibration steps."""

from contextlib import redirect_stdout, redirect_stderr
from functools import lru_cache
import importlib.util
import io
from pathlib import Path
import sys
from typing_extensions import TypedDict


class Initialized(TypedDict):
    options: dict
    state: dict


class StateResult(TypedDict):
    state: dict


class DashboardResult(TypedDict):
    dashboard: dict


class Published(TypedDict):
    exit_code: int
    stdout: str


@lru_cache(maxsize=1)
def source():
    path = (
        Path(__file__).resolve().parents[1]
        / "tests/physics_lean/run_critic_calibration_dashboard.py"
    )
    spec = importlib.util.spec_from_file_location("mathformer_calibration_native", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def register_calibration_dashboard_tools(mcp, before_write):
    @mcp.tool()
    def mathformer_calibration_initialize(argv: list[str]) -> Initialized:
        output, errors = io.StringIO(), io.StringIO()
        try:
            with redirect_stdout(output), redirect_stderr(errors):
                return source().initialize(argv)
        except SystemExit as error:
            raise ValueError(
                f"native argparse terminated with exit code {error.code}"
            ) from None
        finally:
            print(output.getvalue(), end="", file=sys.stderr)
            print(errors.getvalue(), end="", file=sys.stderr)

    @mcp.tool()
    def mathformer_calibration_derivation(state: dict) -> StateResult:
        before_write()
        return {"state": source().derivation(state)}

    @mcp.tool()
    def mathformer_calibration_grounding(state: dict) -> StateResult:
        before_write()
        return {"state": source().grounding(state)}

    @mcp.tool()
    def mathformer_calibration_redefinition(state: dict) -> StateResult:
        return {"state": source().redefinition(state)}

    @mcp.tool()
    def mathformer_calibration_units(state: dict) -> StateResult:
        return {"state": source().units(state)}

    @mcp.tool()
    def mathformer_calibration_summarize(state: dict) -> DashboardResult:
        return {"dashboard": source().summarize(state)}

    @mcp.tool()
    def mathformer_calibration_publish(options: dict, dashboard: dict) -> Published:
        before_write()
        output = io.StringIO()
        try:
            with redirect_stdout(output):
                code = source().publish(options, dashboard)
        finally:
            print(output.getvalue(), end="", file=sys.stderr)
        return {"exit_code": code, "stdout": output.getvalue()}
