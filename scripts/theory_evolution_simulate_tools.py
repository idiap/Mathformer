# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP ports for shared native simulation steps, with JSON RNG state."""

from contextlib import redirect_stdout
from functools import lru_cache
import importlib.util
import io
import os
from pathlib import Path
import sys
from threading import RLock
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "paper_skills/theory-evolution-simulator/scripts/simulate_theory_evolution.py"
_LOCK = RLock()


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "theory_simulator_native", ROOT / SOURCE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class State(TypedDict):
    state: dict


class Report(TypedDict):
    result: dict
    stdout: str


class Context(TypedDict):
    working_directory: str
    model_path: str


def register_theory_evolution_simulate_tools(mcp, write_guard=lambda path: None):
    @mcp.tool()
    def mathformer_theory_simulate_load(
        model: dict, options: dict, context: Context
    ) -> State:
        """Read native JSON and create output directory in explicit CLI context."""
        directory = Path(context["working_directory"])
        if not directory.is_absolute():
            raise ValueError("working_directory must be absolute")
        with _LOCK:
            previous = Path.cwd()
            try:
                os.chdir(directory)
                write_guard(Path(options["output_dir"]).resolve())
                batch = source().load_batch(context["model_path"], options)
                if batch["model"] != model:
                    raise ValueError("model payload differs from native file")
                if (
                    len(model["phases"]) > 16
                    or any(p["duration_steps"] > 256 for p in model["phases"])
                    or batch["options"]["runs"] > 64
                ):
                    raise ValueError("input exceeds contract domain")
                batch["context"] = dict(context)
                return {"state": batch}
            finally:
                os.chdir(previous)

    @mcp.tool()
    def mathformer_theory_simulate_initialize_run(batch: dict) -> State:
        """Initialize metrics, histories and the effective native seed."""
        if not batch["pending"]:
            # A zero native run range must not initialize metrics or read thresholds.
            return {
                "state": {
                    "model": batch["model"],
                    "run_id": batch["run_id"],
                    "seed": batch["options"]["seed"],
                    "rng": [],
                    "epsilon": 0,
                    "metrics": {},
                    "states": [],
                    "transitions": [],
                    "cumulative_cost": 0,
                    "step": 0,
                    "phase_index": 0,
                    "pending": False,
                }
            }
        return {
            "state": source().initialize_trajectory(
                batch["model"], batch["run_id"], batch["options"]["seed"]
            )
        }

    @mcp.tool()
    def mathformer_theory_simulate_prepare_phase(state: dict) -> State:
        """Enter the next ordered phase, retaining all trajectory state."""
        if not state["pending"]:
            return {
                "state": {
                    "trajectory": state,
                    "phase": {},
                    "phase_step": 0,
                    "pending": False,
                }
            }
        return {"state": source().prepare_phase(state)}

    @mcp.tool()
    def mathformer_theory_simulate_advance_step(state: dict) -> State:
        """Execute one native update and append both histories."""
        return {"state": source().advance_step(state) if state["pending"] else state}

    @mcp.tool()
    def mathformer_theory_simulate_finish_phase(state: dict) -> State:
        """Advance phase cursor, including empty range phases."""
        return {
            "state": (
                source().finish_phase(state)
                if state["trajectory"]["pending"]
                else state["trajectory"]
            )
        }

    @mcp.tool()
    def mathformer_theory_simulate_finish_run(batch: dict, trajectory: dict) -> State:
        """Classify only after all steps; append completed trajectory."""
        if not batch["pending"]:
            return {"state": batch}
        batch["runs"].append(source().finish_trajectory(trajectory))
        batch["run_id"] += 1
        batch["pending"] = batch["run_id"] < batch["options"]["runs"]
        return {"state": batch}

    @mcp.tool()
    def mathformer_theory_simulate_report(batch: dict) -> Report:
        """Write the five native artifacts in order; return and emit stdout."""
        with _LOCK:
            previous = Path.cwd()
            try:
                os.chdir(batch["context"]["working_directory"])
                write_guard(Path(batch["options"]["output_dir"]).resolve())
                stream = io.StringIO()
                with redirect_stdout(stream):
                    result = source().report_batch(batch)
                stdout = stream.getvalue()
                print(stdout, end="", file=sys.stderr)
                return {"result": result, "stdout": stdout}
            finally:
                os.chdir(previous)
