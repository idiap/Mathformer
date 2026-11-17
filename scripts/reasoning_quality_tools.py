# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP ports for the source-owned reasoning quality audit steps."""

from functools import lru_cache
import importlib.util
from pathlib import Path
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "skills/control/reasoning-log-schema-guardian/scripts/audit_reasoning_log_quality.py"


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location("_quality_native", ROOT / SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Parsed(TypedDict):
    request: dict
    use_fixtures: bool


class Selected(TypedDict):
    selection: dict


class Audited(TypedDict):
    report: dict


class Emitted(TypedDict):
    result: dict


def register_reasoning_quality_tools(mcp, write_policy=lambda: None):
    @mcp.tool()
    def mathformer_reasoning_quality_parse_and_guard(
        argv: list[str], context: dict
    ) -> Parsed:
        try:
            return source().parse_and_guard(argv, context)
        except SystemExit as error:
            raise ValueError(
                f"native argument parser exited with status {error.code}"
            ) from error

    @mcp.tool()
    def mathformer_reasoning_quality_prepare_fixtures(request: dict) -> Selected:
        write_policy()
        return source().prepare_fixtures(request)

    @mcp.tool()
    def mathformer_reasoning_quality_select_supplied(request: dict) -> Selected:
        return source().select_supplied(request)

    @mcp.tool()
    def mathformer_reasoning_quality_audit_selected(
        request: dict, selection: dict
    ) -> Audited:
        return source().audit_selected(request, selection)

    @mcp.tool()
    def mathformer_reasoning_quality_verify_bad(
        request: dict, selection: dict, report: dict
    ) -> Audited:
        return source().verify_bad(request, selection, report)

    @mcp.tool()
    def mathformer_reasoning_quality_emit(request: dict, report: dict) -> Emitted:
        return source().emit(request, report)
