# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP ports for the shared native ProofNet evaluator transitions.

Open iterators belong to this server process. EOF and read errors close them;
server shutdown closes iterators left by interrupted/failed workflows.
"""

import atexit
from contextlib import redirect_stdout
from functools import lru_cache
import importlib.util
from pathlib import Path
import sys
from typing import TypedDict
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def source():
    sys.path.insert(0, str(ROOT / "benchmarks/proofnet"))
    spec = importlib.util.spec_from_file_location(
        "mathformer_proofnet_evaluator",
        ROOT / "benchmarks/proofnet/evaluate_predictions.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ConfigResult(TypedDict):
    config: dict


class GoldResult(TypedDict):
    gold: list[dict]


class StateResult(TypedDict):
    state: dict


class Transition(TypedDict):
    state: dict
    done: bool


class Finalized(TypedDict):
    metrics: dict
    payload: str
    write_file: bool


class Emitted(TypedDict):
    exit_code: int


def register_proofnet_evaluate_tools(mcp, write_guard):
    readers = {}

    def cleanup():
        for stream in readers.values():
            stream.close()
        readers.clear()

    atexit.register(cleanup)

    @mcp.tool()
    def mathformer_proofnet_parse(argv: list[str]) -> ConfigResult:
        with redirect_stdout(sys.stderr):
            try:
                args = source().parse_args(argv)
            except SystemExit as error:
                # argparse termination must terminate this call, never the MCP process.
                raise ValueError(
                    f"argparse terminated with exit code {error.code}"
                ) from error
        return {
            "config": {
                key: str(value) if isinstance(value, Path) else value
                for key, value in vars(args).items()
            }
        }

    @mcp.tool()
    def mathformer_proofnet_load_gold(config: dict) -> GoldResult:
        return {"gold": source().load_gold(Path(config["gold_dir"]), config["split"])}

    @mcp.tool()
    def mathformer_proofnet_initialize_predictions(config: dict) -> StateResult:
        state = source().prediction_state(
            Path(config["predictions_file"]), config["id_key"], config["prediction_key"]
        )
        stream = Path(config["predictions_file"]).open("r", encoding="utf-8")
        token = uuid4().hex
        readers[token] = stream
        state["reader"] = token
        return {"state": state}

    @mcp.tool()
    def mathformer_proofnet_read_prediction(state: dict) -> Transition:
        token = state["reader"]
        stream = readers[token]
        try:
            done = source().read_prediction(stream, state)
        except BaseException:
            readers.pop(token).close()
            raise
        if done:
            readers.pop(token).close()
        return {"state": state, "done": done}

    @mcp.tool()
    def mathformer_proofnet_initialize_scores(
        gold: list[dict], predictions: dict
    ) -> StateResult:
        return {"state": source().initialize_scores(gold, predictions["predictions"])}

    @mcp.tool()
    def mathformer_proofnet_score_example(state: dict) -> Transition:
        return {"state": state, "done": source().score_example(state)}

    @mcp.tool()
    def mathformer_proofnet_finalize(config: dict, scores: dict) -> Finalized:
        metrics = source().score_metrics(
            Path(config["gold_dir"]),
            config["split"],
            Path(config["predictions_file"]),
            scores,
        )
        metrics, payload, write_file = source().finalize_output(config, metrics)
        return {"metrics": metrics, "payload": payload, "write_file": write_file}

    @mcp.tool()
    def mathformer_proofnet_write_output(config: dict, payload: str) -> Emitted:
        write_guard()
        with redirect_stdout(sys.stderr):
            return {"exit_code": source().write_output(config, payload)}

    @mcp.tool()
    def mathformer_proofnet_print_output(payload: str) -> Emitted:
        with redirect_stdout(sys.stderr):
            return {"exit_code": source().print_output(payload)}
