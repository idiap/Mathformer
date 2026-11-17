# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP ports for the reporter's shared, ordered native stages.

The traversal phase lowers nested loops into one bounded PRISM loop without
moving evaluation, selection, or output work across source boundaries.
"""

from contextlib import redirect_stdout
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any
from typing_extensions import TypedDict

SOURCE = (
    Path(__file__).resolve().parents[1]
    / "skills/physics-common/formalphysics-comparative-analysis-reporter/scripts/build_comparative_report.py"
)


def source():
    name = "mathformer_comparative_report_native"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, SOURCE)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


class Args(TypedDict):
    self_test: bool
    has_input_json: bool
    options: dict[str, Any]


class State(TypedDict):
    has_cases: bool
    native_json: str
    phase: str


class Parsed(TypedDict):
    args: Args


class Stateful(TypedDict):
    state: State


class Assembled(TypedDict):
    report: dict[str, Any]
    report_text: str


class Completion(TypedDict):
    exit_code: int
    payload: dict[str, Any]


class Completed(TypedDict):
    result: Completion


def register_comparative_report_tools(mcp, before_write):
    native = source()

    def envelope(state):
        # PRISM canonicalizes object keys. Carry the native insertion order too,
        # because report renderers expose ordered JSON blocks and review tables.
        return {
            "state": {
                "has_cases": state["has_cases"],
                "phase": state["data"]["phase"],
                "native_json": json.dumps(state, ensure_ascii=False),
            }
        }

    def unpack(state):
        value = json.loads(state["native_json"])
        if (
            value["has_cases"] != state["has_cases"]
            or value["data"]["phase"] != state["phase"]
        ):
            raise ValueError("inconsistent native traversal envelope")
        return value

    def guard(state, phase):
        value = unpack(state)
        if not value["has_cases"] or value["data"]["phase"] != phase:
            raise ValueError("out-of-order comparative report stage: " + phase)
        return value

    @mcp.tool()
    def mathformer_comparative_report_parse(argv: list[str]) -> Parsed:
        try:
            with redirect_stdout(sys.stderr):
                args = native.parse_args(argv)
        except SystemExit as error:
            raise ValueError(f"argument parser exited: {error.code}") from error
        return {
            "args": {
                "self_test": args.self_test,
                "has_input_json": args.input_json is not None,
                "options": native.report_options(args),
            }
        }

    @mcp.tool()
    def mathformer_comparative_report_empty(args: Args) -> Stateful:
        if not args["self_test"]:
            raise ValueError("empty context is only for the self-test branch")
        return envelope({"has_cases": False, "data": {"phase": "open"}})

    @mcp.tool()
    def mathformer_comparative_report_prepare(args: Args) -> Stateful:
        before_write()
        options = native.report_arguments(args["options"])
        if options.self_test or options.input_json is None:
            raise ValueError("--input-json is required unless --self-test is used")
        return envelope(native.prepare_report(options, max_records=1000))

    @mcp.tool()
    def mathformer_comparative_report_open_case(state: State) -> Stateful:
        return envelope(native.open_report_case(guard(state, "open")))

    @mcp.tool()
    def mathformer_comparative_report_candidate(state: State) -> Stateful:
        before_write()  # Optional Lean compilation owns native temporary files.
        return envelope(native.evaluate_report_candidate(guard(state, "candidate")))

    @mcp.tool()
    def mathformer_comparative_report_close_case(state: State) -> Stateful:
        return envelope(native.close_report_case(guard(state, "close")))

    @mcp.tool()
    def mathformer_comparative_report_retain(state: State) -> Stateful:
        if state["has_cases"]:
            raise ValueError("retain is only for an empty traversal")
        return {"state": state}

    @mcp.tool()
    def mathformer_comparative_report_assemble(state: State) -> Assembled:
        if state["has_cases"]:
            raise ValueError("traversal must finish before assembly")
        report = native.assemble_report(unpack(state))
        return {"report": report, "report_text": json.dumps(report, ensure_ascii=False)}

    @mcp.tool()
    def mathformer_comparative_report_write(args: Args, report_text: str) -> Completed:
        before_write()
        with redirect_stdout(sys.stderr):
            return {
                "result": native.complete_report(
                    native.report_arguments(args["options"]), json.loads(report_text)
                )
            }

    @mcp.tool()
    def mathformer_comparative_report_test(args: Args) -> Completed:
        before_write()
        if not args["self_test"]:
            raise ValueError("self-test requires --self-test")
        with redirect_stdout(sys.stderr):
            return {
                "result": native.complete_self_test(
                    native.report_arguments(args["options"])
                )
            }
