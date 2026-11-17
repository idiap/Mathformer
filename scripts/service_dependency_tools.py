# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP bindings for the shared, read-only service dependency probe steps."""

from typing_extensions import TypedDict
import probe_mcp_service_dependencies as native


class ScanState(TypedDict):
    cursor: int
    rows: list[dict]
    done: bool


class Scans(TypedDict):
    packages: ScanState
    tools: ScanState


class Advanced(TypedDict):
    state: ScanState


class Missing(TypedDict):
    missing_required: list[dict]
    optional_blockers: list[dict]
    ready: bool


class Classified(TypedDict):
    missing: Missing


class Requirements(TypedDict):
    entries: list[str]


class Report(TypedDict):
    report: dict


def register_service_dependency_tools(mcp):
    @mcp.tool()
    def mathformer_service_dependencies_initialize() -> Scans:
        return native.initialize_scans()

    @mcp.tool()
    def mathformer_service_dependencies_package_next(state: ScanState) -> Advanced:
        return {"state": native.package_next(state)}

    @mcp.tool()
    def mathformer_service_dependencies_tool_next(state: ScanState) -> Advanced:
        return {"state": native.tool_next(state)}

    @mcp.tool()
    def mathformer_service_dependencies_classify(
        packages: ScanState, tools: ScanState
    ) -> Classified:
        return {
            "missing": native.classify_dependencies(packages["rows"], tools["rows"])
        }

    @mcp.tool()
    def mathformer_service_dependencies_requirements(missing: Missing) -> Requirements:
        return {"entries": native.read_service_requirements()}

    @mcp.tool()
    def mathformer_service_dependencies_assemble(
        packages: ScanState,
        tools: ScanState,
        missing: Missing,
        requirements: list[str],
        status: str,
    ) -> Report:
        return {
            "report": native.assemble_report(
                packages["rows"], tools["rows"], missing, requirements, status
            )
        }
