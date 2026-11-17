# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""JSON-safe MCP ports over the native FormalScience parser and handlers."""

import argparse
from contextlib import redirect_stdout, redirect_stderr
from functools import lru_cache
import importlib.util
import io
from pathlib import Path
import sys
from typing_extensions import TypedDict


class Parsed(TypedDict):
    command: str
    options: dict


class ParseResult(TypedDict):
    args: Parsed


class Completion(TypedDict):
    exit_code: int
    stdout: str
    stderr: str


@lru_cache(maxsize=1)
def source():
    path = (
        Path(__file__).resolve().parents[1]
        / "benchmarks/formal_science/formal_science.py"
    )
    spec = importlib.util.spec_from_file_location(
        "mathformer_formal_science_native", path
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def parse(argv: list[str]) -> ParseResult:
    stdout, stderr = io.StringIO(), io.StringIO()
    try:
        with redirect_stdout(stdout), redirect_stderr(stderr):
            args = source().parse_args(argv)
    except SystemExit as error:
        return {
            "args": {
                "command": "argparse-exit",
                "options": {
                    "exit_code": error.code,
                    "stdout": stdout.getvalue(),
                    "stderr": stderr.getvalue(),
                },
            }
        }
    finally:
        print(stdout.getvalue(), end="", file=sys.stderr)
        print(stderr.getvalue(), end="", file=sys.stderr)
    options = {
        key: str(value) if isinstance(value, Path) else value
        for key, value in vars(args).items()
        if key not in {"func", "command"}
    }
    return {"args": {"command": args.command, "options": options}}


def invoke(command: str, args: Parsed) -> Completion:
    native = source()
    if args["command"] != command:
        raise ValueError("parsed command does not match the selected handler")
    handlers = {
        "download": native._cmd_download,
        "stats": native._cmd_stats,
        "rank": native._cmd_rank,
        "export-informal-sample": native._cmd_export_informal_sample,
        "self-test": native._cmd_self_test,
    }
    options = dict(args["options"])
    for key in ("output", "output_file", "bundle_dir"):
        if key in options and options[key] is not None:
            options[key] = Path(options[key])
    namespace = argparse.Namespace(command=command, func=handlers[command], **options)
    stdout, stderr = io.StringIO(), io.StringIO()
    # The native error boundary and ordered writes run unchanged. Even on an
    # unhandled exception retain diagnostics already emitted before the failure.
    try:
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = native.dispatch_args(namespace)
    finally:
        print(stdout.getvalue(), end="", file=sys.stderr)
        print(stderr.getvalue(), end="", file=sys.stderr)
    return {"exit_code": code, "stdout": stdout.getvalue(), "stderr": stderr.getvalue()}


def register_formal_science_tools(mcp, before_write=None):
    @mcp.tool()
    def mathformer_formal_science_parse(argv: list[str]) -> ParseResult:
        return parse(argv)

    @mcp.tool()
    def mathformer_formal_science_parse_exit(args: Parsed) -> Completion:
        """Transport an argparse termination without dispatching a native handler."""
        if args["command"] != "argparse-exit":
            raise ValueError("expected an argparse termination")
        return {
            "exit_code": args["options"]["exit_code"],
            "stdout": args["options"]["stdout"],
            "stderr": args["options"]["stderr"],
        }

    @mcp.tool()
    def mathformer_formal_science_download(args: Parsed) -> Completion:
        if before_write is not None:
            before_write()
        return invoke("download", args)

    @mcp.tool()
    def mathformer_formal_science_stats(args: Parsed) -> Completion:
        return invoke("stats", args)

    @mcp.tool()
    def mathformer_formal_science_rank(args: Parsed) -> Completion:
        return invoke("rank", args)

    @mcp.tool()
    def mathformer_formal_science_export(args: Parsed) -> Completion:
        if before_write is not None:
            before_write()
        return invoke("export-informal-sample", args)

    @mcp.tool()
    def mathformer_formal_science_self_test(args: Parsed) -> Completion:
        return invoke("self-test", args)
