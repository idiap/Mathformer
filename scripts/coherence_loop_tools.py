# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Registered MCP ports for the one-pass native coherence report."""

from functools import lru_cache
import importlib.util
from pathlib import Path
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "tests/physics_lean/run_mathformerphysicslib_coherence_loop.py"


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "coherence_loop_native", ROOT / SOURCE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Directory(TypedDict):
    directory: str


class Inventory(TypedDict):
    inventory: dict


class Graph(TypedDict):
    graph: dict


class Grounding(TypedDict):
    grounding: dict


class Reports(TypedDict):
    reports: list[dict]


class Plans(TypedDict):
    plans: dict


class Artifacts(TypedDict):
    artifacts: dict
    root: str


class Result(TypedDict):
    result: dict


def register_coherence_loop_tools(mcp, write_policy, path_allowed):
    def writable(directory):
        write_policy()
        if not path_allowed(Path(directory)):
            raise ValueError("Output path is outside configured write roots")

    @mcp.tool()
    def mathformer_coherence_loop_prepare_directory(output_dir: str) -> Directory:
        writable(output_dir)
        return {"directory": source().prepare_directory(Path(output_dir))}

    @mcp.tool()
    def mathformer_coherence_loop_inventory(
        repository_root: str | None = None, directory: str | None = None
    ) -> Inventory:
        # directory is retained as an optional compatibility port for the
        # canonical descriptor. Inventory itself consumes only repository context.
        native = source()
        inventory = (
            native.build_inventory()
            if repository_root is None
            else native.build_inventory(Path(repository_root))
        )
        return {"inventory": inventory}

    @mcp.tool()
    def mathformer_coherence_loop_canonicalize(inventory: dict) -> Graph:
        return {"graph": source().canonicalize(inventory)}

    @mcp.tool()
    def mathformer_coherence_loop_audit_grounding(graph: dict) -> Grounding:
        return {"grounding": source().audit_grounding(graph)}

    @mcp.tool()
    def mathformer_coherence_loop_compare_previous(
        directory: str, grounding: dict
    ) -> Grounding:
        return {"grounding": source().compare_previous(Path(directory), grounding)}

    @mcp.tool()
    def mathformer_coherence_loop_critics(
        inventory: dict,
        graph: dict,
        grounding: dict,
        repository_root: str | None = None,
    ) -> Reports:
        root = None if repository_root is None else Path(repository_root)
        return {"reports": source().run_critics(inventory, graph, grounding, root)}

    @mcp.tool()
    def mathformer_coherence_loop_plan_and_gate(reports: list[dict]) -> Plans:
        return {"plans": source().plan_and_gate(reports)}

    @mcp.tool()
    def mathformer_coherence_loop_write_reports(
        directory: str,
        inventory: dict,
        graph: dict,
        reports: list[dict],
        plans: dict,
        repository_root: str | None = None,
    ) -> Artifacts:
        writable(directory)
        native = source()
        root = native.REPO_ROOT if repository_root is None else Path(repository_root)
        return {
            "artifacts": native.write_reports(
                Path(directory), inventory, graph, reports, plans, root
            ),
            "root": str(root),
        }

    @mcp.tool()
    def mathformer_coherence_loop_check_and_summarize(
        inventory: dict,
        graph: dict,
        reports: list[dict],
        plans: dict,
        artifacts: dict,
        repository_root: str | None = None,
    ) -> Result:
        native = source()
        root = native.REPO_ROOT if repository_root is None else Path(repository_root)
        return {
            "result": native.check_and_summarize(
                inventory, graph, reports, plans, artifacts, root
            )
        }
