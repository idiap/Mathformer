# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Typed MCP bindings to the shared extra-Lean report refresh stages."""

from contextlib import redirect_stdout
from pathlib import Path
import sys
from typing_extensions import TypedDict
import refresh_formalphysics_extra_lean_reports as native


class Case(TypedDict):
    case_id: str
    rank: str
    features: list[str]


class Files(TypedDict):
    case_id: str
    source: str
    lean: str
    directory: str


class Selected(TypedDict):
    case: Case


class Located(TypedDict):
    files: Files


class Advanced(TypedDict):
    cursor: int
    done: bool


def register_refresh_tools(mcp, before_write):
    def root(path):
        return Path(path).resolve(strict=True)

    def validate_case(case):
        if case != {"case_id": case["case_id"], **native.CASES[case["case_id"]]}:
            raise ValueError("case must match the fixed native specification")

    def validate_files(files, repository_root):
        case_id = files["case_id"]
        spec = native.CASES[case_id]
        expected = dict(
            case_id=case_id,
            source=str(
                repository_root
                / native.SOURCE_ROOT.relative_to(native.REPO_ROOT)
                / f"{spec['rank']}_{case_id}.tex"
            ),
            lean=str(
                repository_root
                / native.LIB_ROOT.relative_to(native.REPO_ROOT)
                / case_id
                / "MathformerPhysics.lean"
            ),
            directory=str(
                repository_root
                / native.ARTIFACT_ROOT.relative_to(native.REPO_ROOT)
                / case_id
            ),
        )
        if files != expected:
            raise ValueError("files must identify the native case paths")

    @mcp.tool()
    def mathformer_refresh_select_case(cursor: int) -> Selected:
        return {"case": native.select_case(cursor)}

    @mcp.tool()
    def mathformer_refresh_prepare_compile(case: Case, repository_root: str) -> Located:
        before_write()
        validate_case(case)
        return {"files": native.prepare_compile(case, root(repository_root))}

    @mcp.tool()
    def mathformer_refresh_packets(
        case: Case, files: Files, repository_root: str
    ) -> Located:
        before_write()
        validate_case(case)
        directory = root(repository_root)
        validate_files(files, directory)
        if case["case_id"] != files["case_id"]:
            raise ValueError("packet case differs from compiled case")
        return {"files": native.packets(case, files, directory)}

    @mcp.tool()
    def mathformer_refresh_critics(files: Files, repository_root: str) -> Located:
        before_write()
        directory = root(repository_root)
        validate_files(files, directory)
        return {"files": native.critics(files, directory)}

    @mcp.tool()
    def mathformer_refresh_reviews(files: Files, repository_root: str) -> Located:
        before_write()
        directory = root(repository_root)
        validate_files(files, directory)
        return {"files": native.reviews(files, directory)}

    @mcp.tool()
    def mathformer_refresh_aggregate_copy(
        files: Files, repository_root: str
    ) -> Located:
        before_write()
        directory = root(repository_root)
        validate_files(files, directory)
        return {"files": native.aggregate_copy(files, directory)}

    @mcp.tool()
    def mathformer_refresh_advance(cursor: int, completed: Files) -> Advanced:
        # The diagnostic stream preserves native observability without corrupting MCP frames.
        with redirect_stdout(sys.stderr):
            return native.advance(cursor, completed)
