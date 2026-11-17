# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP ports sharing the coherence gate's native CLI steps."""

from contextlib import redirect_stdout
import sys
import json
from functools import lru_cache
import importlib.util
from pathlib import Path
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "skills/mathformerphysicslib/mathformerphysicslib-coherence-gate/scripts/gate_coherence.py"


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "coherence_gate_native", ROOT / SOURCE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Parsed(TypedDict):
    args: dict
    supplied_reports: bool
    supplied_repairs: bool


class Reports(TypedDict):
    reports: list[dict]


class Repairs(TypedDict):
    repairs: dict


class Gate(TypedDict):
    payload: dict
    serialized_payload: str


class Exit(TypedDict):
    exit_code: int


def register_coherence_gate_tools(mcp, write_policy):
    @mcp.tool()
    def mathformer_coherence_gate_parse(argv: list[str]) -> Parsed:
        try:
            args = source().parse_options(argv)
        except SystemExit as error:
            raise ValueError(f"argparse exited with code {error.code}") from error
        return dict(
            args=args,
            supplied_reports=bool(args["report"]),
            supplied_repairs=bool(args["repair_plan"]),
        )

    @mcp.tool()
    def mathformer_coherence_gate_load_reports(args: dict) -> Reports:
        return {"reports": source().load_reports(args)}

    @mcp.tool()
    def mathformer_coherence_gate_default_reports(args: dict) -> Reports:
        return {"reports": source().default_reports(args["self_test"])}

    @mcp.tool()
    def mathformer_coherence_gate_load_repairs(args: dict) -> Repairs:
        return {"repairs": source().load_repairs(args)}

    @mcp.tool()
    def mathformer_coherence_gate_propose_repairs(reports: list[dict]) -> Repairs:
        return {"repairs": source().repair_plan(reports)}

    @mcp.tool()
    def mathformer_coherence_gate_aggregate(reports: list[dict], repairs: dict) -> Gate:
        payload = source().aggregate(reports, repairs)
        return {"payload": payload, "serialized_payload": json.dumps(payload)}

    @mcp.tool()
    def mathformer_coherence_gate_emit_return(
        args: dict, repairs: dict, serialized_payload: str
    ) -> Exit:
        if args["output"] or args["markdown_output"]:
            write_policy()
        # Preserve native diagnostics on the stdio service diagnostic channel.
        with redirect_stdout(sys.stderr):
            return {
                "exit_code": source().emit_return(
                    args, repairs, json.loads(serialized_payload)
                )
            }
