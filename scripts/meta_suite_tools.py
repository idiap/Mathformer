# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Typed transport for the native suite; no duplicated check implementation."""

from functools import lru_cache
import importlib.util
from pathlib import Path
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "meta_suite_native", ROOT / "tests/meta_skills/run_meta_skill_suite.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Results(TypedDict):
    results: list[dict]


class Command(TypedDict):
    command: list[str]


class Check(TypedDict):
    check: dict


class Appended(TypedDict):
    results: list[dict]
    done: bool


class Report(TypedDict):
    report: dict


def register_meta_suite_tools(mcp, write_policy=lambda: None):
    @mcp.tool()
    def mathformer_meta_suite_initialize() -> Results:
        return {"results": source().initialize_results()}

    @mcp.tool()
    def mathformer_meta_suite_select(results: list[dict]) -> Command:
        return {"command": source().select_command(results)}

    @mcp.tool()
    def mathformer_meta_suite_run(command: list[str], repo_root: str) -> Check:
        write_policy()
        if command not in source().COMMANDS:
            raise ValueError("not a registered suite command")
        return {"check": source().run_command(command, Path(repo_root).resolve())}

    @mcp.tool()
    def mathformer_meta_suite_append(results: list[dict], check: dict) -> Appended:
        return source().append_and_test(results, check)

    @mcp.tool()
    def mathformer_meta_suite_finalize(results: list[dict], output_path: str) -> Report:
        write_policy()
        return {
            "report": source().aggregate_write_return(
                results, Path(output_path).resolve()
            )
        }
