# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Read-only plugin check steps shared with the native synchronization CLI."""

from contextlib import redirect_stdout
from pathlib import Path
import sys
from typing import Literal
from typing_extensions import TypedDict
import sync_agent_plugins as native


class ProjectionResult(TypedDict):
    expected: dict[str, str]
    expected_order: list[str]


class StaleResult(TypedDict):
    stale: list[str]


class ComparisonResult(TypedDict):
    differences: list[str]
    drift: bool


class CheckResult(TypedDict):
    ok: bool
    mode: Literal["check"]
    changed: list[str]
    exit_code: Literal[0, 1]


class ReportResult(TypedDict):
    result: CheckResult


def paths(expected: dict[str, str]) -> dict[Path, str]:
    return {Path(path): content for path, content in expected.items()}


def register_plugin_check_tools(mcp):
    @mcp.tool()
    def mathformer_plugin_check_project(root: str) -> ProjectionResult:
        expected = native.expected_files(Path(root))
        return {
            "expected": {str(p): text for p, text in expected.items()},
            "expected_order": [str(p) for p in expected],
        }

    @mcp.tool()
    def mathformer_plugin_check_find_stale(
        root: str, expected: dict[str, str]
    ) -> StaleResult:
        return {
            "stale": [str(p) for p in native.find_stale(Path(root), paths(expected))]
        }

    @mcp.tool()
    def mathformer_plugin_check_compare(
        root: str, expected: dict[str, str], stale: list[str], expected_order: list[str]
    ) -> ComparisonResult:
        if len(expected_order) != len(expected) or set(expected_order) != set(expected):
            raise ValueError("Projection order does not match expected files")
        ordered = {Path(p): expected[p] for p in expected_order}
        differences = native.compare_projection(
            Path(root), ordered, [Path(p) for p in stale]
        )
        return {"differences": differences, "drift": bool(differences)}

    @mcp.tool()
    def mathformer_plugin_check_report(
        differences: list[str], ok: bool, exit_code: Literal[0, 1]
    ) -> ReportResult:
        # MCP reserves stdout for protocol frames; retain native JSON on stderr.
        with redirect_stdout(sys.stderr):
            payload = native.emit_plugin_report(differences, check=True, ok=ok)
        return {"result": {**payload, "exit_code": exit_code}}


if __name__ == "__main__":
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("mathformer-plugin-check")
    register_plugin_check_tools(server)
    server.run(transport="stdio")
