# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Fixed setup:all MCP stages using the native installer implementation."""

from contextlib import redirect_stdout
import sys
from typing_extensions import TypedDict
import install_env as native


class Settings(TypedDict):
    venv_path: str
    skip_python: bool
    with_lean: bool
    skip_lean: bool
    all_extras: bool
    mcp_service: bool


class Initialized(TypedDict):
    settings: Settings


class Completed(TypedDict):
    exit_code: int


def unpack(settings):
    args = native.parse_args(
        ["--all-extras", "--with-lean", "--venv-path", settings["venv_path"]]
    )
    expected = {
        key: str(args.venv_path) if key == "venv_path" else getattr(args, key)
        for key in Settings.__annotations__
    }
    if settings != expected:
        raise ValueError("settings must preserve the fixed setup:all invocation")
    return args


def register_setup_all_tools(mcp, before_write):
    def invoke(function, *args):
        try:
            with redirect_stdout(sys.stderr):
                return function(*args)
        except SystemExit as error:
            # A missing tool/interpreter is an operation failure, never a server exit.
            raise RuntimeError(str(error)) from error

    @mcp.tool()
    def mathformer_setup_all_initialize() -> Initialized:
        args = invoke(native.initialize, ["--all-extras", "--with-lean"])
        return {
            "settings": {
                key: str(args.venv_path) if key == "venv_path" else getattr(args, key)
                for key in Settings.__annotations__
            }
        }

    @mcp.tool()
    def mathformer_setup_all_python_environment(
        settings: Settings, allow_mutating: bool
    ) -> dict:
        if not allow_mutating:
            raise PermissionError("setup:all requires mutation authorization")
        args = unpack(settings)
        path = (
            args.venv_path
            if args.venv_path.is_absolute()
            else native.ROOT_DIR / args.venv_path
        )
        before_write(path.resolve())
        invoke(native.install_python, args)
        return {}

    @mcp.tool()
    def mathformer_setup_all_lean_environment(allow_mutating: bool) -> dict:
        if not allow_mutating:
            raise PermissionError("setup:all requires mutation authorization")
        before_write((native.ROOT_DIR / ".lake").resolve())
        invoke(native.install_lean)
        return {}

    @mcp.tool()
    def mathformer_setup_all_complete() -> Completed:
        return {"exit_code": invoke(native.complete)}
