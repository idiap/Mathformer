# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Registered MCP steps for the native one-pass integration audit."""

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
from typing_extensions import TypedDict
import audit_workflow_skill_integration as native

ROOT = Path(__file__).resolve().parents[1]


class Context(TypedDict):
    repository_root: str


class PathsResult(TypedDict):
    paths: dict


class InventoryResult(TypedDict):
    inventory: dict


class GraphResult(TypedDict):
    graph: dict
    graph_json: str


class RegistriesResult(TypedDict):
    registries: dict
    registries_json: str


class ClassificationResult(TypedDict):
    classification: dict
    classification_json: str


class ReportResult(TypedDict):
    report: dict
    report_json: str


class Completion(TypedDict):
    result: dict
    exit_code: int
    stdout: str


def repository(context: Context) -> Path:
    root = Path(context["repository_root"]).resolve()
    root.relative_to(ROOT)
    return root


def ordered(value: dict, encoded: str) -> dict:
    """Preserve native insertion order across the PRISM record codec."""
    decoded = json.loads(encoded)
    if decoded != value:
        raise ValueError("ordered payload differs from typed payload")
    return decoded


def register_integration_audit_tools(mcp, write_policy=lambda: None):
    @mcp.tool()
    def mathformer_integration_audit_resolve(
        options: dict, context: Context
    ) -> PathsResult:
        return {"paths": native.resolve_paths(options, repository(context))}

    @mcp.tool()
    def mathformer_integration_audit_inventory(context: Context) -> InventoryResult:
        return {"inventory": native.read_skill_inventory(repository(context))}

    @mcp.tool()
    def mathformer_integration_audit_graph(paths: dict) -> GraphResult:
        graph = native.graph_modeled_skills(Path(paths["graph"]))
        return {"graph": graph, "graph_json": json.dumps(graph)}

    @mcp.tool()
    def mathformer_integration_audit_registries(paths: dict) -> RegistriesResult:
        hooks = native.parse_hook_registry(Path(paths["hooks"]))
        hub = native.parse_agentic_hub(Path(paths["hub"]))
        registries = {"hooks": hooks, "hub": hub}
        return {"registries": registries, "registries_json": json.dumps(registries)}

    @mcp.tool()
    def mathformer_integration_audit_classify(
        inventory: dict, graph: dict, registries: dict
    ) -> ClassificationResult:
        value = native.classify_skills(
            inventory, graph, registries["hooks"], registries["hub"]
        )
        return {"classification": value, "classification_json": json.dumps(value)}

    @mcp.tool()
    def mathformer_integration_audit_assemble(
        inventory: dict,
        graph: dict,
        graph_json: str,
        registries: dict,
        registries_json: str,
        classification: dict,
        classification_json: str,
    ) -> ReportResult:
        registries = ordered(registries, registries_json)
        report = native.assemble_report(
            inventory,
            ordered(graph, graph_json),
            registries["hooks"],
            registries["hub"],
            ordered(classification, classification_json),
        )
        return {"report": report, "report_json": json.dumps(report)}

    @mcp.tool()
    def mathformer_integration_audit_publish(
        paths: dict, report: dict, report_json: str, context: Context
    ) -> Completion:
        write_policy()
        root = repository(context)
        # MCP retains the workflow's artifact write ceiling; standalone CLI is unchanged.
        Path(paths["output_dir"]).resolve().relative_to(
            root / "artifacts/workflow_graphs"
        )
        stream = io.StringIO()
        with redirect_stdout(stream):
            result = native.publish_report(paths, ordered(report, report_json), root)
        stdout = stream.getvalue()
        print(stdout, end="", file=sys.stderr)
        return {"result": result, "exit_code": 0, "stdout": stdout}
