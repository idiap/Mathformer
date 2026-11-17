# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP interfaces to shared native workflow evolution validation steps."""

from functools import lru_cache
import importlib.util
from pathlib import Path
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "workflow_evolution_native",
        ROOT / "meta_skills/scripts/validate_workflow_evolution.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Initialized(TypedDict):
    state: dict
    has_graphs: bool


class Validated(TypedDict):
    findings: list[dict]


class Advanced(TypedDict):
    state: dict
    done: bool


class Retained(TypedDict):
    state: dict
    done: bool


class Finished(TypedDict):
    report: dict


def context_root(repository_root):
    root = (ROOT / repository_root).resolve()
    if not root.is_relative_to(ROOT) or not root.is_dir():
        raise ValueError(
            "workflow evolution context must be a directory inside repository"
        )
    return root


def check_state(state):
    root = context_root(state["repository_root"])
    output = root / "artifacts/meta_skills/workflow_evolution_validation.json"
    if Path(state["output_path"]).resolve() != output.resolve():
        raise ValueError("output differs from context")
    for path in state["paths"]:
        if (
            not Path(path)
            .resolve()
            .is_relative_to((root / "meta_skills/registry/tasks").resolve())
        ):
            raise ValueError("graph path escapes context")
    if not 0 <= state["cursor"] <= len(state["paths"]) <= 1024:
        raise ValueError("invalid cursor or graph bound")
    return output


def register_workflow_evolution_tools(mcp, write_policy=lambda path: None):
    @mcp.tool()
    def mathformer_workflow_evolution_initialize(
        scope: dict, repository_root: str
    ) -> Initialized:
        if scope != {"graph_cap": 1024}:
            raise ValueError("scope must declare graph_cap=1024")
        state = source().initialize(context_root(repository_root))
        check_state(state)
        state["has_graphs"] = bool(state["paths"])
        return {"state": state, "has_graphs": state["has_graphs"]}

    @mcp.tool()
    def mathformer_workflow_evolution_validate_current(state: dict) -> Validated:
        check_state(state)
        return {"findings": source().validate_current(state)}

    @mcp.tool()
    def mathformer_workflow_evolution_accumulate(
        state: dict, findings: list[dict]
    ) -> Advanced:
        check_state(state)
        state = source().accumulate(state, findings)
        return {"state": state, "done": state["cursor"] == len(state["paths"])}

    @mcp.tool()
    def mathformer_workflow_evolution_empty_state(state: dict) -> Retained:
        check_state(state)
        if state["paths"]:
            raise ValueError("empty branch requires empty discovery")
        return {"state": state, "done": True}

    @mcp.tool()
    def mathformer_workflow_evolution_finish(state: dict) -> Finished:
        output = check_state(state)
        if state["cursor"] != len(state["paths"]):
            raise ValueError("cannot finish before consuming all graphs")
        if (
            output.resolve() != source().OUTPUT_PATH.resolve()
            and not output.resolve().is_relative_to(ROOT / "artifacts/workflow_hub")
        ):
            raise ValueError("output outside declared write roots")
        write_policy(output)
        return {"report": source().finish(state)}
