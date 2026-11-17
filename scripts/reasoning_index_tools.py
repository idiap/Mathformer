# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP ports for the shared native reasoning-index validation steps."""

import importlib.util
from functools import lru_cache
from pathlib import Path
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "skills/control/reasoning-log-schema-guardian/scripts/validate_reasoning_log_index.py"


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "reasoning_index_native", ROOT / SOURCE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Loaded(TypedDict):
    state: dict
    scan: bool


class Advanced(TypedDict):
    state: dict
    done: bool


class Finalized(TypedDict):
    report: dict


def register_reasoning_index_tools(mcp):
    @mcp.tool()
    def mathformer_reasoning_index_load(index: str) -> Loaded:
        result = source().load_initialize(Path(index))
        # Admission to this bounded specialization, never a native finding.
        if len(result["state"]["entries"]) > 1000:
            raise ValueError(
                "Index exceeds the workflow admission limit of 1000 entries"
            )
        return result

    @mcp.tool()
    def mathformer_reasoning_index_advance(state: dict) -> Advanced:
        # v1 loops execute at least once; the empty traversal has no entry body.
        if state["offset"] == len(state["entries"]):
            return {"state": state, "done": True}
        return source().validate_entry_advance(state)

    @mcp.tool()
    def mathformer_reasoning_index_finalize(state: dict) -> Finalized:
        return {"report": source().finalize(state)}
