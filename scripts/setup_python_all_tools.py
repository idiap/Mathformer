# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Six callable stages of the fixed setup:python-all native invocation."""

from contextlib import redirect_stdout
from pathlib import Path
import sys
from typing_extensions import TypedDict
import install_env as native
from setup_all_tools import Settings


class Initialized(TypedDict):
    args: Settings


class Environment(TypedDict):
    uv: str
    venv_path: str
    python_bin: str


class Prepared(TypedDict):
    environment: Environment


class Selected(TypedDict):
    dependencies: list[str]


class Installed(TypedDict):
    installed: bool


class Finished(TypedDict):
    finished: bool


class Completed(TypedDict):
    exit_code: int


def serialize(args):
    return {
        key: str(args.venv_path) if key == "venv_path" else getattr(args, key)
        for key in Settings.__annotations__
    }


def unpack(args):
    parsed = native.parse_args(["--all-extras", "--venv-path=" + args["venv_path"]])
    if not args["venv_path"] or serialize(parsed) != args:
        raise ValueError("args must preserve the fixed setup:python-all invocation")
    return parsed


def register_setup_python_all_tools(mcp, before_write):
    def invoke(function, *args):
        try:
            with redirect_stdout(sys.stderr):
                return function(*args)
        except SystemExit as error:
            raise RuntimeError(str(error)) from error

    def authorize(allow_mutating, path):
        if not allow_mutating:
            raise PermissionError("setup:python-all requires mutation authorization")
        before_write(Path(path).resolve())

    @mcp.tool()
    def mathformer_setup_python_all_initialize() -> Initialized:
        return {"args": serialize(invoke(native.initialize, ["--all-extras"]))}

    @mcp.tool()
    def mathformer_setup_python_all_prepare_environment(
        args: Settings, allow_mutating: bool
    ) -> Prepared:
        parsed = unpack(args)
        path = parsed.venv_path
        authorize(
            allow_mutating, path if path.is_absolute() else native.ROOT_DIR / path
        )
        return {"environment": invoke(native.prepare_python_environment, parsed)}

    @mcp.tool()
    def mathformer_setup_python_all_select_dependencies(
        args: Settings, environment: Environment
    ) -> Selected:
        return {"dependencies": invoke(native.selected_python_deps, unpack(args))}

    @mcp.tool()
    def mathformer_setup_python_all_install_dependencies(
        environment: Environment, dependencies: list[str], allow_mutating: bool
    ) -> Installed:
        authorize(allow_mutating, environment["venv_path"])
        invoke(native.install_python_dependencies, environment, dependencies)
        return {"installed": True}

    @mcp.tool()
    def mathformer_setup_python_all_setup_lean(
        args: Settings, installed: bool
    ) -> Finished:
        if installed is not True:
            raise ValueError("Python installation must finish first")
        invoke(native.setup_lean, unpack(args))
        return {"finished": True}

    @mcp.tool()
    def mathformer_setup_python_all_complete(finished: bool) -> Completed:
        if finished is not True:
            raise ValueError("Lean setup must return before completion")
        return {"exit_code": invoke(native.complete)}
