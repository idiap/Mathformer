# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable fixed setup:lean installer stages, shared with the CLI."""

from contextlib import redirect_stdout
import sys
from typing_extensions import TypedDict
import install_env as native


class LeanArgs(TypedDict):
    skip_python: bool
    with_lean: bool
    skip_lean: bool


class Initialized(TypedDict):
    args: LeanArgs


class Resolved(TypedDict):
    lake: str


class Done(TypedDict):
    done: None


class Completed(TypedDict):
    exit_code: int


def register_setup_lean_tools(mcp, before_write):
    def invoke(function, *args):
        try:
            with redirect_stdout(sys.stderr):
                return function(*args)
        except SystemExit as error:
            raise RuntimeError(str(error)) from error

    def authorize(lake, allow_mutating):
        if not allow_mutating:
            raise PermissionError("setup:lean requires mutation authorization")
        before_write((native.ROOT_DIR / ".lake").resolve())
        if lake != native.shutil.which("lake"):
            raise ValueError("Expected the installed Lake executable")

    @mcp.tool()
    def mathformer_setup_lean_initialize(argv: list[str]) -> Initialized:
        if argv != ["--skip-python", "--with-lean"]:
            raise ValueError("setup:lean forbids extra or alternate arguments")
        args = invoke(native.initialize, argv)
        return {"args": {key: getattr(args, key) for key in LeanArgs.__annotations__}}

    @mcp.tool()
    def mathformer_setup_lean_require_lake(args: LeanArgs) -> Resolved:
        if args != dict(skip_python=True, with_lean=True, skip_lean=False):
            raise ValueError("Expected fixed setup:lean arguments")
        return {"lake": invoke(native.resolve_lake)}

    @mcp.tool()
    def mathformer_setup_lean_update(lake: str, allow_mutating: bool) -> Done:
        authorize(lake, allow_mutating)
        return {"done": invoke(native.update_lean, lake)}

    @mcp.tool()
    def mathformer_setup_lean_build(
        lake: str, updated: None, allow_mutating: bool
    ) -> Done:
        authorize(lake, allow_mutating)
        return {"done": invoke(native.build_lean, lake)}

    @mcp.tool()
    def mathformer_setup_lean_complete(built: None) -> Completed:
        return {"exit_code": invoke(native.complete)}
