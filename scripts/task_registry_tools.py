# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP ports for the shared native task-registry validation steps."""

from functools import lru_cache
import importlib.util
from pathlib import Path
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "task_registry_native", ROOT / "meta_skills/scripts/validate_task_registries.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Initialized(TypedDict):
    state: dict
    has_work: bool


class Advanced(TypedDict):
    state: dict
    done: bool


class Retained(TypedDict):
    state: dict
    done: bool


class Reported(TypedDict):
    result: dict


def context_root(repository_root):
    root = (ROOT / repository_root).resolve()
    if not root.is_relative_to(ROOT) or not root.is_dir():
        raise ValueError(
            "task registry context must be a directory inside the repository"
        )
    return root


def check_state(state):
    root = context_root(state["repository_root"])
    output = root / "artifacts/meta_skills/task_registry_validation.json"
    if Path(state["output_path"]).resolve() != output.resolve():
        raise ValueError("task registry output differs from context")
    registries = (root / "meta_skills/registry/tasks").resolve()
    for path in state["registry_paths"]:
        if not Path(path).resolve().is_relative_to(registries):
            raise ValueError("registry path escapes context")
    if not 0 <= state["cursor"] <= len(state["registry_paths"]) <= 10000:
        raise ValueError("invalid registry cursor or bound")
    return output


def register_task_registry_tools(mcp, write_policy=lambda path: None):
    @mcp.tool()
    def mathformer_task_registry_initialize(
        domain: dict, repository_root: str
    ) -> Initialized:
        state = source().initialize(context_root(repository_root))
        count = domain["discovered_registry_count"]
        if (
            type(count) is not int
            or not 0 <= count <= 10000
            or count != len(state["registry_paths"])
        ):
            raise ValueError(
                "discovered_registry_count must equal discovery and be at most 10000"
            )
        check_state(state)
        state["has_work"] = bool(state["registry_paths"])
        return {"state": state, "has_work": state["has_work"]}

    @mcp.tool()
    def mathformer_task_registry_validate_accumulate(state: dict) -> Advanced:
        check_state(state)
        state = source().validate_accumulate(state)
        return {"state": state, "done": state["cursor"] == len(state["registry_paths"])}

    @mcp.tool()
    def mathformer_task_registry_empty_state(state: dict) -> Retained:
        check_state(state)
        if state["registry_paths"]:
            raise ValueError("empty branch requires empty discovery")
        return {"state": state, "done": True}

    @mcp.tool()
    def mathformer_task_registry_write_report(state: dict) -> Reported:
        output = check_state(state)
        if state["cursor"] != len(state["registry_paths"]):
            raise ValueError("cannot report before consuming every registry")
        if (
            output.resolve() != source().OUTPUT_PATH.resolve()
            and not output.resolve().is_relative_to(ROOT / "artifacts/workflow_hub")
        ):
            raise ValueError("task registry output is outside declared write roots")
        write_policy(output)
        return {"result": source().write_report(state)}
