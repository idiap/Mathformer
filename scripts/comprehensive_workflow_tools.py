# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Workstation comprehensive runner blocks using the native cursor implementation.

Canonical matrix assertions and owned state prevent a transported cursor from
becoming an arbitrary command interface. Context retains parse-time defaults.
"""

from contextlib import redirect_stdout
from copy import deepcopy
import json
from pathlib import Path
import sys
from threading import RLock
from uuid import uuid4
from typing_extensions import TypedDict
from comprehensive_strict_tools import source_runner


class Context(TypedDict):
    run_id: str


class RuntimeContext(TypedDict):
    handle: str


class Prepared(TypedDict):
    state: dict
    context: RuntimeContext


class Updated(TypedDict):
    state: dict


class Guarded(TypedDict):
    done: bool


class Retained(TypedDict):
    state: dict
    done: bool


class Reported(TypedDict):
    report: dict


class Published(TypedDict):
    publication: dict


def register_comprehensive_tools(
    mcp, authorize=lambda: None, path_allowed=lambda path: True
):
    scopes = {}
    lock = RLock()

    def owned(context, state=None, phase=None):
        scope = scopes.get(context["handle"])
        if scope is None:
            raise ValueError("unknown or consumed comprehensive context")
        if (state is not None and state != scope["state"]) or (
            phase and scope["phase"] != phase
        ):
            raise ValueError("modified or out-of-order comprehensive state")
        authorize()
        native = source_runner()
        if not path_allowed(native.ARTIFACT_ROOT):
            raise ValueError("comprehensive artifacts outside service write roots")
        return scope

    @mcp.tool()
    def mathformer_comprehensive_prepare(matrix: dict, context: Context) -> Prepared:
        authorize()
        native = source_runner()
        if not path_allowed(native.ARTIFACT_ROOT):
            raise ValueError("comprehensive artifacts outside service write roots")
        with lock:
            native.ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
            if matrix != json.loads(native.MATRIX_FILE.read_text(encoding="utf-8")):
                raise ValueError("matrix must equal canonical tests/test_matrix.json")
            args = native.parse_args(
                [
                    "--module-family",
                    "all",
                    "--write-jsonl",
                    "--write-junit",
                    "--json",
                    "--run-id",
                    context["run_id"],
                ]
            )
            state = native.prepare_checks(args)
            if len(state["matrix"]) > 4096:
                raise ValueError("matrix exceeds the contract bound of 4096")
            handle = uuid4().hex
            scopes[handle] = {"args": args, "state": deepcopy(state), "phase": "guard"}
            return {"state": state, "context": {"handle": handle}}

    @mcp.tool()
    def mathformer_comprehensive_cursor_guard(
        state: dict, context: RuntimeContext
    ) -> Guarded:
        with lock:
            scope = owned(context, state, "guard")
            done = state["index"] >= len(state["selected"])
            scope["phase"] = "finalize" if done else "advance"
            return {"done": done}

    @mcp.tool()
    def mathformer_comprehensive_advance(
        state: dict, context: RuntimeContext
    ) -> Updated:
        with lock:
            scope = owned(context, state, "advance")
            try:
                state = source_runner().advance_check(state, scope["args"])
            except BaseException:
                scopes.pop(context["handle"], None)
                raise
            scope.update(state=deepcopy(state), phase="guard")
            return {"state": state}

    @mcp.tool()
    def mathformer_comprehensive_retain_empty(
        state: dict, context: RuntimeContext
    ) -> Retained:
        with lock:
            owned(context, state, "finalize")
            if state["selected"] or state["results"] or state["index"] != 0:
                raise ValueError("retain_empty requires empty selection")
            return {"state": state, "done": True}

    @mcp.tool()
    def mathformer_comprehensive_finalize(
        state: dict, context: RuntimeContext
    ) -> Reported:
        with lock:
            scope = owned(context, state, "finalize")
            try:
                report = source_runner().finalize_checks(state, scope["args"])
            except BaseException:
                scopes.pop(context["handle"], None)
                raise
            scope.update(report=deepcopy(report), phase="publish")
            return {"report": report}

    @mcp.tool()
    def mathformer_comprehensive_publish(
        report: dict, context: RuntimeContext
    ) -> Published:
        with lock:
            scope = owned(context, phase="publish")
            if report != scope["report"]:
                raise ValueError("modified comprehensive report")
            scopes.pop(context["handle"])
            native, args = source_runner(), scope["args"]
            # Preserve source JSON output on stderr; stdout belongs to MCP.
            with redirect_stdout(sys.stderr):
                code = native.publish_report(report, args)
            return {
                "publication": {
                    "exit_code": code,
                    "json": native.rel(args.output_file),
                    "jsonl": native.rel(Path(args.write_jsonl)),
                    "junit": native.rel(Path(args.write_junit)),
                }
            }
