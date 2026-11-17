# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable MCP boundaries for the shared theorem seed generator steps."""

from contextlib import redirect_stdout, redirect_stderr
from functools import lru_cache
import importlib.util
import io
from pathlib import Path
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "skills/premise-kb/premise-kb-theorem-seed-generator/scripts/generate_theorem_axiom_seed_list.py"


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location("theorem_seed_native", ROOT / SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Parsed(TypedDict):
    options: dict
    state: dict
    halted: bool
    stdout: str


class Inspected(TypedDict):
    seed: dict
    matches: bool


class Advanced(TypedDict):
    state: dict


class Halted(TypedDict):
    state: dict
    done: bool


class Done(TypedDict):
    done: bool


class Finished(TypedDict):
    report: dict | None
    exit_code: int
    stdout: str


def register_theorem_seed_tools(mcp, write_policy=lambda: None):
    @mcp.tool()
    def mathformer_theorem_seed_parse(extra_args: list[str]) -> Parsed:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            try:
                options = source().parse_options(extra_args)
            except SystemExit as error:
                if error.code != 0:
                    raise ValueError(
                        f"argparse exited {error.code}: {err.getvalue()}"
                    ) from error
                return {
                    "options": {
                        "families": [],
                        "kinds": [],
                        "output": "",
                        "json": False,
                    },
                    "state": {"index": 0, "entries": []},
                    "halted": True,
                    "stdout": out.getvalue(),
                }
        return {
            "options": options,
            "state": {"index": 0, "entries": []},
            "halted": False,
            "stdout": out.getvalue(),
        }

    @mcp.tool()
    def mathformer_theorem_seed_inspect(options: dict, state: dict) -> Inspected:
        return source().inspect_seed(options, state)

    @mcp.tool()
    def mathformer_theorem_seed_retain(state: dict, seed: dict) -> Advanced:
        return {"state": source().retain_advance(state, seed)}

    @mcp.tool()
    def mathformer_theorem_seed_skip(state: dict) -> Advanced:
        return {"state": source().skip_advance(state)}

    @mcp.tool()
    def mathformer_theorem_seed_done(state: dict) -> Done:
        return {"done": source().scan_done(state)}

    @mcp.tool()
    def mathformer_theorem_seed_write(options: dict, state: dict) -> Finished:
        write_policy()
        out = io.StringIO()
        with redirect_stdout(out):
            result = source().write_report(options, state)
        return {**result, "stdout": out.getvalue()}

    @mcp.tool()
    def mathformer_theorem_seed_halt(state: dict) -> Halted:
        """Pass parse-time help termination through the loop frame without scanning."""
        return {"state": state, "done": True}

    @mcp.tool()
    def mathformer_theorem_seed_help(stdout: str) -> Finished:
        return {"report": None, "exit_code": 0, "stdout": stdout}


if __name__ == "__main__":
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("Mathformer theorem seeds")
    register_theorem_seed_tools(server)
    server.run(transport="stdio")
