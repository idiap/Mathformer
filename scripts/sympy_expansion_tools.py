# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable ports for one native SymPy expansion-map invocation.

JSON text companions preserve native insertion order across the PRISM codec.
No repairs, rerun gates, retries or background sessions are introduced here.
"""

from contextlib import redirect_stdout
from functools import lru_cache
import importlib.util
import io
import json
from pathlib import Path
import sys
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "skills/physics-sympy/physics-sympy-repair-expansion-cartographer/scripts/map_physics_sympy_repair_expansion.py"


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "sympy_expansion_native", ROOT / SOURCE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Parsed(TypedDict):
    options: dict


class Planned(TypedDict):
    plan: dict
    plan_json: str


class Reviewed(TypedDict):
    reviews: list[dict]
    reviews_json: str


class Mapped(TypedDict):
    expansion: dict
    expansion_json: str


class Emitted(TypedDict):
    result: dict


def ordered(value, encoded):
    decoded = json.loads(encoded)
    if decoded != value:
        raise ValueError("native JSON companion differs from typed payload")
    return decoded


def native_path(value):
    """Retain the registered hub's cwd even when the MCP server starts elsewhere."""
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def parse_registered(extra_args, case_id):
    """Share native parsing while retaining each registered action's fixed argv."""
    try:
        with redirect_stdout(sys.stderr):
            args = source().parse_args(["--case", case_id, "--json", *extra_args])
    except SystemExit as error:
        raise ValueError(f"argparse exited {error.code}") from error
    return {
        "options": {
            "self_test": args.self_test,
            "goal_plan_supplied": bool(args.goal_plan),
            "case_available": bool(args.case),
            "json": args.json,
            "case": args.case,
            "goal_plan": str(args.goal_plan) if args.goal_plan else None,
            "review": [str(p) for p in args.review],
            "output": str(args.output) if args.output else None,
            "reasoning_log": str(args.reasoning_log) if args.reasoning_log else None,
        }
    }


def register_sympy_expansion_tools(mcp, before_write=lambda: None):
    @mcp.tool()
    def mathformer_sympy_expansion_parse_cli(extra_args: list[str]) -> Parsed:
        """Parse the registered action's fixed argv followed by extra args."""
        return parse_registered(extra_args, "formalphysics_0000")

    @mcp.tool()
    def mathformer_sympy_expansion_parse_cli_0004(extra_args: list[str]) -> Parsed:
        """Parse repair-expansion-map-0004's fixed argv before caller overrides."""
        return parse_registered(extra_args, "formalphysics_0004")

    @mcp.tool()
    def mathformer_sympy_expansion_missing_input() -> Planned:
        """Execute the native missing-input exit without terminating MCP."""
        try:
            source().missing_input_plan()
        except SystemExit as error:
            raise ValueError(str(error)) from error
        raise RuntimeError("native missing-input path unexpectedly returned")

    @mcp.tool()
    def mathformer_sympy_expansion_load_plan(options: dict) -> Planned:
        plan = source().load_json(native_path(options["goal_plan"]))
        return {"plan": plan, "plan_json": json.dumps(plan, ensure_ascii=False)}

    @mcp.tool()
    def mathformer_sympy_expansion_plan_case(options: dict) -> Planned:
        if not options["case"]:
            raise ValueError("provide --goal-plan or --case")
        plan = source().run_goal_planner(options["case"])
        return {"plan": plan, "plan_json": json.dumps(plan, ensure_ascii=False)}

    @mcp.tool()
    def mathformer_sympy_expansion_load_reviews(options: dict) -> Reviewed:
        reviews = source().load_many([native_path(p) for p in options["review"]])
        return {
            "reviews": reviews,
            "reviews_json": json.dumps(reviews, ensure_ascii=False),
        }

    @mcp.tool()
    def mathformer_sympy_expansion_build_map(
        plan: dict, plan_json: str, reviews: list[dict], reviews_json: str
    ) -> Mapped:
        expansion = source().build_map(
            ordered(plan, plan_json), ordered(reviews, reviews_json)
        )
        return {
            "expansion": expansion,
            "expansion_json": json.dumps(expansion, ensure_ascii=False),
        }

    @mcp.tool()
    def mathformer_sympy_expansion_self_test() -> Mapped:
        expansion = source().self_test_map()
        return {
            "expansion": expansion,
            "expansion_json": json.dumps(expansion, ensure_ascii=False),
        }

    @mcp.tool()
    def mathformer_sympy_expansion_emit(
        options: dict, expansion: dict, expansion_json: str
    ) -> Emitted:
        native_expansion = ordered(expansion, expansion_json)
        if options["output"] or options["reasoning_log"]:
            before_write()
        stream = io.StringIO()
        try:
            with redirect_stdout(stream):
                result = source().emit_map(
                    native_expansion,
                    native_path(options["output"]) if options["output"] else None,
                    (
                        native_path(options["reasoning_log"])
                        if options["reasoning_log"]
                        else None
                    ),
                )
        finally:
            print(stream.getvalue(), end="", file=sys.stderr)
        return {"result": result}
