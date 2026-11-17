# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP ports sharing the deprecated source-only QM runner's implementation.

Each call owns a fresh module and repository context. Commands, packet contents,
child timeouts, reporting and scientific decisions remain source owned. Hub
admission/dry-run/auditing remain available through the original action.
"""

from contextlib import redirect_stdout
from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "skills/physics-lean/physics-lean-goal-sample-autoformalizer/scripts/run_new_qm_source_only_batch.py"


class Context(TypedDict):
    repository_root: str
    allow_mutating: bool


class BatchState(TypedDict):
    records: list[dict]
    position: int
    cases: list[dict]
    run_gates: bool
    json_output: bool


class CaseWork(TypedDict):
    result: dict
    paths: dict


class Loaded(TypedDict):
    state: BatchState


class Worked(TypedDict):
    work: CaseWork


class Advanced(TypedDict):
    state: BatchState
    done: bool


class Audited(TypedDict):
    audit: dict


class Finished(TypedDict):
    summary: dict
    report_path: str
    exit_code: int


def source(repository_root=None):
    spec = importlib.util.spec_from_file_location(
        "new_qm_source_only_native", ROOT / SOURCE
    )
    native = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(native)
    if repository_root is not None:
        root = Path(repository_root).resolve(strict=True)
        # Relocate all repository paths consistently, including source helpers.
        # Nothing is loaded from provider settings or client environment secrets.
        for name, value in list(vars(native).items()):
            if isinstance(value, Path) and value.is_relative_to(ROOT):
                setattr(native, name, root / value.relative_to(ROOT))
    return native


def validate_state(native, state, complete=False):
    count = state["position"]
    if count != len(state["cases"]) or not 0 <= count <= len(native.SELECTED_CASES):
        raise ValueError("case accumulator differs from fixed source position")
    if complete and count != len(native.SELECTED_CASES):
        raise ValueError("fixed case selection is incomplete")
    for index, result in zip(native.SELECTED_CASES, state["cases"]):
        if result["source_index"] != index or result["case_id"] != native.case_id(
            index
        ):
            raise ValueError("case accumulator order differs from source selection")


def validate_work(native, work):
    result = work["result"]
    index = result["source_index"]
    if index not in native.SELECTED_CASES or result["case_id"] != native.case_id(index):
        raise ValueError("unknown source case")
    cid = result["case_id"]
    lean = native.rel(native.LEAN_ROOT / cid / "MathformerPhysics.lean")
    directory = native.ARTIFACT_ROOT / cid
    record = native.rel(directory / "source_record.json")
    packets = {
        key: native.rel(directory / filename)
        for key, filename in {
            "monitor": "monitor_report.json",
            "objects": "object_packet.json",
            "workbench": "workbench_plan.json",
            "repair_loop": "repair_loop.json",
            "generative": "generative_repair.json",
            "skill_ledger": "skill_usage_ledger.json",
        }.items()
    }
    if (
        work["paths"] != {"lean": lean, "source": record, "packets": packets}
        or result["lean_path"] != lean
        or result["source_record"] != record
    ):
        raise ValueError("case paths differ from native destinations")


def register_new_qm_source_only_tools(mcp, before_write):
    def runtime(context):
        if not context["allow_mutating"]:
            raise ValueError("QM scaffold requires allow_mutating=true")
        native = source(context["repository_root"])
        before_write(native.ARTIFACT_ROOT)
        for filename in ("mathlib_grounding_audit.json", "batch_report.json"):
            before_write(native.ARTIFACT_ROOT / filename)
        before_write(
            native.REPO_ROOT / "artifacts/physics_lean/grounded_sample_thoroughness"
        )
        before_write(
            native.REPO_ROOT
            / "artifacts/physics_lean/grounded_sample_thoroughness/report.json"
        )
        for index in native.SELECTED_CASES:
            cid = native.case_id(index)
            before_write(native.LEAN_ROOT / cid)
            before_write(native.LEAN_ROOT / cid / "MathformerPhysics.lean")
            directory = native.ARTIFACT_ROOT / cid
            before_write(directory)
            for filename in (
                "source_record.json",
                "monitor_report.json",
                "object_packet.json",
                "workbench_plan.json",
                "repair_loop.json",
                "generative_repair.json",
                "skill_usage_ledger.json",
                "goal_plan_initial.json",
                "derivation_completeness.json",
                "repair_expansion_map.json",
                "recursive_control_plan.json",
                "goal_plan_final.json",
            ):
                before_write(directory / filename)
        return native

    @mcp.tool()
    def mathformer_new_qm_initialize(argv: list[str], context: Context) -> Loaded:
        native = runtime(context)
        import mathformer as hub

        action = hub.build_registry()["physics-lean:new-qm-source-only-batch"]
        errors = hub.preflight(
            action,
            hub.RunContext(allow_mutating=True),
            argv,
            repository_root=native.REPO_ROOT,
        )
        if errors:
            raise ValueError("; ".join(errors))
        try:
            return {"state": native.initialize(argv)}
        except SystemExit as error:
            raise ValueError(str(error)) from error

    @mcp.tool()
    def mathformer_new_qm_generate(state: BatchState, context: Context) -> Worked:
        native = runtime(context)
        validate_state(native, state)
        try:
            return {"work": native.generate_next(state)}
        except SystemExit as error:
            raise ValueError(str(error)) from error

    def gate(work, context, method):
        native = runtime(context)
        validate_work(native, work)
        return {"work": getattr(native, method)(deepcopy(work))}

    @mcp.tool()
    def mathformer_new_qm_initial_plan(work: CaseWork, context: Context) -> Worked:
        return gate(work, context, "initial_plan")

    @mcp.tool()
    def mathformer_new_qm_compile(work: CaseWork, context: Context) -> Worked:
        return gate(work, context, "compile_case")

    @mcp.tool()
    def mathformer_new_qm_completeness(work: CaseWork, context: Context) -> Worked:
        return gate(work, context, "check_completeness")

    @mcp.tool()
    def mathformer_new_qm_repair_plans(work: CaseWork, context: Context) -> Worked:
        return gate(work, context, "repair_plans")

    @mcp.tool()
    def mathformer_new_qm_final_plan(work: CaseWork, context: Context) -> Worked:
        return gate(work, context, "final_plan")

    @mcp.tool()
    def mathformer_new_qm_append_case(state: BatchState, work: CaseWork) -> Advanced:
        native = source()
        validate_state(native, state)
        if state["position"] >= len(native.SELECTED_CASES):
            raise ValueError("fixed case selection is exhausted")
        index = native.SELECTED_CASES[state["position"]]
        if work["result"]["source_index"] != index or work["result"][
            "case_id"
        ] != native.case_id(index):
            raise ValueError("case result is out of order")
        return native.append_case(state, work)

    @mcp.tool()
    def mathformer_new_qm_grounding_audit(
        state: BatchState, context: Context
    ) -> Audited:
        native = runtime(context)
        validate_state(native, state, complete=True)
        return {"audit": native.grounding_audit(state)}

    @mcp.tool()
    def mathformer_new_qm_report(
        state: BatchState, audit: dict, context: Context
    ) -> Finished:
        native = runtime(context)
        validate_state(native, state, complete=True)
        # Protocol stdout belongs to MCP; native observability goes to stderr.
        with redirect_stdout(sys.stderr):
            return native.report(state, audit)
