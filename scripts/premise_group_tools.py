# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP ports for the native group inverse regression, shared with its CLI."""

from functools import lru_cache
import importlib.util
from pathlib import Path
from typing_extensions import TypedDict


@lru_cache(maxsize=1)
def source():
    path = (
        Path(__file__).resolve().parents[1]
        / "tests/atp/run_premise_guided_group_inverse.py"
    )
    spec = importlib.util.spec_from_file_location(
        "mathformer_premise_group_source", path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RequestOutput(TypedDict):
    request: dict


class ReportOutput(TypedDict):
    report: dict


class ExitOutput(TypedDict):
    exit_code: int


def register_premise_group_tools(mcp, guard=None):
    @mcp.tool()
    def mathformer_group_resolve(args: dict) -> RequestOutput:
        return {"request": source().resolve_request(args)}

    @mcp.tool()
    def mathformer_group_discover(request: dict) -> ReportOutput:
        # Only the entrypoint's fixed scientific request is supported.
        expected = source().resolve_request(
            {"artifact_root": request["artifact_root"], "json": request["json"]}
        )
        if request != expected:
            raise ValueError("group regression request constants changed")
        if guard:
            guard(Path(request["artifact_root"]))
        return {"report": source().discover_request(request)}

    @mcp.tool()
    def mathformer_group_check(report: dict) -> ReportOutput:
        return {"report": source().check_report(report)}

    @mcp.tool()
    def mathformer_group_emit(
        request: dict, report: dict, exit_code: int
    ) -> ExitOutput:
        # stdout must not corrupt MCP's stdio framing; retain the native text
        # on the server diagnostic stream. The CLI still prints to stdout.
        import contextlib
        import sys

        with contextlib.redirect_stdout(sys.stderr):
            code = source().emit_report(request, report, exit_code)
        return {"exit_code": code}
