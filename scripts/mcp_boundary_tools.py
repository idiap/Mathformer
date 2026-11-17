# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable projections of the shared MCP boundary validator steps."""

from functools import lru_cache
import importlib.util
from pathlib import Path
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "mcp_boundary_native", ROOT / "meta_skills/scripts/validate_mcp_boundary.py"
    )
    native = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(native)
    return native


class Loaded(TypedDict):
    data: dict
    registry: list[str]
    state: dict
    has_actions: bool


class Advanced(TypedDict):
    state: dict
    findings: list[dict]
    done: bool


class Findings(TypedDict):
    findings: list[dict]


class Tools(TypedDict):
    findings: list[dict]
    tools: dict


class Written(TypedDict):
    result: dict


def register_mcp_boundary_tools(
    mcp, before_write=lambda: None, path_allowed=lambda path: True
):
    @mcp.tool()
    def mathformer_boundary_load(scope: dict, repository_root: str) -> Loaded:
        """Read declarations then build the real hub registry, preserving order."""
        if scope != {"max_workflow_actions": 1024}:
            raise ValueError("unsupported declaration domain")
        data, registry = source().load_boundary(
            Path(repository_root) / "meta_skills/registry/workflow_actions.yaml"
        )
        if len(data.get("workflow_actions", [])) > 1024:
            raise ValueError("declaration exceeds the 1024-row contract domain")
        return {
            "data": data,
            "registry": list(registry),
            "state": {"cursor": 0, "findings": []},
            "has_actions": bool(data.get("workflow_actions", [])),
        }

    @mcp.tool()
    def mathformer_boundary_action(
        data: dict, registry: list[str], state: dict
    ) -> Advanced:
        """Check one row without stopping on findings; advance its finite iterator."""
        rows = data.get("workflow_actions", [])
        cursor = state["cursor"]
        if not 0 <= cursor < len(rows) <= 1024:
            raise ValueError("invalid action cursor or domain")
        findings = list(state["findings"])
        source().check_action_row(rows[cursor], registry, findings)
        updated = {"cursor": cursor + 1, "findings": findings}
        return {"state": updated, "findings": findings, "done": cursor + 1 == len(rows)}

    @mcp.tool()
    def mathformer_boundary_empty(state: dict) -> Advanced:
        """Project findings on the zero-iteration path."""
        return {"state": state, "findings": state["findings"], "done": True}

    @mcp.tool()
    def mathformer_boundary_tools(
        data: dict, findings: list[dict], repository_root: str
    ) -> Tools:
        findings = list(findings)
        tools = source().check_tool_set(data, findings, Path(repository_root))
        return {"findings": findings, "tools": tools}

    @mcp.tool()
    def mathformer_boundary_docs(
        findings: list[dict], repository_root: str
    ) -> Findings:
        findings = list(findings)
        source().check_config_docs(findings, Path(repository_root))
        return {"findings": findings}

    @mcp.tool()
    def mathformer_boundary_denials(data: dict, findings: list[dict]) -> Findings:
        findings = list(findings)
        source().check_denied_surfaces(data, findings)
        return {"findings": findings}

    @mcp.tool()
    def mathformer_boundary_write(
        data: dict, tools: dict, findings: list[dict], repository_root: str
    ) -> Written:
        before_write()
        output = (
            Path(repository_root) / "artifacts/mcp/meta_skill_service_self_test.json"
        ).resolve()
        if not path_allowed(output):
            raise ValueError("report path is outside allowed write roots")
        return {
            "result": source().write_boundary_payload(
                data,
                tools,
                findings,
                output,
                "meta_skills/registry/workflow_actions.yaml",
            )
        }
