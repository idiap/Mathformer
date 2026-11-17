# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP interfaces for the runtime trace validator's shared native steps."""

from functools import lru_cache
import importlib.util
from pathlib import Path
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "_runtime_trace_validation_native",
        ROOT / "meta_skills/scripts/validate_runtime_traces.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Initialized(TypedDict):
    state: dict
    has_traces: bool


class Checked(TypedDict):
    check: dict


class Advanced(TypedDict):
    state: dict
    done: bool


class Carried(TypedDict):
    state: dict


class Reported(TypedDict):
    report: dict


def context_root(repository_root):
    root = (ROOT / repository_root).resolve() if repository_root else ROOT
    if not root.is_relative_to(ROOT):
        raise ValueError("runtime trace context must be inside the repository")
    return root


def check_state(state):
    root = context_root(state["repository_root"])
    output = root / "artifacts/meta_skills/runtime_trace_validation.json"
    if Path(state["output_path"]).resolve() != output.resolve():
        raise ValueError("runtime trace output differs from context")
    traces = (root / "artifacts/meta_skills/runtime").resolve()
    for path in state["traces"]:
        if Path(path).resolve().parent != traces or Path(path).suffix != ".jsonl":
            raise ValueError("trace path escapes native discovery context")
    if not 0 <= state["cursor"] <= len(state["traces"]) <= 1000:
        raise ValueError("invalid runtime trace cursor or bound")
    return output


def register_runtime_trace_validation_tools(mcp, write_policy=lambda path: None):
    @mcp.tool()
    def mathformer_trace_validation_initialize(
        discovered_trace_count: int, repository_root: str
    ) -> Initialized:
        state = source().initialize(context_root(repository_root))
        if not 0 <= discovered_trace_count <= 1000 or discovered_trace_count != len(
            state["traces"]
        ):
            raise ValueError(
                "discovered_trace_count must equal actual discovery and be at most 1000"
            )
        check_state(state)
        return {"state": state, "has_traces": bool(state["traces"])}

    @mcp.tool()
    def mathformer_trace_validation_validate_file(state: dict) -> Checked:
        check_state(state)
        return {"check": source().validate_current(state)}

    @mcp.tool()
    def mathformer_trace_validation_accumulate(state: dict, check: dict) -> Advanced:
        check_state(state)
        state = source().accumulate(state, check)
        return {"state": state, "done": state["cursor"] == len(state["traces"])}

    @mcp.tool()
    def mathformer_trace_validation_empty_state(state: dict) -> Advanced:
        check_state(state)
        if state["traces"]:
            raise ValueError("empty branch requires no traces")
        return {"state": state, "done": True}

    @mcp.tool()
    def mathformer_trace_validation_write_report(state: dict) -> Reported:
        output = check_state(state)
        if state["cursor"] != len(state["traces"]):
            raise ValueError("cannot write before consuming every trace")
        if (
            output.resolve() != source().OUTPUT_PATH.resolve()
            and not output.resolve().is_relative_to(ROOT / "artifacts/workflow_hub")
        ):
            raise ValueError("runtime trace output outside declared write roots")
        write_policy(output)
        return {"report": source().write_report(state)}
