# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable strict/all runner blocks shared with the native CLI.

The matrix port is a canonical snapshot assertion, never an alternate command
source. CLI output is returned explicitly so MCP stdout remains valid JSON-RPC.
"""

import contextlib
import importlib.util
import io
from pathlib import Path
import sys
from typing_extensions import TypedDict


def source_runner():
    name = "_mathformer_comprehensive_runner"
    if name not in sys.modules:
        path = (
            Path(__file__).resolve().parents[1]
            / "tests/test_program/run_comprehensive_tests.py"
        )
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


class Context(TypedDict):
    run_id: str


class Prepared(TypedDict):
    state: dict
    has_rows: bool


class Advanced(TypedDict):
    state: dict
    done: bool


class Finalized(TypedDict):
    report: dict


class Published(TypedDict):
    outcome: dict


def strict_args(context):
    return source_runner().parse_args(
        [
            "--module-family",
            "all",
            "--profile",
            "strict",
            "--write-jsonl",
            "--write-junit",
            "--json",
            "--run-id",
            context["run_id"],
        ]
    )


def register_comprehensive_strict_tools(mcp):
    @mcp.tool()
    def mathformer_comprehensive_strict_prepare(
        matrix: dict, context: Context
    ) -> Prepared:
        import json

        native = source_runner()
        native.ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
        if matrix != json.loads(native.MATRIX_FILE.read_text(encoding="utf-8")):
            raise ValueError(
                "matrix must equal the canonical tests/test_matrix.json snapshot"
            )
        state = native.prepare_checks(strict_args(context))
        if len(state["selected"]) > 10000:
            raise ValueError("selected matrix exceeds the contract bound")
        state["context"] = dict(context)
        return {"state": state, "has_rows": bool(state["selected"])}

    @mcp.tool()
    def mathformer_comprehensive_strict_check_next(state: dict) -> Advanced:
        state = source_runner().advance_check(state, strict_args(state["context"]))
        return {"state": state, "done": state["index"] == len(state["selected"])}

    @mcp.tool()
    def mathformer_comprehensive_strict_retain_empty(state: dict) -> Advanced:
        if state["selected"] or state["results"] or state["index"] != 0:
            raise ValueError("retain_empty requires an empty selection")
        return {"state": state, "done": True}

    @mcp.tool()
    def mathformer_comprehensive_strict_finalize(state: dict) -> Finalized:
        return {
            "report": source_runner().finalize_checks(
                state, strict_args(state["context"])
            )
        }

    @mcp.tool()
    def mathformer_comprehensive_strict_publish(report: dict) -> Published:
        native = source_runner()
        args = strict_args({"run_id": report["run_id"]})
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = native.publish_report(report, args)
        return {
            "outcome": {
                "exit_code": code,
                "json_report": native.rel(args.output_file),
                "jsonl_report": native.rel(Path(args.write_jsonl)),
                "junit_report": native.rel(Path(args.write_junit)),
                "stdout": stream.getvalue(),
            }
        }
