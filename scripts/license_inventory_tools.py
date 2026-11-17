# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable ports for the native installed-distribution inventory steps."""

from contextlib import redirect_stdout, redirect_stderr
import io
from pathlib import Path
import sys
from typing_extensions import TypedDict
import generate_python_license_inventory as native


class Context(TypedDict):
    working_directory: str
    allow_mutating: bool


class Parsed(TypedDict):
    output: str | None
    halted: bool
    stdout: str


class Collected(TypedDict):
    rows: list[list[str]]


class Rendered(TypedDict):
    content: str


class Ready(TypedDict):
    ready: bool


class Written(TypedDict):
    exit_code: int
    stdout: str


def destination(output, context):
    if output is None:
        raise ValueError("No output path after argparse early exit")
    root = Path(context["working_directory"])
    if not root.is_absolute() or not root.is_dir():
        raise ValueError("working_directory must be an existing absolute directory")
    path = Path(output)
    return path if path.is_absolute() else root / path


def register_license_inventory_tools(mcp, write_policy=lambda: None):
    @mcp.tool()
    def mathformer_license_inventory_parse(argv: list[str]) -> Parsed:
        stdout, stderr = io.StringIO(), io.StringIO()
        try:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                args = native.parse_arguments(argv)
        except SystemExit as error:
            print(stdout.getvalue() + stderr.getvalue(), end="", file=sys.stderr)
            if error.code != 0:
                raise ValueError(
                    f"argparse exit {error.code}: {stderr.getvalue()}"
                ) from error
            return {"output": None, "halted": True, "stdout": stdout.getvalue()}
        return {
            "output": str(args.output),
            "halted": False,
            "stdout": stdout.getvalue(),
        }

    @mcp.tool()
    def mathformer_license_inventory_help(stdout: str) -> Written:
        return {"exit_code": 0, "stdout": stdout}

    @mcp.tool()
    def mathformer_license_inventory_collect() -> Collected:
        return {"rows": [list(row) for row in native.package_rows()]}

    @mcp.tool()
    def mathformer_license_inventory_render(rows: list[list[str]]) -> Rendered:
        return {"content": native.render(rows)}

    @mcp.tool()
    def mathformer_license_inventory_mkdir(
        output: str | None, context: Context
    ) -> Ready:
        write_policy()
        if not context["allow_mutating"]:
            raise ValueError("Inventory writes require allow_mutating")
        return {"ready": native.create_directory(destination(output, context))}

    @mcp.tool()
    def mathformer_license_inventory_write(
        output: str | None, content: str, ready: bool, context: Context
    ) -> Written:
        write_policy()
        if not context["allow_mutating"] or ready is not True:
            raise ValueError(
                "Inventory write requires authorization and directory completion"
            )
        path = destination(output, context)

        # Preserve the CLI-selected spelling in the source-owned print while
        # resolving relative filesystem access without process-global chdir.
        class Destination:
            def write_text(self, content, *, encoding):
                return path.write_text(content, encoding=encoding)

            def __str__(self):
                return str(Path(output))

        stream = io.StringIO()
        with redirect_stdout(stream):
            code = native.write_inventory(Destination(), content)
        print(stream.getvalue(), end="", file=sys.stderr)
        return {"exit_code": code, "stdout": stream.getvalue()}
