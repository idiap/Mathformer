# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Typed MCP bindings for the native extra Lean generator; no compiler or model."""

from contextlib import redirect_stdout
from pathlib import Path
import sys
from typing import TypedDict
import generate_formalphysics_extra_lean as native


class State(TypedDict):
    index: int
    promote_lib: bool
    generated: list[str]


class Initialized(TypedDict):
    state: State


class Written(TypedDict):
    paths: list[str]


class Advanced(TypedDict):
    state: State
    done: bool


class Finished(TypedDict):
    generated: list[str]
    returncode: int


def register_extra_lean_tools(mcp, before_write=lambda: None):
    @mcp.tool()
    def mathformer_extra_lean_initialize(promote_lib: bool) -> Initialized:
        """Initialize native generation state after argument parsing."""
        return {"state": native.initialize(promote_lib)}

    @mcp.tool()
    def mathformer_extra_lean_write_case(state: State, repository_root: str) -> Written:
        """Render and write the current source-owned case, optionally copying it."""
        before_write()
        return {
            "paths": native.write_current_case(state, Path(repository_root).resolve())
        }

    @mcp.tool()
    def mathformer_extra_lean_advance(state: State, paths: list[str]) -> Advanced:
        """Accumulate paths and advance the native fixed iterator."""
        updated, done = native.advance(state, paths)
        return {"state": updated, "done": done}

    @mcp.tool()
    def mathformer_extra_lean_finish(state: State) -> Finished:
        """Print native paths on the MCP diagnostic stream and return results."""
        with redirect_stdout(sys.stderr):
            return native.finish(state)
