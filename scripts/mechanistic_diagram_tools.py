# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP bindings for the shared native mechanistic diagram steps.

Reports retain their native formatting on stderr; stdout is MCP framing.
SystemExit terminates a call or selects the help branch, never the server.
"""

from contextlib import redirect_stdout
from functools import lru_cache
import importlib.util
import io
from pathlib import Path
import sys
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "paper_skills/mechanistic-diagram-modeler/scripts/build_mechanistic_diagram_model.py"


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "mechanistic_diagram_native", ROOT / SOURCE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Parsed(TypedDict):
    options: dict
    help_report: str | dict


class Constructed(TypedDict):
    model: dict


class Written(TypedDict):
    diagram: dict
    output: str


class Reported(TypedDict):
    report: dict | str
    exit_code: int


def register_mechanistic_diagram_tools(mcp, write_guard=lambda path: None):
    @mcp.tool()
    def mathformer_diagram_parse(argv: list[str]) -> Parsed:
        stream = io.StringIO()
        try:
            with redirect_stdout(stream):
                options = source().parse_options(argv)
        except SystemExit as error:
            text = stream.getvalue()
            if text:
                print(text, end="", file=sys.stderr)
            if error.code != 0:
                raise ValueError(
                    f"argparse terminated with exit code {error.code}"
                ) from error
            return {
                "options": {
                    "preset": "mathformer-framework",
                    "output": "",
                    "json": False,
                    "halted": True,
                },
                "help_report": text,
            }
        return {"options": {**options, "halted": False}, "help_report": ""}

    @mcp.tool()
    def mathformer_diagram_construct(options: dict) -> Constructed:
        return {"model": source().construct_model(options)}

    @mcp.tool()
    def mathformer_diagram_write(options: dict, model: dict) -> Written:
        write_guard(Path(options["output"]).resolve())
        output = source().write_model(options, model)
        return {"diagram": model, "output": output}

    @mcp.tool()
    def mathformer_diagram_report(options: dict, model: dict, output: str) -> Reported:
        with redirect_stdout(sys.stderr):
            return source().report_and_return(options, model, output)


if __name__ == "__main__":
    # Focused stdio service for these deterministic tools. The aggregate service
    # uses the same registrations with its read-only and write-root policy.
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("Mathformer mechanistic diagram")
    register_mechanistic_diagram_tools(server)
    server.run(transport="stdio")
