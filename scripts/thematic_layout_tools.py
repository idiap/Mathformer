# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP interfaces sharing the thematic layout CLI's native operations."""

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
from typing_extensions import TypedDict
import organize_repository_layout as native

ROOT = Path(__file__).resolve().parents[1]


class Context(TypedDict):
    repository_root: str


class Parsed(TypedDict):
    options: dict


class Reported(TypedDict):
    report: dict
    report_json: str


class Halted(TypedDict):
    report: None
    completion: dict


class Finished(TypedDict):
    completion: dict


def repository(context: Context) -> Path:
    root = Path(context["repository_root"]).resolve()
    root.relative_to(ROOT)
    return root


def register_thematic_layout_tools(mcp, write_policy=lambda: None):
    @mcp.tool()
    def mathformer_layout_parse(argv: list[str]) -> Parsed:
        stream = io.StringIO()
        try:
            with redirect_stdout(stream):
                options = native.parse_options(argv)
        except SystemExit as error:
            stdout = stream.getvalue()
            print(stdout, end="", file=sys.stderr)
            if error.code != 0:
                raise ValueError(
                    f"argparse terminated with status {error.code}"
                ) from error
            return {
                "options": {
                    "apply": False,
                    "json": False,
                    "halted": True,
                    "stdout": stdout,
                }
            }
        return {"options": {**options, "halted": False, "stdout": ""}}

    @mcp.tool()
    def mathformer_layout_halt(options: dict) -> Halted:
        """Project argparse's successful help termination without validation."""
        if not options["halted"]:
            raise ValueError("early return requires argparse termination")
        return {
            "report": None,
            "completion": {"stdout": options["stdout"], "exit_code": 0},
        }

    @mcp.tool()
    def mathformer_layout_repair(context: Context) -> dict:
        write_policy()
        root = repository(context)
        try:
            native.apply_views(native.expected_views(root), root)
        except SystemExit as error:
            raise ValueError(str(error)) from error
        return {}

    @mcp.tool()
    def mathformer_layout_validate(context: Context) -> Reported:
        report = native.build_report(repository(context))
        # Retain insertion order across PRISM's record codec for native stdout.
        return {"report": report, "report_json": json.dumps(report)}

    @mcp.tool()
    def mathformer_layout_emit(
        options: dict, report: dict, report_json: str
    ) -> Finished:
        ordered = json.loads(report_json)
        if ordered != report:
            raise ValueError("ordered report differs from typed report")
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = native.finish(ordered, options)
        stdout = stream.getvalue()
        print(stdout, end="", file=sys.stderr)
        return {"completion": {"stdout": stdout, "exit_code": code}}
