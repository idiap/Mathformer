# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP ports over the native foundation drafter, with an explicit mount.

No provider, Lean compiler, or scientific verification is part of drafting.
CLI-relative input/output paths resolve against the mounted working directory.
"""

from contextlib import redirect_stdout
import importlib.util
import json
from pathlib import Path
import sys
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "skills/mathformerphysicslib/mathformerphysicslib-foundation-drafter/scripts/draft_foundation_modules.py"
)
spec = importlib.util.spec_from_file_location("foundation_draft_source", SOURCE)
source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source)


class Context(TypedDict):
    repository_root: str
    allow_mutating: bool


class Parsed(TypedDict):
    options: dict


class Requested(TypedDict):
    request: dict


class Initialized(TypedDict):
    state: dict


class Advanced(TypedDict):
    state: dict
    done: bool


class Finished(TypedDict):
    report: dict
    rendered_report: str


class Emitted(TypedDict):
    exit_code: int


def mount(context):
    root = Path(context["repository_root"]).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("repository_root must be a directory")
    return root


def register_foundation_draft_tools(mcp, write_policy, path_allowed):
    def authorize(context, path):
        if not context["allow_mutating"]:
            raise ValueError("Foundation writes require allow_mutating")
        write_policy()
        if not path_allowed(path):
            raise ValueError("Foundation output is outside service write roots")

    @mcp.tool()
    def mathformer_foundation_draft_parse(argv: list[str]) -> Parsed:
        """Use native argparse; retain diagnostic output and report CLI exits."""
        try:
            with redirect_stdout(sys.stderr):
                return {"options": source.parse_options(argv)}
        except SystemExit as error:
            # An argparse exit must terminate this call, never the MCP service.
            raise ValueError(
                f"Native argparse exited with code {error.code}"
            ) from error

    @mcp.tool()
    def mathformer_foundation_draft_self_test_request() -> Requested:
        return {"request": source.self_test_request()}

    @mcp.tool()
    def mathformer_foundation_draft_load_request(
        options: dict, context: Context
    ) -> Requested:
        return {"request": source.request_from_options(options, mount(context))}

    @mcp.tool()
    def mathformer_foundation_draft_initialize(request: dict) -> Initialized:
        return {"state": source.initialize_draft(request)}

    @mcp.tool()
    def mathformer_foundation_draft_draft_next(
        request: dict, state: dict, context: Context
    ) -> Advanced:
        root = mount(context)
        # Constrain the public iterator port to source-selected module names.
        if state["modules"] != source.modules_from_plan(request["plan"]):
            raise ValueError(
                "Iterator modules differ from the source-selected templates"
            )
        if not 0 <= state["cursor"] < len(state["modules"]):
            raise ValueError("Iterator cursor is outside selected modules")
        if (
            len(state["items"]) != state["cursor"]
            or len(state["item_history"]) != state["cursor"]
        ):
            raise ValueError("Iterator state does not match its cursor")
        if request["write"]:
            authorize(
                context,
                root
                / "MathformerPhysicsLib/Lean/Foundations"
                / f"{state['modules'][state['cursor']]}.lean",
            )
        return source.draft_next(request, state, root)

    @mcp.tool()
    def mathformer_foundation_draft_finish(
        request: dict, state: dict, options: dict, context: Context
    ) -> Finished:
        root = mount(context)
        if state["modules"] != source.modules_from_plan(request["plan"]) or state[
            "cursor"
        ] != len(state["modules"]):
            raise ValueError("Cannot finish an incomplete source traversal")
        if (
            len(state["items"]) != state["cursor"]
            or len(state["item_history"]) != state["cursor"]
        ):
            raise ValueError("Iterator state does not match its cursor")
        if request["write"]:
            authorize(context, root / "MathformerPhysicsLib/Lean/Foundations.lean")
        report = source.finish_draft(request, state, options, root)
        return {"report": report, "rendered_report": source.render_report(report)}

    @mcp.tool()
    def mathformer_foundation_draft_emit(
        options: dict, report: dict, rendered_report: str, context: Context
    ) -> Emitted:
        root = mount(context)
        if json.loads(rendered_report) != report:
            raise ValueError("Rendered report differs from the structured report")
        if options["output"]:
            path = Path(options["output"])
            authorize(context, path if path.is_absolute() else root / path)
        # Protocol stdout is reserved for MCP; native printed reports go to stderr.
        with redirect_stdout(sys.stderr):
            return {"exit_code": source.emit_report(options, rendered_report, root)}
