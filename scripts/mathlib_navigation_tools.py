# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable bindings for native Mathlib navigation; no provider or prover adapter."""

from contextlib import redirect_stdout
from functools import lru_cache
import importlib.util
import io
from pathlib import Path
import sys
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "skills/mathlib/mathlib-navigation-state-planner/scripts/plan_mathlib_navigation_state.py"


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "mathlib_navigation_native", ROOT / SOURCE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Payload(TypedDict):
    payload: dict


class Text(TypedDict):
    text: str


class Emitted(TypedDict):
    exit_code: int
    stdout: str


def register_mathlib_navigation_tools(mcp, write_policy=lambda: None):
    @mcp.tool()
    def mathformer_navigation_require_text(text: str) -> Text:
        try:
            return {"text": source().require_text(text)}
        except SystemExit as error:
            raise ValueError(str(error)) from error

    @mcp.tool()
    def mathformer_navigation_plan(text: str, index: str, context: dict) -> Payload:
        write_policy()
        return {
            "payload": source().plan_navigation(
                text, index_path=Path(index), context=context
            )
        }

    @mcp.tool()
    def mathformer_navigation_monotonic(context: dict) -> Payload:
        write_policy()
        return {"payload": source().monotonic_check(context=context)}

    @mcp.tool()
    def mathformer_navigation_finish_self_test(
        normal: dict, gap: dict, monotonic: dict, context: dict
    ) -> Payload:
        write_policy()
        return {
            "payload": source().finish_self_test(
                normal, gap, monotonic, context=context
            )
        }

    @mcp.tool()
    def mathformer_navigation_emit(payload: dict, json: bool) -> Emitted:
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = source().emit(payload, json)
        print(stream.getvalue(), end="", file=sys.stderr)
        return {"exit_code": code, "stdout": stream.getvalue()}
