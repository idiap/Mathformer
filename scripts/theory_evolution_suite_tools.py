# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable MCP ports for the source-shared theory evolution suite stages."""

from contextlib import contextmanager, redirect_stdout
from functools import lru_cache
import importlib.util
import io
import os
from pathlib import Path
import sys
from typing_extensions import TypedDict

from theory_evolution_simulate_tools import _LOCK

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "paper_skills/theory-evolution-simulator/scripts/run_theory_evolution_simulation_suite.py"


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location("theory_suite_native", ROOT / SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Context(TypedDict):
    working_directory: str


class State(TypedDict):
    state: dict


class Task(TypedDict):
    task: dict


class Result(TypedDict):
    result: dict


class Accumulated(TypedDict):
    state: dict
    done: bool


class Terminal(TypedDict):
    manifest: dict
    exit_code: int
    stdout: str


@contextmanager
def native_context(context):
    directory = Path(context["working_directory"])
    if not directory.is_absolute():
        raise ValueError("working_directory must be absolute")
    with _LOCK:
        previous = Path.cwd()
        try:
            os.chdir(directory)
            yield
        finally:
            os.chdir(previous)


def register_theory_evolution_suite_tools(mcp, write_guard=lambda path: None):
    @mcp.tool()
    def mathformer_theory_suite_initialize(options: dict, context: Context) -> State:
        """Apply native defaults, load JSON, and create the suite directory."""
        # Parse through the CLI's actual parser; the contract specializes only
        # the scenario count. Runs and trajectory durations retain native ranges.
        argv = ["--model", options["model"], "--output-dir", options["output_dir"]]
        for name in ["runs", "seed"]:
            if name in options:
                argv.extend(["--" + name, str(options[name])])
        if "scenarios" in options:
            if not 1 <= len(options["scenarios"]) <= 5:
                raise ValueError("contract requires one to five scenario entries")
            argv.extend(["--scenarios", *options["scenarios"]])
        if options.get("json", False):
            argv.append("--json")
        with native_context(context):
            try:
                args = source().suite_parser().parse_args(argv)
            except SystemExit as error:
                raise ValueError("native suite argument rejection") from error
            write_guard(Path(args.output_dir).resolve())
            state = source().initialize_suite(vars(args))
            state["context"] = dict(context)
            return {"state": state}

    @mcp.tool()
    def mathformer_theory_suite_prepare_scenario(state: dict) -> Task:
        """Select and transform the next scenario; preserve its effective seed."""
        task = source().prepare_suite_scenario(state)
        task["context"] = state["context"]
        return {"task": task}

    @mcp.tool()
    def mathformer_theory_suite_run_scenario(task: dict) -> Result:
        """Run all native trajectories and write the scenario's six artifacts."""
        with native_context(task["context"]):
            write_guard((Path(task["output_dir"]) / task["scenario_id"]).resolve())
            return {"result": source().execute_suite_scenario(task)}

    @mcp.tool()
    def mathformer_theory_suite_accumulate(
        state: dict, task: dict, result: dict
    ) -> Accumulated:
        """Append the full result/model and advance the native scenario cursor."""
        return source().accumulate_suite_scenario(state, task, result)

    @mcp.tool()
    def mathformer_theory_suite_finalize_suite(state: dict) -> Terminal:
        """Write comparison outputs and preserve native terminal stdout."""
        with native_context(state["context"]):
            write_guard(Path(state["options"]["output_dir"]).resolve())
            stream = io.StringIO()
            with redirect_stdout(stream):
                result = source().finalize_suite(state)
            stdout = stream.getvalue()
            print(stdout, end="", file=sys.stderr)
            return {**result, "stdout": stdout}
