# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP bindings to the same grounding blocks used by the native CLI."""

from contextlib import redirect_stdout
from functools import lru_cache
import importlib.util
import io
from pathlib import Path
import sys
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "skills/mathformerphysicslib/mathformerphysicslib-mathlib-grounding-auditor/scripts/audit_mathlib_grounding.py"


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "mathlib_grounding_native", ROOT / SOURCE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Parsed(TypedDict):
    options: dict


class Graph(TypedDict):
    graph: dict


class Report(TypedDict):
    report: dict


class Printed(TypedDict):
    report: dict
    returncode: int
    stdout: str


def register_mathlib_grounding_tools(
    mcp, write_policy=lambda: None, path_allowed=lambda path: True
):
    @mcp.tool()
    def mathformer_mathlib_grounding_parse(argv: list[str]) -> Parsed:
        try:
            with redirect_stdout(sys.stderr):
                options = source().parse_options(argv)
        except SystemExit as error:
            # Preserve argparse early termination without exiting the MCP server.
            raise ValueError(f"argparse exited {error.code}") from error
        return {"options": options}

    @mcp.tool()
    def mathformer_mathlib_grounding_self_test() -> Graph:
        return {"graph": source().self_test_graph()}

    @mcp.tool()
    def mathformer_mathlib_grounding_load(options: dict) -> Graph:
        return {"graph": source().load_graph(options)}

    @mcp.tool()
    def mathformer_mathlib_grounding_inventory(repository_root: str | None) -> Graph:
        return {
            "graph": source().inventory_graph(
                None if repository_root is None else Path(repository_root)
            )
        }

    @mcp.tool()
    def mathformer_mathlib_grounding_audit(graph: dict) -> Report:
        return {"report": source().audit_report(graph)}

    @mcp.tool()
    def mathformer_mathlib_grounding_write(options: dict, report: dict) -> dict:
        write_policy()
        if not path_allowed(Path(options["output"]).resolve()):
            raise ValueError("Grounding output is outside service write roots")
        source().write_report(options, report)
        return {}

    @mcp.tool()
    def mathformer_mathlib_grounding_print(report: dict) -> Printed:
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = source().print_report(report)
        stdout = stream.getvalue()
        print(stdout, end="", file=sys.stderr)
        return {"report": report, "returncode": code, "stdout": stdout}
