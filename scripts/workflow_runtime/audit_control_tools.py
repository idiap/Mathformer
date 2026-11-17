# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Serializable MCP ports for the shared workflow-control audit stages."""

from pathlib import Path
from types import SimpleNamespace
from typing_extensions import TypedDict
import mathformer as hub


class PathsOutput(TypedDict):
    paths: list[str]


class SourcesOutput(TypedDict):
    sources: dict
    controlled: list[str]


class FindingsOutput(TypedDict):
    findings: dict


class ErrorsOutput(TypedDict):
    errors: list[dict]


class ReportOutput(TypedDict):
    result: dict


def native_registry(registry):
    """Project only the attributes consumed by audit_control, retaining order."""
    return {key: SimpleNamespace(**value) for key, value in registry.items()}


def register_audit_control_tools(mcp):
    @mcp.tool()
    def mathformer_audit_registered(
        registry: dict, repository_root: str
    ) -> PathsOutput:
        return {
            "paths": sorted(
                hub.extract_python_paths_from_commands(
                    (item.command for item in native_registry(registry).values()),
                    Path(repository_root),
                )
            )
        }

    @mcp.tool()
    def mathformer_audit_matrix(repository_root: str) -> PathsOutput:
        return {"paths": sorted(hub.load_test_matrix_commands(Path(repository_root)))}

    @mcp.tool()
    def mathformer_audit_hooks(repository_root: str) -> PathsOutput:
        return {"paths": sorted(hub.load_skill_hook_scripts(Path(repository_root)))}

    @mcp.tool()
    def mathformer_audit_pack_sources(
        registered: list[str], matrix: list[str], hooks: list[str]
    ) -> SourcesOutput:
        sources, controlled = hub.audit_pack_sources(registered, matrix, hooks)
        return {"sources": sources, "controlled": controlled}

    @mcp.tool()
    def mathformer_audit_inspect_paths(
        sources: dict, controlled: list[str], repository_root: str
    ) -> FindingsOutput:
        return {
            "findings": hub.audit_inspect_paths(
                sources, controlled, Path(repository_root)
            )
        }

    @mcp.tool()
    def mathformer_audit_dependencies(registry: dict) -> ErrorsOutput:
        return {"errors": hub.audit_dependencies(native_registry(registry))}

    @mcp.tool()
    def mathformer_audit_report(
        sources: dict, findings: dict, errors: list[dict]
    ) -> ReportOutput:
        return {"result": hub.audit_report(sources, findings, errors)}
