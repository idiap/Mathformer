# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Typed read-only MCP operations for the native static ERFL validator."""

from contextlib import redirect_stdout, redirect_stderr
import io
from threading import Lock
from pathlib import Path
from typing_extensions import TypedDict

_EMISSION_LOCK = Lock()


class Context(TypedDict):
    repository_root: str
    program: str


class Request(TypedDict):
    paths: list[str]
    registry: str
    strict: bool
    check_registries: bool
    self_test: bool
    json: bool


class Prepared(TypedDict):
    session: dict
    route: str


class Expanded(TypedDict):
    state: dict
    has_files: bool


class Advanced(TypedDict):
    state: dict
    done: bool


class Completed(TypedDict):
    result: dict


class Early(TypedDict):
    result: dict
    state: dict


def source(context):
    # Isolate repository constants per call while loading the actual validator.
    import importlib.util
    import sys

    ROOT = Path(__file__).resolve().parents[1]
    root = Path(context["repository_root"]).resolve()
    root.relative_to(ROOT)
    path = (
        ROOT
        / "skills/control/reasoning-flow-language/scripts/validate_reasoning_flow.py"
    )
    spec = importlib.util.spec_from_file_location("_reasoning_flow_native", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.REPO_ROOT = root
    module.REASONING_REGISTRY = root / "skills/REASONING_TYPES.yaml"
    module.OUTPUT_REGISTRY = root / "skills/OUTPUT_TYPES.yaml"
    return module


def capture(function, value):
    """Keep CLI output out of the MCP transport, including argparse errors."""
    stdout, stderr = io.StringIO(), io.StringIO()
    payload = None
    with _EMISSION_LOCK, redirect_stdout(stdout), redirect_stderr(stderr):
        try:
            code, payload = function(value)
        except SystemExit as exc:
            code = int(exc.code)
    return {
        "result": {
            "exit_code": code,
            "payload": payload,
            "stdout": stdout.getvalue(),
            "stderr": stderr.getvalue(),
        }
    }


def terminal_state(session, result):
    """Carry an already emitted native result through the root-level loop."""
    return {
        "expanded_paths": [],
        "cursor": 0,
        "reports": [],
        "session": session,
        "pending": False,
        "result": result,
    }


def register_reasoning_flow_tools(mcp):
    @mcp.tool()
    def mathformer_reasoning_flow_prepare(
        request: Request, context: Context
    ) -> Prepared:
        native = source(context)
        import argparse

        args = argparse.Namespace(**request)
        args.paths = [Path(path) for path in request["paths"]]
        args.registry = Path(request["registry"])
        prepared = native.prepare_validation(args)
        prepared["session"]["context"] = dict(context)
        prepared["session"]["program"] = context["program"]
        return prepared

    @mcp.tool()
    def mathformer_reasoning_flow_early_exit(session: dict) -> Early:
        output = capture(source(session["context"]).validation_early_exit, session)
        return {**output, "state": terminal_state(session, output["result"])}

    @mcp.tool()
    def mathformer_reasoning_flow_self_test(session: dict) -> Early:
        output = capture(source(session["context"]).validation_self_test, session)
        return {**output, "state": terminal_state(session, output["result"])}

    @mcp.tool()
    def mathformer_reasoning_flow_expand(session: dict) -> Expanded:
        state = source(session["context"]).expand_validation(session)
        if len(state["expanded_paths"]) > 4096:
            raise ValueError("workflow input domain exceeds 4096 expanded paths")
        state.update(pending=bool(state["expanded_paths"]), result=None)
        return {"state": state, "has_files": state["pending"]}

    @mcp.tool()
    def mathformer_reasoning_flow_validate_next(state: dict) -> Advanced:
        state = source(state["session"]["context"]).validate_next_path(state)
        state["pending"] = state["cursor"] < len(state["expanded_paths"])
        return {"state": state, "done": not state["pending"]}

    @mcp.tool()
    def mathformer_reasoning_flow_finish(state: dict) -> Completed:
        return capture(source(state["session"]["context"]).finish_validation, state)

    @mcp.tool()
    def mathformer_reasoning_flow_settle(state: dict) -> Advanced:
        if state["pending"]:
            raise ValueError("settle requires no pending files")
        return {"state": state, "done": True}

    @mcp.tool()
    def mathformer_reasoning_flow_terminal_result(state: dict) -> Completed:
        if state["result"] is None:
            raise ValueError("terminal result requires a completed early route")
        return {"result": state["result"]}
