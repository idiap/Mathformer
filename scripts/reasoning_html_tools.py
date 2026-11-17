# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable MCP ports for the native reasoning dashboard entrypoint.

Working directory is explicit because native CLI paths are process-relative.
Capture CLI emissions so they cannot corrupt stdio MCP framing.
"""

from contextlib import contextmanager, redirect_stdout, redirect_stderr
import importlib.util
import io
import os
from pathlib import Path
from threading import RLock
from typing import Optional
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "skills/control/reasoning-log-schema-guardian/scripts/render_reasoning_log_html.py"
)
spec = importlib.util.spec_from_file_location("_reasoning_html_native", SOURCE)
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)
_LOCK = RLock()


class Context(TypedDict):
    working_directory: str


class Parsed(TypedDict):
    options: dict
    selected: str
    missing: bool


class Prepared(TypedDict):
    paths: dict


class Loaded(TypedDict):
    events: list[dict]


class Validated(TypedDict):
    validation: Optional[dict]


class Rendered(TypedDict):
    html: str


class Finished(TypedDict):
    result: dict


@contextmanager
def invocation(context):
    with _LOCK:
        previous = Path.cwd()
        emissions = io.StringIO()
        try:
            os.chdir(context["working_directory"])
            with redirect_stdout(emissions), redirect_stderr(emissions):
                try:
                    yield
                except SystemExit as error:
                    raise ValueError(
                        f"argparse exit {error.code}: {emissions.getvalue()}"
                    ) from error
        finally:
            os.chdir(previous)


def register_reasoning_html_tools(mcp):
    @mcp.tool()
    def mathformer_reasoning_html_parse_select(
        argv: list[str], context: Context
    ) -> Parsed:
        with invocation(context):
            return native.parse_select(argv)

    @mcp.tool()
    def mathformer_reasoning_html_resolve_paths(
        options: dict, selected: str, context: Context
    ) -> Prepared:
        with invocation(context):
            return {"paths": native.resolve_paths(options, selected)}

    @mcp.tool()
    def mathformer_reasoning_html_fixtures_resolve(
        options: dict, selected: str, context: Context
    ) -> Prepared:
        with invocation(context):
            return {"paths": native.fixtures_resolve(options, selected)}

    @mcp.tool()
    def mathformer_reasoning_html_load(paths: dict, context: Context) -> Loaded:
        with invocation(context):
            return {"events": native.load_events(Path(paths["log_file"]))}

    @mcp.tool()
    def mathformer_reasoning_html_validate(
        options: dict, paths: dict, context: Context
    ) -> Validated:
        with invocation(context):
            return {"validation": native.validate_selected(options, paths)}

    @mcp.tool()
    def mathformer_reasoning_html_render(
        options: dict,
        paths: dict,
        events: list[dict],
        validation: Optional[dict],
        context: Context,
    ) -> Rendered:
        with invocation(context):
            return {"html": native.render_selected(options, paths, events, validation)}

    @mcp.tool()
    def mathformer_reasoning_html_write_finish(
        paths: dict, html: str, validation: Optional[dict], context: Context
    ) -> Finished:
        with invocation(context):
            return {"result": native.write_finish(paths, html, validation)}
