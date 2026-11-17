# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP ports for the shared native backend-test wrapper steps."""

from functools import lru_cache
import importlib.util
from pathlib import Path
from typing_extensions import TypedDict


@lru_cache(maxsize=1)
def source():
    path = Path(__file__).resolve().parents[1] / "tests/run_backend.py"
    spec = importlib.util.spec_from_file_location("backend_test_native", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Parsed(TypedDict):
    args: dict


class Families(TypedDict):
    families: list[str]


class State(TypedDict):
    state: dict


class Advanced(TypedDict):
    state: dict
    done: bool


class Command(TypedDict):
    command: list[str]


class Finished(TypedDict):
    exit_code: int


def register_backend_test_tools(mcp, write_policy):
    @mcp.tool()
    def mathformer_backend_test_parse(argv: list[str]) -> Parsed:
        """Parse native options; argument errors stop before any launch."""
        try:
            return {"args": source().parse_backend_args(argv)}
        except SystemExit as error:
            raise ValueError(f"backend argparse exited {error.code}") from error

    @mcp.tool()
    def mathformer_backend_test_select_all(args: dict) -> Families:
        return {"families": source().select_all(args)}

    @mcp.tool()
    def mathformer_backend_test_select_sorted(args: dict) -> Families:
        return {"families": source().select_sorted(args)}

    @mcp.tool()
    def mathformer_backend_test_pack(families: list[str]) -> State:
        return {"state": source().pack(families)}

    @mcp.tool()
    def mathformer_backend_test_append_family(state: dict) -> Advanced:
        return source().append_family(state)

    @mcp.tool()
    def mathformer_backend_test_finalize(state: dict, args: dict) -> Command:
        return {"command": source().finalize(state, args)}

    @mcp.tool()
    def mathformer_backend_test_launch(command: list[str]) -> Finished:
        """Launch only the native runner with its advertised backend options."""
        native = source()
        # Do not expose arbitrary subprocess execution through a mutable argv port.
        prefix = native.pack(["lean"])["command"]
        if command[:2] != prefix:
            raise ValueError("not the native backend runner")
        tail = command[2:]
        families = []
        while len(tail) >= 2 and tail[0] == "--module-family":
            families.append(tail[1])
            tail = tail[2:]
        if (
            not families
            or len(families) > 4
            or len(set(families)) != len(families)
            or any(f not in native.select_all({}) for f in families)
            or tail
            not in [
                ["--write-jsonl", "--write-junit"] + flags
                for flags in (
                    [],
                    ["--json"],
                    ["--fail-on-warning"],
                    ["--json", "--fail-on-warning"],
                )
            ]
        ):
            raise ValueError("not native backend runner arguments")
        write_policy(native.REPO_ROOT / "artifacts")
        # Child output must not corrupt the MCP stdio protocol. Inherit stderr
        # for both streams while retaining source-owned reports and transcript.
        import contextlib
        import os
        import sys

        sys.stdout.flush()
        with contextlib.ExitStack() as stack:
            saved = os.dup(1)
            stack.callback(os.close, saved)
            stack.callback(os.dup2, saved, 1)
            os.dup2(2, 1)
            return {"exit_code": native.launch(command)}
