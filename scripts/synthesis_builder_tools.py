# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable ports over the shared native synthesis builder stages.

Ordered native JSON carries insertion order across PRISM's canonical JSON
boundary. No judge is launched and no pending result is waited for here.
"""

import argparse
from contextlib import redirect_stdout
from functools import lru_cache
import importlib.util
import json
from pathlib import Path
import sys
from typing_extensions import TypedDict

SOURCE = (
    Path(__file__).resolve().parents[1]
    / "skills/physics-common/formalphysics-judge-synthesis-reporter/scripts/build_synthesis_report.py"
)


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location("_synthesis_builder_native", SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Ordered(TypedDict):
    native_json: str


class Options(TypedDict):
    self_test: bool
    comparative_report: str | None
    output_dir: str
    codex_results_json: list[str]
    codex_results_dir: list[str]
    json: bool


class Parsed(TypedDict):
    options: Options


class Loaded(TypedDict):
    loaded: Ordered


class Attached(TypedDict):
    report: Ordered


class Approaches(TypedDict):
    approaches: Ordered


class Stateful(TypedDict):
    state: Ordered


class Empty(TypedDict):
    state: Ordered
    report: Ordered


class Advanced(TypedDict):
    state: Ordered
    done: bool


class Synthesized(TypedDict):
    synthesis: Ordered


class Completion(TypedDict):
    returncode: int
    printed_result: dict


class Completed(TypedDict):
    result: Completion


def pack(value):
    return {"native_json": json.dumps(value, ensure_ascii=False)}


def unpack(value):
    return json.loads(value["native_json"])


def arguments(options):
    value = dict(options)
    for name in ("comparative_report", "output_dir"):
        value[name] = Path(value[name]) if value[name] is not None else None
    for name in ("codex_results_json", "codex_results_dir"):
        value[name] = [Path(p) for p in value[name]]
    return argparse.Namespace(**value)


def register_synthesis_builder_tools(mcp, before_write):
    native = source()

    @mcp.tool()
    def mathformer_synthesis_builder_empty_aspects() -> Empty:
        """No comparative state exists in the native self-test branch."""
        return {"state": pack(None), "report": pack(None)}

    @mcp.tool()
    def mathformer_synthesis_builder_retain_aspects(state: Ordered) -> Advanced:
        """Pass through absent comparative state; perform no native work."""
        if unpack(state) is not None:
            raise ValueError("retain is only for the absent self-test state")
        return {"state": state, "done": True}

    @mcp.tool()
    def mathformer_synthesis_builder_parse_cli(argv: list[str]) -> Parsed:
        try:
            with redirect_stdout(sys.stderr):
                args = native.parse_args(argv)
        except SystemExit as error:
            raise ValueError(f"argument parser exited: {error.code}") from error
        options = vars(args)
        options["comparative_report"] = (
            str(args.comparative_report)
            if args.comparative_report is not None
            else None
        )
        options["output_dir"] = str(args.output_dir)
        for key in ("codex_results_json", "codex_results_dir"):
            options[key] = [str(p) for p in options[key]]
        return {"options": options}

    @mcp.tool()
    def mathformer_synthesis_builder_self_test(options: Options) -> Completed:
        before_write()
        with redirect_stdout(sys.stderr):
            return {"result": native.complete_self_test(arguments(options))}

    @mcp.tool()
    def mathformer_synthesis_builder_load_inputs(options: Options) -> Loaded:
        try:
            return {"loaded": pack(native.load_inputs(arguments(options)))}
        except SystemExit as error:
            # FastMCP transports Exception failures; keep the server alive on a
            # native CLI early exit, retaining its source-owned diagnostic.
            raise ValueError(str(error)) from error

    @mcp.tool()
    def mathformer_synthesis_builder_attach_results(loaded: Ordered) -> Attached:
        return {"report": pack(native.attach_results(unpack(loaded)))}

    @mcp.tool()
    def mathformer_synthesis_builder_summarize_approaches(
        report: Ordered,
    ) -> Approaches:
        return {"approaches": pack(native.summarize_approaches(unpack(report)))}

    @mcp.tool()
    def mathformer_synthesis_builder_pack_aspects(approaches: Ordered) -> Stateful:
        return {"state": pack(native.pack_aspects(unpack(approaches)))}

    @mcp.tool()
    def mathformer_synthesis_builder_compare_next_aspect(state: Ordered) -> Advanced:
        state, done = native.compare_next_aspect(unpack(state))
        return {"state": pack(state), "done": done}

    @mcp.tool()
    def mathformer_synthesis_builder_finish_synthesis(
        report: Ordered, aspects: Ordered
    ) -> Synthesized:
        return {
            "synthesis": pack(native.finish_synthesis(unpack(report), unpack(aspects)))
        }

    @mcp.tool()
    def mathformer_synthesis_builder_emit(
        options: Options, synthesis: Ordered
    ) -> Completed:
        before_write()
        with redirect_stdout(sys.stderr):
            return {"result": native.emit(arguments(options), unpack(synthesis))}
