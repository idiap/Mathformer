# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Typed MCP bindings to the native dependency lock contract steps."""

from contextlib import redirect_stdout
from functools import lru_cache
import importlib.util
import io
from pathlib import Path
import sys
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "dependency_lock_native",
        ROOT / "tests/environment/run_dependency_lock_contract.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Context(TypedDict):
    repository_root: str


class UvResult(TypedDict):
    returncode: int
    stdout: str
    stderr: str


class Checked(TypedDict):
    result: UvResult


class FileTexts(TypedDict):
    project_text: str
    lock_text: str


class Read(TypedDict):
    texts: FileTexts


class Evaluated(TypedDict):
    payload: dict


class Emitted(TypedDict):
    stdout: str
    exit_code: int


def register_dependency_lock_tools(mcp):
    @mcp.tool()
    def mathformer_dependency_lock_check_uv(context: Context) -> Checked:
        return {"result": source().check_uv(Path(context["repository_root"]))}

    @mcp.tool()
    def mathformer_dependency_lock_read_files(context: Context) -> Read:
        return {"texts": source().read_files(Path(context["repository_root"]))}

    @mcp.tool()
    def mathformer_dependency_lock_build_payload(
        uv: UvResult, texts: FileTexts, context: Context
    ) -> Evaluated:
        return {
            "payload": source().build_payload(
                Path(context["repository_root"]), uv, texts
            )
        }

    @mcp.tool()
    def mathformer_dependency_lock_print_and_return(
        payload: dict, json_output: bool
    ) -> Emitted:
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = source().print_and_return(payload, json_output)
        # Stdio MCP reserves stdout for protocol frames. Keep native output in
        # the returned port and on the diagnostic stream.
        print(stream.getvalue(), end="", file=sys.stderr)
        return {"stdout": stream.getvalue(), "exit_code": code}
