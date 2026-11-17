# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Typed MCP ports sharing the native Rocq wiki suite implementation."""

from functools import lru_cache
import importlib.util
from pathlib import Path
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "_rocq_wiki_suite", ROOT / "tests/rocq/run_wiki_suite.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Prepared(TypedDict):
    prepared: dict


class Result(TypedDict):
    result: dict


class Report(TypedDict):
    report: dict


def register_rocq_wiki_suite_tools(
    mcp, before_write=lambda: None, path_allowed=lambda path: True
):
    def admit(options):
        before_write()
        path = Path(options["output_dir"]).resolve()
        if not path_allowed(path):
            raise ValueError("destination outside allowed write roots")
        return path

    def validate(prepared):
        # Never execute caller-supplied argv: require the exact native commands.
        path = admit(prepared)
        expected = source().suite_context(
            output_dir=path,
            require_compiler=prepared["require_compiler"],
            timeout_sec=prepared["timeout_sec"],
        )
        if prepared != expected:
            raise ValueError("prepared context differs from native suite commands")

    @mcp.tool()
    def mathformer_rocq_wiki_suite_prepare(options: dict) -> Prepared:
        """Prepare the fixed repository suite and its output context."""
        path = admit(options)
        return {
            "prepared": source().prepare_suite(
                output_dir=path,
                require_compiler=options["require_compiler"],
                timeout_sec=options["timeout_sec"],
            )
        }

    @mcp.tool()
    def mathformer_rocq_wiki_suite_draft(prepared: dict) -> Result:
        """Run the native manifest drafter subprocess."""
        validate(prepared)
        return {"result": source().draft_suite(prepared)}

    @mcp.tool()
    def mathformer_rocq_wiki_suite_check(prepared: dict) -> Result:
        """Run the native execution checker subprocess."""
        validate(prepared)
        return {"result": source().check_suite(prepared)}

    @mcp.tool()
    def mathformer_rocq_wiki_suite_aggregate(
        prepared: dict, draft: dict, execution: dict
    ) -> Report:
        """Aggregate source-owned reports without promoting proof artifacts."""
        return {"report": source().aggregate_suite(prepared, draft, execution)}
