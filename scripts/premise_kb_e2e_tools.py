# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP bindings to the same KB regression stages used by the native CLI."""

from contextlib import redirect_stdout
from functools import lru_cache
import importlib.util
from pathlib import Path
import sys
from typing_extensions import TypedDict


@lru_cache(maxsize=1)
def source():
    path = Path(__file__).resolve().parents[1] / "tests/kb/run_premise_kb_e2e.py"
    spec = importlib.util.spec_from_file_location("_premise_kb_e2e_native", path)
    native = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(native)
    return native


class StateOutput(TypedDict):
    state: dict


class PayloadOutput(TypedDict):
    payload: dict


class ResultOutput(TypedDict):
    result: dict


def register_premise_kb_e2e_tools(mcp, guard=lambda path: None):
    def check(state):
        native = source()
        root = Path(state["kb_root"])
        absolute = root if root.is_absolute() else native.REPO_ROOT / root
        if str(absolute) != state["absolute_root"]:
            raise ValueError("KB root does not match resolved native context")
        guard(absolute)

    @mcp.tool()
    def mathformer_kb_e2e_prepare(request: dict) -> StateOutput:
        root = Path(request.get("kb_root", "artifacts/kb/premise_kb_e2e_test"))
        guard(root if root.is_absolute() else source().REPO_ROOT / root)
        return {"state": source().prepare(request)}

    @mcp.tool()
    def mathformer_kb_e2e_populate(state: dict) -> StateOutput:
        check(state)
        return {"state": source().populate(state)}

    @mcp.tool()
    def mathformer_kb_e2e_query(state: dict) -> StateOutput:
        check(state)
        return {"state": source().query(state)}

    @mcp.tool()
    def mathformer_kb_e2e_update_report(state: dict) -> StateOutput:
        check(state)
        return {"state": source().update_report(state)}

    @mcp.tool()
    def mathformer_kb_e2e_assess(state: dict) -> PayloadOutput:
        return {"payload": source().assess(state)}

    @mcp.tool()
    def mathformer_kb_e2e_emit(payload: dict, format: dict) -> ResultOutput:
        # Keep the source's printed evidence off MCP's stdout transport.
        with redirect_stdout(sys.stderr):
            result = source().emit(payload, format)
        return {"result": result}
