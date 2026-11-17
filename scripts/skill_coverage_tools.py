# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP ports for the shared native skill hook coverage implementation."""

from functools import lru_cache
import importlib.util
from pathlib import Path
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    "skills/control/skill-hook-coverage-maximizer/scripts/audit_skill_hook_coverage.py"
)


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "skill_coverage_native", ROOT / SOURCE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StateResult(TypedDict):
    state: dict


class ReportResult(TypedDict):
    report: dict


def register_skill_coverage_tools(mcp):
    native_source = source

    @mcp.tool()
    def mathformer_skill_coverage_load_and_pack(
        source: dict, repo_root: str
    ) -> StateResult:
        root = Path(repo_root).resolve()
        state = native_source().load_audit(
            hooks_file=(root / source["hooks_file"]).resolve(),
            skills_dir=(root / source["skills_dir"]).resolve(),
            min_non_wrapper_coverage=source["min_non_wrapper_coverage"],
            min_loop_count=source["min_loop_count"],
        )
        return {"state": state}

    @mcp.tool()
    def mathformer_skill_coverage_classify_one(state: dict) -> StateResult:
        return {"state": source().classify_one(state)}

    @mcp.tool()
    def mathformer_skill_coverage_pack_empty_state(state: dict) -> StateResult:
        return {"state": state}

    @mcp.tool()
    def mathformer_skill_coverage_thresholds_and_pack(state: dict) -> StateResult:
        return {"state": source().thresholds_and_pack(state)}

    @mcp.tool()
    def mathformer_skill_coverage_inspect_contract(state: dict) -> StateResult:
        return {"state": source().inspect_contract(state)}

    @mcp.tool()
    def mathformer_skill_coverage_finalize(state: dict) -> ReportResult:
        return {"report": source().finalize_audit(state)}
