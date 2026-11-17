# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP ports for the native finite grounded-sample audit traversal.

The repository context relocates input/report data, never the executable checker.
All audit algorithms and report formatting are shared with the source CLI.
"""

import argparse
from contextlib import redirect_stdout
from functools import lru_cache
import importlib.util
from pathlib import Path
import sys
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "tests/physics_lean/run_grounded_sample_thoroughness.py"


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "grounded_sample_native", ROOT / SOURCE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Initialized(TypedDict):
    state: dict


class Audited(TypedDict):
    result: dict


class Advanced(TypedDict):
    state: dict
    done: bool


class Finalized(TypedDict):
    report: dict
    exit_code: int


class SuiteFinalized(TypedDict):
    report: dict


def register_grounded_sample_tools(mcp, write_policy, path_allowed):
    def authorize(path):
        write_policy()
        if not path_allowed(path):
            raise ValueError("Grounded sample report is outside service write roots")

    @mcp.tool()
    def mathformer_grounded_sample_initialize_suite(
        case_ids: list[str] | None, repository_root: str
    ) -> Initialized:
        """Resolve the contract's finite selection using the native suite."""
        if case_ids is not None and len(case_ids) > 15:
            raise ValueError("Normalized workflow admits at most 15 case arguments")
        try:
            state = source().initialize_suite(case_ids, Path(repository_root).resolve())
        except SystemExit as error:
            raise ValueError(str(error)) from error
        return {"state": state}

    @mcp.tool()
    def mathformer_grounded_sample_finalize_suite(
        state: dict, repository_root: str
    ) -> SuiteFinalized:
        """Write and return run_suite's report, including a failed audit report."""
        native = source()
        root = Path(repository_root).resolve()
        authorize(native.report_path(root))
        return {"report": native.finalize_suite(state, root)}

    @mcp.tool()
    def mathformer_grounded_sample_select_initialize(
        request: dict, repository_root: str
    ) -> Initialized:
        if len(request["case_ids"]) > 15:
            raise ValueError("Normalized workflow admits at most 15 case arguments")
        try:
            state = source().initialize_suite(
                request["case_ids"], Path(repository_root).resolve()
            )
        except SystemExit as error:
            raise ValueError(str(error)) from error
        return {"state": state}

    @mcp.tool()
    def mathformer_grounded_sample_audit_next(
        state: dict, repository_root: str
    ) -> Audited:
        return {"result": source().audit_next(state, Path(repository_root).resolve())}

    @mcp.tool()
    def mathformer_grounded_sample_append_guard(state: dict, result: dict) -> Advanced:
        return source().append_guard(state, result)

    @mcp.tool()
    def mathformer_grounded_sample_finalize(
        state: dict, request: dict, repository_root: str
    ) -> Finalized:
        native = source()
        root = Path(repository_root).resolve()
        authorize(native.report_path(root))
        report = native.finalize_suite(state, root)
        # Native ordering writes the fixed report before the optional output.
        output = Path(request["output"]) if request["output"] else None
        if output:
            authorize(output)
        args = argparse.Namespace(output=output, json=request["json"])
        # MCP stdout carries protocol frames; preserve native output on stderr.
        with redirect_stdout(sys.stderr):
            code = native.emit_report(args, report, root)
        return {"report": report, "exit_code": code}
