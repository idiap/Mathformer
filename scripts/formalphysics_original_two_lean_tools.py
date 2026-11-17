# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable ports for the no-promotion original-two Lean generation workflow."""

from contextlib import redirect_stdout
from pathlib import Path
import sys
from typing_extensions import TypedDict
import generate_formalphysics_original_two_lean as native


class Initialized(TypedDict):
    promote_lib: bool
    generated: list[str]


class Selected(TypedDict):
    case: str


class Files(TypedDict):
    artifact: str
    library: None


class Written(TypedDict):
    written: Files


class Advanced(TypedDict):
    generated: list[str]
    done: bool


class Finished(TypedDict):
    exit_code: int


def register_original_two_lean_tools(mcp, before_write):
    @mcp.tool()
    def mathformer_original_two_lean_initialize(argv: list[str]) -> Initialized:
        if argv:
            raise ValueError("registered hub invocation requires empty argv")
        return native.initialize(argv)

    @mcp.tool()
    def mathformer_original_two_lean_select_case(generated: list[str]) -> Selected:
        return {"case": native.select_case(generated)}

    @mcp.tool()
    def mathformer_original_two_lean_write_case(
        case: str, promote_lib: bool, repository_root: str
    ) -> Written:
        before_write()
        if promote_lib:
            raise ValueError("library promotion is forbidden by this workflow")
        root = Path(repository_root).resolve(strict=True)
        artifact, library = native.write_case(
            case, native.CASES[case], promote_lib, root
        )
        return {"written": {"artifact": str(artifact), "library": library}}

    @mcp.tool()
    def mathformer_original_two_lean_append_and_test(
        generated: list[str], written: Files, repository_root: str
    ) -> Advanced:
        root = Path(repository_root).resolve(strict=True)
        if written["library"] is not None:
            raise ValueError("unexpected library output")
        result = native.append_paths(generated, Path(written["artifact"]), None, root)
        return {"generated": result, "done": len(result) == len(native.CASES)}

    @mcp.tool()
    def mathformer_original_two_lean_finish(generated: list[str]) -> Finished:
        # MCP stdout belongs to the wire protocol; native printing remains visible on stderr.
        with redirect_stdout(sys.stderr):
            return {"exit_code": native.finish(generated)}
