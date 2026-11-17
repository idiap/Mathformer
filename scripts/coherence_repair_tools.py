# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable MCP ports sharing the repair planner's native implementation."""

from contextlib import redirect_stdout
from functools import lru_cache
import importlib.util
from pathlib import Path
import sys
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "skills/mathformerphysicslib/mathformerphysicslib-coherence-repair-planner/scripts/plan_coherence_repairs.py"


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "coherence_repair_native", ROOT / SOURCE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Parsed(TypedDict):
    args: dict


class Reports(TypedDict):
    reports: list[dict]


class Plan(TypedDict):
    payload: dict


class Written(TypedDict):
    pass


class Completion(TypedDict):
    payload: dict
    exit_code: int


def register_coherence_repair_tools(mcp, write_policy, path_allowed):
    @mcp.tool()
    def mathformer_coherence_repair_parse_arguments(argv: list[str]) -> Parsed:
        with redirect_stdout(sys.stderr):
            try:
                return {"args": source().parse_arguments(argv)}
            except SystemExit as error:
                raise ValueError(f"argparse exited with code {error.code}") from error

    @mcp.tool()
    def mathformer_coherence_repair_load_reports(args: dict) -> Reports:
        return {"reports": source().load_reports(args)}

    @mcp.tool()
    def mathformer_coherence_repair_default_reports(
        args: dict, repository_root: str
    ) -> Reports:
        return {
            "reports": source().default_reports(
                args["self_test"], Path(repository_root)
            )
        }

    @mcp.tool()
    def mathformer_coherence_repair_plan(reports: list[dict]) -> Plan:
        return {"payload": source().repair_plan(reports)}

    @mcp.tool()
    def mathformer_coherence_repair_write_output(args: dict, payload: dict) -> Written:
        write_policy()
        if not path_allowed(Path(args["output"])):
            raise ValueError("Output path is outside configured write roots")
        source().write_output(args, payload)
        return {}

    @mcp.tool()
    def mathformer_coherence_repair_emit(payload: dict) -> Completion:
        # Keep native JSON emission; stdio MCP reserves stdout for protocol data.
        with redirect_stdout(sys.stderr):
            code = source().emit(payload)
        return {"payload": payload, "exit_code": code}
