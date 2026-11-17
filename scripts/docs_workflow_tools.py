# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Owned documentation runner cursors over the original native implementation."""

from contextlib import redirect_stdout
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
from threading import RLock
from uuid import uuid4
from typing_extensions import TypedDict
from comprehensive_strict_tools import source_runner


def docs_source():
    name = "_mathformer_docs_wrapper"
    if name not in sys.modules:
        path = Path(__file__).resolve().parents[1] / "tests/run_docs.py"
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


class Parsed(TypedDict):
    args: dict


class Prepared(TypedDict):
    state: dict


class Guarded(TypedDict):
    done: bool


class Retained(TypedDict):
    state: dict
    done: bool


class Finalized(TypedDict):
    report: dict


class Published(TypedDict):
    exit_code: int


def register_docs_tools(mcp, authorize=lambda: None, path_allowed=lambda path: True):
    scopes = {}
    lock = RLock()

    def owned(args, phase, state=None):
        authorize()
        native = source_runner()
        if not path_allowed(native.ARTIFACT_ROOT):
            raise ValueError("docs artifacts outside service write roots")
        scope = scopes.get(args.get("handle"))
        if scope is None or scope["args"] != args or scope["phase"] != phase:
            raise ValueError("unknown, consumed, or out-of-order docs context")
        if state is not None and state != scope.get("state"):
            raise ValueError("modified docs cursor or history")
        return scope

    @mcp.tool()
    def mathformer_docs_parse(argv: list[str]) -> Parsed:
        authorize()
        # argparse SystemExit is a protocol error, never server termination.
        try:
            with redirect_stdout(sys.stderr):
                command = docs_source().delegate_command(argv)
        except SystemExit as error:
            raise ValueError("invalid docs CLI flags") from error
        native_args = source_runner().parse_args(command[2:])
        args = {
            key: str(value) if isinstance(value, Path) else value
            for key, value in vars(native_args).items()
        }
        args["handle"] = uuid4().hex
        with lock:
            scopes[args["handle"]] = {
                "args": deepcopy(args),
                "native_args": native_args,
                "phase": "prepare",
            }
        return {"args": args}

    @mcp.tool()
    def mathformer_docs_prepare(args: dict, matrix: dict) -> Prepared:
        with lock:
            scope = owned(args, "prepare")
            native = source_runner()
            native.ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
            if matrix != json.loads(native.MATRIX_FILE.read_text(encoding="utf-8")):
                raise ValueError("matrix must equal canonical tests/test_matrix.json")
            if len(matrix["tests"]) > 10000:
                raise ValueError("matrix exceeds contract bound of 10000")
            state = native.prepare_checks(scope["native_args"])
            scope.update(state=deepcopy(state), phase="guard")
            return {"state": state}

    @mcp.tool()
    def mathformer_docs_guard(state: dict, args: dict) -> Guarded:
        with lock:
            scope = owned(args, "guard", state)
            done = state["index"] >= len(state["selected"])
            scope["phase"] = "finalize" if done else "advance"
            return {"done": done}

    @mcp.tool()
    def mathformer_docs_advance(state: dict, args: dict) -> Prepared:
        with lock:
            scope = owned(args, "advance", state)
            try:
                state = source_runner().advance_check(state, scope["native_args"])
            except BaseException:
                scopes.pop(args["handle"], None)
                raise
            scope.update(state=deepcopy(state), phase="guard")
            return {"state": state}

    @mcp.tool()
    def mathformer_docs_retain_empty(state: dict, args: dict) -> Retained:
        with lock:
            owned(args, "finalize", state)
            if state["selected"] or state["results"] or state["index"] != 0:
                raise ValueError("retain_empty requires empty selection")
            return {"state": state, "done": True}

    @mcp.tool()
    def mathformer_docs_finalize(state: dict, args: dict) -> Finalized:
        with lock:
            scope = owned(args, "finalize", state)
            try:
                report = source_runner().finalize_checks(state, scope["native_args"])
            except BaseException:
                scopes.pop(args["handle"], None)
                raise
            scope.update(report=deepcopy(report), phase="publish")
            return {"report": report}

    @mcp.tool()
    def mathformer_docs_publish(report: dict, args: dict) -> Published:
        with lock:
            scope = owned(args, "publish")
            if report != scope["report"]:
                raise ValueError("modified docs report")
            scopes.pop(args["handle"])
            # MCP stdout is JSON-RPC; keep source CLI observability on stderr.
            with redirect_stdout(sys.stderr):
                code = source_runner().publish_report(report, scope["native_args"])
            return {"exit_code": code}
