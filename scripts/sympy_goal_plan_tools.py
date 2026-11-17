# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable MCP ports for the native single-pass SymPy goal planner.

Module objects stay in this server process: no source serialization, reimport,
validator replay or repair loop is introduced at the transport boundary.
"""

from contextlib import redirect_stdout
from functools import lru_cache
import importlib.util
import io
import json
from pathlib import Path
import sys
from uuid import uuid4
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "skills/physics-sympy/physics-sympy-goal-sample-autoformalizer/scripts/plan_goal_sample_sympy_autoformalization.py"


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "sympy_goal_plan_native", ROOT / SOURCE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Context(TypedDict):
    working_directory: str


class StateResult(TypedDict):
    state: dict


class Initialized(TypedDict):
    state: dict
    exists: bool


class Imported(TypedDict):
    state: dict
    imported: bool


class Classified(TypedDict):
    decision: dict


class Assembled(TypedDict):
    plan: dict
    plan_json: str
    stdout_text: str


class Emitted(TypedDict):
    exit_code: int
    stdout_text: str
    json_text: str


def packed(state):
    # PRISM sorts JSON object keys; retain source insertion order for emission.
    return {**state, "_native_json": json.dumps(state, ensure_ascii=False)}


def restored(state):
    ordered = json.loads(state["_native_json"])
    if ordered != {k: v for k, v in state.items() if k != "_native_json"}:
        raise ValueError("Native state transport differs from typed state")
    return ordered


def register_sympy_goal_plan_tools(mcp, before_write):
    modules = {}

    def advance(state, function, *, needs_module=False, release=False):
        state = restored(state)
        token = state.get("module_ref")
        if needs_module:
            if token not in modules:
                raise ValueError(
                    "Imported module reference expired or belongs to another server"
                )
            state["module"] = modules[token]
        stream = io.StringIO()
        try:
            with redirect_stdout(stream):
                result = function(state)
            if "module" in state:
                module = state.pop("module")
                if module is not None and token is None:
                    token = uuid4().hex
                    state["module_ref"] = token
                    modules[token] = module
            if release and token:
                modules.pop(token, None)
                state.pop("module_ref", None)
        except BaseException:
            if token:
                modules.pop(token, None)
            raise
        finally:
            print(stream.getvalue(), end="", file=sys.stderr)
        state["stdout_text"] = state.get("stdout_text", "") + stream.getvalue()
        return packed(state), result

    @mcp.tool()
    def mathformer_sympy_goal_plan_initialize(request: dict) -> Initialized:
        """Resolve the native selected case and path; no default path repair."""
        if request["case"] not in {"formalphysics_0000", "formalphysics_0004"}:
            raise ValueError(
                "This interface supports formalphysics_0000 and formalphysics_0004"
            )
        path = (
            Path(request["sympy_file"]) if request["sympy_file"] is not None else None
        )
        native = source()
        case_id = native.normalize_case(request["case"], path)
        state = native.initialize_plan(
            case_id, native.case_path(case_id, path), run_gates=request["run_gates"]
        )
        state["stdout_text"] = ""
        return {"state": packed(state), "exists": state["exists"]}

    @mcp.tool()
    def mathformer_sympy_goal_plan_scan_import(state: dict) -> Imported:
        state, imported = advance(state, source().scan_import_plan)
        return {"state": state, "imported": imported}

    @mcp.tool()
    def mathformer_sympy_goal_plan_inspect(state: dict) -> StateResult:
        state, _ = advance(
            state,
            source().inspect_plan,
            needs_module=True,
            release=not state["run_gates"],
        )
        return {"state": state}

    @mcp.tool()
    def mathformer_sympy_goal_plan_gates(state: dict) -> StateResult:
        state, _ = advance(state, source().gates_plan, needs_module=True, release=True)
        return {"state": state}

    @mcp.tool()
    def mathformer_sympy_goal_plan_add_finding(state: dict, kind: str) -> StateResult:
        state, _ = advance(state, lambda s: source().add_plan_finding(s, kind))
        return {"state": state}

    @mcp.tool()
    def mathformer_sympy_goal_plan_classify(state: dict) -> Classified:
        return {"decision": source().classify_plan(restored(state))}

    @mcp.tool()
    def mathformer_sympy_goal_plan_assemble(state: dict, decision: dict) -> Assembled:
        state = restored(state)
        plan = source().assemble_plan(state, decision)
        return {
            "plan": plan,
            "plan_json": json.dumps(plan, ensure_ascii=False),
            "stdout_text": state["stdout_text"],
        }

    @mcp.tool()
    def mathformer_sympy_goal_plan_emit(
        request: dict, context: Context, plan: dict, plan_json: str, prior_stdout: str
    ) -> Emitted:
        """Use native output and log implementation, respecting service writes."""
        ordered = json.loads(plan_json)
        if ordered != plan:
            raise ValueError("Native plan transport differs from typed plan")
        directory = Path(context["working_directory"])
        if not directory.is_absolute() or not directory.is_dir():
            raise ValueError("working_directory must be an existing absolute directory")

        def path_for(name):
            value = request[name]
            if value is None:
                return None
            path = Path(value)
            return path if path.is_absolute() else directory / path

        output, log = path_for("output"), path_for("reasoning_log")
        # Preserve output-before-log ordering, including failure propagation.
        if output is not None:
            before_write(output)
        native = source()
        stream = io.StringIO()

        # Log authorization is checked at the actual logging boundary, after output.
        def checked_log(*args):
            if log is not None and native.append_reasoning_log_entry is not None:
                before_write(log)
            return original_log(*args)

        original_log = native.append_goal_event
        # Pass a callback rather than swapping process globals across invocations.
        try:
            with redirect_stdout(stream):
                code = native.emit_plan(ordered, output, log, append_event=checked_log)
        finally:
            print(stream.getvalue(), end="", file=sys.stderr)
        return {
            "exit_code": code,
            "stdout_text": prior_stdout + stream.getvalue(),
            "json_text": json.dumps(
                native.json_safe(ordered), ensure_ascii=False, indent=2
            ),
        }
