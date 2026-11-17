# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Transport adapters for the native finite plugin synchronization sweeps."""

from pathlib import Path
from typing_extensions import TypedDict
import sync_agent_plugins as native


class Projection(TypedDict):
    expected: dict[str, str]
    expected_order: list[str]


class Stale(TypedDict):
    stale: list[str]


class State(TypedDict):
    root: str
    expected: dict[str, str]
    expected_order: list[str]
    stale: list[str]
    differences: list[str]
    cursor: int


class Packed(TypedDict):
    state: State


class Advanced(TypedDict):
    state: State
    done: bool


class Finished(TypedDict):
    differences: list[str]


def ordered(expected, order):
    if len(order) != len(expected) or set(order) != set(expected):
        raise ValueError("Projection order does not match expected files")
    return {Path(p): expected[p] for p in order}


def mutation_path(root, relative):
    path = Path(relative)
    if (
        path.is_absolute()
        or ".." in path.parts
        or not any(
            path.is_relative_to(prefix)
            for prefix in ("plugins/mathformer", ".agents/plugins", ".claude-plugin")
        )
    ):
        raise ValueError("Mutation is outside plugin projection paths")
    return Path(root) / path


def validate(state):
    ordered(state["expected"], state["expected_order"])
    if len(state["expected"]) > 10000 or len(state["stale"]) > 10000:
        raise ValueError("Projection exceeds specialization bound")
    if not 0 <= state["cursor"] <= 10000:
        raise ValueError("Invalid cursor")


def register_plugin_sync_tools(mcp, write_policy=lambda path: None):
    @mcp.tool()
    def mathformer_plugin_sync_project(root: str) -> Projection:
        expected = native.expected_files(Path(root))
        if len(expected) > 10000:
            raise ValueError("Projection exceeds specialization bound")
        return {
            "expected": {str(p): v for p, v in expected.items()},
            "expected_order": [str(p) for p in expected],
        }

    @mcp.tool()
    def mathformer_plugin_sync_discover_stale(
        root: str, expected: dict[str, str]
    ) -> Stale:
        stale = native.find_stale(Path(root), {Path(p): v for p, v in expected.items()})
        if len(stale) > 10000:
            raise ValueError("Stale sweep exceeds specialization bound")
        return {"stale": [str(p) for p in stale]}

    @mcp.tool()
    def mathformer_plugin_sync_compare_pack(
        root: str, expected: dict[str, str], stale: list[str], expected_order: list[str]
    ) -> Packed:
        state = State(
            root=root,
            expected=expected,
            expected_order=expected_order,
            stale=stale,
            differences=[],
            cursor=0,
        )
        validate(state)
        state["differences"] = native.compare_projection(
            Path(root), ordered(expected, expected_order), [Path(p) for p in stale]
        )
        return {"state": state}

    @mcp.tool()
    def mathformer_plugin_sync_write_next(state: State) -> Advanced:
        validate(state)
        state = dict(state)
        cursor = state["cursor"]
        order = state["expected_order"]
        if cursor < len(order):
            path = Path(order[cursor])
            write_policy(mutation_path(state["root"], path))
            native.write_projection_item(
                Path(state["root"]), path, state["expected"][str(path)]
            )
            state["cursor"] += 1
        return {"state": state, "done": state["cursor"] >= len(order)}

    @mcp.tool()
    def mathformer_plugin_sync_skip_sweep(state: State) -> Advanced:
        """Check mode bypasses both mutation sweeps without filesystem access."""
        validate(state)
        return {"state": state, "done": True}

    @mcp.tool()
    def mathformer_plugin_sync_reset_cursor(state: State) -> Packed:
        validate(state)
        return {"state": {**state, "cursor": 0}}

    @mcp.tool()
    def mathformer_plugin_sync_remove_next(state: State) -> Advanced:
        validate(state)
        state = dict(state)
        if state["cursor"] < len(state["stale"]):
            path = Path(state["stale"][state["cursor"]])
            write_policy(mutation_path(state["root"], path))
            write_policy(mutation_path(state["root"], path.parent / "workflow.yaml"))
            native.remove_stale_item(Path(state["root"]), path)
            state["cursor"] += 1
        return {"state": state, "done": state["cursor"] >= len(state["stale"])}

    @mcp.tool()
    def mathformer_plugin_sync_return_differences(state: State) -> Finished:
        validate(state)
        return {"differences": state["differences"]}


if __name__ == "__main__":
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("mathformer-plugin-sync")

    def local_write_policy(path):
        path.resolve().relative_to(Path(__file__).resolve().parents[1])

    register_plugin_sync_tools(server, local_write_policy)
    server.run(transport="stdio")
