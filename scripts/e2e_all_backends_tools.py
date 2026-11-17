# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP interfaces for the source-owned all-backends wrapper steps."""

from contextlib import redirect_stdout
from functools import lru_cache
import importlib.util
from pathlib import Path
import sys
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "_e2e_all_backends_native", ROOT / "tests/e2e/run_all_backends.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Context(TypedDict):
    allow_mutating: bool


class Prepared(TypedDict):
    plan: dict


class Executed(TypedDict):
    child: dict


class Finished(TypedDict):
    report: dict
    exit_code: int


def register_e2e_all_backends_tools(mcp, readonly=lambda: False):
    def authorize(context):
        if readonly() or context != {"allow_mutating": True}:
            raise PermissionError(
                "all-backends execution requires allow_mutating and a writable service"
            )

    def validate(plan):
        if plan != source().prepare_command(plan["json_output"]):
            raise ValueError("plan must equal the native fixed all-backends command")

    @mcp.tool()
    def mathformer_e2e_all_backends_prepare(json_output: bool) -> Prepared:
        return {"plan": source().prepare_command(json_output)}

    @mcp.tool()
    def mathformer_e2e_all_backends_execute(plan: dict, context: Context) -> Executed:
        authorize(context)
        validate(plan)
        return {"child": source().run_suite(plan)}

    @mcp.tool()
    def mathformer_e2e_all_backends_finalize(
        plan: dict, child: dict, context: Context
    ) -> Finished:
        authorize(context)
        validate(plan)
        # Preserve native printed observability without corrupting MCP stdio.
        with redirect_stdout(sys.stderr):
            return source().write_wrapper_and_return(plan, child)
