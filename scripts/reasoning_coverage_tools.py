# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable MCP ports for the native reasoning coverage scan."""

import importlib.util
from functools import lru_cache
from pathlib import Path
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "skills/control/reasoning-log-schema-guardian/scripts/audit_skill_reasoning_log_coverage.py"


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location("coverage_native", ROOT / SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Prepared(TypedDict):
    state: dict
    has_skills: bool


class Opened(TypedDict):
    state: dict
    has_scripts: bool


class Advanced(TypedDict):
    state: dict
    done: bool


class Reported(TypedDict):
    report: dict


def register_reasoning_coverage_tools(mcp):
    @mcp.tool()
    def mathformer_coverage_prepare(skills_dir: str, repo_root: str) -> Prepared:
        root = Path(repo_root).resolve()
        directory = Path(skills_dir)
        if not directory.is_absolute():
            directory = root / directory
        return source().prepare_scan(directory, root)

    @mcp.tool()
    def mathformer_coverage_open_skill(state: dict) -> Opened:
        if state["cursor"] == len(state["pending"]):
            return {
                "state": dict(
                    parent=state,
                    name="",
                    path="",
                    scripts=[],
                    agents=[],
                    hook_ids=[],
                    cursor=0,
                    native_scripts=[],
                    wrapper_scripts=[],
                    script_reports=[],
                ),
                "has_scripts": False,
            }
        return source().open_skill(state)

    @mcp.tool()
    def mathformer_coverage_inspect_script(state: dict) -> Advanced:
        if state["cursor"] == len(state["scripts"]):
            return {"state": state, "done": True}
        return source().inspect_script(state)

    @mcp.tool()
    def mathformer_coverage_commit_skill(state: dict) -> Advanced:
        parent = state["parent"]
        if parent["cursor"] == len(parent["pending"]):
            return {"state": parent, "done": True}
        return source().commit_skill(state)

    @mcp.tool()
    def mathformer_coverage_aggregate(state: dict) -> Reported:
        return {"report": source().aggregate_scan(state)}
