# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Typed MCP steps over the native fixed Dirac batch (no alternate algorithm).

A fresh module per call gives each invocation its own repository context without
mutating the CLI module or sharing mutable path globals between MCP requests.
"""

from contextlib import redirect_stdout
from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "scripts/physics-lean/generate_formalphysics_dirac_recursive_lean.py"


class Context(TypedDict):
    repository_root: str
    allow_mutating: bool


class BatchState(TypedDict):
    records: list[dict]
    selected: list[dict]
    lean_results: list[dict]
    review_reports: list[dict]
    completeness_reports: list[dict]


class Grounding(TypedDict):
    concept_file: str
    intake: dict
    surface: dict
    workbench: dict
    verification: dict


class Guards(TypedDict):
    target_restating: bool
    partial: bool
    all_complete: bool


class Loaded(TypedDict):
    state: BatchState


class Advanced(TypedDict):
    state: BatchState
    done: bool


class Grounded(TypedDict):
    grounding: Grounding


class Classified(TypedDict):
    guards: Guards


class Status(TypedDict):
    status: str


class Finished(TypedDict):
    report: dict
    recursive_plan: dict
    exit_code: int


def source(repository_root=None):
    spec = importlib.util.spec_from_file_location(
        "dirac_recursive_native", ROOT / SOURCE
    )
    native = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(native)
    if repository_root is not None:
        native.REPO_ROOT = Path(repository_root).resolve(strict=True)
        native.DATASET = (
            native.REPO_ROOT / "data/benchmarks/formal_science/FormalPhysics.json"
        )
        native.ARTIFACT_ROOT = (
            native.REPO_ROOT / "artifacts/physics_lean/dirac_recursive_batch"
        )
        native.LEAN_ROOT = native.REPO_ROOT / "MathformerPhysicsLib/Lean"
    return native


def validate_state(native, state):
    """Reject altered iterator identities or paths before native I/O."""
    for index, item in enumerate(state["selected"]):
        if index >= len(native.SELECTED_IDS):
            raise ValueError("fixed selection is exhausted")
        source_index = native.SELECTED_IDS[index]
        case_id = f"formalphysics_{source_index:04d}"
        expected = {
            "source_index": source_index,
            "case_id": case_id,
            "lean_path": f"MathformerPhysicsLib/Lean/{case_id}/MathformerPhysics.lean",
            "artifact_dir": f"artifacts/physics_lean/dirac_recursive_batch/{case_id}",
        }
        if any(item.get(key) != value for key, value in expected.items()):
            raise ValueError("state differs from fixed source selection")
    for key in ("lean_results", "review_reports", "completeness_reports"):
        if len(state[key]) > len(state["selected"]):
            raise ValueError("accumulator is ahead of selection")
        for item, selected in zip(state[key], state["selected"]):
            if item.get("case_id") != selected["case_id"]:
                raise ValueError("accumulator order differs from fixed selection")


def require_completed(native, state, *passes):
    """Keep independently callable steps behind the native batch pass order."""
    if any(len(state[key]) != len(native.SELECTED_IDS) for key in passes):
        raise ValueError("preceding fixed pass is incomplete: " + ", ".join(passes))


def register_dirac_recursive_tools(mcp, before_write):
    def runtime(context, writing=False):
        if not context["allow_mutating"]:
            raise ValueError("Dirac batch requires allow_mutating=true")
        native = source(context["repository_root"])
        if writing:
            before_write(native.ARTIFACT_ROOT)
            for index in native.SELECTED_IDS:
                before_write(native.LEAN_ROOT / f"formalphysics_{index:04d}")
        return native

    @mcp.tool()
    def mathformer_dirac_load_and_pack(context: Context) -> Loaded:
        native = runtime(context, True)
        # Reuse the hub preflight; dry-run remains a hub concern and never
        # launches this graph. No credentials or provider configuration is read.
        import mathformer as hub

        action = hub.build_registry()["physics-lean:dirac-recursive-formalphysics"]
        errors = hub.preflight(
            action,
            hub.RunContext(allow_mutating=context["allow_mutating"]),
            [],
            repository_root=native.REPO_ROOT,
        )
        if errors:
            raise ValueError("; ".join(errors))
        native.ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
        return {
            "state": {
                "records": native.load_dataset(),
                "selected": [],
                "lean_results": [],
                "review_reports": [],
                "completeness_reports": [],
            }
        }

    @mcp.tool()
    def mathformer_dirac_write_next_source(
        state: BatchState, context: Context
    ) -> Advanced:
        native = runtime(context, True)
        validate_state(native, state)
        updated = deepcopy(state)
        index = len(updated["selected"])
        if index >= len(native.SELECTED_IDS):
            raise ValueError("fixed selection is exhausted")
        updated["selected"].append(
            native.write_source(updated["records"], native.SELECTED_IDS[index])
        )
        done = len(updated["selected"]) == len(native.SELECTED_IDS)
        if done:
            native.write_selection(updated["selected"])
        return {"state": updated, "done": done}

    @mcp.tool()
    def mathformer_dirac_build_grounding(context: Context) -> Grounded:
        return {"grounding": runtime(context, True).build_grounding_artifacts()}

    def advance(state, context, accumulator, method, grounding=None):
        native = runtime(context, True)
        validate_state(native, state)
        updated = deepcopy(state)
        if len(updated["selected"]) != len(native.SELECTED_IDS):
            raise ValueError("fixed selection is incomplete")
        preceding = {
            "lean_results": ("selected",),
            "review_reports": ("selected", "lean_results"),
            "completeness_reports": ("selected", "lean_results", "review_reports"),
        }
        require_completed(native, updated, *preceding[accumulator])
        index = len(updated[accumulator])
        if index >= len(native.SELECTED_IDS):
            raise ValueError("fixed pass is exhausted")
        item = updated["selected"][index]
        args = ([item],) if grounding is None else ([item], grounding)
        updated[accumulator].extend(getattr(native, method)(*args))
        return {
            "state": updated,
            "done": len(updated[accumulator]) == len(native.SELECTED_IDS),
        }

    @mcp.tool()
    def mathformer_dirac_compile_next(state: BatchState, context: Context) -> Advanced:
        return advance(state, context, "lean_results", "validate_lean")

    @mcp.tool()
    def mathformer_dirac_review_next(state: BatchState, context: Context) -> Advanced:
        return advance(
            state, context, "review_reports", "run_final_hypothesis_reviewers"
        )

    @mcp.tool()
    def mathformer_dirac_check_next(
        state: BatchState, grounding: Grounding, context: Context
    ) -> Advanced:
        return advance(
            state,
            context,
            "completeness_reports",
            "run_derivation_completeness",
            grounding,
        )

    @mcp.tool()
    def mathformer_dirac_compute_guards(
        state: BatchState, grounding: Grounding
    ) -> Classified:
        native = source()
        validate_state(native, state)
        require_completed(
            native,
            state,
            "selected",
            "lean_results",
            "review_reports",
            "completeness_reports",
        )
        return {
            "guards": native.completion_guards(
                state["completeness_reports"],
                state["review_reports"],
                len(grounding["surface"].get("recursive_frontier", [])),
            )
        }

    @mcp.tool()
    def mathformer_dirac_return_status(status: str) -> Status:
        if status not in {
            "blocked_target_restating_assumption",
            "derivation_partial",
            "complete_autoformalization",
            "grounded_scaffold",
        }:
            raise ValueError("unknown completion status")
        return {"status": status}

    @mcp.tool()
    def mathformer_dirac_write_reports(
        state: BatchState, grounding: Grounding, status: str, context: Context
    ) -> Finished:
        native = runtime(context, True)
        validate_state(native, state)
        require_completed(
            native,
            state,
            "selected",
            "lean_results",
            "review_reports",
            "completeness_reports",
        )
        expected = native.completion_status(
            state["completeness_reports"],
            state["review_reports"],
            len(grounding["surface"].get("recursive_frontier", [])),
        )
        if status != expected:
            raise ValueError("classified status differs from native completion status")
        report, plan, code = native.finish_batch(
            grounding,
            state["selected"],
            state["lean_results"],
            state["completeness_reports"],
            state["review_reports"],
        )
        with redirect_stdout(sys.stderr):
            native.emit_report(report, True)
        return {"report": report, "recursive_plan": plan, "exit_code": code}

    @mcp.tool()
    def mathformer_dirac_finish(
        state: BatchState, grounding: Grounding, status: str, context: Context
    ) -> Finished:
        """Report first, then propagate the native CLI's nonzero process exit.

        The separate write_reports interface remains available to callers that
        inspect exit evidence as data. The selected route must fail on that
        evidence, just as the hub's single subprocess action does.
        """
        result = mathformer_dirac_write_reports(state, grounding, status, context)
        if result["exit_code"] != 0:
            raise RuntimeError(
                "Dirac batch exited with status 1 after writing native reports"
            )
        return result
