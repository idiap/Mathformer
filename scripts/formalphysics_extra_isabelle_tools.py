# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP ports for the shared fixed-case Isabelle generator; no prover invocation."""

from contextlib import redirect_stdout
from pathlib import Path
import sys
from typing_extensions import TypedDict
import generate_formalphysics_extra_isabelle as native


class State(TypedDict):
    cursor: int
    promote_lib: bool
    generated: list[str]


class Files(TypedDict):
    artifact_theory: str
    artifact_root: str
    lib_theory: str | None
    lib_root: str | None


class Initialized(TypedDict):
    state: State


class Written(TypedDict):
    files: Files


class Advanced(TypedDict):
    state: State
    done: bool


class Finished(TypedDict):
    generated: list[str]
    exit_code: int


def register_formalphysics_extra_isabelle_tools(mcp, before_write=lambda: None):
    @mcp.tool()
    def mathformer_extra_isabelle_initialize(argv: list[str]) -> Initialized:
        # SystemExit must not terminate the persistent stdio service.
        try:
            with redirect_stdout(sys.stderr):
                return {"state": native.initialize(argv)}
        except SystemExit as error:
            raise ValueError(f"argparse exited with code {error.code}") from error

    @mcp.tool()
    def mathformer_extra_isabelle_write_case(
        cursor: int, promote_lib: bool, repository_root: str
    ) -> Written:
        before_write()
        root = Path(repository_root).resolve(strict=True)
        return {"files": native.write_case_at(cursor, promote_lib, root)}

    @mcp.tool()
    def mathformer_extra_isabelle_advance(
        state: State, files: Files, repository_root: str
    ) -> Advanced:
        state, done = native.advance(
            state, files, Path(repository_root).resolve(strict=True)
        )
        return {"state": state, "done": done}

    @mcp.tool()
    def mathformer_extra_isabelle_finish(state: State) -> Finished:
        with redirect_stdout(sys.stderr):
            return native.finish(state)
