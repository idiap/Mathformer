# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Registered MCP bindings for the shared native SymPy controller stages."""

from contextlib import redirect_stdout
from functools import lru_cache
import importlib.util
import io
import json
from pathlib import Path
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "skills/physics-sympy/physics-sympy-recursive-repair-loop-controller/scripts/control_physics_sympy_recursive_repair.py"


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "sympy_recursive_control_native", ROOT / SOURCE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Context(TypedDict):
    working_directory: str


class Loaded(TypedDict):
    state: dict
    state_json: str


class Guarded(TypedDict):
    guards: dict


class Finished(TypedDict):
    plan: dict
    stdout_text: str
    exit_code: int


def restored(state, state_json):
    """Keep native nested JSON order through PRISM's canonical object codec."""
    ordered = json.loads(state_json)
    if ordered != state:
        raise ValueError("Serialized state differs from its typed payload")
    return ordered


def register_sympy_recursive_repair_control_tools(mcp, write_policy):
    @mcp.tool()
    def mathformer_sympy_recursive_repair_load_state(
        request: dict, context: Context
    ) -> Loaded:
        """Load map then history, with paths resolved against the caller directory."""
        directory = Path(context["working_directory"])
        if not directory.is_absolute() or not directory.is_dir():
            raise ValueError("working_directory must be an existing absolute directory")
        # This workflow projects the hub's registered --case default. Explicit
        # case=None still preserves native missing-input behavior.
        state = source().load_state(
            {"case": "formalphysics_0000", **request}, directory
        )
        return {"state": state, "state_json": json.dumps(state, ensure_ascii=False)}

    @mcp.tool()
    def mathformer_sympy_recursive_repair_compute_guards(
        state: dict, state_json: str
    ) -> Guarded:
        """Evaluate native predicates without changing caller history or iteration."""
        return {"guards": source().compute_guards(restored(state, state_json))}

    @mcp.tool()
    def mathformer_sympy_recursive_repair_finish_plan(
        state: dict, state_json: str, branch: str
    ) -> Finished:
        """Finish the selected plan and perform the requested native emissions."""
        state = restored(state, state_json)
        plan = source().finish_plan(state, branch)
        request = state["request"]
        output = Path(request["output"]) if request.get("output") else None
        log = Path(request["reasoning_log"]) if request.get("reasoning_log") else None
        for path in (log, output):
            if path is not None:
                write_policy(path)
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = source().emit_plan(plan, output, log)
        return {"plan": plan, "exit_code": code, "stdout_text": stdout.getvalue()}
