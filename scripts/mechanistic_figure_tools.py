# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP ports for native figure stages. No provider or alternate renderer.

The explicit working directory preserves relative CLI paths, including tectonic
argv and output metadata. A lock serializes these calls while process cwd and
native stdout are temporarily redirected. stdout remains MCP framing; native
help and reports go to stderr.
"""

from contextlib import contextmanager, redirect_stdout
from functools import lru_cache
import importlib.util
import io
import os
from pathlib import Path
import sys
from threading import RLock
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "paper_skills/mechanistic-figure-renderer/scripts/render_mechanistic_figure.py"
_LOCK = RLock()


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "mechanistic_figure_native", ROOT / SOURCE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Context(TypedDict):
    working_directory: str


class Loaded(TypedDict):
    state: dict
    want_svg: bool
    want_tex: bool
    want_pdf: bool
    halted: bool
    help_text: str


class Carried(TypedDict):
    state: dict


class Reported(TypedDict):
    result: dict | str
    exit_code: int


@contextmanager
def native_context(directory):
    with _LOCK:
        previous = Path.cwd()
        try:
            os.chdir(directory)
            with redirect_stdout(sys.stderr):
                yield
        finally:
            os.chdir(previous)


def register_mechanistic_figure_tools(mcp, write_guard=lambda path: None):
    @mcp.tool()
    def mathformer_figure_load(argv: list[str], context: Context) -> Loaded:
        directory = str(Path(context["working_directory"]).resolve())
        with native_context(directory):
            text = io.StringIO()
            try:
                with redirect_stdout(text):
                    state = source().load_state(argv)
            except SystemExit as error:
                print(text.getvalue(), end="", file=sys.stderr)
                if error.code != 0:
                    raise ValueError(
                        f"argparse terminated with exit code {error.code}"
                    ) from error
                return {
                    "state": {
                        "model": None,
                        "model_path": "",
                        "args": {},
                        "outputs": {},
                        "tex_path": None,
                        "output_order": [],
                        "working_directory": directory,
                    },
                    "want_svg": False,
                    "want_tex": False,
                    "want_pdf": False,
                    "halted": True,
                    "help_text": text.getvalue(),
                }
        state["working_directory"] = directory
        args = state["args"]
        return {
            "state": state,
            "want_svg": bool(args["svg"]),
            "want_tex": bool(args["tex"] or args["compile_pdf"]),
            "want_pdf": args["compile_pdf"],
            "halted": False,
            "help_text": "",
        }

    @mcp.tool()
    def mathformer_figure_carry(state: dict) -> Carried:
        """Export unchanged state from an unrequested output branch."""
        return {"state": state}

    @mcp.tool()
    def mathformer_figure_help(help_text: str) -> Reported:
        """Return argparse's already emitted successful early exit."""
        return {"result": help_text, "exit_code": 0}

    @mcp.tool()
    def mathformer_figure_svg(state: dict) -> Carried:
        with native_context(state["working_directory"]):
            write_guard(Path(state["args"]["svg"]).resolve())
            return {"state": source().svg_step(state)}

    @mcp.tool()
    def mathformer_figure_tex(state: dict) -> Carried:
        with native_context(state["working_directory"]):
            args = state["args"]
            write_guard(
                Path(args["tex"] or Path(args["model"]).with_suffix(".tex")).resolve()
            )
            return {"state": source().tex_step(state)}

    @mcp.tool()
    def mathformer_figure_pdf(state: dict) -> Carried:
        with native_context(state["working_directory"]):
            assert state["tex_path"] is not None
            write_guard(Path(state["tex_path"]).parent.resolve())
            return {"state": source().pdf_step(state)}

    @mcp.tool()
    def mathformer_figure_report(state: dict) -> Reported:
        with native_context(state["working_directory"]):
            return source().report_step(state)
