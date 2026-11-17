# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable stages for the immutable setup:atp-kb installer invocation."""

import argparse
from contextlib import redirect_stdout
from pathlib import Path
import sys
from typing_extensions import TypedDict
import install_env as native


class InstallerArgs(TypedDict):
    skip_python: bool
    with_atp_kb: bool
    with_lean: bool
    skip_lean: bool
    venv_path: str
    with_benchmarks: bool
    with_sympy: bool
    with_paper_extraction: bool
    with_mcp: bool
    mcp_service: bool
    all_extras: bool


class Initialized(TypedDict):
    args: InstallerArgs


class Completed(TypedDict):
    exit_code: int


def serialize(args):
    return {
        key: str(args.venv_path) if key == "venv_path" else getattr(args, key)
        for key in InstallerArgs.__annotations__
    }


def unpack(args):
    expected = serialize(
        native.parse_args(["--with-atp-kb", "--venv-path=" + args["venv_path"]])
    )
    if args != expected or not args["venv_path"]:
        raise ValueError("args must preserve the fixed setup:atp-kb invocation")
    return argparse.Namespace(**{**args, "venv_path": Path(args["venv_path"])})


def register_setup_atp_kb_tools(mcp, before_write):
    def invoke(function, *args):
        try:
            with redirect_stdout(sys.stderr):
                return function(*args)
        except SystemExit as error:
            raise RuntimeError(str(error)) from error

    @mcp.tool()
    def mathformer_setup_atp_kb_initialize() -> Initialized:
        return {"args": serialize(invoke(native.initialize, ["--with-atp-kb"]))}

    @mcp.tool()
    def mathformer_setup_atp_kb_install_python(
        args: InstallerArgs, allow_mutating: bool
    ) -> dict:
        if not allow_mutating:
            raise PermissionError("setup:atp-kb requires mutation authorization")
        settings = unpack(args)
        path = settings.venv_path
        before_write((path if path.is_absolute() else native.ROOT_DIR / path).resolve())
        invoke(native.install_python, settings)
        return {}

    @mcp.tool()
    def mathformer_setup_atp_kb_setup_lean(args: InstallerArgs) -> dict:
        invoke(native.setup_lean, unpack(args))
        return {}

    @mcp.tool()
    def mathformer_setup_atp_kb_complete() -> Completed:
        return {"exit_code": invoke(native.complete)}
