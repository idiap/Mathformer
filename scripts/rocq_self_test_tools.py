# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable ports for the native structural Rocq self-test (no compiler)."""

from pathlib import Path
from typing_extensions import TypedDict
from backends.rocq.MathformerRocq import autoformalize as native


class State(TypedDict):
    state: dict


class Advanced(TypedDict):
    state: dict
    done: bool


class Result(TypedDict):
    result: dict


def register_rocq_self_test_tools(
    mcp, before_write=lambda: None, path_allowed=lambda path: True
):
    @mcp.tool()
    def mathformer_rocq_self_test_initialize(
        defaults: dict, repository_root: str
    ) -> State:
        """Load the fixed five-case suite in an explicit repository context."""
        if defaults != dict(
            manifest_file="tests/latex/wiki_level/manifest.json",
            output_dir="artifacts/rocq_self_test",
        ):
            raise ValueError("self-test requires native defaults")
        root = Path(repository_root).resolve()
        state = native.initialize_draft(
            root / defaults["manifest_file"],
            root / defaults["output_dir"],
            repository_root=root,
        )
        return {"state": state}

    @mcp.tool()
    def mathformer_rocq_self_test_draft_next(state: dict) -> Advanced:
        """Draft, write and structurally check the next source fixture."""
        before_write()
        output = Path(state["output_dir"]).resolve()
        if not path_allowed(output):
            raise ValueError("destination outside allowed write roots")
        case = native.case_from_id(str(state["selected"][state["cursor"]]["id"]))
        if not path_allowed(native.output_path_for_case(case, output).resolve()):
            raise ValueError("destination outside allowed write roots")
        return native.draft_next(state)

    @mcp.tool()
    def mathformer_rocq_self_test_begin_reread(state: dict) -> State:
        return {"state": native.begin_reread(state)}

    @mcp.tool()
    def mathformer_rocq_self_test_validate_next(state: dict) -> Advanced:
        return native.validate_next(state)

    @mcp.tool()
    def mathformer_rocq_self_test_aggregate(state: dict) -> Result:
        return {"result": native.aggregate_self_test(state)}
