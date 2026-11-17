# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Typed MCP ports for the shared, single-pass source-only SymPy runner."""

from contextlib import redirect_stdout
from functools import lru_cache
import importlib.util
import json
from pathlib import Path
import sys
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "skills/physics-sympy/physics-sympy-goal-sample-autoformalizer/scripts/run_recursive_goal_case.py"


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "sympy_source_only_native", ROOT / SOURCE
    )
    native = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(native)
    return native


class Context(TypedDict):
    working_directory: str
    allow_mutating: bool


class Prepared(TypedDict):
    prepared: dict


class State(TypedDict):
    state: dict


class Advanced(TypedDict):
    state: dict
    done: bool


class Assessed(TypedDict):
    assessment: dict


class Result(TypedDict):
    result: dict


def packed(value):
    # PRISM canonicalizes object keys; source iteration and summary ordering
    # must survive transport, including findings and nested source records.
    return {**value, "_native_json": json.dumps(value, ensure_ascii=False)}


def restored(value):
    ordered = json.loads(value["_native_json"])
    if ordered != {k: v for k, v in value.items() if k != "_native_json"}:
        raise ValueError("Native transport differs from typed payload")
    return ordered


def register_sympy_source_only_tools(mcp, before_write):
    def runtime(context):
        if not context["allow_mutating"]:
            raise ValueError("source-only runner requires allow_mutating=true")
        directory = Path(context["working_directory"])
        if not directory.is_absolute() or not directory.is_dir():
            raise ValueError("working_directory must be an existing absolute directory")
        return source(), directory

    def guard(native, prepared):
        directory = Path(prepared["run_dir"])
        if not directory.is_absolute() or directory.name != prepared["case_id"]:
            raise ValueError("invalid native run directory")
        expected = native.stage_commands(
            prepared["case_id"], directory, directory / "reasoning.jsonl"
        )
        if prepared["stage_specs"] != expected or prepared["stage_order"] != list(
            expected
        ):
            raise ValueError("stage commands differ from native interface")
        if prepared["artifact_path"] != str(native.case_path(prepared["case_id"])):
            raise ValueError("artifact differs from native case")
        before_write(directory)
        # Check all fixed children too, so existing symlinks cannot evade the
        # service's allowed write roots.
        for name in (
            "initial_draft.json",
            "source_record.rebuilt.json",
            "reasoning.jsonl",
            "reasoning_log.jsonl",
            "current_evidence.json",
            "design_guard_review.json",
            "repair_expansion.json",
            "controller_decision.json",
            "thoroughness.json",
            "recursive_goal_run.json",
            "summary.md",
            "goal_plan.json",
            "repair_expansion_map.json",
            "recursive_repair_control.json",
            "grounded_sample_thoroughness.json",
        ):
            before_write(directory / name)

    @mcp.tool()
    def mathformer_sympy_source_only_prepare(
        request: dict, context: Context
    ) -> Prepared:
        """Resolve caller paths and use native generation/source preparation."""
        native, directory = runtime(context)

        def resolve(value):
            path = Path(value)
            return path if path.is_absolute() else directory / path

        case = request["case_id"]
        output = resolve(request["output_root"])
        before_write(output / case)
        # Preparation deletes logs and writes these files before constructing
        # the stage packet. Authorize each before invoking the shared source.
        for name in (
            "reasoning.jsonl",
            "reasoning_log.jsonl",
            "initial_draft.json",
            "source_record.rebuilt.json",
        ):
            before_write(output / case / name)
        if (
            request.get("regenerate_initial_artifact", False)
            or not native.case_path(case).exists()
        ):
            before_write(native.case_path(case))
        with redirect_stdout(sys.stderr):
            prepared = native.prepare_run(
                case,
                (
                    resolve(request["source_record"])
                    if request["source_record"] is not None
                    else None
                ),
                output,
                regenerate_initial_artifact=request.get(
                    "regenerate_initial_artifact", False
                ),
            )
        return {"prepared": packed(prepared)}

    @mcp.tool()
    def mathformer_sympy_source_only_pack_state(
        prepared: dict, context: Context
    ) -> State:
        native, _ = runtime(context)
        prepared = restored(prepared)
        guard(native, prepared)
        return {"state": packed(native.pack_run_state(prepared))}

    @mcp.tool()
    def mathformer_sympy_source_only_execute_stage(
        state: dict, context: Context
    ) -> Advanced:
        native, _ = runtime(context)
        state = restored(state)
        guard(native, state["prepared"])
        with redirect_stdout(sys.stderr):
            done = native.execute_run_stage(state)
        return {"state": packed(state), "done": done}

    @mcp.tool()
    def mathformer_sympy_source_only_assess(state: dict, context: Context) -> Assessed:
        native, _ = runtime(context)
        state = restored(state)
        guard(native, state["prepared"])
        return {"assessment": packed(native.assess_run(state))}

    @mcp.tool()
    def mathformer_sympy_source_only_emit(
        assessment: dict, status: str, context: Context
    ) -> Result:
        native, _ = runtime(context)
        assessment = restored(assessment)
        guard(native, assessment["state"]["prepared"])
        expected = (
            "complete_sympy_physics_derivation"
            if assessment["complete"]
            else "blocked" if assessment["blocked"] else "derivation_partial"
        )
        if status != expected:
            raise ValueError("status differs from native assessment")
        with redirect_stdout(sys.stderr):
            return {"result": native.emit_run(assessment, status)}
