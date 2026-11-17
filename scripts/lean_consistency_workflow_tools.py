# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP ports for the shared, single-pass Lean consistency coordinator.

Contexts own native state. Transported state is an assertion, never a command
or a replacement for server-owned arguments. Native exceptions consume context.
"""

from copy import deepcopy
from functools import lru_cache
import importlib.util
from pathlib import Path
from threading import RLock
from uuid import uuid4
from typing_extensions import TypedDict


@lru_cache(maxsize=1)
def source_report():
    path = (
        Path(__file__).resolve().parents[1]
        / "skills/lean/lean-consistency-report-orchestrator/scripts/run_lean_consistency_report.py"
    )
    spec = importlib.util.spec_from_file_location("lean_consistency_native", path)
    native = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(native)
    return native


ARGUMENTS = {
    "lean_file",
    "run_lean_check",
    "informalization_report",
    "output_file",
    "reasoning_log_file",
    "target_mathlib_compatibility",
    "target_reference_free_score",
    "skip_mathlib_grounding",
    "skip_reference_free_monitor",
}
PATH_ARGUMENTS = {"informalization_report", "output_file", "reasoning_log_file"}


def native_arguments(native, values):
    if set(values) - ARGUMENTS:
        raise ValueError("unknown consistency report arguments")
    args = native.parse_args([])
    for key, value in values.items():
        setattr(
            args,
            key,
            Path(value) if key in PATH_ARGUMENTS and value is not None else value,
        )
    return args


def transport(state):
    return dict(
        args={
            k: str(v) if isinstance(v, Path) else deepcopy(v)
            for k, v in vars(state["args"]).items()
            if k in ARGUMENTS
        },
        paths=[str(p) for p in state["paths"]],
        layers=deepcopy(state["layers"]),
        informalization_report=str(state["informalization_report"]),
        output_file=str(state["output_file"]),
    )


class Initialized(TypedDict):
    state: dict
    context: dict
    has_files: bool
    grounding_enabled: bool
    monitor_enabled: bool


class Updated(TypedDict):
    state: dict


class Aggregated(TypedDict):
    report: dict
    report_path: str
    informalization_report_path: str


def register_lean_consistency_tools(
    mcp, authorize=lambda: None, path_allowed=lambda p: True
):
    scopes = {}
    lock = RLock()
    stages = ["compile", "files", "core", "grounding", "monitor", "aggregate"]
    functions = dict(
        compile="compile_report",
        files="check_report_files",
        core="check_report_core",
        grounding="ground_report",
        monitor="monitor_report",
        aggregate="aggregate_report",
    )

    def check_paths(native, args):
        writes = [
            native.ARTIFACT_DIR,
            args.output_file or native.ARTIFACT_DIR / "latest.json",
            args.informalization_report
            or native.ARTIFACT_DIR / "informalization.latest.json",
        ]
        if args.reasoning_log_file:
            writes.append(args.reasoning_log_file)
        # Both grounding and monitoring invoke the native monitor, which owns
        # latest.json and evolution artifacts even with --no-reasoning-log.
        if args.lean_file and (
            not args.skip_mathlib_grounding or not args.skip_reference_free_monitor
        ):
            writes.append(native.REPO_ROOT / "artifacts/reference_free_critic_monitor")
        if any(not path_allowed(Path(p).resolve()) for p in writes):
            raise PermissionError("consistency artifacts outside service write roots")

    @mcp.tool()
    def mathformer_lean_consistency_initialize(args: dict) -> Initialized:
        """Resolve native CLI defaults and create a single-pass report context."""
        with lock:
            authorize()
            native = source_report()
            resolved = native_arguments(native, args)
            check_paths(native, resolved)
            state = native.initialize_report(resolved)
            handle = uuid4().hex
            scopes[handle] = dict(state=state, phase=0)
            return dict(
                state=transport(state),
                context={"handle": handle},
                has_files=bool(state["paths"]),
                grounding_enabled=bool(state["paths"])
                and not resolved.skip_mathlib_grounding,
                monitor_enabled=bool(state["paths"])
                and not resolved.skip_reference_free_monitor,
            )

    def step(stage, state, context, carry=False):
        with lock:
            authorize()
            native = source_report()
            handle = context.get("handle")
            scope = scopes.get(handle)
            if scope is None or context != {"handle": handle}:
                raise ValueError("unknown or consumed consistency context")
            expected = stages[scope["phase"]]
            if state != transport(scope["state"]):
                raise ValueError("modified or replayed consistency state")
            args = scope["state"]["args"]
            enabled = dict(
                files=bool(scope["state"]["paths"]),
                grounding=bool(scope["state"]["paths"])
                and not args.skip_mathlib_grounding,
                monitor=bool(scope["state"]["paths"])
                and not args.skip_reference_free_monitor,
            )
            if (carry and enabled.get(expected, True)) or (
                not carry and (stage != expected or not enabled.get(stage, True))
            ):
                raise ValueError("out-of-order consistency stage or invalid skip")
            check_paths(native, args)
            try:
                if not carry:
                    result = getattr(native, functions[stage])(scope["state"])
                if expected == "aggregate":
                    scopes.pop(handle)
                    return dict(
                        report=result,
                        report_path=result["output_files"]["report"],
                        informalization_report_path=result["output_files"][
                            "informalization_report"
                        ],
                    )
                scope["phase"] += 1
                return {"state": transport(scope["state"])}
            except BaseException:
                scopes.pop(handle, None)
                raise

    @mcp.tool()
    def mathformer_lean_consistency_compile(state: dict, context: dict) -> Updated:
        """Compile every declared file, or append the native skipped layer."""
        return step("compile", state, context)

    @mcp.tool()
    def mathformer_lean_consistency_file_checks(state: dict, context: dict) -> Updated:
        """Check semantic comments, then artifact realness."""
        return step("files", state, context)

    @mcp.tool()
    def mathformer_lean_consistency_core_checks(state: dict, context: dict) -> Updated:
        """Run all six ordered core checks, accumulating ordinary failures."""
        return step("core", state, context)

    @mcp.tool()
    def mathformer_lean_consistency_grounding(state: dict, context: dict) -> Updated:
        """Measure native mathlib grounding and produce repair todos."""
        return step("grounding", state, context)

    @mcp.tool()
    def mathformer_lean_consistency_monitor(state: dict, context: dict) -> Updated:
        """Run the native reference-free monitor and its artifact writes."""
        return step("monitor", state, context)

    @mcp.tool()
    def mathformer_lean_consistency_carry_state(state: dict, context: dict) -> Updated:
        """Preserve state across one source-disabled conditional stage."""
        return step(None, state, context, carry=True)

    @mcp.tool()
    def mathformer_lean_consistency_aggregate(state: dict, context: dict) -> Aggregated:
        """Write the native unified report, retaining failed required layers."""
        return step("aggregate", state, context)
