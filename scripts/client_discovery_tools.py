# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Read-only MCP bindings for the native cross-client discovery traversal."""

from functools import lru_cache
import importlib.util
from pathlib import Path
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "client_discovery_native",
        ROOT / "tests/agent_clients/run_skill_client_discovery.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CanonicalResult(TypedDict):
    canonical: dict[str, str]


class StateResult(TypedDict):
    state: dict


class CheckedResult(TypedDict):
    result: dict


class AdvancedResult(TypedDict):
    state: dict
    done: bool


class ReportResult(TypedDict):
    report: dict


def register_client_discovery_tools(mcp):
    @mcp.tool()
    def mathformer_client_discovery_collect(repo_root: str) -> CanonicalResult:
        return {
            "canonical": {
                name: str(path)
                for name, path in source()
                .canonical_skills(Path(repo_root) / "skills")
                .items()
            }
        }

    @mcp.tool()
    def mathformer_client_discovery_initialize(
        canonical: dict[str, str], repo_root: str
    ) -> StateResult:
        return {"state": source().initialize_discovery(canonical, Path(repo_root))}

    @mcp.tool()
    def mathformer_client_discovery_check(state: dict) -> CheckedResult:
        return {"result": source().inspect_discovery_client(state)}

    @mcp.tool()
    def mathformer_client_discovery_advance(
        state: dict, result: dict
    ) -> AdvancedResult:
        state, done = source().advance_discovery(state, result)
        return {"state": state, "done": done}

    @mcp.tool()
    def mathformer_client_discovery_aggregate(state: dict) -> ReportResult:
        return {"report": source().aggregate_discovery(state)}


if __name__ == "__main__":
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("mathformer-client-discovery")
    register_client_discovery_tools(server)
    server.run(transport="stdio")
