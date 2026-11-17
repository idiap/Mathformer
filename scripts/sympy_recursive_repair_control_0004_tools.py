# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Four native controller stages for the FormalPhysics 0004 workflow.

JSON sidecars preserve native insertion order across PRISM's object codec;
the typed payload and sidecar must agree. No scientific work is substituted.
"""

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
from typing_extensions import TypedDict

from sympy_recursive_repair_control_tools import (
    Context,
    Loaded,
    Guarded,
    restored,
    source,
)


class Planned(TypedDict):
    plan: dict
    plan_json: str


class Emitted(TypedDict):
    exit_code: int
    stdout_text: str


def caller_directory(context: Context) -> Path:
    directory = Path(context["working_directory"])
    if not directory.is_absolute() or not directory.is_dir():
        raise ValueError("working_directory must be an existing absolute directory")
    return directory


def register_sympy_recursive_repair_control_0004_tools(mcp, write_policy):
    @mcp.tool()
    def mathformer_sympy_recursive_repair_0004_load_state(
        request: dict, context: Context
    ) -> Loaded:
        """Load current map before history, using the hub's 0004 case default."""
        state = source().load_state(
            {"case": "formalphysics_0004", **request}, caller_directory(context)
        )
        return {"state": state, "state_json": json.dumps(state, ensure_ascii=False)}

    @mcp.tool()
    def mathformer_sympy_recursive_repair_0004_compute_guards(
        state: dict, state_json: str
    ) -> Guarded:
        """Evaluate native stopping predicates without changing caller state."""
        return {"guards": source().compute_guards(restored(state, state_json))}

    @mcp.tool()
    def mathformer_sympy_recursive_repair_0004_finish_plan(
        state: dict, state_json: str, branch: str
    ) -> Planned:
        """Apply the selected native branch and blocked-map override."""
        plan = source().finish_plan(restored(state, state_json), branch)
        return {"plan": plan, "plan_json": json.dumps(plan, ensure_ascii=False)}

    @mcp.tool()
    def mathformer_sympy_recursive_repair_0004_emit_plan(
        plan: dict,
        plan_json: str,
        output_path: str | None,
        reasoning_log: str | None,
        context: Context,
    ) -> Emitted:
        """Emit the native log, then file or captured stdout, under service policy."""
        plan = restored(plan, plan_json)
        directory = caller_directory(context)

        def path(value):
            if value is None:
                return None
            candidate = Path(value)
            return candidate if candidate.is_absolute() else directory / candidate

        output, log = path(output_path), path(reasoning_log)
        for destination in (log, output):
            if destination is not None:
                write_policy(destination)
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = source().emit_plan(plan, output, log)
        return {"exit_code": code, "stdout_text": stdout.getvalue()}
