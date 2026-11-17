# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP ports for main's ordered ten-case SymPy traversal.

The scientific implementation remains write_case, including its five sequential
validators and immediate exception propagation. CLI streams are captured as
outputs because MCP reserves stdout for its transport.
"""

from contextlib import redirect_stdout
import io
from typing_extensions import TypedDict
import mathformer as hub
import generate_formalphysics_original_two_sympy as native


class Context(TypedDict):
    dry_run: bool
    json_output: bool
    keep_going: bool
    allow_mutating: bool
    write_report: bool


class Options(TypedDict):
    promote_lib: bool
    json: bool


class State(TypedDict):
    cursor: int
    summaries: list[dict]
    summaries_json: list[str]


class Case(TypedDict):
    id: str
    spec: dict[str, str]


class Initialized(TypedDict):
    state: State


class Selected(TypedDict):
    case: Case


class Written(TypedDict):
    summary: dict
    summary_json: str


class Advanced(TypedDict):
    state: State
    done: bool


class Aggregated(TypedDict):
    result: dict
    result_json: str
    exit_code: int


class Emitted(TypedDict):
    stdout: str


def register_original_two_sympy_tools(mcp, before_write):
    @mcp.tool()
    def mathformer_original_two_sympy_initialize() -> Initialized:
        return {"state": native.initialize()}

    @mcp.tool()
    def mathformer_original_two_sympy_select_case(state: State) -> Selected:
        return {"case": native.select_case(state)}

    @mcp.tool()
    def mathformer_original_two_sympy_write_case(
        case: Case, options: Options, context: Context
    ) -> Written:
        before_write()
        runtime = hub.RunContext(**context)
        errors = hub.preflight(
            hub.build_registry()["formalphysics:original-two-sympy"], runtime, ()
        )
        if errors or runtime.dry_run:
            raise ValueError(f"case execution not authorized: {errors}")
        if case["spec"] != native.CASES[case["id"]]:
            raise ValueError("case must match the source catalog")
        with redirect_stdout(io.StringIO()) as stream:
            try:
                summary = native.write_case(
                    case["id"], case["spec"], options["promote_lib"]
                )
            finally:
                # Preserve any native diagnostics without corrupting MCP stdout.
                import sys

                print(stream.getvalue(), end="", file=sys.stderr)
        return {"summary": summary, "summary_json": native.json_safe(summary)}

    @mcp.tool()
    def mathformer_original_two_sympy_advance(
        state: State, summary: dict, summary_json: str
    ) -> Advanced:
        updated, done = native.advance(state, summary, summary_json)
        return {"state": updated, "done": done}

    @mcp.tool()
    def mathformer_original_two_sympy_aggregate(state: State) -> Aggregated:
        result, code = native.aggregate(state)
        return {
            "result": result,
            "result_json": native.json_safe(result),
            "exit_code": code,
        }

    @mcp.tool()
    def mathformer_original_two_sympy_emit_json(result_json: str) -> Emitted:
        with redirect_stdout(io.StringIO()):
            return {"stdout": native.emit_json(result_json)}

    @mcp.tool()
    def mathformer_original_two_sympy_emit_paths(result: dict) -> Emitted:
        with redirect_stdout(io.StringIO()):
            return {"stdout": native.emit_paths(result)}
