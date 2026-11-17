# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable taxonomy self-test steps, sharing the CLI's implementation."""

from contextlib import redirect_stdout
from functools import lru_cache
import importlib.util
import io
from pathlib import Path
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "taxonomic_native", ROOT / "meta_skills/scripts/navigate_workflow_taxonomy.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def path_for(value, default):
    path = (ROOT / value).resolve()
    if path != default.resolve() and not path.is_relative_to(
        (ROOT / "artifacts/workflow_hub").resolve()
    ):
        raise ValueError("path outside taxonomy workflow resources")
    return path


class StateResult(TypedDict):
    state: dict
    has_cases: bool


class Evaluated(TypedDict):
    result: dict


class Advanced(TypedDict):
    state: dict
    done: bool


class Report(TypedDict):
    report: dict


class Finished(TypedDict):
    report: dict
    exit_code: int
    stdout: str


def register_taxonomic_navigation_tools(mcp, write_guard):
    @mcp.tool()
    def mathformer_taxonomic_initialize(taxonomy: str) -> StateResult:
        state = source().initialize(path_for(taxonomy, source().TAXONOMY_PATH))
        if len(state["cases"]) > 10000:
            raise ValueError("contract supports at most 10000 examples; no truncation")
        return {"state": state, "has_cases": bool(state["cases"])}

    @mcp.tool()
    def mathformer_taxonomic_evaluate_case(state: dict) -> Evaluated:
        path_for(state["taxonomy_path"], source().TAXONOMY_PATH)
        return {"result": source().evaluate_case(state)}

    @mcp.tool()
    def mathformer_taxonomic_advance(state: dict, result: dict) -> Advanced:
        updated = source().advance(state, result)
        return {"state": updated, "done": updated["index"] >= len(updated["cases"])}

    @mcp.tool()
    def mathformer_taxonomic_empty_state(state: dict) -> Advanced:
        if state["cases"]:
            raise ValueError("empty branch requires no cases")
        return {"state": state, "done": True}

    @mcp.tool()
    def mathformer_taxonomic_finalize(state: dict, report_path: str) -> Report:
        path = path_for(report_path, source().REPORT_PATH)
        write_guard(path)
        return {"report": source().finalize(state, path)}

    @mcp.tool()
    def mathformer_taxonomic_finish_cli(report: dict) -> Finished:
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = source().finish_cli(report, True)
        return {"report": report, "exit_code": code, "stdout": stream.getvalue()}


def main():
    """Serve the same production registrations without unrelated backend imports."""
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("Mathformer taxonomic navigation")
    register_taxonomic_navigation_tools(mcp, lambda path: None)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
