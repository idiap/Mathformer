# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Pure MCP ports for the shared native pathology repair planner."""

import importlib.util
from functools import lru_cache
from pathlib import Path
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "skills/physics-lean/physics-lean-pathology-repair-orchestrator/scripts/orchestrate_pathology_repair.py"


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "pathology_repair_native", ROOT / SOURCE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FindingsOutput(TypedDict):
    findings: dict


class StatusOutput(TypedDict):
    status: str


class PlanOutput(TypedDict):
    result: dict


def register_pathology_repair_tools(mcp):
    @mcp.tool()
    def mathformer_pathology_repair_aggregate(reports: dict) -> FindingsOutput:
        """Collect all supplied evidence with native conversion/failure semantics."""
        return {
            "findings": source().aggregate_findings(
                monitor_report=reports["monitor_report"],
                workbench_plan=reports["workbench_plan"],
                repair_plans=reports["repair_plans"],
            )
        }

    @mcp.tool()
    def mathformer_pathology_repair_assign_status(status: str) -> StatusOutput:
        """Carry the result of the workflow's ordered status selection."""
        return {"status": source().assign_status(status)}

    @mcp.tool()
    def mathformer_pathology_repair_assemble(
        reports: dict, findings: dict, status: str
    ) -> PlanOutput:
        """Return the source-owned policy and pending gates; execute no repairs."""
        return {
            "result": source().assemble_plan(
                **reports,
                findings=findings,
                status=status,
            )
        }
