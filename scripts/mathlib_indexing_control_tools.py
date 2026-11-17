# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP interfaces for the shared native indexing control suite stages."""

from functools import lru_cache
import importlib.util
from pathlib import Path
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "mathlib_indexing_control_native",
        ROOT / "tests/mathlib/run_indexing_control_suite.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Executed(TypedDict):
    result: dict


class Advanced(TypedDict):
    state: dict
    done: bool


class Passed(TypedDict):
    passed: bool


class Checked(TypedDict):
    checks: list[dict]


class Finished(TypedDict):
    report: dict


def register_mathlib_indexing_control_tools(mcp, write_policy):
    @mcp.tool()
    def mathformer_indexing_control_execute_command(
        state: dict, repo_root: str
    ) -> Executed:
        write_policy()
        return {
            "result": source().execute_command(
                state, Path(repo_root) if repo_root else None
            )
        }

    @mcp.tool()
    def mathformer_indexing_control_advance_state(
        state: dict, result: dict
    ) -> Advanced:
        return source().advance_state(state, result)

    @mcp.tool()
    def mathformer_indexing_control_commands_passed(state: dict) -> Passed:
        return {"passed": source().commands_passed(state)}

    @mcp.tool()
    def mathformer_indexing_control_artifact_oracles(repo_root: str) -> Checked:
        return {
            "checks": source().additional_oracles(
                Path(repo_root) if repo_root else None
            )
        }

    @mcp.tool()
    def mathformer_indexing_control_finish_report(
        state: dict, checks: list[dict], output: str
    ) -> Finished:
        write_policy()
        return {
            "report": source().finish_report(
                state, checks, Path(output) if output else None
            )
        }
