# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable ports for the native generated-skill lifecycle validator."""

from functools import lru_cache
import importlib.util
from pathlib import Path
from typing_extensions import TypedDict


@lru_cache(maxsize=1)
def source():
    path = (
        Path(__file__).resolve().parents[1]
        / "meta_skills/scripts/validate_generated_skill_lifecycle.py"
    )
    spec = importlib.util.spec_from_file_location("_generated_lifecycle_native", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Prepared(TypedDict):
    schema: dict
    state: dict
    has_records: bool


class Validated(TypedDict):
    findings: list[dict]


class Accumulated(TypedDict):
    state: dict
    done: bool


class Written(TypedDict):
    report: dict


def register_generated_lifecycle_tools(mcp, write_policy=lambda: None):
    @mcp.tool()
    def mathformer_generated_lifecycle_prepare(
        context: dict, record_bound: int
    ) -> Prepared:
        if record_bound != 10000:
            raise ValueError("record_bound must be 10000")
        return source().prepare(context, record_bound)

    @mcp.tool()
    def mathformer_generated_lifecycle_validate_record(
        schema: dict, state: dict, context: dict
    ) -> Validated:
        return source().validate_record(schema, state, context)

    @mcp.tool()
    def mathformer_generated_lifecycle_accumulate(
        state: dict, findings: list[dict], context: dict
    ) -> Accumulated:
        return source().accumulate(state, findings, context)

    @mcp.tool()
    def mathformer_generated_lifecycle_write_report(
        state: dict, context: dict
    ) -> Written:
        write_policy()
        return source().write_report(state, context)
