# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""JSON ports for ProofNet's native parser and single-dispatch handlers."""

import argparse
from contextlib import redirect_stdout
from functools import lru_cache
import importlib.util
import io
from pathlib import Path
import sys
from typing import TypedDict

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "mathformer_proofnet_native", ROOT / "benchmarks/proofnet/proofnet.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class Parsed(TypedDict):
    args: dict


class Completion(TypedDict):
    result: int
    stdout: str


def parse(extra_args: list[str]) -> Parsed:
    with redirect_stdout(sys.stderr):
        try:
            args = source().parse_args(extra_args)
        except SystemExit as error:
            # argparse must terminate this operation, never the MCP server.
            raise ValueError(
                f"argparse terminated with exit code {error.code}"
            ) from error
    return {
        "args": {
            key: str(value) if isinstance(value, Path) else value
            for key, value in vars(args).items()
            if key != "func"
        }
    }


def invoke(command: str, args: dict) -> Completion:
    if args["command"] != command:
        raise ValueError("parsed command does not match selected handler")
    native = source()
    handlers = {
        "download": native._cmd_download,
        "stats": native._cmd_stats,
        "sample": native._cmd_sample,
        "export-inputs": native._cmd_export_inputs,
    }
    options = dict(args)
    for key in ("output", "output_file", "cache_dir"):
        if options.get(key) is not None:
            options[key] = Path(options[key])
    namespace = argparse.Namespace(**options, func=handlers[command])
    stdout = io.StringIO()
    try:
        with redirect_stdout(stdout):
            result = native.dispatch_args(namespace)
    finally:
        # Keep native diagnostics visible while protecting the stdio protocol.
        print(stdout.getvalue(), end="", file=sys.stderr)
    return {"result": result, "stdout": stdout.getvalue()}


def register_proofnet_tools(mcp, before_write):
    @mcp.tool()
    def mathformer_proofnet_benchmark_parse(extra_args: list[str]) -> Parsed:
        return parse(extra_args)

    @mcp.tool()
    def mathformer_proofnet_benchmark_download(args: dict) -> Completion:
        before_write(
            [
                Path(args["output"]),
                (
                    Path(args["cache_dir"])
                    if args.get("cache_dir")
                    else Path(args["output"]) / ".hf_cache"
                ),
            ]
        )
        return invoke("download", args)

    @mcp.tool()
    def mathformer_proofnet_benchmark_stats(args: dict) -> Completion:
        return invoke("stats", args)

    @mcp.tool()
    def mathformer_proofnet_benchmark_sample(args: dict) -> Completion:
        return invoke("sample", args)

    @mcp.tool()
    def mathformer_proofnet_benchmark_export_inputs(args: dict) -> Completion:
        before_write([Path(args["output_file"])])
        return invoke("export-inputs", args)
