# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Typed MCP boundaries for the native textual derivation checker.

No compiler or provider is invoked. Native functions also serve the CLI; the
self-test directory is explicit so callers can isolate its two written fixtures.
"""

import argparse
from contextlib import redirect_stdout
from functools import lru_cache
import importlib.util
from pathlib import Path
import sys
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "skills/physics-lean/physics-lean-derivation-completeness-checker/scripts/check_derivation_completeness.py"


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "derivation_completeness_native", ROOT / SOURCE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Parsed(TypedDict):
    args: dict


class Initialized(TypedDict):
    state: dict


class Analyzed(TypedDict):
    artifact: dict


class Advanced(TypedDict):
    state: dict
    done: bool


class Reported(TypedDict):
    report: dict


class Emitted(TypedDict):
    exit_code: int


def namespace(args):
    values = dict(args)
    for name in ("source_record", "recursive_plan", "output"):
        if values[name] is not None:
            values[name] = Path(values[name])
    return argparse.Namespace(**values)


def register_derivation_completeness_tools(mcp, write_policy, path_allowed):
    def authorize(path):
        write_policy()
        if not path_allowed(path):
            raise ValueError(
                "Derivation completeness output is outside service write roots"
            )

    @mcp.tool()
    def mathformer_derivation_completeness_parse(argv: list[str]) -> Parsed:
        if len(argv) > 1024:
            raise ValueError("Normalized workflow admits at most 1024 argv tokens")
        try:
            # Stdout is the MCP protocol channel; retain argparse help on diagnostics.
            with redirect_stdout(sys.stderr):
                args = source().parse_args(argv)
        except SystemExit as error:
            raise ValueError(
                f"Native argparse exited with code {error.code}"
            ) from error
        return {
            "args": {
                key: str(value) if isinstance(value, Path) else value
                for key, value in vars(args).items()
            }
        }

    @mcp.tool()
    def mathformer_derivation_completeness_self_test(directory: str) -> Reported:
        path = Path(directory)
        authorize(path / "bad.lean")
        authorize(path / "good.lean")
        return {"report": source().self_test(path)}

    @mcp.tool()
    def mathformer_derivation_completeness_initialize(args: dict) -> Initialized:
        if not args["lean_file"]:
            raise ValueError("--lean-file is required unless --self-test is used")
        if len(args["lean_file"]) > 1024:
            raise ValueError("Normalized workflow admits at most 1024 files")
        return {"state": source().initialize_report(namespace(args))}

    @mcp.tool()
    def mathformer_derivation_completeness_initialize_self_test() -> Initialized:
        # An administrative frame, with no file traversal or input reads. Lunar
        # cannot lower exhaustion exits inside a switch; the root loop selects
        # either this one-shot native self-test or the ordinary file traversal.
        return {
            "state": {
                "files": [],
                "source_record": {},
                "frontier_count": 0,
                "index": 0,
                "artifacts": [],
                "self_test_report": {},
            }
        }

    @mcp.tool()
    def mathformer_derivation_completeness_finish_self_test(
        state: dict, report: dict
    ) -> Advanced:
        return {"state": {**state, "self_test_report": report}, "done": True}

    @mcp.tool()
    def mathformer_derivation_completeness_analyze_current(state: dict) -> Analyzed:
        return {"artifact": source().analyze_current(state)}

    @mcp.tool()
    def mathformer_derivation_completeness_advance(
        state: dict, artifact: dict
    ) -> Advanced:
        return source().advance_report(state, artifact)

    @mcp.tool()
    def mathformer_derivation_completeness_aggregate(state: dict) -> Reported:
        return {
            "report": (
                state["self_test_report"]
                if "self_test_report" in state
                else source().aggregate_report(state)
            )
        }

    @mcp.tool()
    def mathformer_derivation_completeness_emit(args: dict, report: dict) -> Emitted:
        native_args = namespace(args)
        if native_args.output:
            authorize(native_args.output)
        with redirect_stdout(sys.stderr):
            code = source().emit_report(native_args, report)
        return {"exit_code": code}
