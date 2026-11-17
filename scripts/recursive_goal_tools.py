# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP ports for the native one-pass goal runner; no alternate stage algorithm."""

from contextlib import redirect_stdout
from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
from typing_extensions import TypedDict, NotRequired

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "skills/physics-lean/physics-lean-goal-sample-autoformalizer/scripts/run_recursive_goal_case.py"


class Context(TypedDict):
    repository_root: str
    allow_mutating: bool


class PassState(TypedDict):
    original: dict
    case_id: str
    source_text: str
    source_text_path: str
    lean_file: str
    artifact_dir: str
    outputs: dict[str, str]
    stage_reports: dict[str, dict]
    repair_plan_paths: list[str]
    iteration: int
    max_iterations: int
    json_output: bool
    pending: list[str]
    python: str
    lean_compile_ok: NotRequired[bool]
    lean_log: NotRequired[str]
    execution_status: NotRequired[str | None]
    silent_success: NotRequired[bool]


class Packed(TypedDict):
    state: PassState


class Advanced(TypedDict):
    state: PassState
    done: bool


class Compiled(TypedDict):
    state: PassState
    silent_success: bool


class RunResult(TypedDict):
    returncode: int
    report_path: str
    source_record_path: str
    payload: dict


class Finished(TypedDict):
    result: RunResult


def source(repository_root=None):
    spec = importlib.util.spec_from_file_location(
        "recursive_goal_native", ROOT / SOURCE
    )
    native = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(native)
    if repository_root is not None:
        native.REPO_ROOT = Path(repository_root).resolve(strict=True)
        native.SKILLS = native.REPO_ROOT / "skills"
        native.LEAN_ROOT = native.REPO_ROOT / "MathformerPhysicsLib/Lean"
        native.DEFAULT_ARTIFACT_ROOT = (
            native.REPO_ROOT / "artifacts/physics_lean/recursive_goal_runs"
        )
    return native


def register_recursive_goal_tools(mcp, before_write):
    def runtime(context):
        if not context["allow_mutating"]:
            raise ValueError("goal runner requires allow_mutating=true")
        return source(context["repository_root"])

    def guard(native, path):
        before_write(path)
        # Match the hub action's declared writes; a service mount alone does
        # not authorize arbitrary output paths passed through argv/state.
        declared = native.DEFAULT_ARTIFACT_ROOT / "formalphysics_0009"
        if not Path(path).resolve().is_relative_to(declared.resolve()):
            raise ValueError("output outside native declared writes")

    def validate(native, state):
        directory = Path(state["artifact_dir"])
        guard(native, directory)
        if state["case_id"] != directory.name:
            raise ValueError("case differs from artifact directory")
        if Path(state["source_text_path"]) != directory / "source_text.txt":
            raise ValueError("source path differs from native artifact path")
        for key, path in state["outputs"].items():
            if Path(path) != directory / (key + ".json"):
                raise ValueError("stage output differs from native artifact path")
            guard(native, Path(path))
        if state["python"] != native.workflow_python():
            raise ValueError("workflow interpreter differs from native interpreter")
        repair_paths = state["repair_plan_paths"]
        expected_repairs = [
            directory / (entry[0] + ".json") for entry in native.REPAIR_STAGES
        ]
        if (
            len(repair_paths) > len(expected_repairs)
            or [Path(path) for path in repair_paths]
            != expected_repairs[: len(repair_paths)]
        ):
            raise ValueError("repair path differs from native traversal")
        return deepcopy(state)

    @mcp.tool()
    def mathformer_recursive_goal_prepare_source(
        argv: list[str], context: Context
    ) -> Packed:
        native = runtime(context)
        import mathformer as hub

        action = hub.build_registry()["physics-lean:goal-sample-recursive-0009"]
        errors = hub.preflight(
            action,
            hub.RunContext(allow_mutating=True),
            argv,
            repository_root=native.REPO_ROOT,
        )
        if errors:
            raise ValueError("; ".join(errors))
        try:
            with redirect_stdout(sys.stderr):
                state = native.prepare_source(
                    argv, before_write=lambda path: guard(native, path)
                )
        except SystemExit as error:
            raise ValueError(f"native runner stopped: {error}") from error
        return {"state": state}

    def invoke(name, state, context):
        native = runtime(context)
        updated = validate(native, state)
        with redirect_stdout(sys.stderr):
            return getattr(native, name)(updated)

    @mcp.tool()
    def mathformer_recursive_goal_visit_physics_stage(
        state: PassState, context: Context
    ) -> Advanced:
        updated = invoke("visit_physics_stage", state, context)
        return {"state": updated, "done": not updated["pending"]}

    @mcp.tool()
    def mathformer_recursive_goal_plan_critique_ground(
        state: PassState, context: Context
    ) -> Packed:
        return {"state": invoke("plan_critique_ground", state, context)}

    @mcp.tool()
    def mathformer_recursive_goal_visit_repair_plan(
        state: PassState, context: Context
    ) -> Advanced:
        updated = invoke("visit_repair_plan", state, context)
        return {"state": updated, "done": not updated["pending"]}

    @mcp.tool()
    def mathformer_recursive_goal_finish_plans(
        state: PassState, context: Context
    ) -> Packed:
        return {"state": invoke("finish_plans", state, context)}

    @mcp.tool()
    def mathformer_recursive_goal_compile_interpret(
        state: PassState, context: Context
    ) -> Compiled:
        updated = invoke("compile_interpret", state, context)
        return {"state": updated, "silent_success": updated["silent_success"]}

    @mcp.tool()
    def mathformer_recursive_goal_normalize_silent(
        state: PassState, context: Context
    ) -> Packed:
        if not state.get("silent_success"):
            raise ValueError("normalization requires silent compiler success")
        return {"state": invoke("normalize_silent", state, context)}

    @mcp.tool()
    def mathformer_recursive_goal_retain_state(
        state: PassState, context: Context
    ) -> Packed:
        """Carry non-silent compiler evidence unchanged into final reporting."""
        native = runtime(context)
        return {"state": validate(native, state)}

    @mcp.tool()
    def mathformer_recursive_goal_validate_report(
        state: PassState, context: Context
    ) -> Finished:
        return {"result": invoke("validate_report", state, context)}
