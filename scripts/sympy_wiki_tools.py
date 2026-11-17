# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP bindings for the native wiki runner's shared blocks."""

from contextlib import redirect_stdout
from functools import lru_cache
import importlib.util
from pathlib import Path
import sys
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "sympy_wiki_native", ROOT / "tests/sympy/run_wiki_case.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StateOutput(TypedDict):
    state: dict


class ResultOutput(TypedDict):
    result: dict


class AdvanceOutput(TypedDict):
    state: dict
    done: bool


class CompletionOutput(TypedDict):
    completion: dict


def register_sympy_wiki_tools(
    mcp, before_write=lambda: None, path_allowed=lambda path: True
):
    def options_at_host(options):
        options = dict(options)
        path = Path(
            options.get("artifact_root", "artifacts/sympy/wiki_sum_first_odd_numbers")
        )
        path = path if path.is_absolute() else ROOT / path
        if not path_allowed(path):
            raise ValueError("SymPy wiki artifact root is outside allowed write roots")
        # Relative paths retain native argv spelling; the service runs at ROOT.
        return options

    def checked(state):
        options_at_host(state["options"])
        expected = source().prepare(state["options"])
        for key in ("python", "commands", "artifacts", "generated"):
            if state[key] != expected[key]:
                raise ValueError("State differs from the fixed native wiki plan")
        results = state["results"]
        if state["index"] != len(results) or len(results) > 11:
            raise ValueError("Invalid native command prefix")
        for command, result in zip(expected["commands"], results):
            if result["id"] != command["id"] or result["cmd"] != command["argv"]:
                raise ValueError("Result differs from native command prefix")
        if any(not r["ok"] for r in results[:-1]):
            raise ValueError("Cannot advance beyond a failed command")

    @mcp.tool()
    def mathformer_sympy_wiki_prepare(options: dict) -> StateOutput:
        """Construct the eleven native commands with CLI defaults."""
        before_write()
        return {"state": source().prepare(options_at_host(options))}

    @mcp.tool()
    def mathformer_sympy_wiki_execute(state: dict) -> ResultOutput:
        """Run the next fixed command once with its 120 second timeout."""
        before_write()
        checked(state)
        if state["index"] >= 11 or (
            state["results"] and not state["results"][-1]["ok"]
        ):
            raise ValueError("Native loop has already stopped")
        return {"result": source().execute_step(state)}

    @mcp.tool()
    def mathformer_sympy_wiki_advance(state: dict, result: dict) -> AdvanceOutput:
        """Append a result and compute failure or eleven-command completion."""
        before_write()
        checked(state)
        command = state["commands"][state["index"]]
        if result["id"] != command["id"] or result["cmd"] != command["argv"]:
            raise ValueError("Result is not for the current command")
        updated, done = source().advance(state, result)
        return {"state": updated, "done": done}

    @mcp.tool()
    def mathformer_sympy_wiki_finalize(state: dict) -> CompletionOutput:
        """Write the exact native e2e report and emit its status on service stderr."""
        before_write()
        checked(state)
        if not state["results"] or (
            state["index"] != 11 and state["results"][-1]["ok"]
        ):
            raise ValueError("Native loop is not complete")
        with redirect_stdout(sys.stderr):
            completion = source().finalize(state)
        return {"completion": completion}
