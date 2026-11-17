# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable MCP ports for the shared native static theory-prior steps.

The explicit working directory preserves relative CLI output paths. Calls that
temporarily change cwd or stdout are serialized. Native reports are returned
verbatim and forwarded to stderr, leaving stdout for MCP framing.
"""

from contextlib import redirect_stdout
from functools import lru_cache
import importlib.util
import io
import os
from pathlib import Path
import sys
from threading import RLock
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "paper_skills/theory-evolution-modeler/scripts/build_theory_evolution_model.py"
_LOCK = RLock()


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "theory_evolution_model_native", ROOT / SOURCE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Context(TypedDict):
    working_directory: str


class Parsed(TypedDict):
    args: dict
    help_report: str


class Constructed(TypedDict):
    prior: dict


class Persisted(TypedDict):
    output: str


class Reported(TypedDict):
    result: dict
    exit_code: int
    report: str


class Halted(TypedDict):
    result: None
    exit_code: int
    report: str


def register_theory_evolution_model_tools(mcp, write_guard=lambda path: None):
    @mcp.tool()
    def mathformer_theory_model_parse(argv: list[str]) -> Parsed:
        """Parse native argv, exposing help as a successful terminal branch."""
        stream = io.StringIO()
        with _LOCK:
            try:
                with redirect_stdout(stream):
                    args = source().parse_arguments(argv)
            except SystemExit as error:
                text = stream.getvalue()
                if text:
                    print(text, end="", file=sys.stderr)
                if error.code != 0:
                    raise ValueError(
                        f"argparse terminated with exit code {error.code}"
                    ) from error
                return {
                    "args": {
                        "preset": "default-mathformer-theory",
                        "output": "",
                        "json": False,
                        "halted": True,
                    },
                    "help_report": text,
                }
        return {"args": {**args, "halted": False}, "help_report": ""}

    @mcp.tool()
    def mathformer_theory_model_help(help_report: str) -> Halted:
        """Pack argparse's successful exit; help was already printed by parse."""
        return {"result": None, "exit_code": 0, "report": help_report}

    @mcp.tool()
    def mathformer_theory_model_construct(args: dict) -> Constructed:
        """Construct the sole static prior once through PRESETS."""
        return {"prior": source().construct_prior(args)}

    @mcp.tool()
    def mathformer_theory_model_persist(
        args: dict, prior: dict, context: Context
    ) -> Persisted:
        """Write in the caller's working directory under the service write guard."""
        directory = Path(context["working_directory"])
        if not directory.is_absolute():
            raise ValueError("working_directory must be absolute")
        with _LOCK:
            previous = Path.cwd()
            try:
                os.chdir(directory)
                write_guard(Path(args["output"]).resolve())
                return {"output": source().persist_prior(args, prior)}
            finally:
                os.chdir(previous)

    @mcp.tool()
    def mathformer_theory_model_report(
        args: dict, prior: dict, output: str
    ) -> Reported:
        """Emit and return the exact native report; printing errors propagate."""
        stream = io.StringIO()
        with _LOCK:
            with redirect_stdout(stream):
                result = source().report_and_return(args, prior, output)
            report = stream.getvalue()
            print(report, end="", file=sys.stderr)
        return {**result, "report": report}


if __name__ == "__main__":
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("Mathformer theory evolution model")
    register_theory_evolution_model_tools(server)
    server.run(transport="stdio")
