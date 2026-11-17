# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable ports for the native coherence inventory CLI and self-test."""

from contextlib import redirect_stdout
from functools import lru_cache
import importlib.util
from pathlib import Path
import sys
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "skills/mathformerphysicslib/mathformerphysicslib-coherence-inventory-builder/scripts/build_coherence_inventory.py"


@lru_cache(maxsize=1)
def source():
    directory = ROOT / SOURCE
    sys.path.insert(0, str(directory.parent))
    try:
        spec = importlib.util.spec_from_file_location(
            "coherence_inventory_native", directory
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


class Options(TypedDict):
    options: dict


class Inventory(TypedDict):
    inventory: dict


class Graph(TypedDict):
    graph: dict


class Grounding(TypedDict):
    grounding: dict


class Critics(TypedDict):
    critics: dict


class Payload(TypedDict):
    payload: dict


class Completion(TypedDict):
    result: dict


def register_coherence_inventory_tools(mcp, write_policy, path_allowed):
    @mcp.tool()
    def mathformer_coherence_inventory_parse(argv: list[str]) -> Options:
        # argparse uses SystemExit for invalid input/help. Convert it at transport
        # boundary so a bad call cannot terminate the MCP service.
        with redirect_stdout(sys.stderr):
            try:
                return {"options": source().parse_options(argv)}
            except SystemExit as error:
                raise ValueError(f"argparse exited with code {error.code}") from error

    @mcp.tool()
    def mathformer_coherence_inventory_fixture() -> Inventory:
        return {"inventory": source().common.self_test_inventory()}

    @mcp.tool()
    def mathformer_coherence_inventory_canonicalize(inventory: dict) -> Graph:
        return {"graph": source().common.canonicalize(inventory)}

    @mcp.tool()
    def mathformer_coherence_inventory_grounding(graph: dict) -> Grounding:
        return {"grounding": source().common.audit_grounding(graph)}

    @mcp.tool()
    def mathformer_coherence_inventory_critics(
        inventory: dict, graph: dict, grounding: dict, repository_root: str
    ) -> Critics:
        return {
            "critics": source().common.self_test_critics(
                inventory, graph, grounding, Path(repository_root)
            )
        }

    @mcp.tool()
    def mathformer_coherence_inventory_finish(
        graph: dict, grounding: dict, critics: dict
    ) -> Payload:
        return {"payload": source().common.finish_self_test(graph, grounding, critics)}

    @mcp.tool()
    def mathformer_coherence_inventory_inventory(repository_root: str) -> Payload:
        return {"payload": source().common.build_inventory(Path(repository_root))}

    @mcp.tool()
    def mathformer_coherence_inventory_emit(options: dict, payload: dict) -> Completion:
        if options["output"]:
            write_policy()
            if not path_allowed(Path(options["output"])):
                raise ValueError("Output path is outside configured write roots")
        # Retain source emission on the stdio service diagnostic channel.
        with redirect_stdout(sys.stderr):
            code = source().emit_payload(options, payload)
        return {"result": {"payload": payload, "exit_code": code}}
